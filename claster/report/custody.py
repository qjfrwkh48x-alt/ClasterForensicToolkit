"""
Chain of custody and hash verification functions for reports.
"""

from datetime import datetime
from typing import Dict, List, Any

from claster.core.hashing import compute_hash, verify_hash
from claster.core.logger import get_logger

logger = get_logger(__name__)

def add_chain_of_custody(report: Dict[str, Any], evidence_item: Dict[str, str]) -> Dict[str, Any]:
    """
    Add a chain of custody entry to the report.

    Args:
        report: The report dictionary (should contain 'custody' list).
        evidence_item: Dict with 'action', 'person', 'notes' keys.

    Returns:
        Updated report dictionary.
    """
    if 'custody' not in report:
        report['custody'] = []
    entry = {
        'timestamp': datetime.now().isoformat(),
        'action': evidence_item.get('action', 'Unknown'),
        'person': evidence_item.get('person', 'Unknown'),
        'notes': evidence_item.get('notes', '')
    }
    report['custody'].append(entry)
    logger.info(f"Added chain of custody entry: {entry['action']} by {entry['person']}")
    return report

def add_hash_verification(report: Dict[str, Any], file_path: str,
                          algorithm: str = 'sha256') -> Dict[str, Any]:
    """
    Compute hash of a file and add verification record to report.

    Args:
        report: Report dictionary.
        file_path: Path to file.
        algorithm: Hash algorithm.

    Returns:
        Updated report.
    """
    file_hash = compute_hash(file_path, algorithm)
    if 'hash_verifications' not in report:
        report['hash_verifications'] = []
    report['hash_verifications'].append({
        'file': file_path,
        'algorithm': algorithm,
        'hash': file_hash,
        'timestamp': datetime.now().isoformat()
    })
    logger.info(f"Added hash verification for {file_path}: {file_hash}")
    return report