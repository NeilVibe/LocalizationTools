#!/usr/bin/env python3
"""
XLSTransfer Standalone Launcher

Quick launcher for the XLSTransfer tool.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger
from client.tools.xls_transfer.ui import create_ui


def main():
    """Launch XLSTransfer UI."""

    logger.info("Starting XLSTransfer...")

    # Create UI
    app = create_ui()

    # Launch
    logger.info("Launching XLSTransfer on http://127.0.0.1:7860")

    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True,
        quiet=False,
        inbrowser=True  # Auto-open in browser
    )


if __name__ == "__main__":
    main()
