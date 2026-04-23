"""
Widget for running forensic tasks with argument dialog.
"""

import importlib
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTextEdit, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter
)
from PyQt6.QtCore import pyqtSignal, Qt

from claster.gui.dialogs.function_args_dialog import FunctionArgsDialog
from claster.gui.workers.analysis_worker import AnalysisWorker
from claster.gui.translations import FUNC_TRANSLATIONS

# Перевод названий модулей
MODULE_TRANSLATIONS = {
    "core": "Ядро",
    "disk": "Диск",
    "registry": "Реестр",
    "memory": "Память",
    "network": "Сеть",
    "stego": "Стеганография",
    "crypto": "Криптография",
    "metadata": "Метаданные",
    "browser": "Браузеры",
    "pfi": "PFI",
    "report": "Отчёты",
}


class TaskRunnerWidget(QWidget):
    task_started = pyqtSignal(str)
    task_finished_signal = pyqtSignal(object)
    task_error_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Выбор модуля и функции
        selection_layout = QHBoxLayout()
        selection_layout.addWidget(QLabel("Модуль:"))
        self.module_combo = QComboBox()
        
        # Добавляем модули с русскими названиями
        for mod_key, mod_name in MODULE_TRANSLATIONS.items():
            self.module_combo.addItem(mod_name, mod_key)
        
        self.module_combo.currentIndexChanged.connect(self._update_function_list)
        selection_layout.addWidget(self.module_combo)

        selection_layout.addWidget(QLabel("Функция:"))
        self.func_combo = QComboBox()
        self.func_combo.setMinimumWidth(250)
        selection_layout.addWidget(self.func_combo)
        layout.addLayout(selection_layout)

        # Кнопка запуска
        self.run_btn = QPushButton("▶ Запустить")
        self.run_btn.clicked.connect(self._run_task)
        self.run_btn.setStyleSheet("""
            QPushButton {
                background-color: #0d7377;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #14a085;
            }
        """)
        layout.addWidget(self.run_btn)

        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Разделитель между логом и результатами
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Лог выполнения
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setPlaceholderText("Лог выполнения...")
        splitter.addWidget(self.log_text)

        # Таблица результатов
        self.results_table = QTableWidget()
        self.results_table.setAlternatingRowColors(True)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        splitter.addWidget(self.results_table)
        
        layout.addWidget(splitter)
        self.setLayout(layout)

    def _update_function_list(self, index: int):
        """Обновляет список функций при выборе модуля."""
        self.func_combo.clear()
        module_key = self.module_combo.currentData()
        if not module_key:
            return

        try:
            module = importlib.import_module(f"claster.{module_key}")
            if hasattr(module, '__all__'):
                for func_name in sorted(module.__all__):
                    if func_name.startswith('_'):
                        continue
                    display_name = FUNC_TRANSLATIONS.get(func_name, func_name)
                    self.func_combo.addItem(display_name, func_name)
        except ImportError as e:
            self.log_text.append(f"Ошибка загрузки модуля: {e}")

    def _run_task(self):
        """Запускает выбранную функцию."""
        module_key = self.module_combo.currentData()
        func_name = self.func_combo.currentData()
        
        if not module_key or not func_name:
            return

        try:
            module = importlib.import_module(f"claster.{module_key}")
            func = getattr(module, func_name)
        except Exception as e:
            self.log_text.append(f"❌ Ошибка импорта: {e}")
            return

        # Диалог ввода аргументов
        dialog = FunctionArgsDialog(func, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        
        args = dialog.get_arguments()

        # Запуск воркера
        self.run_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.log_text.clear()
        self.results_table.clear()
        self.results_table.setRowCount(0)
        
        module_display = MODULE_TRANSLATIONS.get(module_key, module_key)
        func_display = FUNC_TRANSLATIONS.get(func_name, func_name)
        self.log_text.append(f"🚀 Запуск: {module_display} → {func_display}")
        self.task_started.emit(f"{module_key}.{func_name}")

        self.worker = AnalysisWorker(func, **args)
        self.worker.message.connect(self._on_log_message)
        self.worker.finished.connect(self._task_finished)
        self.worker.error.connect(self._task_error)
        self.worker.start()

    def _on_log_message(self, message: str):
        """Обработчик сообщений от воркера."""
        self.log_text.append(message)

    def _task_finished(self, result):
        """Обработчик завершения задачи."""
        self.run_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.log_text.append("✅ Задача завершена")
        
        # Отображение результата в таблице
        self._display_result(result)
        self.task_finished_signal.emit(result)

    def _task_error(self, error_msg: str):
        """Обработчик ошибки."""
        self.run_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.log_text.append(f"❌ Ошибка: {error_msg}")
        self.task_error_signal.emit(error_msg)

    def _display_result(self, result):
        """Отображает результат в виде таблицы."""
        self.results_table.clear()
        
        if result is None:
            self.results_table.setColumnCount(1)
            self.results_table.setHorizontalHeaderLabels(["Результат"])
            self.results_table.setRowCount(1)
            self.results_table.setItem(0, 0, QTableWidgetItem("Нет данных"))
            return
        
        if isinstance(result, dict):
            # Словарь → две колонки
            self.results_table.setColumnCount(2)
            self.results_table.setHorizontalHeaderLabels(["Ключ", "Значение"])
            self.results_table.setRowCount(len(result))
            
            for i, (key, value) in enumerate(result.items()):
                self.results_table.setItem(i, 0, QTableWidgetItem(str(key)))
                # Форматирование значения
                if isinstance(value, (list, dict)):
                    import json
                    display_value = json.dumps(value, ensure_ascii=False, indent=2)
                else:
                    display_value = str(value)
                self.results_table.setItem(i, 1, QTableWidgetItem(display_value))
        
        elif isinstance(result, list):
            # Список → одна колонка или таблица из словарей
            if result and isinstance(result[0], dict):
                # Список словарей → таблица с заголовками
                headers = list(result[0].keys())
                self.results_table.setColumnCount(len(headers))
                self.results_table.setHorizontalHeaderLabels(headers)
                self.results_table.setRowCount(len(result))
                
                for i, item in enumerate(result):
                    for j, key in enumerate(headers):
                        value = item.get(key, "")
                        if isinstance(value, (list, dict)):
                            import json
                            value = json.dumps(value, ensure_ascii=False)
                        self.results_table.setItem(i, j, QTableWidgetItem(str(value)))
            else:
                # Обычный список
                self.results_table.setColumnCount(1)
                self.results_table.setHorizontalHeaderLabels(["Элемент"])
                self.results_table.setRowCount(len(result))
                for i, item in enumerate(result):
                    self.results_table.setItem(i, 0, QTableWidgetItem(str(item)))
        else:
            # Примитивный тип
            self.results_table.setColumnCount(1)
            self.results_table.setHorizontalHeaderLabels(["Результат"])
            self.results_table.setRowCount(1)
            self.results_table.setItem(0, 0, QTableWidgetItem(str(result)))

    def run_function(self, module_name: str, func_name: str, args: dict = None):
        """Публичный метод для запуска функции."""
        # Находим индекс модуля
        for i in range(self.module_combo.count()):
            if self.module_combo.itemData(i) == module_name:
                self.module_combo.setCurrentIndex(i)
                break
        
        # Находим индекс функции
        for i in range(self.func_combo.count()):
            if self.func_combo.itemData(i) == func_name:
                self.func_combo.setCurrentIndex(i)
                break
        
        if args:
            # Если аргументы переданы, запускаем без диалога
            self._run_with_args(module_name, func_name, args)
        else:
            self._run_task()

    def _run_with_args(self, module_name: str, func_name: str, args: dict):
        """Запускает функцию с готовыми аргументами."""
        try:
            module = importlib.import_module(f"claster.{module_name}")
            func = getattr(module, func_name)
        except Exception as e:
            self.log_text.append(f"❌ Ошибка импорта: {e}")
            return

        self.run_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.log_text.clear()
        self.results_table.clear()
        
        module_display = MODULE_TRANSLATIONS.get(module_name, module_name)
        func_display = FUNC_TRANSLATIONS.get(func_name, func_name)
        self.log_text.append(f"🚀 Запуск: {module_display} → {func_display}")

        self.worker = AnalysisWorker(func, **args)
        self.worker.message.connect(self._on_log_message)
        self.worker.finished.connect(self._task_finished)
        self.worker.error.connect(self._task_error)
        self.worker.start()