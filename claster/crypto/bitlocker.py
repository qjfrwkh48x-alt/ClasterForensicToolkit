"""
BitLocker detection and decryption (Windows only, or using dislocker on Linux).
"""

import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Union

from claster.core.logger import get_logger

logger = get_logger(__name__)

def detect_bitlocker(volume_path: str) -> bool:
    """
    Check if a volume is encrypted with BitLocker.

    Args:
        volume_path: Drive letter (Windows, e.g., 'C:') or device path.

    Returns:
        True if BitLocker is detected.
    """
    system = platform.system()
    if system == 'Windows':
        try:
            result = subprocess.run(
                ['manage-bde', '-status', volume_path],
                capture_output=True, text=True, check=False
            )
            if 'Conversion Status:      Fully Encrypted' in result.stdout or \
               'Encryption Method:       XTS-AES' in result.stdout:
                return True
        except Exception as e:
            logger.error(f"manage-bde error: {e}")
        return False
    else:
        # Linux: check for BitLocker signature using dislocker or hexdump
        try:
            with open(volume_path, 'rb') as f:
                header = f.read(512)
            # BitLocker signature at offset 3: "-FVE-FS-"
            if b'-FVE-FS-' in header:
                return True
        except Exception:
            pass
        return False

def decrypt_bitlocker(volume_path: str, recovery_key: str, mount_point: Optional[str] = None) -> bool:
    """
    Unlock and mount a BitLocker volume using recovery key.

    Args:
        volume_path: Encrypted volume path.
        recovery_key: 48-digit recovery key (with or without dashes).
        mount_point: Where to mount (Linux only). If None, auto-generate.

    Returns:
        True if successfully mounted.
    """
    # Clean recovery key (remove dashes)
    recovery_key_clean = recovery_key.replace('-', '').strip()
    if len(recovery_key_clean) != 48 or not recovery_key_clean.isdigit():
        raise ValueError("Invalid recovery key format. Should be 48 digits.")

    system = platform.system()
    if system == 'Windows':
        # Use manage-bde to unlock
        try:
            result = subprocess.run(
                ['manage-bde', '-unlock', volume_path, '-recoverypassword', recovery_key_clean],
                capture_output=True, text=True, check=True
            )
            logger.info(f"BitLocker volume {volume_path} unlocked.")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"manage-bde unlock failed: {e.stderr}")
            return False
    else:
        # Linux: use dislocker
        if not shutil.which('dislocker'):
            logger.error("dislocker is not installed. Install with: sudo apt install dislocker")
            return False

        if mount_point is None:
            mount_point = f"/mnt/bitlocker_{Path(volume_path).name}"

        # Create mount directories
        dislocker_dir = f"/tmp/dislocker_{Path(volume_path).name}"
        Path(dislocker_dir).mkdir(parents=True, exist_ok=True)
        Path(mount_point).mkdir(parents=True, exist_ok=True)

        try:
            # Decrypt with dislocker
            subprocess.run([
                'sudo', 'dislocker', '-V', volume_path,
                f'-p{recovery_key_clean}',
                '--', dislocker_dir
            ], check=True)
            # Mount the decrypted volume
            subprocess.run([
                'sudo', 'mount', '-o', 'ro', f'{dislocker_dir}/dislocker-file', mount_point
            ], check=True)
            logger.info(f"BitLocker volume mounted at {mount_point}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"dislocker/mount failed: {e}")
            return False