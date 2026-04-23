"""
FAT32 and exFAT filesystem parsing using pytsk3.
"""

from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from claster.core.logger import get_logger
from claster.core.exceptions import FileSystemError

logger = get_logger(__name__)

try:
    import pytsk3
    HAS_TSK = True
except ImportError:
    HAS_TSK = False
    logger.warning("pytsk3 not installed. FAT/exFAT parsing disabled.")


def _get_fs_handle(volume_path: str):
    """Open a file system object using TSK."""
    if not HAS_TSK:
        return None
    try:
        img = pytsk3.Img_Info(volume_path)
        fs = pytsk3.FS_Info(img)
        return fs
    except Exception as e:
        logger.error(f"Failed to open filesystem with TSK: {e}")
        return None


def _tsk_time_to_datetime(tsk_time: int) -> Optional[datetime]:
    """Convert TSK timestamp (Unix epoch seconds) to datetime."""
    if tsk_time == 0:
        return None
    return datetime.fromtimestamp(tsk_time)


def parse_fat(volume_path: str) -> List[Dict]:
    """
    Parse FAT32 directory tree and return file metadata.
    Uses TSK to traverse the filesystem.
    """
    if not HAS_TSK:
        raise NotImplementedError("pytsk3 required for FAT parsing.")

    fs = _get_fs_handle(volume_path)
    if not fs:
        return []

    entries = []

    def walk_dir(directory, path="/"):
        for entry in directory:
            name = entry.info.name.name.decode('utf-8', errors='replace')
            if name in ['.', '..']:
                continue
            meta = entry.info.meta
            if meta is None:
                continue
            file_info = {
                'name': name,
                'full_path': path + name,
                'size': meta.size,
                'created': _tsk_time_to_datetime(meta.crtime),
                'modified': _tsk_time_to_datetime(meta.mtime),
                'accessed': _tsk_time_to_datetime(meta.atime),
                'inode': meta.addr,
                'is_directory': meta.type == pytsk3.TSK_FS_META_TYPE_DIR,
                'is_deleted': meta.flags & pytsk3.TSK_FS_META_FLAG_UNALLOC != 0
            }
            entries.append(file_info)
            if file_info['is_directory']:
                try:
                    sub_dir = entry.open_dir()
                    walk_dir(sub_dir, path + name + "/")
                except:
                    pass

    try:
        root_dir = fs.open_dir("/")
        walk_dir(root_dir)
    except Exception as e:
        logger.error(f"FAT parsing failed: {e}")
        raise FileSystemError(f"FAT parsing error: {e}")

    logger.info(f"Parsed {len(entries)} entries from FAT volume.")
    return entries


def parse_exfat(volume_path: str) -> List[Dict]:
    """
    Parse exFAT directory tree using TSK (exFAT is supported in modern TSK).
    """
    # TSK supports exFAT similarly; we can reuse the same traversal.
    return parse_fat(volume_path)


def recover_deleted_fat(volume_path: str, filename: str, output: str) -> bool:
    """
    Attempt to recover a deleted file from FAT by its name.
    Searches for unallocated directory entries and recovers associated clusters.
    """
    if not HAS_TSK:
        logger.error("pytsk3 required for recovery.")
        return False

    fs = _get_fs_handle(volume_path)
    if not fs:
        return False

    def search_deleted(directory, path=""):
        for entry in directory:
            name = entry.info.name.name.decode('utf-8', errors='replace')
            meta = entry.info.meta
            if meta and (meta.flags & pytsk3.TSK_FS_META_FLAG_UNALLOC):
                if name == filename:
                    # Found deleted file, attempt recovery
                    try:
                        f = entry.open_meta()
                        data = f.read_random(0, meta.size)
                        with open(output, 'wb') as out:
                            out.write(data)
                        logger.info(f"Recovered deleted file '{filename}' to {output}")
                        return True
                    except Exception as e:
                        logger.error(f"Recovery failed: {e}")
                        return False
            if meta and meta.type == pytsk3.TSK_FS_META_TYPE_DIR:
                try:
                    sub_dir = entry.open_dir()
                    if search_deleted(sub_dir, path + name + "/"):
                        return True
                except:
                    pass
        return False

    root_dir = fs.open_dir("/")
    found = search_deleted(root_dir)
    if not found:
        logger.warning(f"Deleted file '{filename}' not found.")
    return found