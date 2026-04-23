"""
Dialog for configuring report generation.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QHBoxLayout, QDialogButtonBox, QFileDialog, QTextEdit, QLabel
)
import json


class ReportDialog(QDialog):
    def __init__(self, parent=None, func_name=""):
        super().__init__(parent)
        self.func_name = func_name
        self.setWindowTitle("Параметры отчёта")
        self.setMinimumWidth(500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        form = QFormLayout()

        # Data file selection
        self.data_file_edit = QLineEdit()
        data_btn = QPushButton("Обзор")
        data_btn.clicked.connect(self._browse_data_file)
        data_layout = QHBoxLayout()
        data_layout.addWidget(self.data_file_edit)
        data_layout.addWidget(data_btn)
        form.addRow("Файл с данными (JSON):", data_layout)

        # Or manual data entry
        form.addRow(QLabel("Или введите данные вручную:"))
        self.data_text = QTextEdit()
        self.data_text.setPlaceholderText('{"case_name": "Test", "examiner": "John", ...}')
        form.addRow(self.data_text)

        # Output file
        self.output_edit = QLineEdit()
        output_btn = QPushButton("Обзор")
        output_btn.clicked.connect(self._browse_output_file)
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_edit)
        output_layout.addWidget(output_btn)
        form.addRow("Сохранить как:", output_layout)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def _browse_data_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите JSON файл", "", "JSON (*.json)")
        if path:
            self.data_file_edit.setText(path)

    def _browse_output_file(self):
        ext_map = {
            "generate_html_report": "HTML (*.html)",
            "generate_pdf_report": "PDF (*.pdf)",
            "generate_docx_report": "DOCX (*.docx)",
            "generate_csv_report": "CSV (*.csv)",
            "generate_json_report": "JSON (*.json)",
        }
        file_filter = ext_map.get(self.func_name, "Все файлы (*.*)")
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить отчёт", "", file_filter)
        if path:
            self.output_edit.setText(path)

    def get_parameters(self):
        data = None
        if self.data_file_edit.text():
            try:
                with open(self.data_file_edit.text(), 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                data = {"error": f"Failed to load JSON: {e}"}
        elif self.data_text.toPlainText().strip():
            try:
                data = json.loads(self.data_text.toPlainText().strip())
            except Exception as e:
                data = {"error": f"Invalid JSON: {e}"}
        else:
            data = {"case_name": "Default", "examiner": "Claster"}

        output = self.output_edit.text()
        return {"data": data, "output": output}