#!/usr/bin/env python3
"""
Real-time Log Monitor for Claude
Allows me to check all server logs programmatically
"""

import os
import subprocess
from pathlib import Path

BASE_DIR = Path("/home/<USERNAME>/LocalizationTools")
LOG_FILE = BASE_DIR / "server/logs/localizationtools.log"
ERROR_LOG = BASE_DIR / "server/logs/error.log"

def check_running_servers():
    """Check what servers are running"""
    print("\n🔍 RUNNING SERVERS:")
    print("=" * 60)

    # Check backend
    result = subprocess.run(
        ["pgrep", "-f", "python3 server/main.py"],
        capture_output=True, text=True
    )
    if result.stdout.strip():
        print(f"✅ Backend Server: PID {result.stdout.strip()}")
    else:
        print("❌ Backend Server: NOT RUNNING")

    # Check dashboard
    result = subprocess.run(
        ["pgrep", "-f", "npm run dev.*5175"],
        capture_output=True, text=True
    )
    if result.stdout.strip():
        print(f"✅ Admin Dashboard: PID {result.stdout.strip()}")
    else:
        print("❌ Admin Dashboard: NOT RUNNING")

    print()

def check_server_health():
    """Check server health endpoints"""
    print("🏥 SERVER HEALTH:")
    print("=" * 60)

    import urllib.request
    import json

    # Backend health
    try:
        response = urllib.request.urlopen("http://localhost:8888/health", timeout=5)
        data = json.loads(response.read())
        print(f"✅ Backend (8888): {data.get('status', 'unknown')}")
        print(f"   Database: {data.get('database', 'unknown')}")
        print(f"   Version: {data.get('version', 'unknown')}")
    except Exception as e:
        print(f"❌ Backend (8888): {str(e)}")

    # Dashboard
    try:
        response = urllib.request.urlopen("http://localhost:5175/", timeout=5)
        print(f"✅ Dashboard (5175): Online")
    except Exception as e:
        print(f"❌ Dashboard (5175): {str(e)}")

    print()

def get_recent_errors(n=10):
    """Get recent error log entries"""
    print(f"\n❌ RECENT ERRORS (Last {n}):")
    print("=" * 60)

    if ERROR_LOG.exists():
        result = subprocess.run(
            ["tail", "-n", str(n), str(ERROR_LOG)],
            capture_output=True, text=True
        )
        if result.stdout.strip():
            print(result.stdout)
        else:
            print("No errors! 🎉")
    else:
        print("No error log file found")
    print()

def get_recent_activity(n=20):
    """Get recent activity from main log"""
    print(f"\n📊 RECENT ACTIVITY (Last {n}):")
    print("=" * 60)

    if LOG_FILE.exists():
        result = subprocess.run(
            ["tail", "-n", str(n), str(LOG_FILE)],
            capture_output=True, text=True
        )

        for line in result.stdout.split('\n'):
            if 'ERROR' in line:
                print(f"❌ {line}")
            elif 'WARNING' in line:
                print(f"⚠️  {line}")
            elif 'SUCCESS' in line:
                print(f"✅ {line}")
            elif 'INFO' in line:
                print(f"ℹ️  {line}")
            elif line.strip():
                print(f"   {line}")
    else:
        print("No log file found")
    print()

def get_api_stats():
    """Get API request statistics"""
    print("\n📈 API REQUEST STATS:")
    print("=" * 60)

    if LOG_FILE.exists():
        # Count requests
        result = subprocess.run(
            ["grep", "-c", "→ GET", str(LOG_FILE)],
            capture_output=True, text=True
        )
        get_count = result.stdout.strip() if result.returncode == 0 else "0"

        result = subprocess.run(
            ["grep", "-c", "→ POST", str(LOG_FILE)],
            capture_output=True, text=True
        )
        post_count = result.stdout.strip() if result.returncode == 0 else "0"

        result = subprocess.run(
            ["grep", "-c", "← 200", str(LOG_FILE)],
            capture_output=True, text=True
        )
        success_count = result.stdout.strip() if result.returncode == 0 else "0"

        result = subprocess.run(
            ["grep", "-c", "← 40", str(LOG_FILE)],
            capture_output=True, text=True
        )
        error_count = result.stdout.strip() if result.returncode == 0 else "0"

        print(f"GET requests: {get_count}")
        print(f"POST requests: {post_count}")
        print(f"Success (200): {success_count}")
        print(f"Errors (40x): {error_count}")
    else:
        print("No log file found")
    print()

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🔍 LocaNext - Complete Server Status")
    print("=" * 60)

    check_running_servers()
    check_server_health()
    get_api_stats()
    get_recent_activity(15)
    get_recent_errors(5)

    print("\n" + "=" * 60)
    print("📝 LIVE MONITORING COMMANDS:")
    print("=" * 60)
    print("Watch live logs: tail -f server/logs/localizationtools.log")
    print("Check errors:    tail -f server/logs/error.log")
    print("Run this again:  python3 scripts/check_logs.py")
    print("=" * 60 + "\n")
