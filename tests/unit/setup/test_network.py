"""Tests for server.setup.network — LAN IP detection and subnet calculation."""
from __future__ import annotations

import re
import socket

import pytest

from server.setup.network import detect_lan_ip, get_subnet


IP_PATTERN = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")


class TestDetectLanIp:
    """detect_lan_ip must return a valid IPv4 string, using only local OS queries."""

    def test_returns_valid_ipv4(self):
        ip = detect_lan_ip()
        assert IP_PATTERN.match(ip), f"Expected valid IPv4, got {ip!r}"

    def test_no_internet_calls(self, monkeypatch):
        """Ensure we never connect to a real external IP (only broadcast or loopback)."""
        real_connect = socket.socket.connect
        called_external = []

        def guarded_connect(self, address):
            host = address[0] if isinstance(address, tuple) else address
            # Allow broadcast (255.255.255.255) and loopback
            if host not in ("255.255.255.255", "127.0.0.1", "localhost", "0.0.0.0"):
                # Check if it's a LAN address or the machine's own hostname resolution
                # Only flag truly external IPs (like 8.8.8.8, 1.1.1.1 etc.)
                parts = host.split(".")
                if len(parts) == 4:
                    first = int(parts[0])
                    # Allow private ranges: 10.x, 172.16-31.x, 192.168.x
                    if first not in (10, 172, 192, 127):
                        called_external.append(host)
            return real_connect(self, address)

        monkeypatch.setattr(socket.socket, "connect", guarded_connect)
        detect_lan_ip()
        assert called_external == [], f"External IPs contacted: {called_external}"

    def test_fallback_to_localhost(self, monkeypatch):
        """When all detection methods fail, return 127.0.0.1."""
        monkeypatch.setattr(socket, "gethostname", lambda: "impossible-host-xyz")
        monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **kw: (_ for _ in ()).throw(OSError("mock")))

        def broken_connect(self, address):
            raise OSError("mock network failure")

        monkeypatch.setattr(socket.socket, "connect", broken_connect)
        assert detect_lan_ip() == "127.0.0.1"


class TestGetSubnet:
    """get_subnet converts an IP to its /24 CIDR notation."""

    def test_normal_ip(self):
        assert get_subnet("192.168.1.100") == "192.168.1.0/24"

    def test_another_ip(self):
        assert get_subnet("10.0.5.42") == "10.0.5.0/24"

    def test_invalid_ip_returns_none(self):
        assert get_subnet("not-an-ip") is None

    def test_empty_string(self):
        assert get_subnet("") is None

    def test_loopback_returns_none(self):
        assert get_subnet("127.0.0.1") is None
