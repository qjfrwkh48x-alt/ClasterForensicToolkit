"""
Network scanning utilities: port scanning, ARP scanning, network mapping.
"""

import ipaddress
import socket
from typing import List, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from scapy.all import IP, TCP, UDP, ICMP, sr1, sr, ARP, conf
from scapy.layers.l2 import Ether
from claster.core.logger import get_logger

logger = get_logger(__name__)

def port_scan(target_ip: str, ports: List[int], timeout: float = 2.0,
              max_threads: int = 50) -> Dict[int, str]:
    """
    Perform TCP SYN scan on specified ports.

    Returns:
        Dictionary mapping port number to 'open', 'closed', or 'filtered'.
    """
    results = {}

    def scan_port(port):
        pkt = IP(dst=target_ip) / TCP(dport=port, flags='S')
        resp = sr1(pkt, timeout=timeout, verbose=0)
        if resp is None:
            return port, 'filtered'
        elif resp.haslayer(TCP):
            flags = resp.getlayer(TCP).flags
            if flags & 0x12:  # SYN-ACK
                # Send RST to close
                sr1(IP(dst=target_ip) / TCP(dport=port, flags='R'), timeout=1, verbose=0)
                return port, 'open'
            elif flags & 0x14:  # RST-ACK
                return port, 'closed'
        return port, 'unknown'

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {executor.submit(scan_port, port): port for port in ports}
        for future in as_completed(futures):
            port, status = future.result()
            results[port] = status

    open_ports = [p for p, s in results.items() if s == 'open']
    logger.info(f"TCP scan on {target_ip}: {len(open_ports)} open ports")
    return results

def port_scan_udp(target_ip: str, ports: List[int], timeout: float = 2.0) -> Dict[int, str]:
    """
    Perform UDP scan (less reliable). Open ports usually send no response.
    """
    results = {}
    for port in ports:
        pkt = IP(dst=target_ip) / UDP(dport=port)
        resp = sr1(pkt, timeout=timeout, verbose=0)
        if resp is None:
            results[port] = 'open|filtered'
        elif resp.haslayer(ICMP) and resp.getlayer(ICMP).type == 3 and resp.getlayer(ICMP).code == 3:
            results[port] = 'closed'
        elif resp.haslayer(UDP):
            results[port] = 'open'
        else:
            results[port] = 'unknown'
    logger.info(f"UDP scan on {target_ip} completed.")
    return results

def arp_scan(network: str, timeout: float = 2.0) -> List[Dict[str, str]]:
    """
    Perform ARP scan to discover live hosts on a local network.

    Args:
        network: CIDR notation, e.g., '192.168.1.0/24'.

    Returns:
        List of dicts with 'ip' and 'mac'.
    """
    ans, _ = sr(Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=network),
                timeout=timeout, verbose=0)
    hosts = []
    for sent, received in ans:
        hosts.append({'ip': received.psrc, 'mac': received.hwsrc})
    logger.info(f"ARP scan found {len(hosts)} hosts on {network}.")
    return hosts

def network_map(interface: str) -> Dict[str, Any]:
    """
    Build a basic network map: local IP, gateway, live hosts via ARP.

    Args:
        interface: Network interface name.

    Returns:
        Dictionary with network info.
    """
    # Get interface IP and netmask
    ip = conf.ifaces[interface].ip
    netmask = conf.ifaces[interface].netmask
    network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
    gateway = conf.route.route("0.0.0.0")[2]  # default gateway

    hosts = arp_scan(str(network))
    return {
        'interface': interface,
        'ip': ip,
        'netmask': netmask,
        'network': str(network),
        'gateway': gateway,
        'live_hosts': hosts,
    }