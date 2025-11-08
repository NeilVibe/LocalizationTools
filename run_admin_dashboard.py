#!/usr/bin/env python3
"""
Admin Dashboard Launcher

Quick launcher for the LocalizationTools admin dashboard.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger
from server.admin.dashboard import create_admin_dashboard
from server import config


def main():
    """Launch Admin Dashboard."""

    logger.info("Starting LocalizationTools Admin Dashboard...")
    logger.info(f"Server: {config.APP_NAME} v{config.APP_VERSION}")
    logger.info(f"Database: {config.DATABASE_TYPE}")

    # Create dashboard
    dashboard = create_admin_dashboard()

    # Launch
    logger.info(f"Launching Admin Dashboard on http://127.0.0.1:{config.ADMIN_DASHBOARD_PORT}")

    dashboard.launch(
        server_name="0.0.0.0",
        server_port=config.ADMIN_DASHBOARD_PORT,
        share=False,
        show_error=True,
        quiet=False,
        inbrowser=True  # Auto-open in browser
    )


if __name__ == "__main__":
    main()
