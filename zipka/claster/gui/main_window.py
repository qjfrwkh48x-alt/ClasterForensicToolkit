"""
Claster Forensic Toolkit - Professional GUI
Main Window with full forensic functionality
"""

import sys
import os
import json
import shutil
import importlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QMenuBar, QMenu, QToolBar, QStatusBar,
    QDockWidget, QTabWidget, QSplitter, QTreeView, QTextEdit,
    QFileDialog, QMessageBox, QVBoxLayout, QHBoxLayout, QWidget,
    QLabel, QProgressBar, QPushButton, QToolButton, QComboBox,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFrame, QSizePolicy, QSpacerItem, QDialog,
    QFormLayout, QDialogButtonBox, QDateTimeEdit, QCheckBox,
    QSpinBox, QDoubleSpinBox, QListWidget, QListWidgetItem,
    QScrollArea, QGroupBox, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import (
    Qt, QSettings, QTimer, QDir, 
    QThread, pyqtSignal, QSize, QPoint, QRect, QDateTime,
    QProcess, QUrl
)
from PyQt6.QtGui import (
    QAction, QIcon, QKeySequence, QFont, QColor, QPalette,
    QFontDatabase, QPixmap, QFileSystemModel, QTextCursor, QDesktopServices
)

from claster.gui.widgets.dashboard import DashboardWidget
from claster.gui.widgets.file_browser import FileBrowserWidget
from claster.gui.widgets.hex_viewer import HexViewerWidget
from claster.gui.widgets.terminal import TerminalWidget
from claster.gui.widgets.task_runner import TaskRunnerWidget
from claster.gui.widgets.pfi_trainer import PFITrainerWidget
from claster.gui.widgets.case_manager import CaseManagerWidget
from claster.gui.widgets.evidence_viewer import EvidenceViewerWidget
from claster.gui.dialogs.settings import SettingsDialog
from claster.gui.dialogs.about import AboutDialog
from claster.gui.dialogs.new_case import NewCaseDialog
from claster.gui.dialogs.function_args_dialog import FunctionArgsDialog
from claster.gui.dialogs.report_dialog import ReportDialog
from claster.gui.dialogs.plugin_manager import PluginManagerDialog
from claster.gui.translations import FUNC_TRANSLATIONS
from claster.gui.i18n import load_translations, get_supported_languages

from claster.core.config import get_config, Config
from claster.core.logger import get_logger, setup_logger
from claster.core.database import get_db, Database
from claster.core.events import event_bus, Event
from claster.core.plugins import plugin_manager, PluginBase
from claster.core.hashing import compute_hash, verify_hash
from claster.core.system import get_system_info, is_admin, request_elevation
from claster.core.utils import ensure_dir, timestamp, human_size

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """Главное окно Claster Forensic Toolkit."""
    
    def __init__(self):
        super().__init__()
        
        # Инициализация конфигурации и состояния
        self.config = get_config()
        self.current_case: Optional[Dict[str, Any]] = None
        self.db = get_db()
        self.workers: List[QThread] = []
        self.recent_cases: List[str] = []
        self.pfi_monitoring_active = False
        
        # Настройка окна
        self.setWindowTitle("Claster Forensic Toolkit - Professional Edition")
        self.setMinimumSize(1400, 900)
        
        # Загрузка стилей
        self.load_stylesheet()
        
        # Настройка UI
        self.setup_ui()
        
        # Восстановление состояния окна
        self.restore_state()
        
        # Настройка слушателей событий
        self.setup_event_listeners()
        
        # Загрузка плагинов
        self.load_plugins()
        
        # Обновление меню недавних дел
        self.load_recent_cases()
        
        # Таймер для автосохранения
        self.setup_autosave()
        
        logger.info("Главное окно инициализировано")

    def load_stylesheet(self):
        """Загружает таблицу стилей QSS."""
        style_path = Path(__file__).parent / "styles.qss"
        if style_path.exists():
            with open(style_path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())
        else:
            logger.warning(f"Файл стилей не найден: {style_path}")

    def setup_ui(self):
        """Настраивает пользовательский интерфейс."""
        self.create_menus()
        self.create_toolbar()
        self.create_statusbar()
        self.create_central_widget()
        self.create_dock_windows()
        self.setTabPosition(Qt.DockWidgetArea.AllDockWidgetAreas, QTabWidget.TabPosition.North)

    def create_menus(self):
        """Создаёт главное меню."""
        menubar = self.menuBar()
        menubar.setNativeMenuBar(False)  # Для единообразия на всех платформах

        # ==================== ФАЙЛ ====================
        file_menu = menubar.addMenu("&Файл")
        
        new_case_action = QAction("&Новое дело...", self)
        new_case_action.setShortcut(QKeySequence.StandardKey.New)
        new_case_action.setStatusTip("Создать новое криминалистическое дело")
        new_case_action.triggered.connect(self.new_case)
        file_menu.addAction(new_case_action)

        open_case_action = QAction("&Открыть дело...", self)
        open_case_action.setShortcut(QKeySequence.StandardKey.Open)
        open_case_action.setStatusTip("Открыть существующее дело")
        open_case_action.triggered.connect(self.open_case)
        file_menu.addAction(open_case_action)

        self.recent_menu = QMenu("&Недавние дела", self)
        file_menu.addMenu(self.recent_menu)

        file_menu.addSeparator()

        save_action = QAction("&Сохранить", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.setStatusTip("Сохранить текущее дело")
        save_action.triggered.connect(self.save_case)
        file_menu.addAction(save_action)

        save_as_action = QAction("Сохранить &как...", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.setStatusTip("Сохранить дело под новым именем")
        save_as_action.triggered.connect(self.save_case_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        import_action = QAction("&Импорт доказательств...", self)
        import_action.setShortcut(QKeySequence("Ctrl+I"))
        import_action.setStatusTip("Импортировать файлы как доказательства")
        import_action.triggered.connect(self.import_evidence)
        file_menu.addAction(import_action)

        export_action = QAction("&Экспорт отчёта...", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.setStatusTip("Экспортировать отчёт по делу")
        export_action.triggered.connect(self.export_report)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        settings_action = QAction("&Настройки...", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.setStatusTip("Настройки приложения")
        settings_action.triggered.connect(self.open_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        exit_action = QAction("&Выход", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.setStatusTip("Выйти из приложения")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # ==================== ПРАВКА ====================
        edit_menu = menubar.addMenu("&Правка")
        
        undo_action = QAction("&Отменить", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.setStatusTip("Отменить последнее действие")
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("&Повторить", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.setStatusTip("Повторить отменённое действие")
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        cut_action = QAction("&Вырезать", self)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        cut_action.setStatusTip("Вырезать выделенное")
        cut_action.triggered.connect(self.cut)
        edit_menu.addAction(cut_action)

        copy_action = QAction("&Копировать", self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.setStatusTip("Копировать выделенное")
        copy_action.triggered.connect(self.copy)
        edit_menu.addAction(copy_action)

        paste_action = QAction("&Вставить", self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.setStatusTip("Вставить из буфера обмена")
        paste_action.triggered.connect(self.paste)
        edit_menu.addAction(paste_action)

        edit_menu.addSeparator()

        find_action = QAction("&Найти...", self)
        find_action.setShortcut(QKeySequence.StandardKey.Find)
        find_action.setStatusTip("Поиск в текущем представлении")
        find_action.triggered.connect(self.find)
        edit_menu.addAction(find_action)

        find_next_action = QAction("Найти &далее", self)
        find_next_action.setShortcut(QKeySequence.StandardKey.FindNext)
        find_next_action.setStatusTip("Найти следующее вхождение")
        find_next_action.triggered.connect(self.find_next)
        edit_menu.addAction(find_next_action)

        # ==================== ВИД ====================
        view_menu = menubar.addMenu("&Вид")
        
        self.view_actions: Dict[str, QAction] = {}
        
        toolbar_action = QAction("&Панель инструментов", self, checkable=True)
        toolbar_action.setChecked(True)
        toolbar_action.setStatusTip("Показать/скрыть панель инструментов")
        toolbar_action.triggered.connect(self.toggle_toolbar)
        self.view_actions["toolbar"] = toolbar_action
        view_menu.addAction(toolbar_action)

        statusbar_action = QAction("&Строка состояния", self, checkable=True)
        statusbar_action.setChecked(True)
        statusbar_action.setStatusTip("Показать/скрыть строку состояния")
        statusbar_action.triggered.connect(self.toggle_statusbar)
        self.view_actions["statusbar"] = statusbar_action
        view_menu.addAction(statusbar_action)

        file_browser_action = QAction("&Навигатор файлов", self, checkable=True)
        file_browser_action.setChecked(True)
        file_browser_action.setStatusTip("Показать/скрыть навигатор файлов")
        file_browser_action.triggered.connect(self.toggle_file_browser)
        self.view_actions["file_browser"] = file_browser_action
        view_menu.addAction(file_browser_action)

        hex_viewer_action = QAction("&HEX-просмотрщик", self, checkable=True)
        hex_viewer_action.setChecked(True)
        hex_viewer_action.setStatusTip("Показать/скрыть HEX-просмотрщик")
        hex_viewer_action.triggered.connect(self.toggle_hex_viewer)
        self.view_actions["hex_viewer"] = hex_viewer_action
        view_menu.addAction(hex_viewer_action)

        properties_action = QAction("&Свойства", self, checkable=True)
        properties_action.setChecked(True)
        properties_action.setStatusTip("Показать/скрыть панель свойств")
        properties_action.triggered.connect(self.toggle_properties)
        self.view_actions["properties"] = properties_action
        view_menu.addAction(properties_action)

        terminal_action = QAction("&Терминал", self, checkable=True)
        terminal_action.setChecked(True)
        terminal_action.setStatusTip("Показать/скрыть терминал")
        terminal_action.triggered.connect(self.toggle_terminal)
        self.view_actions["terminal"] = terminal_action
        view_menu.addAction(terminal_action)

        view_menu.addSeparator()

        fullscreen_action = QAction("&Полноэкранный режим", self)
        fullscreen_action.setShortcut(QKeySequence("F11"))
        fullscreen_action.setCheckable(True)
        fullscreen_action.setStatusTip("Переключить полноэкранный режим")
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)

        zoom_in_action = QAction("&Увеличить", self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.setStatusTip("Увеличить масштаб")
        zoom_in_action.triggered.connect(self.zoom_in)
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("&Уменьшить", self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.setStatusTip("Уменьшить масштаб")
        zoom_out_action.triggered.connect(self.zoom_out)
        view_menu.addAction(zoom_out_action)

        zoom_reset_action = QAction("&Сбросить масштаб", self)
        zoom_reset_action.setShortcut(QKeySequence("Ctrl+0"))
        zoom_reset_action.setStatusTip("Сбросить масштаб")
        zoom_reset_action.triggered.connect(self.zoom_reset)
        view_menu.addAction(zoom_reset_action)

        view_menu.addSeparator()

        reset_layout_action = QAction("&Сбросить расположение окон", self)
        reset_layout_action.setStatusTip("Восстановить стандартное расположение окон")
        reset_layout_action.triggered.connect(self.reset_layout)
        view_menu.addAction(reset_layout_action)

        # ==================== ИНСТРУМЕНТЫ ====================
        tools_menu = menubar.addMenu("&Инструменты")
        self.populate_tools_menu(tools_menu)

        # ==================== АНАЛИЗ ====================
        analysis_menu = menubar.addMenu("&Анализ")
        
        memory_analysis_action = QAction("&Анализ памяти", self)
        memory_analysis_action.setStatusTip("Анализ дампа оперативной памяти")
        memory_analysis_action.triggered.connect(self.analyze_memory)
        analysis_menu.addAction(memory_analysis_action)

        disk_analysis_action = QAction("Анализ &диска", self)
        disk_analysis_action.setStatusTip("Анализ диска или образа")
        disk_analysis_action.triggered.connect(self.analyze_disk)
        analysis_menu.addAction(disk_analysis_action)

        network_analysis_action = QAction("Анализ &сети", self)
        network_analysis_action.setStatusTip("Анализ сетевого трафика")
        network_analysis_action.triggered.connect(self.analyze_network)
        analysis_menu.addAction(network_analysis_action)

        registry_analysis_action = QAction("Анализ &реестра", self)
        registry_analysis_action.setStatusTip("Анализ реестра Windows")
        registry_analysis_action.triggered.connect(self.analyze_registry)
        analysis_menu.addAction(registry_analysis_action)

        browser_analysis_action = QAction("Анализ &браузеров", self)
        browser_analysis_action.setStatusTip("Анализ истории браузеров")
        browser_analysis_action.triggered.connect(self.analyze_browser)
        analysis_menu.addAction(browser_analysis_action)

        analysis_menu.addSeparator()

        timeline_action = QAction("&Построить таймлайн", self)
        timeline_action.setShortcut(QKeySequence("Ctrl+T"))
        timeline_action.setStatusTip("Построить временную шкалу событий")
        timeline_action.triggered.connect(self.build_timeline)
        analysis_menu.addAction(timeline_action)

        correlation_action = QAction("&Корреляция событий", self)
        correlation_action.setStatusTip("Найти связи между событиями")
        correlation_action.triggered.connect(self.correlate_events)
        analysis_menu.addAction(correlation_action)

        # ==================== PFI ====================
        pfi_menu = menubar.addMenu("&PFI")
        
        pfi_start_action = QAction("&Запустить мониторинг", self)
        pfi_start_action.setShortcut(QKeySequence("Ctrl+Shift+M"))
        pfi_start_action.setStatusTip("Запустить мониторинг PFI в реальном времени")
        pfi_start_action.triggered.connect(self.start_pfi_monitoring)
        pfi_menu.addAction(pfi_start_action)

        pfi_stop_action = QAction("&Остановить мониторинг", self)
        pfi_stop_action.setShortcut(QKeySequence("Ctrl+Shift+X"))
        pfi_stop_action.setStatusTip("Остановить мониторинг PFI")
        pfi_stop_action.triggered.connect(self.stop_pfi_monitoring)
        pfi_menu.addAction(pfi_stop_action)

        pfi_menu.addSeparator()

        pfi_train_action = QAction("&Обучить модель...", self)
        pfi_train_action.setStatusTip("Обучить модель PFI на датасете")
        pfi_train_action.triggered.connect(self.train_pfi_model)
        pfi_menu.addAction(pfi_train_action)

        pfi_load_action = QAction("&Загрузить модель...", self)
        pfi_load_action.setStatusTip("Загрузить предобученную модель PFI")
        pfi_load_action.triggered.connect(self.load_pfi_model)
        pfi_menu.addAction(pfi_load_action)

        pfi_menu.addSeparator()

        pfi_forecast_action = QAction("&Прогноз угроз", self)
        pfi_forecast_action.setStatusTip("Показать прогноз угроз на основе PFI")
        pfi_forecast_action.triggered.connect(self.show_pfi_forecast)
        pfi_menu.addAction(pfi_forecast_action)

        pfi_export_action = QAction("&Экспорт датасета", self)
        pfi_export_action.setStatusTip("Экспортировать данные для обучения")
        pfi_export_action.triggered.connect(self.export_training_dataset)
        pfi_menu.addAction(pfi_export_action)

        # ==================== ПЛАГИНЫ ====================
        self.plugins_menu = menubar.addMenu("&Плагины")
        
        manage_plugins_action = QAction("&Управление плагинами...", self)
        manage_plugins_action.setStatusTip("Установка и настройка плагинов")
        manage_plugins_action.triggered.connect(self.manage_plugins)
        self.plugins_menu.addAction(manage_plugins_action)
        self.plugins_menu.addSeparator()

        # ==================== ОКНА ====================
        windows_menu = menubar.addMenu("&Окна")
        
        cascade_action = QAction("&Каскадом", self)
        cascade_action.setStatusTip("Расположить окна каскадом")
        cascade_action.triggered.connect(self.cascade_windows)
        windows_menu.addAction(cascade_action)

        tile_action = QAction("&Плиткой", self)
        tile_action.setStatusTip("Расположить окна плиткой")
        tile_action.triggered.connect(self.tile_windows)
        windows_menu.addAction(tile_action)

        close_all_action = QAction("&Закрыть все", self)
        close_all_action.setStatusTip("Закрыть все открытые окна")
        close_all_action.triggered.connect(self.close_all_windows)
        windows_menu.addAction(close_all_action)

        windows_menu.addSeparator()

        # ==================== СПРАВКА ====================
        help_menu = menubar.addMenu("&Справка")
        
        help_action = QAction("&Документация", self)
        help_action.setShortcut(QKeySequence.StandardKey.HelpContents)
        help_action.setStatusTip("Открыть документацию")
        help_action.triggered.connect(self.open_documentation)
        help_menu.addAction(help_action)

        check_updates_action = QAction("&Проверить обновления...", self)
        check_updates_action.setStatusTip("Проверить наличие обновлений")
        check_updates_action.triggered.connect(self.check_updates)
        help_menu.addAction(check_updates_action)

        help_menu.addSeparator()

        about_action = QAction("&О программе", self)
        about_action.setStatusTip("Информация о программе")
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def populate_tools_menu(self, menu: QMenu):
        """Заполняет меню инструментов функциями всех модулей."""
        modules = [
            ("core", "Ядро"),
            ("disk", "Диск"),
            ("registry", "Реестр"),
            ("memory", "Память"),
            ("network", "Сеть"),
            ("stego", "Стеганография"),
            ("crypto", "Криптография"),
            ("metadata", "Метаданные"),
            ("browser", "Браузеры"),
            ("mobile", "Мобильная"),
            ("report", "Отчёты"),
        ]

        for mod_name, mod_label in modules:
            try:
                module = importlib.import_module(f"claster.{mod_name}")
                if hasattr(module, '__all__'):
                    submenu = menu.addMenu(mod_label)
                    funcs = sorted([f for f in module.__all__ if not f.startswith('_')])
                    
                    for func_name in funcs:
                        display_name = FUNC_TRANSLATIONS.get(func_name, func_name)
                        action = QAction(display_name, self)
                        action.setStatusTip(f"Выполнить {display_name}")
                        action.triggered.connect(
                            lambda checked, m=mod_name, f=func_name: self.run_tool(m, f)
                        )
                        submenu.addAction(action)
            except ImportError as e:
                logger.warning(f"Модуль {mod_name} недоступен: {e}")

    def create_toolbar(self):
        """Создаёт панель инструментов."""
        self.toolbar = QToolBar("Главная панель", self)
        self.toolbar.setObjectName("MainToolbar")
        self.toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        # Кнопка нового дела
        new_btn = QToolButton()
        new_btn.setText("Новое дело")
        new_btn.setToolTip("Создать новое дело")
        new_btn.setStatusTip("Создать новое криминалистическое дело")
        new_btn.clicked.connect(self.new_case)
        self.toolbar.addWidget(new_btn)

        # Кнопка открытия дела
        open_btn = QToolButton()
        open_btn.setText("Открыть")
        open_btn.setToolTip("Открыть существующее дело")
        open_btn.setStatusTip("Открыть существующее дело")
        open_btn.clicked.connect(self.open_case)
        self.toolbar.addWidget(open_btn)

        # Кнопка сохранения
        save_btn = QToolButton()
        save_btn.setText("Сохранить")
        save_btn.setToolTip("Сохранить текущее дело")
        save_btn.setStatusTip("Сохранить текущее дело")
        save_btn.clicked.connect(self.save_case)
        self.toolbar.addWidget(save_btn)

        self.toolbar.addSeparator()

        # Кнопка импорта
        import_btn = QToolButton()
        import_btn.setText("Импорт")
        import_btn.setToolTip("Импортировать доказательства")
        import_btn.setStatusTip("Импортировать файлы как доказательства")
        import_btn.clicked.connect(self.import_evidence)
        self.toolbar.addWidget(import_btn)

        # Кнопка экспорта
        export_btn = QToolButton()
        export_btn.setText("Экспорт")
        export_btn.setToolTip("Экспортировать отчёт")
        export_btn.setStatusTip("Экспортировать отчёт по делу")
        export_btn.clicked.connect(self.export_report)
        self.toolbar.addWidget(export_btn)

        self.toolbar.addSeparator()

        # Кнопка быстрого анализа
        analyze_btn = QToolButton()
        analyze_btn.setText("Анализ")
        analyze_btn.setToolTip("Быстрый анализ")
        analyze_btn.setStatusTip("Запустить быстрый анализ")
        analyze_btn.clicked.connect(self.quick_analyze)
        self.toolbar.addWidget(analyze_btn)

        # Кнопка PFI
        pfi_btn = QToolButton()
        pfi_btn.setText("PFI")
        pfi_btn.setToolTip("Мониторинг PFI")
        pfi_btn.setStatusTip("Запустить/остановить мониторинг PFI")
        pfi_btn.clicked.connect(self.toggle_pfi_monitoring)
        self.toolbar.addWidget(pfi_btn)
        self.pfi_toolbar_btn = pfi_btn

        self.toolbar.addSeparator()

        # Выбор активного модуля
        self.module_selector = QComboBox()
        self.module_selector.setToolTip("Выберите модуль для быстрого доступа")
        self.module_selector.addItems([
            "Все инструменты", "Память", "Диск", "Сеть", "Реестр", "Браузеры"
        ])
        self.module_selector.currentTextChanged.connect(self.on_module_selected)
        self.toolbar.addWidget(self.module_selector)

        # Поиск по инструментам
        self.toolbar.addSeparator()
        search_label = QLabel("Поиск:")
        self.toolbar.addWidget(search_label)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск инструмента...")
        self.search_edit.setMaximumWidth(200)
        self.search_edit.textChanged.connect(self.on_search_tools)
        self.toolbar.addWidget(self.search_edit)

        # Растягивающийся спейсер
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.toolbar.addWidget(spacer)

        # Индикатор PFI
        self.pfi_indicator = QLabel("🔴 PFI: выкл")
        self.pfi_indicator.setStyleSheet("color: #888; padding: 0 8px;")
        self.toolbar.addWidget(self.pfi_indicator)

    def create_statusbar(self):
        """Создаёт строку состояния."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        # Основной статус
        self.status_label = QLabel("Готов")
        self.status_label.setMinimumWidth(200)
        self.statusbar.addWidget(self.status_label)

        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.statusbar.addPermanentWidget(self.progress_bar)

        # Информация о деле
        self.case_label = QLabel("📁 Дело: не открыто")
        self.case_label.setStyleSheet("padding: 0 8px;")
        self.statusbar.addPermanentWidget(self.case_label)

        # Использование памяти
        self.memory_label = QLabel("💾 RAM: --")
        self.memory_label.setStyleSheet("padding: 0 8px;")
        self.statusbar.addPermanentWidget(self.memory_label)

        # Версия
        version_label = QLabel("v2.0 Professional")
        version_label.setStyleSheet("padding: 0 8px; color: #888;")
        self.statusbar.addPermanentWidget(version_label)

        # Таймер обновления статуса
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status_info)
        self.status_timer.start(2000)

    def create_central_widget(self):
        """Создаёт центральный виджет с вкладками."""
        self.central_tabs = QTabWidget()
        self.central_tabs.setTabsClosable(True)
        self.central_tabs.tabCloseRequested.connect(self.close_tab)
        self.central_tabs.setMovable(True)
        self.setCentralWidget(self.central_tabs)

        # Дашборд
        self.dashboard = DashboardWidget()
        self.central_tabs.addTab(self.dashboard, "📊 Дашборд")

        # Выполнение задач
        self.task_runner = TaskRunnerWidget()
        self.central_tabs.addTab(self.task_runner, "⚙️ Задачи")

        # Обучение PFI
        self.pfi_trainer = PFITrainerWidget()
        self.central_tabs.addTab(self.pfi_trainer, "🧠 Обучение PFI")

        # Результаты анализа
        self.results_widget = QTextEdit()
        self.results_widget.setReadOnly(True)
        self.results_widget.setFont(QFont("Consolas", 10))
        self.central_tabs.addTab(self.results_widget, "📋 Результаты")

    def create_dock_windows(self):
        # Левый док: Файловый браузер
        self.file_browser_dock = QDockWidget("📁 Файловый браузер", self)
        self.file_browser_dock.setObjectName("FileBrowserDock")
        self.file_browser_dock.setMinimumWidth(250)
        self.file_browser_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.file_browser = FileBrowserWidget()
        self.file_browser.file_selected.connect(self.on_file_selected)
        self.file_browser_dock.setWidget(self.file_browser)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.file_browser_dock)

        # Правый док: Просмотр с вкладками и скроллом
        self.right_dock = QDockWidget("🔍 Просмотр", self)
        self.right_dock.setObjectName("ViewerDock")
        self.right_dock.setMinimumWidth(350)
        self.right_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        
        right_tabs = QTabWidget()
        right_tabs.setTabPosition(QTabWidget.TabPosition.North)
        right_tabs.setMovable(True)
        
        # HEX-просмотрщик в скроллируемом контейнере
        hex_scroll = QScrollArea()
        hex_scroll.setWidgetResizable(True)
        hex_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        hex_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.hex_viewer = HexViewerWidget()
        hex_scroll.setWidget(self.hex_viewer)
        right_tabs.addTab(hex_scroll, "HEX")
        
        # Просмотр улик в скроллируемом контейнере
        evidence_scroll = QScrollArea()
        evidence_scroll.setWidgetResizable(True)
        self.evidence_viewer = EvidenceViewerWidget()
        evidence_scroll.setWidget(self.evidence_viewer)
        right_tabs.addTab(evidence_scroll, "📄 Улики")
        
        # Метаданные
        metadata_scroll = QScrollArea()
        metadata_scroll.setWidgetResizable(True)
        self.metadata_viewer = QTextEdit()
        self.metadata_viewer.setReadOnly(True)
        metadata_scroll.setWidget(self.metadata_viewer)
        right_tabs.addTab(metadata_scroll, "ℹ️ Метаданные")
        
        self.right_dock.setWidget(right_tabs)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.right_dock)

        # Нижний док: Терминал и управление делом
        self.bottom_dock = QDockWidget("💻 Терминал и дело", self)
        self.bottom_dock.setObjectName("BottomDock")
        self.bottom_dock.setMinimumHeight(200)
        self.bottom_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        
        bottom_tabs = QTabWidget()
        bottom_tabs.setTabPosition(QTabWidget.TabPosition.South)
        bottom_tabs.setMovable(True)
        
        # Терминал
        self.terminal = TerminalWidget()
        bottom_tabs.addTab(self.terminal, "💻 Терминал")
        
        # Управление делом
        self.case_manager = CaseManagerWidget()
        self.case_manager.case_updated.connect(self.on_case_updated)
        bottom_tabs.addTab(self.case_manager, "📂 Управление делом")
        
        # Лог событий
        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.setFont(QFont("Consolas", 9))
        bottom_tabs.addTab(self.event_log, "📜 Лог событий")
        
        self.bottom_dock.setWidget(bottom_tabs)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.bottom_dock)

        # Установка начальных размеров
        self.resizeDocks(
            [self.file_browser_dock, self.right_dock],
            [280, 420],
            Qt.Orientation.Horizontal
        )
        self.resizeDocks(
            [self.bottom_dock],
            [220],
            Qt.Orientation.Vertical
        )
        
        # Запрет перекрытия вкладок
        self.setDockOptions(
            QMainWindow.DockOption.AnimatedDocks |
            QMainWindow.DockOption.AllowNestedDocks |
            QMainWindow.DockOption.GroupedDragging
        )

    def setup_event_listeners(self):
        """Настраивает слушатели событий."""
        event_bus.subscribe("pfi.alert", self.on_pfi_alert)
        event_bus.subscribe("task.completed", self.on_task_completed)
        event_bus.subscribe("task.error", self.on_task_error)
        event_bus.subscribe("case.updated", self.on_case_updated)
        event_bus.subscribe("evidence.added", self.on_evidence_added)

    def setup_autosave(self):
        """Настраивает автосохранение."""
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self.auto_save)
        self.autosave_timer.start(300000)  # Каждые 5 минут

    def load_plugins(self):
        """Загружает плагины."""
        try:
            plugin_manager.discover_plugins()
            plugins = plugin_manager.list_plugins()
            
            for plugin_info in plugins:
                action = QAction(plugin_info['name'], self)
                action.setStatusTip(plugin_info.get('description', ''))
                action.triggered.connect(
                    lambda checked, p=plugin_info['name']: self.run_plugin(p)
                )
                self.plugins_menu.addAction(action)
            
            logger.info(f"Загружено плагинов: {len(plugins)}")
        except Exception as e:
            logger.error(f"Ошибка загрузки плагинов: {e}")

    def load_recent_cases(self):
        """Загружает список недавних дел."""
        settings = QSettings("Claster", "ForensicToolkit")
        self.recent_cases = settings.value("recentCases", [])
        if isinstance(self.recent_cases, str):
            self.recent_cases = [self.recent_cases]
        self.update_recent_menu()

    def update_recent_menu(self):
        """Обновляет меню недавних дел."""
        self.recent_menu.clear()
        
        if not self.recent_cases:
            empty_action = QAction("(Нет недавних дел)", self)
            empty_action.setEnabled(False)
            self.recent_menu.addAction(empty_action)
            return
        
        for case_path in self.recent_cases[:10]:
            if not case_path or not Path(case_path).exists():
                continue
            action = QAction(Path(case_path).stem, self)
            action.setData(case_path)
            action.setStatusTip(f"Открыть {case_path}")
            action.triggered.connect(
                lambda checked, p=case_path: self.open_case_by_path(p)
            )
            self.recent_menu.addAction(action)
        
        self.recent_menu.addSeparator()
        clear_action = QAction("Очистить список", self)
        clear_action.triggered.connect(self.clear_recent_cases)
        self.recent_menu.addAction(clear_action)

    def add_recent_case(self, path: str):
        """Добавляет дело в список недавних."""
        if path in self.recent_cases:
            self.recent_cases.remove(path)
        self.recent_cases.insert(0, path)
        self.recent_cases = self.recent_cases[:10]
        
        settings = QSettings("Claster", "ForensicToolkit")
        settings.setValue("recentCases", self.recent_cases)
        self.update_recent_menu()

    def clear_recent_cases(self):
        """Очищает список недавних дел."""
        self.recent_cases = []
        settings = QSettings("Claster", "ForensicToolkit")
        settings.setValue("recentCases", [])
        self.update_recent_menu()

    def restore_state(self):
        """Восстанавливает состояние окна."""
        settings = QSettings("Claster", "ForensicToolkit")
        
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        state = settings.value("windowState")
        if state:
            self.restoreState(state)

    def closeEvent(self, event):
        """Обработчик закрытия окна."""
        # Остановка всех воркеров
        for worker in self.workers:
            if worker.isRunning():
                worker.quit()
                worker.wait(1000)
        
        # Остановка мониторинга PFI
        if self.pfi_monitoring_active:
            self.stop_pfi_monitoring()
        
        # Сохранение состояния
        settings = QSettings("Claster", "ForensicToolkit")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        
        # Автосохранение дела
        if self.current_case:
            self.save_case()
        
        event.accept()

    # ==================== Слоты меню Файл ====================
    
    def new_case(self):
        """Создаёт новое дело."""
        dialog = NewCaseDialog(self)
        if dialog.exec():
            case_info = dialog.get_case_info()
            self.current_case = case_info
            self.case_label.setText(f"📁 Дело: {case_info['name']}")
            self.case_manager.create_case(case_info)
            self.add_recent_case(case_info['directory'])
            self.status_label.setText(f"Создано новое дело: {case_info['name']}")
            logger.info(f"Создано дело: {case_info['name']}")

    def open_case(self):
        """Открывает существующее дело."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Открыть дело", "",
            "Claster Case (*.claster);;Все файлы (*.*)"
        )
        if path:
            self.open_case_by_path(path)

    def open_case_by_path(self, path: str):
        """Открывает дело по указанному пути."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                case_info = json.load(f)
            
            self.current_case = case_info
            self.case_label.setText(f"📁 Дело: {case_info.get('name', Path(path).stem)}")
            self.case_manager.load_case(case_info)
            self.add_recent_case(path)
            self.status_label.setText(f"Открыто дело: {case_info.get('name', 'Без названия')}")
            logger.info(f"Открыто дело: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть дело:\n{e}")
            logger.error(f"Ошибка открытия дела {path}: {e}")

    def save_case(self):
        """Сохраняет текущее дело."""
        if not self.current_case:
            QMessageBox.warning(self, "Предупреждение", "Нет открытого дела для сохранения.")
            return
        
        case_path = self.current_case.get('path')
        if not case_path:
            self.save_case_as()
            return
        
        self._save_case_to_path(case_path)

    def save_case_as(self):
        """Сохраняет дело под новым именем."""
        if not self.current_case:
            QMessageBox.warning(self, "Предупреждение", "Нет открытого дела для сохранения.")
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить дело как", "",
            "Claster Case (*.claster);;Все файлы (*.*)"
        )
        if path:
            self._save_case_to_path(path)

    def _save_case_to_path(self, path: str):
        """Сохраняет дело по указанному пути."""
        try:
            self.current_case['path'] = path
            self.current_case['last_modified'] = datetime.now().isoformat()
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.current_case, f, indent=2, ensure_ascii=False)
            
            self.add_recent_case(path)
            self.status_label.setText(f"Дело сохранено: {Path(path).name}")
            logger.info(f"Дело сохранено: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить дело:\n{e}")
            logger.error(f"Ошибка сохранения дела: {e}")

    def import_evidence(self):
        """Импортирует доказательства."""
        if not self.current_case:
            QMessageBox.warning(self, "Предупреждение", "Сначала создайте или откройте дело.")
            return
        
        files, _ = QFileDialog.getOpenFileNames(
            self, "Выберите файлы для импорта", "",
            "Все файлы (*.*);;Образы дисков (*.dd *.e01 *.aff4);;"
            "Дампы памяти (*.mem *.dmp *.raw);;Логи (*.evtx *.log)"
        )
        
        if files:
            self.case_manager.add_evidence_files(files)
            self.status_label.setText(f"Импортировано файлов: {len(files)}")

    def export_report(self):
        """Экспортирует отчёт."""
        if not self.current_case:
            QMessageBox.warning(self, "Предупреждение", "Нет открытого дела для экспорта.")
            return
        
        dialog = ReportDialog(self)
        if dialog.exec():
            params = dialog.get_parameters()
            self.status_label.setText("Генерация отчёта...")
            # Запуск генерации в фоне
            self.run_tool("report", "generate_html_report", params)

    def open_settings(self):
        """Открывает диалог настроек."""
        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self.apply_settings)
        dialog.exec()

    def apply_settings(self):
        """Применяет настройки."""
        self.config = get_config(reload=True)
        self.load_stylesheet()
        
        # Обновление языка
        lang = self.config.get('language', 'ru')
        load_translations(QApplication.instance(), lang)
        
        self.status_label.setText("Настройки применены")

    # ==================== Слоты меню Правка ====================
    
    def undo(self):
        """Отменяет последнее действие."""
        focused = QApplication.focusWidget()
        if hasattr(focused, 'undo'):
            focused.undo()

    def redo(self):
        """Повторяет отменённое действие."""
        focused = QApplication.focusWidget()
        if hasattr(focused, 'redo'):
            focused.redo()

    def cut(self):
        """Вырезает выделенный текст."""
        focused = QApplication.focusWidget()
        if hasattr(focused, 'cut'):
            focused.cut()

    def copy(self):
        """Копирует выделенный текст."""
        focused = QApplication.focusWidget()
        if hasattr(focused, 'copy'):
            focused.copy()

    def paste(self):
        """Вставляет текст из буфера."""
        focused = QApplication.focusWidget()
        if hasattr(focused, 'paste'):
            focused.paste()

    def find(self):
        """Открывает диалог поиска."""
        QMessageBox.information(self, "Поиск", "Функция поиска в разработке")

    def find_next(self):
        """Ищет следующее вхождение."""
        pass

    # ==================== Слоты меню Вид ====================
    
    def toggle_toolbar(self, checked: bool):
        """Показывает/скрывает панель инструментов."""
        self.toolbar.setVisible(checked)

    def toggle_statusbar(self, checked: bool):
        """Показывает/скрывает строку состояния."""
        self.statusbar.setVisible(checked)

    def toggle_file_browser(self, checked: bool):
        """Показывает/скрывает файловый браузер."""
        self.file_browser_dock.setVisible(checked)

    def toggle_hex_viewer(self, checked: bool):
        """Показывает/скрывает HEX-просмотрщик."""
        self.right_dock.setVisible(checked)

    def toggle_properties(self, checked: bool):
        """Показывает/скрывает панель свойств."""
        pass  # Реализуется отдельно

    def toggle_terminal(self, checked: bool):
        """Показывает/скрывает терминал."""
        self.bottom_dock.setVisible(checked)

    def toggle_fullscreen(self, checked: bool):
        """Переключает полноэкранный режим."""
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()

    def zoom_in(self):
        """Увеличивает масштаб."""
        current = self.central_tabs.currentWidget()
        if hasattr(current, 'zoomIn'):
            current.zoomIn()

    def zoom_out(self):
        """Уменьшает масштаб."""
        current = self.central_tabs.currentWidget()
        if hasattr(current, 'zoomOut'):
            current.zoomOut()

    def zoom_reset(self):
        """Сбрасывает масштаб."""
        current = self.central_tabs.currentWidget()
        if hasattr(current, 'zoomReset'):
            current.zoomReset()

    def reset_layout(self):
        """Сбрасывает расположение окон."""
        self.restoreState(self.saveState())

    # ==================== Слоты меню Анализ ====================
    
    def analyze_memory(self):
        """Запускает анализ памяти."""
        self.central_tabs.setCurrentWidget(self.task_runner)
        self.task_runner.run_function("memory", "list_processes")

    def analyze_disk(self):
        """Запускает анализ диска."""
        self.central_tabs.setCurrentWidget(self.task_runner)
        self.task_runner.run_function("disk", "parse_mft")

    def analyze_network(self):
        """Запускает анализ сети."""
        self.central_tabs.setCurrentWidget(self.task_runner)
        self.task_runner.run_function("network", "sniff_packets")

    def analyze_registry(self):
        """Запускает анализ реестра."""
        self.central_tabs.setCurrentWidget(self.task_runner)
        self.task_runner.run_function("registry", "parse_hive")

    def analyze_browser(self):
        """Запускает анализ браузеров."""
        self.central_tabs.setCurrentWidget(self.task_runner)
        self.task_runner.run_function("browser", "get_chrome_history")

    def build_timeline(self):
        """Строит временную шкалу."""
        QMessageBox.information(self, "Таймлайн", "Построение временной шкалы в разработке")

    def correlate_events(self):
        """Коррелирует события."""
        QMessageBox.information(self, "Корреляция", "Корреляция событий в разработке")

    # ==================== Слоты меню PFI ====================
    
    def start_pfi_monitoring(self):
        """Запускает мониторинг PFI."""
        from claster.pfi.monitor import start_monitoring, is_monitoring
        
        if is_monitoring():
            QMessageBox.information(self, "PFI", "Мониторинг уже запущен")
            return
        
        threshold = self.config.get('pfi_threshold', 0.75)
        interval = self.config.get('pfi_monitoring_interval', 5)
        
        try:
            if start_monitoring(interval, threshold):
                self.pfi_monitoring_active = True
                self.pfi_indicator.setText("🟢 PFI: активен")
                self.pfi_indicator.setStyleSheet("color: #0f0; padding: 0 8px;")
                self.pfi_toolbar_btn.setText("⏹️ Остановить PFI")
                self.status_label.setText("✅ Мониторинг PFI запущен")
                logger.info("Мониторинг PFI запущен")
            else:
                QMessageBox.warning(
                    self, "Ошибка", 
                    "Не удалось запустить мониторинг PFI.\n"
                    "Проверьте, что модель обучена и находится в правильной директории.\n"
                    "Путь к модели можно указать в настройках."
                )
        except FileNotFoundError as e:
            QMessageBox.warning(
                self, "Модель не найдена",
                f"Модель PFI не найдена.\n\n{e}\n\n"
                "Пожалуйста, обучите модель в разделе «Обучение PFI» "
                "или укажите путь к существующей модели в настройках."
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить мониторинг:\n{e}")
            logger.error(f"Ошибка запуска PFI: {e}")

    def stop_pfi_monitoring(self):
        from claster.pfi.monitor import stop_monitoring
        
        stop_monitoring()
        self.pfi_monitoring_active = False
        self.pfi_indicator.setText("🔴 PFI: выкл")
        self.pfi_indicator.setStyleSheet("color: #888; padding: 0 8px;")
        self.pfi_toolbar_btn.setText("▶️ Запустить PFI")
        self.status_label.setText("⏹️ Мониторинг PFI остановлен")
        logger.info("Мониторинг PFI остановлен")

        
        stop_monitoring()
        self.pfi_monitoring_active = False
        self.pfi_indicator.setText("🔴 PFI: выкл")
        self.pfi_indicator.setStyleSheet("color: #888; padding: 0 8px;")
        self.status_label.setText("Мониторинг PFI остановлен")
        logger.info("Мониторинг PFI остановлен")

    def toggle_pfi_monitoring(self):
        """Переключает мониторинг PFI."""
        if self.pfi_monitoring_active:
            self.stop_pfi_monitoring()
        else:
            self.start_pfi_monitoring()

    def train_pfi_model(self):
        """Открывает вкладку обучения PFI."""
        self.central_tabs.setCurrentWidget(self.pfi_trainer)

    def load_pfi_model(self):
        """Загружает модель PFI."""
        path = QFileDialog.getExistingDirectory(
            self, "Выберите директорию с моделью PFI"
        )
        if path:
            from claster.pfi.inference import load_model
            try:
                load_model(path)
                self.config.pfi_model_path = path
                self.config.save("config.yaml")
                QMessageBox.information(self, "Успех", f"Модель загружена из {path}")
                logger.info(f"Модель PFI загружена: {path}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить модель:\n{e}")

    def show_pfi_forecast(self):
        """Показывает прогноз угроз PFI."""
        from claster.pfi.inference import predict_attack_probability
        from claster.pfi.monitor import extract_sequence
        
        seq = extract_sequence(50)
        if seq:
            prob, label, probs = predict_attack_probability(seq)
            
            msg = f"Текущий уровень риска: {label}\n"
            msg += f"Вероятность атаки: {prob:.1%}\n\n"
            msg += "Детальные вероятности:\n"
            for cls, p in probs.items():
                msg += f"  {cls}: {p:.1%}\n"
            
            QMessageBox.information(self, "Прогноз PFI", msg)
        else:
            QMessageBox.warning(self, "Прогноз PFI", "Недостаточно данных для прогноза")

    def export_training_dataset(self):
        """Экспортирует датасет для обучения."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт датасета", "",
            "CSV (*.csv);;JSON (*.json)"
        )
        if path:
            from claster.pfi.train import export_training_dataset
            export_training_dataset(path)
            self.status_label.setText(f"Датасет экспортирован: {Path(path).name}")

    # ==================== Слоты меню Плагины ====================
    
    def manage_plugins(self):
        """Открывает диалог управления плагинами."""
        dialog = PluginManagerDialog(self)
        dialog.exec()
        # Обновление меню плагинов
        self.plugins_menu.clear()
        self.load_plugins()

    def run_plugin(self, plugin_name: str):
        """Запускает плагин."""
        plugin = plugin_manager.get_plugin(plugin_name)
        if plugin and hasattr(plugin, 'run'):
            try:
                plugin.run()
                self.status_label.setText(f"Плагин {plugin_name} запущен")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка выполнения плагина:\n{e}")

    # ==================== Слоты меню Окна ====================
    
    def cascade_windows(self):
        """Располагает окна каскадом."""
        self.central_tabs.cascadeSubWindows()

    def tile_windows(self):
        """Располагает окна плиткой."""
        self.central_tabs.tileSubWindows()

    def close_all_windows(self):
        """Закрывает все окна."""
        while self.central_tabs.count() > 0:
            self.central_tabs.removeTab(0)

    # ==================== Слоты меню Справка ====================
    
    def open_documentation(self):
        """Открывает документацию."""
        QDesktopServices.openUrl(QUrl("https://github.com/claster/forensic-toolkit/wiki"))

    def check_updates(self):
        """Проверяет обновления."""
        QMessageBox.information(self, "Обновления", "У вас установлена последняя версия.")

    def show_about(self):
        """Показывает диалог о программе."""
        dialog = AboutDialog(self)
        dialog.exec()

    # ==================== Вспомогательные слоты ====================
    
    def on_file_selected(self, path: str):
        """Обработчик выбора файла в браузере."""
        self.hex_viewer.open_file(path)
        self.evidence_viewer.load_file(path)
        self.status_label.setText(f"Выбран: {path}")
        
        # Добавляем в историю
        self.file_browser_dock.setWindowTitle(f"📁 Файловый браузер - {Path(path).parent}")

    def on_case_updated(self, case_info: dict):
        """Обработчик обновления дела."""
        self.current_case = case_info
        self.case_label.setText(f"📁 Дело: {case_info.get('name', 'Без названия')}")

    def on_evidence_added(self, event: Event):
        """Обработчик добавления улики."""
        self.status_label.setText(f"Добавлена улика: {event.data.get('name', '')}")

    def on_pfi_alert(self, event: Event):
        """Обработчик алерта PFI."""
        data = event.data
        prob = data.get('probability', 0)
        label = data.get('label', 'unknown')
        
        self.event_log.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] "
            f"⚠️ PFI Alert: {label} (вероятность: {prob:.1%})"
        )
        
        if prob > 0.8:
            QMessageBox.warning(
                self, "⚠️ Обнаружена угроза!",
                f"PFI обнаружил потенциальную угрозу!\n\n"
                f"Тип: {label}\n"
                f"Вероятность: {prob:.1%}\n\n"
                f"Рекомендуется немедленно провести расследование."
            )

    def on_task_completed(self, event: Event):
        """Обработчик завершения задачи."""
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Задача выполнена: {event.data.get('name', '')}")
        
        # Добавляем результат в соответствующую вкладку
        result = event.data.get('result')
        if result:
            self.results_widget.append(f"\n=== {event.data.get('name')} ===\n{result}")

    def on_task_error(self, event: Event):
        """Обработчик ошибки задачи."""
        self.progress_bar.setVisible(False)
        error = event.data.get('error', 'Неизвестная ошибка')
        self.status_label.setText(f"Ошибка: {error}")
        self.event_log.append(f"[ERROR] {event.data.get('name')}: {error}")

    def on_module_selected(self, module: str):
        """Обработчик выбора модуля в селекторе."""
        if module == "Все инструменты":
            return
        # Можно фильтровать отображение инструментов

    def on_search_tools(self, text: str):
        """Обработчик поиска по инструментам."""
        # Фильтрация инструментов
        pass

    def close_tab(self, index: int):
        """Закрывает вкладку."""
        if index > 0:  # Первую вкладку (Дашборд) не закрываем
            self.central_tabs.removeTab(index)

    def run_tool(self, module: str, func: str, args: dict = None):
        """Запускает инструмент."""
        self.central_tabs.setCurrentWidget(self.task_runner)
        self.task_runner.run_function(module, func, args)
        self.progress_bar.setVisible(True)
        self.status_label.setText(f"Запуск: {module}.{func}")

    def quick_analyze(self):
        """Запускает быстрый анализ."""
        if not self.current_case:
            QMessageBox.warning(self, "Предупреждение", "Сначала откройте дело.")
            return
        
        # Запуск базового набора анализов
        self.run_tool("memory", "list_processes")
        self.run_tool("network", "sniff_packets")

    def update_status_info(self):
        """Обновляет информацию в строке состояния."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            used_gb = mem.used / (1024**3)
            total_gb = mem.total / (1024**3)
            self.memory_label.setText(f"💾 RAM: {used_gb:.1f}/{total_gb:.1f} ГБ")
        except ImportError:
            pass

    def auto_save(self):
        """Автоматическое сохранение."""
        if self.current_case:
            self.save_case()
            logger.debug("Автосохранение выполнено")