"""
Claster Forensic Toolkit - Steganography Module

Provides functions for embedding and extracting hidden data in:
- Images (LSB)
- JPEG (DCT coefficients)
- Audio (echo hiding)
- Video (motion vectors)

Also includes steganalysis tools (chi-square, RS analysis, visual bit-plane inspection).
"""

from claster.stego.lsb import (
    hide_text_lsb,
    extract_text_lsb,
    hide_file_lsb,
    extract_file_lsb,
)
from claster.stego.dct import (
    hide_jpeg_dct,
    extract_jpeg_dct,
)
from claster.stego.audio import (
    hide_audio_echo,
    extract_audio_echo,
)
from claster.stego.video import (
    hide_video_motion,
)
from claster.stego.detection import (
    detect_lsb_chi2,
    detect_lsb_rs,
    detect_lsb_visual,
)

__all__ = [
    'hide_text_lsb',
    'extract_text_lsb',
    'hide_file_lsb',
    'extract_file_lsb',
    'hide_jpeg_dct',
    'extract_jpeg_dct',
    'hide_audio_echo',
    'extract_audio_echo',
    'hide_video_motion',
    'detect_lsb_chi2',
    'detect_lsb_rs',
    'detect_lsb_visual',
]