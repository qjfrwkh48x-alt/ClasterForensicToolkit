"""
Claster Forensic Toolkit - Metadata Extraction Module

Provides functions to extract metadata from:
- Images (EXIF, GPS)
- Office documents (DOCX, XLSX, PPTX)
- PDF files
- Audio and video files
- Archives (ZIP, RAR, 7z)
- Windows shortcut files (.lnk)
- Filesystem metadata (size, timestamps)
"""

from claster.metadata.exif import get_exif, get_gps_coordinates, remove_exif
from claster.metadata.office import get_office_metadata, get_excel_metadata, get_ppt_metadata
from claster.metadata.pdf import get_pdf_metadata
from claster.metadata.audio_video import get_audio_metadata, get_video_metadata
from claster.metadata.archive import get_archive_metadata
from claster.metadata.lnk_fs import get_lnk_metadata, get_fs_metadata

__all__ = [
    'get_exif',
    'get_gps_coordinates',
    'remove_exif',
    'get_office_metadata',
    'get_excel_metadata',
    'get_ppt_metadata',
    'get_pdf_metadata',
    'get_audio_metadata',
    'get_video_metadata',
    'get_archive_metadata',
    'get_lnk_metadata',
    'get_fs_metadata',
]