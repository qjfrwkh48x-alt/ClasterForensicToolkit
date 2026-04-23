"""
Network utility functions.
"""

import socket
import psutil
from typing import List, Dict

def get_interfaces() -> List[Dict[str, str]]:
    """Return list of network interfaces with IP addresses."""
    interfaces = []
    for name, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET:
                interfaces.append({'name': name, 'ip': addr.address, 'netmask': addr.netmask})
    return interfaces

def is_private_ip(ip: str) -> bool:
    """Check if an IP address is private."""
    import ipaddress
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False