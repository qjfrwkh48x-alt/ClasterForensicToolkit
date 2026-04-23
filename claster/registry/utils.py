"""
Utility functions for Windows Registry analysis.
"""

import struct
from datetime import datetime, timedelta
from typing import Optional


def filetime_to_datetime(filetime: int) -> Optional[datetime]:
    """
    Convert Windows FILETIME (64-bit, 100ns intervals since 1601-01-01) to datetime.
    """
    if filetime == 0:
        return None
    # FILETIME epoch: 1601-01-01
    epoch = datetime(1601, 1, 1)
    # Convert to seconds
    timestamp = filetime / 10_000_000  # 100ns -> seconds
    try:
        return epoch + timedelta(seconds=timestamp)
    except OverflowError:
        return None


def decode_rot13(data: bytes) -> str:
    """ROT13 decode for certain registry values (e.g., UserAssist)."""
    if isinstance(data, str):
        data = data.encode('ascii', errors='ignore')
    result = bytearray()
    for b in data:
        if 65 <= b <= 90:  # A-Z
            result.append(((b - 65 + 13) % 26) + 65)
        elif 97 <= b <= 122:  # a-z
            result.append(((b - 97 + 13) % 26) + 97)
        else:
            result.append(b)
    return result.decode('ascii', errors='ignore')


def sid_to_string(sid_bytes: bytes) -> str:
    """
    Convert binary SID to string format (S-1-5-...).
    """
    if not sid_bytes:
        return ""
    # SID structure: Revision (1 byte), SubAuthorityCount (1 byte), IdentifierAuthority (6 bytes),
    # then SubAuthorities (each 4 bytes little-endian)
    if len(sid_bytes) < 8:
        return ""
    rev = sid_bytes[0]
    count = sid_bytes[1]
    auth = int.from_bytes(sid_bytes[2:8], 'big')
    sid_str = f"S-{rev}-{auth}"
    for i in range(count):
        offset = 8 + i * 4
        sub_auth = struct.unpack('<I', sid_bytes[offset:offset+4])[0]
        sid_str += f"-{sub_auth}"
    return sid_str