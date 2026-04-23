"""
Steganalysis tools: Chi-square test, RS analysis, visual bit-plane inspection.
"""

import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Tuple, List, Dict

from claster.core.logger import get_logger

logger = get_logger(__name__)

def detect_lsb_chi2(image_path: str, threshold: float = 0.05) -> Tuple[bool, float]:
    """
    Perform chi-square test on LSB pairs to detect LSB embedding.
    Returns (is_stego, p_value).
    """
    img = Image.open(image_path)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    pixels = np.array(img).flatten()

    # Count frequencies of each byte value
    hist, _ = np.histogram(pixels, bins=256, range=(0, 256))

    # For LSB steganography, the distribution of PoVs (pairs of values) becomes more uniform.
    # Pair values that differ only in LSB: (2k, 2k+1)
    chi2 = 0.0
    degrees = 0
    for k in range(0, 256, 2):
        n1 = hist[k]
        n2 = hist[k+1]
        if n1 + n2 > 0:
            expected = (n1 + n2) / 2
            chi2 += ((n1 - expected)**2) / expected
            chi2 += ((n2 - expected)**2) / expected
            degrees += 1

    from scipy.stats import chi2 as chi2_dist
    p_value = 1 - chi2_dist.cdf(chi2, degrees - 1)
    is_stego = p_value > threshold
    logger.info(f"Chi-square test: p={p_value:.4f}, stego={is_stego}")
    return is_stego, p_value

def detect_lsb_rs(image_path: str) -> Dict[str, float]:
    """
    RS (Regular-Singular) analysis for LSB detection.
    Estimates the embedding rate based on smoothness groups.
    """
    img = Image.open(image_path).convert('L')
    pixels = np.array(img, dtype=np.int32)

    def f(x):
        return x

    def f_neg(x):
        return x ^ 1  # flip LSB

    def discrimination(x, mask):
        # Measure smoothness as sum of absolute differences with neighbors
        diff = 0
        h, w = x.shape
        for i in range(h):
            for j in range(w):
                if mask[i, j] == 1:
                    # Compare with right and down neighbors
                    if j+1 < w:
                        diff += abs(int(x[i,j]) - int(x[i,j+1]))
                    if i+1 < h:
                        diff += abs(int(x[i,j]) - int(x[i+1,j]))
        return diff

    # Create random mask for groups
    mask = np.random.randint(0, 2, pixels.shape)
    # Compute Rm, Sm, R-m, S-m
    # Placeholder: actual RS is more complex
    logger.warning("RS analysis is a simplified placeholder; full implementation requires group classification.")
    return {'estimated_rate': 0.0}

def detect_lsb_visual(image_path: str, output_dir: str) -> List[str]:
    """
    Generate visual bit-plane images for manual inspection.
    Saves each bit plane (0-7) as separate PNG files.

    Returns:
        List of saved file paths.
    """
    img = Image.open(image_path).convert('L')
    pixels = np.array(img, dtype=np.uint8)
    h, w = pixels.shape
    output_paths = []

    for bit in range(8):
        bit_plane = (pixels >> bit) & 1
        # Scale to 0-255 for visibility
        vis = (bit_plane * 255).astype(np.uint8)
        out_img = Image.fromarray(vis, mode='L')
        out_path = Path(output_dir) / f"bitplane_{bit}.png"
        out_img.save(out_path)
        output_paths.append(str(out_path))

    logger.info(f"Saved {len(output_paths)} bit-plane images to {output_dir}")
    return output_paths