"""
Memory forensics utility functions.
"""

import ctypes
import sys
from claster.core.logger import get_logger

logger = get_logger(__name__)

def is_admin() -> bool:
    """Check if process has admin privileges."""
    if sys.platform == 'win32':
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    else:
        return os.geteuid() == 0

def require_admin() -> None:
    """Raise an error if not admin."""
    if not is_admin():
        raise PermissionError("Administrative privileges required for this memory operation.")