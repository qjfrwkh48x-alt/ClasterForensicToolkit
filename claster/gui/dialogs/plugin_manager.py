"""
Plugin management dialog.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QListWidgetItem, QLabel, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt

from claster.core.plugins import plugin_manager


class PluginManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление плагинами")
        self.setMinimumSize(500, 400)
        self.setup_ui()
        self.refresh_list()

    def setup_ui(self):
        layout = QVBoxLayout()

        self.plugin_list = QListWidget()
        layout.addWidget(self.plugin_list)

        btn_layout = QHBoxLayout()
        load_btn = QPushButton("Загрузить плагин")
        load_btn.clicked.connect(self.load_plugin)
        unload_btn = QPushButton("Выгрузить")
        unload_btn.clicked.connect(self.unload_plugin)
        add_dir_btn = QPushButton("Добавить директорию")
        add_dir_btn.clicked.connect(self.add_directory)
        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.refresh_list)

        btn_layout.addWidget(load_btn)
        btn_layout.addWidget(unload_btn)
        btn_layout.addWidget(add_dir_btn)
        btn_layout.addWidget(refresh_btn)
        layout.addLayout(btn_layout)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def refresh_list(self):
        self.plugin_list.clear()
        plugins = plugin_manager.list_plugins()
        for p in plugins:
            item = QListWidgetItem(f"{p['name']} v{p['version']} - {p['description']}")
            item.setData(Qt.ItemDataRole.UserRole, p['name'])
            if plugin_manager.get_plugin(p['name']) is not None:
                item.setForeground(Qt.GlobalColor.green)
            self.plugin_list.addItem(item)
        self.status_label.setText(f"Найдено плагинов: {len(plugins)}")

    def load_plugin(self):
        item = self.plugin_list.currentItem()
        if item:
            name = item.data(Qt.ItemDataRole.UserRole)
            plugin = plugin_manager.load_plugin(name)
            if plugin:
                QMessageBox.information(self, "Успех", f"Плагин {name} загружен.")
                self.refresh_list()

    def unload_plugin(self):
        item = self.plugin_list.currentItem()
        if item:
            name = item.data(Qt.ItemDataRole.UserRole)
            plugin_manager.unload_plugin(name)
            QMessageBox.information(self, "Успех", f"Плагин {name} выгружен.")
            self.refresh_list()

    def add_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Выберите директорию с плагинами")
        if dir_path:
            from claster.core.config import get_config
            config = get_config()
            if dir_path not in config.plugin_directories:
                config.plugin_directories.append(dir_path)
                config.save("config.yaml")
            plugin_manager.discover_plugins([dir_path])
            self.refresh_list()