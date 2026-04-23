"""
Steganography utility functions.
"""

import struct
from typing import Tuple

def bytes_to_bits(data: bytes) -> str:
    """Convert bytes to a string of '0' and '1'."""
    return ''.join(f'{byte:08b}' for byte in data)

def bits_to_bytes(bits: str) -> bytes:
    """Convert a bit string back to bytes."""
    if len(bits) % 8 != 0:
        bits = bits.ljust((len(bits) + 7) // 8 * 8, '0')
    return bytes(int(bits[i:i+8], 2) for i in range(0, len(bits), 8))

def embed_length_prefix(bits: str, length: int) -> str:
    """
    Prepend a 32-bit length field to the bit string.
    Used for embedding arbitrary-length data.
    """
    length_bits = f'{length:032b}'
    return length_bits + bits

def extract_length_prefix(bits: str) -> Tuple[int, str]:
    """
    Extract the 32-bit length prefix and return (length, remaining_bits).
    """
    if len(bits) < 32:
        return 0, bits
    length = int(bits[:32], 2)
    return length, bits[32:32+length]

def capacity_image_lsb(image_path: str, bits_per_pixel: int = 1) -> int:
    """Calculate maximum bytes that can be embedded in an image using LSB."""
    from PIL import Image
    with Image.open(image_path) as img:
        width, height = img.size
        total_pixels = width * height
        if img.mode == 'RGB':
            total_components = total_pixels * 3
        elif img.mode == 'RGBA':
            total_components = total_pixels * 4
        else:
            total_components = total_pixels  # grayscale
        return (total_components * bits_per_pixel) // 8