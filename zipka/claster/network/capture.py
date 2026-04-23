"""
Packet capture functions using scapy.
"""

import time
from typing import Optional, List
from scapy.all import sniff, wrpcap, conf, get_if_list

from claster.core.logger import get_logger
from claster.core.exceptions import ClasterError

logger = get_logger(__name__)

class NetworkCaptureError(ClasterError):
    """Raised when packet capture fails."""
    pass

def sniff_packets(interface: Optional[str] = None, count: int = 100,
                  output_pcap: Optional[str] = None, timeout: Optional[int] = None,
                  filter_str: Optional[str] = None) -> List:
    """
    Capture a specified number of packets from a network interface.

    Args:
        interface: Network interface name (e.g., 'eth0', 'en0'). If None, uses default.
        count: Number of packets to capture.
        output_pcap: If provided, save captured packets to this PCAP file.
        timeout: Stop capture after this many seconds (overrides count if reached).
        filter_str: BPF filter string (e.g., 'tcp port 80').

    Returns:
        List of captured packets (scapy Packet objects).
    """
    if interface is None:
        interface = conf.iface
    else:
        if interface not in get_if_list():
            raise NetworkCaptureError(f"Interface '{interface}' not found. Available: {get_if_list()}")

    logger.info(f"Starting packet capture on {interface} (count={count}, filter={filter_str})")
    packets = []
    start_time = time.time()

    def stop_callback(pkt):
        packets.append(pkt)
        if timeout and (time.time() - start_time) >= timeout:
            return True
        return len(packets) >= count

    try:
        sniff(iface=interface, prn=lambda p: packets.append(p), stop_filter=stop_callback,
              store=False, filter=filter_str)
    except PermissionError:
        raise NetworkCaptureError("Permission denied. Run with administrator/root privileges.")
    except Exception as e:
        raise NetworkCaptureError(f"Capture failed: {e}")

    if output_pcap:
        wrpcap(output_pcap, packets)
        logger.info(f"Captured {len(packets)} packets, saved to {output_pcap}")
    else:
        logger.info(f"Captured {len(packets)} packets")
    return packets

def sniff_duration(interface: Optional[str] = None, seconds: int = 10,
                   output_pcap: Optional[str] = None, filter_str: Optional[str] = None) -> List:
    """
    Capture packets for a specified duration.

    Args:
        interface: Network interface.
        seconds: Capture duration in seconds.
        output_pcap: Save to PCAP if provided.
        filter_str: BPF filter.

    Returns:
        List of captured packets.
    """
    logger.info(f"Capturing packets on {interface} for {seconds} seconds")
    return sniff_packets(interface=interface, count=0, output_pcap=output_pcap,
                         timeout=seconds, filter_str=filter_str)