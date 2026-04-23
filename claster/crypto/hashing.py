"""
Cryptographic hashing functions for files and text.
"""

import hashlib
from pathlib import Path
from typing import Union, Optional, Callable

from claster.core.logger import get_logger

logger = get_logger(__name__)

def hash_file(file_path: Union[str, Path], algorithm: str = 'sha256',
              callback: Optional[Callable[[int, int], None]] = None) -> str:
    """
    Compute cryptographic hash of a file.

    Args:
        file_path: Path to the file.
        algorithm: Hash algorithm (md5, sha1, sha256, sha512, sha3_256, sha3_512, blake2b).
        callback: Optional progress callback(current_bytes, total_bytes).

    Returns:
        Hexadecimal hash string.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    algorithms = {
        'md5': hashlib.md5,
        'sha1': hashlib.sha1,
        'sha256': hashlib.sha256,
        'sha512': hashlib.sha512,
        'sha3_256': hashlib.sha3_256,
        'sha3_512': hashlib.sha3_512,
        'blake2b': hashlib.blake2b
    }
    if algorithm not in algorithms:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    hasher = algorithms[algorithm]()
    file_size = file_path.stat().st_size
    bytes_read = 0

    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
            bytes_read += len(chunk)
            if callback:
                callback(bytes_read, file_size)

    digest = hasher.hexdigest()
    logger.debug(f"{algorithm} hash of {file_path}: {digest}")
    return digest

def hash_text(text: str, algorithm: str = 'sha256') -> str:
    """
    Compute hash of a text string.

    Args:
        text: Input text.
        algorithm: Hash algorithm.

    Returns:
        Hexadecimal hash string.
    """
    algorithms = {
        'md5': hashlib.md5,
        'sha1': hashlib.sha1,
        'sha256': hashlib.sha256,
        'sha512': hashlib.sha512,
        'sha3_256': hashlib.sha3_256,
        'sha3_512': hashlib.sha3_512,
        'blake2b': hashlib.blake2b
    }
    if algorithm not in algorithms:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    hasher = algorithms[algorithm]()
    hasher.update(text.encode('utf-8'))
    return hasher.hexdigest()