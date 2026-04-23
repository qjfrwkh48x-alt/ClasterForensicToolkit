"""
Claster Forensic Toolkit - Browser and Application Artifacts Module

Extracts history, passwords, downloads from Chrome, Firefox, Edge,
and data from Skype, Telegram, Discord, WhatsApp. Also parses Thumbs.db and Recent Files.
"""

from claster.browser.chromium import (
    get_chrome_history,
    get_chrome_passwords,
    get_chrome_downloads,
    get_edge_history,
)
from claster.browser.firefox import (
    get_firefox_history,
    get_firefox_passwords,
)
from claster.browser.messengers import (
    get_skype_history,
    get_telegram_history,
    get_discord_history,
    get_whatsapp_history,
)
from claster.browser.windows_artifacts import (
    parse_thumbs_db,
    parse_recent_files,
)

__all__ = [
    'get_chrome_history',
    'get_chrome_passwords',
    'get_chrome_downloads',
    'get_edge_history',
    'get_firefox_history',
    'get_firefox_passwords',
    'get_skype_history',
    'get_telegram_history',
    'get_discord_history',
    'get_whatsapp_history',
    'parse_thumbs_db',
    'parse_recent_files',
]