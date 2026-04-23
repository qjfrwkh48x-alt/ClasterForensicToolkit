"""
File browser widget with file system navigation.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeView,
                             QLineEdit, QPushButton, QComboBox)
from PyQt6.QtCore import QDir, pyqtSignal
from PyQt6.QtGui import QFileSystemModel


class FileBrowserWidget(QWidget):
    file_selected = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.history = []         
        self.history_index = -1    
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Панель навигации
        nav_layout = QHBoxLayout()
        self.back_btn = QPushButton("←")
        self.forward_btn = QPushButton("→")
        self.up_btn = QPushButton("↑")
        self.path_edit = QLineEdit()
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Все файлы (*.*)", "Образы (*.dd *.e01)", "Логи (*.evtx *.log)"])
        
        nav_layout.addWidget(self.back_btn)
        nav_layout.addWidget(self.forward_btn)
        nav_layout.addWidget(self.up_btn)
        nav_layout.addWidget(self.path_edit)
        nav_layout.addWidget(self.filter_combo)
        layout.addLayout(nav_layout)

        # Дерево файлов
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        self.model.setFilter(QDir.Filter.AllEntries | QDir.Filter.Hidden | QDir.Filter.System)
        
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(QDir.rootPath()))
        self.tree.setColumnWidth(0, 250)
        self.tree.clicked.connect(self.on_clicked)
        
        # Связываем навигацию
        self.path_edit.returnPressed.connect(self.navigate_to_path)
        self.back_btn.clicked.connect(self.goBack)
        self.forward_btn.clicked.connect(self.goForward)
        self.up_btn.clicked.connect(self.go_up)
        
        layout.addWidget(self.tree)
        self.setLayout(layout)
        
        # Инициализация истории
        self._add_to_history(QDir.rootPath())
        self._update_nav_buttons()

    def on_clicked(self, index):
        path = self.model.filePath(index)
        self.path_edit.setText(path)
        if not self.model.isDir(index):
            self.file_selected.emit(path)

    def navigate_to_path(self):
        path = self.path_edit.text()
        index = self.model.index(path)
        if index.isValid():
            self.tree.setRootIndex(index)
            self._add_to_history(path)

    def go_up(self):
        current = self.tree.rootIndex()
        parent = self.model.parent(current)
        if parent.isValid():
            parent_path = self.model.filePath(parent)
            self.tree.setRootIndex(parent)
            self.path_edit.setText(parent_path)
            self._add_to_history(parent_path)

    def goBack(self):
        """Вернуться к предыдущему пути в истории."""
        if self.history_index > 0:
            self.history_index -= 1
            path = self.history[self.history_index]
            self._navigate_without_history(path)

    def goForward(self):
        """Перейти к следующему пути в истории."""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            path = self.history[self.history_index]
            self._navigate_without_history(path)

    def _add_to_history(self, path: str):
        """Добавить путь в историю навигации."""
        # Удаляем пути после текущей позиции (если переходили назад)
        self.history = self.history[:self.history_index + 1]
        # Добавляем новый путь, если он отличается от последнего
        if not self.history or self.history[-1] != path:
            self.history.append(path)
            self.history_index = len(self.history) - 1
        self._update_nav_buttons()

    def _navigate_without_history(self, path: str):
        """Перейти по пути без добавления в историю."""
        index = self.model.index(path)
        if index.isValid():
            self.tree.setRootIndex(index)
            self.path_edit.setText(path)
        self._update_nav_buttons()

    def _update_nav_buttons(self):
        """Обновить состояние кнопок навигации."""
        self.back_btn.setEnabled(self.history_index > 0)
        self.forward_btn.setEnabled(self.history_index < len(self.history) - 1)