#!/usr/bin/env python3
"""
QR Code File Sharer – GUI
"""

import socket
import threading
import tkinter as tk
import ipaddress
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from tkinter import filedialog, messagebox
from urllib.parse import quote
from urllib.request import urlopen
from datetime import datetime

import customtkinter as ctk
import qrcode
from PIL import Image, ImageDraw
import pyperclip

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG          = "#101116"
SIDEBAR     = "#151923"
CONTENT     = "#0f1117"
CARD        = "#202638"
CARD_HOVER  = "#283149"
BORDER      = "#30384e"
BORDER_LIT  = "#5c78b8"
ACCENT      = "#6ea8fe"
ACCENT_DIM  = "#4a7ed8"
SECONDARY   = "#2d3650"
SECONDARY_HOVER = "#394767"
STOP_BG     = "#d84f5f"
STOP_HOVER  = "#b83d4c"
SUCCESS     = "#3ecf8e"
DANGER      = "#f06060"
WARNING     = "#f5a623"
TEXT_HI     = "#ffffff"
TEXT_MED    = "#e6ecf8"
TEXT_LO     = "#b8c5df"
FONT_MONO   = "Consolas"
APP_NAME    = "QR File Sharer"
APP_VER     = "1.0.3"
WIN_W, WIN_H = 1120, 820
SIDEBAR_W    = 420

def resource_path(name: str) -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / name
    return Path(__file__).resolve().parent / name

def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()

def get_public_ip() -> str:
    for endpoint in ("https://api.ipify.org", "https://ifconfig.me/ip"):
        try:
            with urlopen(endpoint, timeout=8) as resp:
                ip = resp.read().decode("utf-8", errors="replace").strip()
            ipaddress.ip_address(ip)
            return ip
        except Exception:
            pass
    raise RuntimeError("Öffentliche IP konnte nicht ermittelt werden.")

def fmt_size(b: int) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"

def ext_icon(ext: str) -> str:
    return {
        ".apk": "📱", ".exe": "⚙️",  ".msi": "⚙️",
        ".pdf": "📕", ".zip": "🗜️",  ".rar": "🗜️", ".7z": "🗜️",
        ".mp4": "🎬", ".mov": "🎬",  ".avi": "🎬",
        ".mp3": "🎵", ".wav": "🎵",  ".flac": "🎵",
        ".jpg": "🖼️", ".jpeg": "🖼️", ".png": "🖼️", ".gif": "🖼️",
        ".py":  "🐍", ".js":  "📜",  ".html": "🌐", ".csv": "📊",
    }.get(ext, "📄")

def make_qr_pil(url: str, px: int = 260) -> Image.Image:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10, border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0d0f14", back_color="#f5f6fa").convert("RGBA")
    return img.resize((px, px), Image.LANCZOS)

def make_placeholder_pil(px: int = 260) -> Image.Image:
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    r = 18
    color = (58, 66, 96, 200)
    draw.rounded_rectangle([0, 0, px - 1, px - 1], radius=r, outline=color, width=2)
    sq = 36
    pad = 20
    corners = [(pad, pad), (px - pad - sq, pad), (pad, px - pad - sq)]
    for cx, cy in corners:
        draw.rounded_rectangle([cx, cy, cx + sq, cy + sq], radius=5, outline=color, width=2)
        draw.rounded_rectangle([cx + 8, cy + 8, cx + sq - 8, cy + sq - 8], radius=2, fill=color)
    dot_color = (58, 66, 96, 100)
    for row in range(7):
        for col in range(7):
            x = 115 + col * 10
            y = 115 + row * 10
            draw.ellipse([x, y, x + 3, y + 3], fill=dot_color)
    return img

class FileHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, log_cb=None, **kwargs):
        self._log_cb = log_cb
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self._log_cb:
            ts = datetime.now().strftime("%H:%M:%S")
            self._log_cb(f"[{ts}]  {self.client_address[0]}  ->  GET {self.path}")
        return super().do_GET()

class StatusBadge(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color=CARD, corner_radius=20,
                         border_width=1, border_color=BORDER, height=34, **kw)
        self._dot = ctk.CTkLabel(self, text="●", font=ctk.CTkFont(size=11),
                                  text_color=TEXT_LO, fg_color="transparent")
        self._dot.pack(side="left", padx=(12, 5))
        self._lbl = ctk.CTkLabel(self, text="Offline", font=ctk.CTkFont(size=13, weight="bold"),
                                  text_color=TEXT_MED, fg_color="transparent")
        self._lbl.pack(side="left", padx=(0, 14))

    def set(self, text: str, color: str):
        self._dot.configure(text_color=color)
        self._lbl.configure(text=text, text_color=color)

class SectionLabel(ctk.CTkLabel):
    def __init__(self, parent, text: str, **kw):
        kw.setdefault("font", ctk.CTkFont(size=12, weight="bold"))
        kw.setdefault("text_color", TEXT_LO)
        kw.setdefault("anchor", "w")
        super().__init__(parent, text=text.upper(), **kw)

class Divider(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, height=1, fg_color=BORDER, **kw)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VER}")
        self.geometry(f"{WIN_W}x{WIN_H}")
        self.minsize(980, 720)
        self.configure(fg_color=BG)
        self._set_window_icon()

        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{WIN_W}x{WIN_H}+{(sw - WIN_W)//2}+{(sh - WIN_H)//2}")

        self.server      = None
        self.srv_thread  = None
        self.cur_file: Path | None = None
        self._qr_img_ref = None
        self._uploading = False
        self._log_lines: list[str] = []
        self._log_window = None
        self._log_popup_text = None

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _set_window_icon(self):
        icon_path = resource_path("qr_file_sharer_icon.ico")
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

    def _build(self):
        self.grid_columnconfigure(0, weight=0, minsize=SIDEBAR_W)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_content()

    def _build_sidebar(self):
        self._sb = ctk.CTkFrame(self, fg_color=SIDEBAR, corner_radius=0)
        self._sb.grid(row=0, column=0, sticky="nsew")
        self._sb.grid_rowconfigure(4, weight=1)
        self._sb.grid_columnconfigure(0, weight=1)
        sb = self._sb

        brand = ctk.CTkFrame(sb, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 0))

        logo_row = ctk.CTkFrame(brand, fg_color="transparent")
        logo_row.pack(fill="x")

        ctk.CTkLabel(logo_row, text="◈", font=ctk.CTkFont(size=23),
                     text_color=ACCENT, fg_color="transparent").pack(side="left", padx=(0, 8))
        ctk.CTkLabel(logo_row, text="QR File Sharer",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=TEXT_HI, fg_color="transparent").pack(side="left")

        ctk.CTkLabel(brand, text="Direkt teilen ohne Cloud-Upload",
                     font=ctk.CTkFont(size=13),
                     text_color=TEXT_LO, anchor="w").pack(fill="x", pady=(2, 0))

        Divider(sb).grid(row=1, column=0, sticky="ew", padx=24, pady=18)

        panel = ctk.CTkFrame(sb, fg_color="transparent")
        panel.grid(row=2, column=0, sticky="ew", padx=24)
        panel.grid_columnconfigure(0, weight=1)

        SectionLabel(panel, "Datei").grid(row=0, column=0, sticky="w", pady=(0, 6))

        self._drop = ctk.CTkFrame(panel, fg_color=CARD, corner_radius=14,
                                   border_width=2, border_color=BORDER,
                                   height=94, cursor="hand2")
        self._drop.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        self._drop.grid_propagate(False)

        drop_inner = ctk.CTkFrame(self._drop, fg_color="transparent")
        drop_inner.place(relx=0.5, rely=0.5, anchor="center")

        self._drop_icon_lbl = ctk.CTkLabel(drop_inner, text="📂",
                                            font=ctk.CTkFont(size=32))
        self._drop_icon_lbl.pack(side="left", padx=(0, 14))

        drop_txt = ctk.CTkFrame(drop_inner, fg_color="transparent")
        drop_txt.pack(side="left")
        self._drop_main_lbl = ctk.CTkLabel(drop_txt, text="Datei auswählen",
                                            font=ctk.CTkFont(size=17, weight="bold"),
                                            text_color=TEXT_MED, anchor="w")
        self._drop_main_lbl.pack(anchor="w")
        ctk.CTkLabel(drop_txt, text="wird direkt von diesem PC geteilt",
                     font=ctk.CTkFont(size=13), text_color=TEXT_LO,
                     anchor="w").pack(anchor="w")

        self._bind_drop_clicks(self._drop)
        self._drop.bind("<Enter>", lambda e: self._drop.configure(border_color=BORDER_LIT, fg_color=CARD_HOVER))
        self._drop.bind("<Leave>", self._drop_leave)

        self._file_card = ctk.CTkFrame(panel, fg_color=CARD, corner_radius=12,
                                        border_width=1, border_color=BORDER)
        self._file_card.grid(row=2, column=0, sticky="ew", pady=(0, 16))

        fc_inner = ctk.CTkFrame(self._file_card, fg_color="transparent")
        fc_inner.pack(fill="x", padx=14, pady=12)

        self._file_icon = ctk.CTkLabel(fc_inner, text="📄", font=ctk.CTkFont(size=30))
        self._file_icon.pack(side="left", padx=(0, 10))

        fc_txt = ctk.CTkFrame(fc_inner, fg_color="transparent")
        fc_txt.pack(side="left", fill="x", expand=True)

        self._file_name = ctk.CTkLabel(fc_txt, text="Keine Datei",
                                        font=ctk.CTkFont(size=15, weight="bold"),
                                        text_color=TEXT_MED, anchor="w", wraplength=260)
        self._file_name.pack(anchor="w")
        self._file_size = ctk.CTkLabel(fc_txt, text="–", font=ctk.CTkFont(size=13),
                                        text_color=TEXT_LO, anchor="w")
        self._file_size.pack(anchor="w")

        # Mode selection
        SectionLabel(panel, "Modus").grid(row=3, column=0, sticky="w", pady=(0, 6))

        mode_var = ctk.StringVar(value="local")

        local_btn = ctk.CTkRadioButton(panel, text="WLAN / lokale IP", variable=mode_var,
                                        value="local", fg_color=ACCENT, border_color=BORDER,
                                        font=ctk.CTkFont(size=14), text_color=TEXT_MED,
                                        command=self._on_mode_change)
        local_btn.grid(row=4, column=0, sticky="w", pady=(0, 4))

        online_btn = ctk.CTkRadioButton(panel, text="Internet / öffentliche IP", variable=mode_var,
                                         value="online", fg_color=ACCENT, border_color=BORDER,
                                         font=ctk.CTkFont(size=14), text_color=TEXT_MED,
                                         command=self._on_mode_change)
        online_btn.grid(row=5, column=0, sticky="w", pady=(0, 6))

        self._mode_hint = ctk.CTkLabel(
            panel,
            text="Für Geräte im selben WLAN.",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_LO,
            anchor="w",
            wraplength=330,
        )
        self._mode_hint.grid(row=6, column=0, sticky="ew", pady=(0, 16))

        self._mode_var = mode_var

        # Port row (only for local mode)
        self._port_row = ctk.CTkFrame(panel, fg_color="transparent")
        self._port_row.grid(row=7, column=0, sticky="ew", pady=(0, 16))
        self._port_row.grid_columnconfigure(1, weight=1)

        SectionLabel(self._port_row, "Port").grid(row=0, column=0, sticky="w", padx=(0, 12))
        self._port_var = ctk.StringVar()
        self._port_entry = ctk.CTkEntry(self._port_row, textvariable=self._port_var,
                     placeholder_text="automatisch",
                     width=150, height=38, corner_radius=8,
                     fg_color=CARD, border_color=BORDER,
                     font=ctk.CTkFont(size=14, family=FONT_MONO),
                     text_color=TEXT_HI)
        self._port_entry.grid(row=0, column=1, sticky="w")

        # Action buttons
        btn_row = ctk.CTkFrame(panel, fg_color="transparent")
        btn_row.grid(row=8, column=0, sticky="ew", pady=(0, 6))
        btn_row.grid_columnconfigure(0, weight=1)
        btn_row.grid_columnconfigure(1, weight=1)

        self._start_btn = ctk.CTkButton(
            btn_row, text="▶  Starten",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=50, corner_radius=12,
            fg_color=ACCENT, hover_color=ACCENT_DIM,
            text_color="#ffffff",
            text_color_disabled="#dbe7ff",
            state="disabled", command=self._start_server,
        )
        self._start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self._stop_btn = ctk.CTkButton(
            btn_row, text="■  Stoppen",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=50, corner_radius=12,
            fg_color=SECONDARY, hover_color=SECONDARY_HOVER,
            border_width=1, border_color=BORDER,
            text_color=TEXT_HI,
            text_color_disabled="#aeb8cc",
            state="disabled", command=self._stop_server,
        )
        self._stop_btn.grid(row=0, column=1, sticky="ew")

        self._badge = StatusBadge(panel)
        self._badge.grid(row=9, column=0, sticky="w", pady=(8, 0))

        log_frame = ctk.CTkFrame(sb, fg_color="transparent")
        log_frame.grid(row=4, column=0, sticky="sew", padx=24, pady=(18, 20))
        log_frame.grid_columnconfigure(0, weight=1)

        SectionLabel(log_frame, "Server-Log").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self._open_log_btn = ctk.CTkButton(
            log_frame, text="Server-Log öffnen",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42, corner_radius=10,
            fg_color=SECONDARY, hover_color=SECONDARY_HOVER,
            border_width=1, border_color=BORDER,
            text_color=TEXT_HI, command=self._open_log_window,
        )
        self._open_log_btn.grid(row=1, column=0, sticky="ew")

    def _build_content(self):
        self._sb_content = ctk.CTkFrame(self, fg_color=CONTENT, corner_radius=0)
        self._sb_content.grid(row=0, column=1, sticky="nsew")
        self._sb_content.grid_rowconfigure(0, weight=1)
        self._sb_content.grid_columnconfigure(0, weight=1)
        ct = self._sb_content

        inner = ctk.CTkFrame(ct, fg_color="transparent")
        inner.grid(row=0, column=0, sticky="nsew", padx=32, pady=32)
        inner.grid_rowconfigure(1, weight=1)
        inner.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(inner, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 20))

        ctk.CTkLabel(hdr, text="QR-Code",
                     font=ctk.CTkFont(size=19, weight="bold"),
                     text_color=TEXT_HI, anchor="w").pack(side="left")

        self._scan_hint = ctk.CTkLabel(hdr, text="Mit Handy scannen →",
                                        font=ctk.CTkFont(size=13),
                                        text_color=TEXT_LO, anchor="e")
        self._scan_hint.pack(side="right")

        self._qr_card = ctk.CTkFrame(inner, fg_color=CARD, corner_radius=16,
                                border_width=1, border_color=BORDER)
        self._qr_card.grid(row=1, column=0, sticky="nsew")
        self._qr_card.grid_rowconfigure(0, weight=1)
        self._qr_card.grid_columnconfigure(0, weight=1)
        qr_card = self._qr_card

        self._qr_inner = ctk.CTkFrame(qr_card, fg_color="transparent")
        self._qr_inner.grid(row=0, column=0, sticky="nsew")

        ph_pil = make_placeholder_pil(320)
        self._ph_img = ctk.CTkImage(light_image=ph_pil, dark_image=ph_pil, size=(320, 320))
        self._ph_lbl = ctk.CTkLabel(self._qr_inner, image=self._ph_img, text="")
        self._ph_lbl.pack(pady=(24, 8))
        ctk.CTkLabel(self._qr_inner, text="Starte den Server um den QR-Code zu erzeugen",
                     font=ctk.CTkFont(size=14), text_color=TEXT_LO).pack(pady=(0, 24))

        self._qr_outer = ctk.CTkFrame(qr_card, fg_color="transparent")
        self._qr_outer.grid(row=0, column=0, sticky="nsew")
        self._qr_outer.grid_rowconfigure(0, weight=1)
        self._qr_outer.grid_columnconfigure(0, weight=1)
        self._qr_outer.grid_remove()

        qr_img_frame = ctk.CTkFrame(self._qr_outer, fg_color="#f5f6fa", corner_radius=12)
        qr_img_frame.grid(row=0, column=0, padx=32, pady=24, sticky="")

        self._qr_lbl = ctk.CTkLabel(qr_img_frame, text="")
        self._qr_lbl.pack(padx=16, pady=16)

        url_strip = ctk.CTkFrame(qr_card, fg_color="#0d0f14", corner_radius=0, height=64)
        url_strip.grid(row=1, column=0, sticky="ew")
        url_strip.grid_propagate(False)
        url_strip.grid_columnconfigure(0, weight=1)

        url_inner = ctk.CTkFrame(url_strip, fg_color="transparent")
        url_inner.grid(row=0, column=0, sticky="ew", padx=16, pady=10)
        url_inner.grid_columnconfigure(0, weight=1)

        self._url_var = ctk.StringVar()
        self._url_entry = ctk.CTkEntry(
            url_inner, textvariable=self._url_var,
            state="readonly", height=40, corner_radius=8,
            font=ctk.CTkFont(size=13, family=FONT_MONO),
            fg_color=CARD, border_color=BORDER,
            text_color=TEXT_MED,
            placeholder_text="URL erscheint hier …",
        )
        self._url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self._copy_btn = ctk.CTkButton(
            url_inner, text="📋", width=44, height=40, corner_radius=10,
            fg_color=SECONDARY, hover_color=SECONDARY_HOVER,
            border_width=1, border_color=BORDER,
            text_color=TEXT_HI, command=self._copy_url,
        )
        self._copy_btn.grid(row=0, column=1)

    def _on_mode_change(self):
        mode = self._mode_var.get()
        if mode == "online":
            self._mode_hint.configure(
                text="Keine Datei wird hochgeladen. Der QR nutzt deine öffentliche IP; Portweiterleitung im Router muss passen."
            )
            self._port_entry.configure(placeholder_text="8000 empfohlen")
        else:
            self._mode_hint.configure(text="Für Geräte im selben WLAN.")
            self._port_entry.configure(placeholder_text="automatisch")

    def _bind_drop_clicks(self, widget):
        widget.bind("<Button-1>", self._browse_file, add="+")
        try:
            widget.configure(cursor="hand2")
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._bind_drop_clicks(child)

    def _browse_file(self, event=None):
        if self._uploading:
            return "break"
        path = filedialog.askopenfilename(title="Datei auswählen")
        if path:
            self._set_file(path)
        return "break"

    def _set_file(self, path: str):
        p = Path(path)
        self.cur_file = p
        if self.server or self._url_var.get():
            self._stop_server()

        icon = ext_icon(p.suffix.lower())
        self._file_icon.configure(text=icon)
        self._file_name.configure(text=p.name, text_color=TEXT_HI)
        self._file_size.configure(text=fmt_size(p.stat().st_size))
        self._drop.configure(border_color=SUCCESS)
        self._drop_icon_lbl.configure(text=icon)
        self._drop_main_lbl.configure(text=p.name, text_color=SUCCESS)
        self._start_btn.configure(state="normal")
        self._badge.set("Bereit", WARNING)

    def _drop_leave(self, event=None):
        border = SUCCESS if (self.cur_file and self.server is None and self._drop_main_lbl.cget("text_color") == SUCCESS) \
                         else (SUCCESS if self.cur_file else BORDER)
        self._drop.configure(border_color=border, fg_color=CARD)

    def _copy_url(self):
        url = self._url_var.get()
        if not url:
            return
        try:
            pyperclip.copy(url)
        except Exception:
            self.clipboard_clear()
            self.clipboard_append(url)
        self._copy_btn.configure(text="✓", fg_color=SUCCESS, text_color="#ffffff", border_color=SUCCESS)
        self.after(1800, lambda: self._copy_btn.configure(text="📋", fg_color=SECONDARY,
                                                           text_color=TEXT_HI, border_color=BORDER))

    def _clear_log(self):
        self._log_lines.clear()
        self._refresh_log_popup()
        self._update_log_button()

    def _log_write(self, msg: str):
        self._log_lines.append(msg)
        self._refresh_log_popup()
        self._update_log_button()

    def _log_text(self) -> str:
        return "\n".join(self._log_lines)

    def _update_log_button(self):
        count = len(self._log_lines)
        suffix = f" ({count})" if count else ""
        self._open_log_btn.configure(text=f"Server-Log öffnen{suffix}")

    def _refresh_log_popup(self):
        if not self._log_popup_text:
            return
        self._log_popup_text.configure(state="normal")
        self._log_popup_text.delete("0.0", "end")
        self._log_popup_text.insert("end", self._log_text())
        self._log_popup_text.see("end")
        self._log_popup_text.configure(state="disabled")

    def _open_log_window(self):
        if self._log_window and self._log_window.winfo_exists():
            self._log_window.focus()
            self._log_window.lift()
            self._refresh_log_popup()
            return

        win = ctk.CTkToplevel(self)
        win.title("Server-Log")
        win.geometry("760x460")
        win.minsize(560, 320)
        win.configure(fg_color=BG)
        win.grid_columnconfigure(0, weight=1)
        win.grid_rowconfigure(1, weight=1)
        self._log_window = win

        header = ctk.CTkFrame(win, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text="Server-Log",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=TEXT_HI, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            header, text="kopieren", width=82, height=30,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=SECONDARY, hover_color=SECONDARY_HOVER,
            border_width=1, border_color=BORDER,
            text_color=TEXT_HI, command=self._copy_log,
        ).grid(row=0, column=1, padx=(8, 0))

        ctk.CTkButton(
            header, text="leeren", width=72, height=30,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=SECONDARY, hover_color=SECONDARY_HOVER,
            border_width=1, border_color=BORDER,
            text_color=TEXT_HI, command=self._clear_log,
        ).grid(row=0, column=2, padx=(8, 0))

        self._log_popup_text = ctk.CTkTextbox(
            win,
            font=ctk.CTkFont(size=13, family=FONT_MONO),
            fg_color=CARD, border_color=BORDER, border_width=1,
            corner_radius=8, text_color=TEXT_MED, wrap="word",
        )
        self._log_popup_text.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self._refresh_log_popup()

        def on_close():
            self._log_popup_text = None
            self._log_window = None
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", on_close)

    def _copy_log(self):
        text = self._log_text()
        if not text:
            return
        try:
            pyperclip.copy(text)
        except Exception:
            self.clipboard_clear()
            self.clipboard_append(text)

    def _start_server(self):
        if self._uploading:
            return

        if not self.cur_file or not self.cur_file.exists():
            messagebox.showwarning("Hinweis", "Bitte eine Datei auswählen.")
            return

        mode = self._mode_var.get()
        sdir = self.cur_file.parent
        fname = self.cur_file.name
        fstem = self.cur_file.stem
        port_s = self._port_var.get().strip()

        try:
            port = int(port_s) if port_s else (8000 if mode == "online" else 0)
            if not 0 <= port <= 65535:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ungültiger Port", "Bitte eine Zahl zwischen 0 und 65535 eingeben.")
            return

        factory = lambda *a, **kw: FileHandler(
            *a, directory=str(sdir), log_cb=self._log_write, **kw
        )
        try:
            self.server = HTTPServer(("0.0.0.0", port), factory)
        except OSError as e:
            messagebox.showerror("Port belegt", str(e))
            return

        real_port = self.server.server_port
        if mode == "online":
            self._badge.set("Ermittle öffentliche IP", WARNING)
            self.update()
            try:
                ip = get_public_ip()
            except Exception as e:
                self.server.server_close()
                self.server = None
                messagebox.showerror("IP nicht gefunden", str(e))
                return
            url = f"http://{ip}:{real_port}/{quote(fname)}"
            self._log_write(f"[{datetime.now().strftime('%H:%M:%S')}]  Öffentliche IP {ip}:{real_port}")
            self._log_write("  Hinweis: Router/Firewall müssen diesen Port zu diesem PC weiterleiten.")
        else:
            ip = get_local_ip()
            url = f"http://{ip}:{real_port}/{quote(fname)}"
            self._log_write(f"[{datetime.now().strftime('%H:%M:%S')}]  Lokaler Server auf Port {real_port}")

        self._finish_share(mode, url, sdir, fstem, fname, ip=ip, real_port=real_port)

    def _finish_share(self, mode: str, url: str, sdir: Path, fstem: str, fname: str, ip: str | None = None, real_port: int | None = None):
        self._badge.set("Generiere QR …", WARNING)
        self.update()

        try:
            pil = make_qr_pil(url, px=320)
            tk_img = ctk.CTkImage(light_image=pil, dark_image=pil, size=(320, 320))
            self._qr_lbl.configure(image=tk_img)
            self._qr_lbl.image = tk_img
            self._qr_img_ref = tk_img

            self._qr_inner.grid_remove()
            self._qr_outer.grid()

        except Exception as e:
            messagebox.showerror("QR-Fehler", str(e))
            if self.server:
                self.server.shutdown()
                self.server = None
            return

        self._url_var.set(url)
        if ip is not None and real_port is not None:
            prefix = "WLAN" if mode == "local" else "Internet"
            self._badge.set(f"{prefix}  {ip}:{real_port}", SUCCESS)
        else:
            self._badge.set("Online", SUCCESS)
        self._scan_hint.configure(text="← Jetzt scannen!", text_color=SUCCESS)
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal",
                                  fg_color=STOP_BG, hover_color=STOP_HOVER,
                                  border_color=STOP_BG, text_color="#ffffff")
        self._drop.configure(border_color=SUCCESS)

        self._log_write(f"  URL   {url}")
        self._log_write(f"  Datei {fname}  ({fmt_size(self.cur_file.stat().st_size)})")
        self._log_write("  Warte auf Verbindungen …\n")

        if self.server:
            self.srv_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.srv_thread.start()

    def _stop_server(self):
        if self._uploading:
            return

        if self.server:
            try:
                self.server.shutdown()
            except Exception:
                pass
            self.server = None

        self._qr_outer.grid_remove()
        self._qr_inner.grid()

        self._url_var.set("")
        self._badge.set("Offline", TEXT_LO)
        self._scan_hint.configure(text="Mit Handy scannen →", text_color=TEXT_LO)
        self._start_btn.configure(state="normal" if self.cur_file else "disabled")
        self._stop_btn.configure(state="disabled",
                                  fg_color=SECONDARY, hover_color=SECONDARY_HOVER,
                                  border_color=BORDER, text_color=TEXT_HI)
        self._log_write(f"[{datetime.now().strftime('%H:%M:%S')}]  ⏹  Server gestoppt\n")

    def _on_close(self):
        self._stop_server()
        self.destroy()

if __name__ == "__main__":
    App().mainloop()
