"""
Красивый диалог ввода аргументов функций на русском языке.
"""

import inspect
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QComboBox, QDialogButtonBox, QFileDialog, QPushButton, QHBoxLayout,
    QTextEdit, QWidget, QLabel, QScrollArea, QFrame, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Переводы типов аргументов
TYPE_NAMES = {
    'str': 'Строка',
    'int': 'Целое число',
    'float': 'Дробное число',
    'bool': 'Да/Нет',
    'list': 'Список',
    'Path': 'Путь',
    'dict': 'Словарь',
}


class FunctionArgsDialog(QDialog):
    def __init__(self, func, parent=None):
        super().__init__(parent)
        self.func = func
        self.setWindowTitle(f"Аргументы функции: {func.__name__}")
        self.setMinimumWidth(550)
        self.setMinimumHeight(400)
        self.inputs = {}
        self.setup_ui()
        
        # Применяем стиль
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 10pt;
            }
            QGroupBox {
                color: #e94560;
                font-weight: bold;
                border: 1px solid #0f3460;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit {
                background-color: #0f0f1a;
                color: #e0e0e0;
                border: 1px solid #0f3460;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton {
                background-color: #0f3460;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1a4a7a;
            }
            QCheckBox {
                color: #e0e0e0;
            }
            QDialogButtonBox QPushButton {
                min-width: 100px;
                padding: 8px 16px;
            }
            QDialogButtonBox QPushButton:first-child {
                background-color: #0d7377;
            }
            QDialogButtonBox QPushButton:first-child:hover {
                background-color: #14a085;
            }
        """)

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(12)
        
        # Заголовок с описанием
        doc = inspect.getdoc(self.func)
        if doc:
            desc_label = QLabel(doc.split('\n')[0] if doc else "")
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #888; font-style: italic; padding: 8px;")
            main_layout.addWidget(desc_label)

        # Скроллируемая область для аргументов
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        scroll_widget = QWidget()
        form = QFormLayout(scroll_widget)
        form.setSpacing(10)
        form.setContentsMargins(10, 10, 10, 10)

        sig = inspect.signature(self.func)
        for name, param in sig.parameters.items():
            if name in ('self', 'cls', 'callback'):
                continue
            
            # Группа для каждого аргумента
            group = QGroupBox()
            group_layout = QVBoxLayout()
            
            # Заголовок с типом
            type_name = self._get_type_name(param)
            header = QLabel(f"{name} <span style='color: #0d7377;'>({type_name})</span>")
            header.setStyleSheet("font-weight: bold;")
            group_layout.addWidget(header)
            
            # Виджет ввода
            widget = self._create_widget(name, param)
            group_layout.addWidget(widget)
            
            # Подсказка из аннотации
            if param.annotation != inspect.Parameter.empty:
                hint = QLabel(f"Тип: {self._get_full_type_name(param.annotation)}")
                hint.setStyleSheet("color: #666; font-size: 9pt;")
                group_layout.addWidget(hint)
            
            group.setLayout(group_layout)
            form.addRow(group)
            self.inputs[name] = widget

        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("✓ Запустить")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("✗ Отмена")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

        self.setLayout(main_layout)

    def _get_type_name(self, param: inspect.Parameter) -> str:
        """Возвращает читаемое имя типа параметра."""
        if param.annotation != inspect.Parameter.empty:
            if hasattr(param.annotation, '__name__'):
                return TYPE_NAMES.get(param.annotation.__name__, param.annotation.__name__)
            return str(param.annotation)
        if param.default != inspect.Parameter.empty:
            type_name = type(param.default).__name__
            return TYPE_NAMES.get(type_name, type_name)
        return "строка"

    def _get_full_type_name(self, annotation) -> str:
        """Возвращает полное имя типа."""
        if hasattr(annotation, '__name__'):
            return annotation.__name__
        return str(annotation)

    def _create_widget(self, name: str, param: inspect.Parameter):
        """Создаёт подходящий виджет для параметра."""
        annotation = param.annotation
        default = param.default
        
        # Определяем тип
        if annotation != inspect.Parameter.empty:
            param_type = annotation
        elif default != inspect.Parameter.empty:
            param_type = type(default)
        else:
            param_type = str

        # Создаём виджет в зависимости от типа
        if param_type == bool:
            w = QCheckBox()
            if default != inspect.Parameter.empty:
                w.setChecked(default)
            w.setText("Да" if w.isChecked() else "Нет")
            w.stateChanged.connect(lambda state: w.setText("Да" if state else "Нет"))
            
        elif param_type == int:
            w = QSpinBox()
            w.setRange(-999999, 999999)
            if default != inspect.Parameter.empty:
                w.setValue(default)
            w.setToolTip(f"Введите целое число")
            
        elif param_type == float:
            w = QDoubleSpinBox()
            w.setRange(-999999.0, 999999.0)
            w.setSingleStep(0.1)
            w.setDecimals(6)
            if default != inspect.Parameter.empty:
                w.setValue(default)
            w.setToolTip(f"Введите дробное число")
            
        elif param_type == list:
            w = QTextEdit()
            w.setPlaceholderText("Введите элементы списка, каждый с новой строки...")
            w.setMaximumHeight(120)
            if default != inspect.Parameter.empty and isinstance(default, list):
                w.setText("\n".join(str(x) for x in default))
                
        elif param_type == Path or (hasattr(param_type, '__name__') and 'Path' in param_type.__name__):
            container = QWidget()
            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            
            line = QLineEdit()
            line.setText(str(default) if default != inspect.Parameter.empty else "")
            line.setPlaceholderText("Выберите путь...")
            
            btn = QPushButton("📁 Обзор")
            
            is_dir = 'dir' in name.lower() or 'directory' in name.lower()
            if is_dir:
                btn.clicked.connect(lambda: self._browse_directory(line))
                line.setPlaceholderText("Выберите директорию...")
            else:
                btn.clicked.connect(lambda: self._browse_file(line))
                line.setPlaceholderText("Выберите файл...")
            
            layout.addWidget(line, 1)
            layout.addWidget(btn)
            container.setLayout(layout)
            w = container
            w.line_edit = line
            
        elif param_type == dict:
            w = QTextEdit()
            w.setPlaceholderText('{"key": "value", ...}')
            w.setMaximumHeight(100)
            if default != inspect.Parameter.empty:
                import json
                w.setText(json.dumps(default, indent=2, ensure_ascii=False))
                
        elif hasattr(param_type, '__members__'):  # Enum
            w = QComboBox()
            for member in param_type.__members__.values():
                w.addItem(member.name, member)
            if default != inspect.Parameter.empty:
                idx = w.findData(default)
                if idx >= 0:
                    w.setCurrentIndex(idx)
                    
        else:  # str по умолчанию
            w = QLineEdit()
            if default != inspect.Parameter.empty:
                w.setText(str(default))
            w.setPlaceholderText(f"Введите {self._get_type_name(param)}...")
            
        return w

    def _browse_file(self, line_edit: QLineEdit):
        """Диалог выбора файла."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл", "",
            "Все файлы (*.*)"
        )
        if path:
            line_edit.setText(path)

    def _browse_directory(self, line_edit: QLineEdit):
        """Диалог выбора директории."""
        path = QFileDialog.getExistingDirectory(
            self, "Выберите директорию"
        )
        if path:
            line_edit.setText(path)

    def get_arguments(self) -> dict:
        """Извлекает аргументы из виджетов."""
        kwargs = {}
        sig = inspect.signature(self.func)
        
        for name, widget in self.inputs.items():
            param = sig.parameters[name]
            annotation = param.annotation
            if annotation == inspect.Parameter.empty:
                annotation = type(param.default) if param.default != inspect.Parameter.empty else str

            # Извлекаем значение
            if isinstance(widget, QCheckBox):
                value = widget.isChecked()
            elif isinstance(widget, QSpinBox):
                value = widget.value()
            elif isinstance(widget, QDoubleSpinBox):
                value = widget.value()
            elif isinstance(widget, QTextEdit):
                text = widget.toPlainText().strip()
                if annotation == list:
                    value = [line.strip() for line in text.split('\n') if line.strip()]
                elif annotation == dict:
                    import json
                    try:
                        value = json.loads(text) if text else {}
                    except:
                        value = {}
                else:
                    value = text
            elif isinstance(widget, QComboBox):
                value = widget.currentData() or widget.currentText()
            elif hasattr(widget, 'line_edit'):
                value = widget.line_edit.text()
                if annotation == Path:
                    value = Path(value) if value else None
            elif isinstance(widget, QLineEdit):
                value = widget.text()
                # Приведение типов
                if annotation == int:
                    value = int(value) if value else 0
                elif annotation == float:
                    value = float(value) if value else 0.0
                elif annotation == bool:
                    value = value.lower() in ('true', '1', 'yes', 'да')
                elif annotation == Path:
                    value = Path(value) if value else None
            else:
                value = None

            kwargs[name] = value
            
        return kwargs