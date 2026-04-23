"""
Evidence viewer widget with metadata display.
"""

import os
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QTableWidget, QTableWidgetItem, QPushButton, QGroupBox,
    QFormLayout, QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont

from claster.core.hashing import compute_hash
from claster.metadata.exif import get_exif
from claster.metadata.office import get_office_metadata


class EvidenceViewerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Информация о файле
        info_group = QGroupBox("Информация о файле")
        info_layout = QFormLayout()
        
        self.lbl_name = QLabel("-")
        self.lbl_name.setWordWrap(True)
        info_layout.addRow("Имя:", self.lbl_name)
        
        self.lbl_path = QLabel("-")
        self.lbl_path.setWordWrap(True)
        info_layout.addRow("Путь:", self.lbl_path)
        
        self.lbl_size = QLabel("-")
        info_layout.addRow("Размер:", self.lbl_size)
        
        self.lbl_modified = QLabel("-")
        info_layout.addRow("Изменён:", self.lbl_modified)
        
        self.lbl_created = QLabel("-")
        info_layout.addRow("Создан:", self.lbl_created)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Хэши
        hash_group = QGroupBox("Криптографические хэши")
        hash_layout = QFormLayout()
        
        self.lbl_md5 = QLabel("-")
        self.lbl_md5.setFont(QFont("Courier New", 9))
        hash_layout.addRow("MD5:", self.lbl_md5)
        
        self.lbl_sha1 = QLabel("-")
        self.lbl_sha1.setFont(QFont("Courier New", 9))
        hash_layout.addRow("SHA-1:", self.lbl_sha1)
        
        self.lbl_sha256 = QLabel("-")
        self.lbl_sha256.setFont(QFont("Courier New", 9))
        self.lbl_sha256.setWordWrap(True)
        hash_layout.addRow("SHA-256:", self.lbl_sha256)
        
        hash_group.setLayout(hash_layout)
        layout.addWidget(hash_group)

        # Метаданные
        self.metadata_group = QGroupBox("Метаданные")
        self.metadata_layout = QFormLayout()
        self.metadata_group.setLayout(self.metadata_layout)
        layout.addWidget(self.metadata_group)

        # Предпросмотр изображений
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMaximumHeight(300)
        self.image_label.setStyleSheet("background-color: #2d2d2d;")
        layout.addWidget(self.image_label)

        # Кнопки действий
        btn_layout = QHBoxLayout()
        self.btn_analyze = QPushButton("🔍 Анализировать")
        self.btn_analyze.clicked.connect(self.analyze_file)
        self.btn_export = QPushButton("📤 Экспортировать")
        self.btn_export.clicked.connect(self.export_file)
        self.btn_carve = QPushButton("🔪 Восстановить (Carve)")
        self.btn_carve.clicked.connect(self.carve_file)
        
        btn_layout.addWidget(self.btn_analyze)
        btn_layout.addWidget(self.btn_export)
        btn_layout.addWidget(self.btn_carve)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()
        self.setLayout(layout)

    def load_file(self, file_path: str):
        """Загружает информацию о файле."""
        self.current_file = file_path
        path = Path(file_path)
        
        if not path.exists():
            return

        stat = path.stat()
        self.lbl_name.setText(path.name)
        self.lbl_path.setText(str(path))
        self.lbl_size.setText(self._format_size(stat.st_size))
        self.lbl_modified.setText(datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'))
        self.lbl_created.setText(datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'))

        # Вычисляем хэши в фоне (можно добавить QThread)
        try:
            self.lbl_md5.setText(compute_hash(file_path, 'md5'))
            self.lbl_sha1.setText(compute_hash(file_path, 'sha1'))
            self.lbl_sha256.setText(compute_hash(file_path, 'sha256'))
        except Exception as e:
            self.lbl_sha256.setText(f"Ошибка: {e}")

        # Извлекаем метаданные в зависимости от типа файла
        self._extract_metadata(file_path)

        # Предпросмотр изображений
        ext = path.suffix.lower()
        if ext in ('.png', '.jpg', '.jpeg', '.bmp', '.gif'):
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                scaled = pixmap.scaledToHeight(280, Qt.TransformationMode.SmoothTransformation)
                self.image_label.setPixmap(scaled)
            else:
                self.image_label.setText("Не удалось загрузить изображение")
        else:
            self.image_label.clear()

    def _extract_metadata(self, file_path: str):
        """Извлекает метаданные в зависимости от типа файла."""
        # Очищаем предыдущие метаданные
        while self.metadata_layout.count():
            item = self.metadata_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        path = Path(file_path)
        ext = path.suffix.lower()

        try:
            if ext in ('.jpg', '.jpeg', '.png', '.tiff', '.bmp'):
                exif = get_exif(file_path)
                for key, value in list(exif.items())[:10]:
                    self.metadata_layout.addRow(f"{key}:", QLabel(str(value)))
            elif ext in ('.docx', '.doc'):
                meta = get_office_metadata(file_path)
                for key, value in meta.items():
                    self.metadata_layout.addRow(f"{key}:", QLabel(str(value)))
            else:
                self.metadata_layout.addRow("Тип:", QLabel("Метаданные не поддерживаются"))
        except Exception as e:
            self.metadata_layout.addRow("Ошибка:", QLabel(str(e)))

    def _format_size(self, size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    def analyze_file(self):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Анализ", f"Запуск анализа файла: {self.current_file}")

    def export_file(self):
        from PyQt6.QtWidgets import QFileDialog
        dest, _ = QFileDialog.getSaveFileName(self, "Экспорт файла", self.current_file)
        if dest:
            import shutil
            shutil.copy2(self.current_file, dest)

    def carve_file(self):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Carving", "Функция восстановления файлов будет доступна в следующей версии.")