"""
Internationalization support for Claster GUI.
"""

from PyQt6.QtCore import QTranslator, QLocale, QLibraryInfo
from PyQt6.QtWidgets import QApplication
from pathlib import Path

_translators = {}


def load_translations(app: QApplication, language: str = None):
    """Load translation files for the given language."""
    global _translators
    for t in _translators.values():
        app.removeTranslator(t)
    _translators.clear()

    if language is None:
        language = QLocale.system().name()[:2]  # e.g., 'ru'

    base_dir = Path(__file__).parent / "translations"

    # Qt base translations
    qt_translator = QTranslator()
    qt_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if qt_translator.load(QLocale(language), "qtbase", "_", qt_path):
        app.installTranslator(qt_translator)
        _translators['qt'] = qt_translator

    # Claster translations
    claster_translator = QTranslator()
    if claster_translator.load(QLocale(language), "claster", "_", str(base_dir)):
        app.installTranslator(claster_translator)
        _translators['claster'] = claster_translator


def get_supported_languages():
    """Return list of supported language codes."""
    return ['ru', 'en', 'es', 'pt', 'zh', 'de']