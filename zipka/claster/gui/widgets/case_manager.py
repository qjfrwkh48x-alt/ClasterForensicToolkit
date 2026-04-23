"""
Case management widget for forensic investigations.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QGroupBox, QFormLayout, QFileDialog, QMessageBox,
    QTabWidget, QTreeWidget, QTreeWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from claster.core.database import get_db
from claster.core.logger import get_logger

logger = get_logger(__name__)


class CaseManagerWidget(QWidget):
    case_updated = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.current_case = None
        self.db = get_db()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Верхняя панель с информацией о деле
        info_group = QGroupBox("Информация о деле")
        info_layout = QFormLayout()

        self.case_name_label = QLabel("Не открыто")
        self.case_name_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        info_layout.addRow("Название:", self.case_name_label)

        self.examiner_label = QLabel("-")
        info_layout.addRow("Эксперт:", self.examiner_label)

        self.created_label = QLabel("-")
        info_layout.addRow("Создано:", self.created_label)

        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setMaximumHeight(80)
        info_layout.addRow("Описание:", self.description_text)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Вкладки с уликами и цепочкой хранения
        self.tabs = QTabWidget()
        
        # Вкладка улик
        evidence_widget = QWidget()
        evidence_layout = QVBoxLayout()
        
        btn_layout = QHBoxLayout()
        add_evidence_btn = QPushButton("➕ Добавить улику")
        add_evidence_btn.clicked.connect(self.add_evidence)
        import_folder_btn = QPushButton("📁 Импорт папки")
        import_folder_btn.clicked.connect(self.import_folder)
        btn_layout.addWidget(add_evidence_btn)
        btn_layout.addWidget(import_folder_btn)
        btn_layout.addStretch()
        evidence_layout.addLayout(btn_layout)

        self.evidence_table = QTableWidget()
        self.evidence_table.setColumnCount(6)
        self.evidence_table.setHorizontalHeaderLabels([
            "ID", "Имя", "Путь", "Размер", "Хэш (SHA-256)", "Добавлен"
        ])
        self.evidence_table.horizontalHeader().setStretchLastSection(True)
        self.evidence_table.setAlternatingRowColors(True)
        self.evidence_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        evidence_layout.addWidget(self.evidence_table)
        
        evidence_widget.setLayout(evidence_layout)
        self.tabs.addTab(evidence_widget, "📄 Улики")

        # Вкладка цепочки хранения
        custody_widget = QWidget()
        custody_layout = QVBoxLayout()
        
        add_custody_btn = QPushButton("➕ Добавить запись")
        add_custody_btn.clicked.connect(self.add_custody_entry)
        custody_layout.addWidget(add_custody_btn)
        
        self.custody_tree = QTreeWidget()
        self.custody_tree.setHeaderLabels(["Дата/Время", "Действие", "От кого", "Кому", "Примечания"])
        self.custody_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        custody_layout.addWidget(self.custody_tree)
        
        custody_widget.setLayout(custody_layout)
        self.tabs.addTab(custody_widget, "🔗 Цепочка хранения")

        # Вкладка заметок
        notes_widget = QWidget()
        notes_layout = QVBoxLayout()
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Введите заметки по делу...")
        save_notes_btn = QPushButton("💾 Сохранить заметки")
        save_notes_btn.clicked.connect(self.save_notes)
        notes_layout.addWidget(self.notes_edit)
        notes_layout.addWidget(save_notes_btn)
        notes_widget.setLayout(notes_layout)
        self.tabs.addTab(notes_widget, "📝 Заметки")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def create_case(self, case_info: dict):
        """Создаёт новое дело."""
        self.current_case = case_info
        self.case_name_label.setText(case_info.get('name', 'Без названия'))
        self.examiner_label.setText(case_info.get('examiner', 'Не указан'))
        self.created_label.setText(datetime.now().strftime('%Y-%m-%d %H:%M'))
        self.description_text.setText(case_info.get('description', ''))
        
        # Создаём запись в БД
        try:
            with self.db.get_connection() as conn:
                conn.execute("""
                    INSERT INTO cases (case_name, examiner, description, created_at)
                    VALUES (?, ?, ?, ?)
                """, (case_info['name'], case_info.get('examiner'), 
                      case_info.get('description'), datetime.now().isoformat()))
            self.case_updated.emit(case_info)
            logger.info(f"Дело создано: {case_info['name']}")
        except Exception as e:
            logger.error(f"Ошибка создания дела: {e}")

    def add_evidence(self):
        """Добавляет файл улики в дело."""
        if not self.current_case:
            QMessageBox.warning(self, "Ошибка", "Сначала создайте или откройте дело.")
            return

        files, _ = QFileDialog.getOpenFileNames(
            self, "Выберите файлы улик", "", "Все файлы (*.*)"
        )
        for file_path in files:
            self._add_evidence_file(file_path)

    def _add_evidence_file(self, file_path: str):
        """Добавляет один файл в таблицу улик."""
        from claster.core.hashing import compute_hash
        
        path = Path(file_path)
        size = path.stat().st_size
        file_hash = compute_hash(file_path, 'sha256')
        
        row = self.evidence_table.rowCount()
        self.evidence_table.insertRow(row)
        self.evidence_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.evidence_table.setItem(row, 1, QTableWidgetItem(path.name))
        self.evidence_table.setItem(row, 2, QTableWidgetItem(str(path)))
        self.evidence_table.setItem(row, 3, QTableWidgetItem(self._format_size(size)))
        self.evidence_table.setItem(row, 4, QTableWidgetItem(file_hash[:16] + "..."))
        self.evidence_table.setItem(row, 5, QTableWidgetItem(datetime.now().strftime('%Y-%m-%d %H:%M')))

    def _format_size(self, size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    def import_folder(self):
        """Импортирует все файлы из папки."""
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку с уликами")
        if folder:
            for root, dirs, files in os.walk(folder):
                for file in files:
                    self._add_evidence_file(os.path.join(root, file))

    def add_custody_entry(self):
        """Добавляет запись в цепочку хранения."""
        from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QDateTimeEdit, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить запись цепочки хранения")
        layout = QFormLayout(dialog)
        
        action_edit = QLineEdit()
        layout.addRow("Действие:", action_edit)
        
        from_edit = QLineEdit()
        layout.addRow("От кого:", from_edit)
        
        to_edit = QLineEdit()
        layout.addRow("Кому:", to_edit)
        
        notes_edit = QLineEdit()
        layout.addRow("Примечания:", notes_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec():
            item = QTreeWidgetItem([
                datetime.now().strftime('%Y-%m-%d %H:%M'),
                action_edit.text(),
                from_edit.text(),
                to_edit.text(),
                notes_edit.text()
            ])
            self.custody_tree.addTopLevelItem(item)

    def save_notes(self):
        """Сохраняет заметки по делу."""
        notes = self.notes_edit.toPlainText()
        logger.info(f"Заметки сохранены: {len(notes)} символов")
        QMessageBox.information(self, "Сохранено", "Заметки успешно сохранены.")