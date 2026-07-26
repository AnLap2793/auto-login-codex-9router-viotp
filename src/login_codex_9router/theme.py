"""Bảng màu và style ttk dùng chung cho cửa sổ chính và modal VIOTP."""

from tkinter import ttk

BACKGROUND = "#f4f1ea"
SURFACE = "#fffdf8"
TEXT = "#20251f"
MUTED_TEXT = "#60675e"
ACCENT = "#245c45"
ACCENT_ACTIVE = "#194b37"
ACCENT_DISABLED = "#9aa69f"


def configure_style() -> None:
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TFrame", background=BACKGROUND)
    style.configure("TLabel", background=BACKGROUND, foreground=TEXT, font=("Segoe UI", 10))
    style.configure("Title.TLabel", font=("Segoe UI Semibold", 20))
    style.configure("Section.TLabel", font=("Segoe UI Semibold", 11))
    style.configure("Hint.TLabel", foreground=MUTED_TEXT)
    style.configure("Accent.TButton", background=ACCENT, foreground="white", padding=(18, 10))
    style.map("Accent.TButton", background=[("active", ACCENT_ACTIVE), ("disabled", ACCENT_DISABLED)])
    style.configure("TButton", padding=(14, 9))
    style.configure("Treeview", rowheight=28, background=SURFACE, fieldbackground=SURFACE)
    style.configure("Treeview.Heading", font=("Segoe UI Semibold", 9), padding=6)
    style.configure("Overlay.TFrame", background="#d4d1ca")
    style.configure("Modal.TFrame", background=SURFACE, relief="solid", borderwidth=1)
    style.configure("Modal.TLabel", background=SURFACE, foreground=TEXT, font=("Segoe UI", 10))
    style.configure("ModalTitle.TLabel", background=SURFACE, foreground=TEXT, font=("Segoe UI Semibold", 18))
    style.configure("ModalHint.TLabel", background=SURFACE, foreground=MUTED_TEXT)
