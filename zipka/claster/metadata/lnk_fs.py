"""
Windows shortcut (.lnk) and filesystem metadata extraction.
"""

import os
import sys
import struct
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from claster.core.logger import get_logger

logger = get_logger(__name__)


def get_lnk_metadata(lnk_path: str) -> Dict[str, Any]:
    """
    Parse a Windows shortcut (.lnk) file and extract its metadata.

    Returns:
        Dictionary with target path, working directory, arguments, timestamps, etc.
    """
    path = Path(lnk_path)
    if not path.exists():
        raise FileNotFoundError(f"LNK file not found: {path}")

    metadata = {}
    try:
        with open(path, 'rb') as f:
            data = f.read()

        # Check LNK signature
        if data[:4] != b'\x4C\x00\x00\x00':
            logger.error("Not a valid LNK file.")
            return {}

        # Flags at offset 0x14
        flags = struct.unpack('<I', data[0x14:0x18])[0]
        has_target_id_list = flags & 0x01
        has_link_info = flags & 0x02
        has_name = flags & 0x04
        has_relative_path = flags & 0x08
        has_working_dir = flags & 0x10
        has_arguments = flags & 0x20
        has_icon_location = flags & 0x40

        # File attributes at offset 0x18
        attr = struct.unpack('<I', data[0x18:0x1C])[0]
        metadata['is_directory'] = bool(attr & 0x10)
        metadata['is_readonly'] = bool(attr & 0x01)

        # Timestamps
        creation_time = struct.unpack('<Q', data[0x1C:0x24])[0]
        access_time = struct.unpack('<Q', data[0x24:0x2C])[0]
        write_time = struct.unpack('<Q', data[0x2C:0x34])[0]

        def filetime_to_datetime(ft):
            if ft == 0:
                return None
            # Windows FILETIME (100ns since 1601-01-01)
            return datetime(1601, 1, 1) + timedelta(microseconds=ft // 10)

        metadata['creation_time'] = filetime_to_datetime(creation_time)
        metadata['access_time'] = filetime_to_datetime(access_time)
        metadata['write_time'] = filetime_to_datetime(write_time)

        # Target size at 0x34
        metadata['target_size'] = struct.unpack('<I', data[0x34:0x38])[0]

        # Parse LinkInfo if present (simplified)
        offset = 0x4C
        # Skip LinkInfo parsing for brevity; full implementation would read structures.

        # Read string data sections (simplified)
        # We can use pylnk library for full parsing.
        logger.debug("Full LNK parsing requires pylnk; using limited manual extraction.")

    except Exception as e:
        logger.error(f"Failed to parse LNK: {e}")

    return metadata


def get_fs_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extract filesystem metadata (size, timestamps, permissions) for any file.

    Returns:
        Dictionary with 'size', 'created', 'modified', 'accessed', 'mode', etc.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    stat = path.stat()
    metadata = {
        'size': stat.st_size,
        'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
        'accessed': datetime.fromtimestamp(stat.st_atime).isoformat(),
    }

    if sys.platform == 'win32':
        # Windows-specific: get attributes
        import ctypes
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
        if attrs != 0xFFFFFFFF:
            metadata['readonly'] = bool(attrs & 0x01)
            metadata['hidden'] = bool(attrs & 0x02)
            metadata['system'] = bool(attrs & 0x04)
            metadata['directory'] = bool(attrs & 0x10)
            metadata['archive'] = bool(attrs & 0x20)
    else:
        # Unix permissions
        metadata['mode'] = oct(stat.st_mode)[-3:]
        metadata['uid'] = stat.st_uid
        metadata['gid'] = stat.st_gid

    return metadata