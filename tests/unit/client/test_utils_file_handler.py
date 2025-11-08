"""
Unit Tests for File Handler Utilities

Tests all functionality of the file handling system including:
- File validation
- File size calculation
- File hashing
- Temporary file management
- Safe filename generation
- Output path creation

CLEAN, organized, comprehensive testing.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path

from client.utils.file_handler import (
    get_file_size_mb,
    get_file_hash,
    create_temp_copy,
    safe_delete_file,
    ensure_output_path,
    validate_file_exists,
    get_safe_filename,
    count_files_in_directory,
    TempFileManager
)


# ============================================
# File Size Tests
# ============================================

@pytest.mark.unit
@pytest.mark.client
def test_get_file_size_mb_existing_file(temp_file):
    """
    Test that get_file_size_mb returns correct size.

    Given: A file with known size
    When: get_file_size_mb is called
    Then: Correct size in MB is returned
    """
    # Create file with known size (1 KB = 0.001 MB)
    temp_file.write_bytes(b"x" * 1024)

    size_mb = get_file_size_mb(str(temp_file))

    assert size_mb == 0.0  # Rounds to 0.0 MB (2 decimals)


@pytest.mark.unit
@pytest.mark.client
def test_get_file_size_mb_larger_file(temp_dir):
    """
    Test file size calculation for larger file.

    Given: A file with size of 2.5 MB
    When: get_file_size_mb is called
    Then: Correct size is returned
    """
    large_file = temp_dir / "large.txt"
    large_file.write_bytes(b"x" * (2 * 1024 * 1024 + 512 * 1024))  # 2.5 MB

    size_mb = get_file_size_mb(str(large_file))

    assert 2.4 <= size_mb <= 2.6  # Should be around 2.5 MB


@pytest.mark.unit
@pytest.mark.client
def test_get_file_size_mb_nonexistent_file():
    """
    Test that nonexistent file returns 0.0.

    Given: A path to nonexistent file
    When: get_file_size_mb is called
    Then: 0.0 is returned
    """
    size_mb = get_file_size_mb("/nonexistent/file.txt")

    assert size_mb == 0.0


@pytest.mark.unit
@pytest.mark.client
def test_get_file_size_mb_empty_file(temp_file):
    """
    Test that empty file returns 0.0 MB.

    Given: An empty file
    When: get_file_size_mb is called
    Then: 0.0 is returned
    """
    temp_file.write_bytes(b"")

    size_mb = get_file_size_mb(str(temp_file))

    assert size_mb == 0.0


# ============================================
# File Hash Tests
# ============================================

@pytest.mark.unit
@pytest.mark.client
def test_get_file_hash_md5(temp_file):
    """
    Test MD5 hash calculation.

    Given: A file with known content
    When: get_file_hash is called with MD5
    Then: Correct MD5 hash is returned
    """
    content = b"Hello, World!"
    temp_file.write_bytes(content)

    hash_value = get_file_hash(str(temp_file), algorithm="md5")

    # Known MD5 hash of "Hello, World!"
    expected_hash = "65a8e27d8879283831b664bd8b7f0ad4"
    assert hash_value == expected_hash


@pytest.mark.unit
@pytest.mark.client
def test_get_file_hash_sha256(temp_file):
    """
    Test SHA256 hash calculation.

    Given: A file with known content
    When: get_file_hash is called with SHA256
    Then: Correct SHA256 hash is returned
    """
    content = b"Test content"
    temp_file.write_bytes(content)

    hash_value = get_file_hash(str(temp_file), algorithm="sha256")

    assert len(hash_value) == 64  # SHA256 produces 64-character hex string
    assert isinstance(hash_value, str)


@pytest.mark.unit
@pytest.mark.client
def test_get_file_hash_consistency(temp_file):
    """
    Test that hash is consistent for same content.

    Given: A file with specific content
    When: Hash is calculated multiple times
    Then: Same hash is returned
    """
    temp_file.write_bytes(b"Consistent content")

    hash1 = get_file_hash(str(temp_file))
    hash2 = get_file_hash(str(temp_file))

    assert hash1 == hash2


@pytest.mark.unit
@pytest.mark.client
def test_get_file_hash_different_content(temp_dir):
    """
    Test that different content produces different hash.

    Given: Two files with different content
    When: Hashes are calculated
    Then: Different hashes are returned
    """
    file1 = temp_dir / "file1.txt"
    file2 = temp_dir / "file2.txt"

    file1.write_bytes(b"Content A")
    file2.write_bytes(b"Content B")

    hash1 = get_file_hash(str(file1))
    hash2 = get_file_hash(str(file2))

    assert hash1 != hash2


# ============================================
# Temporary File Tests
# ============================================

@pytest.mark.unit
@pytest.mark.client
def test_create_temp_copy_creates_file(temp_dir):
    """
    Test that create_temp_copy creates a copy.

    Given: An original file
    When: create_temp_copy is called
    Then: Temporary copy is created
    """
    original = temp_dir / "original.txt"
    original.write_text("Original content")

    temp_copy = create_temp_copy(str(original))

    assert Path(temp_copy).exists()
    assert Path(temp_copy).read_text() == "Original content"


@pytest.mark.unit
@pytest.mark.client
def test_create_temp_copy_with_suffix(temp_dir):
    """
    Test that create_temp_copy uses custom suffix.

    Given: An original file and custom suffix
    When: create_temp_copy is called
    Then: Temp file has custom suffix
    """
    original = temp_dir / "data.xlsx"
    original.write_text("Data")

    temp_copy = create_temp_copy(str(original), suffix="_backup")

    assert "_backup" in temp_copy
    assert Path(temp_copy).suffix == ".xlsx"


@pytest.mark.unit
@pytest.mark.client
def test_create_temp_copy_preserves_extension(temp_dir):
    """
    Test that temp copy preserves file extension.

    Given: A file with specific extension
    When: create_temp_copy is called
    Then: Extension is preserved
    """
    original = temp_dir / "document.pdf"
    original.write_bytes(b"PDF content")

    temp_copy = create_temp_copy(str(original))

    assert Path(temp_copy).suffix == ".pdf"


# ============================================
# Safe Delete Tests
# ============================================

@pytest.mark.unit
@pytest.mark.client
def test_safe_delete_file_existing(temp_file):
    """
    Test that safe_delete_file deletes existing file.

    Given: An existing file
    When: safe_delete_file is called
    Then: File is deleted and True is returned
    """
    temp_file.write_text("Content")
    assert temp_file.exists()

    result = safe_delete_file(str(temp_file))

    assert result is True
    assert not temp_file.exists()


@pytest.mark.unit
@pytest.mark.client
def test_safe_delete_file_nonexistent():
    """
    Test that safe_delete_file handles nonexistent file.

    Given: A path to nonexistent file
    When: safe_delete_file is called
    Then: False is returned, no exception raised
    """
    result = safe_delete_file("/nonexistent/file.txt")

    assert result is False


@pytest.mark.unit
@pytest.mark.client
def test_safe_delete_file_already_deleted(temp_file):
    """
    Test that deleting already deleted file doesn't crash.

    Given: A file that was already deleted
    When: safe_delete_file is called again
    Then: False is returned
    """
    temp_file.write_text("Content")
    safe_delete_file(str(temp_file))

    # Try to delete again
    result = safe_delete_file(str(temp_file))

    assert result is False


# ============================================
# Output Path Tests
# ============================================

@pytest.mark.unit
@pytest.mark.client
def test_ensure_output_path_with_suffix(temp_dir):
    """
    Test that ensure_output_path generates correct path.

    Given: An input file path and suffix
    When: ensure_output_path is called
    Then: Correct output path is generated
    """
    input_path = temp_dir / "input.xlsx"

    output_path = ensure_output_path(str(input_path), "_translated")

    expected = temp_dir / "input_translated.xlsx"
    assert Path(output_path) == expected


@pytest.mark.unit
@pytest.mark.client
def test_ensure_output_path_preserves_extension(temp_dir):
    """
    Test that output path preserves file extension.

    Given: An input file with specific extension
    When: ensure_output_path is called
    Then: Extension is preserved
    """
    input_path = temp_dir / "data.csv"

    output_path = ensure_output_path(str(input_path), "_processed")

    assert Path(output_path).suffix == ".csv"


@pytest.mark.unit
@pytest.mark.client
def test_ensure_output_path_with_output_dir(temp_dir):
    """
    Test that output path can use different directory.

    Given: Input path and separate output directory
    When: ensure_output_path is called with output_dir
    Then: File is placed in output directory
    """
    input_path = temp_dir / "input" / "file.txt"
    output_dir = temp_dir / "output"
    output_dir.mkdir()

    output_path = ensure_output_path(str(input_path), "_done", str(output_dir))

    assert Path(output_path).parent == output_dir
    assert Path(output_path).name == "file_done.txt"


@pytest.mark.unit
@pytest.mark.client
def test_ensure_output_path_same_dir_default(temp_dir):
    """
    Test that output defaults to same directory as input.

    Given: Input path without output_dir specified
    When: ensure_output_path is called
    Then: Output is in same directory as input
    """
    input_path = temp_dir / "file.xlsx"

    output_path = ensure_output_path(str(input_path), "_result")

    assert Path(output_path).parent == temp_dir


# ============================================
# File Validation Tests
# ============================================

@pytest.mark.unit
@pytest.mark.client
def test_validate_file_exists_valid_file(temp_file):
    """
    Test validation of existing file.

    Given: An existing file
    When: validate_file_exists is called
    Then: (True, "") is returned
    """
    temp_file.write_text("Content")

    is_valid, error = validate_file_exists(str(temp_file))

    assert is_valid is True
    assert error == ""


@pytest.mark.unit
@pytest.mark.client
def test_validate_file_exists_nonexistent():
    """
    Test validation of nonexistent file.

    Given: Path to nonexistent file
    When: validate_file_exists is called
    Then: (False, error_message) is returned
    """
    is_valid, error = validate_file_exists("/nonexistent/file.txt")

    assert is_valid is False
    assert "not found" in error.lower()


@pytest.mark.unit
@pytest.mark.client
def test_validate_file_exists_with_valid_extension(temp_file):
    """
    Test validation with correct extension.

    Given: File with .txt extension
    When: validate_file_exists is called with ['.txt'] extensions
    Then: (True, "") is returned
    """
    temp_file.write_text("Content")

    # Rename to have .txt extension
    txt_file = temp_file.with_suffix('.txt')
    temp_file.rename(txt_file)

    is_valid, error = validate_file_exists(str(txt_file), ['.txt'])

    assert is_valid is True
    assert error == ""


@pytest.mark.unit
@pytest.mark.client
def test_validate_file_exists_with_invalid_extension(temp_file):
    """
    Test validation with wrong extension.

    Given: File with .txt extension
    When: validate_file_exists is called with ['.xlsx'] extensions
    Then: (False, error_message) is returned
    """
    temp_file.write_text("Content")

    is_valid, error = validate_file_exists(str(temp_file), ['.xlsx', '.xls'])

    assert is_valid is False
    assert "invalid file type" in error.lower()


@pytest.mark.unit
@pytest.mark.client
def test_validate_file_exists_multiple_extensions(temp_dir):
    """
    Test validation with multiple allowed extensions.

    Given: File with .txt extension
    When: validate_file_exists is called with ['.txt', '.md']
    Then: (True, "") is returned
    """
    txt_file = temp_dir / "test_file.txt"
    txt_file.write_text("Content")

    is_valid, error = validate_file_exists(str(txt_file), ['.txt', '.md', '.rst'])

    assert is_valid is True
    assert error == ""


@pytest.mark.unit
@pytest.mark.client
def test_validate_file_exists_case_insensitive_extension(temp_dir):
    """
    Test that extension validation is case insensitive.

    Given: File with .TXT extension
    When: validate_file_exists is called with ['.txt']
    Then: (True, "") is returned
    """
    txt_file = temp_dir / "test_file.TXT"
    txt_file.write_text("Content")

    is_valid, error = validate_file_exists(str(txt_file), ['.txt'])

    assert is_valid is True


@pytest.mark.unit
@pytest.mark.client
def test_validate_file_exists_empty_path():
    """
    Test validation with empty path.

    Given: Empty string as path
    When: validate_file_exists is called
    Then: (False, error_message) is returned
    """
    is_valid, error = validate_file_exists("")

    assert is_valid is False
    assert "no file path" in error.lower()


@pytest.mark.unit
@pytest.mark.client
def test_validate_file_exists_directory_not_file(temp_dir):
    """
    Test validation fails for directory.

    Given: A directory path
    When: validate_file_exists is called
    Then: (False, error_message) is returned
    """
    is_valid, error = validate_file_exists(str(temp_dir))

    assert is_valid is False
    assert "not a file" in error.lower()


# ============================================
# Safe Filename Tests
# ============================================

@pytest.mark.unit
@pytest.mark.client
def test_get_safe_filename_removes_unsafe_chars():
    """
    Test that unsafe characters are removed.

    Given: Filename with unsafe characters
    When: get_safe_filename is called
    Then: Unsafe characters are replaced
    """
    unsafe_name = "file<name>with:bad|chars?.txt"

    safe_name = get_safe_filename(unsafe_name)

    assert '<' not in safe_name
    assert '>' not in safe_name
    assert ':' not in safe_name
    assert '|' not in safe_name
    assert '?' not in safe_name


@pytest.mark.unit
@pytest.mark.client
def test_get_safe_filename_preserves_safe_chars():
    """
    Test that safe characters are preserved.

    Given: Filename with safe characters
    When: get_safe_filename is called
    Then: Filename is unchanged
    """
    safe_name_input = "my_file-name_123.txt"

    safe_name = get_safe_filename(safe_name_input)

    assert safe_name == safe_name_input


@pytest.mark.unit
@pytest.mark.client
def test_get_safe_filename_strips_leading_trailing():
    """
    Test that leading/trailing spaces and dots are removed.

    Given: Filename with leading/trailing spaces and dots
    When: get_safe_filename is called
    Then: Spaces and dots are stripped
    """
    unsafe_name = "  ..filename.txt..  "

    safe_name = get_safe_filename(unsafe_name)

    assert not safe_name.startswith(' ')
    assert not safe_name.startswith('.')
    assert not safe_name.endswith(' ')
    assert not safe_name.endswith('.')


@pytest.mark.unit
@pytest.mark.client
def test_get_safe_filename_truncates_long_names():
    """
    Test that very long filenames are truncated.

    Given: Filename longer than max_length
    When: get_safe_filename is called with max_length
    Then: Filename is truncated
    """
    long_name = "a" * 300 + ".txt"

    safe_name = get_safe_filename(long_name, max_length=50)

    assert len(safe_name) <= 50


@pytest.mark.unit
@pytest.mark.client
def test_get_safe_filename_preserves_extension_when_truncating():
    """
    Test that extension is preserved when truncating.

    Given: Long filename with extension
    When: get_safe_filename truncates
    Then: Extension is kept
    """
    long_name = "a" * 300 + ".xlsx"

    safe_name = get_safe_filename(long_name, max_length=50)

    assert safe_name.endswith(".xlsx")


# ============================================
# Count Files Tests
# ============================================

@pytest.mark.unit
@pytest.mark.client
def test_count_files_in_directory_all_files(temp_dir):
    """
    Test counting all files in directory.

    Given: Directory with multiple files
    When: count_files_in_directory is called
    Then: Correct count is returned
    """
    # Create test files
    (temp_dir / "file1.txt").write_text("1")
    (temp_dir / "file2.txt").write_text("2")
    (temp_dir / "file3.xlsx").write_text("3")

    count = count_files_in_directory(str(temp_dir), pattern="*")

    assert count == 3


@pytest.mark.unit
@pytest.mark.client
def test_count_files_in_directory_with_pattern(temp_dir):
    """
    Test counting files with specific pattern.

    Given: Directory with mixed file types
    When: count_files_in_directory is called with pattern
    Then: Only matching files are counted
    """
    (temp_dir / "file1.txt").write_text("1")
    (temp_dir / "file2.txt").write_text("2")
    (temp_dir / "file3.xlsx").write_text("3")

    count = count_files_in_directory(str(temp_dir), pattern="*.txt")

    assert count == 2


@pytest.mark.unit
@pytest.mark.client
def test_count_files_in_directory_nonexistent():
    """
    Test counting files in nonexistent directory.

    Given: Path to nonexistent directory
    When: count_files_in_directory is called
    Then: 0 is returned
    """
    count = count_files_in_directory("/nonexistent/directory", pattern="*")

    assert count == 0


@pytest.mark.unit
@pytest.mark.client
def test_count_files_in_directory_empty(temp_dir):
    """
    Test counting files in empty directory.

    Given: Empty directory
    When: count_files_in_directory is called
    Then: 0 is returned
    """
    count = count_files_in_directory(str(temp_dir), pattern="*")

    assert count == 0


# ============================================
# TempFileManager Tests
# ============================================

@pytest.mark.unit
@pytest.mark.client
def test_temp_file_manager_creates_temp_copy(temp_dir):
    """
    Test that TempFileManager creates temp copies.

    Given: Original file
    When: create_temp_copy is called via manager
    Then: Temp copy is created and tracked
    """
    original = temp_dir / "original.txt"
    original.write_text("Content")

    with TempFileManager() as temp_mgr:
        temp_copy = temp_mgr.create_temp_copy(str(original))

        assert Path(temp_copy).exists()
        assert len(temp_mgr.temp_files) == 1


@pytest.mark.unit
@pytest.mark.client
def test_temp_file_manager_cleans_up_on_exit(temp_dir):
    """
    Test that TempFileManager cleans up temp files on exit.

    Given: Temp files created via manager
    When: Context manager exits
    Then: Temp files are deleted
    """
    original = temp_dir / "original.txt"
    original.write_text("Content")

    temp_path = None

    with TempFileManager() as temp_mgr:
        temp_path = temp_mgr.create_temp_copy(str(original))
        assert Path(temp_path).exists()

    # After exit, temp file should be deleted
    assert not Path(temp_path).exists()


@pytest.mark.unit
@pytest.mark.client
def test_temp_file_manager_cleans_up_multiple_files(temp_dir):
    """
    Test that TempFileManager cleans up multiple temp files.

    Given: Multiple temp files created
    When: Context manager exits
    Then: All temp files are deleted
    """
    files = []
    for i in range(3):
        file = temp_dir / f"file_{i}.txt"
        file.write_text(f"Content {i}")
        files.append(file)

    temp_paths = []

    with TempFileManager() as temp_mgr:
        for file in files:
            temp_path = temp_mgr.create_temp_copy(str(file))
            temp_paths.append(temp_path)

        # All should exist
        for temp_path in temp_paths:
            assert Path(temp_path).exists()

    # After exit, all should be deleted
    for temp_path in temp_paths:
        assert not Path(temp_path).exists()


@pytest.mark.unit
@pytest.mark.client
def test_temp_file_manager_cleans_up_on_exception(temp_dir):
    """
    Test that TempFileManager cleans up even if exception occurs.

    Given: Temp files created, then exception raised
    When: Context manager exits due to exception
    Then: Temp files are still cleaned up
    """
    original = temp_dir / "original.txt"
    original.write_text("Content")

    temp_path = None

    try:
        with TempFileManager() as temp_mgr:
            temp_path = temp_mgr.create_temp_copy(str(original))
            assert Path(temp_path).exists()
            raise ValueError("Test exception")
    except ValueError:
        pass

    # Temp file should still be cleaned up despite exception
    assert not Path(temp_path).exists()


@pytest.mark.unit
@pytest.mark.client
def test_temp_file_manager_manual_cleanup(temp_dir):
    """
    Test that manual cleanup works.

    Given: TempFileManager with temp files
    When: cleanup() is called manually
    Then: Temp files are deleted
    """
    original = temp_dir / "original.txt"
    original.write_text("Content")

    temp_mgr = TempFileManager()
    temp_path = temp_mgr.create_temp_copy(str(original))

    assert Path(temp_path).exists()

    temp_mgr.cleanup()

    assert not Path(temp_path).exists()
    assert len(temp_mgr.temp_files) == 0


# ============================================
# Integration Tests
# ============================================

@pytest.mark.unit
@pytest.mark.client
def test_complete_file_processing_workflow(temp_dir):
    """
    Test complete file processing workflow using utilities.

    Given: An input file to process
    When: File is validated, copied, processed, and output created
    Then: All steps complete successfully
    """
    # Step 1: Create input file
    input_file = temp_dir / "input.xlsx"
    input_file.write_text("Original data")

    # Step 2: Validate
    is_valid, error = validate_file_exists(str(input_file), ['.xlsx'])
    assert is_valid is True

    # Step 3: Get file info
    size_mb = get_file_size_mb(str(input_file))
    file_hash = get_file_hash(str(input_file))
    assert size_mb >= 0
    assert len(file_hash) > 0

    # Step 4: Create temp copy for processing
    with TempFileManager() as temp_mgr:
        temp_copy = temp_mgr.create_temp_copy(str(input_file))
        assert Path(temp_copy).exists()

        # Simulate processing (modify temp file)
        Path(temp_copy).write_text("Processed data")

        # Step 5: Create output path
        output_path = ensure_output_path(str(input_file), "_processed")

        # Step 6: Move temp to output
        shutil.move(temp_copy, output_path)
        assert Path(output_path).exists()

    # Verify temp was cleaned (already moved, so won't exist anyway)
    assert Path(output_path).exists()
    assert Path(output_path).read_text() == "Processed data"
