#!/usr/bin/env python3
"""
QR Signature App
=================
Aplikasi desktop (Tkinter) untuk membuat tanda tangan digital berbasis QR Code.

Fitur:
1. Tab Key Generator  - membuat pasangan private/public key (Ed25519 / ECDSA P-256)
2. Tab QR Maker       - mengisi data dokumen, menandatangani, dan membuat QR
3. Tab Verifier       - memindai QR dan memverifikasi tanda tangan

Dependensi: cryptography, qrcode, pillow, opencv-python-headless
    pip install cryptography qrcode pillow opencv-python-headless
"""

import base64
import json
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import ed25519, ec
from cryptography.exceptions import InvalidSignature

import qrcode
from qrcode.constants import ERROR_CORRECT_H, ERROR_CORRECT_M
from PIL import Image, ImageDraw, ImageTk

import cv2
import numpy as np

# --------------------------------------------------------------------------- #
# Konstanta
# --------------------------------------------------------------------------- #

ALGO_ED25519 = "Ed25519"
ALGO_ECDSA_P256 = "ECDSA-P256"

TIMEZONES = {
    "UTC": 0,
    "WIB": 7,
    "WITA": 8,
    "WIT": 9,
}

LOGO_NONE = "Tanpa logo"
LOGO_SPACE = "Logo dengan ruang sendiri (di tengah)"
LOGO_OVERLAY = "Logo menutup sebagian QR (tanpa ruang)"

MAGIC = "QRSIGv1"  # penanda format payload


# --------------------------------------------------------------------------- #
# Helper: waktu & zona waktu
# --------------------------------------------------------------------------- #

def now_in_tz(tz_name: str) -> datetime:
    """Mengembalikan datetime 'sekarang' pada zona waktu Indonesia/UTC yang dipilih."""
    offset = TIMEZONES.get(tz_name, 0)
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=offset)))


def make_datetime(tz_name: str, year, month, day, hour, minute) -> datetime:
    offset = TIMEZONES.get(tz_name, 0)
    return datetime(int(year), int(month), int(day), int(hour), int(minute),
                     tzinfo=timezone(timedelta(hours=offset)))


def fmt_dt(dt: datetime, tz_name: str) -> str:
    """Format string yang menyimpan info zona waktu label (WIB/WITA/WIT/UTC) secara eksplisit."""
    return f"{dt.strftime('%Y-%m-%d %H:%M:%S')} {tz_name}"


def parse_dt(s: str):
    """Parse string hasil fmt_dt kembali menjadi datetime timezone-aware + label tz."""
    try:
        dt_part, tz_label = s.rsplit(" ", 1)
        offset = TIMEZONES.get(tz_label, 0)
        dt = datetime.strptime(dt_part, "%Y-%m-%d %H:%M:%S")
        dt = dt.replace(tzinfo=timezone(timedelta(hours=offset)))
        return dt, tz_label
    except Exception:
        return None, None


# --------------------------------------------------------------------------- #
# Helper: kriptografi
# --------------------------------------------------------------------------- #

def generate_keypair(algo: str):
    if algo == ALGO_ED25519:
        priv = ed25519.Ed25519PrivateKey.generate()
    elif algo == ALGO_ECDSA_P256:
        priv = ec.generate_private_key(ec.SECP256R1())
    else:
        raise ValueError("Algoritma tidak dikenal")
    pub = priv.public_key()
    return priv, pub


def private_key_to_pem(priv) -> bytes:
    return priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def public_key_to_pem(pub) -> bytes:
    return pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def load_private_key(path: str):
    with open(path, "rb") as f:
        data = f.read()
    priv = serialization.load_pem_private_key(data, password=None)
    if isinstance(priv, ed25519.Ed25519PrivateKey):
        return priv, ALGO_ED25519
    elif isinstance(priv, ec.EllipticCurvePrivateKey) and isinstance(priv.curve, ec.SECP256R1):
        return priv, ALGO_ECDSA_P256
    else:
        raise ValueError("Jenis private key tidak didukung (harus Ed25519 atau ECDSA P-256)")


def load_public_key(path: str):
    with open(path, "rb") as f:
        data = f.read()
    pub = serialization.load_pem_public_key(data)
    if isinstance(pub, ed25519.Ed25519PublicKey):
        return pub, ALGO_ED25519
    elif isinstance(pub, ec.EllipticCurvePublicKey) and isinstance(pub.curve, ec.SECP256R1):
        return pub, ALGO_ECDSA_P256
    else:
        raise ValueError("Jenis public key tidak didukung (harus Ed25519 atau ECDSA P-256)")


def sign_bytes(priv, algo: str, data: bytes) -> bytes:
    if algo == ALGO_ED25519:
        return priv.sign(data)
    elif algo == ALGO_ECDSA_P256:
        return priv.sign(data, ec.ECDSA(hashes.SHA256()))
    else:
        raise ValueError("Algoritma tidak dikenal")


def verify_bytes(pub, algo: str, data: bytes, sig: bytes) -> bool:
    try:
        if algo == ALGO_ED25519:
            pub.verify(sig, data)
        elif algo == ALGO_ECDSA_P256:
            pub.verify(sig, data, ec.ECDSA(hashes.SHA256()))
        else:
            return False
        return True
    except InvalidSignature:
        return False


def canonical_json(payload: dict) -> bytes:
    """JSON kanonik (sorted key, tanpa spasi) supaya signature konsisten & deterministik."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


# --------------------------------------------------------------------------- #
# Helper: QR Code
# --------------------------------------------------------------------------- #

def build_qr_image(content: str, fill_color: str, logo_path: str, logo_mode: str) -> Image.Image:
    """Membuat gambar QR (PIL Image) dari string content, dengan opsi warna & logo."""
    # error correction lebih tinggi kalau ada logo, supaya tetap terbaca
    ec_level = ERROR_CORRECT_H if logo_mode != LOGO_NONE else ERROR_CORRECT_M

    qr = qrcode.QRCode(
        version=None,
        error_correction=ec_level,
        box_size=10,
        border=4,
    )
    qr.add_data(content)
    qr.make(fit=True)

    img = qr.make_image(fill_color=fill_color, back_color="white").convert("RGB")

    if logo_mode != LOGO_NONE and logo_path and os.path.isfile(logo_path):
        img = _apply_logo(img, logo_path, logo_mode)

    return img


def _apply_logo(qr_img: Image.Image, logo_path: str, logo_mode: str) -> Image.Image:
    qr_img = qr_img.convert("RGBA")
    logo = Image.open(logo_path).convert("RGBA")

    W, H = qr_img.size

    if logo_mode == LOGO_SPACE:
        # Logo diberi ruang putih bersih di tengah (tidak menimpa modul QR di area itu)
        logo_size = int(W * 0.28)
        logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
        pad = int(logo_size * 0.12)
        box_size = logo_size + pad * 2
        box_pos = ((W - box_size) // 2, (H - box_size) // 2)

        draw = ImageDraw.Draw(qr_img)
        draw.rectangle(
            [box_pos, (box_pos[0] + box_size, box_pos[1] + box_size)],
            fill="white",
        )
        logo_pos = ((W - logo_size) // 2, (H - logo_size) // 2)
        qr_img.paste(logo, logo_pos, logo)

    elif logo_mode == LOGO_OVERLAY:
        # Logo langsung menimpa sebagian modul QR (tanpa kotak putih di belakangnya)
        logo_size = int(W * 0.28)
        logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
        logo_pos = ((W - logo_size) // 2, (H - logo_size) // 2)
        qr_img.paste(logo, logo_pos, logo)

    return qr_img.convert("RGB")


def decode_qr_from_image(path: str):
    """Decode QR pakai OpenCV, mengembalikan string data (atau None kalau gagal)."""
    img = cv2.imread(path)
    if img is None:
        # fallback: buka lewat PIL (untuk kompatibilitas format), lalu convert
        pil_img = Image.open(path).convert("RGB")
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    detector = cv2.QRCodeDetector()
    data, points, _ = detector.detectAndDecode(img)
    if data:
        return data

    # coba upscale kalau gagal (QR kecil / resolusi rendah)
    h, w = img.shape[:2]
    big = cv2.resize(img, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
    data, points, _ = detector.detectAndDecode(big)
    return data if data else None


# --------------------------------------------------------------------------- #
# GUI: Root App
# --------------------------------------------------------------------------- #

class QRSignatureApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("QR Signature - Key Generator, QR Maker & Verifier")
        self.geometry("1080x800")
        self.minsize(980, 700)

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.tab_keygen = KeyGenTab(notebook)
        self.tab_qrmaker = QRMakerTab(notebook)
        self.tab_verifier = VerifierTab(notebook)

        notebook.add(self.tab_keygen, text="  Key Generator  ")
        notebook.add(self.tab_qrmaker, text="  QR Maker  ")
        notebook.add(self.tab_verifier, text="  Verifier  ")


# --------------------------------------------------------------------------- #
# Tab 1: Key Generator
# --------------------------------------------------------------------------- #

class KeyGenTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=16)
        self.priv = None
        self.pub = None
        self.algo = tk.StringVar(value=ALGO_ED25519)

        ttk.Label(self, text="Key Generator", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(self, text="Buat pasangan private key & public key untuk menandatangani dokumen.",
                  foreground="#555").pack(anchor="w", pady=(0, 12))

        algo_frame = ttk.LabelFrame(self, text="Algoritma ECC", padding=10)
        algo_frame.pack(fill="x", pady=6)
        ttk.Radiobutton(algo_frame, text="Ed25519 (cepat, ringkas, direkomendasikan)",
                         variable=self.algo, value=ALGO_ED25519).pack(anchor="w")
        ttk.Radiobutton(algo_frame, text="ECDSA P-256 (secp256r1)",
                         variable=self.algo, value=ALGO_ECDSA_P256).pack(anchor="w")

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", pady=10)
        ttk.Button(btn_frame, text="Generate Key Pair", command=self.on_generate).pack(side="left")
        self.save_priv_btn = ttk.Button(btn_frame, text="Simpan Private Key (.pem)",
                                         command=self.save_private, state="disabled")
        self.save_priv_btn.pack(side="left", padx=8)
        self.save_pub_btn = ttk.Button(btn_frame, text="Simpan Public Key (.pem)",
                                        command=self.save_public, state="disabled")
        self.save_pub_btn.pack(side="left")

        ttk.Label(self, text="Private Key (PEM):").pack(anchor="w", pady=(10, 2))
        self.priv_text = tk.Text(self, height=8, wrap="none", font=("Consolas", 9))
        self.priv_text.pack(fill="both", expand=False)

        ttk.Label(self, text="Public Key (PEM):").pack(anchor="w", pady=(10, 2))
        self.pub_text = tk.Text(self, height=8, wrap="none", font=("Consolas", 9))
        self.pub_text.pack(fill="both", expand=False)

        warn = ("Peringatan: simpan private key di tempat aman dan jangan dibagikan. "
                "Public key boleh dibagikan bebas untuk keperluan verifikasi.")
        ttk.Label(self, text=warn, foreground="#a33", wraplength=800, justify="left").pack(anchor="w", pady=(10, 0))

    def on_generate(self):
        try:
            self.priv, self.pub = generate_keypair(self.algo.get())
            priv_pem = private_key_to_pem(self.priv).decode()
            pub_pem = public_key_to_pem(self.pub).decode()

            self.priv_text.delete("1.0", "end")
            self.priv_text.insert("1.0", priv_pem)
            self.pub_text.delete("1.0", "end")
            self.pub_text.insert("1.0", pub_pem)

            self.save_priv_btn["state"] = "normal"
            self.save_pub_btn["state"] = "normal"
            messagebox.showinfo("Berhasil", f"Key pair {self.algo.get()} berhasil dibuat.")
        except Exception as e:
            messagebox.showerror("Gagal", str(e))

    def save_private(self):
        if not self.priv:
            return
        path = filedialog.asksaveasfilename(defaultextension=".pem",
                                             filetypes=[("PEM file", "*.pem")],
                                             initialfile="private_key.pem")
        if path:
            with open(path, "wb") as f:
                f.write(private_key_to_pem(self.priv))
            messagebox.showinfo("Tersimpan", f"Private key disimpan ke:\n{path}")

    def save_public(self):
        if not self.pub:
            return
        path = filedialog.asksaveasfilename(defaultextension=".pem",
                                             filetypes=[("PEM file", "*.pem")],
                                             initialfile="public_key.pem")
        if path:
            with open(path, "wb") as f:
                f.write(public_key_to_pem(self.pub))
            messagebox.showinfo("Tersimpan", f"Public key disimpan ke:\n{path}")


# --------------------------------------------------------------------------- #
# Widget kecil: pemilih tanggal & jam
# --------------------------------------------------------------------------- #

class DateTimePicker(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        now = datetime.now()

        self.year = tk.StringVar(value=str(now.year))
        self.month = tk.StringVar(value=f"{now.month:02d}")
        self.day = tk.StringVar(value=f"{now.day:02d}")
        self.hour = tk.StringVar(value=f"{now.hour:02d}")
        self.minute = tk.StringVar(value=f"{now.minute:02d}")

        ttk.Spinbox(self, from_=2000, to=2100, textvariable=self.year, width=6).pack(side="left")
        ttk.Label(self, text="-").pack(side="left")
        ttk.Spinbox(self, from_=1, to=12, textvariable=self.month, width=4, format="%02.0f").pack(side="left")
        ttk.Label(self, text="-").pack(side="left")
        ttk.Spinbox(self, from_=1, to=31, textvariable=self.day, width=4, format="%02.0f").pack(side="left")
        ttk.Label(self, text="   ").pack(side="left")
        ttk.Spinbox(self, from_=0, to=23, textvariable=self.hour, width=4, format="%02.0f").pack(side="left")
        ttk.Label(self, text=":").pack(side="left")
        ttk.Spinbox(self, from_=0, to=59, textvariable=self.minute, width=4, format="%02.0f").pack(side="left")

    def get(self):
        return (self.year.get(), self.month.get(), self.day.get(),
                self.hour.get(), self.minute.get())


# --------------------------------------------------------------------------- #
# Tab 2: QR Maker
# --------------------------------------------------------------------------- #

class QRMakerTab(ttk.Frame):
    FIELD_WIDTH = 70  # lebar entry/textbox agar muat ~70 karakter

    def __init__(self, parent):
        super().__init__(parent, padding=12)

        self.priv_key = None
        self.priv_algo = None
        self.qr_color = "#000000"
        self.logo_path = ""
        self.generated_img = None

        # Layout dua kolom langsung (tanpa canvas/scrollbar) agar hemat ruang
        left = ttk.Frame(self, padding=(0, 0, 12, 0))
        left.pack(side="left", fill="both", expand=True, anchor="n")

        right = ttk.Frame(self)
        right.pack(side="left", fill="y", anchor="n")

        # ---- Private key section ----
        keyf = ttk.LabelFrame(left, text="Private Key Penandatangan", padding=8)
        keyf.pack(fill="x", pady=4)
        self.key_label = ttk.Label(keyf, text="Belum ada key dimuat.", foreground="#a33")
        self.key_label.pack(side="left")
        ttk.Button(keyf, text="Load Private Key (.pem)", command=self.load_key).pack(side="right")

        # ---- Data dokumen ----
        dataf = ttk.LabelFrame(left, text="Data Dokumen", padding=8)
        dataf.pack(fill="x", pady=4)

        self.doc_id = self._add_field(dataf, "Doc ID *")
        self.signed_by = self._add_field(dataf, "Signed by *")
        self.doc_no = self._add_field(dataf, "Doc No. (opsional)")
        self.desc = self._add_text_field(dataf, "Deskripsi (opsional, maks. 4 baris)")

        # ---- Valid Until & Time Signature (berdampingan) ----
        vu_ts_row = ttk.Frame(left)
        vu_ts_row.pack(fill="x", pady=4)

        vu_frame = ttk.LabelFrame(vu_ts_row, text="Valid Until", padding=8)
        vu_frame.pack(side="left", fill="both", expand=True, padx=(0, 4))
        self.valid_until_on = tk.BooleanVar(value=False)
        ttk.Checkbutton(vu_frame, text="Aktifkan", variable=self.valid_until_on,
                         command=self._toggle_vu).pack(anchor="w")
        self.vu_picker = DateTimePicker(vu_frame)
        self.vu_picker.pack(anchor="w", pady=(4, 4))
        tzrow = ttk.Frame(vu_frame)
        tzrow.pack(anchor="w")
        ttk.Label(tzrow, text="Zona: ").pack(side="left")
        self.vu_tz = tk.StringVar(value="WIB")
        ttk.Combobox(tzrow, textvariable=self.vu_tz, values=list(TIMEZONES.keys()),
                     width=6, state="readonly").pack(side="left")
        self._toggle_vu()

        ts_frame = ttk.LabelFrame(vu_ts_row, text="Time Signature", padding=8)
        ts_frame.pack(side="left", fill="both", expand=True, padx=(4, 0))
        self.time_sig_on = tk.BooleanVar(value=True)
        ttk.Checkbutton(ts_frame, text="Sertakan waktu pembuatan QR",
                        variable=self.time_sig_on).pack(anchor="w")
        tzrow2 = ttk.Frame(ts_frame)
        tzrow2.pack(anchor="w", pady=(4, 0))
        ttk.Label(tzrow2, text="Zona: ").pack(side="left")
        self.ts_tz = tk.StringVar(value="WIB")
        ttk.Combobox(tzrow2, textvariable=self.ts_tz, values=list(TIMEZONES.keys()),
                     width=6, state="readonly").pack(side="left")

        # ---- Logo & Warna (berdampingan) ----
        logo_color_row = ttk.Frame(left)
        logo_color_row.pack(fill="x", pady=4)

        logo_frame = ttk.LabelFrame(logo_color_row, text="Logo QR", padding=8)
        logo_frame.pack(side="left", fill="both", expand=True, padx=(0, 4))
        self.logo_mode = tk.StringVar(value=LOGO_NONE)
        for opt in (LOGO_NONE, LOGO_SPACE, LOGO_OVERLAY):
            ttk.Radiobutton(logo_frame, text=opt, variable=self.logo_mode, value=opt,
                             command=self._toggle_logo_btn).pack(anchor="w")
        self.logo_btn = ttk.Button(logo_frame, text="Pilih Gambar Logo...",
                                    command=self.choose_logo, state="disabled")
        self.logo_btn.pack(anchor="w", pady=(4, 0))
        self.logo_path_label = ttk.Label(logo_frame, text="(belum ada logo dipilih)", foreground="#555")
        self.logo_path_label.pack(anchor="w")

        color_frame = ttk.LabelFrame(logo_color_row, text="Warna QR", padding=8)
        color_frame.pack(side="left", fill="both", expand=True, padx=(4, 0))
        swatch_row = ttk.Frame(color_frame)
        swatch_row.pack(anchor="w")
        self.color_swatch = tk.Canvas(swatch_row, width=24, height=24, bg=self.qr_color,
                                       highlightthickness=1, highlightbackground="#999")
        self.color_swatch.pack(side="left", padx=(0, 8))
        ttk.Button(swatch_row, text="Pilih Warna...", command=self.choose_color).pack(side="left")
        ttk.Label(color_frame, text="(default: hitam)", foreground="#555").pack(anchor="w", pady=(4, 0))

        # ---- Generate ----
        ttk.Button(left, text="Buat & Tanda Tangani QR", command=self.on_generate).pack(
            fill="x", pady=(8, 0), ipady=6)

        # ---- Preview panel (right, dibuat ringkas) ----
        prevf = ttk.LabelFrame(right, text="Preview QR", padding=8)
        prevf.pack(fill="both")
        self.preview_label = ttk.Label(prevf, text="Belum ada\nQR dibuat.", justify="center")
        self.preview_label.pack(pady=4)
        self.save_qr_btn = ttk.Button(prevf, text="Simpan QR (.png)", command=self.save_qr, state="disabled")
        self.save_qr_btn.pack(pady=(4, 0), fill="x")

    # -- UI helpers -- #
    def _add_field(self, parent, label):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=2)
        ttk.Label(row, text=label).pack(anchor="w")
        var = tk.StringVar()
        ttk.Entry(row, textvariable=var, width=self.FIELD_WIDTH).pack(anchor="w", fill="x")
        return var

    def _add_text_field(self, parent, label):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=2)
        ttk.Label(row, text=label).pack(anchor="w")
        txt_frame = ttk.Frame(row)
        txt_frame.pack(anchor="w", fill="x")
        txt = tk.Text(txt_frame, width=self.FIELD_WIDTH, height=4, wrap="word", font=("Segoe UI", 9))
        txt.pack(side="left", fill="x", expand=True)
        sb = ttk.Scrollbar(txt_frame, orient="vertical", command=txt.yview)
        sb.pack(side="left", fill="y")
        txt.configure(yscrollcommand=sb.set)
        return txt

    def _toggle_vu(self):
        state = "normal" if self.valid_until_on.get() else "disabled"
        for child in self.vu_picker.winfo_children():
            try:
                child.configure(state=state)
            except tk.TclError:
                pass

    def _toggle_logo_btn(self):
        self.logo_btn["state"] = "disabled" if self.logo_mode.get() == LOGO_NONE else "normal"

    def choose_logo(self):
        path = filedialog.askopenfilename(
            filetypes=[("Gambar", "*.png *.jpg *.jpeg *.bmp *.gif")])
        if path:
            self.logo_path = path
            self.logo_path_label.config(text=os.path.basename(path))

    def choose_color(self):
        rgb, hexcode = colorchooser.askcolor(color=self.qr_color, title="Pilih warna QR")
        if hexcode:
            self.qr_color = hexcode
            self.color_swatch.configure(bg=hexcode)

    def load_key(self):
        path = filedialog.askopenfilename(filetypes=[("PEM file", "*.pem")])
        if not path:
            return
        try:
            self.priv_key, self.priv_algo = load_private_key(path)
            self.key_label.config(
                text=f"Key dimuat: {os.path.basename(path)}  ({self.priv_algo})",
                foreground="#0a0")
        except Exception as e:
            messagebox.showerror("Gagal memuat key", str(e))

    # -- Core action -- #
    def on_generate(self):
        if not self.priv_key:
            messagebox.showwarning("Perhatian", "Silakan load private key terlebih dahulu.")
            return
        if not self.doc_id.get().strip() or not self.signed_by.get().strip():
            messagebox.showwarning("Perhatian", "Doc ID dan Signed by wajib diisi.")
            return

        desc_val = self.desc.get("1.0", "end-1c").strip()
        # buffer +10 untuk Desc: 4 baris x 70 karakter + toleransi karakter baris baru
        limit_checks = [
            ("Doc ID", self.doc_id.get().strip(), 70),
            ("Signed by", self.signed_by.get().strip(), 70),
            ("Doc No.", self.doc_no.get().strip(), 70),
            ("Deskripsi", desc_val, 70 * 4 + 10),
        ]
        for label, value, limit in limit_checks:
            if len(value) > limit:
                messagebox.showwarning(
                    "Perhatian",
                    f"{label} melebihi batas maksimal {limit} karakter (saat ini {len(value)} karakter).")
                return

        payload = {
            "doc_id": self.doc_id.get().strip(),
            "signed_by": self.signed_by.get().strip(),
            "doc_no": self.doc_no.get().strip(),
            "desc": self.desc.get("1.0", "end-1c").strip(),
        }

        if self.time_sig_on.get():
            tz_name = self.ts_tz.get()
            payload["time_signature"] = fmt_dt(now_in_tz(tz_name), tz_name)
        else:
            payload["time_signature"] = ""

        if self.valid_until_on.get():
            try:
                y, mo, d, h, mi = self.vu_picker.get()
                tz_name = self.vu_tz.get()
                dt = make_datetime(tz_name, y, mo, d, h, mi)
                payload["valid_until"] = fmt_dt(dt, tz_name)
            except Exception as e:
                messagebox.showerror("Tanggal tidak valid", str(e))
                return
        else:
            payload["valid_until"] = ""

        data_bytes = canonical_json(payload)
        sig = sign_bytes(self.priv_key, self.priv_algo, data_bytes)
        sig_b64 = base64.b64encode(sig).decode()

        envelope = {
            "magic": MAGIC,
            "alg": self.priv_algo,
            "data": payload,
            "sig": sig_b64,
        }
        content = json.dumps(envelope, ensure_ascii=False, separators=(",", ":"))

        try:
            img = build_qr_image(content, self.qr_color, self.logo_path, self.logo_mode.get())
        except Exception as e:
            messagebox.showerror("Gagal membuat QR", str(e))
            return

        self.generated_img = img
        self._show_preview(img)
        self.save_qr_btn["state"] = "normal"
        messagebox.showinfo("Berhasil", "QR berhasil dibuat dan ditandatangani.")

    def _show_preview(self, img: Image.Image):
        preview = img.copy()
        preview.thumbnail((220, 220))
        self._tk_img = ImageTk.PhotoImage(preview)
        self.preview_label.configure(image=self._tk_img, text="")

    def save_qr(self):
        if not self.generated_img:
            return
        path = filedialog.asksaveasfilename(defaultextension=".png",
                                             filetypes=[("PNG image", "*.png")],
                                             initialfile="signed_qr.png")
        if path:
            self.generated_img.save(path)
            messagebox.showinfo("Tersimpan", f"QR disimpan ke:\n{path}")


# --------------------------------------------------------------------------- #
# Tab 3: Verifier
# --------------------------------------------------------------------------- #

class VerifierTab(ttk.Frame):
    MODE_IMAGE = "Dari Gambar QR"
    MODE_TEXT = "Dari Teks Hasil Scan"

    def __init__(self, parent):
        super().__init__(parent, padding=16)

        self.pub_key = None
        self.pub_algo = None
        self.qr_path = ""

        keyf = ttk.LabelFrame(self, text="Public Key Penandatangan", padding=10)
        keyf.pack(fill="x", pady=6)
        self.key_label = ttk.Label(keyf, text="Belum ada key dimuat.", foreground="#a33")
        self.key_label.pack(side="left")
        ttk.Button(keyf, text="Load Public Key (.pem)", command=self.load_key).pack(side="right")

        # ---- Sumber data QR: gambar atau teks hasil scan ----
        srcf = ttk.LabelFrame(self, text="Sumber Data QR", padding=10)
        srcf.pack(fill="x", pady=6)

        self.mode = tk.StringVar(value=self.MODE_IMAGE)
        mode_row = ttk.Frame(srcf)
        mode_row.pack(fill="x")
        ttk.Radiobutton(mode_row, text=self.MODE_IMAGE, variable=self.mode,
                         value=self.MODE_IMAGE, command=self._toggle_mode).pack(side="left")
        ttk.Radiobutton(mode_row, text=self.MODE_TEXT, variable=self.mode,
                         value=self.MODE_TEXT, command=self._toggle_mode).pack(side="left", padx=(16, 0))

        # -- opsi gambar --
        self.image_frame = ttk.Frame(srcf)
        self.image_frame.pack(fill="x", pady=(8, 0))
        self.qr_label = ttk.Label(self.image_frame, text="Belum ada QR dipilih.")
        self.qr_label.pack(side="left")
        ttk.Button(self.image_frame, text="Pilih Gambar QR...", command=self.choose_qr).pack(side="right")

        # -- opsi teks hasil scan --
        self.text_frame = ttk.Frame(srcf)
        ttk.Label(self.text_frame, text="Tempel teks hasil scan QR di sini:").pack(anchor="w", pady=(8, 2))
        txt_wrap = ttk.Frame(self.text_frame)
        txt_wrap.pack(fill="x")
        self.scan_text = tk.Text(txt_wrap, width=80, height=5, wrap="char", font=("Consolas", 9))
        self.scan_text.pack(side="left", fill="x", expand=True)
        sb = ttk.Scrollbar(txt_wrap, orient="vertical", command=self.scan_text.yview)
        sb.pack(side="left", fill="y")
        self.scan_text.configure(yscrollcommand=sb.set)

        self._toggle_mode()

        ttk.Button(self, text="Verifikasi", command=self.on_verify).pack(fill="x", pady=12, ipady=6)

        result_f = ttk.LabelFrame(self, text="Hasil Verifikasi", padding=12)
        result_f.pack(fill="both", expand=True, pady=6)

        self.status_label = ttk.Label(result_f, text="", font=("Segoe UI", 12, "bold"))
        self.status_label.pack(anchor="w", pady=(0, 8))

        self.fields = {}
        for key, label in [
            ("doc_id", "Doc ID"),
            ("signed_by", "Signed by"),
            ("doc_no", "No."),
            ("desc", "Desc"),
            ("time_signature", "Time Signature"),
            ("valid_until", "Valid Until"),
        ]:
            row = ttk.Frame(result_f)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=f"{label}:", width=16, font=("Segoe UI", 10, "bold")).pack(side="left")
            val = ttk.Label(row, text="-")
            val.pack(side="left", fill="x", expand=True)
            self.fields[key] = val

    def load_key(self):
        path = filedialog.askopenfilename(filetypes=[("PEM file", "*.pem")])
        if not path:
            return
        try:
            self.pub_key, self.pub_algo = load_public_key(path)
            self.key_label.config(
                text=f"Key dimuat: {os.path.basename(path)}  ({self.pub_algo})",
                foreground="#0a0")
        except Exception as e:
            messagebox.showerror("Gagal memuat key", str(e))

    def choose_qr(self):
        path = filedialog.askopenfilename(
            filetypes=[("Gambar", "*.png *.jpg *.jpeg *.bmp")])
        if path:
            self.qr_path = path
            self.qr_label.config(text=os.path.basename(path))

    def _toggle_mode(self):
        if self.mode.get() == self.MODE_IMAGE:
            self.text_frame.pack_forget()
            self.image_frame.pack(fill="x", pady=(8, 0))
        else:
            self.image_frame.pack_forget()
            self.text_frame.pack(fill="x", pady=(8, 0))

    def on_verify(self):
        if not self.pub_key:
            messagebox.showwarning("Perhatian", "Silakan load public key terlebih dahulu.")
            return

        if self.mode.get() == self.MODE_IMAGE:
            if not self.qr_path:
                messagebox.showwarning("Perhatian", "Silakan pilih gambar QR terlebih dahulu.")
                return
            content = decode_qr_from_image(self.qr_path)
            if not content:
                self._set_status("QR tidak terbaca / bukan gambar QR yang valid.", "#a33")
                self._clear_fields()
                return
        else:
            content = self.scan_text.get("1.0", "end-1c").strip()
            if not content:
                messagebox.showwarning("Perhatian", "Silakan tempel teks hasil scan QR terlebih dahulu.")
                return

        try:
            envelope = json.loads(content)
            if envelope.get("magic") != MAGIC:
                raise ValueError("Format QR tidak dikenali (bukan QR Signature).")
            algo = envelope["alg"]
            payload = envelope["data"]
            sig = base64.b64decode(envelope["sig"])
        except Exception as e:
            self._set_status(f"Gagal membaca isi QR: {e}", "#a33")
            self._clear_fields()
            return

        if algo != self.pub_algo:
            self._set_status(
                f"Algoritma tidak cocok (QR: {algo}, key dimuat: {self.pub_algo}).", "#a33")
            self._clear_fields()
            return

        data_bytes = canonical_json(payload)
        is_valid_sig = verify_bytes(self.pub_key, algo, data_bytes, sig)

        self._fill_fields(payload)

        if not is_valid_sig:
            self._set_status("TIDAK VALID - tanda tangan tidak cocok / data telah diubah.", "#a33")
            return

        # cek kedaluwarsa jika ada valid_until
        expired = False
        vu_str = payload.get("valid_until", "")
        if vu_str:
            dt, tz_label = parse_dt(vu_str)
            if dt:
                now_utc = datetime.now(timezone.utc)
                if now_utc > dt.astimezone(timezone.utc):
                    expired = True

        if expired:
            self._set_status("KEDALUWARSA - tanda tangan valid, namun sudah melewati Valid Until.", "#c80")
        else:
            self._set_status("VALID - tanda tangan sah dan sesuai.", "#0a0")

    def _fill_fields(self, payload: dict):
        self.fields["doc_id"].config(text=payload.get("doc_id", "-") or "-")
        self.fields["signed_by"].config(text=payload.get("signed_by", "-") or "-")
        self.fields["doc_no"].config(text=payload.get("doc_no", "") or "-")
        self.fields["desc"].config(text=payload.get("desc", "") or "-")
        self.fields["time_signature"].config(text=payload.get("time_signature", "") or "-")
        self.fields["valid_until"].config(text=payload.get("valid_until", "") or "-")

    def _clear_fields(self):
        for lbl in self.fields.values():
            lbl.config(text="-")

    def _set_status(self, text, color):
        self.status_label.config(text=text, foreground=color)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    app = QRSignatureApp()
    app.mainloop()
