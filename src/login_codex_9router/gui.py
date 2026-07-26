"""Cửa sổ chính: gắn command vào widget, chạy automation trong thread nền.

Bố cục widget nằm ở `main_window_layout`, style ở `theme`.
"""

import asyncio
import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .accounts import parse_accounts
from .auth.results import WAITING_MANUAL_STATUS
from .cancellation import CancellationToken
from .config import (
    DEFAULT_NETWORK,
    AppConfig,
    ConfigError,
    load_config,
    normalize_host,
    save_config,
)
from .main_window_layout import build_main_window
from .runner import StatusUpdate, run_text
from .theme import BACKGROUND, configure_style
from .ui_models import ViotpConfig, calculate_stats
from .viotp_dialog import ViotpConfigOverlay

NO_VIOTP_SUMMARY = "VIOTP: Chưa cấu hình"

# Sau khi nhấn Dừng, chờ tối đa ngần này rồi thoát cưỡng bức nếu Playwright treo.
CLEANUP_TIMEOUT_MS = 30_000


class Application:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.events: queue.Queue[object] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.cancellation: CancellationToken | None = None
        self.app_config, config_error = load_config()
        self.viotp_config = (
            ViotpConfig(self.app_config.viotp_token, self.app_config.viotp_network, None)
            if self.app_config.viotp_token
            else None
        )
        self.viotp_dialog: ViotpConfigOverlay | None = None
        self.viotp_backdrop: ttk.Frame | None = None
        self.statuses: dict[int, str] = {}
        self.account_tokens: dict[int, CancellationToken] = {}
        self.closing = False
        self.running = False

        root.title("9Router · Codex Account Connector")
        root.geometry("1100x760")
        root.minsize(960, 680)
        root.configure(bg=BACKGROUND)
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        configure_style()
        self._build()
        if config_error:
            root.after_idle(
                lambda: messagebox.showwarning(
                    "Không thể đọc cấu hình",
                    f"Ứng dụng đang dùng cấu hình mặc định.\n\n{config_error}",
                    parent=root,
                )
            )
        root.after(100, self._drain_events)

    def _build(self) -> None:
        summary_text = self.viotp_config.summary if self.viotp_config else NO_VIOTP_SUMMARY
        widgets = build_main_window(self.root, self.app_config, summary_text, self._stats_text())
        self.host = widgets.host
        self.dashboard_password = widgets.dashboard_password
        self.browser_mode = widgets.browser_mode
        self.visible_mode = widgets.visible_mode
        self.headless_mode = widgets.headless_mode
        self.accounts = widgets.accounts
        self.account_count = widgets.account_count
        self.choose_button = widgets.choose_button
        self.clear_button = widgets.clear_button
        self.viotp_summary = widgets.viotp_summary
        self.viotp_button = widgets.viotp_button
        self.start_button = widgets.start_button
        self.stop_button = widgets.stop_button
        self.skip_button = widgets.skip_button
        self.summary = widgets.summary
        self.stats_label = widgets.stats_label
        self.results = widgets.results

        self.viotp_button.configure(command=self._open_viotp)
        self.choose_button.configure(command=self._choose_file)
        self.clear_button.configure(command=self._clear_accounts)
        self.start_button.configure(command=self._start)
        self.stop_button.configure(command=self._stop)
        self.skip_button.configure(command=self._skip_selected)
        self.accounts.bind("<KeyRelease>", self._update_account_count)
        self.results.bind("<<TreeviewSelect>>", self._refresh_skip_button)

    def _open_viotp(self) -> None:
        if self.viotp_dialog and self.viotp_dialog.winfo_exists():
            self.viotp_dialog.lift()
            return
        # Dọn backdrop cũ trước: nếu overlay lần trước chết mà không gọi on_close thì
        # backdrop còn sót lại sẽ phủ kín cửa sổ và nuốt mọi thao tác chuột.
        self._destroy_backdrop()
        # Backdrop phủ kín cửa sổ để modal tách bạch về thị giác; grab_set của overlay
        # mới là thứ thực sự chặn tương tác.
        self.viotp_backdrop = ttk.Frame(self.root, style="Overlay.TFrame")
        self.viotp_backdrop.place(x=0, y=0, relwidth=1, relheight=1)
        try:
            self.viotp_dialog = ViotpConfigOverlay(
                self.root,
                self.viotp_config,
                self._save_viotp,
                self._close_viotp,
            )
        except BaseException:
            self._destroy_backdrop()
            raise

    def _destroy_backdrop(self) -> None:
        if self.viotp_backdrop is not None:
            self.viotp_backdrop.destroy()
            self.viotp_backdrop = None

    def _close_viotp(self) -> None:
        self._destroy_backdrop()
        self.viotp_dialog = None

    def _save_viotp(self, config: ViotpConfig) -> None:
        self.viotp_config = config if config.token else None
        summary = self.viotp_config.summary if self.viotp_config else NO_VIOTP_SUMMARY
        self.viotp_summary.configure(text=summary)
        self._persist_app_config()

    def _collect_app_config(self) -> AppConfig:
        return AppConfig(
            host=normalize_host(self.host.get()),
            browser_mode=self.browser_mode.get(),
            dashboard_password=self.dashboard_password.get(),
            viotp_token=self.viotp_config.token if self.viotp_config else "",
            viotp_network=self.viotp_config.network if self.viotp_config else DEFAULT_NETWORK,
        )

    def _persist_app_config(
        self, config: AppConfig | None = None, context: str = "Cấu hình vẫn dùng được trong phiên này"
    ) -> None:
        try:
            config = config or self._collect_app_config()
            if config != self.app_config:
                self.app_config = save_config(config)
        except (ConfigError, OSError, ValueError) as error:
            messagebox.showwarning(
                "Không thể lưu cấu hình",
                f"{context} nhưng chưa được lưu.\n\n{error}",
                parent=self.root,
            )

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
        text = self.accounts.get("1.0", "end-1c")
        if not self.host.get().strip() or not text.strip():
            messagebox.showwarning("Thiếu dữ liệu", "Nhập HOST và ít nhất một tài khoản.")
            return
        try:
            config = self._collect_app_config()
        except ValueError as error:
            messagebox.showwarning("HOST không hợp lệ", str(error), parent=self.root)
            return
        self._persist_app_config(config, "Automation vẫn tiếp tục")
        for item in self.results.get_children():
            self.results.delete(item)
        self.statuses.clear()
        self.account_tokens.clear()
        self._update_stats()
        password = config.dashboard_password or None
        headless = config.browser_mode == "headless"
        self.cancellation = CancellationToken()
        self._set_running(True)
        self.worker = threading.Thread(
            target=self._run_worker,
            args=(text, config.host, password, headless, self.cancellation),
            daemon=False,
        )
        self.worker.start()

    def _run_worker(
        self, text: str, host: str, password: str | None, headless: bool, cancellation: CancellationToken
    ) -> None:
        def on_account_start(line_number: int, token: CancellationToken) -> None:
            self.events.put(("account_token", line_number, token))

        try:
            asyncio.run(
                run_text(
                    text,
                    host,
                    self.events.put,
                    cancellation,
                    password,
                    headless,
                    on_account_start=on_account_start,
                )
            )
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
                self._refresh_skip_button()
                self.summary.configure(text=f"Dòng {event.line_number}: {event.status}")
            elif event[0] == "account_token":
                self.account_tokens[event[1]] = event[2]
                self._refresh_skip_button()
            elif event[0] == "error":
                if not self.closing:
                    messagebox.showerror("Không thể chạy", event[1])
            elif event[0] == "done":
                self.summary.configure(text=self._completion_text())
            elif event[0] == "worker_stopped":
                # Mở khóa tại đây chứ không ở "done"/"error": nếu worker chết vì một
                # BaseException (CancelledError, SystemExit) thì hai nhánh kia không chạy
                # và giao diện sẽ kẹt ở trạng thái disabled vĩnh viễn.
                self._set_running(False)
                if self.closing:
                    self.root.destroy()
                    return
        self.root.after(100, self._drain_events)

    def _completion_text(self) -> str:
        stats = calculate_stats(self.statuses)
        if not stats.total:
            return "Không có tài khoản nào để chạy"
        parts = [f"thành công {stats.success}/{stats.total}"]
        if stats.failed:
            parts.append(f"thất bại {stats.failed}")
        if stats.cancelled:
            parts.append(f"đã dừng {stats.cancelled}")
        return "Hoàn tất · " + " · ".join(parts)

    def _stats_text(self) -> str:
        stats = calculate_stats(self.statuses)
        text = (
            f"Tổng {stats.total}   Đang chạy {stats.running}   Thành công {stats.success}   "
            f"Thất bại {stats.failed}   Đã dừng {stats.cancelled}"
        )
        return f"{text}   Chờ xác minh {stats.waiting}" if stats.waiting else text

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
        self._refresh_skip_button()
        if running:
            self.summary.configure(text="Đang khởi chạy Chrome…")

    def _stop(self) -> None:
        if self.cancellation:
            self.cancellation.cancel()
        self.stop_button.configure(state="disabled")
        self.skip_button.configure(state="disabled")
        self.summary.configure(text="Đang dọn Chrome…")

    def _selected_line(self) -> int | None:
        selection = self.results.selection()
        if not selection:
            return None
        try:
            return int(selection[0])
        except ValueError:
            return None

    def _refresh_skip_button(self, _event: tk.Event | None = None) -> None:
        """Chỉ cho bỏ qua tài khoản đang chạy hoặc đang chờ xác minh; đã xong thì vô nghĩa."""
        line = self._selected_line()
        active = (
            self.running
            and line is not None
            and line in self.account_tokens
            and self.statuses.get(line) in {"running", WAITING_MANUAL_STATUS}
        )
        self.skip_button.configure(state="normal" if active else "disabled")

    def _skip_selected(self) -> None:
        line = self._selected_line()
        token = self.account_tokens.get(line) if line is not None else None
        if token is None:
            return
        token.cancel()
        self.skip_button.configure(state="disabled")
        self.summary.configure(text=f"Đang bỏ qua dòng {line}…")

    def _on_close(self) -> None:
        if self.worker and self.worker.is_alive():
            if not messagebox.askokcancel("Automation đang chạy", "Đóng sau khi các Chrome được dọn dẹp?"):
                return
            self._persist_app_config()
            self.closing = True
            if not self.worker.is_alive():
                self.root.destroy()
                return
            self._stop()
            self.root.withdraw()
            self.root.after(CLEANUP_TIMEOUT_MS, self._force_close)
            return
        self._persist_app_config()
        self.root.destroy()

    def _force_close(self) -> None:
        """Thoát cưỡng bức khi Playwright treo. Worker chạy non-daemon nên nếu chỉ destroy
        cửa sổ, tiến trình vẫn sống mãi và người dùng thấy một process ma."""
        if not self.closing or not (self.worker and self.worker.is_alive()):
            return
        os._exit(1)


def main() -> None:
    root = tk.Tk()
    Application(root)
    root.mainloop()


if __name__ == "__main__":
    main()
