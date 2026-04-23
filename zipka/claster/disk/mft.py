"""
NTFS Master File Table (MFT) parsing and analysis.

This module uses the 'python-ntfs' library or fallback to 'pytsk3'.
If neither is available, it raises an ImportError with guidance.
"""

import csv
import struct
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union, Generator, Any

from claster.core.logger import get_logger
from claster.core.exceptions import FileSystemError
from claster.core.utils import ensure_dir, human_size

logger = get_logger(__name__)

# Try to import NTFS parsing libraries
try:
    import ntfs
    HAS_NTFS = True
except ImportError:
    HAS_NTFS = False
    logger.warning("python-ntfs library not found. MFT parsing will be limited.")

try:
    import pytsk3
    HAS_TSK = True
except ImportError:
    HAS_TSK = False
    logger.warning("pytsk3 (SleuthKit) not found. Some disk operations may be unavailable.")


# MFT record structure constants
MFT_RECORD_SIZE = 1024  # bytes (usually)
FILE_RECORD_SEGMENT_IN_USE = 0x0001
FILE_RECORD_IS_DIRECTORY = 0x0002


def _get_volume_handle(volume_path: str):
    """
    Open a volume for raw reading using appropriate method.
    Returns a file-like object or TSK Img_Info.
    """
    if volume_path.startswith('\\\\.\\') and HAS_TSK:
        # Physical drive or volume on Windows
        return pytsk3.Img_Info(volume_path)
    elif HAS_TSK:
        # Assume it's a disk image or partition
        return pytsk3.Img_Info(volume_path)
    else:
        # Fallback to standard file open (for raw dd images)
        return open(volume_path, 'rb')


def _parse_mft_record_bytes(volume_path: str, data: bytes, record_number: int) -> Optional[Dict[str, Any]]:
    """
    Parse a 1024-byte MFT record from raw bytes.
    Returns a dictionary with extracted attributes.
    This is a simplified parser; full implementation requires NTFS attribute parsing.
    """
    if len(data) < 48:
        return None

    signature = data[0:4]
    if signature != b'FILE':
        return None

    # Parse fixup array offset and size
    usa_offset = struct.unpack('<H', data[4:6])[0]
    usa_size = struct.unpack('<H', data[6:8])[0]

    # Sequence number and hard link count
    seq_num = struct.unpack('<H', data[16:18])[0]
    hard_links = struct.unpack('<H', data[18:20])[0]

    # Flags: 0x01 = in use, 0x02 = directory
    flags = struct.unpack('<H', data[22:24])[0]
    in_use = bool(flags & 0x0001)
    is_dir = bool(flags & 0x0002)

    # First attribute offset (usually 0x38)
    first_attr_offset = struct.unpack('<H', data[32:34])[0]

    # We'll do a basic attribute walk to find $FILE_NAME and $STANDARD_INFORMATION
    # For a production tool, we'd implement full attribute parsing.
    # Here we extract timestamps from $STANDARD_INFORMATION if possible.

    record_info = {
        'record_number': record_number,
        'in_use': in_use,
        'is_directory': is_dir,
        'sequence_number': seq_num,
        'hard_links': hard_links,
        'filename': None,
        'parent_mft_ref': None,
        'creation_time': None,
        'last_modification_time': None,
        'last_access_time': None,
        'entry_modified_time': None,
        'size': 0,
        'allocated_size': 0,
    }

    # Rough parsing: we'd need to walk attributes. For brevity, we'll note that a full implementation
    # would use an NTFS library (python-ntfs) to avoid reimplementing the wheel.
    # Since this is a large project, we'll use the library approach.

    if HAS_NTFS:
        # Use python-ntfs for proper parsing
        try:
            vol = ntfs.Volume(volume_path)
            mft = vol.get_mft()
            record = mft.get_record(record_number)
            if record:
                record_info['in_use'] = record.is_in_use()
                record_info['filename'] = record.get_filename()
                record_info['size'] = record.get_data_size()
        except Exception as e:
            logger.debug(f"ntfs library error: {e}")

    return record_info


def parse_mft(volume_path: str, output_csv: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Parse the entire MFT and return a list of records.

    Args:
        volume_path: Path to the volume (e.g., '\\.\C:' or '/dev/sda1' or image file).
        output_csv: Optional path to export CSV.

    Returns:
        List of parsed MFT records (each a dict).
    """
    if not HAS_NTFS and not HAS_TSK:
        raise NotImplementedError("MFT parsing requires python-ntfs or pytsk3. Install one.")

    records = []
    if HAS_NTFS:
        try:
            vol = ntfs.Volume(volume_path)
            mft = vol.get_mft()
            for i, record in enumerate(mft.records()):
                if record is None:
                    continue
                rec_dict = {
                    'record_number': i,
                    'in_use': record.is_in_use(),
                    'filename': record.get_filename(),
                    'size': record.get_data_size(),
                    'creation_time': record.get_standard_information().creation_time.isoformat() if record.get_standard_information() else None,
                    'modification_time': record.get_standard_information().last_modification_time.isoformat() if record.get_standard_information() else None,
                    'access_time': record.get_standard_information().last_access_time.isoformat() if record.get_standard_information() else None,
                    'mft_entry_modified': record.get_standard_information().last_mft_change_time.isoformat() if record.get_standard_information() else None,
                }
                records.append(rec_dict)
        except Exception as e:
            logger.error(f"Failed to parse MFT: {e}")
            raise FileSystemError(f"MFT parsing failed: {e}")
    elif HAS_TSK:
        # Use TSK to walk filesystem and extract MFT attributes manually
        img = pytsk3.Img_Info(volume_path)
        fs = pytsk3.FS_Info(img)
        # TSK does not expose raw MFT directly; we would need to read $MFT file and parse.
        # This is complex, so we'll note that for a real tool, a dedicated NTFS library is essential.
        logger.warning("MFT parsing via pytsk3 is limited. Use python-ntfs for full support.")
        # We can still get file entries via TSK's directory walk, but that's not raw MFT.

    if output_csv:
        export_mft_csv(volume_path, output_csv)

    logger.info(f"Parsed {len(records)} MFT records.")
    return records


def parse_mft_record(volume_path: str, record_number: int) -> Optional[Dict[str, Any]]:
    """Parse a single MFT record by its number."""
    if HAS_NTFS:
        vol = ntfs.Volume(volume_path)
        mft = vol.get_mft()
        record = mft.get_record(record_number)
        if record:
            return {
                'record_number': record_number,
                'in_use': record.is_in_use(),
                'filename': record.get_filename(),
                'size': record.get_data_size(),
            }
    return None


def find_deleted_mft_records(volume_path: str) -> List[Dict[str, Any]]:
    """Return all MFT records marked as not in use but still present."""
    all_records = parse_mft(volume_path)
    deleted = [r for r in all_records if not r.get('in_use', True)]
    logger.info(f"Found {len(deleted)} deleted MFT records.")
    return deleted


def recover_deleted_by_mft(volume_path: str, record_number: int, output_path: str) -> bool:
    """
    Attempt to recover a file by its MFT record number.
    Requires reading the data runs from the MFT entry.
    """
    if not HAS_NTFS:
        raise NotImplementedError("Recovery requires python-ntfs.")
    try:
        vol = ntfs.Volume(volume_path)
        mft = vol.get_mft()
        record = mft.get_record(record_number)
        if not record or record.is_in_use():
            return False
        data = record.read_data()
        with open(output_path, 'wb') as f:
            f.write(data)
        logger.info(f"Recovered file from record {record_number} to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Recovery failed: {e}")
        return False


def recover_deleted_by_name(volume_path: str, filename: str, output_path: str) -> bool:
    """Find a deleted file by its name and recover it."""
    deleted = find_deleted_mft_records(volume_path)
    for rec in deleted:
        if rec.get('filename') == filename:
            return recover_deleted_by_mft(volume_path, rec['record_number'], output_path)
    logger.warning(f"Deleted file '{filename}' not found.")
    return False


def get_mft_timestamps(volume_path: str) -> List[Dict]:
    """Extract timestamps from all MFT entries."""
    records = parse_mft(volume_path)
    timestamps = []
    for r in records:
        ts = {
            'filename': r.get('filename'),
            'creation': r.get('creation_time'),
            'modification': r.get('modification_time'),
            'access': r.get('access_time'),
            'mft_change': r.get('mft_entry_modified')
        }
        timestamps.append(ts)
    return timestamps


def export_mft_csv(volume_path: str, csv_path: str) -> None:
    """Export parsed MFT to CSV."""
    records = parse_mft(volume_path)
    if not records:
        return
    fieldnames = list(records[0].keys())
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    logger.info(f"MFT exported to {csv_path}")