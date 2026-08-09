# Youtube comment downloader

#!/usr/bin/env python3
"""
YouTube Comment Downloader - GUI (Tkinter)
Mengunduh komentar dari sebuah video YouTube, dengan pilihan jumlah maksimum
komentar (atau semua), progress bar, dan ekspor ke CSV / JSON / TXT.

Dependensi:
    pip install youtube-comment-downloader
"""

import csv
import json
import os
import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

try:
    from youtube_comment_downloader import (
        SORT_BY_POPULAR,
        SORT_BY_RECENT,
        YoutubeCommentDownloader,
    )
except ImportError:
    YoutubeCommentDownloader = None


# ----------------------------------------------------------------------
# Tema warna (dark theme)
# ----------------------------------------------------------------------
BG = "#1e1e1e"
PANEL = "#252526"
FG = "#e8e8e8"
FG_MUTED = "#9a9a9a"
ACCENT = "#ff3b3b"       # merah ala YouTube
ACCENT_HOVER = "#ff5c5c"
ENTRY_BG = "#2d2d30"
BORDER = "#3c3c3c"
OK_COLOR = "#4caf50"
ERR_COLOR = "#f14c4c"
FONT_NORMAL = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 15, "bold")
FONT_MONO = ("Consolas", 9)


def add_context_menu(widget):
    """Klik kanan -> cut/copy/paste, dipakai di seluruh app ini."""
    menu = tk.Menu(widget, tearoff=0, bg=PANEL, fg=FG,
                    activebackground=ACCENT, activeforeground="white")
    menu.add_command(label="Cut", command=lambda: widget.event_generate("<<Cut>>"))
    menu.add_command(label="Copy", command=lambda: widget.event_generate("<<Copy>>"))
    menu.add_command(label="Paste", command=lambda: widget.event_generate("<<Paste>>"))
    menu.add_separator()
    menu.add_command(label="Select All", command=lambda: widget.event_generate("<<SelectAll>>"))

    def show(event):
        menu.tk_popup(event.x_root, event.y_root)

    widget.bind("<Button-3>", show)
    return menu


class YTCommentDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Comment Downloader")
        self.root.geometry("720x680")
        self.root.minsize(660, 600)
        self.root.configure(bg=BG)

        self.msg_queue = queue.Queue()
        self.cancel_event = threading.Event()
        self.worker_thread = None
        self.output_dir = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads"))

        self._build_style()
        self._build_ui()
        self._poll_queue()

    # ------------------------------------------------------------------
    # Style
    # ------------------------------------------------------------------
    def _build_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)

        style.configure("TLabel", background=BG, foreground=FG, font=FONT_NORMAL)
        style.configure("Panel.TLabel", background=PANEL, foreground=FG, font=FONT_NORMAL)
        style.configure("Muted.TLabel", background=PANEL, foreground=FG_MUTED, font=FONT_NORMAL)
        style.configure("Title.TLabel", background=BG, foreground=FG, font=FONT_TITLE)

        style.configure("TRadiobutton", background=PANEL, foreground=FG, font=FONT_NORMAL)
        style.map("TRadiobutton",
                  background=[("active", PANEL)],
                  foreground=[("active", ACCENT)])

        style.configure("TCheckbutton", background=PANEL, foreground=FG, font=FONT_NORMAL)
        style.map("TCheckbutton", background=[("active", PANEL)])

        style.configure("TEntry", fieldbackground=ENTRY_BG, foreground=FG,
                         insertcolor=FG, bordercolor=BORDER, lightcolor=BORDER,
                         darkcolor=BORDER, borderwidth=1)
        style.map("TEntry", bordercolor=[("focus", ACCENT)])

        style.configure("Accent.TButton", background=ACCENT, foreground="white",
                         font=FONT_BOLD, borderwidth=0, focuscolor=ACCENT, padding=8)
        style.map("Accent.TButton", background=[("active", ACCENT_HOVER), ("disabled", "#7a2b2b")])

        style.configure("Secondary.TButton", background=ENTRY_BG, foreground=FG,
                         font=FONT_NORMAL, borderwidth=1, padding=8)
        style.map("Secondary.TButton", background=[("active", BORDER)])

        style.configure("TProgressbar", troughcolor=ENTRY_BG, background=ACCENT,
                         bordercolor=ENTRY_BG, lightcolor=ACCENT, darkcolor=ACCENT)

    # ------------------------------------------------------------------
    # UI layout
    # ------------------------------------------------------------------
    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 14))
        ttk.Label(header, text="▶ YouTube Comment Downloader", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="Unduh komentar video YouTube ke CSV / JSON / TXT",
                  foreground=FG_MUTED, background=BG, font=FONT_NORMAL).pack(anchor="w")

        # ---------------- URL ----------------
        url_panel = self._panel(outer, "Link Video")
        url_panel.pack(fill="x", pady=(0, 12))
        row = ttk.Frame(url_panel, style="Panel.TFrame")
        row.pack(fill="x", padx=12, pady=(0, 12))
        self.url_entry = ttk.Entry(row, font=FONT_NORMAL)
        self.url_entry.pack(fill="x", ipady=5)
        self.url_entry.insert(0, "https://www.youtube.com/watch?v=")
        add_context_menu(self.url_entry)

        # ---------------- Options ----------------
        opt_panel = self._panel(outer, "Opsi Pengunduhan")
        opt_panel.pack(fill="x", pady=(0, 12))
        opt_body = ttk.Frame(opt_panel, style="Panel.TFrame")
        opt_body.pack(fill="x", padx=12, pady=(0, 12))

        # Sort by
        sort_row = ttk.Frame(opt_body, style="Panel.TFrame")
        sort_row.pack(fill="x", pady=(0, 8))
        ttk.Label(sort_row, text="Urutkan:", style="Panel.TLabel").pack(side="left", padx=(0, 10))
        self.sort_var = tk.StringVar(value="popular")
        ttk.Radiobutton(sort_row, text="Populer", variable=self.sort_var, value="popular").pack(side="left", padx=(0, 12))
        ttk.Radiobutton(sort_row, text="Terbaru", variable=self.sort_var, value="recent").pack(side="left")

        # Max comments
        max_row = ttk.Frame(opt_body, style="Panel.TFrame")
        max_row.pack(fill="x", pady=(0, 8))
        self.all_var = tk.BooleanVar(value=False)
        ttk.Label(max_row, text="Jumlah maksimum:", style="Panel.TLabel").pack(side="left", padx=(0, 10))
        self.max_entry = ttk.Entry(max_row, width=10, font=FONT_NORMAL)
        self.max_entry.insert(0, "100")
        self.max_entry.pack(side="left", ipady=3)
        add_context_menu(self.max_entry)
        self.all_check = ttk.Checkbutton(max_row, text="Ambil SEMUA komentar",
                                          variable=self.all_var, command=self._toggle_all)
        self.all_check.pack(side="left", padx=(14, 0))

        # Output format
        fmt_row = ttk.Frame(opt_body, style="Panel.TFrame")
        fmt_row.pack(fill="x", pady=(0, 8))
        ttk.Label(fmt_row, text="Format simpan:", style="Panel.TLabel").pack(side="left", padx=(0, 10))
        self.format_var = tk.StringVar(value="csv")
        for val, label in [("csv", "CSV"), ("json", "JSON"), ("txt", "TXT")]:
            ttk.Radiobutton(fmt_row, text=label, variable=self.format_var, value=val).pack(side="left", padx=(0, 12))

        # Output folder
        folder_row = ttk.Frame(opt_body, style="Panel.TFrame")
        folder_row.pack(fill="x")
        ttk.Label(folder_row, text="Simpan ke:", style="Panel.TLabel").pack(side="left", padx=(0, 10))
        self.folder_entry = ttk.Entry(folder_row, textvariable=self.output_dir, font=FONT_NORMAL)
        self.folder_entry.pack(side="left", fill="x", expand=True, ipady=3)
        add_context_menu(self.folder_entry)
        ttk.Button(folder_row, text="Pilih...", style="Secondary.TButton",
                   command=self._choose_folder).pack(side="left", padx=(8, 0))

        # ---------------- Buttons ----------------
        btn_row = ttk.Frame(outer)
        btn_row.pack(fill="x", pady=(4, 12))
        self.start_btn = ttk.Button(btn_row, text="⬇  Mulai Unduh", style="Accent.TButton",
                                     command=self._start_download)
        self.start_btn.pack(side="left")
        self.cancel_btn = ttk.Button(btn_row, text="Batalkan", style="Secondary.TButton",
                                      command=self._cancel_download, state="disabled")
        self.cancel_btn.pack(side="left", padx=(8, 0))

        # ---------------- Progress ----------------
        prog_panel = self._panel(outer, "Progress")
        prog_panel.pack(fill="x", pady=(0, 12))
        prog_body = ttk.Frame(prog_panel, style="Panel.TFrame")
        prog_body.pack(fill="x", padx=12, pady=(0, 12))

        self.progress = ttk.Progressbar(prog_body, mode="determinate", style="TProgressbar")
        self.progress.pack(fill="x", ipady=3)

        status_row = ttk.Frame(prog_body, style="Panel.TFrame")
        status_row.pack(fill="x", pady=(6, 0))
        self.status_label = ttk.Label(status_row, text="Siap.", style="Panel.TLabel")
        self.status_label.pack(side="left")
        self.count_label = ttk.Label(status_row, text="", style="Muted.TLabel")
        self.count_label.pack(side="right")

        # ---------------- Log ----------------
        log_panel = self._panel(outer, "Log")
        log_panel.pack(fill="both", expand=True)
        log_body = ttk.Frame(log_panel, style="Panel.TFrame")
        log_body.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.log_text = tk.Text(log_body, height=8, bg="#111111", fg="#c8c8c8",
                                 insertbackground=FG, font=FONT_MONO, wrap="word",
                                 relief="flat", borderwidth=0)
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(log_body, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=scrollbar.set, state="disabled")
        add_context_menu(self.log_text)

    def _panel(self, parent, title):
        frame = ttk.Frame(parent, style="Panel.TFrame")
        ttk.Label(frame, text=title, style="Panel.TLabel", font=FONT_BOLD).pack(
            anchor="w", padx=12, pady=(10, 6))
        return frame

    # ------------------------------------------------------------------
    # UI actions
    # ------------------------------------------------------------------
    def _toggle_all(self):
        if self.all_var.get():
            self.max_entry.configure(state="disabled")
        else:
            self.max_entry.configure(state="normal")

    def _choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.output_dir.get() or os.getcwd())
        if folder:
            self.output_dir.set(folder)

    def _log(self, text, tag=None):
        self.log_text.configure(state="normal")
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{stamp}] {text}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _set_running_state(self, running):
        self.start_btn.configure(state="disabled" if running else "normal")
        self.cancel_btn.configure(state="normal" if running else "disabled")
        self.url_entry.configure(state="disabled" if running else "normal")
        self.max_entry.configure(state="disabled" if (running or self.all_var.get()) else "normal")
        self.all_check.configure(state="disabled" if running else "normal")

    # ------------------------------------------------------------------
    # Download flow
    # ------------------------------------------------------------------
    def _start_download(self):
        if YoutubeCommentDownloader is None:
            messagebox.showerror(
                "Modul hilang",
                "Package 'youtube-comment-downloader' belum terpasang.\n\n"
                "Jalankan: pip install youtube-comment-downloader"
            )
            return

        url = self.url_entry.get().strip()
        if not url or "youtube.com" not in url and "youtu.be" not in url:
            messagebox.showwarning("URL tidak valid", "Masukkan link video YouTube yang valid.")
            return

        want_all = self.all_var.get()
        max_count = None
        if not want_all:
            raw = self.max_entry.get().strip()
            if not raw.isdigit() or int(raw) <= 0:
                messagebox.showwarning("Jumlah tidak valid", "Masukkan angka maksimum komentar yang valid (>0).")
                return
            max_count = int(raw)

        out_dir = self.output_dir.get().strip()
        if not out_dir:
            messagebox.showwarning("Folder belum dipilih", "Pilih folder tujuan untuk menyimpan hasil.")
            return
        os.makedirs(out_dir, exist_ok=True)

        self.cancel_event.clear()
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

        if want_all:
            self.progress.configure(mode="indeterminate")
            self.progress.start(12)
        else:
            self.progress.configure(mode="determinate", maximum=max_count, value=0)

        self.status_label.configure(text="Mengunduh komentar...")
        self.count_label.configure(text="0 komentar")
        self._set_running_state(True)
        self._log(f"Mulai mengunduh dari: {url}")
        self._log(f"Mode: {'Semua komentar' if want_all else f'Maksimum {max_count} komentar'}, "
                   f"urutan: {self.sort_var.get()}, format: {self.format_var.get().upper()}")

        self.worker_thread = threading.Thread(
            target=self._worker,
            args=(url, max_count, out_dir, self.format_var.get(), self.sort_var.get()),
            daemon=True,
        )
        self.worker_thread.start()

    def _cancel_download(self):
        self.cancel_event.set()
        self.status_label.configure(text="Membatalkan...")
        self._log("Permintaan pembatalan dikirim, menunggu proses berhenti...")

    def _worker(self, url, max_count, out_dir, fmt, sort_key):
        downloader = YoutubeCommentDownloader()
        sort_by = SORT_BY_POPULAR if sort_key == "popular" else SORT_BY_RECENT
        comments = []
        error = None
        cancelled = False

        try:
            generator = downloader.get_comments_from_url(url, sort_by=sort_by)
            if generator is None:
                error = "Tidak dapat mengambil komentar. Video mungkin tidak ditemukan atau komentar dimatikan."
            else:
                for i, comment in enumerate(generator, start=1):
                    if self.cancel_event.is_set():
                        cancelled = True
                        break
                    comments.append(comment)
                    self.msg_queue.put(("progress", i, max_count))
                    if max_count is not None and i >= max_count:
                        break
        except Exception as exc:  # noqa: BLE001
            error = str(exc)

        if error:
            self.msg_queue.put(("error", error))
            return

        if cancelled and not comments:
            self.msg_queue.put(("cancelled", 0))
            return

        try:
            filepath = self._save_comments(comments, out_dir, fmt, url)
        except Exception as exc:  # noqa: BLE001
            self.msg_queue.put(("error", f"Gagal menyimpan file: {exc}"))
            return

        if cancelled:
            self.msg_queue.put(("cancelled", len(comments), filepath))
        else:
            self.msg_queue.put(("done", len(comments), filepath))

    def _save_comments(self, comments, out_dir, fmt, url):
        video_id = self._extract_video_id(url)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"comments_{video_id or 'video'}_{stamp}"
        filepath = os.path.join(out_dir, f"{base_name}.{fmt}")

        if fmt == "csv":
            with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["author", "text", "time", "votes", "replies", "is_reply", "channel", "cid"])
                for c in comments:
                    writer.writerow([
                        c.get("author", ""), c.get("text", ""), c.get("time", ""),
                        c.get("votes", ""), c.get("replies", ""), c.get("reply", ""),
                        c.get("channel", ""), c.get("cid", ""),
                    ])
        elif fmt == "json":
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(comments, f, ensure_ascii=False, indent=2)
        else:  # txt
            with open(filepath, "w", encoding="utf-8") as f:
                for c in comments:
                    f.write(f"{c.get('author', '')} ({c.get('time', '')}) - {c.get('votes', '0')} suka\n")
                    f.write(f"{c.get('text', '')}\n")
                    f.write("-" * 60 + "\n")

        return filepath

    @staticmethod
    def _extract_video_id(url):
        import re
        match = re.search(r"(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{6,})", url)
        return match.group(1) if match else None

    # ------------------------------------------------------------------
    # Queue polling -> update UI thread-safely
    # ------------------------------------------------------------------
    def _poll_queue(self):
        try:
            while True:
                item = self.msg_queue.get_nowait()
                kind = item[0]

                if kind == "progress":
                    _, count, max_count = item
                    self.count_label.configure(text=f"{count} komentar")
                    if max_count is not None:
                        self.progress.configure(value=count)
                    if count % 20 == 0 or (max_count and count == max_count):
                        self._log(f"Terkumpul {count} komentar...")

                elif kind == "done":
                    _, count, filepath = item
                    self.progress.stop()
                    self.progress.configure(mode="determinate", value=self.progress["maximum"] or 1)
                    self.status_label.configure(text="Selesai ✔", foreground=OK_COLOR)
                    self.count_label.configure(text=f"{count} komentar")
                    self._log(f"Selesai! {count} komentar disimpan ke:\n{filepath}")
                    self._set_running_state(False)
                    messagebox.showinfo("Selesai", f"{count} komentar berhasil disimpan ke:\n{filepath}")

                elif kind == "cancelled":
                    self.progress.stop()
                    self.status_label.configure(text="Dibatalkan", foreground=FG_MUTED)
                    self._set_running_state(False)
                    if len(item) == 3:
                        _, count, filepath = item
                        self._log(f"Dibatalkan. {count} komentar yang sempat terkumpul disimpan ke:\n{filepath}")
                    else:
                        self._log("Dibatalkan sebelum ada komentar tersimpan.")

                elif kind == "error":
                    _, message = item
                    self.progress.stop()
                    self.progress.configure(mode="determinate", value=0)
                    self.status_label.configure(text="Gagal ✖", foreground=ERR_COLOR)
                    self._log(f"ERROR: {message}")
                    self._set_running_state(False)
                    messagebox.showerror("Terjadi kesalahan", message)

        except queue.Empty:
            pass

        self.root.after(100, self._poll_queue)


def main():
    root = tk.Tk()
    app = YTCommentDownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
