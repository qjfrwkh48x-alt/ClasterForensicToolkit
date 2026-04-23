"""
Claster Forensic Toolkit - Disk and Filesystem Forensics Module

This module provides capabilities for:
- NTFS MFT parsing, recovery, and anomaly detection
- USN journal analysis and timeline generation
- Alternate Data Streams (ADS) discovery and extraction
- File carving by signatures for 20+ file types
- Slack space and unallocated space analysis
- FAT/exFAT/Ext4 basic parsing and recovery
- Disk imaging (RAW/dd, E01) and image mounting
"""

from claster.disk.mft import (
    parse_mft, parse_mft_record, find_deleted_mft_records,
    recover_deleted_by_mft, recover_deleted_by_name,
    get_mft_timestamps, export_mft_csv
)
from claster.disk.usn import (
    parse_usn_journal, filter_usn_by_operation, build_usn_timeline
)
from claster.disk.ads import list_ads, extract_ads, find_all_ads, parse_ads_as_file
from claster.disk.anomalies import detect_timestomping, analyze_mft_anomalies
from claster.disk.carving import (
    carve_by_signature, carve_jpeg, carve_png, carve_gif, carve_bmp,
    carve_pdf, carve_zip, carve_rar, carve_7z, carve_exe, carve_elf,
    carve_mp3, carve_mp4, carve_avi, carve_office, carve_html,
    carve_email, carve_sqlite, carve_all
)
from claster.disk.slack import scan_slack_space, scan_unallocated_space, analyze_resident_data
from claster.disk.fat_exfat import parse_fat, parse_exfat, recover_deleted_fat
from claster.disk.ext4 import parse_ext4
from claster.disk.imaging import (
    create_dd_image, create_e01_image, mount_image,
    verify_image_integrity, convert_image_format, split_image
)

from claster.disk.utils import read_sectors, is_physical_drive

__all__ = [
    # MFT
    'parse_mft', 'parse_mft_record', 'find_deleted_mft_records',
    'recover_deleted_by_mft', 'recover_deleted_by_name',
    'get_mft_timestamps', 'export_mft_csv',
    # USN
    'parse_usn_journal', 'filter_usn_by_operation', 'build_usn_timeline',
    # ADS
    'list_ads', 'extract_ads', 'find_all_ads', 'parse_ads_as_file',
    # Anomalies
    'detect_timestomping', 'analyze_mft_anomalies',
    # Carving
    'carve_by_signature', 'carve_jpeg', 'carve_png', 'carve_gif', 'carve_bmp',
    'carve_pdf', 'carve_zip', 'carve_rar', 'carve_7z', 'carve_exe', 'carve_elf',
    'carve_mp3', 'carve_mp4', 'carve_avi', 'carve_office', 'carve_html',
    'carve_email', 'carve_sqlite', 'carve_all',
    # Slack
    'scan_slack_space', 'scan_unallocated_space', 'analyze_resident_data',
    # FAT/exFAT
    'parse_fat', 'parse_exfat', 'recover_deleted_fat',
    # Ext4
    'parse_ext4',
    # Imaging
    'create_dd_image', 'create_e01_image', 'mount_image',
    'verify_image_integrity', 'convert_image_format', 'split_image', 'read_sectors', 'is_physical_drive'
]