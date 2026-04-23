"""
Firefox browser artifacts (history and passwords).
Uses sqlite3 for places.sqlite and logins.json.
"""

import os
import sys
import sqlite3
import json
import base64
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

from claster.core.logger import get_logger

logger = get_logger(__name__)

FIREFOX_PATHS = {
    'win32': Path(os.environ.get('APPDATA', '')) / 'Mozilla/Firefox/Profiles',
    'darwin': Path.home() / 'Library/Application Support/Firefox/Profiles',
    'linux': Path.home() / '.mozilla/firefox',
}


def _find_firefox_profile() -> Optional[Path]:
    """Find a Firefox profile directory."""
    base = FIREFOX_PATHS.get(sys.platform)
    if not base or not base.exists():
        return None
    for item in base.iterdir():
        if item.is_dir() and (item / 'places.sqlite').exists():
            return item
    return None


def _firefox_timestamp_to_datetime(timestamp: int) -> Optional[datetime]:
    """Convert Firefox timestamp (microseconds since epoch) to datetime."""
    if timestamp == 0:
        return None
    try:
        return datetime.fromtimestamp(timestamp / 1_000_000)
    except (OSError, OverflowError):
        return None


def get_firefox_history(profile_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extract browsing history from Firefox.

    Args:
        profile_path: Path to Firefox profile. Auto-detects if None.

    Returns:
        List of history entries.
    """
    if profile_path is None:
        profile = _find_firefox_profile()
        if not profile:
            logger.error("Firefox profile not found.")
            return []
        profile_path = str(profile)
    else:
        profile_path = Path(profile_path)

    places_db = Path(profile_path) / 'places.sqlite'
    if not places_db.exists():
        logger.error(f"places.sqlite not found: {places_db}")
        return []

    import tempfile
    import shutil
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        shutil.copy2(places_db, tmp.name)
        tmp_path = tmp.name

    conn = sqlite3.connect(tmp_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    entries = []
    try:
        cursor.execute('''
            SELECT url, title, visit_count, last_visit_date
            FROM moz_places
            WHERE last_visit_date IS NOT NULL
            ORDER BY last_visit_date DESC
        ''')
        for row in cursor.fetchall():
            entries.append({
                'url': row['url'],
                'title': row['title'],
                'visit_count': row['visit_count'],
                'last_visit': _firefox_timestamp_to_datetime(row['last_visit_date']),
            })
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
    finally:
        conn.close()
        os.unlink(tmp_path)

    logger.info(f"Extracted {len(entries)} Firefox history entries.")
    return entries


def get_firefox_passwords(profile_path: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Extract saved passwords from Firefox (logins.json).
    Note: Passwords are encrypted with master password; we only return encrypted data.
    """
    if profile_path is None:
        profile = _find_firefox_profile()
        if not profile:
            return []
        profile_path = str(profile)
    else:
        profile_path = Path(profile_path)

    logins_file = Path(profile_path) / 'logins.json'
    if not logins_file.exists():
        logger.error(f"logins.json not found: {logins_file}")
        return []

    passwords = []
    try:
        with open(logins_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for entry in data.get('logins', []):
                passwords.append({
                    'hostname': entry.get('hostname'),
                    'username': entry.get('encryptedUsername'),
                    'password': entry.get('encryptedPassword'),  # encrypted
                })
    except Exception as e:
        logger.error(f"Failed to read logins.json: {e}")

    logger.info(f"Extracted {len(passwords)} Firefox password entries (encrypted).")
    return passwords