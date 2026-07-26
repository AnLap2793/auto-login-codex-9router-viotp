"""Dựng widget cho cửa sổ chính.

Chỉ tạo và sắp xếp widget. Command và binding do `gui.Application` gắn sau
để phần bố cục không phụ thuộc vào logic chạy automation.
"""

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

from .config import AppConfig
from .theme import SURFACE, TEXT


@dataclass(slots=True)
class MainWindowWidgets:
    host: ttk.Entry
    dashboard_password: ttk.Entry
    browser_mode: tk.StringVar
    visible_mode: ttk.Radiobutton
    headless_mode: ttk.Radiobutton
    accounts: tk.Text
    account_count: ttk.Label
    choose_button: ttk.Button
    clear_button: ttk.Button
    viotp_summary: ttk.Label
    viotp_button: ttk.Button
    start_button: ttk.Button
    stop_button: ttk.Button
    skip_button: ttk.Button
    summary: ttk.Label
    stats_label: ttk.Label
    results: ttk.Treeview


def _build_header(outer: ttk.Frame, viotp_summary_text: str) -> tuple[ttk.Label, ttk.Button]:
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
    viotp_summary = ttk.Label(settings, text=viotp_summary_text, style="Hint.TLabel")
    viotp_summary.pack(side="left", padx=(0, 10))
    viotp_button = ttk.Button(settings, text="Cấu hình VIOTP")
    viotp_button.pack(side="left")
    return viotp_summary, viotp_button


def _build_connection(outer: ttk.Frame, config: AppConfig) -> tuple:
    connection = ttk.LabelFrame(outer, text="1. Cấu hình kết nối", padding=16)
    connection.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
    ttk.Label(connection, text="9router HOST").pack(anchor="w")
    host = ttk.Entry(connection, font=("Segoe UI", 11))
    host.insert(0, config.host)
    host.pack(fill="x", pady=(6, 13), ipady=7)
    ttk.Label(connection, text="Mật khẩu dashboard (nếu bật đăng nhập)").pack(anchor="w")
    dashboard_password = ttk.Entry(connection, font=("Segoe UI", 11), show="•")
    dashboard_password.insert(0, config.dashboard_password)
    dashboard_password.pack(fill="x", pady=(6, 14), ipady=7)
    ttk.Label(connection, text="Chế độ Chrome").pack(anchor="w")
    mode = ttk.Frame(connection)
    mode.pack(fill="x", pady=(6, 3))
    browser_mode = tk.StringVar(value=config.browser_mode)
    visible_mode = ttk.Radiobutton(mode, text="Hiển thị", value="visible", variable=browser_mode)
    visible_mode.pack(side="left")
    headless_mode = ttk.Radiobutton(mode, text="Chạy ẩn", value="headless", variable=browser_mode)
    headless_mode.pack(side="left", padx=(12, 0))
    ttk.Label(
        connection,
        text=(
            "Gặp CAPTCHA hoặc xác minh điện thoại: chế độ Hiển thị giữ cửa sổ Chrome mở và chờ "
            "bạn tự xử lý (5 phút), chế độ Chạy ẩn dừng ngay vì không có cửa sổ để thao tác."
        ),
        style="Hint.TLabel",
        wraplength=360,
    ).pack(anchor="w", pady=(5, 0))
    return host, dashboard_password, browser_mode, visible_mode, headless_mode


def _build_accounts(outer: ttk.Frame) -> tuple:
    frame = ttk.LabelFrame(outer, text="2. Danh sách tài khoản", padding=16)
    frame.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(1, weight=1)
    header = ttk.Frame(frame)
    header.grid(row=0, column=0, sticky="ew", pady=(0, 7))
    ttk.Label(header, text="Mỗi dòng: email|password|2fa_secret", style="Hint.TLabel").pack(side="left")
    account_count = ttk.Label(header, text="0 tài khoản")
    account_count.pack(side="right")
    accounts = tk.Text(
        frame,
        height=9,
        wrap="none",
        font=("Consolas", 10),
        bg=SURFACE,
        fg=TEXT,
        insertbackground=TEXT,
        relief="solid",
        borderwidth=1,
        padx=10,
        pady=10,
    )
    accounts.grid(row=1, column=0, sticky="nsew")
    actions = ttk.Frame(frame)
    actions.grid(row=2, column=0, sticky="ew", pady=(9, 0))
    choose_button = ttk.Button(actions, text="Chọn file .txt")
    choose_button.pack(side="left")
    clear_button = ttk.Button(actions, text="Xóa danh sách")
    clear_button.pack(side="left", padx=(8, 0))
    return accounts, account_count, choose_button, clear_button


def _build_results(outer: ttk.Frame, stats_text: str) -> tuple[ttk.Label, ttk.Treeview]:
    header = ttk.Frame(outer)
    header.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 7))
    ttk.Label(header, text="3. Kết quả", style="Section.TLabel").pack(side="left")
    stats_label = ttk.Label(header, text=stats_text, style="Hint.TLabel")
    stats_label.pack(side="right")
    columns = ("line", "account", "status", "detail")
    results = ttk.Treeview(outer, columns=columns, show="headings")
    headings = {"line": "Dòng", "account": "Tài khoản", "status": "Trạng thái", "detail": "Chi tiết"}
    widths = {"line": 55, "account": 250, "status": 150, "detail": 480}
    for column in columns:
        results.heading(column, text=headings[column])
        results.column(column, width=widths[column], minwidth=widths[column], stretch=column == "detail")
    results.grid(row=4, column=0, columnspan=2, sticky="nsew")
    return stats_label, results


def build_main_window(
    root: tk.Tk, config: AppConfig, viotp_summary_text: str, stats_text: str
) -> MainWindowWidgets:
    outer = ttk.Frame(root, padding=22)
    outer.grid(sticky="nsew")
    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)
    outer.columnconfigure(0, weight=4)
    outer.columnconfigure(1, weight=6)
    outer.rowconfigure(4, weight=1)

    viotp_summary, viotp_button = _build_header(outer, viotp_summary_text)
    host, dashboard_password, browser_mode, visible_mode, headless_mode = _build_connection(outer, config)
    accounts, account_count, choose_button, clear_button = _build_accounts(outer)

    actions = ttk.Frame(outer)
    actions.grid(row=2, column=0, columnspan=2, sticky="ew", pady=14)
    start_button = ttk.Button(actions, text="Bắt đầu kết nối", style="Accent.TButton")
    start_button.pack(side="left")
    stop_button = ttk.Button(actions, text="Dừng", state="disabled")
    stop_button.pack(side="left", padx=(8, 0))
    skip_button = ttk.Button(actions, text="Bỏ qua tài khoản đang chọn", state="disabled")
    skip_button.pack(side="left", padx=(8, 0))
    summary = ttk.Label(actions, text="Sẵn sàng", style="Hint.TLabel")
    summary.pack(side="left", padx=14)

    stats_label, results = _build_results(outer, stats_text)

    return MainWindowWidgets(
        host=host,
        dashboard_password=dashboard_password,
        browser_mode=browser_mode,
        visible_mode=visible_mode,
        headless_mode=headless_mode,
        accounts=accounts,
        account_count=account_count,
        choose_button=choose_button,
        clear_button=clear_button,
        viotp_summary=viotp_summary,
        viotp_button=viotp_button,
        start_button=start_button,
        stop_button=stop_button,
        skip_button=skip_button,
        summary=summary,
        stats_label=stats_label,
        results=results,
    )
