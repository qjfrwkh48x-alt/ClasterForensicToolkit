"""
Memory dump analysis: strings extraction, regex search, artifact recovery.
Uses Volatility 3 framework under the hood.
"""

import os
import re
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Any

from claster.core.logger import get_logger
from claster.core.utils import ensure_dir
from claster.memory.volatility_wrapper import VolatilityWrapper, run_volatility_plugin

logger = get_logger(__name__)

# ----------------------------------------------------------------------
# RAM acquisition
# ----------------------------------------------------------------------
def dump_system_ram(output_path: str) -> bool:
    """
    Create a full memory dump of the system.

    On Windows, requires a driver like winpmem or using livekd.
    On Linux, use LiME or /dev/fmem.

    Args:
        output_path: Path for the memory dump file.

    Returns:
        True if successful.
    """
    # We'll use Volatility's ability to acquire memory via winpmem.
    # For simplicity, we invoke winpmem if available.
    if os.name == 'nt':
        winpmem_path = "winpmem_mini.exe"  # Should be bundled or in PATH
        try:
            subprocess.run([winpmem_path, output_path], check=True)
            logger.info(f"System RAM dumped to {output_path}")
            return True
        except Exception as e:
            logger.error(f"winpmem failed: {e}")
            return False
    else:
        # Linux: suggest using LiME
        logger.error("Full RAM dump on Linux requires LiME kernel module.")
        return False

# ----------------------------------------------------------------------
# String extraction
# ----------------------------------------------------------------------
def search_strings(dump_path: str, min_len: int = 4) -> List[str]:
    """
    Extract ASCII/UTF-8 strings from a memory dump file.

    Args:
        dump_path: Path to the dump file.
        min_len: Minimum string length.

    Returns:
        List of extracted strings.
    """
    strings = []
    pattern = re.compile(rb'[ -~]{%d,}' % min_len)
    try:
        with open(dump_path, 'rb') as f:
            for match in pattern.finditer(f.read()):
                try:
                    s = match.group().decode('ascii')
                    strings.append(s)
                except UnicodeDecodeError:
                    pass
        logger.info(f"Extracted {len(strings)} strings from {dump_path}")
    except Exception as e:
        logger.error(f"String extraction failed: {e}")
    return strings

def search_regex(dump_path: str, pattern: str) -> List[str]:
    """
    Search memory dump for matches of a regular expression.

    Args:
        dump_path: Path to dump file.
        pattern: Regex pattern (string).

    Returns:
        List of matched strings.
    """
    regex = re.compile(pattern.encode() if isinstance(pattern, str) else pattern)
    matches = []
    try:
        with open(dump_path, 'rb') as f:
            data = f.read()
            for match in regex.finditer(data):
                try:
                    matches.append(match.group().decode('utf-8', errors='ignore'))
                except:
                    matches.append(str(match.group()))
        logger.info(f"Found {len(matches)} regex matches in {dump_path}")
    except Exception as e:
        logger.error(f"Regex search failed: {e}")
    return matches

# ----------------------------------------------------------------------
# Artifact extraction using Volatility
# ----------------------------------------------------------------------
def extract_network_connections(dump_path: str) -> List[Dict[str, Any]]:
    """
    Extract active network connections from memory dump using Volatility netscan plugin.

    Args:
        dump_path: Path to memory dump.

    Returns:
        List of connection records.
    """
    output = run_volatility_plugin(dump_path, "windows.netscan.NetScan")
    # Parse JSON output
    connections = []
    try:
        data = json.loads(output)
        for item in data.get('rows', []):
            connections.append({
                'protocol': item.get('Protocol'),
                'local_addr': item.get('LocalAddr'),
                'local_port': item.get('LocalPort'),
                'foreign_addr': item.get('ForeignAddr'),
                'foreign_port': item.get('ForeignPort'),
                'state': item.get('State'),
                'pid': item.get('PID'),
                'owner': item.get('Owner'),
                'created': item.get('Created'),
            })
        logger.info(f"Extracted {len(connections)} network connections.")
    except json.JSONDecodeError:
        logger.error("Failed to parse Volatility netscan output.")
    return connections

def extract_registry_keys(dump_path: str) -> List[Dict[str, Any]]:
    """
    Extract registry keys and values from memory using Volatility hivelist/printkey.

    Args:
        dump_path: Path to memory dump.

    Returns:
        List of registry artifacts.
    """
    # First get hive offsets
    hives_output = run_volatility_plugin(dump_path, "windows.registry.hivelist.HiveList")
    # Then for each hive, we could enumerate keys. This is complex to automate.
    # We'll return raw output for now.
    logger.warning("Full registry extraction requires parsing multiple hives.")
    return [{'hives': hives_output}]

def extract_passwords(dump_path: str) -> List[Dict[str, Any]]:
    """
    Search memory for password patterns and use Volatility plugins (hashdump, lsadump).

    Args:
        dump_path: Path to memory dump.

    Returns:
        List of potential credentials.
    """
    creds = []
    # Run hashdump for NTLM hashes
    hashdump_out = run_volatility_plugin(dump_path, "windows.hashdump.Hashdump")
    if hashdump_out:
        creds.append({'type': 'ntlm_hashes', 'data': hashdump_out})
    # Run lsadump for LSA secrets
    lsadump_out = run_volatility_plugin(dump_path, "windows.lsadump.Lsadump")
    if lsadump_out:
        creds.append({'type': 'lsa_secrets', 'data': lsadump_out})
    return creds

def extract_screenshots(dump_path: str, output_dir: str) -> List[str]:
    """
    Extract screenshots from memory dump using Volatility screenshot plugin.

    Args:
        dump_path: Path to memory dump.
        output_dir: Directory to save extracted screenshots.

    Returns:
        List of paths to saved screenshot files.
    """
    ensure_dir(output_dir)
    # Volatility screenshot plugin saves files in current dir; we need to manage that.
    # We'll use a wrapper that runs in output_dir.
    saved_files = []
    try:
        # This is pseudocode; actual implementation requires handling Volatility output.
        run_volatility_plugin(dump_path, "windows.screenshot.Screenshot", output_dir=output_dir)
        # Collect any PNG files created
        for f in Path(output_dir).glob("*.png"):
            saved_files.append(str(f))
        logger.info(f"Extracted {len(saved_files)} screenshots.")
    except Exception as e:
        logger.error(f"Screenshot extraction failed: {e}")
    return saved_files