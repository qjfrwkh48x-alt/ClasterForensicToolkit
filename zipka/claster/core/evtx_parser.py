"""
Windows Event Log (.evtx) parsing and export functions.
Uses python-evtx library (install via pip: python-evtx).
"""

import csv
import json
from pathlib import Path
from typing import Dict, Generator, List, Optional, Union
from datetime import datetime
from claster.core.logger import get_logger
from claster.core.exceptions import EventLogError

logger = get_logger(__name__)

try:
    from evtx.Evtx import Evtx
    from evtx.Views import evtx_file_xml_view
    HAS_EVTX = True
except ImportError:
    HAS_EVTX = False
    logger.warning("python-evtx library not installed. EVTX parsing disabled.")


def _parse_evtx_records(evtx_path: Union[str, Path]) -> Generator[Dict, None, None]:
    """
    Internal generator that yields each event record as a dictionary.
    """
    if not HAS_EVTX:
        raise EventLogError("python-evtx library is required for EVTX parsing.")

    evtx_path = Path(evtx_path)
    if not evtx_path.exists():
        raise EventLogError(f"EVTX file not found: {evtx_path}")

    try:
        with Evtx(str(evtx_path)) as log:
            for record in log.records():
                try:
                    # Use xml() method for full event data
                    xml_str = record.xml()
                    # Simple parsing: we could use xmltodict, but for performance we'll extract basic fields
                    # Here we just include raw XML and basic attributes
                    event_data = {
                        'event_record_id': record.record_num(),
                        'timestamp': record.timestamp().isoformat() if record.timestamp() else None,
                        'event_id': None,
                        'level': None,
                        'provider': None,
                        'computer': None,
                        'raw_xml': xml_str
                    }
                    # Extract some common fields from XML using simple string search (to avoid heavy XML parsing)
                    import re
                    eid_match = re.search(r'<EventID[^>]*>(\d+)</EventID>', xml_str)
                    if eid_match:
                        event_data['event_id'] = int(eid_match.group(1))
                    level_match = re.search(r'<Level>(\d+)</Level>', xml_str)
                    if level_match:
                        event_data['level'] = int(level_match.group(1))
                    prov_match = re.search(r'<Provider[^>]*Name="([^"]*)"', xml_str)
                    if prov_match:
                        event_data['provider'] = prov_match.group(1)
                    comp_match = re.search(r'<Computer>([^<]+)</Computer>', xml_str)
                    if comp_match:
                        event_data['computer'] = comp_match.group(1)

                    yield event_data
                except Exception as e:
                    logger.warning(f"Failed to parse record {record.record_num()}: {e}")
                    continue
    except Exception as e:
        logger.error(f"Failed to open EVTX file {evtx_path}: {e}")
        raise EventLogError(f"EVTX parsing failed: {e}")


def parse_evtx(evtx_path: Union[str, Path]) -> List[Dict]:
    """
    Parse an EVTX file and return a list of event dictionaries.

    Args:
        evtx_path: Path to .evtx file.

    Returns:
        List of parsed events.
    """
    events = list(_parse_evtx_records(evtx_path))
    logger.info(f"Parsed {len(events)} events from {evtx_path}")
    return events


def export_evtx_csv(evtx_path: Union[str, Path], csv_path: Union[str, Path]) -> None:
    """
    Export EVTX events to a CSV file.

    Args:
        evtx_path: Source EVTX file.
        csv_path: Destination CSV file.

    Raises:
        EventLogError: If export fails.
    """
    evtx_path = Path(evtx_path)
    csv_path = Path(csv_path)

    events = parse_evtx(evtx_path)
    if not events:
        logger.warning(f"No events to export from {evtx_path}")
        return

    # Determine fields from first event
    fieldnames = ['event_record_id', 'timestamp', 'event_id', 'level', 'provider', 'computer', 'raw_xml']

    try:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(events)
        logger.info(f"Exported {len(events)} events to {csv_path}")
    except Exception as e:
        logger.error(f"Failed to export to CSV: {e}")
        raise EventLogError(f"CSV export failed: {e}")