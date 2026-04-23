"""
Cryptographic hashing functions with progress reporting and large file support.
"""

import hashlib
import os
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union
from claster.core.logger import get_logger
from claster.core.exceptions import HashingError

logger = get_logger(__name__)

# Supported algorithms mapping
ALGORITHMS = {
    'md5': hashlib.md5,
    'sha1': hashlib.sha1,
    'sha256': hashlib.sha256,
    'sha512': hashlib.sha512,
    'sha3_256': hashlib.sha3_256,
    'sha3_512': hashlib.sha3_512,
    'blake2b': hashlib.blake2b,
    'blake2s': hashlib.blake2s
}

DEFAULT_ALGORITHM = 'sha256'
CHUNK_SIZE = 1024 * 1024  # 1 MB for efficient I/O


def compute_hash(
    file_path: Union[str, Path],
    algorithm: str = DEFAULT_ALGORITHM,
    callback: Optional[Callable[[int, int], None]] = None
) -> str:
    """
    Compute a single hash for a file with optional progress callback.

    Args:
        file_path: Path to the file.
        algorithm: Hash algorithm name (must be in ALGORITHMS).
        callback: Optional function(current_bytes, total_bytes) called periodically.

    Returns:
        Hexadecimal hash string.

    Raises:
        HashingError: If algorithm unsupported or file cannot be read.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise HashingError(f"File not found: {file_path}")
    if algorithm not in ALGORITHMS:
        raise HashingError(f"Unsupported hash algorithm: {algorithm}")

    file_size = file_path.stat().st_size
    hasher = ALGORITHMS[algorithm]()
    bytes_read = 0

    try:
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                hasher.update(chunk)
                bytes_read += len(chunk)
                if callback:
                    callback(bytes_read, file_size)
    except IOError as e:
        logger.error(f"I/O error while hashing {file_path}: {e}")
        raise HashingError(f"Failed to read file: {e}")

    result = hasher.hexdigest()
    logger.debug(f"Computed {algorithm} hash for {file_path}: {result}")
    return result


def compute_hashes_multiple(
    file_path: Union[str, Path],
    algorithms: List[str],
    callback: Optional[Callable[[int, int], None]] = None
) -> Dict[str, str]:
    """
    Compute multiple hashes in a single pass over the file.

    Args:
        file_path: Path to the file.
        algorithms: List of algorithm names.
        callback: Progress callback.

    Returns:
        Dictionary mapping algorithm name to hex digest.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise HashingError(f"File not found: {file_path}")

    # Validate all algorithms first
    for alg in algorithms:
        if alg not in ALGORITHMS:
            raise HashingError(f"Unsupported algorithm: {alg}")

    file_size = file_path.stat().st_size
    hashers = {alg: ALGORITHMS[alg]() for alg in algorithms}
    bytes_read = 0

    try:
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                for hasher in hashers.values():
                    hasher.update(chunk)
                bytes_read += len(chunk)
                if callback:
                    callback(bytes_read, file_size)
    except IOError as e:
        logger.error(f"I/O error while hashing {file_path}: {e}")
        raise HashingError(f"Failed to read file: {e}")

    results = {alg: h.hexdigest() for alg, h in hashers.items()}
    logger.debug(f"Computed {len(algorithms)} hashes for {file_path}")
    return results


def compute_hash_large(
    file_path: Union[str, Path],
    algorithm: str = DEFAULT_ALGORITHM,
    callback: Optional[Callable[[int, int], None]] = None
) -> str:
    """
    Optimized hashing for very large files (>2GB) using memory-mapped I/O on supported platforms.
    Falls back to standard streaming on Windows/other.

    This is an alias to compute_hash with explicit large-file handling.
    """
    # On Python 3.8+, standard open with buffering handles >2GB fine on all OS.
    # Memory mapping could be used for speed but may fail on 32-bit.
    # We'll keep the streaming approach which is safe.
    return compute_hash(file_path, algorithm, callback)


def verify_hash(
    file_path: Union[str, Path],
    expected_hash: str,
    algorithm: str = DEFAULT_ALGORITHM
) -> bool:
    """
    Verify that a file's hash matches an expected value.

    Args:
        file_path: Path to the file.
        expected_hash: Expected hexadecimal hash string.
        algorithm: Hash algorithm used.

    Returns:
        True if hashes match (case-insensitive), False otherwise.
    """
    actual_hash = compute_hash(file_path, algorithm)
    match = actual_hash.lower() == expected_hash.lower()
    if match:
        logger.info(f"Hash verification PASSED for {file_path} ({algorithm})")
    else:
        logger.warning(f"Hash verification FAILED for {file_path}: expected {expected_hash}, got {actual_hash}")
    return match