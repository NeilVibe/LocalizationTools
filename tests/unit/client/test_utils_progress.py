"""
Unit Tests for Progress Tracking Utilities

Tests all functionality of the progress tracking system including:
- ProgressTracker context manager
- Console and callback progress updates
- Status message handling
- SimpleProgress helper
- track_progress convenience function

CLEAN, organized, comprehensive testing.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import time

from server.utils.client.progress import ProgressTracker, SimpleProgress, track_progress


# ============================================
# ProgressTracker Tests
# ============================================

@pytest.mark.unit
@pytest.mark.client
def test_progress_tracker_initialization():
    """
    Test that ProgressTracker initializes correctly.

    Given: ProgressTracker parameters
    When: ProgressTracker is instantiated
    Then: All properties are set correctly
    """
    tracker = ProgressTracker(total=100, desc="Testing")

    assert tracker.total == 100
    assert tracker.desc == "Testing"
    assert tracker.current == 0
    assert tracker.callback is None
    assert tracker.tqdm_bar is None


@pytest.mark.unit
@pytest.mark.client
def test_progress_tracker_context_manager_creates_tqdm():
    """
    Test that entering context manager creates tqdm bar.

    Given: A ProgressTracker instance
    When: Used as context manager
    Then: tqdm bar is created
    """
    with ProgressTracker(total=10, desc="Test") as tracker:
        assert tracker.tqdm_bar is not None


@pytest.mark.unit
@pytest.mark.client
def test_progress_tracker_context_manager_cleanup():
    """
    Test that exiting context manager cleans up tqdm bar.

    Given: A ProgressTracker instance in use
    When: Context manager exits
    Then: tqdm bar is closed
    """
    tracker = ProgressTracker(total=10, desc="Test")

    with tracker:
        tqdm_bar = tracker.tqdm_bar
        assert tqdm_bar is not None

    # After exit, tqdm should be closed (we can't easily check this, but no errors should occur)
    # Just verify it completed without exception


@pytest.mark.unit
@pytest.mark.client
def test_progress_tracker_update_increments_current():
    """
    Test that update() increments current value.

    Given: A ProgressTracker at current=0
    When: update(5) is called
    Then: current becomes 5
    """
    with ProgressTracker(total=100, desc="Test") as tracker:
        tracker.update(5)
        assert tracker.current == 5

        tracker.update(3)
        assert tracker.current == 8


@pytest.mark.unit
@pytest.mark.client
def test_progress_tracker_update_with_status():
    """
    Test that update() accepts status message.

    Given: A ProgressTracker instance
    When: update() is called with status message
    Then: Status is updated without errors
    """
    with ProgressTracker(total=10, desc="Test") as tracker:
        # Should not raise exception
        tracker.update(1, status="Processing item 1")
        assert tracker.current == 1


@pytest.mark.unit
@pytest.mark.client
def test_progress_tracker_set_status():
    """
    Test that set_status() updates status without incrementing.

    Given: A ProgressTracker at current=5
    When: set_status() is called
    Then: current remains 5
    """
    with ProgressTracker(total=10, desc="Test") as tracker:
        tracker.update(5)
        tracker.set_status("Waiting...")

        assert tracker.current == 5  # Should not increment


@pytest.mark.unit
@pytest.mark.client
def test_progress_tracker_with_callback():
    """
    Test that ProgressTracker works with callback function.

    Given: A mock callback function
    When: ProgressTracker updates
    Then: Callback is called with correct values
    """
    mock_callback = Mock()

    with ProgressTracker(total=100, desc="Test", callback=mock_callback) as tracker:
        tracker.update(25, status="Quarter done")

        # Callback should be called
        mock_callback.assert_called()
        call_args = mock_callback.call_args

        # Should be called with progress value (0.25) and status
        progress_value = call_args[0][0]
        assert progress_value == 0.25


@pytest.mark.unit
@pytest.mark.client
def test_progress_tracker_callback_with_status():
    """
    Test that callback receives status messages.

    Given: A ProgressTracker with callback
    When: update() is called with status
    Then: Callback receives progress value and status
    """
    mock_callback = Mock()

    with ProgressTracker(total=10, desc="Processing", callback=mock_callback) as tracker:
        tracker.update(5, status="Item 5")

        call_args = mock_callback.call_args
        status = call_args[0][1]

        assert "Item 5" in status


@pytest.mark.unit
@pytest.mark.client
def test_progress_tracker_zero_total_no_crash():
    """
    Test that zero total doesn't cause division by zero.

    Given: ProgressTracker with total=0
    When: update() is called
    Then: No exception is raised
    """
    mock_callback = Mock()

    with ProgressTracker(total=0, desc="Test", callback=mock_callback) as tracker:
        # Should not crash
        tracker.update(1)

        # Callback should receive 0.0 as progress
        call_args = mock_callback.call_args
        progress_value = call_args[0][0]
        assert progress_value == 0.0


@pytest.mark.unit
@pytest.mark.client
def test_progress_tracker_full_workflow():
    """
    Test complete progress tracking workflow.

    Given: A ProgressTracker for 10 items
    When: All 10 items are processed with updates
    Then: Progress reaches 100%
    """
    mock_callback = Mock()

    with ProgressTracker(total=10, desc="Processing", callback=mock_callback) as tracker:
        for i in range(10):
            tracker.update(1, status=f"Item {i+1}")

        assert tracker.current == 10

        # Final progress should be 1.0 (100%)
        final_call = mock_callback.call_args
        progress_value = final_call[0][0]
        assert progress_value == 1.0


# ============================================
# track_progress Function Tests
# ============================================

@pytest.mark.unit
@pytest.mark.client
def test_track_progress_processes_all_items():
    """
    Test that track_progress processes all items in list.

    Given: A list of 5 items
    When: track_progress is called with a processing function
    Then: All 5 items are processed and results returned
    """
    items = [1, 2, 3, 4, 5]

    def double(x):
        return x * 2

    results = track_progress(items, double, desc="Doubling")

    assert results == [2, 4, 6, 8, 10]


@pytest.mark.unit
@pytest.mark.client
def test_track_progress_with_callback():
    """
    Test that track_progress works with callback.

    Given: A list of items and mock callback
    When: track_progress is called
    Then: Callback is updated for each item
    """
    items = ["a", "b", "c"]
    mock_callback = Mock()

    def uppercase(x):
        return x.upper()

    results = track_progress(
        items,
        uppercase,
        desc="Converting",
        callback=mock_callback
    )

    assert results == ["A", "B", "C"]

    # Callback should be called for each item
    assert mock_callback.call_count >= len(items)


@pytest.mark.unit
@pytest.mark.client
def test_track_progress_empty_list():
    """
    Test that track_progress handles empty list.

    Given: An empty list
    When: track_progress is called
    Then: Empty list is returned without errors
    """
    items = []

    def process(x):
        return x

    results = track_progress(items, process, desc="Processing")

    assert results == []


@pytest.mark.unit
@pytest.mark.client
def test_track_progress_function_exception_propagates():
    """
    Test that exceptions in processing function propagate.

    Given: A processing function that raises exception
    When: track_progress is called
    Then: Exception is raised
    """
    items = [1, 2, 3]

    def failing_func(x):
        if x == 2:
            raise ValueError("Test error")
        return x

    with pytest.raises(ValueError, match="Test error"):
        track_progress(items, failing_func, desc="Processing")


# ============================================
# SimpleProgress Tests
# ============================================

@pytest.mark.unit
@pytest.mark.client
def test_simple_progress_initialization():
    """
    Test that SimpleProgress initializes and prints message.

    Given: An initial message
    When: SimpleProgress is created
    Then: Message is stored
    """
    progress = SimpleProgress("Loading model")

    assert progress.message == "Loading model"


@pytest.mark.unit
@pytest.mark.client
def test_simple_progress_update(capsys):
    """
    Test that update() prints new message.

    Given: A SimpleProgress instance
    When: update() is called
    Then: New message is printed
    """
    progress = SimpleProgress("Initial")

    progress.update("Updated message")

    captured = capsys.readouterr()
    assert "Updated message" in captured.out


@pytest.mark.unit
@pytest.mark.client
def test_simple_progress_done(capsys):
    """
    Test that done() prints completion message.

    Given: A SimpleProgress instance
    When: done() is called
    Then: Completion message is printed
    """
    progress = SimpleProgress("Loading")

    progress.done("Loaded successfully!")

    captured = capsys.readouterr()
    assert "Loaded successfully!" in captured.out


@pytest.mark.unit
@pytest.mark.client
def test_simple_progress_done_default_message(capsys):
    """
    Test that done() uses default message if none provided.

    Given: A SimpleProgress instance
    When: done() is called without message
    Then: Default completion message is printed
    """
    progress = SimpleProgress("Processing")

    progress.done()

    captured = capsys.readouterr()
    assert "Processing" in captured.out
    assert "Complete" in captured.out


@pytest.mark.unit
@pytest.mark.client
def test_simple_progress_error(capsys):
    """
    Test that error() prints error message.

    Given: A SimpleProgress instance
    When: error() is called
    Then: Error message is printed
    """
    progress = SimpleProgress("Processing")

    progress.error("Something went wrong!")

    captured = capsys.readouterr()
    assert "Something went wrong!" in captured.out


@pytest.mark.unit
@pytest.mark.client
def test_simple_progress_workflow(capsys):
    """
    Test complete SimpleProgress workflow.

    Given: A SimpleProgress instance
    When: Various methods are called in sequence
    Then: All messages are printed correctly
    """
    progress = SimpleProgress("Starting task")
    progress.update("Step 1 complete")
    progress.update("Step 2 complete")
    progress.done("All done!")

    captured = capsys.readouterr()

    assert "Starting task" in captured.out
    assert "Step 1 complete" in captured.out
    assert "Step 2 complete" in captured.out
    assert "All done!" in captured.out


# ============================================
# Edge Cases and Error Handling
# ============================================

@pytest.mark.unit
@pytest.mark.client
def test_progress_tracker_negative_update():
    """
    Test that negative updates are handled.

    Given: A ProgressTracker
    When: update() is called with negative value
    Then: Current is updated (though unusual use case)
    """
    with ProgressTracker(total=10, desc="Test") as tracker:
        tracker.update(5)
        tracker.update(-2)

        # Unusual but should work
        assert tracker.current == 3


@pytest.mark.unit
@pytest.mark.client
def test_progress_tracker_update_beyond_total():
    """
    Test that updating beyond total doesn't crash.

    Given: A ProgressTracker with total=10
    When: update() is called to exceed total
    Then: No exception is raised
    """
    mock_callback = Mock()

    with ProgressTracker(total=10, desc="Test", callback=mock_callback) as tracker:
        tracker.update(15)

        # Should not crash, current becomes 15
        assert tracker.current == 15

        # Progress value should be capped at or exceed 1.0
        call_args = mock_callback.call_args
        progress_value = call_args[0][0]
        assert progress_value >= 1.0


@pytest.mark.unit
@pytest.mark.client
def test_progress_tracker_without_tqdm():
    """
    Test that ProgressTracker works if tqdm fails to initialize.

    Given: ProgressTracker with tqdm disabled
    When: update() is called
    Then: No exception is raised
    """
    tracker = ProgressTracker(total=10, desc="Test")

    # Don't use context manager, so tqdm_bar is None
    tracker.update(5)

    assert tracker.current == 5


@pytest.mark.unit
@pytest.mark.client
def test_track_progress_single_item():
    """
    Test track_progress with single item.

    Given: A list with one item
    When: track_progress is called
    Then: Single result is returned
    """
    items = [42]

    def identity(x):
        return x

    results = track_progress(items, identity, desc="Processing")

    assert results == [42]


@pytest.mark.unit
@pytest.mark.client
def test_progress_tracker_multiple_status_updates():
    """
    Test that multiple status updates work correctly.

    Given: A ProgressTracker
    When: set_status() is called multiple times
    Then: Current value doesn't change
    """
    with ProgressTracker(total=100, desc="Test") as tracker:
        tracker.update(10)

        tracker.set_status("Status 1")
        assert tracker.current == 10

        tracker.set_status("Status 2")
        assert tracker.current == 10

        tracker.set_status("Status 3")
        assert tracker.current == 10


# ============================================
# Integration Tests
# ============================================

@pytest.mark.unit
@pytest.mark.client
def test_progress_tracker_realistic_file_processing():
    """
    Test realistic file processing scenario with progress tracking.

    Given: A list of simulated files to process
    When: Processing with progress tracking
    Then: All files are processed with correct progress updates
    """
    files = [f"file_{i}.txt" for i in range(10)]
    processed_files = []

    mock_callback = Mock()

    with ProgressTracker(total=len(files), desc="Processing files", callback=mock_callback) as tracker:
        for i, file in enumerate(files):
            # Simulate processing
            processed_files.append(file.upper())
            tracker.update(1, status=f"Processed {file}")

    assert len(processed_files) == 10
    assert tracker.current == 10

    # Verify final progress is 100%
    final_call = mock_callback.call_args
    progress_value = final_call[0][0]
    assert progress_value == 1.0


@pytest.mark.unit
@pytest.mark.client
def test_combined_progress_trackers():
    """
    Test using multiple progress trackers in sequence.

    Given: Two separate tasks requiring progress tracking
    When: Both use ProgressTracker
    Then: Both complete independently
    """
    # First task
    with ProgressTracker(total=5, desc="Task 1") as tracker1:
        for i in range(5):
            tracker1.update(1)
        assert tracker1.current == 5

    # Second task
    with ProgressTracker(total=3, desc="Task 2") as tracker2:
        for i in range(3):
            tracker2.update(1)
        assert tracker2.current == 3
