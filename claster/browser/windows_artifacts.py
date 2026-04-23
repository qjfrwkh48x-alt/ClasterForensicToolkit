"""
Windows-specific artifacts: Thumbs.db and Recent Files.
"""

import os
import sys
import struct
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from claster.core.logger import get_logger

logger = get_logger(__name__)


def parse_thumbs_db(folder_path: str) -> List[Dict[str, Any]]:
    """
    Parse Thumbs.db file (Windows thumbnail cache) using vinetto or custom parser.
    Returns list of cached filenames.
    """
    path = Path(folder_path) / 'Thumbs.db'
    if not path.exists():
        logger.error(f"Thumbs.db not found in {folder_path}")
        return []

    # Thumbs.db is OLE compound file; use olefile or vinetto.
    try:
        import olefile
        if not olefile.isOleFile(path):
            logger.error("Not a valid OLE file.")
            return []
        ole = olefile.OleFileIO(path)
        # Catalog stream contains filenames
        if ole.exists('Catalog'):
            data = ole.openstream('Catalog').read()
            # Simple extraction: find UTF-16LE strings
            import re
            names = re.findall(rb'(?:[A-Za-z]:\\[^\x00]+\.[a-z]{3,4})', data, re.I)
            ole.close()
            return [{'filename': n.decode('utf-16-le', errors='ignore')} for n in names]
    except ImportError:
        logger.warning("olefile not installed; cannot parse Thumbs.db.")
    except Exception as e:
        logger.error(f"Thumbs.db parse error: {e}")
    return []


def parse_recent_files(user_profile: str) -> List[Dict[str, Any]]:
    """
    Parse Windows Recent Files from %APPDATA%\Microsoft\Windows\Recent.
    Returns list of .lnk files with target paths.
    """
    if sys.platform != 'win32':
        logger.error("Recent Files parsing only supported on Windows.")
        return []

    recent_dir = Path(user_profile) / 'AppData/Roaming/Microsoft/Windows/Recent'
    if not recent_dir.exists():
        logger.error(f"Recent directory not found: {recent_dir}")
        return []

    files = []
    for lnk in recent_dir.glob('*.lnk'):
        try:
            # Use pylnk or our manual parser from metadata module
            from claster.metadata.lnk_fs import get_lnk_metadata
            meta = get_lnk_metadata(str(lnk))
            files.append({
                'lnk_file': lnk.name,
                'target': meta.get('target_path', ''),
                'modified': lnk.stat().st_mtime,
            })
        except Exception as e:
            logger.debug(f"Error parsing {lnk}: {e}")

    logger.info(f"Parsed {len(files)} recent files.")
    return files