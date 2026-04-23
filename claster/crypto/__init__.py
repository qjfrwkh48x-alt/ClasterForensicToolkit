"""
Claster Forensic Toolkit - Cryptography Module

Provides cryptographic functions: hashing, encryption/decryption (AES, RSA),
password cracking for archives (ZIP, PDF, RAR, 7z), entropy analysis,
and BitLocker support.
"""

from claster.crypto.hashing import hash_file, hash_text
from claster.crypto.cracking import (
    crack_zip_dict, crack_zip_bruteforce,
    crack_pdf_dict, crack_pdf_bruteforce,
    crack_rar_dict, crack_7z_dict
)
from claster.crypto.aes_rsa import (
    aes_encrypt, aes_decrypt,
    rsa_encrypt, rsa_decrypt,
    generate_rsa_keys
)
from claster.crypto.entropy import calculate_entropy, detect_encryption
from claster.crypto.bitlocker import detect_bitlocker, decrypt_bitlocker

__all__ = [
    'hash_file', 'hash_text',
    'crack_zip_dict', 'crack_zip_bruteforce',
    'crack_pdf_dict', 'crack_pdf_bruteforce',
    'crack_rar_dict', 'crack_7z_dict',
    'aes_encrypt', 'aes_decrypt',
    'rsa_encrypt', 'rsa_decrypt', 'generate_rsa_keys',
    'calculate_entropy', 'detect_encryption',
    'detect_bitlocker', 'decrypt_bitlocker'
]