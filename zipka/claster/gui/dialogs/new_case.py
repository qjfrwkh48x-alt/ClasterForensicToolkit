"""
New case creation dialog.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QDialogButtonBox, QFileDialog, QPushButton, QHBoxLayout, QLabel
)
from PyQt6.QtCore import QDir
from datetime import datetime


class NewCaseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создание нового дела")
        self.setMinimumWidth(500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Например: Расследование_2024-001")
        form.addRow("Название дела:", self.name_edit)

        self.examiner_edit = QLineEdit()
        self.examiner_edit.setPlaceholderText("ФИО эксперта")
        form.addRow("Эксперт:", self.examiner_edit)

        # Директория дела
        dir_layout = QHBoxLayout()
        self.dir_edit = QLineEdit()
        self.dir_edit.setText(QDir.homePath() + "/ClasterCases")
        browse_btn = QPushButton("Обзор")
        browse_btn.clicked.connect(self.browse_directory)
        dir_layout.addWidget(self.dir_edit)
        dir_layout.addWidget(browse_btn)
        form.addRow("Директория:", dir_layout)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Краткое описание дела...")
        self.desc_edit.setMaximumHeight(100)
        form.addRow("Описание:", self.desc_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def browse_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Выберите директорию для дела")
        if dir_path:
            self.dir_edit.setText(dir_path)

    def get_case_info(self) -> dict:
        return {
            'name': self.name_edit.text() or f"Дело_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'examiner': self.examiner_edit.text() or "Не указан",
            'directory': self.dir_edit.text(),
            'description': self.desc_edit.toPlainText(),
            'created': datetime.now().isoformat()
        }