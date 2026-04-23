"""
Claster Forensic Toolkit - Professional GUI
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from claster.gui.main_window import MainWindow
from claster.gui.i18n import load_translations
from claster.core.config import get_config


def run_gui():
    app = QApplication(sys.argv)
    app.setApplicationName("Claster Forensic Toolkit")
    app.setOrganizationName("Claster")
    app.setApplicationVersion("2.0 Professional")

    icon_path = Path(__file__).parent.parent / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    config = get_config()
    language = config.get('language', 'ru')
    load_translations(app, language)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())