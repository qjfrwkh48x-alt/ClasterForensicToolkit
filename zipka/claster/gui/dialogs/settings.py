"""
Расширенный диалог настроек с тонкой настройкой всех модулей.
"""

import os
import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLineEdit, QSpinBox, QCheckBox, QComboBox,
    QDialogButtonBox, QFileDialog, QPushButton, QGroupBox,
    QDoubleSpinBox, QTextEdit, QLabel, QScrollArea, QFrame,
    QSlider, QFontComboBox, QColorDialog, QListWidget, QListWidgetItem,
    QRadioButton, QButtonGroup, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSettings
from PyQt6.QtGui import QFont, QColor

from claster.core.config import get_config, Config
from claster.core.logger import get_logger
from claster.gui.i18n import get_supported_languages

logger = get_logger(__name__)


class SettingsDialog(QDialog):
    """Расширенный диалог настроек приложения."""
    
    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = get_config()
        self.setWindowTitle("⚙️ Настройки Claster Forensic Toolkit")
        self.setMinimumSize(900, 650)
        self.setup_ui()
        self.load_settings()
        
        # Применяем стиль
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
            }
            QTabWidget::pane {
                border: 1px solid #0f3460;
                background-color: #1a1a2e;
            }
            QTabBar::tab {
                background-color: #16213e;
                color: #e0e0e0;
                padding: 10px 20px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #e94560;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background-color: #0f3460;
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
            QLabel {
                color: #e0e0e0;
            }
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit {
                background-color: #0f0f1a;
                color: #e0e0e0;
                border: 1px solid #0f3460;
                border-radius: 4px;
                padding: 6px;
            }
            QCheckBox, QRadioButton {
                color: #e0e0e0;
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
            QSlider::groove:horizontal {
                height: 6px;
                background: #0f0f1a;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #e94560;
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

    def setup_ui(self):
        """Настраивает интерфейс диалога."""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        
        # Создаём все вкладки
        self.tabs.addTab(self.create_general_tab(), "🎛️ Общие")
        self.tabs.addTab(self.create_paths_tab(), "📁 Пути")
        self.tabs.addTab(self.create_appearance_tab(), "🎨 Оформление")
        self.tabs.addTab(self.create_pfi_tab(), "🧠 PFI")
        self.tabs.addTab(self.create_network_tab(), "🌐 Сеть")
        self.tabs.addTab(self.create_disk_tab(), "💾 Диск")
        self.tabs.addTab(self.create_memory_tab(), "🧮 Память")
        self.tabs.addTab(self.create_registry_tab(), "📝 Реестр")
        self.tabs.addTab(self.create_browser_tab(), "🌍 Браузеры")
        self.tabs.addTab(self.create_crypto_tab(), "🔐 Криптография")
        self.tabs.addTab(self.create_stego_tab(), "🖼️ Стеганография")
        self.tabs.addTab(self.create_report_tab(), "📊 Отчёты")
        self.tabs.addTab(self.create_plugins_tab(), "🔌 Плагины")
        self.tabs.addTab(self.create_advanced_tab(), "⚙️ Дополнительно")
        self.tabs.addTab(self.create_experimental_tab(), "🧪 Экспериментальное")
        
        layout.addWidget(self.tabs)
        
        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("💾 Сохранить")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #0d7377;
                min-width: 120px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #14a085;
            }
        """)
        
        cancel_btn = QPushButton("❌ Отмена")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                min-width: 120px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #5d5d5d;
            }
        """)
        
        apply_btn = QPushButton("✓ Применить")
        apply_btn.clicked.connect(self.apply_settings)
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #0f3460;
                min-width: 120px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #1a4a7a;
            }
        """)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(apply_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

    def create_scrollable_tab(self, content_widget: QWidget) -> QScrollArea:
        """Создаёт скроллируемую вкладку."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content_widget)
        return scroll

    # ==================== ОБЩИЕ ====================
    
    def create_general_tab(self):
        """Вкладка общих настроек."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Основные настройки
        basic_group = QGroupBox("Основные настройки")
        basic_layout = QFormLayout()
        
        self.case_name_edit = QLineEdit()
        self.case_name_edit.setPlaceholderText("Название дела по умолчанию")
        basic_layout.addRow("Название дела:", self.case_name_edit)
        
        self.examiner_name_edit = QLineEdit()
        self.examiner_name_edit.setPlaceholderText("Имя эксперта")
        basic_layout.addRow("Эксперт по умолчанию:", self.examiner_name_edit)
        
        self.organization_edit = QLineEdit()
        self.organization_edit.setPlaceholderText("Организация")
        basic_layout.addRow("Организация:", self.organization_edit)
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        # Язык и регион
        locale_group = QGroupBox("Язык и регион")
        locale_layout = QFormLayout()
        
        self.language_combo = QComboBox()
        for code, name in get_supported_languages():
            self.language_combo.addItem(name, code)
        locale_layout.addRow("Язык интерфейса:", self.language_combo)
        
        self.timezone_combo = QComboBox()
        import pytz
        for tz in pytz.common_timezones:
            self.timezone_combo.addItem(tz)
        locale_layout.addRow("Часовой пояс:", self.timezone_combo)
        
        self.date_format_combo = QComboBox()
        self.date_format_combo.addItems([
            "YYYY-MM-DD", "DD.MM.YYYY", "MM/DD/YYYY", "DD/MM/YYYY"
        ])
        locale_layout.addRow("Формат даты:", self.date_format_combo)
        
        self.time_format_combo = QComboBox()
        self.time_format_combo.addItems(["24-часовой", "12-часовой (AM/PM)"])
        locale_layout.addRow("Формат времени:", self.time_format_combo)
        
        locale_group.setLayout(locale_layout)
        layout.addWidget(locale_group)
        
        # Логирование
        log_group = QGroupBox("Логирование")
        log_layout = QFormLayout()
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        log_layout.addRow("Уровень логирования:", self.log_level_combo)
        
        self.log_file_edit = QLineEdit()
        browse_btn = QPushButton("📁 Обзор")
        browse_btn.clicked.connect(lambda: self.browse_file(self.log_file_edit, "*.log"))
        log_file_layout = QHBoxLayout()
        log_file_layout.addWidget(self.log_file_edit)
        log_file_layout.addWidget(browse_btn)
        log_layout.addRow("Файл лога:", log_file_layout)
        
        self.log_max_size_spin = QSpinBox()
        self.log_max_size_spin.setRange(1, 1000)
        self.log_max_size_spin.setSuffix(" MB")
        log_layout.addRow("Макс. размер лога:", self.log_max_size_spin)
        
        self.log_retention_spin = QSpinBox()
        self.log_retention_spin.setRange(1, 365)
        self.log_retention_spin.setSuffix(" дней")
        log_layout.addRow("Хранить логи:", self.log_retention_spin)
        
        self.console_logging = QCheckBox("Выводить логи в консоль")
        log_layout.addRow(self.console_logging)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # Автосохранение
        autosave_group = QGroupBox("Автосохранение")
        autosave_layout = QFormLayout()
        
        self.autosave_enabled = QCheckBox("Включить автосохранение")
        autosave_layout.addRow(self.autosave_enabled)
        
        self.autosave_interval_spin = QSpinBox()
        self.autosave_interval_spin.setRange(1, 60)
        self.autosave_interval_spin.setSuffix(" минут")
        autosave_layout.addRow("Интервал:", self.autosave_interval_spin)
        
        self.autosave_keep_versions = QSpinBox()
        self.autosave_keep_versions.setRange(1, 100)
        self.autosave_keep_versions.setSuffix(" версий")
        autosave_layout.addRow("Хранить версий:", self.autosave_keep_versions)
        
        autosave_group.setLayout(autosave_layout)
        layout.addWidget(autosave_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return self.create_scrollable_tab(widget)

    # ==================== ПУТИ ====================
    
    def create_paths_tab(self):
        """Вкладка настройки путей."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        paths = [
            ("case_directory", "Директория дел"),
            ("evidence_directory", "Директория улик"),
            ("reports_directory", "Директория отчётов"),
            ("temp_directory", "Временная директория"),
            ("exports_directory", "Директория экспорта"),
            ("plugins_directory", "Директория плагинов"),
            ("scripts_directory", "Директория скриптов"),
            ("templates_directory", "Директория шаблонов"),
        ]
        
        for attr_name, label in paths:
            group = QGroupBox(label)
            group_layout = QVBoxLayout()
            
            edit = QLineEdit()
            edit.setObjectName(attr_name)
            btn = QPushButton("📁 Обзор")
            btn.clicked.connect(lambda checked, e=edit: self.browse_directory(e))
            
            path_layout = QHBoxLayout()
            path_layout.addWidget(edit)
            path_layout.addWidget(btn)
            group_layout.addLayout(path_layout)
            
            # Подсказка
            hint = QLabel(f"Путь для {label.lower()}")
            hint.setStyleSheet("color: #666; font-size: 9pt;")
            group_layout.addWidget(hint)
            
            group.setLayout(group_layout)
            layout.addWidget(group)
            
            setattr(self, f"{attr_name}_edit", edit)
        
        # Дополнительные пути
        extra_group = QGroupBox("Дополнительные пути")
        extra_layout = QFormLayout()
        
        self.external_tools_path_edit = QLineEdit()
        extra_layout.addRow("Внешние инструменты:", self.external_tools_path_edit)
        
        self.signature_db_path_edit = QLineEdit()
        extra_layout.addRow("База сигнатур:", self.signature_db_path_edit)
        
        self.wordlists_path_edit = QLineEdit()
        extra_layout.addRow("Словари:", self.wordlists_path_edit)
        
        self.yara_rules_path_edit = QLineEdit()
        extra_layout.addRow("YARA правила:", self.yara_rules_path_edit)
        
        extra_group.setLayout(extra_layout)
        layout.addWidget(extra_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return self.create_scrollable_tab(widget)

    # ==================== ОФОРМЛЕНИЕ ====================
    
    def create_appearance_tab(self):
        """Вкладка настройки оформления."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Тема
        theme_group = QGroupBox("Тема оформления")
        theme_layout = QVBoxLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Тёмная (по умолчанию)", "Светлая", "Высокий контраст", "Синяя", "Зелёная"])
        theme_layout.addWidget(self.theme_combo)
        
        self.custom_theme_check = QCheckBox("Использовать пользовательскую тему")
        theme_layout.addWidget(self.custom_theme_check)
        
        theme_file_layout = QHBoxLayout()
        self.theme_file_edit = QLineEdit()
        theme_file_btn = QPushButton("📁 Обзор")
        theme_file_btn.clicked.connect(lambda: self.browse_file(self.theme_file_edit, "*.qss"))
        theme_file_layout.addWidget(self.theme_file_edit)
        theme_file_layout.addWidget(theme_file_btn)
        theme_layout.addLayout(theme_file_layout)
        
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # Шрифты
        font_group = QGroupBox("Шрифты")
        font_layout = QFormLayout()
        
        self.font_combo = QFontComboBox()
        font_layout.addRow("Шрифт интерфейса:", self.font_combo)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setSuffix(" pt")
        font_layout.addRow("Размер шрифта:", self.font_size_spin)
        
        self.mono_font_combo = QFontComboBox()
        self.mono_font_combo.setFontFilters(QFontComboBox.FontFilter.MonospacedFonts)
        font_layout.addRow("Моноширинный шрифт:", self.mono_font_combo)
        
        self.mono_font_size_spin = QSpinBox()
        self.mono_font_size_spin.setRange(8, 20)
        self.mono_font_size_spin.setSuffix(" pt")
        font_layout.addRow("Размер моноширинного:", self.mono_font_size_spin)
        
        font_group.setLayout(font_layout)
        layout.addWidget(font_group)
        
        # Цвета
        color_group = QGroupBox("Цвета подсветки")
        color_layout = QFormLayout()
        
        self.highlight_color_btn = QPushButton("Выбрать цвет")
        self.highlight_color_btn.clicked.connect(self.choose_highlight_color)
        color_layout.addRow("Цвет подсветки:", self.highlight_color_btn)
        
        self.selection_color_btn = QPushButton("Выбрать цвет")
        self.selection_color_btn.clicked.connect(self.choose_selection_color)
        color_layout.addRow("Цвет выделения:", self.selection_color_btn)
        
        self.error_color_btn = QPushButton("Выбрать цвет")
        self.error_color_btn.clicked.connect(self.choose_error_color)
        color_layout.addRow("Цвет ошибок:", self.error_color_btn)
        
        color_group.setLayout(color_layout)
        layout.addWidget(color_group)
        
        # Интерфейс
        ui_group = QGroupBox("Элементы интерфейса")
        ui_layout = QVBoxLayout()
        
        self.show_toolbar_labels = QCheckBox("Показывать подписи на панели инструментов")
        ui_layout.addWidget(self.show_toolbar_labels)
        
        self.show_statusbar = QCheckBox("Показывать строку состояния")
        ui_layout.addWidget(self.show_statusbar)
        
        self.tab_position_combo = QComboBox()
        self.tab_position_combo.addItems(["Сверху", "Снизу", "Слева", "Справа"])
        ui_layout.addWidget(QLabel("Позиция вкладок:"))
        ui_layout.addWidget(self.tab_position_combo)
        
        self.icon_size_spin = QSpinBox()
        self.icon_size_spin.setRange(16, 64)
        self.icon_size_spin.setSuffix(" px")
        ui_layout.addWidget(QLabel("Размер иконок:"))
        ui_layout.addWidget(self.icon_size_spin)
        
        ui_group.setLayout(ui_layout)
        layout.addWidget(ui_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return self.create_scrollable_tab(widget)

    # ==================== PFI ====================
    
    def create_pfi_tab(self):
        """Вкладка настроек PFI."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Модель
        model_group = QGroupBox("Модель PFI")
        model_layout = QFormLayout()
        
        model_path_layout = QHBoxLayout()
        self.pfi_model_path_edit = QLineEdit()
        model_path_btn = QPushButton("📁 Обзор")
        model_path_btn.clicked.connect(lambda: self.browse_directory(self.pfi_model_path_edit))
        model_path_layout.addWidget(self.pfi_model_path_edit)
        model_path_layout.addWidget(model_path_btn)
        model_layout.addRow("Путь к модели:", model_path_layout)
        
        self.pfi_model_type_combo = QComboBox()
        self.pfi_model_type_combo.addItems(["Transformer", "BiLSTM", "CNN-LSTM", "Autoencoder"])
        model_layout.addRow("Тип модели:", self.pfi_model_type_combo)
        
        self.pfi_sequence_length_spin = QSpinBox()
        self.pfi_sequence_length_spin.setRange(10, 500)
        self.pfi_sequence_length_spin.setValue(50)
        model_layout.addRow("Длина последовательности:", self.pfi_sequence_length_spin)
        
        self.pfi_embedding_dim_spin = QSpinBox()
        self.pfi_embedding_dim_spin.setRange(32, 512)
        self.pfi_embedding_dim_spin.setValue(128)
        model_layout.addRow("Размерность эмбеддинга:", self.pfi_embedding_dim_spin)
        
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        # Мониторинг
        monitor_group = QGroupBox("Мониторинг")
        monitor_layout = QFormLayout()
        
        self.pfi_threshold_spin = QDoubleSpinBox()
        self.pfi_threshold_spin.setRange(0.0, 1.0)
        self.pfi_threshold_spin.setSingleStep(0.05)
        self.pfi_threshold_spin.setValue(0.75)
        monitor_layout.addRow("Порог срабатывания:", self.pfi_threshold_spin)
        
        self.pfi_interval_spin = QSpinBox()
        self.pfi_interval_spin.setRange(1, 60)
        self.pfi_interval_spin.setSuffix(" сек")
        self.pfi_interval_spin.setValue(5)
        monitor_layout.addRow("Интервал мониторинга:", self.pfi_interval_spin)
        
        self.pfi_auto_start = QCheckBox("Автоматически запускать мониторинг при старте")
        monitor_layout.addRow(self.pfi_auto_start)
        
        self.pfi_alert_sound = QCheckBox("Звуковое оповещение при угрозе")
        monitor_layout.addRow(self.pfi_alert_sound)
        
        self.pfi_alert_popup = QCheckBox("Всплывающее окно при угрозе")
        monitor_layout.addRow(self.pfi_alert_popup)
        
        monitor_group.setLayout(monitor_layout)
        layout.addWidget(monitor_group)
        
        # Обучение
        train_group = QGroupBox("Обучение")
        train_layout = QFormLayout()
        
        self.pfi_default_dataset_combo = QComboBox()
        self.pfi_default_dataset_combo.addItems(["synthetic", "cicids2017", "unsw_nb15", "ton_iot", "lanl"])
        train_layout.addRow("Датасет по умолчанию:", self.pfi_default_dataset_combo)
        
        self.pfi_epochs_spin = QSpinBox()
        self.pfi_epochs_spin.setRange(1, 200)
        self.pfi_epochs_spin.setValue(30)
        train_layout.addRow("Количество эпох:", self.pfi_epochs_spin)
        
        self.pfi_batch_size_spin = QSpinBox()
        self.pfi_batch_size_spin.setRange(8, 512)
        self.pfi_batch_size_spin.setValue(64)
        train_layout.addRow("Размер батча:", self.pfi_batch_size_spin)
        
        self.pfi_learning_rate_spin = QDoubleSpinBox()
        self.pfi_learning_rate_spin.setRange(0.00001, 0.1)
        self.pfi_learning_rate_spin.setSingleStep(0.0001)
        self.pfi_learning_rate_spin.setDecimals(5)
        self.pfi_learning_rate_spin.setValue(0.001)
        train_layout.addRow("Learning rate:", self.pfi_learning_rate_spin)
        
        self.pfi_dropout_spin = QDoubleSpinBox()
        self.pfi_dropout_spin.setRange(0.0, 0.9)
        self.pfi_dropout_spin.setSingleStep(0.05)
        self.pfi_dropout_spin.setValue(0.2)
        train_layout.addRow("Dropout:", self.pfi_dropout_spin)
        
        train_group.setLayout(train_layout)
        layout.addWidget(train_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return self.create_scrollable_tab(widget)

    # ==================== СЕТЬ ====================
    
    def create_network_tab(self):
        """Вкладка настроек сети."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Захват пакетов
        capture_group = QGroupBox("Захват пакетов")
        capture_layout = QFormLayout()
        
        self.network_interface_combo = QComboBox()
        self.populate_interfaces()
        capture_layout.addRow("Интерфейс по умолчанию:", self.network_interface_combo)
        
        self.max_packets_spin = QSpinBox()
        self.max_packets_spin.setRange(1, 1000000)
        self.max_packets_spin.setValue(10000)
        capture_layout.addRow("Макс. пакетов:", self.max_packets_spin)
        
        self.snaplen_spin = QSpinBox()
        self.snaplen_spin.setRange(68, 65535)
        self.snaplen_spin.setValue(65535)
        capture_layout.addRow("Snaplen (байт):", self.snaplen_spin)
        
        self.promiscuous_mode = QCheckBox("Promiscuous mode")
        self.promiscuous_mode.setChecked(True)
        capture_layout.addRow(self.promiscuous_mode)
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 3600)
        self.timeout_spin.setSuffix(" сек")
        self.timeout_spin.setValue(30)
        capture_layout.addRow("Таймаут захвата:", self.timeout_spin)
        
        capture_group.setLayout(capture_layout)
        layout.addWidget(capture_group)
        
        # Фильтры
        filter_group = QGroupBox("Фильтры BPF")
        filter_layout = QVBoxLayout()
        
        self.default_filter_edit = QLineEdit()
        self.default_filter_edit.setPlaceholderText("tcp port 80 or udp port 53")
        filter_layout.addWidget(QLabel("Фильтр по умолчанию:"))
        filter_layout.addWidget(self.default_filter_edit)
        
        self.filter_presets_list = QListWidget()
        self.filter_presets_list.addItems([
            "HTTP only (tcp port 80)",
            "HTTPS only (tcp port 443)",
            "DNS only (udp port 53)",
            "No broadcast (not broadcast and not multicast)",
            "ICMP only (icmp)"
        ])
        filter_layout.addWidget(QLabel("Предустановки:"))
        filter_layout.addWidget(self.filter_presets_list)
        
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # Сканирование
        scan_group = QGroupBox("Сканирование")
        scan_layout = QFormLayout()
        
        self.scan_timeout_spin = QDoubleSpinBox()
        self.scan_timeout_spin.setRange(0.1, 10.0)
        self.scan_timeout_spin.setSingleStep(0.1)
        self.scan_timeout_spin.setValue(2.0)
        scan_layout.addRow("Таймаут сканирования (сек):", self.scan_timeout_spin)
        
        self.scan_threads_spin = QSpinBox()
        self.scan_threads_spin.setRange(1, 500)
        self.scan_threads_spin.setValue(50)
        scan_layout.addRow("Потоков сканирования:", self.scan_threads_spin)
        
        self.scan_common_ports = QCheckBox("Сканировать только частые порты")
        scan_layout.addRow(self.scan_common_ports)
        
        scan_group.setLayout(scan_layout)
        layout.addWidget(scan_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return self.create_scrollable_tab(widget)

    # ==================== ДИСК ====================
    
    def create_disk_tab(self):
        """Вкладка настроек диска."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Образы
        imaging_group = QGroupBox("Создание образов")
        imaging_layout = QFormLayout()
        
        self.image_format_combo = QComboBox()
        self.image_format_combo.addItems(["RAW (dd)", "E01 (EnCase)", "AFF4", "VMDK", "VHD"])
        imaging_layout.addRow("Формат образа:", self.image_format_combo)
        
        self.compression_level_spin = QSpinBox()
        self.compression_level_spin.setRange(0, 9)
        self.compression_level_spin.setValue(6)
        imaging_layout.addRow("Уровень сжатия:", self.compression_level_spin)
        
        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(1, 4096)
        self.chunk_size_spin.setSuffix(" MB")
        self.chunk_size_spin.setValue(64)
        imaging_layout.addRow("Размер блока:", self.chunk_size_spin)
        
        self.verify_image = QCheckBox("Проверять образ после создания")
        self.verify_image.setChecked(True)
        imaging_layout.addRow(self.verify_image)
        
        imaging_group.setLayout(imaging_layout)
        layout.addWidget(imaging_group)
        
        # MFT
        mft_group = QGroupBox("Анализ MFT")
        mft_layout = QFormLayout()
        
        self.mft_export_format_combo = QComboBox()
        self.mft_export_format_combo.addItems(["CSV", "JSON", "SQLite"])
        mft_layout.addRow("Формат экспорта:", self.mft_export_format_combo)
        
        self.mft_include_deleted = QCheckBox("Включать удалённые записи")
        self.mft_include_deleted.setChecked(True)
        mft_layout.addRow(self.mft_include_deleted)
        
        self.mft_detect_timestomping = QCheckBox("Обнаруживать timestomping")
        self.mft_detect_timestomping.setChecked(True)
        mft_layout.addRow(self.mft_detect_timestomping)
        
        mft_group.setLayout(mft_layout)
        layout.addWidget(mft_group)
        
        # Кара́винг
        carving_group = QGroupBox("Восстановление файлов")
        carving_layout = QFormLayout()
        
        self.carving_min_size_spin = QSpinBox()
        self.carving_min_size_spin.setRange(1, 10240)
        self.carving_min_size_spin.setSuffix(" KB")
        self.carving_min_size_spin.setValue(10)
        carving_layout.addRow("Мин. размер файла:", self.carving_min_size_spin)
        
        self.carving_max_size_spin = QSpinBox()
        self.carving_max_size_spin.setRange(1, 10240)
        self.carving_max_size_spin.setSuffix(" MB")
        self.carving_max_size_spin.setValue(100)
        carving_layout.addRow("Макс. размер файла:", self.carving_max_size_spin)
        
        carving_group.setLayout(carving_layout)
        layout.addWidget(carving_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return self.create_scrollable_tab(widget)

    # ==================== ПАМЯТЬ ====================
    
    def create_memory_tab(self):
        """Вкладка настроек памяти."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Дамп памяти
        dump_group = QGroupBox("Дамп памяти")
        dump_layout = QFormLayout()
        
        self.memory_dump_format_combo = QComboBox()
        self.memory_dump_format_combo.addItems(["RAW", "Microsoft Crash Dump", "ELF Core"])
        dump_layout.addRow("Формат дампа:", self.memory_dump_format_combo)
        
        self.memory_dump_compress = QCheckBox("Сжимать дамп")
        dump_layout.addRow(self.memory_dump_compress)
        
        dump_group.setLayout(dump_layout)
        layout.addWidget(dump_group)
        
        # Анализ
        analysis_group = QGroupBox("Анализ памяти")
        analysis_layout = QFormLayout()
        
        self.strings_min_len_spin = QSpinBox()
        self.strings_min_len_spin.setRange(3, 20)
        self.strings_min_len_spin.setValue(4)
        analysis_layout.addRow("Мин. длина строки:", self.strings_min_len_spin)
        
        self.volatility_profile_combo = QComboBox()
        self.volatility_profile_combo.addItems(["Win10x64", "Win7x64", "Linux", "macOS"])
        analysis_layout.addRow("Профиль Volatility:", self.volatility_profile_combo)
        
        analysis_group.setLayout(analysis_layout)
        layout.addWidget(analysis_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return self.create_scrollable_tab(widget)

    # ==================== РЕЕСТР ====================
    
    def create_registry_tab(self):
        """Вкладка настроек реестра."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        group = QGroupBox("Анализ реестра")
        form = QFormLayout()
        
        self.registry_parse_deleted = QCheckBox("Восстанавливать удалённые ключи")
        form.addRow(self.registry_parse_deleted)
        
        self.registry_export_format_combo = QComboBox()
        self.registry_export_format_combo.addItems(["JSON", "CSV", "REGTEXT"])
        form.addRow("Формат экспорта:", self.registry_export_format_combo)
        
        group.setLayout(form)
        layout.addWidget(group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return self.create_scrollable_tab(widget)

    # ==================== БРАУЗЕРЫ ====================
    
    def create_browser_tab(self):
        """Вкладка настроек браузеров."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        group = QGroupBox("Анализ браузеров")
        form = QFormLayout()
        
        self.browser_decrypt_passwords = QCheckBox("Расшифровывать пароли")
        form.addRow(self.browser_decrypt_passwords)
        
        self.browser_include_incognito = QCheckBox("Включать приватный режим")
        form.addRow(self.browser_include_incognito)
        
        self.browser_history_limit_spin = QSpinBox()
        self.browser_history_limit_spin.setRange(100, 100000)
        self.browser_history_limit_spin.setValue(10000)
        form.addRow("Лимит истории:", self.browser_history_limit_spin)
        
        group.setLayout(form)
        layout.addWidget(group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return self.create_scrollable_tab(widget)

    # ==================== КРИПТОГРАФИЯ ====================
    
    def create_crypto_tab(self):
        """Вкладка настроек криптографии."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Хеширование
        hash_group = QGroupBox("Хеширование")
        hash_layout = QFormLayout()
        
        self.default_hash_algo = QComboBox()
        self.default_hash_algo.addItems(["md5", "sha1", "sha256", "sha512", "sha3-256", "sha3-512", "blake2b"])
        self.default_hash_algo.setCurrentText("sha256")
        hash_layout.addRow("Алгоритм по умолчанию:", self.default_hash_algo)
        
        self.verify_copy = QCheckBox("Проверять целостность при копировании")
        self.verify_copy.setChecked(True)
        hash_layout.addRow(self.verify_copy)
        
        hash_group.setLayout(hash_layout)
        layout.addWidget(hash_group)
        
        # Взлом
        crack_group = QGroupBox("Взлом паролей")
        crack_layout = QFormLayout()
        
        self.crack_default_wordlist_edit = QLineEdit()
        crack_layout.addRow("Словарь по умолчанию:", self.crack_default_wordlist_edit)
        
        self.crack_max_length_spin = QSpinBox()
        self.crack_max_length_spin.setRange(1, 20)
        self.crack_max_length_spin.setValue(8)
        crack_layout.addRow("Макс. длина брутфорса:", self.crack_max_length_spin)
        
        self.crack_charset_edit = QLineEdit()
        self.crack_charset_edit.setText("abcdefghijklmnopqrstuvwxyz0123456789")
        crack_layout.addRow("Набор символов:", self.crack_charset_edit)
        
        crack_group.setLayout(crack_layout)
        layout.addWidget(crack_group)
        
        # Шифрование
        encrypt_group = QGroupBox("Шифрование")
        encrypt_layout = QFormLayout()
        
        self.aes_mode_combo = QComboBox()
        self.aes_mode_combo.addItems(["CBC", "ECB", "CFB", "OFB", "CTR", "GCM"])
        encrypt_layout.addRow("Режим AES:", self.aes_mode_combo)
        
        self.rsa_key_size_combo = QComboBox()
        self.rsa_key_size_combo.addItems(["2048", "3072", "4096"])
        encrypt_layout.addRow("Размер ключа RSA:", self.rsa_key_size_combo)
        
        encrypt_group.setLayout(encrypt_layout)
        layout.addWidget(encrypt_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return self.create_scrollable_tab(widget)

    # ==================== СТЕГАНОГРАФИЯ ====================
    
    def create_stego_tab(self):
        """Вкладка настроек стеганографии."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        group = QGroupBox("Стеганография")
        form = QFormLayout()
        
        self.stego_lsb_bits_spin = QSpinBox()
        self.stego_lsb_bits_spin.setRange(1, 4)
        self.stego_lsb_bits_spin.setValue(1)
        form.addRow("Бит на пиксель (LSB):", self.stego_lsb_bits_spin)
        
        self.stego_jpeg_quality_spin = QSpinBox()
        self.stego_jpeg_quality_spin.setRange(50, 100)
        self.stego_jpeg_quality_spin.setValue(85)
        form.addRow("Качество JPEG:", self.stego_jpeg_quality_spin)
        
        self.stego_echo_delay_spin = QSpinBox()
        self.stego_echo_delay_spin.setRange(10, 200)
        self.stego_echo_delay_spin.setValue(50)
        form.addRow("Задержка эха:", self.stego_echo_delay_spin)
        
        group.setLayout(form)
        layout.addWidget(group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return self.create_scrollable_tab(widget)

    # ==================== ОТЧЁТЫ ====================
    
    def create_report_tab(self):
        """Вкладка настроек отчётов."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        group = QGroupBox("Генерация отчётов")
        form = QFormLayout()
        
        self.report_default_format_combo = QComboBox()
        self.report_default_format_combo.addItems(["HTML", "PDF", "DOCX", "CSV", "JSON"])
        form.addRow("Формат по умолчанию:", self.report_default_format_combo)
        
        self.report_include_hashes = QCheckBox("Включать хэши")
        self.report_include_hashes.setChecked(True)
        form.addRow(self.report_include_hashes)
        
        self.report_include_timeline = QCheckBox("Включать таймлайн")
        self.report_include_timeline.setChecked(True)
        form.addRow(self.report_include_timeline)
        
        self.report_include_screenshots = QCheckBox("Включать скриншоты")
        form.addRow(self.report_include_screenshots)
        
        self.report_sign_digital = QCheckBox("Цифровая подпись отчёта")
        form.addRow(self.report_sign_digital)
        
        group.setLayout(form)
        layout.addWidget(group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return self.create_scrollable_tab(widget)

    # ==================== ПЛАГИНЫ ====================
    
    def create_plugins_tab(self):
        """Вкладка настроек плагинов."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        group = QGroupBox("Плагины")
        vlayout = QVBoxLayout()
        
        vlayout.addWidget(QLabel("Директории плагинов:"))
        self.plugin_dirs_edit = QTextEdit()
        self.plugin_dirs_edit.setPlaceholderText("По одной директории на строку")
        self.plugin_dirs_edit.setMaximumHeight(100)
        vlayout.addWidget(self.plugin_dirs_edit)
        
        self.auto_load_plugins = QCheckBox("Автоматически загружать плагины при старте")
        self.auto_load_plugins.setChecked(True)
        vlayout.addWidget(self.auto_load_plugins)
        
        self.plugin_sandbox = QCheckBox("Запускать плагины в песочнице")
        vlayout.addWidget(self.plugin_sandbox)
        
        group.setLayout(vlayout)
        layout.addWidget(group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return self.create_scrollable_tab(widget)

    # ==================== ДОПОЛНИТЕЛЬНО ====================
    
    def create_advanced_tab(self):
        """Вкладка дополнительных настроек."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Производительность
        perf_group = QGroupBox("Производительность")
        perf_layout = QFormLayout()
        
        self.max_threads_spin = QSpinBox()
        self.max_threads_spin.setRange(1, 64)
        self.max_threads_spin.setValue(os.cpu_count() or 4)
        perf_layout.addRow("Макс. потоков:", self.max_threads_spin)
        
        self.memory_limit_spin = QSpinBox()
        self.memory_limit_spin.setRange(256, 16384)
        self.memory_limit_spin.setSuffix(" MB")
        self.memory_limit_spin.setValue(4096)
        perf_layout.addRow("Лимит памяти:", self.memory_limit_spin)
        
        self.gpu_acceleration = QCheckBox("Использовать GPU (если доступно)")
        perf_layout.addRow(self.gpu_acceleration)
        
        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)
        
        # База данных
        db_group = QGroupBox("База данных")
        db_layout = QFormLayout()
        
        self.db_path_edit = QLineEdit()
        db_layout.addRow("Путь к БД:", self.db_path_edit)
        
        self.db_cache_size_spin = QSpinBox()
        self.db_cache_size_spin.setRange(1, 1024)
        self.db_cache_size_spin.setSuffix(" MB")
        self.db_cache_size_spin.setValue(100)
        db_layout.addRow("Размер кэша:", self.db_cache_size_spin)
        
        db_group.setLayout(db_layout)
        layout.addWidget(db_group)
        
        # Отладка
        debug_group = QGroupBox("Отладка")
        debug_layout = QVBoxLayout()
        
        self.debug_mode = QCheckBox("Режим отладки")
        debug_layout.addWidget(self.debug_mode)
        
        self.dev_tools = QCheckBox("Инструменты разработчика")
        debug_layout.addWidget(self.dev_tools)
        
        debug_group.setLayout(debug_layout)
        layout.addWidget(debug_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return self.create_scrollable_tab(widget)

    # ==================== ЭКСПЕРИМЕНТАЛЬНОЕ ====================
    
    def create_experimental_tab(self):
        """Вкладка экспериментальных настроек."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        warning = QLabel("⚠️ Внимание! Эти функции находятся в разработке и могут быть нестабильны.")
        warning.setStyleSheet("color: #e94560; font-weight: bold; padding: 10px;")
        warning.setWordWrap(True)
        layout.addWidget(warning)
        
        group = QGroupBox("Экспериментальные функции")
        vlayout = QVBoxLayout()
        
        self.exp_ai_assistant = QCheckBox("AI-ассистент расследования")
        vlayout.addWidget(self.exp_ai_assistant)
        
        self.exp_cloud_analysis = QCheckBox("Облачный анализ")
        vlayout.addWidget(self.exp_cloud_analysis)
        
        self.exp_blockchain_evidence = QCheckBox("Анализ блокчейн-улик")
        vlayout.addWidget(self.exp_blockchain_evidence)
        
        self.exp_quantum_crypto = QCheckBox("Пост-квантовая криптография")
        vlayout.addWidget(self.exp_quantum_crypto)
        
        group.setLayout(vlayout)
        layout.addWidget(group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return self.create_scrollable_tab(widget)

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================
    
    def populate_interfaces(self):
        """Заполняет список сетевых интерфейсов."""
        try:
            import psutil
            for name, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == 2:  # AF_INET
                        self.network_interface_combo.addItem(f"{name} ({addr.address})", name)
        except ImportError:
            self.network_interface_combo.addItem("Не удалось получить список")

    def browse_directory(self, line_edit: QLineEdit):
        """Диалог выбора директории."""
        path = QFileDialog.getExistingDirectory(self, "Выберите директорию")
        if path:
            line_edit.setText(path)

    def browse_file(self, line_edit: QLineEdit, filter_str: str = "*.*"):
        """Диалог выбора файла."""
        path, _ = QFileDialog.getOpenFileName(self, "Выберите файл", "", filter_str)
        if path:
            line_edit.setText(path)

    def choose_highlight_color(self):
        """Выбор цвета подсветки."""
        color = QColorDialog.getColor()
        if color.isValid():
            self.highlight_color_btn.setStyleSheet(f"background-color: {color.name()};")
            self.highlight_color_btn.setText(color.name())

    def choose_selection_color(self):
        """Выбор цвета выделения."""
        color = QColorDialog.getColor()
        if color.isValid():
            self.selection_color_btn.setStyleSheet(f"background-color: {color.name()};")
            self.selection_color_btn.setText(color.name())

    def choose_error_color(self):
        """Выбор цвета ошибок."""
        color = QColorDialog.getColor()
        if color.isValid():
            self.error_color_btn.setStyleSheet(f"background-color: {color.name()};")
            self.error_color_btn.setText(color.name())

    def load_settings(self):
        """Загружает настройки из конфига."""
        # Общие
        self.case_name_edit.setText(self.config.case_name)
        self.examiner_name_edit.setText(getattr(self.config, 'examiner', ''))
        self.organization_edit.setText(getattr(self.config, 'organization', ''))
        
        # Язык
        idx = self.language_combo.findData(self.config.get('language', 'ru'))
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)
        
        # Логирование
        self.log_level_combo.setCurrentText(self.config.log_level)
        self.log_file_edit.setText(self.config.log_file or '')
        
        # Пути
        self.case_directory_edit.setText(str(self.config.case_directory))
        self.evidence_directory_edit.setText(str(self.config.evidence_directory))
        self.reports_directory_edit.setText(str(self.config.reports_directory))
        self.temp_directory_edit.setText(str(self.config.temp_directory))
        
        # PFI
        self.pfi_model_path_edit.setText(self.config.pfi_model_path or '')
        self.pfi_threshold_spin.setValue(self.config.pfi_threshold)
        self.pfi_interval_spin.setValue(self.config.pfi_monitoring_interval)
        
        # Сеть
        self.max_packets_spin.setValue(self.config.max_packet_sniff)
        
        # Плагины
        self.plugin_dirs_edit.setText('\n'.join(self.config.plugin_directories))
        
        # Хеширование
        self.default_hash_algo.setCurrentText(self.config.default_hash_algorithm)
        self.verify_copy.setChecked(self.config.verify_copy)

    def save_settings(self):
        """Сохраняет настройки и закрывает диалог."""
        self._apply_settings()
        self.accept()

    def apply_settings(self):
        """Применяет настройки без закрытия."""
        self._apply_settings()

    def _apply_settings(self):
        """Внутренний метод применения настроек."""
        # Общие
        self.config.case_name = self.case_name_edit.text()
        self.config.examiner = self.examiner_name_edit.text()
        self.config.organization = self.organization_edit.text()
        
        # Язык
        self.config.language = self.language_combo.currentData()
        
        # Логирование
        self.config.log_level = self.log_level_combo.currentText()
        self.config.log_file = self.log_file_edit.text()
        
        # Пути
        self.config.case_directory = Path(self.case_directory_edit.text())
        self.config.evidence_directory = Path(self.evidence_directory_edit.text())
        self.config.reports_directory = Path(self.reports_directory_edit.text())
        self.config.temp_directory = Path(self.temp_directory_edit.text())
        
        # PFI
        self.config.pfi_model_path = self.pfi_model_path_edit.text()
        self.config.pfi_threshold = self.pfi_threshold_spin.value()
        self.config.pfi_monitoring_interval = self.pfi_interval_spin.value()
        
        # Сеть
        self.config.max_packet_sniff = self.max_packets_spin.value()
        
        # Плагины
        self.config.plugin_directories = [
            d.strip() for d in self.plugin_dirs_edit.toPlainText().split('\n') if d.strip()
        ]
        
        # Хеширование
        self.config.default_hash_algorithm = self.default_hash_algo.currentText()
        self.config.verify_copy = self.verify_copy.isChecked()
        
        # Сохранение в файл
        self.config.save("config.yaml")
        self.settings_changed.emit()
        
        logger.info("Настройки сохранены")