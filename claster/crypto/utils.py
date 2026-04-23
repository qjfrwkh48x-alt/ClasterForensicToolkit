"""
Cryptography utilities.
"""

def is_valid_recovery_key(key: str) -> bool:
    """Validate BitLocker recovery key format."""
    clean = key.replace('-', '').strip()
    return len(clean) == 48 and clean.isdigit()