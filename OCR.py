import sys
import os
import pytesseract
from PIL import Image, ImageGrab
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QFileDialog, QMessageBox, QFrame, QSplitter
)
from PySide6.QtGui import QPixmap, QFont, QKeySequence, QShortcut
from PySide6.QtCore import Qt

# --- TESSERACT CONFIGURATION ---
# If Tesseract is not added to your system PATH (especially on Windows),
# uncomment and set the exact path to tesseract.exe below:
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


class OCRApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OCR Text Extractor (Image & Clipboard)")
        self.resize(1100, 700)
        self.setStyleSheet("background-color: #F4F6F9;")

        self.current_image = None
        self.setup_ui()

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(15)

        # Header Title
        title_label = QLabel("OCR TEXT EXTRACTOR")
        title_label.setFont(QFont("Helvetica", 20, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #2C3E50;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        subtitle_label = QLabel("Upload an image or paste from clipboard to extract text.")
        subtitle_label.setFont(QFont("Helvetica", 11, QFont.Weight.Normal))
        subtitle_label.setStyleSheet("color: #7F8C8D;")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(subtitle_label)

        # Splitter to separate Image Preview and Extracted Text
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Panel: Image Preview Area
        left_box = QFrame()
        left_box.setFrameShape(QFrame.Shape.StyledPanel)
        left_box.setStyleSheet("background-color: #FFFFFF; border: 1px solid #BDC3C7; border-radius: 8px;")
        left_layout = QVBoxLayout(left_box)

        preview_header = QLabel("IMAGE PREVIEW")
        preview_header.setFont(QFont("Helvetica", 12, QFont.Weight.Bold))
        preview_header.setStyleSheet("color: #2980B9; border: none;")
        left_layout.addWidget(preview_header)

        self.image_label = QLabel("No image loaded.\nUpload a file or paste from clipboard.")
        self.image_label.setFont(QFont("Helvetica", 12))
        self.image_label.setStyleSheet("color: #95A5A6; border: 2px dashed #BDC3C7; border-radius: 5px;")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(False)
        left_layout.addWidget(self.image_label)

        splitter.addWidget(left_box)

        # Right Panel: Text Display Area
        right_box = QFrame()
        right_box.setFrameShape(QFrame.Shape.StyledPanel)
        right_box.setStyleSheet("background-color: #FFFFFF; border: 1px solid #BDC3C7; border-radius: 8px;")
        right_layout = QVBoxLayout(right_box)

        text_header = QLabel("EXTRACTED TEXT")
        text_header.setFont(QFont("Helvetica", 12, QFont.Weight.Bold))
        text_header.setStyleSheet("color: #27AE60; border: none;")
        right_layout.addWidget(text_header)

        # Text Area with Large Font for Presentation Display
        self.text_area = QTextEdit()
        self.text_area.setFont(QFont("Consolas", 18))  # Large font size
        self.text_area.setPlaceholderText("Extracted text will appear here...")
        self.text_area.setStyleSheet("border: none;")
        right_layout.addWidget(self.text_area)

        splitter.addWidget(right_box)
        splitter.setSizes([450, 550])
        main_layout.addWidget(splitter)

        # Button Controls Layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        # Upload Button
        self.btn_upload = QPushButton("📁 Upload Image")
        self.btn_upload.setFont(QFont("Helvetica", 12, QFont.Weight.Bold))
        self.btn_upload.setStyleSheet(self.get_button_style("#2980B9", "#1F618D"))
        self.btn_upload.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_upload.clicked.connect(self.upload_image)
        btn_layout.addWidget(self.btn_upload)

        # Paste Button
        self.btn_paste = QPushButton("📋 Paste Clipboard")
        self.btn_paste.setFont(QFont("Helvetica", 12, QFont.Weight.Bold))
        self.btn_paste.setStyleSheet(self.get_button_style("#8E44AD", "#703688"))
        self.btn_paste.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_paste.clicked.connect(self.paste_image)
        btn_layout.addWidget(self.btn_paste)

        # Run OCR Button
        self.btn_ocr = QPushButton("⚙️ Extract Text")
        self.btn_ocr.setFont(QFont("Helvetica", 12, QFont.Weight.Bold))
        self.btn_ocr.setStyleSheet(self.get_button_style("#27AE60", "#1E8449"))
        self.btn_ocr.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ocr.clicked.connect(self.process_ocr)
        btn_layout.addWidget(self.btn_ocr)

        # Clear Button
        self.btn_clear = QPushButton("🧹 Clear All")
        self.btn_clear.setFont(QFont("Helvetica", 12, QFont.Weight.Bold))
        self.btn_clear.setStyleSheet(self.get_button_style("#E74C3C", "#C0392B"))
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.clicked.connect(self.clear_all)
        btn_layout.addWidget(self.btn_clear)

        main_layout.addLayout(btn_layout)

        # Global Keyboard Shortcut: Ctrl+V anywhere pastes image
        self.shortcut_paste = QShortcut(QKeySequence.StandardKey.Paste, self)
        self.shortcut_paste.activated.connect(self.paste_image)

    def get_button_style(self, bg_color, hover_color):
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: white;
                border-radius: 6px;
                padding: 12px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
        """

    def display_image(self, pil_image):
        """Displays PIL Image in the GUI while retaining aspect ratio."""
        self.current_image = pil_image

        # Convert PIL Image to QPixmap for rendering
        temp_path = "_temp_ocr_display.png"
        pil_image.save(temp_path)
        pixmap = QPixmap(temp_path)
        
        # Scale pixmap smoothly to fit container
        scaled_pixmap = pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)

        if os.path.exists(temp_path):
            os.remove(temp_path)

    def upload_image(self):
        """Opens file dialog to select an image file."""
        file_filter = "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff *.webp)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image File", "", file_filter)

        if file_path:
            try:
                img = Image.open(file_path)
                self.display_image(img)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load image:\n{str(e)}")

    def paste_image(self):
        """Retrieves image directly from system clipboard."""
        try:
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                self.display_image(img)
            else:
                QMessageBox.warning(self, "Clipboard Empty", "No image found in clipboard.\nPlease copy an image or take a screenshot first.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to access clipboard:\n{str(e)}")

    def process_ocr(self):
        """Executes pytesseract OCR on the currently loaded image."""
        if self.current_image is None:
            QMessageBox.warning(self, "No Image Loaded", "Please upload or paste an image first.")
            return

        try:
            # Perform OCR recognition
            extracted_text = pytesseract.image_to_string(self.current_image)

            if not extracted_text.strip():
                self.text_area.setText("[No readable text was detected in the image.]")
            else:
                self.text_area.setText(extracted_text.strip())

        except Exception as e:
            QMessageBox.critical(
                self, 
                "Tesseract OCR Error", 
                f"An error occurred during text extraction:\n{str(e)}\n\n"
                "Please verify that Tesseract OCR is installed on your operating system."
            )

    def clear_all(self):
        """Resets the UI back to initial state."""
        self.current_image = None
        self.image_label.clear()
        self.image_label.setText("No image loaded.\nUpload a file or paste from clipboard.")
        self.text_area.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OCRApp()
    window.show()
    sys.exit(app.exec())
