"""
TextBatchProcessor Core Functions

Simple, clean functions for batch text file processing.
"""

from typing import List, Dict, Tuple
from pathlib import Path
import re
from loguru import logger


def find_and_replace(
    file_paths: List[str],
    find_pattern: str,
    replace_text: str,
    use_regex: bool = False,
    output_dir: str = None
) -> Dict[str, str]:
    """
    Find and replace text patterns in multiple files.

    Args:
        file_paths: List of file paths to process
        find_pattern: Text or regex pattern to find
        replace_text: Replacement text
        use_regex: Whether to use regex matching
        output_dir: Output directory (defaults to same as input)

    Returns:
        Dict mapping original file path to output file path

    Example:
        >>> result = find_and_replace(
        ...     ['/path/to/file.txt'],
        ...     'Hello',
        ...     'Hi',
        ...     use_regex=False
        ... )
        >>> result
        {'/path/to/file.txt': '/path/to/file_replaced.txt'}
    """
    logger.info(f"Find and replace in {len(file_paths)} files")
    logger.info(f"Pattern: {find_pattern} → {replace_text}")

    results = {}

    for file_path in file_paths:
        file_path = Path(file_path)

        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            continue

        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace
        if use_regex:
            new_content = re.sub(find_pattern, replace_text, content)
        else:
            new_content = content.replace(find_pattern, replace_text)

        # Determine output path
        if output_dir:
            output_path = Path(output_dir) / f"{file_path.stem}_replaced{file_path.suffix}"
        else:
            output_path = file_path.parent / f"{file_path.stem}_replaced{file_path.suffix}"

        # Write output
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        results[str(file_path)] = str(output_path)
        logger.info(f"Processed: {file_path.name} → {output_path.name}")

    logger.info(f"Find and replace complete: {len(results)} files processed")
    return results


def extract_unique_strings(
    file_paths: List[str],
    output_path: str = None,
    sort_alphabetically: bool = True
) -> Tuple[List[str], str]:
    """
    Extract all unique lines from multiple files.

    Args:
        file_paths: List of file paths to process
        output_path: Output file path (optional)
        sort_alphabetically: Whether to sort the results

    Returns:
        Tuple of (unique_strings, output_file_path)

    Example:
        >>> strings, output = extract_unique_strings(
        ...     ['/path/to/file1.txt', '/path/to/file2.txt']
        ... )
        >>> len(strings)
        150
    """
    logger.info(f"Extracting unique strings from {len(file_paths)} files")

    unique_strings = set()

    for file_path in file_paths:
        file_path = Path(file_path)

        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            continue

        # Read file and extract lines
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Add non-empty lines to set
        for line in lines:
            line = line.strip()
            if line:
                unique_strings.add(line)

    # Convert to sorted list
    unique_list = list(unique_strings)
    if sort_alphabetically:
        unique_list.sort()

    # Determine output path
    if not output_path:
        output_path = Path(file_paths[0]).parent / "unique_strings.txt"
    else:
        output_path = Path(output_path)

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(unique_list))

    logger.info(f"Extracted {len(unique_list)} unique strings → {output_path}")
    return unique_list, str(output_path)


def combine_files(
    file_paths: List[str],
    output_path: str = None,
    separator: str = "\n"
) -> Tuple[str, int]:
    """
    Combine multiple text files into one.

    Args:
        file_paths: List of file paths to combine
        output_path: Output file path (optional)
        separator: Separator between files

    Returns:
        Tuple of (output_file_path, total_lines)

    Example:
        >>> output, lines = combine_files(
        ...     ['/path/to/file1.txt', '/path/to/file2.txt'],
        ...     separator='\\n---\\n'
        ... )
        >>> lines
        500
    """
    logger.info(f"Combining {len(file_paths)} files")

    combined_content = []

    for file_path in file_paths:
        file_path = Path(file_path)

        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            continue

        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        combined_content.append(content)

    # Join with separator
    final_content = separator.join(combined_content)

    # Determine output path
    if not output_path:
        output_path = Path(file_paths[0]).parent / "combined.txt"
    else:
        output_path = Path(output_path)

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_content)

    total_lines = final_content.count('\n') + 1
    logger.info(f"Combined {len(file_paths)} files → {output_path} ({total_lines} lines)")

    return str(output_path), total_lines


def get_word_count_stats(file_paths: List[str]) -> Dict[str, Dict[str, int]]:
    """
    Get word count statistics for multiple files.

    Args:
        file_paths: List of file paths to analyze

    Returns:
        Dict mapping file path to statistics

    Example:
        >>> stats = get_word_count_stats(['/path/to/file.txt'])
        >>> stats['/path/to/file.txt']
        {'words': 1000, 'characters': 5000, 'lines': 50}
    """
    logger.info(f"Analyzing {len(file_paths)} files")

    stats = {}

    for file_path in file_paths:
        file_path = Path(file_path)

        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            continue

        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Calculate statistics
        words = len(content.split())
        characters = len(content)
        characters_no_spaces = len(content.replace(' ', '').replace('\n', '').replace('\t', ''))
        lines = content.count('\n') + 1

        stats[str(file_path)] = {
            'words': words,
            'characters': characters,
            'characters_no_spaces': characters_no_spaces,
            'lines': lines
        }

        logger.info(f"{file_path.name}: {words} words, {characters} chars, {lines} lines")

    return stats


def split_by_delimiter(
    file_path: str,
    delimiter: str = "\n\n",
    output_dir: str = None,
    prefix: str = "part"
) -> List[str]:
    """
    Split a file by delimiter into multiple files.

    Args:
        file_path: File path to split
        delimiter: Delimiter to split by (default: double newline)
        output_dir: Output directory (optional)
        prefix: Prefix for output files

    Returns:
        List of output file paths

    Example:
        >>> parts = split_by_delimiter(
        ...     '/path/to/file.txt',
        ...     delimiter='---'
        ... )
        >>> len(parts)
        5
    """
    logger.info(f"Splitting file by delimiter: {repr(delimiter)}")

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Read file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by delimiter
    parts = content.split(delimiter)

    # Determine output directory
    if not output_dir:
        output_dir = file_path.parent / f"{file_path.stem}_parts"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Write parts
    output_paths = []
    for i, part in enumerate(parts, 1):
        if not part.strip():  # Skip empty parts
            continue

        output_path = output_dir / f"{prefix}_{i:03d}.txt"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(part)

        output_paths.append(str(output_path))

    logger.info(f"Split into {len(output_paths)} parts → {output_dir}")
    return output_paths


# Example usage
if __name__ == "__main__":
    print("TextBatchProcessor Core Functions")
    print("Available functions:")
    print("- find_and_replace()")
    print("- extract_unique_strings()")
    print("- combine_files()")
    print("- get_word_count_stats()")
    print("- split_by_delimiter()")
