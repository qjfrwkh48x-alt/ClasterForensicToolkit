"""
HEX viewer widget.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QScrollBar
from PyQt6.QtGui import QFont, QTextCursor, QColor
from PyQt6.QtCore import Qt, QFile, QIODevice

class HexViewerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.data = b""

    def setup_ui(self):
        layout = QHBoxLayout()
        
        # HEX область
        self.hex_view = QTextEdit()
        self.hex_view.setFont(QFont("Courier New", 10))
        self.hex_view.setReadOnly(True)
        self.hex_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        
        # ASCII область
        self.ascii_view = QTextEdit()
        self.ascii_view.setFont(QFont("Courier New", 10))
        self.ascii_view.setReadOnly(True)
        self.ascii_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.ascii_view.setMaximumWidth(200)
        
        # Синхронизация скроллов
        self.hex_scroll = self.hex_view.verticalScrollBar()
        self.ascii_scroll = self.ascii_view.verticalScrollBar()
        self.hex_scroll.valueChanged.connect(self.ascii_scroll.setValue)
        self.ascii_scroll.valueChanged.connect(self.hex_scroll.setValue)
        
        layout.addWidget(self.hex_view)
        layout.addWidget(self.ascii_view)
        self.setLayout(layout)

    def open_file(self, path: str):
        try:
            with open(path, 'rb') as f:
                self.data = f.read(10 * 1024 * 1024)  # Читаем первые 10 МБ
            self.display_data()
        except Exception as e:
            self.hex_view.setText(f"Ошибка открытия файла: {e}")

    def display_data(self):
        if not self.data:
            return
        
        hex_lines = []
        ascii_lines = []
        for i in range(0, len(self.data), 16):
            chunk = self.data[i:i+16]
            hex_part = ' '.join(f'{b:02x}' for b in chunk)
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            hex_lines.append(f"{i:08x}  {hex_part:<48}")
            ascii_lines.append(ascii_part)
        
        self.hex_view.setText('\n'.join(hex_lines))
        self.ascii_view.setText('\n'.join(ascii_lines))