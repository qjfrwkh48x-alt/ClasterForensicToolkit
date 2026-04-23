"""
Claster Forensic Toolkit - Network Forensics Module

Provides packet capture, PCAP analysis, file extraction, stream reconstruction,
port scanning, ARP scanning, network mapping, GeoIP, WHOIS, and attack detection.
"""

from claster.network.capture import (
    sniff_packets,
    sniff_duration,
)
from claster.network.analysis import (
    analyze_pcap,
    extract_http_files,
    extract_http_headers,
    extract_http_passwords,
    extract_dns_queries,
    extract_dns_tunneling,
    extract_ssl_certificates,
    analyze_tls_handshake,
    extract_smb_files,
    extract_ftp_files,
    extract_smtp_emails,
    extract_icmp_data,
)
from claster.network.reconstruction import (
    reconstruct_tcp_stream,
    reconstruct_all_tcp_streams,
)
from claster.network.scanning import (
    port_scan,
    port_scan_udp,
    arp_scan,
    network_map,
)
from claster.network.geoip_whois import (
    geoip_lookup,
    whois_lookup,
)
from claster.network.detection import (
    detect_port_scan_attack,
    detect_ddos_pattern,
    live_alert_on_suspicious_ip,
)

__all__ = [
    # Capture
    'sniff_packets',
    'sniff_duration',
    # Analysis
    'analyze_pcap',
    'extract_http_files',
    'extract_http_headers',
    'extract_http_passwords',
    'extract_dns_queries',
    'extract_dns_tunneling',
    'extract_ssl_certificates',
    'analyze_tls_handshake',
    'extract_smb_files',
    'extract_ftp_files',
    'extract_smtp_emails',
    'extract_icmp_data',
    # Reconstruction
    'reconstruct_tcp_stream',
    'reconstruct_all_tcp_streams',
    # Scanning
    'port_scan',
    'port_scan_udp',
    'arp_scan',
    'network_map',
    # GeoIP & WHOIS
    'geoip_lookup',
    'whois_lookup',
    # Detection
    'detect_port_scan_attack',
    'detect_ddos_pattern',
    'live_alert_on_suspicious_ip',
]