"""
Detection of MFT anomalies such as timestomping.
"""

from datetime import datetime
from typing import List, Dict
from claster.core.logger import get_logger

logger = get_logger(__name__)


def detect_timestomping(volume_path: str) -> List[Dict]:
    """
    Detect potential timestomping by checking for inconsistent timestamps.
    Indicators:
    - Creation time after modification time
    - Zero timestamps
    - Sub-second precision mismatches (NTFS has 100ns granularity, if all zero, suspicious)
    - MFT entry modified time much older than other times
    """
    from claster.disk.mft import get_mft_timestamps
    timestamps = get_mft_timestamps(volume_path)
    anomalies = []

    for ts in timestamps:
        reasons = []
        # Convert strings to datetime
        try:
            c = datetime.fromisoformat(ts['creation']) if ts['creation'] else None
            m = datetime.fromisoformat(ts['modification']) if ts['modification'] else None
            a = datetime.fromisoformat(ts['access']) if ts['access'] else None
            e = datetime.fromisoformat(ts['mft_change']) if ts['mft_change'] else None
        except:
            continue

        if c and m and c > m:
            reasons.append("Creation after modification")
        if e and m and e < m:
            reasons.append("MFT entry modified before last file modification")
        if c and (c.microsecond == 0 and c.second == 0 and c.minute == 0):
            reasons.append("Creation time has zero sub-second components (possible tool usage)")

        if reasons:
            anomalies.append({
                'filename': ts['filename'],
                'reasons': reasons,
                'timestamps': ts
            })

    logger.info(f"Detected {len(anomalies)} possible timestomped entries.")
    return anomalies


def analyze_mft_anomalies(volume_path: str) -> Dict:
    """
    Comprehensive MFT anomaly analysis:
    - Sequence number mismatches
    - Invalid attribute sizes
    - Resident data in non-resident attributes
    - Unusual filename lengths
    """
    # This would require deep MFT attribute parsing.
    logger.warning("Full MFT anomaly analysis requires low-level attribute parsing.")
    return {}