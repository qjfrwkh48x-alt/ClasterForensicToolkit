"""
Miscellaneous utility functions used throughout the toolkit.
"""

import os
import sys
import ctypes
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, Union
from claster.core.logger import get_logger
from claster.core.exceptions import PrivilegeError, FileSystemError

logger = get_logger(__name__)

def ensure_dir(path: Union[str, Path]) -> Path:
    """
    Create directory recursively if it doesn't exist.

    Args:
        path: Directory path.

    Returns:
        Path object of the directory.
    """
    path = Path(path)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created directory: {path}")
    return path

def timestamp(format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Return current timestamp as formatted string.

    Args:
        format_str: strftime format string.

    Returns:
        Formatted timestamp.
    """
    return datetime.now().strftime(format_str)

def is_admin() -> bool:
    """
    Check if the current process has administrative privileges.

    Returns:
        True if running as admin/root, False otherwise.
    """
    if sys.platform == "win32":
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        # Unix-like
        return os.geteuid() == 0

def request_elevation() -> bool:
    """
    Attempt to restart the script with elevated privileges (Windows UAC / Unix sudo).

    Returns:
        True if elevation was requested (process will exit), False if already admin.
    """
    if is_admin():
        logger.debug("Already running with administrative privileges.")
        return False

    if sys.platform == "win32":
        # Windows: use ShellExecute with 'runas'
        import ctypes.wintypes
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
            logger.info("Elevation requested (UAC). Exiting current process.")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Failed to request elevation: {e}")
            raise PrivilegeError("Failed to elevate privileges.")
    else:
        # Unix: try sudo
        try:
            os.execvp("sudo", ["sudo", sys.executable] + sys.argv)
        except Exception as e:
            logger.error(f"Failed to request elevation via sudo: {e}")
            raise PrivilegeError("Failed to elevate privileges. Please run with sudo.")
    return True

def get_temp_path(prefix: str = "claster_") -> Path:
    """Create and return a temporary directory path."""
    temp_dir = Path(tempfile.gettempdir()) / f"{prefix}{os.getpid()}"
    ensure_dir(temp_dir)
    return temp_dir

def safe_filename(filename: str) -> str:
    """Remove potentially dangerous characters from a filename."""
    import re
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def human_size(size_bytes: int) -> str:
    """Convert bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"