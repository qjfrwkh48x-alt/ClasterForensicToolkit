"""
AES and RSA encryption/decryption functions.
"""

import os
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
from typing import Union, Tuple

from claster.core.logger import get_logger

logger = get_logger(__name__)

# ----------------------------------------------------------------------
# AES
# ----------------------------------------------------------------------
def aes_encrypt(data: Union[bytes, str], key: bytes, mode: str = 'CBC') -> bytes:
    """
    Encrypt data using AES.

    Args:
        data: Plaintext (bytes or str).
        key: AES key (16, 24, or 32 bytes).
        mode: 'CBC' (default) or 'ECB' (not recommended).

    Returns:
        Ciphertext bytes. For CBC, prepended with IV.
    """
    if isinstance(data, str):
        data = data.encode('utf-8')

    if len(key) not in (16, 24, 32):
        raise ValueError("AES key must be 16, 24, or 32 bytes.")

    if mode.upper() == 'CBC':
        iv = get_random_bytes(16)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        ciphertext = cipher.encrypt(pad(data, AES.block_size))
        return iv + ciphertext
    elif mode.upper() == 'ECB':
        cipher = AES.new(key, AES.MODE_ECB)
        ciphertext = cipher.encrypt(pad(data, AES.block_size))
        return ciphertext
    else:
        raise ValueError("Unsupported mode. Use 'CBC' or 'ECB'.")

def aes_decrypt(ciphertext: bytes, key: bytes, mode: str = 'CBC') -> bytes:
    """
    Decrypt AES-encrypted data.

    Args:
        ciphertext: Encrypted bytes (with IV prepended if CBC).
        key: AES key.
        mode: Mode used for encryption.

    Returns:
        Plaintext bytes.
    """
    if len(key) not in (16, 24, 32):
        raise ValueError("AES key must be 16, 24, or 32 bytes.")

    if mode.upper() == 'CBC':
        if len(ciphertext) < 16:
            raise ValueError("Ciphertext too short.")
        iv = ciphertext[:16]
        ct = ciphertext[16:]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        pt = unpad(cipher.decrypt(ct), AES.block_size)
        return pt
    elif mode.upper() == 'ECB':
        cipher = AES.new(key, AES.MODE_ECB)
        pt = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return pt
    else:
        raise ValueError("Unsupported mode.")

# ----------------------------------------------------------------------
# RSA
# ----------------------------------------------------------------------
def generate_rsa_keys(size: int = 2048) -> Tuple[bytes, bytes]:
    """
    Generate RSA key pair.

    Args:
        size: Key size in bits (2048 or 4096).

    Returns:
        Tuple (private_key_pem, public_key_pem) as bytes.
    """
    key = RSA.generate(size)
    private_key = key.export_key()
    public_key = key.publickey().export_key()
    logger.info(f"Generated {size}-bit RSA key pair.")
    return private_key, public_key

def rsa_encrypt(data: Union[bytes, str], public_key: bytes) -> bytes:
    """
    Encrypt data with RSA public key (OAEP padding).

    Args:
        data: Plaintext.
        public_key: RSA public key in PEM format.

    Returns:
        Ciphertext.
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    key = RSA.import_key(public_key)
    cipher = PKCS1_OAEP.new(key)
    # RSA can encrypt limited data; for larger data use hybrid encryption.
    return cipher.encrypt(data)

def rsa_decrypt(ciphertext: bytes, private_key: bytes) -> bytes:
    """
    Decrypt data with RSA private key.

    Args:
        ciphertext: Encrypted data.
        private_key: RSA private key in PEM format.

    Returns:
        Plaintext.
    """
    key = RSA.import_key(private_key)
    cipher = PKCS1_OAEP.new(key)
    return cipher.decrypt(ciphertext)