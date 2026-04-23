"""
Disk imaging functions: create dd, E01, mount, verify, convert.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import List, Optional, Union

from claster.core.logger import get_logger
from claster.core.hashing import compute_hash, verify_hash
from claster.core.utils import ensure_dir

logger = get_logger(__name__)


def create_dd_image(source: str, output: str, compression: bool = False) -> None:
    """
    Create a raw (dd) image of a source drive/partition.
    Uses Python block copy (cross-platform).
    """
    source_path = source
    # On Windows, physical drives are accessed via \\.\PhysicalDriveN
    if os.name == 'nt' and source.startswith('\\\\.\\'):
        # Use Windows raw disk reading
        pass  # open works

    block_size = 1024 * 1024 * 10  # 10 MB
    total_copied = 0
    try:
        with open(source_path, 'rb') as src, open(output, 'wb') as dst:
            while True:
                chunk = src.read(block_size)
                if not chunk:
                    break
                dst.write(chunk)
                total_copied += len(chunk)
                if total_copied % (100*1024*1024) == 0:
                    logger.debug(f"Copied {total_copied // (1024*1024)} MB")
        logger.info(f"Raw image created: {output} ({total_copied} bytes)")
    except Exception as e:
        logger.error(f"Failed to create dd image: {e}")
        raise


def create_e01_image(source: str, output: str, compression: int = 6) -> None:
    """
    Create an EnCase E01 image.
    Requires ewfacquire (libewf) in PATH or pyewf library.
    """
    try:
        import pyewf
        # pyewf usage
        filenames = pyewf.glob(output + ".E01")
        handle = pyewf.handle()
        handle.open(filenames, 'w')
        # Set compression
        handle.set_compression_level(compression)
        # Write data
        with open(source, 'rb') as src:
            while True:
                chunk = src.read(1024*1024)
                if not chunk:
                    break
                handle.write(chunk)
        handle.close()
        logger.info(f"E01 image created: {output}.E01")
    except ImportError:
        # Fallback to command-line ewfacquire
        if shutil.which('ewfacquire') is None:
            logger.error("ewfacquire not found in PATH. Install libewf or pyewf.")
            raise RuntimeError("E01 creation requires ewfacquire or pyewf.")
        cmd = ['ewfacquire', source, '-t', output, '-c', f'compression:{compression}']
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"E01 image created: {output}.E01")
        except subprocess.CalledProcessError as e:
            logger.error(f"ewfacquire failed: {e.stderr}")
            raise


def mount_image(image_path: str, mount_point: str) -> bool:
    """
    Mount a disk image using appropriate tools.
    Returns True if mounted successfully.
    """
    if sys.platform == 'win32':
        # Use Arsenal Image Mounter or OSFMount command line
        # For simplicity, we'll use PowerShell to mount via DiskPart? Not trivial.
        logger.warning("Automatic mounting on Windows not implemented. Use Arsenal Image Mounter manually.")
        return False
    else:
        # Linux: use mount command with loop device
        if not os.path.exists(mount_point):
            os.makedirs(mount_point, exist_ok=True)
        cmd = ['sudo', 'mount', '-o', 'ro,loop', image_path, mount_point]
        try:
            subprocess.run(cmd, check=True)
            logger.info(f"Mounted {image_path} at {mount_point}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Mount failed: {e}")
            return False


def verify_image_integrity(image_path: str, hash_file: str) -> bool:
    """
    Verify image against stored hash (format: hash *filename or just hash).
    """
    expected_hash = None
    with open(hash_file, 'r') as f:
        content = f.read().strip()
        parts = content.split()
        if len(parts) >= 1:
            expected_hash = parts[0]
    if not expected_hash:
        logger.error("No hash found in hash file.")
        return False
    return verify_hash(image_path, expected_hash)


def convert_image_format(input_image: str, output_format: str) -> str:
    """
    Convert between RAW, E01, AFF using external tools.
    Returns path to converted image.
    """
    output_path = input_image + '.' + output_format
    if output_format.lower() == 'e01':
        create_e01_image(input_image, output_path)
    elif output_format.lower() == 'raw':
        if input_image.lower().endswith('.e01'):
            # Use ewfexport
            if shutil.which('ewfexport') is None:
                raise RuntimeError("ewfexport required to convert E01 to raw.")
            subprocess.run(['ewfexport', '-t', output_path, input_image], check=True)
        else:
            shutil.copy(input_image, output_path)
    else:
        raise ValueError(f"Unsupported output format: {output_format}")
    return output_path


def split_image(image_path: str, chunk_size_mb: int = 2000) -> List[str]:
    """Split a raw image into multiple files (e.g., for FAT32 compatibility)."""
    chunk_size = chunk_size_mb * 1024 * 1024
    parts = []
    with open(image_path, 'rb') as f:
        part_num = 0
        while True:
            part_data = f.read(chunk_size)
            if not part_data:
                break
            part_name = f"{image_path}.{part_num:03d}"
            with open(part_name, 'wb') as pf:
                pf.write(part_data)
            parts.append(part_name)
            part_num += 1
    logger.info(f"Image split into {len(parts)} parts of {chunk_size_mb} MB each.")
    return parts