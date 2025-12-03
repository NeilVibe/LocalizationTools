"""
Progress Tracking Utilities

Provides clean, reusable progress tracking for long-running operations.
Works seamlessly with Gradio's progress indicators.
"""

from typing import Callable, Optional
from tqdm import tqdm
import gradio as gr


class ProgressTracker:
    """
    Clean progress tracker that works with both console and Gradio.

    Usage:
        with ProgressTracker(total=100, desc="Processing") as progress:
            for i in range(100):
                # Do work
                progress.update(1, status=f"Processing item {i}")
    """

    def __init__(
        self,
        total: int,
        desc: str = "Processing",
        gradio_progress: Optional[gr.Progress] = None
    ):
        """
        Initialize progress tracker.

        Args:
            total: Total number of items to process
            desc: Description of the operation
            gradio_progress: Optional Gradio progress object
        """
        self.total = total
        self.desc = desc
        self.gradio_progress = gradio_progress
        self.current = 0
        self.tqdm_bar = None

    def __enter__(self):
        """Start progress tracking."""
        # Create tqdm progress bar for console
        self.tqdm_bar = tqdm(
            total=self.total,
            desc=self.desc,
            unit="items",
            ncols=80
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up progress tracking."""
        if self.tqdm_bar:
            self.tqdm_bar.close()
        return False

    def update(self, n: int = 1, status: Optional[str] = None):
        """
        Update progress.

        Args:
            n: Number of items completed
            status: Optional status message
        """
        self.current += n

        # Update tqdm bar
        if self.tqdm_bar:
            self.tqdm_bar.update(n)
            if status:
                self.tqdm_bar.set_postfix_str(status)

        # Update Gradio progress if available
        if self.gradio_progress:
            progress_value = self.current / self.total if self.total > 0 else 0
            if status:
                self.gradio_progress(progress_value, desc=f"{self.desc}: {status}")
            else:
                self.gradio_progress(progress_value, desc=self.desc)

    def set_status(self, status: str):
        """
        Update status message without incrementing progress.

        Args:
            status: Status message
        """
        if self.tqdm_bar:
            self.tqdm_bar.set_postfix_str(status)

        if self.gradio_progress:
            progress_value = self.current / self.total if self.total > 0 else 0
            self.gradio_progress(progress_value, desc=f"{self.desc}: {status}")


def track_progress(
    items: list,
    process_func: Callable,
    desc: str = "Processing",
    gradio_progress: Optional[gr.Progress] = None
):
    """
    Convenience function to track progress over a list of items.

    Args:
        items: List of items to process
        process_func: Function to apply to each item
        desc: Description of the operation
        gradio_progress: Optional Gradio progress object

    Returns:
        List of results

    Example:
        results = track_progress(
            items=files,
            process_func=lambda f: process_file(f),
            desc="Processing files"
        )
    """
    results = []

    with ProgressTracker(
        total=len(items),
        desc=desc,
        gradio_progress=gradio_progress
    ) as progress:
        for i, item in enumerate(items):
            result = process_func(item)
            results.append(result)
            progress.update(1, status=f"Item {i+1}/{len(items)}")

    return results


class SimpleProgress:
    """
    Simplified progress tracker for quick operations.

    Usage:
        progress = SimpleProgress("Loading model...")
        # Do work
        progress.done("Model loaded!")
    """

    def __init__(self, message: str):
        """
        Initialize simple progress.

        Args:
            message: Initial message
        """
        print(f"⏳ {message}")
        self.message = message

    def update(self, message: str):
        """Update progress message."""
        print(f"⏳ {message}")

    def done(self, message: Optional[str] = None):
        """Mark as complete."""
        if message:
            print(f"✓ {message}")
        else:
            print(f"✓ {self.message} - Complete!")

    def error(self, message: str):
        """Mark as error."""
        print(f"✗ {message}")


# Example usage
if __name__ == "__main__":
    import time

    # Example 1: Basic progress tracking
    print("Example 1: Basic Progress Tracking")
    with ProgressTracker(total=10, desc="Processing files") as progress:
        for i in range(10):
            time.sleep(0.1)
            progress.update(1, status=f"File {i+1}")

    print("\nExample 2: Simple Progress")
    progress = SimpleProgress("Loading model")
    time.sleep(0.5)
    progress.update("Configuring model")
    time.sleep(0.5)
    progress.done("Model ready!")
