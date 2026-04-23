"""
Disk-related utility functions.
"""

import os
import struct

def read_sectors(device: str, start_sector: int, num_sectors: int, sector_size: int = 512) -> bytes:
    """Read raw sectors from a device or image file."""
    with open(device, 'rb') as f:
        f.seek(start_sector * sector_size)
        return f.read(num_sectors * sector_size)

def is_physical_drive(path: str) -> bool:
    """Check if path points to a physical drive (Windows or Linux)."""
    if os.name == 'nt':
        return path.startswith(r'\\\\.\\PhysicalDrive')
    else:
        return path.startswith('/dev/') and not path[-1].isdigit()