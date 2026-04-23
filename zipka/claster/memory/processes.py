"""
Live process operations using psutil and platform-specific APIs.
"""

import os
import sys
import ctypes
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Any

from claster.core.logger import get_logger
from claster.core.exceptions import ClasterError, PrivilegeError
from claster.core.utils import ensure_dir

logger = get_logger(__name__)

class MemoryError(ClasterError):
    """Raised when a memory operation fails."""
    pass

# ----------------------------------------------------------------------
# Process listing
# ----------------------------------------------------------------------
def list_processes() -> List[Dict[str, Any]]:
    """
    Return a list of running processes with basic info (PID, name, user).

    Returns:
        List of dicts with keys: pid, name, username.
    """
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'username']):
        try:
            pinfo = proc.info
            processes.append({
                'pid': pinfo['pid'],
                'name': pinfo['name'],
                'username': pinfo['username'],
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    logger.info(f"Listed {len(processes)} processes.")
    return processes

def list_processes_full() -> List[Dict[str, Any]]:
    """
    Return full process information including CPU, memory, create time, exe path.

    Returns:
        List of detailed process dicts.
    """
    processes = []
    for proc in psutil.process_iter():
        try:
            with proc.oneshot():
                pinfo = proc.as_dict(attrs=[
                    'pid', 'name', 'username', 'exe', 'cmdline',
                    'create_time', 'cpu_percent', 'memory_info',
                    'num_threads', 'status'
                ])
                # Convert memory_info to dict
                if pinfo.get('memory_info'):
                    mem = pinfo['memory_info']
                    pinfo['memory_rss'] = mem.rss
                    pinfo['memory_vms'] = mem.vms
                    del pinfo['memory_info']
                processes.append(pinfo)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    logger.info(f"Listed {len(processes)} processes with full details.")
    return processes

def get_process_modules(pid: int) -> List[Dict[str, str]]:
    """
    Get loaded modules (DLLs) for a given process.

    Args:
        pid: Process ID.

    Returns:
        List of dicts with 'name' and 'path'.
    """
    try:
        proc = psutil.Process(pid)
        modules = []
        for mod in proc.memory_maps():
            if mod.path:
                modules.append({
                    'name': Path(mod.path).name,
                    'path': mod.path,
                })
        logger.debug(f"Process {pid} has {len(modules)} loaded modules.")
        return modules
    except psutil.NoSuchProcess:
        logger.error(f"Process {pid} not found.")
        return []
    except psutil.AccessDenied:
        logger.error(f"Access denied to process {pid}.")
        return []

def get_process_environment(pid: int) -> Dict[str, str]:
    """
    Retrieve environment variables for a process.

    Args:
        pid: Process ID.

    Returns:
        Dictionary of environment variables.
    """
    try:
        proc = psutil.Process(pid)
        env = proc.environ()
        return env
    except psutil.NoSuchProcess:
        logger.error(f"Process {pid} not found.")
        return {}
    except psutil.AccessDenied:
        logger.error(f"Access denied to environment of process {pid}.")
        return {}

def get_process_command_line(pid: int) -> Optional[List[str]]:
    """
    Get the command line used to start the process.

    Args:
        pid: Process ID.

    Returns:
        List of arguments, or None if unavailable.
    """
    try:
        proc = psutil.Process(pid)
        return proc.cmdline()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None

def get_process_memory_map(pid: int) -> List[Dict[str, Any]]:
    """
    Get memory map (regions) of a process.

    Returns:
        List of memory region dicts with address, size, permissions, path.
    """
    try:
        proc = psutil.Process(pid)
        maps = []
        for mmap in proc.memory_maps():
            maps.append({
                'path': mmap.path,
                'rss': mmap.rss,
                'size': mmap.size,
                'perms': mmap.perms,
            })
        return maps
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return []

# ----------------------------------------------------------------------
# Process dumping
# ----------------------------------------------------------------------
def dump_process(pid: int, output_path: str) -> bool:
    """
    Create a memory dump of a single process.

    On Windows, uses MiniDumpWriteDump via ctypes.
    On Linux, reads /proc/[pid]/mem.

    Args:
        pid: Process ID.
        output_path: Path to save the dump file.

    Returns:
        True if successful.
    """
    ensure_dir(Path(output_path).parent)

    if sys.platform == 'win32':
        return _dump_process_windows(pid, output_path)
    else:
        return _dump_process_linux(pid, output_path)

def _dump_process_windows(pid: int, output_path: str) -> bool:
    """Windows process dumping using MiniDumpWriteDump."""
    import ctypes
    from ctypes import wintypes

    # Constants
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010
    PROCESS_DUP_HANDLE = 0x0040
    MiniDumpWithFullMemory = 0x00000002

    kernel32 = ctypes.windll.kernel32
    dbghelp = ctypes.windll.dbghelp

    class MINIDUMP_EXCEPTION_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("ThreadId", wintypes.DWORD),
            ("ExceptionPointers", ctypes.c_void_p),
            ("ClientPointers", wintypes.BOOL),
        ]

    # Open process
    hProcess = kernel32.OpenProcess(
        PROCESS_QUERY_INFORMATION | PROCESS_VM_READ | PROCESS_DUP_HANDLE,
        False, pid
    )
    if not hProcess:
        logger.error(f"Failed to open process {pid}. Error: {kernel32.GetLastError()}")
        return False

    # Create output file
    hFile = kernel32.CreateFileW(
        output_path,
        0x40000000,  # GENERIC_WRITE
        0, None, 2,  # CREATE_ALWAYS
        0x80,  # FILE_ATTRIBUTE_NORMAL
        None
    )
    if hFile == -1:
        kernel32.CloseHandle(hProcess)
        logger.error(f"Failed to create dump file {output_path}")
        return False

    # Write minidump
    success = dbghelp.MiniDumpWriteDump(
        hProcess, pid, hFile,
        MiniDumpWithFullMemory,
        None, None, None
    )

    kernel32.CloseHandle(hFile)
    kernel32.CloseHandle(hProcess)

    if success:
        logger.info(f"Process {pid} dumped to {output_path}")
    else:
        logger.error(f"MiniDumpWriteDump failed for PID {pid}")
    return bool(success)

def _dump_process_linux(pid: int, output_path: str) -> bool:
    """Linux process dumping by reading /proc/[pid]/mem."""
    mem_path = f"/proc/{pid}/mem"
    try:
        with open(mem_path, 'rb') as mem_file, open(output_path, 'wb') as out_file:
            # Read memory mappings from /proc/[pid]/maps to dump only readable regions
            maps_path = f"/proc/{pid}/maps"
            with open(maps_path, 'r') as maps_file:
                for line in maps_file:
                    parts = line.split()
                    if len(parts) < 2:
                        continue
                    addr_range = parts[0]
                    perms = parts[1]
                    if 'r' not in perms:
                        continue
                    start, end = addr_range.split('-')
                    start = int(start, 16)
                    end = int(end, 16)
                    try:
                        mem_file.seek(start)
                        chunk = mem_file.read(end - start)
                        out_file.write(chunk)
                    except OSError:
                        # Some regions may not be readable despite 'r' permission
                        continue
        logger.info(f"Process {pid} memory dumped to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Linux process dump failed for PID {pid}: {e}")
        return False

def dump_all_processes(output_dir: str) -> Dict[int, bool]:
    """
    Dump memory of all running processes to individual files.

    Args:
        output_dir: Directory to store dumps.

    Returns:
        Dictionary mapping PID to success status.
    """
    ensure_dir(output_dir)
    results = {}
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            pid = proc.info['pid']
            name = proc.info['name']
            out_file = Path(output_dir) / f"{pid}_{name}.dmp"
            success = dump_process(pid, str(out_file))
            results[pid] = success
        except Exception as e:
            logger.error(f"Error dumping PID {pid}: {e}")
            results[pid] = False
    return results