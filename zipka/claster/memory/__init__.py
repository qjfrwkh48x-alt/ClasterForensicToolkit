"""
Claster Forensic Toolkit - Memory Forensics Module

Provides functions for:
- Live process enumeration and dumping
- Full RAM acquisition (requires driver/Volatility)
- String and regex search in memory dumps
- Detection of hidden processes, code injection, and malware artifacts
- Extraction of network connections, registry keys, passwords, screenshots
"""

from claster.memory.processes import (
    dump_process,
    dump_all_processes,
    list_processes,
    list_processes_full,
    get_process_modules,
    get_process_environment,
    get_process_command_line,
    get_process_memory_map,
)
from claster.memory.analysis import (
    dump_system_ram,
    search_strings,
    search_regex,
    extract_network_connections,
    extract_registry_keys,
    extract_passwords,
    extract_screenshots,
)
from claster.memory.detection import (
    find_hidden_processes,
    detect_code_injection,
    analyze_malware_config,
)

__all__ = [
    # Processes
    'dump_process',
    'dump_all_processes',
    'list_processes',
    'list_processes_full',
    'get_process_modules',
    'get_process_environment',
    'get_process_command_line',
    'get_process_memory_map',
    # Analysis
    'dump_system_ram',
    'search_strings',
    'search_regex',
    'extract_network_connections',
    'extract_registry_keys',
    'extract_passwords',
    'extract_screenshots',
    # Detection
    'find_hidden_processes',
    'detect_code_injection',
    'analyze_malware_config',
]