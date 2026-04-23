"""
LSB (Least Significant Bit) steganography for images.
Supports PNG, BMP, and lossless formats.
"""

import numpy as np
from PIL import Image
from pathlib import Path
from typing import Optional

from claster.core.logger import get_logger
from claster.stego.utils import (
    bytes_to_bits, bits_to_bytes,
    embed_length_prefix, extract_length_prefix
)

logger = get_logger(__name__)

def _embed_bit_sequence(pixels: np.ndarray, bit_sequence: str) -> np.ndarray:
    """
    Embed a bit sequence into the LSB of image pixels.
    Modifies pixels in-place.
    """
    flat = pixels.flatten()
    total_bits = len(bit_sequence)
    if total_bits > len(flat):
        raise ValueError(f"Data too large: {total_bits} bits, capacity {len(flat)} bits")

    for i, bit in enumerate(bit_sequence):
        # Clear LSB and set to bit value
        flat[i] = (flat[i] & 0xFE) | int(bit)
    return flat.reshape(pixels.shape)

def _extract_bit_sequence(pixels: np.ndarray, num_bits: int) -> str:
    """Extract a bit sequence from LSBs of pixels."""
    flat = pixels.flatten()
    bits = []
    for i in range(min(num_bits, len(flat))):
        bits.append(str(flat[i] & 1))
    return ''.join(bits)

def hide_text_lsb(image_path: str, text: str, output_path: str) -> None:
    """
    Embed text into an image using LSB.

    Args:
        image_path: Source image (PNG recommended).
        text: Text to hide.
        output_path: Output image path (PNG to avoid compression).
    """
    img = Image.open(image_path)
    if img.mode not in ('RGB', 'RGBA', 'L'):
        img = img.convert('RGB')
    pixels = np.array(img, dtype=np.uint8)

    data_bytes = text.encode('utf-8')
    bits = bytes_to_bits(data_bytes)
    bits_with_len = embed_length_prefix(bits, len(bits))

    new_pixels = _embed_bit_sequence(pixels, bits_with_len)
    new_img = Image.fromarray(new_pixels, mode=img.mode)
    new_img.save(output_path, format='PNG')
    logger.info(f"Text embedded into {output_path} ({len(data_bytes)} bytes)")

def extract_text_lsb(image_path: str) -> str:
    """
    Extract hidden text from an LSB-stego image.

    Returns:
        Extracted text string.
    """
    img = Image.open(image_path)
    pixels = np.array(img, dtype=np.uint8)
    flat = pixels.flatten()

    # First extract 32 bits for length
    if len(flat) < 32:
        return ""
    length_bits = ''.join(str(flat[i] & 1) for i in range(32))
    data_len = int(length_bits, 2)

    # Extract data bits
    if data_len == 0 or data_len > len(flat) - 32:
        return ""
    data_bits = ''.join(str(flat[32 + i] & 1) for i in range(data_len))
    data_bytes = bits_to_bytes(data_bits)
    try:
        text = data_bytes.decode('utf-8')
    except UnicodeDecodeError:
        text = data_bytes.decode('latin-1', errors='ignore')
    logger.info(f"Extracted {len(text)} characters from {image_path}")
    return text

def hide_file_lsb(image_path: str, file_path: str, output_path: str) -> None:
    """Embed any file into an image using LSB."""
    with open(file_path, 'rb') as f:
        data = f.read()
    img = Image.open(image_path)
    if img.mode not in ('RGB', 'RGBA', 'L'):
        img = img.convert('RGB')
    pixels = np.array(img, dtype=np.uint8)

    bits = bytes_to_bits(data)
    bits_with_len = embed_length_prefix(bits, len(bits))
    new_pixels = _embed_bit_sequence(pixels, bits_with_len)
    new_img = Image.fromarray(new_pixels, mode=img.mode)
    new_img.save(output_path, format='PNG')
    logger.info(f"File embedded into {output_path} ({len(data)} bytes)")

def extract_file_lsb(image_path: str, output_file: str) -> None:
    """Extract hidden file from an LSB-stego image."""
    img = Image.open(image_path)
    pixels = np.array(img, dtype=np.uint8)
    flat = pixels.flatten()

    if len(flat) < 32:
        return
    length_bits = ''.join(str(flat[i] & 1) for i in range(32))
    data_len = int(length_bits, 2)

    if data_len == 0 or data_len > len(flat) - 32:
        return
    data_bits = ''.join(str(flat[32 + i] & 1) for i in range(data_len))
    data_bytes = bits_to_bytes(data_bits)

    with open(output_file, 'wb') as f:
        f.write(data_bytes)
    logger.info(f"File extracted to {output_file} ({len(data_bytes)} bytes)")