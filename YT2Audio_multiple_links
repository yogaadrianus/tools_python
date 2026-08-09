# Downloader from Youtube to OPUS, M4A, WEBM, MP3 with original quality
# Can download multiple links at one time

import os
import sys
import json
import subprocess
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


# ----------------------------------------------------------------------
# Helper: cross-OS default Music folder
# ----------------------------------------------------------------------
def get_default_music_folder():
    r"""
    Returns the default Music folder path.
    Windows -> C:\Users\<user>\Music
    Linux/Mac -> ~/Music
    """
    home = os.path.expanduser("~")
    music = os.path.join(home, "Music")
    if not os.path.isdir(music):
        try:
            os.makedirs(music, exist_ok=True)
        except OSError:
            music = home  # fallback if folder creation fails
    return music


# ----------------------------------------------------------------------
# Right-click context menu for Entry: cut, copy, paste, select all
# ----------------------------------------------------------------------
class EntryContextMenu:
    def __init__(self, widget: tk.Entry):
        self.widget = widget
        self.menu = tk.Menu(widget, tearoff=0)
        self.menu.add_command(label="Cut", command=self.cut)
        self.menu.add_command(label="Copy", command=self.copy)
        self.menu.add_command(label="Paste", command=self.paste)
        self.menu.add_separator()
        self.menu.add_command(label="Select All", command=self.select_all)

        widget.bind("<Button-3>", self.show_menu)
        widget.bind("<Button-2>", self.show_menu)

    def show_menu(self, event):
        try:
            self.widget.focus_set()
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def cut(self):
        try:
            self.widget.event_generate("<<Cut>>")
        except tk.TclError:
            pass

    def copy(self):
        try:
            self.widget.event_generate("<<Copy>>")
        except tk.TclError:
            pass

    def paste(self):
        try:
            self.widget.event_generate("<<Paste>>")
        except tk.TclError:
            pass

    def select_all(self):
        self.widget.select_range(0, tk.END)
        self.widget.icursor(tk.END)


class TextContextMenu:
    """
    Right-click context menu for a Text widget.
    editable=True -> full menu (Cut/Copy/Paste/Select All), for input boxes.
    editable=False -> read-only menu (Copy/Select All), for the log box.
    """
    def __init__(self, widget: tk.Text, editable: bool = False):
        self.widget = widget
        self.editable = editable
        self.menu = tk.Menu(widget, tearoff=0)

        if editable:
            self.menu.add_command(label="Cut", command=self.cut)
            self.menu.add_command(label="Copy", command=self.copy)
            self.menu.add_command(label="Paste", command=self.paste)
            self.menu.add_separator()
            self.menu.add_command(label="Select All", command=self.select_all)
        else:
            self.menu.add_command(label="Copy", command=self.copy)
            self.menu.add_command(label="Select All", command=self.select_all)

        widget.bind("<Button-3>", self.show_menu)
        widget.bind("<Button-2>", self.show_menu)

    def show_menu(self, event):
        try:
            self.widget.focus_set()
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def cut(self):
        try:
            self.widget.event_generate("<<Cut>>")
        except tk.TclError:
            pass

    def copy(self):
        try:
            self.widget.event_generate("<<Copy>>")
        except tk.TclError:
            pass

    def paste(self):
        try:
            self.widget.event_generate("<<Paste>>")
        except tk.TclError:
            pass

    def select_all(self):
        self.widget.tag_add(tk.SEL, "1.0", tk.END)
        self.widget.mark_set(tk.INSERT, tk.END)
        self.widget.see(tk.INSERT)


# ----------------------------------------------------------------------
# Main application
# ----------------------------------------------------------------------
class YTAudioDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Audio Downloader")
        self.root.geometry("700x680")
        self.root.minsize(600, 560)

        self.log_queue = queue.Queue()
        self.is_downloading = False
        self.cancel_requested = False

        # Default format choice: OPUS (Format ID 251)
        self.format_var = tk.StringVar(value="opus")
        self.save_path_var = tk.StringVar(value=get_default_music_folder())

        self._build_ui()
        self._poll_log_queue()

        if yt_dlp is None:
            self._log("[ERROR] The 'yt-dlp' module is not installed.\n"
                      "Run: pip install yt-dlp\n")

    # ------------------------------------------------------------------
    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        main = ttk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True)

        # --- URL input (multi-line, satu link per baris) ---
        url_frame = ttk.LabelFrame(main, text="YouTube Links (satu link per baris, pisahkan dengan Enter)")
        url_frame.pack(fill=tk.BOTH, expand=False, **pad)

        url_inner = ttk.Frame(url_frame)
        url_inner.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.url_text = tk.Text(url_inner, height=10, wrap="none", font=("Segoe UI", 10),
                                 undo=True)
        self.url_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        TextContextMenu(self.url_text, editable=True)

        url_scroll = ttk.Scrollbar(url_inner, orient=tk.VERTICAL, command=self.url_text.yview)
        url_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.url_text.configure(yscrollcommand=url_scroll.set)

        url_btn_row = ttk.Frame(url_frame)
        url_btn_row.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Button(url_btn_row, text="Clear Links", command=self._clear_links).pack(side=tk.LEFT)
        self.link_count_label = ttk.Label(url_btn_row, text="0 link")
        self.link_count_label.pack(side=tk.RIGHT)
        self.url_text.bind("<KeyRelease>", self._update_link_count)

        # --- Format choice ---
        format_frame = ttk.LabelFrame(main, text="Audio Format")
        format_frame.pack(fill=tk.X, **pad)

        ttk.Radiobutton(
            format_frame,
            text="WEBM (Format ID 251) — raw download, absolutely no re-encode",
            variable=self.format_var,
            value="webm"
        ).pack(anchor="w", padx=8, pady=3)

        ttk.Radiobutton(
            format_frame,
            text="OPUS (Format ID 251) — remuxed to .opus, no re-encode [Best Original Quality]",
            variable=self.format_var,
            value="opus"
        ).pack(anchor="w", padx=8, pady=3)

        ttk.Radiobutton(
            format_frame,
            text="M4A / AAC (Format ID 140) — native, no re-encode",
            variable=self.format_var,
            value="m4a"
        ).pack(anchor="w", padx=8, pady=3)

        ttk.Radiobutton(
            format_frame,
            text="MP3 — converted from the original audio, widest compatibility",
            variable=self.format_var,
            value="mp3"
        ).pack(anchor="w", padx=8, pady=3)

        # --- Save location ---
        save_frame = ttk.LabelFrame(main, text="Save Location")
        save_frame.pack(fill=tk.X, **pad)

        save_inner = ttk.Frame(save_frame)
        save_inner.pack(fill=tk.X, padx=8, pady=8)

        self.save_entry = ttk.Entry(save_inner, textvariable=self.save_path_var, font=("Segoe UI", 10))
        self.save_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        EntryContextMenu(self.save_entry)

        ttk.Button(save_inner, text="Browse...", command=self._browse_folder).pack(side=tk.LEFT, padx=(6, 0))

        # --- Action buttons ---
        action_frame = ttk.Frame(main)
        action_frame.pack(fill=tk.X, **pad)

        self.download_btn = ttk.Button(action_frame, text="Download", command=self._start_download)
        self.download_btn.pack(side=tk.LEFT)

        self.cancel_btn = ttk.Button(action_frame, text="Cancel", command=self._cancel_download, state="disabled")
        self.cancel_btn.pack(side=tk.LEFT, padx=(6, 0))

        progress_col = ttk.Frame(action_frame)
        progress_col.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))

        self.overall_label = ttk.Label(progress_col, text="")
        self.overall_label.pack(anchor="w")

        self.progress = ttk.Progressbar(progress_col, mode="determinate", maximum=100)
        self.progress.pack(fill=tk.X)

        # --- Log box ---
        log_frame = ttk.LabelFrame(main, text="Log")
        log_frame.pack(fill=tk.BOTH, expand=True, **pad)

        self.log_text = tk.Text(log_frame, height=10, wrap="word", state="disabled",
                               bg="#1e1e1e", fg="#d4d4d4", insertbackground="white")
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        TextContextMenu(self.log_text, editable=False)

    # ------------------------------------------------------------------
    def _get_urls(self):
        """Ambil semua link dari text box, satu per baris, buang baris kosong/duplikat."""
        raw = self.url_text.get("1.0", tk.END)
        urls = []
        seen = set()
        for line in raw.splitlines():
            url = line.strip()
            if url and url not in seen:
                urls.append(url)
                seen.add(url)
        return urls

    def _update_link_count(self, event=None):
        count = len(self._get_urls())
        self.link_count_label.configure(text=f"{count} link")

    def _clear_links(self):
        if self.is_downloading:
            return
        self.url_text.delete("1.0", tk.END)
        self._update_link_count()

    # ------------------------------------------------------------------
    def _browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.save_path_var.get() or os.path.expanduser("~"))
        if folder:
            self.save_path_var.set(folder)

    # ------------------------------------------------------------------
    def _log(self, msg: str):
        self.log_queue.put(msg)

    def _poll_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.configure(state="normal")
                self.log_text.insert(tk.END, msg)
                self.log_text.see(tk.END)
                self.log_text.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(150, self._poll_log_queue)

    # ------------------------------------------------------------------
    def _start_download(self):
        if self.is_downloading:
            messagebox.showinfo("Info", "Ada download yang sedang berjalan, mohon tunggu.")
            return

        if yt_dlp is None:
            messagebox.showerror("Error", "The yt-dlp module is not installed.\nRun: pip install yt-dlp")
            return

        urls = self._get_urls()
        if not urls:
            messagebox.showwarning("Warning", "Masukkan minimal satu link YouTube (satu link per baris).")
            return

        save_dir = self.save_path_var.get().strip() or get_default_music_folder()
        if not os.path.isdir(save_dir):
            try:
                os.makedirs(save_dir, exist_ok=True)
            except OSError as e:
                messagebox.showerror("Error", f"Could not create the destination folder:\n{e}")
                return

        fmt = self.format_var.get()

        self.is_downloading = True
        self.cancel_requested = False
        self.download_btn.configure(state="disabled", text="Downloading...")
        self.cancel_btn.configure(state="normal")
        self.progress["value"] = 0
        self.overall_label.configure(text=f"Menyiapkan {len(urls)} link...")
        self._log(f"\n=== Memulai batch download ({fmt.upper()}) — {len(urls)} link ===\nSaving to: {save_dir}\n")

        t = threading.Thread(target=self._batch_download_worker, args=(urls, save_dir, fmt), daemon=True)
        t.start()

    def _cancel_download(self):
        if self.is_downloading:
            self.cancel_requested = True
            self.cancel_btn.configure(state="disabled")
            self._log("\n[!] Cancel diminta — akan berhenti setelah link yang sedang berjalan selesai...\n")

    # ------------------------------------------------------------------
    def _set_progress(self, value):
        """Called ONLY via root.after -> safe to invoke from the download thread."""
        self.progress["value"] = value

    def _set_overall_label(self, text):
        self.overall_label.configure(text=text)

    def _progress_hook(self, d):
        # d runs inside the worker thread (not the main thread), so Tkinter
        # widgets must never be touched directly here. All UI updates are
        # scheduled via self.root.after(0, ...) so they run on the main thread.
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            if total:
                pct = downloaded / total * 100
                self.root.after(0, self._set_progress, pct)
            speed = d.get("_speed_str", "")
            eta = d.get("_eta_str", "")
            self._log(f"\r[download] {d.get('_percent_str', '')} speed={speed} eta={eta}")
        elif d.get("status") == "finished":
            self.root.after(0, self._set_progress, 100)
            self._log("\n[download] Download finished...\n")

    # ------------------------------------------------------------------
    @staticmethod
    def _channel_label(channels):
        if channels is None:
            return None
        if channels == 1:
            return "Mono"
        if channels == 2:
            return "Stereo"
        return f"{channels} channel"

    @staticmethod
    def _get_output_filepath(info, ydl):
        """
        Locate the FINAL output file (after postprocessing, if any).
        yt-dlp fills info['requested_downloads'][0]['filepath'] with the final
        path; that's the most reliable source. Falls back to
        ydl.prepare_filename() (the pre-postprocessing path, only correct
        when there's no postprocessor so the path doesn't change).
        """
        try:
            rd = info.get("requested_downloads") or []
            if rd:
                fp = rd[0].get("filepath") or rd[0].get("_filename")
                if fp and os.path.isfile(fp):
                    return fp
        except Exception:
            pass
        try:
            fp = ydl.prepare_filename(info)
            if os.path.isfile(fp):
                return fp
        except Exception:
            pass
        return None

    @staticmethod
    def _probe_output_file(filepath):
        """
        Read the ACTUAL metadata of the final file using ffprobe.
        This is more trustworthy than yt-dlp's info dict for MP3, since it
        reflects the file's real state after FFmpeg has finished converting.
        Returns None if ffprobe is unavailable or parsing fails.
        """
        if not filepath or not os.path.isfile(filepath):
            return None
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet",
                    "-print_format", "json",
                    "-show_format", "-show_streams",
                    filepath,
                ],
                capture_output=True, text=True, timeout=20,
            )
            if result.returncode != 0 or not result.stdout:
                return None
            data = json.loads(result.stdout)
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            return None

        audio_stream = next(
            (s for s in data.get("streams", []) if s.get("codec_type") == "audio"),
            None,
        )
        if not audio_stream:
            return None

        fmt_info = data.get("format", {})
        bitrate_raw = audio_stream.get("bit_rate") or fmt_info.get("bit_rate")
        try:
            bitrate_kbps = int(bitrate_raw) // 1000 if bitrate_raw else None
        except (TypeError, ValueError):
            bitrate_kbps = None

        return {
            "ext": os.path.splitext(filepath)[1].lstrip(".").upper(),
            "codec": audio_stream.get("codec_name"),
            "sample_rate": audio_stream.get("sample_rate"),
            "channels": audio_stream.get("channels"),
            "channel_layout": audio_stream.get("channel_layout"),
            "bitrate_kbps": bitrate_kbps,
        }

    def _format_info_block(self, info, fmt, probe=None):
        """Builds the info block from real metadata, not assumptions."""
        title = info.get("title", "Unknown")
        codec = info.get("acodec")
        fmtid = info.get("format_id")
        abr = info.get("abr")
        asr = info.get("asr")
        channels = info.get("audio_channels")
        ch_label = self._channel_label(channels)

        lines = [f"\n✅ Download complete: {title}"]

        if fmt == "mp3":
            # MP3 is always re-encoded from the best available source audio
            # (Opus), so real MP3 quality can never exceed the source's quality.
            lines.append("Format    : MP3 (converted with FFmpeg from the original YouTube audio)")
            if abr:
                lines.append(f"Source bitrate : ~{abr:.0f} kbps (before converting to MP3)")
            lines.append("Note      : MP3 quality is capped by the source bitrate above,")
            lines.append("            not by the MP3 target bitrate itself.")
        elif fmt == "webm":
            # WEBM: the raw file exactly as served by YouTube. No postprocessor
            # is involved at all, so there is zero re-encoding of any kind.
            lines.append(f"Format    : WEBM / {(codec or '').upper() or 'Opus'} (raw download, absolutely no re-encode)")
            if fmtid:
                lines.append(f"Format ID : {fmtid}")
            if abr:
                lines.append(f"Bitrate   : ~{abr:.0f} kbps")
            if asr:
                lines.append(f"Sample Rate : {asr} Hz (original, not resampled)")
            if ch_label:
                lines.append(f"Channels  : {ch_label} (original, not forced)")
        else:
            # OPUS: remuxed into a .opus container (no re-encode, see worker notes).
            # M4A: downloaded as-is, no postprocessor at all.
            if fmt == "opus":
                lines.append(f"Format    : {(codec or fmt).upper()} (remuxed to .opus, no re-encode)")
            else:
                lines.append(f"Format    : {(codec or fmt).upper()} (native from YouTube, no re-encode)")
            if fmtid:
                lines.append(f"Format ID : {fmtid}")
            if abr:
                lines.append(f"Bitrate   : ~{abr:.0f} kbps")
            if asr:
                lines.append(f"Sample Rate : {asr} Hz (original, not resampled)")
            if ch_label:
                lines.append(f"Channels  : {ch_label} (original, not forced)")

        # Metadata of the ACTUAL FINAL FILE, read straight from disk via ffprobe.
        # This is the most trustworthy source, especially for MP3, since it
        # reflects the state after FFmpeg finished, not before.
        if probe:
            lines.append("")
            lines.append("Output file (ffprobe):")
            lines.append(f"  Container/Codec : {probe['ext']} / {probe.get('codec') or '-'}")
            if probe.get("sample_rate"):
                lines.append(f"  Sample Rate     : {probe['sample_rate']} Hz")
            if probe.get("channels"):
                layout = probe.get("channel_layout") or self._channel_label(probe["channels"]) or ""
                lines.append(f"  Channels        : {probe['channels']} ({layout})")
            if probe.get("bitrate_kbps"):
                lines.append(f"  Bitrate         : ~{probe['bitrate_kbps']} kbps")
        else:
            lines.append("")
            lines.append("(ffprobe not found / failed to read the file — output metadata not shown)")

        return "\n".join(lines) + "\n"

    def _build_ydl_opts(self, fmt, outtmpl):
        if fmt == "webm":
            # Format 251 is downloaded exactly as YouTube serves it
            # (WebM container, Opus stream inside). NO postprocessor at all,
            # so there is absolutely no re-encoding or remuxing of any kind.
            return {
                "format": "251/bestaudio[acodec=opus]/bestaudio/best",
                "outtmpl": outtmpl,
                "progress_hooks": [self._progress_hook],
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
            }

        elif fmt == "opus":
            # Format 251 is already native Opus audio inside a WebM container.
            # preferredcodec="opus" WITHOUT preferredquality -> yt-dlp detects
            # the source codec already matches the target, so FFmpeg only
            # performs a REMUX (-c:a copy), never a re-encode. The result is a
            # .opus file with identical codec and audio quality.
            return {
                "format": "251/bestaudio[acodec=opus]/bestaudio/best",
                "outtmpl": outtmpl,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "opus",
                }],
                "progress_hooks": [self._progress_hook],
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
            }

        elif fmt == "m4a":
            # Format 140 is already native AAC/M4A audio.
            # NO postprocessor -> the file is saved exactly as downloaded.
            return {
                "format": "140/bestaudio[ext=m4a]/bestaudio/best",
                "outtmpl": outtmpl,
                "progress_hooks": [self._progress_hook],
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
            }

        else:
            # MP3 genuinely needs FFmpeg since the target codec differs from
            # the source. -ar/-ac are never forced, so the original sample
            # rate and channel count are preserved; only the codec changes.
            return {
                "format": "251/bestaudio/best",
                "outtmpl": outtmpl,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "0",  # best VBR FFmpeg can provide
                }],
                "progress_hooks": [self._progress_hook],
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
            }

    def _download_one(self, url, save_dir, fmt):
        """Download satu link. Return True kalau sukses, False kalau gagal."""
        outtmpl = os.path.join(save_dir, "%(title)s.%(ext)s")
        ydl_opts = self._build_ydl_opts(fmt, outtmpl)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                out_filepath = self._get_output_filepath(info, ydl)

            probe = self._probe_output_file(out_filepath)
            msg = self._format_info_block(info, fmt, probe)
            msg += f"Location  : {save_dir}\n"
            self._log(msg)
            return True
        except Exception as e:
            err_msg = str(e)
            if "ffmpeg" in err_msg.lower():
                err_msg += "\n\n[Tip] Make sure FFmpeg is installed and available in the System PATH."
            self._log(f"\n❌ Gagal download ({url}): {err_msg}\n")
            return False

    def _batch_download_worker(self, urls, save_dir, fmt):
        total = len(urls)
        success_count = 0
        failed_urls = []

        for idx, url in enumerate(urls, start=1):
            if self.cancel_requested:
                self._log(f"\n[!] Dibatalkan oleh user. {idx - 1}/{total} link sudah diproses.\n")
                break

            self.root.after(0, self._set_overall_label, f"Link {idx}/{total}: {url}")
            self.root.after(0, self._set_progress, 0)
            self._log(f"\n=== [{idx}/{total}] Mengunduh: {url} ===\n")

            ok = self._download_one(url, save_dir, fmt)
            if ok:
                success_count += 1
            else:
                failed_urls.append(url)

        summary = f"\n=== Selesai: {success_count}/{total} berhasil"
        if failed_urls:
            summary += f", {len(failed_urls)} gagal ===\nLink gagal:\n" + "\n".join(f"  - {u}" for u in failed_urls) + "\n"
        else:
            summary += " ===\n"
        self._log(summary)

        self.is_downloading = False
        self.cancel_requested = False
        self.root.after(0, self._set_overall_label, f"Selesai: {success_count}/{total} berhasil")
        self.root.after(0, lambda: self.download_btn.configure(state="normal", text="Download"))
        self.root.after(0, lambda: self.cancel_btn.configure(state="disabled"))


# ----------------------------------------------------------------------
def main():
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")
    except tk.TclError:
        pass

    app = YTAudioDownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    if sys.version_info < (3, 7):
        print("Requires Python 3.7 or later.")
        sys.exit(1)
    main()
