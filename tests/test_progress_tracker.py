#!/usr/bin/env python3
"""
Test progress tracker database connection
"""
import sys
from pathlib import Path

# Add client tools path
client_path = Path(__file__).parent / "client" / "tools" / "xls_transfer"
sys.path.insert(0, str(client_path))

from progress_tracker import ProgressTracker

# Test without operation_id (should be disabled)
print("=" * 60)
print("Test 1: Progress tracker without operation_id")
print("=" * 60)
tracker1 = ProgressTracker()
tracker1.update(50.0, "Test update without operation_id")
tracker1.log_milestone("Test milestone")

# Test with fake operation_id (should try to update database)
print("\n" + "=" * 60)
print("Test 2: Progress tracker with operation_id=999")
print("=" * 60)
tracker2 = ProgressTracker(operation_id=999)
tracker2.update(75.0, "Test update with operation_id", completed_steps=75, total_steps=100)
tracker2.log_milestone("Database test milestone")

print("\n" + "=" * 60)
print("Tests completed!")
print("=" * 60)
