"""
Help browser widget using QTextBrowser with embedded HTML documentation.
"""

from PyQt6.QtWidgets import QTextBrowser
from PyQt6.QtCore import QUrl


class HelpBrowser(QTextBrowser):
    def __init__(self):
        super().__init__()
        self.setOpenExternalLinks(True)
        self.setSource(QUrl("qrc:/docs/index.html"))