"""
Echo hiding steganography for audio files (WAV).
Based on embedding data by introducing delayed echoes with different amplitudes.
"""

import wave
import numpy as np
import struct
from pathlib import Path
from typing import Optional

from claster.core.logger import get_logger
from claster.stego.utils import bytes_to_bits, bits_to_bytes, embed_length_prefix

logger = get_logger(__name__)

def hide_audio_echo(audio_path: str, text: str, output_path: str,
                    delay: int = 50, decay: float = 0.5, block_size: int = 1024) -> None:
    """
    Hide text in audio using echo hiding.

    Args:
        audio_path: Input WAV file.
        text: Text to hide.
        output_path: Output WAV file.
        delay: Echo delay in samples (determines bit '1' delay; '0' uses delay//2).
        decay: Echo amplitude relative to original.
        block_size: Number of samples per hidden bit.
    """
    with wave.open(audio_path, 'rb') as wav_in:
        params = wav_in.getparams()
        frames = wav_in.readframes(params.nframes)
        dtype = 'int16' if params.sampwidth == 2 else 'int32'
        audio = np.frombuffer(frames, dtype=dtype).astype(np.float32)

    # Prepare data bits
    data_bytes = text.encode('utf-8')
    bits = bytes_to_bits(data_bytes)
    bits_with_len = embed_length_prefix(bits, len(bits))
    bit_array = np.array([int(b) for b in bits_with_len])

    # Ensure audio length is enough
    total_samples = len(audio)
    required_samples = len(bit_array) * block_size
    if required_samples > total_samples:
        raise ValueError(f"Audio too short: need {required_samples} samples, have {total_samples}")

    # Embed using echo kernel
    output = audio.copy()
    for i, bit in enumerate(bit_array):
        start = i * block_size
        end = min(start + block_size, total_samples)
        if bit == 1:
            echo_delay = delay
        else:
            echo_delay = delay // 2
        # Add echo
        echo_start = start + echo_delay
        if echo_start < total_samples:
            length = min(block_size, total_samples - echo_start)
            output[echo_start:echo_start+length] += decay * audio[start:start+length]

    # Normalize to prevent clipping
    max_val = np.max(np.abs(output))
    if max_val > 32767:
        output = output * (32767 / max_val)
    output = output.astype(dtype)

    with wave.open(output_path, 'wb') as wav_out:
        wav_out.setparams(params)
        wav_out.writeframes(output.tobytes())
    logger.info(f"Text embedded into audio {output_path} ({len(data_bytes)} bytes)")

def extract_audio_echo(audio_path: str, original_audio_path: Optional[str] = None,
                       delay: int = 50, block_size: int = 1024) -> str:
    """
    Extract hidden text from echo-stego audio.

    Args:
        audio_path: Stego audio WAV.
        original_audio_path: Original clean audio (required for reliable extraction).
        delay: Echo delay used during embedding.
        block_size: Block size used.

    Returns:
        Extracted text.
    """
    if original_audio_path is None:
        logger.error("Original audio is required for echo extraction (reference).")
        return ""

    with wave.open(audio_path, 'rb') as wav_stego, wave.open(original_audio_path, 'rb') as wav_orig:
        params = wav_stego.getparams()
        frames_stego = wav_stego.readframes(params.nframes)
        frames_orig = wav_orig.readframes(params.nframes)
        dtype = 'int16' if params.sampwidth == 2 else 'int32'
        audio_stego = np.frombuffer(frames_stego, dtype=dtype).astype(np.float32)
        audio_orig = np.frombuffer(frames_orig, dtype=dtype).astype(np.float32)

    total_samples = len(audio_orig)
    bits = []
    # First extract 32 bits for length
    for i in range(32):
        start = i * block_size
        end = start + block_size
        if end > total_samples:
            break
        # Compute cepstrum or correlation to detect echo delay
        segment_stego = audio_stego[start:end]
        segment_orig = audio_orig[start:end]
        # Simplified: correlate with delayed version
        corr1 = np.correlate(segment_stego - segment_orig, segment_orig[delay//2:], mode='valid')
        corr2 = np.correlate(segment_stego - segment_orig, segment_orig[delay:], mode='valid')
        if np.max(corr2) > np.max(corr1):
            bits.append('1')
        else:
            bits.append('0')

    length = int(''.join(bits[:32]), 2)
    data_bits = []
    for i in range(32, 32 + length):
        start = i * block_size
        end = start + block_size
        if end > total_samples:
            break
        segment_stego = audio_stego[start:end]
        segment_orig = audio_orig[start:end]
        corr1 = np.correlate(segment_stego - segment_orig, segment_orig[delay//2:], mode='valid')
        corr2 = np.correlate(segment_stego - segment_orig, segment_orig[delay:], mode='valid')
        data_bits.append('1' if np.max(corr2) > np.max(corr1) else '0')

    data_bytes = bits_to_bytes(''.join(data_bits))
    return data_bytes.decode('utf-8', errors='ignore')