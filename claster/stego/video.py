"""
Video steganography by modifying motion vectors (experimental).
Uses OpenCV to read/write video and manipulate macroblock motion vectors.
"""

import cv2
import numpy as np
from pathlib import Path

from claster.core.logger import get_logger
from claster.stego.utils import bytes_to_bits

logger = get_logger(__name__)

def hide_video_motion(video_path: str, text: str, output_path: str) -> None:
    """
    Hide text in video by altering motion vectors in P/B frames.
    This is a simplified demonstration; full implementation requires
    access to encoder motion estimation.

    Args:
        video_path: Input video file.
        text: Text to hide.
        output_path: Output video file.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    data_bytes = text.encode('utf-8')
    bits = bytes_to_bits(data_bytes)
    bit_idx = 0

    prev_frame = None
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if prev_frame is not None and bit_idx < len(bits):
            # Calculate motion between prev_frame and frame (simplified)
            flow = cv2.calcOpticalFlowFarneback(
                cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY),
                cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY),
                None, 0.5, 3, 15, 3, 5, 1.2, 0
            )
            # Embed bit into motion vector magnitude (e.g., modify horizontal component)
            # This is a placeholder; actual motion vector manipulation requires encoding level.
            if bit_idx < len(bits):
                # For demonstration, we just log
                logger.debug(f"Would embed bit {bits[bit_idx]} at frame {frame_count}")
                bit_idx += 1
        out.write(frame)
        prev_frame = frame.copy()
        frame_count += 1

    cap.release()
    out.release()
    logger.info(f"Video with hidden data saved to {output_path} (conceptual).")