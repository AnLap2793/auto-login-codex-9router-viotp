import queue
import threading
import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from .config import DEFAULT_NETWORK
from .integrations.viotp import OPENAI_SERVICE, ViotpError, get_balance, get_networks
from .ui_models import ViotpConfig


class ViotpConfigOverlay(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        current: ViotpConfig | None,
        on_save: Callable[[ViotpConfig], None],
        on_close: Callable[[], None],
    ) -> None:
        super().__init__(parent, style="Modal.TFrame", padding=24)
        self.on_save = on_save
        self.on_close = on_close
        self.events: queue.Queue[tuple] = queue.Queue()
        self.checking = False
        self.verified: ViotpConfig | None = current

        self.place(relx=0.5, rely=0.5, anchor="center", width=540)
        self.lift()
        self._build(current)
        root = self.winfo_toplevel()
        self._escape_binding = root.bind("<Escape>", self._escape, add="+")
        self.grab_set()
        self.token.focus_set()
        self.after(100, self._drain_events)

    def _build(self, current: ViotpConfig | None) -> None:
        card = self

        header = ttk.Frame(card, style="Modal.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="Cấu hình VIOTP", style="ModalTitle.TLabel").pack(side="left")
        ttk.Button(header, text="×", width=3, command=self.close).pack(side="right")
        ttk.Label(
            card,
            text="Token được lưu bằng bảo vệ dữ liệu của tài khoản Windows.",
            style="ModalHint.TLabel",
        ).pack(anchor="w", pady=(3, 18))

        ttk.Label(card, text="API token", style="Modal.TLabel").pack(anchor="w")
        token_row = ttk.Frame(card, style="Modal.TFrame")
        token_row.pack(fill="x", pady=(6, 12))
        self.token = ttk.Entry(token_row, show="•", font=("Segoe UI", 11))
        self.token.pack(side="left", fill="x", expand=True, ipady=6)
        if current:
            self.token.insert(0, current.token)
        self.token.bind("<KeyRelease>", self._token_changed)
        self.toggle_button = ttk.Button(token_row, text="Hiện", width=7, command=self._toggle_token)
        self.toggle_button.pack(side="left", padx=(8, 0))

        check_row = ttk.Frame(card, style="Modal.TFrame")
        check_row.pack(fill="x", pady=(0, 12))
        self.check_button = ttk.Button(check_row, text="Kiểm tra kết nối", command=self._check)
        self.check_button.pack(side="left")
        self.status = ttk.Label(
            check_row,
            text=current.summary if current else "VIOTP: Chưa kiểm tra",
            style="ModalHint.TLabel",
        )
        self.status.pack(side="left", padx=12)

        ttk.Label(card, text="Nhà mạng", style="Modal.TLabel").pack(anchor="w")
        current_network = current.network if current else DEFAULT_NETWORK
        networks = (DEFAULT_NETWORK,) if current_network == DEFAULT_NETWORK else (DEFAULT_NETWORK, current_network)
        self.network = ttk.Combobox(card, state="readonly", values=networks)
        self.network.pack(fill="x", pady=(6, 12), ipady=4)
        self.network.set(current_network)

        service = (
            f"{OPENAI_SERVICE.name} · ID {OPENAI_SERVICE.id} · "
            f"{OPENAI_SERVICE.price:,.0f}đ"
        ).replace(",", ".")
        ttk.Label(card, text="Dịch vụ", style="Modal.TLabel").pack(anchor="w")
        ttk.Label(card, text=service, style="ModalHint.TLabel").pack(anchor="w", pady=(5, 18))

        actions = ttk.Frame(card, style="Modal.TFrame")
        actions.pack(fill="x", side="bottom")
        ttk.Button(actions, text="Hủy", command=self.close).pack(side="right")
        self.save_button = ttk.Button(actions, text="Lưu cấu hình", command=self._save)
        self.save_button.pack(side="right", padx=(0, 8))
        self.save_button.configure(state="normal" if current else "disabled")

    def _escape(self, _event: tk.Event | None = None) -> str:
        self.close()
        return "break"

    def close(self) -> None:
        if not self.winfo_exists():
            return
        self.grab_release()
        root = self.winfo_toplevel()
        if self._escape_binding:
            root.unbind("<Escape>", self._escape_binding)
        self.destroy()
        self.on_close()

    def _toggle_token(self) -> None:
        visible = self.token.cget("show") == ""
        self.token.configure(show="•" if visible else "")
        self.toggle_button.configure(text="Hiện" if visible else "Ẩn")

    def _token_changed(self, _event: tk.Event | None = None) -> None:
        if self.checking:
            return
        token = self.token.get().strip()
        self.network.configure(values=(DEFAULT_NETWORK,))
        self.network.set(DEFAULT_NETWORK)
        if not token:
            self.verified = ViotpConfig("", DEFAULT_NETWORK, None)
            self.status.configure(text="VIOTP: Sẽ xóa cấu hình")
            self.save_button.configure(state="normal")
            return
        self.verified = None
        self.status.configure(text="VIOTP: Chưa kiểm tra")
        self.save_button.configure(state="disabled")

    def _check(self) -> None:
        token = self.token.get().strip()
        if not token:
            messagebox.showwarning("Thiếu token", "Nhập token VIOTP trước khi kiểm tra.", parent=self)
            return
        self.checking = True
        self.check_button.configure(state="disabled")
        self.save_button.configure(state="disabled")
        self.status.configure(text="VIOTP: Đang kiểm tra…")
        threading.Thread(target=self._run_check, args=(token,), daemon=True).start()

    def _run_check(self, token: str) -> None:
        try:
            balance = get_balance(token)
            networks = tuple(network.name for network in get_networks(token))
            self.events.put(("ok", token, balance, networks))
        except ViotpError as error:
            self.events.put(("error", token, str(error)))

    def _drain_events(self) -> None:
        if not self.winfo_exists():
            return
        try:
            event = self.events.get_nowait()
        except queue.Empty:
            self.after(100, self._drain_events)
            return
        self.checking = False
        self.check_button.configure(state="normal")
        if self.token.get().strip() != event[1]:
            self._token_changed()
        elif event[0] == "error":
            self._token_changed()
            messagebox.showerror("Không thể kết nối VIOTP", event[2], parent=self)
        else:
            values = (DEFAULT_NETWORK, *event[3])
            self.network.configure(values=values)
            self.network.set(DEFAULT_NETWORK)
            self.verified = ViotpConfig(event[1], DEFAULT_NETWORK, event[2])
            self.status.configure(text=self.verified.summary)
            self.save_button.configure(state="normal")
        self.after(100, self._drain_events)

    def _save(self) -> None:
        token = self.token.get().strip()
        if not self.verified or token != self.verified.token:
            return
        config = ViotpConfig(token, self.network.get(), self.verified.balance)
        self.on_save(config)
        self.close()
