import asyncio
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .accounts import parse_accounts
from .cancellation import CancellationToken
from .runner import StatusUpdate, run_text
from .ui_models import ViotpConfig, calculate_stats
from .viotp_dialog import ViotpConfigOverlay


class Application:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.events: queue.Queue[object] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.cancellation: CancellationToken | None = None
        self.viotp_config: ViotpConfig | None = None
        self.viotp_dialog: ViotpConfigOverlay | None = None
        self.statuses: dict[int, str] = {}
        self.closing = False
        self.running = False

        root.title("9Router · Codex Account Connector")
        root.geometry("1100x760")
        root.minsize(960, 680)
        root.configure(bg="#f4f1ea")
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._configure_style()
        self._build()
        root.after(100, self._drain_events)

    def _configure_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f4f1ea")
        style.configure("TLabel", background="#f4f1ea", foreground="#20251f", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 20))
        style.configure("Section.TLabel", font=("Segoe UI Semibold", 11))
        style.configure("Hint.TLabel", foreground="#60675e")
        style.configure("Accent.TButton", background="#245c45", foreground="white", padding=(18, 10))
        style.map("Accent.TButton", background=[("active", "#194b37"), ("disabled", "#9aa69f")])
        style.configure("TButton", padding=(14, 9))
        style.configure("Treeview", rowheight=28, background="#fffdf8", fieldbackground="#fffdf8")
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 9), padding=6)
        style.configure("Overlay.TFrame", background="#d4d1ca")
        style.configure("Modal.TFrame", background="#fffdf8", relief="solid", borderwidth=1)
        style.configure("Modal.TLabel", background="#fffdf8", foreground="#20251f", font=("Segoe UI", 10))
        style.configure("ModalTitle.TLabel", background="#fffdf8", foreground="#20251f", font=("Segoe UI Semibold", 18))
        style.configure("ModalHint.TLabel", background="#fffdf8", foreground="#60675e")

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=22)
        outer.grid(sticky="nsew")
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        outer.columnconfigure(0, weight=4)
        outer.columnconfigure(1, weight=6)
        outer.rowconfigure(4, weight=1)

        header = ttk.Frame(outer)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 18))
        header.columnconfigure(0, weight=1)
        title = ttk.Frame(header)
        title.grid(row=0, column=0, sticky="w")
        ttk.Label(title, text="Codex Account Connector", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            title,
            text="Mỗi tài khoản chạy trong một tiến trình Google Chrome riêng.",
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(3, 0))
        settings = ttk.Frame(header)
        settings.grid(row=0, column=1, sticky="e")
        self.viotp_summary = ttk.Label(settings, text="VIOTP: Chưa cấu hình", style="Hint.TLabel")
        self.viotp_summary.pack(side="left", padx=(0, 10))
        self.viotp_button = ttk.Button(settings, text="Cấu hình VIOTP", command=self._open_viotp)
        self.viotp_button.pack(side="left")

        connection = ttk.LabelFrame(outer, text="1. Cấu hình kết nối", padding=16)
        connection.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        ttk.Label(connection, text="9router HOST").pack(anchor="w")
        self.host = ttk.Entry(connection, font=("Segoe UI", 11))
        self.host.insert(0, "http://localhost:20127")
        self.host.pack(fill="x", pady=(6, 13), ipady=7)
        ttk.Label(connection, text="Mật khẩu dashboard (nếu bật đăng nhập)").pack(anchor="w")
        self.dashboard_password = ttk.Entry(connection, font=("Segoe UI", 11), show="•")
        self.dashboard_password.pack(fill="x", pady=(6, 14), ipady=7)
        ttk.Label(connection, text="Chế độ Chrome").pack(anchor="w")
        mode = ttk.Frame(connection)
        mode.pack(fill="x", pady=(6, 3))
        self.browser_mode = tk.StringVar(value="visible")
        self.visible_mode = ttk.Radiobutton(mode, text="Hiển thị", value="visible", variable=self.browser_mode)
        self.visible_mode.pack(side="left")
        self.headless_mode = ttk.Radiobutton(mode, text="Chạy ẩn", value="headless", variable=self.browser_mode)
        self.headless_mode.pack(side="left", padx=(12, 0))
        ttk.Label(
            connection,
            text="Chạy ẩn không phù hợp khi cần CAPTCHA hoặc xác minh thủ công.",
            style="Hint.TLabel",
            wraplength=360,
        ).pack(anchor="w", pady=(5, 0))

        accounts_frame = ttk.LabelFrame(outer, text="2. Danh sách tài khoản", padding=16)
        accounts_frame.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        accounts_frame.columnconfigure(0, weight=1)
        accounts_frame.rowconfigure(1, weight=1)
        account_header = ttk.Frame(accounts_frame)
        account_header.grid(row=0, column=0, sticky="ew", pady=(0, 7))
        ttk.Label(account_header, text="Mỗi dòng: email|password|2fa_secret", style="Hint.TLabel").pack(side="left")
        self.account_count = ttk.Label(account_header, text="0 tài khoản")
        self.account_count.pack(side="right")
        self.accounts = tk.Text(
            accounts_frame,
            height=9,
            wrap="none",
            font=("Consolas", 10),
            bg="#fffdf8",
            fg="#20251f",
            insertbackground="#20251f",
            relief="solid",
            borderwidth=1,
            padx=10,
            pady=10,
        )
        self.accounts.grid(row=1, column=0, sticky="nsew")
        self.accounts.bind("<KeyRelease>", self._update_account_count)
        account_actions = ttk.Frame(accounts_frame)
        account_actions.grid(row=2, column=0, sticky="ew", pady=(9, 0))
        self.choose_button = ttk.Button(account_actions, text="Chọn file .txt", command=self._choose_file)
        self.choose_button.pack(side="left")
        self.clear_button = ttk.Button(account_actions, text="Xóa danh sách", command=self._clear_accounts)
        self.clear_button.pack(side="left", padx=(8, 0))

        actions = ttk.Frame(outer)
        actions.grid(row=2, column=0, columnspan=2, sticky="ew", pady=14)
        self.start_button = ttk.Button(actions, text="Bắt đầu kết nối", style="Accent.TButton", command=self._start)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(actions, text="Dừng", command=self._stop, state="disabled")
        self.stop_button.pack(side="left", padx=(8, 0))
        self.summary = ttk.Label(actions, text="Sẵn sàng", style="Hint.TLabel")
        self.summary.pack(side="left", padx=14)

        results_header = ttk.Frame(outer)
        results_header.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 7))
        ttk.Label(results_header, text="3. Kết quả", style="Section.TLabel").pack(side="left")
        self.stats_label = ttk.Label(results_header, text=self._stats_text(), style="Hint.TLabel")
        self.stats_label.pack(side="right")
        columns = ("line", "account", "status", "detail")
        self.results = ttk.Treeview(outer, columns=columns, show="headings")
        headings = {"line": "Dòng", "account": "Tài khoản", "status": "Trạng thái", "detail": "Chi tiết"}
        widths = {"line": 55, "account": 250, "status": 150, "detail": 480}
        for column in columns:
            self.results.heading(column, text=headings[column])
            self.results.column(column, width=widths[column], minwidth=widths[column], stretch=column == "detail")
        self.results.grid(row=4, column=0, columnspan=2, sticky="nsew")

    def _open_viotp(self) -> None:
        if self.viotp_dialog and self.viotp_dialog.winfo_exists():
            self.viotp_dialog.lift()
            return
        self.viotp_dialog = ViotpConfigOverlay(
            self.root,
            self.viotp_config,
            self._save_viotp,
            self._close_viotp,
        )

    def _close_viotp(self) -> None:
        self.viotp_dialog = None

    def _save_viotp(self, config: ViotpConfig) -> None:
        self.viotp_config = config
        self.viotp_summary.configure(text=config.summary)

    def _update_account_count(self, _event: tk.Event | None = None) -> None:
        accounts, errors = parse_accounts(self.accounts.get("1.0", "end-1c"))
        suffix = f" · {len(errors)} dòng lỗi" if errors else ""
        self.account_count.configure(text=f"{len(accounts)} tài khoản{suffix}")

    def _choose_file(self) -> None:
        selected = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not selected:
            return
        try:
            content = Path(selected).read_text(encoding="utf-8-sig")
        except OSError as error:
            messagebox.showerror("Không thể đọc file", str(error))
            return
        self.accounts.delete("1.0", "end")
        self.accounts.insert("1.0", content)
        self._update_account_count()

    def _clear_accounts(self) -> None:
        self.accounts.delete("1.0", "end")
        self._update_account_count()

    def _start(self) -> None:
        host = self.host.get().strip()
        text = self.accounts.get("1.0", "end-1c")
        if not host or not text.strip():
            messagebox.showwarning("Thiếu dữ liệu", "Nhập HOST và ít nhất một tài khoản.")
            return
        for item in self.results.get_children():
            self.results.delete(item)
        self.statuses.clear()
        self._update_stats()
        password = self.dashboard_password.get() or None
        headless = self.browser_mode.get() == "headless"
        self.cancellation = CancellationToken()
        self._set_running(True)
        self.worker = threading.Thread(
            target=self._run_worker,
            args=(text, host, password, headless, self.cancellation),
            daemon=False,
        )
        self.worker.start()

    def _run_worker(
        self, text: str, host: str, password: str | None, headless: bool, cancellation: CancellationToken
    ) -> None:
        try:
            asyncio.run(run_text(text, host, self.events.put, cancellation, password, headless))
            self.events.put(("done", "Hoàn tất"))
        except Exception as error:
            self.events.put(("error", str(error) or type(error).__name__))
        finally:
            self.events.put(("worker_stopped", ""))

    def _drain_events(self) -> None:
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            if isinstance(event, StatusUpdate):
                values = (event.line_number, event.masked_email, event.status, event.detail)
                item = str(event.line_number)
                if self.results.exists(item):
                    self.results.item(item, values=values)
                else:
                    self.results.insert("", "end", iid=item, values=values)
                self.statuses[event.line_number] = str(event.status)
                self._update_stats()
                self.summary.configure(text=f"Dòng {event.line_number}: {event.status}")
            elif event[0] == "error":
                self._set_running(False)
                if not self.closing:
                    messagebox.showerror("Không thể chạy", event[1])
            elif event[0] == "done":
                self._set_running(False)
                self.summary.configure(text=event[1])
            elif event[0] == "worker_stopped" and self.closing:
                self.root.destroy()
                return
        self.root.after(100, self._drain_events)

    def _stats_text(self) -> str:
        stats = calculate_stats(self.statuses)
        return (
            f"Tổng {stats.total}   Đang chạy {stats.running}   Thành công {stats.success}   "
            f"Thất bại {stats.failed}   Đã dừng {stats.cancelled}"
        )

    def _update_stats(self) -> None:
        self.stats_label.configure(text=self._stats_text())

    def _set_running(self, running: bool) -> None:
        self.running = running
        state = "disabled" if running else "normal"
        self.host.configure(state=state)
        self.dashboard_password.configure(state=state)
        self.visible_mode.configure(state=state)
        self.headless_mode.configure(state=state)
        self.accounts.configure(state=state)
        self.choose_button.configure(state=state)
        self.clear_button.configure(state=state)
        self.viotp_button.configure(state=state)
        self.start_button.configure(state=state)
        self.stop_button.configure(state="normal" if running else "disabled")
        if running:
            self.summary.configure(text="Đang khởi chạy Chrome…")

    def _stop(self) -> None:
        if self.cancellation:
            self.cancellation.cancel()
        self.stop_button.configure(state="disabled")
        self.summary.configure(text="Đang dọn Chrome…")

    def _on_close(self) -> None:
        if self.worker and self.worker.is_alive():
            if not messagebox.askokcancel("Automation đang chạy", "Đóng sau khi các Chrome được dọn dẹp?"):
                return
            self.closing = True
            self._stop()
            self.root.withdraw()
            return
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    Application(root)
    root.mainloop()


if __name__ == "__main__":
    main()
