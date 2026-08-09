#!/usr/bin/env python3
"""
Audio Cutter GUI
-----------------
Cuts an audio file (MP3, M4A, OPUS) based on a start & end time with
millisecond precision (format: HH:MM:SS:mmm), includes a preview
player, and lets you choose the output format (Original / MP3 / M4A / OPUS).

HOW AUDIO QUALITY IS HANDLED:
  - "Original" output -> uses FFmpeg stream-copy (-c copy).
    The audio is NOT decoded/re-encoded at all, so the output is
    100% bit-identical to the original source.
  - MP3/M4A/OPUS output (different from the source format) -> requires
    re-encoding (because the codec changes), so the highest available
    quality setting is used (near-transparent to the ear), even though
    technically a lossy-to-lossy re-encode can never be 100%
    bit-identical.

DEPENDENCIES:
    - Python 3.8+
    - FFmpeg (ffmpeg, ffprobe, ffplay) must be installed & available on PATH.
      Download: https://ffmpeg.org/download.html
      Windows : add the ffmpeg\\bin folder to PATH
      macOS   : brew install ffmpeg
      Linux   : sudo apt install ffmpeg

USAGE:
    python audio_cutter.py
"""

import os
import re
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

TIME_RE = re.compile(r"^(\d{1,2}):(\d{1,2}):(\d{1,2})[:.](\d{1,3})$")

SUPPORTED_INPUT_EXT = [".opus", ".m4a", ".mp3"]

OUTPUT_FORMATS = {
    "Original (same as input)": "original",
    "MP3": "mp3",
    "M4A (AAC)": "m4a",
    "OPUS": "opus",
}


def which_or_none(name):
    return shutil.which(name)


def parse_time(text):
    """Parse 'HH:MM:SS:mmm' or 'HH:MM:SS.mmm' -> total seconds (float)."""
    text = text.strip()
    m = TIME_RE.match(text)
    if not m:
        raise ValueError(f"Invalid time format: '{text}'. Use HH:MM:SS:mmm")
    hh, mm, ss, ms = m.groups()
    ms = ms.ljust(3, "0")[:3]  # pad/truncate to 3 digits
    total = int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000.0
    return total


def seconds_to_time(total_seconds):
    if total_seconds < 0:
        total_seconds = 0
    hh = int(total_seconds // 3600)
    mm = int((total_seconds % 3600) // 60)
    ss = int(total_seconds % 60)
    ms = int(round((total_seconds - int(total_seconds)) * 1000))
    if ms >= 1000:
        ms = 0
        ss += 1
        if ss >= 60:
            ss = 0
            mm += 1
            if mm >= 60:
                mm = 0
                hh += 1
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ms:03d}"


def get_duration(filepath):
    """Get file duration (seconds) via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        filepath,
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


class AudioCutterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Audio Cutter - Cut Audio Without Losing Quality")
        self.geometry("680x600")
        self.minsize(660, 560)
        # Allow resizing and maximizing the window
        self.resizable(True, True)

        self.input_path = None
        self.output_path = None  # explicit "Save As" target, if chosen
        self.duration = 0.0
        self.preview_process = None

        self.ffmpeg_ok = which_or_none("ffmpeg") is not None
        self.ffprobe_ok = which_or_none("ffprobe") is not None
        self.ffplay_ok = which_or_none("ffplay") is not None

        self._build_ui()

        if not (self.ffmpeg_ok and self.ffprobe_ok):
            messagebox.showwarning(
                "FFmpeg not found",
                "ffmpeg / ffprobe was not found on PATH.\n\n"
                "This application requires FFmpeg to cut audio.\n"
                "Please install FFmpeg first:\n"
                "https://ffmpeg.org/download.html\n\n"
                "Windows: make sure ffmpeg.exe is on PATH.\n"
                "macOS  : brew install ffmpeg\n"
                "Linux  : sudo apt install ffmpeg",
            )

    # ---------------------------------------------------------- UI ----
    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # --- File input ---
        frame_file = ttk.LabelFrame(self, text="1. Select Audio File (opus / m4a / mp3)")
        frame_file.pack(fill="x", **pad)

        self.lbl_file = ttk.Label(frame_file, text="No file selected", foreground="gray")
        self.lbl_file.pack(side="left", padx=10, pady=10, fill="x", expand=True)

        ttk.Button(frame_file, text="Browse...", command=self.browse_file).pack(
            side="right", padx=10, pady=10
        )

        # --- Time range ---
        frame_time = ttk.LabelFrame(self, text="2. Set Cut Range (format: HH:MM:SS:mmm)")
        frame_time.pack(fill="x", **pad)

        ttk.Label(frame_time, text="Start:").grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.entry_start = ttk.Entry(frame_time, width=15, justify="center")
        self.entry_start.insert(0, "00:00:00:000")
        self.entry_start.grid(row=0, column=1, padx=5, pady=8)

        ttk.Label(frame_time, text="End:").grid(row=0, column=2, padx=10, pady=8, sticky="w")
        self.entry_end = ttk.Entry(frame_time, width=15, justify="center")
        self.entry_end.insert(0, "00:00:00:000")
        self.entry_end.grid(row=0, column=3, padx=5, pady=8)

        ttk.Button(frame_time, text="Set End = Full Duration", command=self.set_end_to_full).grid(
            row=1, column=0, columnspan=2, padx=10, pady=4, sticky="w"
        )
        self.lbl_duration = ttk.Label(frame_time, text="File duration: -")
        self.lbl_duration.grid(row=1, column=2, columnspan=2, padx=10, pady=4, sticky="w")

        # --- Preview ---
        frame_preview = ttk.LabelFrame(self, text="3. Preview (plays the selected section)")
        frame_preview.pack(fill="x", **pad)

        self.btn_preview = ttk.Button(frame_preview, text="\u25b6 Preview Cut", command=self.play_preview)
        self.btn_preview.pack(side="left", padx=10, pady=10)

        self.btn_stop = ttk.Button(frame_preview, text="\u25a0 Stop", command=self.stop_preview, state="disabled")
        self.btn_stop.pack(side="left", padx=5, pady=10)

        if not self.ffplay_ok:
            ttk.Label(
                frame_preview,
                text="(ffplay not found - preview disabled)",
                foreground="red",
            ).pack(side="left", padx=10)
            self.btn_preview.config(state="disabled")

        # --- Output format ---
        frame_out = ttk.LabelFrame(self, text="4. Output Format")
        frame_out.pack(fill="x", **pad)

        self.output_format_var = tk.StringVar(value="Original (same as input)")
        col = 0
        for label in OUTPUT_FORMATS:
            ttk.Radiobutton(
                frame_out, text=label, value=label, variable=self.output_format_var,
                command=self._on_format_changed,
            ).grid(row=0, column=col, padx=10, pady=8, sticky="w")
            col += 1

        note = (
            "Note: 'Original' cuts using stream-copy (no re-encoding), so the audio\n"
            "quality is 100% identical to the source file. Converting to another format\n"
            "requires re-encoding and uses the highest quality setting available."
        )
        ttk.Label(frame_out, text=note, foreground="gray", justify="left").grid(
            row=1, column=0, columnspan=4, padx=10, pady=(0, 8), sticky="w"
        )

        # --- Save As ---
        frame_save = ttk.LabelFrame(self, text="5. Save Location")
        frame_save.pack(fill="x", **pad)

        self.lbl_output = ttk.Label(
            frame_save, text="Not set - you'll be asked when you click Cut Audio",
            foreground="gray",
        )
        self.lbl_output.pack(side="left", padx=10, pady=10, fill="x", expand=True)

        ttk.Button(frame_save, text="Save As...", command=self.choose_save_path).pack(
            side="right", padx=10, pady=10
        )

        # --- Export ---
        frame_export = ttk.LabelFrame(self, text="6. Cut & Export")
        frame_export.pack(fill="x", **pad)

        self.btn_export = ttk.Button(frame_export, text="\u2702 Cut Audio", command=self.export_audio)
        self.btn_export.pack(side="left", padx=10, pady=10)

        self.progress = ttk.Progressbar(frame_export, mode="indeterminate", length=300)
        self.progress.pack(side="left", padx=10, pady=10)

        self.lbl_status = ttk.Label(self, text="", foreground="blue", wraplength=640, justify="left")
        self.lbl_status.pack(fill="x", padx=15, pady=(0, 10))

    # ------------------------------------------------------- actions ----
    def _current_out_ext(self):
        output_kind = OUTPUT_FORMATS[self.output_format_var.get()]
        input_ext = os.path.splitext(self.input_path)[1].lower().lstrip(".") if self.input_path else "mp3"
        return input_ext if output_kind == "original" else output_kind

    def _on_format_changed(self):
        # If a save path was already chosen but the extension no longer
        # matches the selected format, clear it so the user re-confirms.
        if self.output_path:
            ext = os.path.splitext(self.output_path)[1].lower().lstrip(".")
            if ext != self._current_out_ext():
                self.output_path = None
                self.lbl_output.config(
                    text="Not set - you'll be asked when you click Cut Audio",
                    foreground="gray",
                )

    def choose_save_path(self):
        out_ext = self._current_out_ext()
        default_name = "output_cut." + out_ext
        if self.input_path:
            default_name = os.path.splitext(os.path.basename(self.input_path))[0] + f"_cut.{out_ext}"

        save_path = filedialog.asksaveasfilename(
            title="Save cut audio as",
            defaultextension=f".{out_ext}",
            initialfile=default_name,
            filetypes=[(f"{out_ext.upper()} file", f"*.{out_ext}")],
        )
        if not save_path:
            return
        self.output_path = save_path
        self.lbl_output.config(text=save_path, foreground="black")

    def browse_file(self):
        filetypes = [
            ("Audio Files", "*.opus *.m4a *.mp3"),
            ("OPUS", "*.opus"),
            ("M4A", "*.m4a"),
            ("MP3", "*.mp3"),
            ("All Files", "*.*"),
        ]
        path = filedialog.askopenfilename(title="Select an audio file", filetypes=filetypes)
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        if ext not in SUPPORTED_INPUT_EXT:
            messagebox.showwarning(
                "Unsupported format",
                f"Format {ext} is not supported.\nUse opus, m4a, or mp3.",
            )
            return

        self.input_path = path
        self.lbl_file.config(text=os.path.basename(path), foreground="black")
        # A new source file invalidates any previously chosen save path
        self.output_path = None
        self.lbl_output.config(
            text="Not set - you'll be asked when you click Cut Audio",
            foreground="gray",
        )

        if self.ffprobe_ok:
            try:
                self.duration = get_duration(path)
                self.lbl_duration.config(text=f"File duration: {seconds_to_time(self.duration)}")
                self.entry_start.delete(0, tk.END)
                self.entry_start.insert(0, "00:00:00:000")
                self.entry_end.delete(0, tk.END)
                self.entry_end.insert(0, seconds_to_time(self.duration))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read file duration:\n{e}")
        else:
            self.lbl_duration.config(text="File duration: (ffprobe not available)")

    def set_end_to_full(self):
        if self.duration:
            self.entry_end.delete(0, tk.END)
            self.entry_end.insert(0, seconds_to_time(self.duration))

    def _get_validated_range(self):
        if not self.input_path:
            raise ValueError("Please select an audio file first.")
        start = parse_time(self.entry_start.get())
        end = parse_time(self.entry_end.get())
        if end <= start:
            raise ValueError("End time must be greater than start time.")
        if self.duration and end > self.duration + 0.5:
            raise ValueError(f"End time exceeds the file duration ({seconds_to_time(self.duration)}).")
        return start, end

    def play_preview(self):
        if not self.ffplay_ok:
            return
        try:
            start, end = self._get_validated_range()
        except Exception as e:
            messagebox.showerror("Invalid input", str(e))
            return

        self.stop_preview()
        duration = end - start
        cmd = [
            "ffplay", "-nodisp", "-autoexit",
            "-ss", str(start),
            "-t", str(duration),
            self.input_path,
        ]
        try:
            self.preview_process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            self.btn_stop.config(state="normal")
            self.lbl_status.config(
                text=f"Playing preview {seconds_to_time(start)} - {seconds_to_time(end)} ..."
            )
            threading.Thread(target=self._watch_preview, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to play preview:\n{e}")

    def _watch_preview(self):
        proc = self.preview_process
        if proc:
            proc.wait()
            if self.preview_process is proc:
                self.btn_stop.config(state="disabled")
                self.lbl_status.config(text="Preview finished.")

    def stop_preview(self):
        if self.preview_process and self.preview_process.poll() is None:
            self.preview_process.terminate()
        self.preview_process = None
        self.btn_stop.config(state="disabled")

    def export_audio(self):
        if not (self.ffmpeg_ok and self.ffprobe_ok):
            messagebox.showerror("FFmpeg not found", "ffmpeg/ffprobe was not found on PATH.")
            return
        try:
            start, end = self._get_validated_range()
        except Exception as e:
            messagebox.showerror("Invalid input", str(e))
            return

        output_label = self.output_format_var.get()
        output_kind = OUTPUT_FORMATS[output_label]
        out_ext = self._current_out_ext()

        save_path = self.output_path
        if not save_path:
            default_name = os.path.splitext(os.path.basename(self.input_path))[0] + f"_cut.{out_ext}"
            save_path = filedialog.asksaveasfilename(
                title="Save cut audio as",
                defaultextension=f".{out_ext}",
                initialfile=default_name,
                filetypes=[(f"{out_ext.upper()} file", f"*.{out_ext}")],
            )
            if not save_path:
                return
            self.output_path = save_path
            self.lbl_output.config(text=save_path, foreground="black")

        self.btn_export.config(state="disabled")
        self.progress.start(10)
        self.lbl_status.config(text="Cutting audio...")

        thread = threading.Thread(
            target=self._run_export,
            args=(start, end, output_kind, save_path),
            daemon=True,
        )
        thread.start()

    def _run_export(self, start, end, output_kind, save_path):
        duration = end - start
        try:
            if output_kind == "original":
                # Stream copy -> no decode/re-encode at all,
                # quality is 100% identical to the source.
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(start),
                    "-i", self.input_path,
                    "-t", str(duration),
                    "-c", "copy",
                    "-avoid_negative_ts", "make_zero",
                    save_path,
                ]
            elif output_kind == "mp3":
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(start),
                    "-i", self.input_path,
                    "-t", str(duration),
                    "-c:a", "libmp3lame",
                    "-q:a", "0",  # highest VBR quality (~245kbps), near-transparent
                    save_path,
                ]
            elif output_kind == "m4a":
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(start),
                    "-i", self.input_path,
                    "-t", str(duration),
                    "-c:a", "aac",
                    "-b:a", "320k",
                    save_path,
                ]
            elif output_kind == "opus":
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(start),
                    "-i", self.input_path,
                    "-t", str(duration),
                    "-c:a", "libopus",
                    "-b:a", "256k",
                    "-vbr", "on",
                    save_path,
                ]
            else:
                raise ValueError("Unknown output format.")

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(result.stderr[-1500:])

            self.after(0, self._export_done, True, save_path, None)
        except Exception as e:
            self.after(0, self._export_done, False, save_path, str(e))

    def _export_done(self, success, save_path, error):
        self.progress.stop()
        self.btn_export.config(state="normal")
        if success:
            self.lbl_status.config(text=f"Saved successfully: {save_path}")
            messagebox.showinfo("Done", f"Audio was cut and saved to:\n{save_path}")
        else:
            self.lbl_status.config(text="Failed to cut audio.")
            messagebox.showerror("Failed", f"An error occurred while cutting the audio:\n\n{error}")

    def on_close(self):
        self.stop_preview()
        self.destroy()


def main():
    app = AudioCutterApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()


if __name__ == "__main__":
    main()
