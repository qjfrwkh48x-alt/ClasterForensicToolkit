"""
Digital signature for reports using RSA.
"""

from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.exceptions import InvalidSignature

from claster.core.logger import get_logger

logger = get_logger(__name__)

def sign_report(report_file: str, private_key_path: str, output_signature: str = None) -> str:
    """
    Digitally sign a report file using RSA private key.

    Args:
        report_file: Path to report file to sign.
        private_key_path: Path to PEM-encoded private key.
        output_signature: Optional path to save signature. If None, auto-generated.

    Returns:
        Path to signature file.
    """
    report_path = Path(report_file)
    if not report_path.exists():
        raise FileNotFoundError(f"Report file not found: {report_file}")

    with open(private_key_path, 'rb') as key_file:
        private_key = load_pem_private_key(key_file.read(), password=None)

    with open(report_path, 'rb') as f:
        report_data = f.read()

    signature = private_key.sign(
        report_data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )

    if output_signature is None:
        output_signature = str(report_path) + '.sig'
    with open(output_signature, 'wb') as sig_file:
        sig_file.write(signature)

    logger.info(f"Report signed, signature saved to {output_signature}")
    return output_signature

def verify_report_signature(report_file: str, signature_file: str, public_key_path: str) -> bool:
    """
    Verify a report's digital signature.

    Returns:
        True if signature is valid.
    """
    report_path = Path(report_file)
    sig_path = Path(signature_file)
    if not report_path.exists() or not sig_path.exists():
        return False

    with open(public_key_path, 'rb') as key_file:
        public_key = serialization.load_pem_public_key(key_file.read())

    with open(report_path, 'rb') as f:
        report_data = f.read()
    with open(sig_path, 'rb') as f:
        signature = f.read()

    try:
        public_key.verify(
            signature,
            report_data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        logger.info("Report signature verified successfully.")
        return True
    except InvalidSignature:
        logger.error("Report signature verification failed.")
        return False