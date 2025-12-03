"""
File Handling Utilities

Common file operations used across all tools.
CLEAN, reusable, with proper error handling.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple
import hashlib


def get_file_size_mb(file_path: str) -> float:
    """
    Get file size in megabytes.

    Args:
        file_path: Path to the file

    Returns:
        File size in MB (rounded to 2 decimals)
    """
    try:
        size_bytes = os.path.getsize(file_path)
        size_mb = size_bytes / (1024 * 1024)
        return round(size_mb, 2)
    except Exception:
        return 0.0


def get_file_hash(file_path: str, algorithm: str = "md5") -> str:
    """
    Calculate file hash for integrity checking.

    Args:
        file_path: Path to the file
        algorithm: Hash algorithm ('md5', 'sha256', etc.)

    Returns:
        Hex digest of the file hash
    """
    hash_func = hashlib.new(algorithm)

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)

    return hash_func.hexdigest()


def create_temp_copy(file_path: str, suffix: Optional[str] = None) -> str:
    """
    Create a temporary copy of a file.

    Args:
        file_path: Original file path
        suffix: Optional suffix for temp file (e.g., "_temp")

    Returns:
        Path to the temporary copy

    Note:
        Remember to clean up temp files after use!
    """
    file_path = Path(file_path)

    if suffix is None:
        suffix = "_temp"

    temp_name = f"{file_path.stem}{suffix}{file_path.suffix}"
    temp_path = file_path.parent / temp_name

    shutil.copy2(file_path, temp_path)
    return str(temp_path)


def safe_delete_file(file_path: str) -> bool:
    """
    Safely delete a file (no exception if doesn't exist).

    Args:
        file_path: Path to file to delete

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception:
        return False


def ensure_output_path(input_path: str, suffix: str, output_dir: Optional[str] = None) -> str:
    """
    Generate a clean output file path based on input path.

    Args:
        input_path: Original input file path
        suffix: Suffix to add (e.g., "_translated", "_processed")
        output_dir: Optional output directory (defaults to same as input)

    Returns:
        Path for the output file

    Example:
        input: "data/file.xlsx"
        suffix: "_translated"
        output: "data/file_translated.xlsx"
    """
    input_path = Path(input_path)

    output_name = f"{input_path.stem}{suffix}{input_path.suffix}"

    if output_dir:
        output_path = Path(output_dir) / output_name
    else:
        output_path = input_path.parent / output_name

    return str(output_path)


def validate_file_exists(file_path: str, extensions: Optional[List[str]] = None) -> Tuple[bool, str]:
    """
    Validate that a file exists and optionally check extension.

    Args:
        file_path: Path to validate
        extensions: Optional list of allowed extensions (e.g., ['.xlsx', '.xls'])

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        valid, error = validate_file_exists("data.xlsx", ['.xlsx', '.xls'])
        if not valid:
            print(error)
    """
    if not file_path:
        return False, "No file path provided"

    file_path = Path(file_path)

    if not file_path.exists():
        return False, f"File not found: {file_path}"

    if not file_path.is_file():
        return False, f"Path is not a file: {file_path}"

    if extensions:
        if file_path.suffix.lower() not in [ext.lower() for ext in extensions]:
            return False, f"Invalid file type. Expected: {', '.join(extensions)}"

    return True, ""


def get_safe_filename(filename: str, max_length: int = 255) -> str:
    """
    Clean a filename to make it safe for all operating systems.

    Args:
        filename: Original filename
        max_length: Maximum filename length

    Returns:
        Cleaned, safe filename

    Example:
        get_safe_filename("my/file<name>.txt") -> "my_file_name_.txt"
    """
    # Remove or replace unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    safe_name = filename

    for char in unsafe_chars:
        safe_name = safe_name.replace(char, '_')

    # Remove leading/trailing spaces and dots
    safe_name = safe_name.strip('. ')

    # Truncate if too long
    if len(safe_name) > max_length:
        name_part = Path(safe_name).stem[:max_length-10]
        ext_part = Path(safe_name).suffix
        safe_name = name_part + ext_part

    return safe_name


def count_files_in_directory(directory: str, pattern: str = "*") -> int:
    """
    Count files in a directory matching a pattern.

    Args:
        directory: Directory to search
        pattern: Glob pattern (e.g., "*.xlsx", "*.txt")

    Returns:
        Number of matching files
    """
    directory = Path(directory)
    if not directory.exists():
        return 0

    return len(list(directory.glob(pattern)))


class TempFileManager:
    """
    Context manager for handling temporary files.
    Ensures cleanup even if errors occur.

    Usage:
        with TempFileManager() as temp_mgr:
            temp_file = temp_mgr.create_temp_copy("input.xlsx")
            # Do work with temp_file
            # Automatically cleaned up on exit
    """

    def __init__(self):
        """Initialize temp file manager."""
        self.temp_files: List[str] = []

    def __enter__(self):
        """Enter context."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up all temp files on exit."""
        self.cleanup()
        return False

    def create_temp_copy(self, file_path: str) -> str:
        """Create and track a temp file."""
        temp_path = create_temp_copy(file_path)
        self.temp_files.append(temp_path)
        return temp_path

    def cleanup(self):
        """Delete all temp files."""
        for temp_file in self.temp_files:
            safe_delete_file(temp_file)
        self.temp_files.clear()


# Example usage
if __name__ == "__main__":
    # Example 1: File validation
    valid, error = validate_file_exists("test.xlsx", ['.xlsx', '.xls'])
    print(f"Valid: {valid}, Error: {error}")

    # Example 2: Safe filename
    safe_name = get_safe_filename("my<file>name?.xlsx")
    print(f"Safe filename: {safe_name}")

    # Example 3: Output path generation
    output_path = ensure_output_path("data/input.xlsx", "_processed")
    print(f"Output path: {output_path}")

    # Example 4: Temp file manager
    print("\nTemp file manager example:")
    # with TempFileManager() as temp_mgr:
    #     temp = temp_mgr.create_temp_copy("somefile.xlsx")
    #     print(f"Created temp: {temp}")
    #     # Automatically cleaned up here
