"""
File carving based on header/footer signatures.
Supports 20+ file types.
"""

import os
import re
import struct
import binascii
from pathlib import Path
from typing import List, Dict, Optional, Tuple, BinaryIO

from claster.core.logger import get_logger
from claster.core.utils import ensure_dir, human_size

logger = get_logger(__name__)

# Signature database
SIGNATURES = {
    'jpeg': {
        'headers': [b'\xFF\xD8\xFF'],
        'footers': [b'\xFF\xD9'],
        'ext': '.jpg'
    },
    'png': {
        'headers': [b'\x89PNG\r\n\x1A\n'],
        'footers': [b'IEND\xAEB`\x82'],
        'ext': '.png'
    },
    'gif': {
        'headers': [b'GIF87a', b'GIF89a'],
        'footers': [b'\x00\x3B'],
        'ext': '.gif'
    },
    'bmp': {
        'headers': [b'BM'],
        'footers': [],  # no standard footer, carve by size from header
        'ext': '.bmp',
        'size_offset': 2,
        'size_format': '<I'
    },
    'pdf': {
        'headers': [b'%PDF'],
        'footers': [b'%%EOF'],
        'ext': '.pdf'
    },
    'zip': {
        'headers': [b'PK\x03\x04'],
        'footers': [],  # complex, use end of central directory
        'ext': '.zip'
    },
    'rar': {
        'headers': [b'Rar!\x1A\x07\x00', b'Rar!\x1A\x07\x01\x00'],
        'footers': [],
        'ext': '.rar'
    },
    '7z': {
        'headers': [b"7z\xBC\xAF'\x1C"],
        'footers': [],
        'ext': '.7z'
    },
    'exe': {
        'headers': [b'MZ'],
        'footers': [],  # PE files have size in header
        'ext': '.exe'
    },
    'elf': {
        'headers': [b'\x7FELF'],
        'footers': [],
        'ext': '.elf'
    },
    'mp3': {
        'headers': [b'\xFF\xFB', b'\xFF\xF3', b'\xFF\xF2', b'\xFF\xF1'],  # ID3v2 also common
        'footers': [],
        'ext': '.mp3'
    },
    'mp4': {
        'headers': [b'\x00\x00\x00\x18ftypmp42', b'\x00\x00\x00\x20ftypisom'],
        'footers': [],
        'ext': '.mp4'
    },
    'avi': {
        'headers': [b'RIFF', b'AVI '],
        'footers': [],
        'ext': '.avi'
    },
    'office': {
        'headers': [b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'],  # OLE2
        'footers': [],
        'ext': '.doc'
    },
    'html': {
        'headers': [b'<html', b'<HTML', b'<!DOCTYPE html'],
        'footers': [b'</html>', b'</HTML>'],
        'ext': '.html'
    },
    'eml': {
        'headers': [b'From:', b'Received:'],
        'footers': [],
        'ext': '.eml'
    },
    'sqlite': {
        'headers': [b'SQLite format 3\x00'],
        'footers': [],
        'ext': '.sqlite'
    },
}


def _find_all_occurrences(data: bytes, pattern: bytes, start: int = 0) -> List[int]:
    """Return list of offsets where pattern occurs."""
    offsets = []
    pos = start
    while True:
        pos = data.find(pattern, pos)
        if pos == -1:
            break
        offsets.append(pos)
        pos += 1
    return offsets


def carve_by_signature(
    image_path: str,
    signatures: List[str],
    output_dir: str,
    min_size: int = 1024,
    max_size: int = 1024*1024*1024  # 1 GB
) -> Dict[str, int]:
    """
    Universal carving function.
    Carves files based on header/footer signatures.

    Args:
        image_path: Path to disk image or raw device.
        signatures: List of signature keys from SIGNATURES dict (e.g., ['jpeg','png']).
        output_dir: Directory to save carved files.
        min_size: Minimum carved file size.
        max_size: Maximum carved file size.

    Returns:
        Dictionary with counts of carved files per type.
    """
    ensure_dir(output_dir)
    counts = {sig: 0 for sig in signatures}

    with open(image_path, 'rb') as f:
        data = f.read()  # For large images, memory mapping is better; here we do simple read

    for sig_key in signatures:
        sig = SIGNATURES.get(sig_key)
        if not sig:
            logger.error(f"Unknown signature: {sig_key}")
            continue

        headers = sig['headers']
        footers = sig['footers']
        ext = sig['ext']

        for header in headers:
            header_offsets = _find_all_occurrences(data, header)
            logger.debug(f"Found {len(header_offsets)} potential {sig_key} headers.")

            for h_off in header_offsets:
                # Determine footer or length
                if footers:
                    # Find the first footer after header
                    footer_pos = None
                    for footer in footers:
                        fpos = data.find(footer, h_off + len(header))
                        if fpos != -1:
                            footer_pos = fpos + len(footer)
                            break
                    if footer_pos:
                        end = footer_pos
                    else:
                        # No footer found, use max carve size or skip
                        continue
                else:
                    # Try to get size from header (e.g., BMP)
                    if 'size_offset' in sig and 'size_format' in sig:
                        size_offset = sig['size_offset']
                        size_fmt = sig['size_format']
                        size_start = h_off + size_offset
                        if size_start + struct.calcsize(size_fmt) <= len(data):
                            file_size = struct.unpack(size_fmt, data[size_start:size_start+struct.calcsize(size_fmt)])[0]
                            end = h_off + file_size
                        else:
                            continue
                    else:
                        # Default: carve up to next header or max_size
                        next_header = len(data)
                        for next_hdr in headers:
                            nh = data.find(next_hdr, h_off + len(header))
                            if nh != -1 and nh < next_header:
                                next_header = nh
                        end = min(h_off + max_size, next_header)

                size = end - h_off
                if min_size <= size <= max_size:
                    out_path = Path(output_dir) / f"{sig_key}_{counts[sig_key]:06d}{ext}"
                    with open(out_path, 'wb') as out:
                        out.write(data[h_off:end])
                    counts[sig_key] += 1
                    logger.debug(f"Carved {sig_key} to {out_path}")

    logger.info(f"Carving completed. Counts: {counts}")
    return counts


# Specialized functions (convenience wrappers)
def carve_jpeg(image_file: str, output_dir: str) -> int:
    return carve_by_signature(image_file, ['jpeg'], output_dir).get('jpeg', 0)

def carve_png(image_file: str, output_dir: str) -> int:
    return carve_by_signature(image_file, ['png'], output_dir).get('png', 0)

def carve_gif(image_file: str, output_dir: str) -> int:
    return carve_by_signature(image_file, ['gif'], output_dir).get('gif', 0)

def carve_bmp(image_file: str, output_dir: str) -> int:
    return carve_by_signature(image_file, ['bmp'], output_dir).get('bmp', 0)

def carve_pdf(image_file: str, output_dir: str) -> int:
    return carve_by_signature(image_file, ['pdf'], output_dir).get('pdf', 0)

def carve_zip(image_file: str, output_dir: str) -> int:
    return carve_by_signature(image_file, ['zip'], output_dir).get('zip', 0)

def carve_rar(image_file: str, output_dir: str) -> int:
    return carve_by_signature(image_file, ['rar'], output_dir).get('rar', 0)

def carve_7z(image_file: str, output_dir: str) -> int:
    return carve_by_signature(image_file, ['7z'], output_dir).get('7z', 0)

def carve_exe(image_file: str, output_dir: str) -> int:
    return carve_by_signature(image_file, ['exe'], output_dir).get('exe', 0)

def carve_elf(image_file: str, output_dir: str) -> int:
    return carve_by_signature(image_file, ['elf'], output_dir).get('elf', 0)

def carve_mp3(image_file: str, output_dir: str) -> int:
    return carve_by_signature(image_file, ['mp3'], output_dir).get('mp3', 0)

def carve_mp4(image_file: str, output_dir: str) -> int:
    return carve_by_signature(image_file, ['mp4'], output_dir).get('mp4', 0)

def carve_avi(image_file: str, output_dir: str) -> int:
    return carve_by_signature(image_file, ['avi'], output_dir).get('avi', 0)

def carve_office(image_file: str, output_dir: str) -> int:
    return carve_by_signature(image_file, ['office'], output_dir).get('office', 0)

def carve_html(image_file: str, output_dir: str) -> int:
    return carve_by_signature(image_file, ['html'], output_dir).get('html', 0)

def carve_email(image_file: str, output_dir: str) -> int:
    return carve_by_signature(image_file, ['eml'], output_dir).get('eml', 0)

def carve_sqlite(image_file: str, output_dir: str) -> int:
    return carve_by_signature(image_file, ['sqlite'], output_dir).get('sqlite', 0)

def carve_all(image_file: str, output_dir: str) -> Dict[str, int]:
    """Carve all supported file types."""
    return carve_by_signature(image_file, list(SIGNATURES.keys()), output_dir)