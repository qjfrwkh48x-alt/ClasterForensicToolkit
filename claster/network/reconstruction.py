"""
TCP stream reconstruction.
"""

from collections import defaultdict
from scapy.all import rdpcap, IP, TCP, Raw
from typing import Dict, Tuple, List, Optional
from pathlib import Path

from claster.core.logger import get_logger
from claster.core.utils import ensure_dir

logger = get_logger(__name__)

def reconstruct_tcp_stream(pcap_file: str, src_ip: str, dst_ip: str,
                           src_port: int, dst_port: int) -> Optional[bytes]:
    """
    Reconstruct a specific TCP stream.

    Returns:
        Concatenated bytes of the stream payload.
    """
    packets = rdpcap(pcap_file)
    stream_data = bytearray()
    # We need to follow sequence numbers properly, but for simple cases, just collect payload.
    for pkt in packets:
        if IP in pkt and TCP in pkt and Raw in pkt:
            if (pkt[IP].src == src_ip and pkt[IP].dst == dst_ip and
                pkt[TCP].sport == src_port and pkt[TCP].dport == dst_port):
                stream_data.extend(bytes(pkt[Raw]))
            elif (pkt[IP].src == dst_ip and pkt[IP].dst == src_ip and
                  pkt[TCP].sport == dst_port and pkt[TCP].dport == src_port):
                stream_data.extend(bytes(pkt[Raw]))
    return bytes(stream_data) if stream_data else None

def reconstruct_all_tcp_streams(pcap_file: str, output_dir: str) -> List[str]:
    """
    Reconstruct all TCP streams and save each as a separate file.

    Returns:
        List of saved file paths.
    """
    ensure_dir(output_dir)
    packets = rdpcap(pcap_file)
    streams = defaultdict(bytearray)

    # Simple reassembly: group by 4-tuple (bidirectional combined)
    for pkt in packets:
        if IP in pkt and TCP in pkt and Raw in pkt:
            src = pkt[IP].src
            dst = pkt[IP].dst
            sport = pkt[TCP].sport
            dport = pkt[TCP].dport
            # Use canonical tuple (smaller IP/port first)
            if (src, sport) < (dst, dport):
                key = (src, dst, sport, dport)
            else:
                key = (dst, src, dport, sport)
            streams[key].extend(bytes(pkt[Raw]))

    saved = []
    for key, data in streams.items():
        if len(data) > 0:
            filename = f"tcp_stream_{key[0]}_{key[1]}_{key[2]}_{key[3]}.bin"
            out_path = Path(output_dir) / filename
            with open(out_path, 'wb') as f:
                f.write(data)
            saved.append(str(out_path))
    logger.info(f"Reconstructed {len(saved)} TCP streams.")
    return saved