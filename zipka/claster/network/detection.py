"""
Network attack detection: port scans, DDoS patterns, suspicious IP alerts.
"""

import time
from collections import defaultdict
from scapy.all import rdpcap, IP, TCP, UDP
from typing import List, Dict, Set

from claster.core.logger import get_logger
from claster.core.events import event_bus, Event

logger = get_logger(__name__)

def detect_port_scan_attack(pcap_file: str, threshold: int = 20) -> List[Dict]:
    """
    Detect port scanning activity by counting unique destination ports per source IP.

    Returns:
        List of source IPs with count of unique ports accessed.
    """
    packets = rdpcap(pcap_file)
    src_port_map = defaultdict(set)

    for pkt in packets:
        if IP in pkt:
            src = pkt[IP].src
            if TCP in pkt:
                src_port_map[src].add(pkt[TCP].dport)
            elif UDP in pkt:
                src_port_map[src].add(pkt[UDP].dport)

    scanners = []
    for src, ports in src_port_map.items():
        if len(ports) >= threshold:
            scanners.append({'src_ip': src, 'unique_ports': len(ports), 'ports': list(ports)[:100]})
    logger.info(f"Detected {len(scanners)} potential port scanners.")
    return scanners

def detect_ddos_pattern(pcap_file: str, packet_rate_threshold: float = 1000.0) -> List[Dict]:
    """
    Detect DDoS patterns by analyzing packet rate per destination.

    Returns:
        List of destinations with high packet rates.
    """
    packets = rdpcap(pcap_file)
    if not packets:
        return []

    dst_counts = defaultdict(int)
    timestamps = []

    for pkt in packets:
        if IP in pkt:
            dst = pkt[IP].dst
            dst_counts[dst] += 1
            timestamps.append(pkt.time)

    duration = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 1
    victims = []
    for dst, count in dst_counts.items():
        rate = count / duration
        if rate >= packet_rate_threshold:
            victims.append({'dst_ip': dst, 'packet_count': count, 'duration': duration, 'rate': rate})
    logger.info(f"Detected {len(victims)} potential DDoS victims.")
    return victims

def live_alert_on_suspicious_ip(interface: str, suspicious_ips: Set[str], duration: int = 60) -> None:
    """
    Monitor live traffic and fire an event when a suspicious IP is contacted.

    Args:
        interface: Network interface.
        suspicious_ips: Set of IPs to watch for.
        duration: Monitoring duration in seconds (0 for indefinite).
    """
    from scapy.all import sniff, IP

    def packet_callback(pkt):
        if IP in pkt:
            src = pkt[IP].src
            dst = pkt[IP].dst
            if src in suspicious_ips or dst in suspicious_ips:
                logger.warning(f"Suspicious IP detected: {src} -> {dst}")
                event_bus.publish(Event(
                    name="network.suspicious_ip",
                    data={'src': src, 'dst': dst, 'matched_ip': src if src in suspicious_ips else dst}
                ))

    logger.info(f"Starting live monitor on {interface} for {duration} seconds...")
    sniff(iface=interface, prn=packet_callback, store=False, timeout=duration if duration > 0 else None)