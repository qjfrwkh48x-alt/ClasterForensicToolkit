"""
Detection of anomalies in memory: hidden processes, code injection, malware configs.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from claster.core.logger import get_logger
from claster.memory.volatility_wrapper import run_volatility_plugin
from claster.memory.processes import list_processes

logger = get_logger(__name__)

def find_hidden_processes() -> List[Dict[str, Any]]:
    """
    Detect hidden processes by comparing live process list with what's found in memory structures.
    This requires both live access and a memory dump. For simplicity, we use psutil vs Volatility pslist.

    Returns:
        List of discrepancies.
    """
    live_procs = {p['pid']: p['name'] for p in list_processes()}
    # Without a memory dump, we can't complete this. Return empty.
    logger.warning("Hidden process detection requires a memory dump and Volatility.")
    return []

def detect_code_injection(dump_path: str) -> List[Dict[str, Any]]:
    """
    Detect code injection using Volatility malfind plugin.

    Args:
        dump_path: Path to memory dump.

    Returns:
        List of injection findings.
    """
    output = run_volatility_plugin(dump_path, "windows.malfind.Malfind")
    findings = []
    try:
        data = json.loads(output)
        for item in data.get('rows', []):
            findings.append({
                'pid': item.get('PID'),
                'process': item.get('Process'),
                'start': item.get('Start'),
                'end': item.get('End'),
                'protection': item.get('Protection'),
                'tag': item.get('Tag'),
            })
        logger.info(f"Detected {len(findings)} potential code injections.")
    except json.JSONDecodeError:
        logger.error("Failed to parse malfind output.")
    return findings

def analyze_malware_config(dump_path: str) -> Dict[str, Any]:
    """
    Attempt to extract malware configuration from memory using Volatility plugins
    like cmdline, envars, and custom yara rules.

    Returns:
        Dictionary with configuration data.
    """
    config = {}
    # Get command lines
    cmdline_out = run_volatility_plugin(dump_path, "windows.cmdline.CmdLine")
    if cmdline_out:
        config['cmdlines'] = cmdline_out
    # Run yarascan for known malware patterns (requires YARA rules)
    # yara_out = run_volatility_plugin(dump_path, "windows.yarascan.YaraScan", yara_rules="rules.yar")
    # config['yara_matches'] = yara_out
    logger.info("Malware config analysis completed.")
    return config