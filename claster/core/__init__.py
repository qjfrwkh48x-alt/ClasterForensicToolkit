"""
Claster Forensic Toolkit - Core Module

This module provides fundamental functionality used across all other modules:
- Logging configuration
- Hashing and integrity verification
- System utilities (admin rights, timestamps)
- File system helpers (safe copy, secure delete)
- Windows Event Log parsing
- Configuration management
- Database abstraction for case management
- Plugin system for extensibility
- Custom exceptions
- Event bus for inter-module communication
"""

from claster.core.logger import setup_logger, get_logger
from claster.core.exceptions import ClasterError, ClasterCoreError
from claster.core.config import Config, get_config
from claster.core.database import Database, get_db
from claster.core.events import EventBus, Event, event_bus
from claster.core.utils import ensure_dir, timestamp, is_admin, request_elevation
from claster.core.plugins import PluginManager, PluginBase, plugin_manager
from claster.core.hashing import compute_hash, compute_hashes_multiple, compute_hash_large, verify_hash
from claster.core.system import get_system_info, get_timezone, is_admin, request_elevation
from claster.core.fs_ops import safe_copy, secure_delete, wipe_free_space, get_disk_geometry, get_volume_info,compare_files
from claster.core.evtx_parser import parse_evtx, export_evtx_csv
from claster.core.utils import ensure_dir, timestamp, get_temp_path, safe_filename, human_size

__version__ = "0.1.0"
__all__ = [
    "setup_logger",
    "get_logger",
    "ClasterError",
    "ClasterCoreError",
    "Config",
    "get_config",
    "Database",
    "get_db",
    "EventBus",
    "Event",
    "event_bus",
    "ensure_dir",
    "timestamp",
    "is_admin",
    "request_elevation",
    "PluginManager",
    "PluginBase",
    "plugin_manager",
    "compute_hash", 
    "compute_hashes_multiple", 
    "compute_hash_large", 
    "verify_hash",
    "get_system_info", 
    "get_timezone",
    "safe_copy", 
    "secure_delete", 
    "wipe_free_space", 
    "get_disk_geometry", 
    "get_volume_info",
    "compare_files",
    "parse_evtx", 
    "export_evtx_csv",
    "get_temp_path", 
    "safe_filename", 
    "human_size",
]