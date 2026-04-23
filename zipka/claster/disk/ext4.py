"""
Ext4 filesystem parsing using pytsk3.
"""

from typing import List, Dict
from datetime import datetime

from claster.core.logger import get_logger
from claster.core.exceptions import FileSystemError

logger = get_logger(__name__)

try:
    import pytsk3
    HAS_TSK = True
except ImportError:
    HAS_TSK = False
    logger.warning("pytsk3 not installed. Ext4 parsing disabled.")


def _tsk_time_to_datetime(tsk_time: int) -> datetime:
    if tsk_time == 0:
        return None
    return datetime.fromtimestamp(tsk_time)


def parse_ext4(volume_path: str) -> List[Dict]:
    """
    Parse Ext4 directory tree and return file metadata using TSK.
    Ext4 is fully supported by TSK.
    """
    if not HAS_TSK:
        raise NotImplementedError("pytsk3 required for Ext4 parsing.")

    try:
        img = pytsk3.Img_Info(volume_path)
        fs = pytsk3.FS_Info(img)
    except Exception as e:
        logger.error(f"Failed to open Ext4 filesystem: {e}")
        raise FileSystemError(f"Ext4 open error: {e}")

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
                'is_deleted': meta.flags & pytsk3.TSK_FS_META_FLAG_UNALLOC != 0,
                'uid': meta.uid,
                'gid': meta.gid,
                'mode': meta.mode,
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
        logger.error(f"Ext4 parsing failed: {e}")
        raise FileSystemError(f"Ext4 parsing error: {e}")

    logger.info(f"Parsed {len(entries)} entries from Ext4 volume.")
    return entries