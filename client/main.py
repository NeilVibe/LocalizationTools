"""
LocalizationTools Client Application

Main entry point for the Gradio desktop application.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import gradio as gr
from loguru import logger

from client import config


def setup_logging():
    """Configure logging for the application."""
    logger.remove()  # Remove default handler

    # Add file logging
    logger.add(
        config.LOG_FILE,
        format=config.LOG_FORMAT,
        level=config.LOG_LEVEL,
        rotation=config.LOG_ROTATION,
        retention=config.LOG_RETENTION,
    )

    # Add console logging in debug mode
    if config.DEBUG:
        logger.add(sys.stdout, format=config.LOG_FORMAT, level="DEBUG")

    logger.info(f"Starting {config.APP_NAME} v{config.APP_VERSION}")
    logger.info(f"Machine ID: {config.MACHINE_ID}")
    logger.info(f"OS: {config.OS_INFO}")


def create_interface():
    """Create the main Gradio interface."""

    with gr.Blocks(
        title=config.WINDOW_TITLE,
        theme=config.UI_THEME,
    ) as app:

        # Header
        with gr.Row():
            gr.Markdown(
                f"""
                # {config.APP_NAME}
                ### Version {config.APP_VERSION}

                Welcome to the unified localization tools suite.
                """
            )

        # Tabs for different tools
        with gr.Tabs():

            # XLSTransfer tab (placeholder)
            with gr.Tab("XLS Transfer"):
                gr.Markdown("### XLS Transfer Tool")
                gr.Markdown("AI-powered translation transfer between Excel files")

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("**Coming Soon**: Create Dictionary, Transfer files, and more")

                # TODO: Import and integrate actual XLSTransfer UI
                # from client.tools.xls_transfer.ui import create_xls_transfer_interface
                # create_xls_transfer_interface()

            # Placeholder for future tools
            with gr.Tab("Quick Search"):
                gr.Markdown("### Quick Search")
                gr.Markdown("*Tool coming soon...*")

            with gr.Tab("TFM Tools"):
                gr.Markdown("### Translation Memory Tools")
                gr.Markdown("*Tool coming soon...*")

            with gr.Tab("Settings"):
                gr.Markdown("### Application Settings")

                with gr.Row():
                    with gr.Column():
                        server_status = gr.Textbox(
                            label="Server Status",
                            value="Checking...",
                            interactive=False
                        )

                        machine_id = gr.Textbox(
                            label="Machine ID",
                            value=config.MACHINE_ID,
                            interactive=False
                        )

                        version_info = gr.Textbox(
                            label="Version",
                            value=config.APP_VERSION,
                            interactive=False
                        )

        # Footer
        with gr.Row():
            gr.Markdown(
                f"""
                ---
                *LocalizationTools* by {config.APP_AUTHOR} |
                Server: {config.SERVER_URL} |
                Logs: {config.LOGS_DIR}
                """
            )

    return app


def main():
    """Main application entry point."""

    # Setup logging
    setup_logging()

    logger.info("Initializing application...")

    try:
        # Create interface
        app = create_interface()

        logger.info("Launching Gradio interface...")

        # Launch app
        app.launch(
            server_name=config.GRADIO_SERVER_NAME,
            server_port=config.GRADIO_SERVER_PORT,
            share=config.GRADIO_SHARE,
            inbrowser=config.GRADIO_INBROWSER,
            quiet=not config.DEBUG,
        )

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        logger.info("Application shutdown complete")


if __name__ == "__main__":
    main()
