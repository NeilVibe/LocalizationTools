from __future__ import annotations
import socket


def detect_lan_ip() -> str:
    """Detect LAN IP without any internet access. Local OS queries only."""
    try:
        hostname = socket.gethostname()
        ips = socket.getaddrinfo(hostname, None, socket.AF_INET)
        for _, _, _, _, (ip, _) in ips:
            if not ip.startswith("127."):
                return ip
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("255.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        if not ip.startswith("127."):
            return ip
    except Exception:
        pass
    return "127.0.0.1"


def get_subnet(ip: str) -> str:
    """Get /24 subnet. '192.168.1.100' -> '192.168.1.0/24'."""
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    return "0.0.0.0/0"
