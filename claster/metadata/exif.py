"""
EXIF metadata extraction from images (JPEG, TIFF, etc.) using Pillow.
"""

import os
from pathlib import Path
from typing import Dict, Optional, Any
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

from claster.core.logger import get_logger

logger = get_logger(__name__)


def _convert_gps_to_decimal(gps_info: Dict) -> Optional[tuple]:
    """
    Convert GPS coordinates from EXIF format (degrees, minutes, seconds) to decimal degrees.
    """
    try:
        def to_degrees(value):
            d, m, s = value
            return d[0] / d[1] + (m[0] / m[1]) / 60 + (s[0] / s[1]) / 3600

        lat = to_degrees(gps_info[2])
        if gps_info[1] == 'S':
            lat = -lat
        lon = to_degrees(gps_info[4])
        if gps_info[3] == 'W':
            lon = -lon
        return lat, lon
    except (KeyError, IndexError, TypeError, ZeroDivisionError):
        return None


def get_exif(image_path: str) -> Dict[str, Any]:
    """
    Extract all EXIF metadata from an image.

    Args:
        image_path: Path to image file.

    Returns:
        Dictionary with EXIF tags (human-readable names) and values.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    exif_data = {}
    try:
        with Image.open(path) as img:
            exif = img._getexif()
            if exif:
                for tag_id, value in exif.items():
                    tag_name = TAGS.get(tag_id, tag_id)
                    # Convert bytes to string if needed
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8', errors='ignore')
                        except:
                            value = value.hex()
                    exif_data[tag_name] = value
    except Exception as e:
        logger.error(f"Failed to extract EXIF from {image_path}: {e}")
    return exif_data


def get_gps_coordinates(image_path: str) -> Optional[Dict[str, float]]:
    """
    Extract GPS coordinates from image EXIF.

    Returns:
        Dictionary with 'latitude' and 'longitude' in decimal degrees, or None.
    """
    exif = get_exif(image_path)
    gps_info = exif.get('GPSInfo')
    if not gps_info:
        return None

    # Map GPS tags to readable names
    parsed_gps = {}
    for key, value in gps_info.items():
        tag_name = GPSTAGS.get(key, key)
        parsed_gps[tag_name] = value

    coords = _convert_gps_to_decimal(parsed_gps)
    if coords:
        return {'latitude': coords[0], 'longitude': coords[1]}
    return None


def remove_exif(image_path: str, output_path: str) -> None:
    """
    Create a copy of an image with all EXIF metadata removed.

    Args:
        image_path: Source image.
        output_path: Destination for cleaned image.
    """
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if necessary (some modes lose data)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            data = list(img.getdata())
            img_without_exif = Image.new(img.mode, img.size)
            img_without_exif.putdata(data)
            img_without_exif.save(output_path)
        logger.info(f"EXIF removed, saved to {output_path}")
    except Exception as e:
        logger.error(f"Failed to remove EXIF: {e}")