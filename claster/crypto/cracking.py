"""
Password cracking for ZIP, PDF, RAR, 7z archives using dictionary and bruteforce.
"""

import zipfile
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Optional, List, Generator, Union

from claster.core.logger import get_logger

logger = get_logger(__name__)

# ----------------------------------------------------------------------
# ZIP cracking
# ----------------------------------------------------------------------
def crack_zip_dict(zip_path: Union[str, Path], dict_file: Union[str, Path]) -> Optional[str]:
    """
    Perform dictionary attack on password-protected ZIP archive.

    Args:
        zip_path: Path to ZIP file.
        dict_file: Path to dictionary file (one password per line).

    Returns:
        Password if found, else None.
    """
    zip_path = Path(zip_path)
    dict_file = Path(dict_file)

    if not zip_path.exists():
        raise FileNotFoundError(f"ZIP not found: {zip_path}")
    if not dict_file.exists():
        raise FileNotFoundError(f"Dictionary not found: {dict_file}")

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Check if any file is encrypted
            encrypted_files = [f for f in zf.infolist() if f.flag_bits & 0x1]
            if not encrypted_files:
                logger.warning("ZIP is not encrypted.")
                return None

            test_file = encrypted_files[0].filename

            with open(dict_file, 'r', encoding='utf-8', errors='ignore') as df:
                for line in df:
                    pwd = line.strip()
                    if not pwd:
                        continue
                    try:
                        zf.read(test_file, pwd=pwd.encode('utf-8'))
                        logger.info(f"Password found: {pwd}")
                        return pwd
                    except (RuntimeError, zipfile.BadZipFile):
                        continue
                    except Exception:
                        continue
    except Exception as e:
        logger.error(f"Error during ZIP cracking: {e}")

    logger.info("Password not found in dictionary.")
    return None

def crack_zip_bruteforce(zip_path: Union[str, Path], max_len: int = 4,
                         charset: str = 'abcdefghijklmnopqrstuvwxyz0123456789') -> Optional[str]:
    """
    Bruteforce ZIP password (exhaustive search). Use only for short passwords.

    Args:
        zip_path: Path to ZIP.
        max_len: Maximum password length.
        charset: Characters to use.

    Returns:
        Password if found.
    """
    import itertools

    zip_path = Path(zip_path)
    if not zip_path.exists():
        raise FileNotFoundError(f"ZIP not found: {zip_path}")

    with zipfile.ZipFile(zip_path, 'r') as zf:
        encrypted_files = [f for f in zf.infolist() if f.flag_bits & 0x1]
        if not encrypted_files:
            logger.warning("ZIP is not encrypted.")
            return None
        test_file = encrypted_files[0].filename

        for length in range(1, max_len + 1):
            for combo in itertools.product(charset, repeat=length):
                pwd = ''.join(combo)
                try:
                    zf.read(test_file, pwd=pwd.encode('utf-8'))
                    logger.info(f"Password found: {pwd}")
                    return pwd
                except (RuntimeError, zipfile.BadZipFile):
                    continue
                except Exception:
                    continue

    logger.info("Bruteforce failed.")
    return None

# ----------------------------------------------------------------------
# PDF cracking (uses pdf2john + john)
# ----------------------------------------------------------------------
def crack_pdf_dict(pdf_path: Union[str, Path], dict_file: Union[str, Path]) -> Optional[str]:
    """
    Dictionary attack on PDF using pdf2john and john the ripper.

    Args:
        pdf_path: Path to PDF.
        dict_file: Dictionary file.

    Returns:
        Password if found.
    """
    pdf_path = Path(pdf_path)
    dict_file = Path(dict_file)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if not dict_file.exists():
        raise FileNotFoundError(f"Dictionary not found: {dict_file}")

    # Create temporary hash file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.hash', delete=False) as hash_f:
        hash_path = hash_f.name
    try:
        # Extract hash using pdf2john
        result = subprocess.run(['pdf2john', str(pdf_path)], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"pdf2john failed: {result.stderr}")
            return None
        # pdf2john outputs the hash to stdout; write to file
        with open(hash_path, 'w') as f:
            f.write(result.stdout.strip())

        # Run john with dictionary
        john_cmd = ['john', f'--wordlist={dict_file}', hash_path]
        subprocess.run(john_cmd, capture_output=True, check=False)

        # Show cracked password
        show_cmd = ['john', '--show', hash_path]
        show_result = subprocess.run(show_cmd, capture_output=True, text=True)
        if show_result.returncode == 0 and show_result.stdout:
            # Output format: filename:password
            lines = show_result.stdout.strip().split('\n')
            if lines:
                parts = lines[0].split(':', 1)
                if len(parts) >= 2:
                    pwd = parts[1]
                    logger.info(f"PDF password found: {pwd}")
                    return pwd
    except Exception as e:
        logger.error(f"Error cracking PDF: {e}")
    finally:
        if os.path.exists(hash_path):
            os.unlink(hash_path)

    logger.info("PDF password not found.")
    return None

def crack_pdf_bruteforce(pdf_path: Union[str, Path], max_len: int = 4,
                         charset: str = 'abcdefghijklmnopqrstuvwxyz0123456789') -> Optional[str]:
    """
    Bruteforce PDF using john's incremental mode.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.hash', delete=False) as hash_f:
        hash_path = hash_f.name
    try:
        result = subprocess.run(['pdf2john', str(pdf_path)], capture_output=True, text=True)
        if result.returncode != 0:
            return None
        with open(hash_path, 'w') as f:
            f.write(result.stdout.strip())

        # Run john incremental with max length
        john_cmd = ['john', f'--incremental=ASCII', f'--max-len={max_len}', hash_path]
        subprocess.run(john_cmd, capture_output=True, check=False)

        show_cmd = ['john', '--show', hash_path]
        show_result = subprocess.run(show_cmd, capture_output=True, text=True)
        if show_result.returncode == 0 and show_result.stdout:
            lines = show_result.stdout.strip().split('\n')
            if lines:
                parts = lines[0].split(':', 1)
                if len(parts) >= 2:
                    return parts[1]
    finally:
        if os.path.exists(hash_path):
            os.unlink(hash_path)
    return None

# ----------------------------------------------------------------------
# RAR cracking (requires unrar and rar2john)
# ----------------------------------------------------------------------
def crack_rar_dict(rar_path: Union[str, Path], dict_file: Union[str, Path]) -> Optional[str]:
    """
    Dictionary attack on RAR archive using rar2john.
    """
    rar_path = Path(rar_path)
    dict_file = Path(dict_file)

    if not rar_path.exists():
        raise FileNotFoundError(f"RAR not found: {rar_path}")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.hash', delete=False) as hash_f:
        hash_path = hash_f.name
    try:
        result = subprocess.run(['rar2john', str(rar_path)], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("rar2john failed. Ensure john is installed with RAR support.")
            return None
        with open(hash_path, 'w') as f:
            f.write(result.stdout.strip())

        john_cmd = ['john', f'--wordlist={dict_file}', hash_path]
        subprocess.run(john_cmd, capture_output=True)

        show_result = subprocess.run(['john', '--show', hash_path], capture_output=True, text=True)
        if show_result.returncode == 0 and show_result.stdout:
            lines = show_result.stdout.strip().split('\n')
            if lines:
                parts = lines[0].split(':', 1)
                if len(parts) >= 2:
                    pwd = parts[1]
                    logger.info(f"RAR password found: {pwd}")
                    return pwd
    except Exception as e:
        logger.error(f"Error cracking RAR: {e}")
    finally:
        if os.path.exists(hash_path):
            os.unlink(hash_path)
    return None

# ----------------------------------------------------------------------
# 7z cracking (requires 7z2john)
# ----------------------------------------------------------------------
def crack_7z_dict(sz_path: Union[str, Path], dict_file: Union[str, Path]) -> Optional[str]:
    """
    Dictionary attack on 7z archive using 7z2john.
    """
    sz_path = Path(sz_path)
    dict_file = Path(dict_file)

    if not sz_path.exists():
        raise FileNotFoundError(f"7z not found: {sz_path}")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.hash', delete=False) as hash_f:
        hash_path = hash_f.name
    try:
        result = subprocess.run(['7z2john', str(sz_path)], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("7z2john failed.")
            return None
        with open(hash_path, 'w') as f:
            f.write(result.stdout.strip())

        subprocess.run(['john', f'--wordlist={dict_file}', hash_path], capture_output=True)
        show_result = subprocess.run(['john', '--show', hash_path], capture_output=True, text=True)
        if show_result.returncode == 0 and show_result.stdout:
            lines = show_result.stdout.strip().split('\n')
            if lines:
                parts = lines[0].split(':', 1)
                if len(parts) >= 2:
                    return parts[1]
    finally:
        if os.path.exists(hash_path):
            os.unlink(hash_path)
    return None