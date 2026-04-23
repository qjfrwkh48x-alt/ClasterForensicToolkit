"""
Entropy calculation and encryption detection.
"""

import math
import numpy as np
from pathlib import Path
from typing import Union

from claster.core.logger import get_logger

logger = get_logger(__name__)

def calculate_entropy(data: Union[bytes, str, Path]) -> float:
    """
    Calculate Shannon entropy of data.

    Args:
        data: Bytes, string, or path to file.

    Returns:
        Entropy value between 0 and 8.
    """
    if isinstance(data, (str, Path)):
        path = Path(data)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        with open(path, 'rb') as f:
            data = f.read()
    elif isinstance(data, str):
        data = data.encode('utf-8')

    if not data:
        return 0.0

    # Count byte frequencies
    freq = np.zeros(256, dtype=np.float64)
    for byte in data:
        freq[byte] += 1
    freq /= len(data)

    # Shannon entropy
    entropy = 0.0
    for p in freq:
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy

def detect_encryption(file_path: Union[str, Path], threshold: float = 7.5) -> bool:
    """
    Detect if a file is likely encrypted or compressed based on high entropy.

    Args:
        file_path: Path to file.
        threshold: Entropy threshold (default 7.5).

    Returns:
        True if entropy >= threshold.
    """
    entropy = calculate_entropy(file_path)
    is_encrypted = entropy >= threshold
    logger.info(f"File {file_path} entropy: {entropy:.4f}, encrypted={is_encrypted}")
    return is_encrypted