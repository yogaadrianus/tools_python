# Number converter: denary, binary, hexadecimal, BCD

import tkinter as tk
from tkinter import messagebox

# Mengaktifkan HiDPI agar tampilan tulisan tajam di layar/proyektor resolusi tinggi
try:
    from ctypes import windll
    windll.shcore.SetProcessDPIAwareness(1)
except Exception:
    pass

class NumberConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Number System Converter (Denary, Binary, Hexadecimal, BCD)")
        self.root.geometry("850x650")
        self.root.configure(bg="#F4F6F9")

        # Konfigurasi Font Besar untuk Tampilan Kelas
        self.label_font = ("Helvetica", 14, "bold")
        self.entry_font = ("Consolas", 24, "bold")  # Font monospaced agar angka sejajar
        self.button_font = ("Helvetica", 14, "bold")

        # Variabel lacak input terakhir yang aktif
        self.last_focused = None

        self.setup_ui()

    def setup_ui(self):
        # Header / Judul
        title_label = tk.Label(
            self.root, 
            text="NUMBER SYSTEM CONVERTER", 
            font=("Helvetica", 20, "bold"), 
            bg="#F4F6F9", 
            fg="#2C3E50"
        )
        title_label.pack(pady=(20, 10))

        subtitle_label = tk.Label(
            self.root, 
            text="denary - binary - hexadecimal - BCD", 
            font=("Helvetica", 11, "italic"), 
            bg="#F4F6F9", 
            fg="#7F8C8D"
        )
        subtitle_label.pack(pady=(0, 20))

        # Container Frame Input (DISETEL padx=40)
        input_frame = tk.Frame(self.root, bg="#F4F6F9")
        input_frame.pack(fill="x", padx=40)

        # 1. Denary (Decimal)
        tk.Label(input_frame, text="Denary:", font=self.label_font, bg="#F4F6F9", fg="#2980B9").pack(anchor="w")
        self.den_entry = tk.Entry(input_frame, font=self.entry_font, bg="#FFFFFF", fg="#2C3E50", bd=2, relief="solid")
        self.den_entry.pack(fill="x", pady=(5, 15), ipady=8)
        self.attach_field_events(self.den_entry, "den")

        # 2. Binary
        tk.Label(input_frame, text="Binary:", font=self.label_font, bg="#F4F6F9", fg="#27AE60").pack(anchor="w")
        self.bin_entry = tk.Entry(input_frame, font=self.entry_font, bg="#FFFFFF", fg="#2C3E50", bd=2, relief="solid")
        self.bin_entry.pack(fill="x", pady=(5, 15), ipady=8)
        self.attach_field_events(self.bin_entry, "bin")

        # 3. Hexadecimal
        tk.Label(input_frame, text="Hexadecimal:", font=self.label_font, bg="#F4F6F9", fg="#8E44AD").pack(anchor="w")
        self.hex_entry = tk.Entry(input_frame, font=self.entry_font, bg="#FFFFFF", fg="#2C3E50", bd=2, relief="solid")
        self.hex_entry.pack(fill="x", pady=(5, 15), ipady=8)
        self.attach_field_events(self.hex_entry, "hex")

        # 4. BCD (Binary Coded Decimal)
        tk.Label(input_frame, text="BCD (Binary Coded Decimal):", font=self.label_font, bg="#F4F6F9", fg="#D35400").pack(anchor="w")
        self.bcd_entry = tk.Entry(input_frame, font=self.entry_font, bg="#FFFFFF", fg="#2C3E50", bd=2, relief="solid")
        self.bcd_entry.pack(fill="x", pady=(5, 20), ipady=8)
        self.attach_field_events(self.bcd_entry, "bcd")

        # Container Frame Tombol (DISETEL padx=40)
        btn_frame = tk.Frame(self.root, bg="#F4F6F9")
        btn_frame.pack(fill="x", padx=40)

        # Tombol Convert
        self.btn_convert = tk.Button(
            btn_frame, 
            text="CONVERT (Enter)", 
            font=self.button_font, 
            bg="#2980B9", 
            fg="white", 
            activebackground="#1F618D", 
            activeforeground="white",
            bd=0, 
            cursor="hand2",
            command=self.convert
        )
        self.btn_convert.pack(side="left", expand=True, fill="x", padx=(0, 10), ipady=10)

        # Tombol Clear
        self.btn_clear = tk.Button(
            btn_frame, 
            text="CLEAR (Esc)", 
            font=self.button_font, 
            bg="#E74C3C", 
            fg="white", 
            activebackground="#C0392B", 
            activeforeground="white",
            bd=0, 
            cursor="hand2",
            command=self.clear_all
        )
        self.btn_clear.pack(side="right", expand=True, fill="x", padx=(10, 0), ipady=10)

        # Global Keyboard Binds
        self.root.bind("<Return>", lambda e: self.convert())
        self.root.bind("<Escape>", lambda e: self.clear_all())

        # Set fokus awal pada input Denary
        self.den_entry.focus_set()
        self.last_focused = "den"

    def attach_field_events(self, entry_widget, field_type):
        """Mendaftarkan event fokus dan menu klik kanan pada Entry."""
        entry_widget.bind("<FocusIn>", lambda e: self.set_focused(field_type))
        self.add_context_menu(entry_widget)

    def set_focused(self, field_type):
        self.last_focused = field_type

    def add_context_menu(self, widget):
        """Menambahkan Popup Menu Klik Kanan (Cut, Copy, Paste, Select All)."""
        menu = tk.Menu(widget, tearoff=0, font=("Helvetica", 11))
        menu.add_command(label="Cut", command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_command(label="Copy", command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label="Paste", command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Select All", command=lambda: self.select_all(widget))

        def show_popup(event):
            widget.focus_set()
            menu.tk_popup(event.x_root, event.y_root)

        # Mengakomodasi Windows, Linux (<Button-3>) dan macOS (<Button-2>)
        widget.bind("<Button-3>", show_popup)
        widget.bind("<Button-2>", show_popup)

    def select_all(self, widget):
        widget.select_range(0, tk.END)
        widget.icursor(tk.END)
        return "break"

    @staticmethod
    def decimal_to_bcd(val):
        """Mengubah bilangan bulat non-negatif menjadi string BCD (4 bit per digit, dipisah spasi)."""
        digits = str(val)
        nibbles = [format(int(d), "04b") for d in digits]
        return " ".join(nibbles)

    @staticmethod
    def bcd_to_decimal(raw_val):
        """Mengubah string BCD menjadi bilangan bulat. Melempar ValueError jika tidak valid."""
        cleaned = raw_val.replace(" ", "")
        if not cleaned:
            raise ValueError("empty")
        if len(cleaned) % 4 != 0:
            raise ValueError("BCD length must be a multiple of 4 bits per digit")
        if any(ch not in "01" for ch in cleaned):
            raise ValueError("BCD may only contain 0s and 1s")

        digits = []
        for i in range(0, len(cleaned), 4):
            nibble = cleaned[i:i + 4]
            digit_val = int(nibble, 2)
            if digit_val > 9:
                # Nibble represents an invalid BCD digit (A-F range, 1010-1111)
                raise ValueError(f"Nibble '{nibble}' is not a valid BCD digit (0000-1001)")
            digits.append(str(digit_val))

        return int("".join(digits))

    def convert(self):
        """Logika Utama Konversi Bilangan."""
        if not self.last_focused:
            if self.den_entry.get(): self.last_focused = "den"
            elif self.bin_entry.get(): self.last_focused = "bin"
            elif self.hex_entry.get(): self.last_focused = "hex"
            elif self.bcd_entry.get(): self.last_focused = "bcd"
            else: self.last_focused = "den"

        try:
            if self.last_focused == "den":
                raw_val = self.den_entry.get().strip()
                if not raw_val: return
                val = int(raw_val, 10)

            elif self.last_focused == "bin":
                raw_val = self.bin_entry.get().strip().replace(" ", "")
                if raw_val.startswith("0b") or raw_val.startswith("0B"):
                    raw_val = raw_val[2:]
                if not raw_val: return
                val = int(raw_val, 2)

            elif self.last_focused == "hex":
                raw_val = self.hex_entry.get().strip().replace(" ", "")
                if raw_val.startswith("0x") or raw_val.startswith("0X"):
                    raw_val = raw_val[2:]
                if not raw_val: return
                val = int(raw_val, 16)

            elif self.last_focused == "bcd":
                raw_val = self.bcd_entry.get().strip()
                if not raw_val: return
                val = self.bcd_to_decimal(raw_val)

            if val < 0:
                messagebox.showerror("Error", "Program ini saat ini khusus untuk bilangan bulat positif / non-negatif.")
                return

            self.update_entries(val)

        except ValueError as e:
            if self.last_focused == "bcd":
                messagebox.showerror(
                    "Input Tidak Valid",
                    f"Nilai BCD tidak valid: {e}\n\n"
                    "Gunakan 4 bit per digit desimal, contoh: 0010 0101 (untuk 25)."
                )
            else:
                messagebox.showerror(
                    "Input Tidak Valid", 
                    f"Karakter yang Anda masukkan di kolom '{self.last_focused.upper()}' bukan format angka yang benar."
                )

    def update_entries(self, val):
        """Memasukkan hasil konversi ke dalam tiap-tiap Entry box."""
        self.den_entry.delete(0, tk.END)
        self.den_entry.insert(0, str(val))

        self.bin_entry.delete(0, tk.END)
        self.bin_entry.insert(0, bin(val)[2:])

        self.hex_entry.delete(0, tk.END)
        self.hex_entry.insert(0, hex(val)[2:].upper())

        self.bcd_entry.delete(0, tk.END)
        self.bcd_entry.insert(0, self.decimal_to_bcd(val))

    def clear_all(self):
        """Membersihkan seluruh bidang input."""
        self.den_entry.delete(0, tk.END)
        self.bin_entry.delete(0, tk.END)
        self.hex_entry.delete(0, tk.END)
        self.bcd_entry.delete(0, tk.END)
        self.den_entry.focus_set()
        self.last_focused = "den"

if __name__ == "__main__":
    root = tk.Tk()
    app = NumberConverterApp(root)
    root.mainloop()
