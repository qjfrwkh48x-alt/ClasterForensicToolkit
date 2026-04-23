"""
Chromium-based browser artifacts (Chrome, Edge, Brave, Opera).
Includes history, passwords (decryption), and downloads.
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
from claster.core.exceptions import ClasterError

logger = get_logger(__name__)

# Chrome/Chromium profile paths
CHROME_PATHS = {
    'win32': [
        Path(os.environ.get('LOCALAPPDATA', '')) / 'Google/Chrome/User Data',
        Path(os.environ.get('LOCALAPPDATA', '')) / 'Microsoft/Edge/User Data',
    ],
    'darwin': [
        Path.home() / 'Library/Application Support/Google/Chrome',
        Path.home() / 'Library/Application Support/Microsoft Edge',
    ],
    'linux': [
        Path.home() / '.config/google-chrome',
        Path.home() / '.config/microsoft-edge',
    ]
}


def _find_profiles(base_path: Path) -> List[Path]:
    """Find all profile directories (Default, Profile 1, etc.)."""
    profiles = []
    if not base_path.exists():
        return profiles
    for item in base_path.iterdir():
        if item.is_dir() and (item.name == 'Default' or item.name.startswith('Profile')):
            if (item / 'History').exists():
                profiles.append(item)
    return profiles


def _chrome_timestamp_to_datetime(chrome_time: int) -> Optional[datetime]:
    """Convert Chrome timestamp (microseconds since 1601-01-01) to datetime."""
    if chrome_time == 0:
        return None
    try:
        return datetime(1601, 1, 1) + timedelta(microseconds=chrome_time)
    except OverflowError:
        return None


def get_chrome_history(profile_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extract browsing history from Chrome/Chromium.

    Args:
        profile_path: Path to profile directory (e.g., '.../Default'). If None, auto-detect.

    Returns:
        List of history entries with url, title, visit_count, last_visit_time.
    """
    if profile_path is None:
        # Auto-detect first available
        for base in CHROME_PATHS.get(sys.platform, []):
            profiles = _find_profiles(base)
            if profiles:
                profile_path = str(profiles[0])
                break
    if not profile_path:
        logger.error("No Chrome profile found.")
        return []

    history_db = Path(profile_path) / 'History'
    if not history_db.exists():
        logger.error(f"History file not found: {history_db}")
        return []

    # Copy DB to avoid lock issues
    import tempfile
    import shutil
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        shutil.copy2(history_db, tmp.name)
        tmp_path = tmp.name

    conn = sqlite3.connect(tmp_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    entries = []
    try:
        cursor.execute('''
            SELECT url, title, visit_count, last_visit_time
            FROM urls
            ORDER BY last_visit_time DESC
        ''')
        for row in cursor.fetchall():
            entries.append({
                'url': row['url'],
                'title': row['title'],
                'visit_count': row['visit_count'],
                'last_visit': _chrome_timestamp_to_datetime(row['last_visit_time']),
            })
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
    finally:
        conn.close()
        os.unlink(tmp_path)

    logger.info(f"Extracted {len(entries)} history entries.")
    return entries


def _decrypt_chrome_password(encrypted_value: bytes) -> Optional[str]:
    """Decrypt Chrome password using DPAPI (Windows) or Keychain (macOS)."""
    if sys.platform == 'win32':
        try:
            import win32crypt
            return win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1].decode('utf-8')
        except Exception as e:
            logger.debug(f"DPAPI decrypt failed: {e}")
            return None
    elif sys.platform == 'darwin':
        # macOS: keychain access required
        logger.warning("macOS password decryption not implemented.")
        return None
    else:
        # Linux: use secret storage
        logger.warning("Linux password decryption requires gnome-keyring.")
        return None


def get_chrome_passwords(profile_path: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Extract saved passwords from Chrome/Chromium.

    Returns:
        List of dicts with 'origin_url', 'username', 'password'.
    """
    if profile_path is None:
        for base in CHROME_PATHS.get(sys.platform, []):
            profiles = _find_profiles(base)
            if profiles:
                profile_path = str(profiles[0])
                break
    if not profile_path:
        logger.error("No profile found.")
        return []

    login_db = Path(profile_path) / 'Login Data'
    if not login_db.exists():
        logger.error(f"Login Data not found: {login_db}")
        return []

    import tempfile
    import shutil
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        shutil.copy2(login_db, tmp.name)
        tmp_path = tmp.name

    conn = sqlite3.connect(tmp_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    passwords = []
    try:
        cursor.execute('SELECT origin_url, username_value, password_value FROM logins')
        for row in cursor.fetchall():
            decrypted = _decrypt_chrome_password(row['password_value'])
            if decrypted:
                passwords.append({
                    'url': row['origin_url'],
                    'username': row['username_value'],
                    'password': decrypted,
                })
    except Exception as e:
        logger.error(f"Failed to read passwords: {e}")
    finally:
        conn.close()
        os.unlink(tmp_path)

    logger.info(f"Extracted {len(passwords)} passwords.")
    return passwords


def get_chrome_downloads(profile_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Extract download history from Chrome."""
    if profile_path is None:
        for base in CHROME_PATHS.get(sys.platform, []):
            profiles = _find_profiles(base)
            if profiles:
                profile_path = str(profiles[0])
                break
    if not profile_path:
        return []

    history_db = Path(profile_path) / 'History'
    if not history_db.exists():
        return []

    import tempfile
    import shutil
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        shutil.copy2(history_db, tmp.name)
        tmp_path = tmp.name

    conn = sqlite3.connect(tmp_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    downloads = []
    try:
        cursor.execute('''
            SELECT target_path, tab_url, total_bytes, start_time, end_time, state
            FROM downloads
            ORDER BY start_time DESC
        ''')
        for row in cursor.fetchall():
            downloads.append({
                'target_path': row['target_path'],
                'source_url': row['tab_url'],
                'total_bytes': row['total_bytes'],
                'start_time': _chrome_timestamp_to_datetime(row['start_time']),
                'end_time': _chrome_timestamp_to_datetime(row['end_time']),
                'state': 'complete' if row['state'] == 1 else 'incomplete',
            })
    except Exception as e:
        logger.error(f"Failed to read downloads: {e}")
    finally:
        conn.close()
        os.unlink(tmp_path)

    logger.info(f"Extracted {len(downloads)} download entries.")
    return downloads


def get_edge_history(profile_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Alias for get_chrome_history, since Edge is Chromium-based."""
    return get_chrome_history(profile_path)