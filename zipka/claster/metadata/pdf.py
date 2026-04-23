"""
Metadata extraction from PDF files.
"""

from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from claster.core.logger import get_logger

logger = get_logger(__name__)


def get_pdf_metadata(pdf_path: str) -> Dict[str, Any]:
    """
    Extract metadata from a PDF file using PyPDF2 and pdfplumber.

    Returns:
        Dictionary with author, title, creation/modification dates, etc.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    metadata = {}
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(path)
        info = reader.metadata
        if info:
            # Convert PyPDF2 metadata to dict
            for key, value in info.items():
                clean_key = key.lstrip('/')
                # Try to parse dates
                if 'Date' in clean_key and isinstance(value, str):
                    try:
                        # PDF dates are often in format "D:YYYYMMDDHHMMSS"
                        if value.startswith('D:'):
                            value = value[2:]
                        dt = datetime.strptime(value[:14], '%Y%m%d%H%M%S')
                        metadata[clean_key] = dt.isoformat()
                    except:
                        metadata[clean_key] = value
                else:
                    metadata[clean_key] = value
    except ImportError:
        logger.warning("PyPDF2 not installed, trying pdfplumber.")
    except Exception as e:
        logger.debug(f"PyPDF2 read error: {e}")

    # Fallback or supplement with pdfplumber
    if not metadata:
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                meta = pdf.metadata
                if meta:
                    for key, value in meta.items():
                        clean_key = key.lstrip('/')
                        metadata[clean_key] = value
        except ImportError:
            logger.error("Neither PyPDF2 nor pdfplumber is installed.")
        except Exception as e:
            logger.error(f"pdfplumber read error: {e}")

    return metadata