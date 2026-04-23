"""
File system operations: safe copy, secure deletion, disk wiping, volume info, etc.
"""

import os
import sys
import shutil
import stat
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple, Union, Dict
from claster.core.logger import get_logger
from claster.core.exceptions import FileSystemError, PrivilegeError
from claster.core.hashing import compute_hash, verify_hash
from claster.core.utils import ensure_dir
from claster.core.system import is_admin

logger = get_logger(__name__)


def safe_copy(
    src: Union[str, Path],
    dst: Union[str, Path],
    verify: bool = True,
    hash_algorithm: str = 'sha256',
    overwrite: bool = False
) -> Path:
    """
    Copy a file safely with optional hash verification.

    Args:
        src: Source file path.
        dst: Destination file path.
        verify: If True, compute and compare hashes after copy.
        hash_algorithm: Algorithm for verification.
        overwrite: If True, overwrite existing destination.

    Returns:
        Path to the destination file.

    Raises:
        FileSystemError: If copy fails or verification fails.
    """
    src = Path(src)
    dst = Path(dst)

    if not src.exists():
        raise FileSystemError(f"Source file not found: {src}")
    if not src.is_file():
        raise FileSystemError(f"Source is not a regular file: {src}")

    # Pre-compute source hash if verification requested
    src_hash = None
    if verify:
        src_hash = compute_hash(src, hash_algorithm)
        logger.debug(f"Source hash ({hash_algorithm}): {src_hash}")

    # Ensure destination directory exists
    dst.parent.mkdir(parents=True, exist_ok=True)

    if dst.exists() and not overwrite:
        raise FileSystemError(f"Destination already exists and overwrite=False: {dst}")

    try:
        shutil.copy2(src, dst)  # copy2 preserves metadata
    except Exception as e:
        logger.error(f"Failed to copy {src} to {dst}: {e}")
        raise FileSystemError(f"Copy failed: {e}")

    if verify:
        dst_hash = compute_hash(dst, hash_algorithm)
        if dst_hash != src_hash:
            # Remove corrupted copy
            dst.unlink()
            raise FileSystemError(f"Hash verification failed after copy. Expected {src_hash}, got {dst_hash}")
        logger.info(f"File copied and verified: {src} -> {dst}")

    return dst


def secure_delete(file_path: Union[str, Path], passes: int = 3) -> None:
    """
    Securely delete a file by overwriting with random data, then zeros, then remove.

    Args:
        file_path: Path to the file.
        passes: Number of overwrite passes (default 3: random, zeros, random).

    Raises:
        FileSystemError: If deletion fails.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        logger.warning(f"File does not exist, nothing to delete: {file_path}")
        return

    if not file_path.is_file():
        raise FileSystemError(f"Cannot securely delete non-file: {file_path}")

    file_size = file_path.stat().st_size
    logger.debug(f"Securely deleting {file_path} ({file_size} bytes) with {passes} passes")

    try:
        with open(file_path, 'r+b') as f:
            for p in range(passes):
                f.seek(0)
                if p % 2 == 0:
                    # Write random data
                    import os as os_module
                    data = os_module.urandom(file_size)
                else:
                    # Write zeros
                    data = b'\x00' * file_size
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        # Finally remove
        file_path.unlink()
        logger.info(f"Securely deleted: {file_path}")
    except Exception as e:
        logger.error(f"Secure deletion failed for {file_path}: {e}")
        raise FileSystemError(f"Secure deletion failed: {e}")


def wipe_free_space(drive_letter: str, passes: int = 1) -> None:
    """
    Wipe free space on a drive (Windows only with cipher.exe or sdelete).

    Args:
        drive_letter: Drive letter, e.g., 'C:'.
        passes: Number of passes (cipher only does 1 pass by default).

    Raises:
        FileSystemError: If wiping fails or not on Windows.
    """
    if sys.platform != 'win32':
        raise NotImplementedError("wipe_free_space is currently Windows-only.")

    if not is_admin():
        raise PrivilegeError("Administrative privileges required to wipe free space.")

    # Use cipher.exe (built-in) for a single pass
    cmd = ['cipher', '/w:' + drive_letter]
    logger.info(f"Wiping free space on {drive_letter} using cipher.exe")
    try:
        # cipher /w writes to a temp folder and deletes it
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise FileSystemError(f"cipher failed: {result.stderr}")
        logger.info(f"Free space wipe completed on {drive_letter}")
    except Exception as e:
        logger.error(f"Wipe free space failed: {e}")
        raise FileSystemError(f"Wipe free space failed: {e}")

    # Alternative: use Sysinternals SDelete for multiple passes, but requires download.
    if passes > 1:
        logger.warning("Multiple passes not supported with cipher.exe. Install SDelete for that.")


def get_disk_geometry(drive: str) -> Dict:
    geometry = {}
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes

        # Windows API DeviceIoControl to get drive geometry
        IOCTL_DISK_GET_DRIVE_GEOMETRY = 0x00070000
        GENERIC_READ = 0x80000000
        FILE_SHARE_READ = 0x00000001
        FILE_SHARE_WRITE = 0x00000002
        OPEN_EXISTING = 3

        class DISK_GEOMETRY(ctypes.Structure):
            _fields_ = [
                ("Cylinders", ctypes.c_longlong),
                ("MediaType", ctypes.c_int),
                ("TracksPerCylinder", ctypes.c_ulong),
                ("SectorsPerTrack", ctypes.c_ulong),
                ("BytesPerSector", ctypes.c_ulong),
            ]

        handle = ctypes.windll.kernel32.CreateFileW(
            drive, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE,
            None, OPEN_EXISTING, 0, None
        )
        if handle == -1:
            logger.error(f"Could not open drive: {drive}")
            return geometry

        geom = DISK_GEOMETRY()
        bytes_returned = wintypes.DWORD()
        success = ctypes.windll.kernel32.DeviceIoControl(
            handle, IOCTL_DISK_GET_DRIVE_GEOMETRY,
            None, 0, ctypes.byref(geom), ctypes.sizeof(geom),
            ctypes.byref(bytes_returned), None
        )
        ctypes.windll.kernel32.CloseHandle(handle)

        if success:
            geometry = {
                'cylinders': geom.Cylinders,
                'tracks_per_cylinder': geom.TracksPerCylinder,
                'sectors_per_track': geom.SectorsPerTrack,
                'bytes_per_sector': geom.BytesPerSector,
                'total_sectors': geom.Cylinders * geom.TracksPerCylinder * geom.SectorsPerTrack,
                'total_size_bytes': geom.Cylinders * geom.TracksPerCylinder * geom.SectorsPerTrack * geom.BytesPerSector
            }
            logger.debug(f"Drive geometry for {drive}: {geometry}")
        else:
            logger.error(f"DeviceIoControl failed for {drive}")
    else:
        # Linux: use /sys/block/sda/queue/...
        if drive.startswith('/dev/'):
            dev_name = Path(drive).name
            sys_path = Path(f"/sys/block/{dev_name}")
            if sys_path.exists():
                # Get sector size and total sectors
                sector_size_file = sys_path / "queue/hw_sector_size"
                size_file = sys_path / "size"
                if sector_size_file.exists() and size_file.exists():
                    sector_size = int(sector_size_file.read_text().strip())
                    total_sectors = int(size_file.read_text().strip())
                    geometry = {
                        'bytes_per_sector': sector_size,
                        'total_sectors': total_sectors,
                        'total_size_bytes': sector_size * total_sectors
                    }
    return geometry


def get_volume_info(volume_path: str) -> Dict:
    """
    Get volume information: serial number, label, filesystem type.

    Args:
        volume_path: Volume mount point, e.g., 'C:\\' or '/'.

    Returns:
        Dictionary with volume info.
    """
    info = {}
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes

        volume_name_buffer = ctypes.create_unicode_buffer(261)
        volume_serial = wintypes.DWORD()
        max_component_len = wintypes.DWORD()
        fs_flags = wintypes.DWORD()
        fs_name_buffer = ctypes.create_unicode_buffer(261)

        success = ctypes.windll.kernel32.GetVolumeInformationW(
            volume_path,
            volume_name_buffer, ctypes.sizeof(volume_name_buffer),
            ctypes.byref(volume_serial),
            ctypes.byref(max_component_len),
            ctypes.byref(fs_flags),
            fs_name_buffer, ctypes.sizeof(fs_name_buffer)
        )
        if success:
            info['label'] = volume_name_buffer.value
            info['serial_number'] = f"{volume_serial.value:08X}"
            info['filesystem'] = fs_name_buffer.value
            info['max_component_length'] = max_component_len.value
    else:
        # Linux: use os.statvfs and /proc/mounts
        try:
            statvfs = os.statvfs(volume_path)
            info['filesystem'] = 'Unknown'  # Could parse /proc/mounts
            info['block_size'] = statvfs.f_bsize
            info['total_blocks'] = statvfs.f_blocks
            info['free_blocks'] = statvfs.f_bfree
            info['available_blocks'] = statvfs.f_bavail
        except Exception:
            pass
    logger.debug(f"Volume info for {volume_path}: {info}")
    return info


def compare_files(file1: Union[str, Path], file2: Union[str, Path], method: str = 'hash') -> bool:
    """
    Compare two files for equality.

    Args:
        file1: First file path.
        file2: Second file path.
        method: 'hash' (fast for large files) or 'byte' (exact comparison).

    Returns:
        True if files are identical.
    """
    file1 = Path(file1)
    file2 = Path(file2)

    if not file1.exists() or not file2.exists():
        raise FileSystemError("One or both files do not exist.")

    if file1.stat().st_size != file2.stat().st_size:
        return False

    if method == 'hash':
        hash1 = compute_hash(file1)
        hash2 = compute_hash(file2)
        return hash1 == hash2
    elif method == 'byte':
        with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
            while True:
                b1 = f1.read(8192)
                b2 = f2.read(8192)
                if b1 != b2:
                    return False
                if not b1:
                    return True
    else:
        raise ValueError(f"Unknown comparison method: {method}")