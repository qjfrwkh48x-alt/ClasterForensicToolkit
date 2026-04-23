"""
NTFS USN Journal parsing using python-ntfs or manual extraction.
"""

import struct
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Generator

from claster.core.logger import get_logger
from claster.core.exceptions import FileSystemError

logger = get_logger(__name__)

# Try to import ntfs library
try:
    import ntfs
    HAS_NTFS = True
except ImportError:
    HAS_NTFS = False

# USN_RECORD_V2 structure (simplified, full structure is larger)
# Size is variable because filename is appended
USN_RECORD_V2_FMT = '<LLLQQQLLL'
USN_RECORD_V2_SIZE = struct.calcsize(USN_RECORD_V2_FMT)

# Reason flags
USN_REASON = {
    0x00000001: 'DATA_OVERWRITE',
    0x00000002: 'DATA_EXTEND',
    0x00000004: 'DATA_TRUNCATION',
    0x00000010: 'NAMED_DATA_OVERWRITE',
    0x00000020: 'NAMED_DATA_EXTEND',
    0x00000040: 'NAMED_DATA_TRUNCATION',
    0x00000100: 'FILE_CREATE',
    0x00000200: 'FILE_DELETE',
    0x00000400: 'EA_CHANGE',
    0x00000800: 'SECURITY_CHANGE',
    0x00001000: 'RENAME_OLD_NAME',
    0x00002000: 'RENAME_NEW_NAME',
    0x00004000: 'INDEXABLE_CHANGE',
    0x00008000: 'BASIC_INFO_CHANGE',
    0x00010000: 'HARD_LINK_CHANGE',
    0x00020000: 'COMPRESSION_CHANGE',
    0x00040000: 'ENCRYPTION_CHANGE',
    0x00080000: 'OBJECT_ID_CHANGE',
    0x00100000: 'REPARSE_POINT_CHANGE',
    0x00200000: 'STREAM_CHANGE',
    0x80000000: 'CLOSE',
}


def _windows_filetime_to_datetime(filetime: int) -> datetime:
    """Convert Windows FILETIME (100ns intervals since 1601-01-01) to datetime."""
    if filetime == 0:
        return None
    # FILETIME epoch: 1601-01-01
    epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
    return epoch + timedelta(microseconds=filetime // 10)


def _parse_usn_record_v2(data: bytes, offset: int) -> Optional[Dict]:
    """Parse a single USN_RECORD_V2 at given offset."""
    if len(data) - offset < USN_RECORD_V2_SIZE:
        return None
    header = data[offset:offset+USN_RECORD_V2_SIZE]
    (
        record_length,
        major_version,
        minor_version,
        file_ref_number,
        parent_file_ref_number,
        usn,
        timestamp,
        reason,
        source_info
    ) = struct.unpack(USN_RECORD_V2_FMT, header)

    # Basic validation
    if record_length < USN_RECORD_V2_SIZE:
        return None
    if major_version != 2:
        return None

    # Extract filename (Unicode, variable length)
    filename_offset = offset + USN_RECORD_V2_SIZE
    filename_end = offset + record_length
    filename_bytes = data[filename_offset:filename_end]
    # Filename is UTF-16LE, null-terminated
    try:
        filename = filename_bytes.decode('utf-16-le').split('\x00')[0]
    except:
        filename = "<non-unicode>"

    return {
        'record_length': record_length,
        'file_ref_number': file_ref_number,
        'parent_file_ref_number': parent_file_ref_number,
        'usn': usn,
        'timestamp': _windows_filetime_to_datetime(timestamp),
        'reason': reason,
        'reason_flags': [USN_REASON.get(1 << i, f'UNKNOWN_{1<<i}') for i in range(32) if reason & (1 << i)],
        'source_info': source_info,
        'filename': filename
    }


def parse_usn_journal(volume_path: str, since_datetime: Optional[datetime] = None) -> List[Dict]:
    """
    Parse USN journal from a live volume or disk image.

    Args:
        volume_path: Path to volume (e.g., '\\.\C:' or image file).
        since_datetime: Only return entries newer than this UTC datetime.

    Returns:
        List of parsed USN records.
    """
    if not HAS_NTFS:
        logger.error("USN journal parsing requires python-ntfs library.")
        raise NotImplementedError("Install python-ntfs to parse USN journal.")

    records = []
    try:
        vol = ntfs.Volume(volume_path)
        # USN journal is stored in $Extend\$UsnJrnl:$J
        # Use ntfs to open the file
        usn_file = vol.get_file_by_path('\\$Extend\\$UsnJrnl')
        if not usn_file:
            logger.warning("USN journal not found on volume.")
            return records

        # The journal data is in the $J stream (alternate data stream)
        # In python-ntfs, we can read the data attribute of the $J stream
        # First find the $J stream
        for attr in usn_file.attributes():
            if attr.type == ntfs.AttributeType.DATA and attr.name == '$J':
                data = attr.read()
                break
        else:
            logger.warning("USN journal $J stream not found.")
            return records

        # Parse all records
        offset = 0
        while offset < len(data):
            rec = _parse_usn_record_v2(data, offset)
            if rec is None:
                break
            if since_datetime is None or rec['timestamp'] >= since_datetime:
                records.append(rec)
            offset += rec['record_length']

    except Exception as e:
        logger.error(f"Failed to parse USN journal: {e}")
        raise FileSystemError(f"USN parsing failed: {e}")

    logger.info(f"Parsed {len(records)} USN journal records.")
    return records


def filter_usn_by_operation(usn_records: List[Dict], operations: List[str]) -> List[Dict]:
    """Filter USN records by operation names (e.g., 'FILE_CREATE', 'FILE_DELETE')."""
    filtered = []
    op_masks = {name: mask for mask, name in USN_REASON.items()}
    target_masks = [op_masks[op] for op in operations if op in op_masks]

    for rec in usn_records:
        reason = rec['reason']
        if any(reason & mask for mask in target_masks):
            filtered.append(rec)
    return filtered


def build_usn_timeline(volume_path: str, output_file: Optional[str] = None) -> List[Dict]:
    """Build a timeline of file system changes from USN journal."""
    records = parse_usn_journal(volume_path)
    timeline = []
    for rec in records:
        timeline.append({
            'timestamp': rec['timestamp'].isoformat() if rec['timestamp'] else None,
            'filename': rec['filename'],
            'operation': '|'.join(rec['reason_flags']),
            'usn': rec['usn']
        })
    if output_file:
        import json
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(timeline, f, indent=2, default=str)
        logger.info(f"USN timeline exported to {output_file}")
    return timeline