"""
Metadata extraction from archive files (ZIP, RAR, 7z).
"""

import zipfile
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from claster.core.logger import get_logger

logger = get_logger(__name__)


def get_archive_metadata(archive_path: str) -> Dict[str, Any]:
    """
    Extract metadata from an archive (ZIP, RAR, 7z).
    Returns basic info and list of contained files with metadata.

    Args:
        archive_path: Path to archive file.

    Returns:
        Dictionary with 'format', 'file_count', 'total_size', 'files' (list of file entries).
    """
    path = Path(archive_path)
    if not path.exists():
        raise FileNotFoundError(f"Archive not found: {path}")

    ext = path.suffix.lower()
    metadata = {'format': ext, 'file_count': 0, 'total_size': 0, 'files': []}

    if ext == '.zip':
        try:
            with zipfile.ZipFile(path, 'r') as zf:
                for info in zf.infolist():
                    if not info.is_dir():
                        metadata['file_count'] += 1
                        metadata['total_size'] += info.file_size
                        metadata['files'].append({
                            'filename': info.filename,
                            'size': info.file_size,
                            'compress_size': info.compress_size,
                            'modified': datetime(*info.date_time).isoformat() if info.date_time else None,
                        })
        except Exception as e:
            logger.error(f"Failed to read ZIP: {e}")

    elif ext == '.rar':
        try:
            import rarfile
            with rarfile.RarFile(path, 'r') as rf:
                for info in rf.infolist():
                    if not info.is_dir():
                        metadata['file_count'] += 1
                        metadata['total_size'] += info.file_size
                        metadata['files'].append({
                            'filename': info.filename,
                            'size': info.file_size,
                            'compress_size': info.compress_size,
                            'modified': info.date_time.isoformat() if info.date_time else None,
                        })
        except ImportError:
            logger.error("rarfile library required for RAR metadata.")
        except Exception as e:
            logger.error(f"Failed to read RAR: {e}")

    elif ext == '.7z':
        try:
            import py7zr
            with py7zr.SevenZipFile(path, 'r') as szf:
                for info in szf.list():
                    if not info.is_directory:
                        metadata['file_count'] += 1
                        metadata['total_size'] += info.uncompressed
                        metadata['files'].append({
                            'filename': info.filename,
                            'size': info.uncompressed,
                            'compress_size': info.compressed,
                            'modified': info.creation.isoformat() if info.creation else None,
                        })
        except ImportError:
            logger.error("py7zr library required for 7z metadata.")
        except Exception as e:
            logger.error(f"Failed to read 7z: {e}")

    else:
        logger.warning(f"Unsupported archive format: {ext}")

    return metadata