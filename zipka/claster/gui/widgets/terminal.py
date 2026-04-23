"""
Claster intelligent terminal for running forensic commands.
"""

import sys
import re
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit
from PyQt6.QtGui import QFont, QTextCursor, QColor
from PyQt6.QtCore import Qt, QProcess, pyqtSlot

class TerminalWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.history = []
        self.history_index = -1
        self.commands = self._get_available_commands()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Consolas", 10))
        self.output.setStyleSheet("background-color: #0C0C0C; color: #CCCCCC;")
        
        self.input = QLineEdit()
        self.input.setFont(QFont("Consolas", 10))
        self.input.setStyleSheet("background-color: #0C0C0C; color: #00FF00; border: none; padding: 5px;")
        self.input.returnPressed.connect(self.execute_command)
        self.input.keyPressEvent = self.handle_key_press
        
        layout.addWidget(self.output)
        layout.addWidget(self.input)
        self.setLayout(layout)
        
        self.output.append("Терминал Claster готов. Введите 'help' для списка команд.\n")

    def _get_available_commands(self):
        """Возвращает список доступных команд Claster."""
        return {
            'help': 'Показать справку',
            'clear': 'Очистить экран',
            'hash': 'Вычислить хэш файла',
            'mft': 'Парсинг MFT',
            'carve': 'Восстановление файлов',
            'pfi': 'Управление PFI',
            'case': 'Управление делом',
            'export': 'Экспорт результатов',
        }

    def handle_key_press(self, event):
        if event.key() == Qt.Key.Key_Up:
            if self.history_index < len(self.history) - 1:
                self.history_index += 1
                self.input.setText(self.history[self.history_index])
        elif event.key() == Qt.Key.Key_Down:
            if self.history_index > 0:
                self.history_index -= 1
                self.input.setText(self.history[self.history_index])
            else:
                self.history_index = -1
                self.input.clear()
        else:
            QLineEdit.keyPressEvent(self.input, event)

    def execute_command(self):
        cmd = self.input.text().strip()
        if not cmd:
            return
        
        self.history.insert(0, cmd)
        self.history_index = -1
        self.output.append(f"<span style='color: #00FF00;'>$ {cmd}</span>")
        self.input.clear()
        
        parts = cmd.split()
        if not parts:
            return
        
        command = parts[0].lower()
        if command == 'help':
            self.show_help()
        elif command == 'clear':
            self.output.clear()
        elif command == 'hash':
            if len(parts) > 1:
                self.run_hash_command(parts[1])
            else:
                self.output.append("Использование: hash <файл>")
        else:
            self.output.append(f"Неизвестная команда: {command}. Введите 'help'.")

    def show_help(self):
        help_text = "\nДоступные команды:\n"
        for cmd, desc in self.commands.items():
            help_text += f"  {cmd:<10} - {desc}\n"
        self.output.append(help_text)

    def run_hash_command(self, file_path):
        from claster.core.hashing import compute_hash
        try:
            h = compute_hash(file_path, 'sha256')
            self.output.append(f"SHA256: {h}")
        except Exception as e:
            self.output.append(f"Ошибка: {e}")