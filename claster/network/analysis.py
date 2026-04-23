"""
PCAP analysis: extraction of files, headers, credentials, and other artifacts.
Uses scapy, dpkt, and pyshark for deep inspection.
"""

import os
import re
import base64
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Any, Union
from collections import defaultdict

from scapy.all import rdpcap, TCP, UDP, IP, IPv6, Raw, DNS, DNSQR, ICMP
from scapy.layers.http import HTTPRequest, HTTPResponse
from scapy.layers.tls.all import TLS, TLSClientHello, TLSServerHello, TLSCertificate
from scapy.layers.smb2 import SMB2_Header
from scapy.layers.netbios import NBTSession
import email
from email import policy
from email.parser import BytesParser

from claster.core.logger import get_logger
from claster.core.utils import ensure_dir, safe_filename
from claster.core.hashing import compute_hash

logger = get_logger(__name__)

# ----------------------------------------------------------------------
# General PCAP analysis
# ----------------------------------------------------------------------
def analyze_pcap(pcap_file: str) -> Dict[str, Any]:
    """
    Provide basic statistics about a PCAP file.

    Args:
        pcap_file: Path to PCAP file.

    Returns:
        Dictionary with counts, protocols, top talkers, etc.
    """
    try:
        packets = rdpcap(pcap_file)
    except Exception as e:
        logger.error(f"Failed to read PCAP {pcap_file}: {e}")
        return {}

    stats = {
        'total_packets': len(packets),
        'protocols': defaultdict(int),
        'src_ips': defaultdict(int),
        'dst_ips': defaultdict(int),
        'tcp_ports': defaultdict(int),
        'udp_ports': defaultdict(int),
    }

    for pkt in packets:
        if IP in pkt:
            stats['src_ips'][pkt[IP].src] += 1
            stats['dst_ips'][pkt[IP].dst] += 1
            stats['protocols']['IP'] += 1
        if IPv6 in pkt:
            stats['src_ips'][pkt[IPv6].src] += 1
            stats['dst_ips'][pkt[IPv6].dst] += 1
            stats['protocols']['IPv6'] += 1
        if TCP in pkt:
            stats['protocols']['TCP'] += 1
            stats['tcp_ports'][pkt[TCP].sport] += 1
            stats['tcp_ports'][pkt[TCP].dport] += 1
        if UDP in pkt:
            stats['protocols']['UDP'] += 1
            stats['udp_ports'][pkt[UDP].sport] += 1
            stats['udp_ports'][pkt[UDP].dport] += 1
        if DNS in pkt:
            stats['protocols']['DNS'] += 1
        if ICMP in pkt:
            stats['protocols']['ICMP'] += 1

    # Convert defaultdicts to regular dicts for JSON serialization
    for key in ['protocols', 'src_ips', 'dst_ips', 'tcp_ports', 'udp_ports']:
        stats[key] = dict(stats[key])

    logger.info(f"Analyzed PCAP {pcap_file}: {stats['total_packets']} packets")
    return stats

# ----------------------------------------------------------------------
# HTTP extraction
# ----------------------------------------------------------------------
def extract_http_files(pcap_file: str, output_dir: str) -> List[str]:
    """
    Extract files transferred over HTTP (based on Content-Disposition or raw body).

    Args:
        pcap_file: Path to PCAP.
        output_dir: Directory to save extracted files.

    Returns:
        List of saved file paths.
    """
    ensure_dir(output_dir)
    saved_files = []
    packets = rdpcap(pcap_file)

    # Reassemble TCP streams for HTTP
    streams = {}  # (src, dst, sport, dport) -> bytes

    for pkt in packets:
        if TCP in pkt and Raw in pkt:
            key = (pkt[IP].src, pkt[IP].dst, pkt[TCP].sport, pkt[TCP].dport)
            streams.setdefault(key, b'')
            streams[key] += bytes(pkt[Raw])

    for key, data in streams.items():
        # Look for HTTP response
        if b'HTTP/' in data and b'Content-Type:' in data:
            # Find end of headers
            header_end = data.find(b'\r\n\r\n')
            if header_end == -1:
                continue
            headers = data[:header_end].decode('utf-8', errors='ignore')
            body = data[header_end+4:]

            # Check for Content-Disposition (attachment)
            cd_match = re.search(r'Content-Disposition: attachment; filename="?([^"\r\n]+)"?', headers, re.I)
            if cd_match:
                filename = cd_match.group(1)
            else:
                # Try to infer extension from Content-Type
                ct_match = re.search(r'Content-Type: ([^;\r\n]+)', headers, re.I)
                if ct_match:
                    mime_type = ct_match.group(1).strip()
                    ext = {
                        'application/pdf': '.pdf',
                        'application/zip': '.zip',
                        'application/x-msdownload': '.exe',
                        'image/jpeg': '.jpg',
                        'image/png': '.png',
                        'text/html': '.html',
                    }.get(mime_type, '.bin')
                else:
                    ext = '.bin'
                filename = f"http_file_{hashlib.md5(body[:1024]).hexdigest()[:8]}{ext}"

            filename = safe_filename(filename)
            out_path = Path(output_dir) / filename
            with open(out_path, 'wb') as f:
                f.write(body)
            saved_files.append(str(out_path))
            logger.debug(f"Extracted HTTP file: {out_path}")

    logger.info(f"Extracted {len(saved_files)} files from HTTP.")
    return saved_files

def extract_http_headers(pcap_file: str) -> List[Dict[str, Any]]:
    """Extract HTTP request/response headers."""
    packets = rdpcap(pcap_file)
    headers_list = []

    for pkt in packets:
        if TCP in pkt and Raw in pkt:
            payload = bytes(pkt[Raw])
            try:
                if payload.startswith(b'GET ') or payload.startswith(b'POST ') or payload.startswith(b'HTTP/'):
                    # Attempt to parse
                    header_end = payload.find(b'\r\n\r\n')
                    if header_end != -1:
                        header_part = payload[:header_end].decode('utf-8', errors='ignore')
                        lines = header_part.split('\r\n')
                        first_line = lines[0]
                        headers_list.append({
                            'src': pkt[IP].src,
                            'dst': pkt[IP].dst,
                            'sport': pkt[TCP].sport,
                            'dport': pkt[TCP].dport,
                            'first_line': first_line,
                            'raw_headers': header_part[:500],  # truncated
                        })
            except Exception:
                pass
    logger.info(f"Extracted {len(headers_list)} HTTP headers.")
    return headers_list

def extract_http_passwords(pcap_file: str) -> List[Dict[str, str]]:
    """
    Search HTTP POST bodies for password fields.
    """
    packets = rdpcap(pcap_file)
    creds = []
    for pkt in packets:
        if TCP in pkt and Raw in pkt:
            payload = bytes(pkt[Raw])
            if b'POST ' in payload:
                header_end = payload.find(b'\r\n\r\n')
                if header_end != -1:
                    body = payload[header_end+4:].decode('utf-8', errors='ignore')
                    # Simple regex for common password parameter names
                    pw_match = re.search(r'(?:pass|pwd|password)=([^&\s]+)', body, re.I)
                    if pw_match:
                        creds.append({
                            'src': pkt[IP].src,
                            'dst': pkt[IP].dst,
                            'password_field': pw_match.group(1),
                        })
    logger.info(f"Found {len(creds)} possible passwords in HTTP traffic.")
    return creds

# ----------------------------------------------------------------------
# DNS extraction
# ----------------------------------------------------------------------
def extract_dns_queries(pcap_file: str) -> List[Dict[str, Any]]:
    """Extract DNS queries and responses."""
    packets = rdpcap(pcap_file)
    queries = []
    for pkt in packets:
        if DNS in pkt and pkt[DNS].qr == 0:  # query
            qname = pkt[DNS].qd.qname.decode('utf-8', errors='ignore') if pkt[DNS].qd else ''
            queries.append({
                'src': pkt[IP].src,
                'dst': pkt[IP].dst,
                'qname': qname.rstrip('.'),
                'qtype': pkt[DNS].qd.qtype if pkt[DNS].qd else None,
                'timestamp': float(pkt.time),
            })
    logger.info(f"Extracted {len(queries)} DNS queries.")
    return queries

def extract_dns_tunneling(pcap_file: str) -> List[Dict[str, Any]]:
    """
    Detect potential DNS tunneling by looking for long subdomains, high entropy, or large TXT responses.
    Returns list of suspicious DNS exchanges.
    """
    packets = rdpcap(pcap_file)
    suspicious = []
    for pkt in packets:
        if DNS in pkt:
            if pkt[DNS].qr == 0 and pkt[DNS].qd:
                qname = pkt[DNS].qd.qname.decode('utf-8', errors='ignore')
                # Long subdomain (possible base64 data)
                if len(qname) > 50:
                    suspicious.append({'type': 'long_query', 'qname': qname, 'src': pkt[IP].src})
            elif pkt[DNS].qr == 1 and pkt[DNS].an:
                # Check for large TXT responses
                for ans in pkt[DNS].an:
                    if ans.type == 16:  # TXT
                        txt_data = b''.join(ans.rdata)
                        if len(txt_data) > 200:
                            suspicious.append({'type': 'large_txt', 'size': len(txt_data), 'dst': pkt[IP].dst})
    logger.info(f"Detected {len(suspicious)} potential DNS tunneling indicators.")
    return suspicious

# ----------------------------------------------------------------------
# SSL/TLS
# ----------------------------------------------------------------------
def extract_ssl_certificates(pcap_file: str) -> List[Dict[str, Any]]:
    """Extract X.509 certificates from TLS handshakes."""
    packets = rdpcap(pcap_file)
    certs = []
    for pkt in packets:
        if TLS in pkt:
            # Look for Certificate handshake message
            if hasattr(pkt[TLS], 'msg'):
                for msg in pkt[TLS].msg:
                    if hasattr(msg, 'certificates'):
                        for cert_bytes in msg.certificates:
                            # Parse certificate using cryptography
                            try:
                                from cryptography import x509
                                from cryptography.hazmat.backends import default_backend
                                cert = x509.load_der_x509_certificate(cert_bytes, default_backend())
                                certs.append({
                                    'subject': cert.subject.rfc4514_string(),
                                    'issuer': cert.issuer.rfc4514_string(),
                                    'serial_number': str(cert.serial_number),
                                    'not_before': cert.not_valid_before.isoformat(),
                                    'not_after': cert.not_valid_after.isoformat(),
                                    'src': pkt[IP].src,
                                    'dst': pkt[IP].dst,
                                })
                            except ImportError:
                                logger.warning("cryptography library not installed; cannot parse certs.")
                                certs.append({'raw': cert_bytes.hex()[:200]})
    logger.info(f"Extracted {len(certs)} SSL certificates.")
    return certs

def analyze_tls_handshake(pcap_file: str) -> List[Dict[str, Any]]:
    """Analyze TLS handshake parameters (versions, cipher suites, SNI)."""
    packets = rdpcap(pcap_file)
    handshakes = []
    for pkt in packets:
        if TLS in pkt and TLSClientHello in pkt:
            ch = pkt[TLSClientHello]
            sni = None
            if hasattr(ch, 'ext'):
                for ext in ch.ext:
                    if ext.type == 0:  # server_name
                        sni = ext.servernames[0].servername.decode('utf-8', errors='ignore')
            handshakes.append({
                'src': pkt[IP].src,
                'dst': pkt[IP].dst,
                'version': ch.version,
                'cipher_suites': ch.ciphers,
                'sni': sni,
                'timestamp': float(pkt.time),
            })
    logger.info(f"Analyzed {len(handshakes)} TLS handshakes.")
    return handshakes

# ----------------------------------------------------------------------
# SMB / FTP / SMTP / ICMP extraction
# ----------------------------------------------------------------------
def extract_smb_files(pcap_file: str, output_dir: str) -> List[str]:
    """
    Extract files transferred over SMB.
    Requires scapy SMB2 layer support; for simplicity, we'll use a placeholder.
    In production, use pyshark or tshark.
    """
    logger.warning("SMB file extraction requires deeper protocol parsing; not fully implemented.")
    return []

def extract_ftp_files(pcap_file: str, output_dir: str) -> List[str]:
    """Extract files from FTP-DATA sessions."""
    ensure_dir(output_dir)
    packets = rdpcap(pcap_file)
    ftp_data_streams = defaultdict(bytearray)
    saved = []

    for pkt in packets:
        if TCP in pkt and Raw in pkt:
            sport = pkt[TCP].sport
            dport = pkt[TCP].dport
            if sport == 20 or dport == 20:  # FTP data
                key = (pkt[IP].src, pkt[IP].dst, sport, dport)
                ftp_data_streams[key] += bytes(pkt[Raw])

    for key, data in ftp_data_streams.items():
        if len(data) > 0:
            filename = f"ftp_data_{hashlib.md5(data[:1024]).hexdigest()[:8]}.bin"
            out_path = Path(output_dir) / filename
            with open(out_path, 'wb') as f:
                f.write(data)
            saved.append(str(out_path))
    logger.info(f"Extracted {len(saved)} FTP data files.")
    return saved

def extract_smtp_emails(pcap_file: str, output_dir: str) -> List[str]:
    """Extract emails from SMTP traffic."""
    ensure_dir(output_dir)
    packets = rdpcap(pcap_file)
    streams = defaultdict(bytearray)
    saved = []

    for pkt in packets:
        if TCP in pkt and Raw in pkt:
            dport = pkt[TCP].dport
            if dport == 25:  # SMTP
                key = (pkt[IP].src, pkt[IP].dst, pkt[TCP].sport, pkt[TCP].dport)
                streams[key] += bytes(pkt[Raw])

    for key, data in streams.items():
        # Look for DATA command
        data_str = data.decode('utf-8', errors='ignore')
        if 'From:' in data_str and 'To:' in data_str:
            try:
                msg = BytesParser(policy=policy.default).parsebytes(data)
                subject = msg.get('Subject', 'no_subject')
                filename = safe_filename(f"email_{subject}_{hashlib.md5(data).hexdigest()[:8]}.eml")
                out_path = Path(output_dir) / filename
                with open(out_path, 'wb') as f:
                    f.write(data)
                saved.append(str(out_path))
            except Exception:
                pass
    logger.info(f"Extracted {len(saved)} SMTP emails.")
    return saved

def extract_icmp_data(pcap_file: str) -> List[bytes]:
    """Extract raw payload data from ICMP packets (potential exfiltration)."""
    packets = rdpcap(pcap_file)
    data_chunks = []
    for pkt in packets:
        if ICMP in pkt and Raw in pkt:
            data_chunks.append(bytes(pkt[Raw]))
    logger.info(f"Extracted {len(data_chunks)} ICMP payloads.")
    return data_chunks