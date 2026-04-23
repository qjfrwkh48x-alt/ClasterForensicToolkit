"""
Alternate Data Streams (ADS) handling for NTFS.
"""

import os
from pathlib import Path
from typing import List, Tuple, Dict

from claster.core.logger import get_logger

logger = get_logger(__name__)


def list_ads(file_path: str) -> List[Tuple[str, int]]:
    """
    List all alternate data streams of a file.
    Returns list of (stream_name, size).
    """
    streams = []
    if os.name != 'nt':
        logger.warning("ADS are only supported on Windows.")
        return streams

    # Use Windows API via ctypes or PowerShell
    import subprocess
    try:
        result = subprocess.run(
            ['powershell', '-Command', f"Get-Item -Path '{file_path}' -Stream * | Select-Object Stream, Length"],
            capture_output=True, text=True, check=True
        )
        # Parse output (simplified)
        for line in result.stdout.splitlines()[3:]:  # skip header
            if not line.strip():
                continue
            parts = line.strip().split()
            if len(parts) >= 2:
                stream_name = parts[0]
                try:
                    size = int(parts[-1])
                except ValueError:
                    size = 0
                streams.append((stream_name, size))
    except Exception as e:
        logger.error(f"Failed to list ADS: {e}")

    return streams


def extract_ads(file_path: str, ads_name: str, output_path: str) -> bool:
    """
    Extract an ADS to a file.
    """
    if os.name != 'nt':
        return False
    ads_path = f"{file_path}:{ads_name}"
    try:
        with open(ads_path, 'rb') as src, open(output_path, 'wb') as dst:
            dst.write(src.read())
        logger.info(f"Extracted ADS '{ads_name}' from {file_path} to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to extract ADS: {e}")
        return False


def find_all_ads(directory_path: str) -> List[Dict]:
    """
    Recursively find all files with ADS in a directory.
    """
    results = []
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            full_path = os.path.join(root, file)
            streams = list_ads(full_path)
            for name, size in streams:
                if name != ':$DATA':  # default stream
                    results.append({
                        'file': full_path,
                        'stream_name': name,
                        'size': size
                    })
    logger.info(f"Found {len(results)} ADS entries.")
    return results


def parse_ads_as_file(ads_path: str) -> bytes:
    """
    Read the content of an ADS as if it were a file.
    """
    with open(ads_path, 'rb') as f:
        return f.read()