from __future__ import annotations
import socket


def detect_lan_ip() -> str:
    """Detect LAN IP using local OS queries only. Zero network calls."""
    try:
        hostname = socket.gethostname()
        ips = socket.getaddrinfo(hostname, None, socket.AF_INET)
        for _, _, _, _, (ip, _) in ips:
            if not ip.startswith("127."):
                return ip
    except Exception:
        pass
    return "127.0.0.1"


def get_subnet(ip: str) -> str | None:
    """Get /24 subnet. '192.168.1.100' -> '192.168.1.0/24'. Returns None for loopback."""
    parts = ip.split(".")
    if len(parts) == 4 and not ip.startswith("127."):
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    return None
