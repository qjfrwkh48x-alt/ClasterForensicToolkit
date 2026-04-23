"""
Claster Forensic Toolkit - Windows Registry Forensics Module

Provides functions for parsing offline registry hives and live registry access.
Includes analysis of autorun locations, USB history, user activity, network config,
installed software, SAM hashes, LSA secrets, and more.
"""

from claster.registry.registry import (
    parse_hive,
    get_autorun,
    get_autorun_all,
    get_usb_history,
    get_usb_storage_details,
    get_recent_docs,
    get_user_assist,
    get_mru_list,
    get_typed_urls,
    get_network_interfaces,
    get_network_profiles,
    get_installed_software,
    get_uninstall_history,
    get_sam_hashes,
    get_lsa_secrets,
    get_boot_execute,
    get_scheduled_tasks,
    get_services,
    get_driver_list,
    get_windows_activation_key,
)

__all__ = [
    'parse_hive',
    'get_autorun',
    'get_autorun_all',
    'get_usb_history',
    'get_usb_storage_details',
    'get_recent_docs',
    'get_user_assist',
    'get_mru_list',
    'get_typed_urls',
    'get_network_interfaces',
    'get_network_profiles',
    'get_installed_software',
    'get_uninstall_history',
    'get_sam_hashes',
    'get_lsa_secrets',
    'get_boot_execute',
    'get_scheduled_tasks',
    'get_services',
    'get_driver_list',
    'get_windows_activation_key',
]