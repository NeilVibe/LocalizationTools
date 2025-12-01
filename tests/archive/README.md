# Test Archive

This folder contains archived/deprecated tests that are no longer part of the active test suite.

## Why Archive Instead of Delete?

- Preserves test history for reference
- May contain useful testing patterns
- Can be reactivated if needed
- Helps track test evolution over time

## Guidelines

1. Move tests here when they are:
   - Replaced by newer, more efficient tests
   - Testing deprecated functionality
   - Redundant with other tests

2. When archiving:
   - Add a comment at the top explaining why it was archived
   - Include the date of archival
   - Note what test replaced it (if applicable)

## Currently Archived (2025-12-01)

| File | Reason | Replaced By |
|------|--------|-------------|
| `test_kr_similar.py` | Duplicate | `e2e/test_kr_similar_e2e.py` |
| `test_quicksearch_phase4.py` | Duplicate | `e2e/test_quicksearch_e2e.py` |
| `test_xlstransfer_cli.py` | Duplicate | `e2e/test_xlstransfer_e2e.py` |
| `test_full_workflow.py` | Duplicate | `e2e/test_complete_user_flow.py` |
