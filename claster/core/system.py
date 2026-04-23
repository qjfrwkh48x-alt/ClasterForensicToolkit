"""
System information and utility functions.
"""

import os
import sys
import platform
import socket
import time
from datetime import datetime
from typing import Dict, Optional
from claster.core.logger import get_logger

logger = get_logger(__name__)


def get_system_info() -> Dict[str, str]:
    """
    Collect comprehensive system information.

    Returns:
        Dictionary with OS, version, hostname, CPU, RAM, etc.
    """
    info = {
        'os': platform.system(),
        'os_release': platform.release(),
        'os_version': platform.version(),
        'architecture': platform.machine(),
        'processor': platform.processor(),
        'hostname': socket.gethostname(),
        'python_version': sys.version,
    }

    # RAM (cross-platform approximation)
    try:
        import psutil
        mem = psutil.virtual_memory()
        info['total_ram_gb'] = f"{mem.total / (1024**3):.2f}"
        info['available_ram_gb'] = f"{mem.available / (1024**3):.2f}"
        cpu_count = psutil.cpu_count(logical=True)
        physical_cores = psutil.cpu_count(logical=False)
        info['cpu_logical_cores'] = str(cpu_count)
        info['cpu_physical_cores'] = str(physical_cores)
    except ImportError:
        logger.debug("psutil not installed, limited system info.")
        # Fallback
        info['total_ram_gb'] = 'N/A'
        info['available_ram_gb'] = 'N/A'
        info['cpu_logical_cores'] = str(os.cpu_count() or 'N/A')
        info['cpu_physical_cores'] = 'N/A'

    # Windows-specific details
    if sys.platform == 'win32':
        try:
            import winreg
            # Windows version from registry
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
            info['windows_product_name'] = winreg.QueryValueEx(key, "ProductName")[0]
            info['windows_current_build'] = winreg.QueryValueEx(key, "CurrentBuild")[0]
            info['windows_edition_id'] = winreg.QueryValueEx(key, "EditionID")[0]
            winreg.CloseKey(key)
        except Exception as e:
            logger.debug(f"Could not read Windows registry version: {e}")

    logger.debug(f"System info collected: {info['hostname']} running {info['os']}")
    return info


def get_timezone() -> str:
    """
    Get the system's current timezone.

    Returns:
        Timezone name (e.g., 'Europe/Moscow', 'America/New_York') or UTC offset.
    """
    try:
        # Python 3.9+ has zoneinfo
        from zoneinfo import ZoneInfo
        local_tz = datetime.now().astimezone().tzinfo
        if hasattr(local_tz, 'key'):
            return local_tz.key
        return str(local_tz)
    except ImportError:
        # Fallback to time.tzname
        return time.tzname[0] if time.tzname[0] else 'Unknown'

    # Alternative using datetime
    offset = time.timezone if not time.daylight else time.altzone
    hours = abs(offset) // 3600
    minutes = (abs(offset) % 3600) // 60
    sign = '-' if offset > 0 else '+'
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def is_admin() -> bool:
    """
    Check if the current process has administrative privileges.

    Returns:
        True if running as admin/root.
    """
    if sys.platform == 'win32':
        import ctypes
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        return os.geteuid() == 0


def request_elevation() -> bool:
    """
    Attempt to restart the script with elevated privileges.

    Returns:
        True if elevation requested (process will exit), False if already admin.
    """
    if is_admin():
        logger.debug("Already running with admin privileges.")
        return False

    if sys.platform == 'win32':
        import ctypes
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
            logger.info("Elevation requested (UAC). Exiting.")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Failed to request elevation: {e}")
            raise PrivilegeError("Failed to elevate privileges.")
    else:
        # Unix: use sudo
        try:
            os.execvp("sudo", ["sudo", sys.executable] + sys.argv)
        except Exception as e:
            logger.error(f"Failed to request elevation via sudo: {e}")
            raise PrivilegeError("Failed to elevate privileges. Run with sudo.")
    return True


# Import PrivilegeError from core.exceptions (add it if not already present)
from claster.core.exceptions import PrivilegeError