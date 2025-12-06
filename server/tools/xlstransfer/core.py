"""
XLSTransfer Core Utilities

Text processing, column conversion, and code pattern handling.
CLEAN, modular functions extracted from original XLSTransfer script.
"""

from typing import Optional, Dict, Set, Tuple, List, Any
import re

from server.tools.xlstransfer import config


# ============================================
# Text Cleaning
# ============================================

def clean_text(text: Optional[Any]) -> Optional[str]:
    """
    Clean text by removing carriage return characters.

    Args:
        text: Input text (can be None, str, or other type)

    Returns:
        Cleaned text string, or None if input is None

    Example:
        >>> clean_text("Hello_x000D_World")
        'HelloWorld'
        >>> clean_text(None)
        None
        >>> clean_text(123)
        '123'
    """
    if text is None:
        return None

    # Convert to string if not already
    if not isinstance(text, str):
        text = str(text)

    # Remove carriage return characters
    if config.REMOVE_CARRIAGE_RETURN:
        text = text.replace('_x000D_', '')

    # Strip whitespace if configured
    if config.STRIP_WHITESPACE:
        text = text.strip()

    return text


# ============================================
# Column Conversion
# ============================================

def excel_column_to_index(column_letter: str) -> int:
    """
    Convert Excel column letter to zero-based index.

    Args:
        column_letter: Column letter (e.g., 'A', 'B', 'AA')

    Returns:
        Zero-based column index

    Example:
        >>> excel_column_to_index('A')
        0
        >>> excel_column_to_index('B')
        1
        >>> excel_column_to_index('Z')
        25
    """
    return ord(column_letter.upper()) - ord('A')


def index_to_excel_column(index: int) -> str:
    """
    Convert zero-based index to Excel column letter.

    Args:
        index: Zero-based column index

    Returns:
        Column letter (e.g., 'A', 'B', 'AA')

    Example:
        >>> index_to_excel_column(0)
        'A'
        >>> index_to_excel_column(1)
        'B'
        >>> index_to_excel_column(25)
        'Z'
    """
    return chr(ord('A') + index)


# ============================================
# Cell Value Conversion
# ============================================

def convert_cell_value(value: Any) -> Any:
    """
    Convert string numbers to actual numbers for Excel cells.

    Args:
        value: Cell value (any type)

    Returns:
        Float if value is a numeric string, otherwise original value

    Example:
        >>> convert_cell_value("123.45")
        123.45
        >>> convert_cell_value("Hello")
        'Hello'
        >>> convert_cell_value(42)
        42
    """
    if isinstance(value, str):
        # Try to convert string numbers to actual numbers
        try:
            # Check if it's a pure number string
            float(value)
            return float(value)
        except ValueError:
            # If conversion fails, it's not a pure number, keep as string
            return value
    return value


# ============================================
# Code Pattern Detection
# ============================================

def analyze_code_patterns(text: str) -> Dict[str, Any]:
    """
    Analyze and extract game code patterns from text.

    Detects patterns like {Code}, <PAColor>, etc. and their relationships.

    Args:
        text: Text to analyze

    Returns:
        Dictionary with:
            - 'start_codes': Set of codes that appear at the start
            - 'next_levels': Dict mapping code sequences to next codes

    Example:
        >>> text = "{Code1}{Code2}Hello<PAColor>World<PAOldColor>"
        >>> patterns = analyze_code_patterns(text)
        >>> '{Code1}' in patterns['start_codes']
        True
    """
    patterns = {
        'start_codes': set(),
        'next_levels': {}  # Stores code relationships for any level depth
    }

    current_pos = 0

    while current_pos < len(text):
        if text[current_pos] == '{' or text[current_pos:].startswith("<PAColor"):
            # Process consecutive code blocks
            code_positions = []  # Store positions of all code blocks

            while current_pos < len(text):
                if text[current_pos] == '{' or text[current_pos:].startswith("<PAColor"):
                    code_start = current_pos
                    if text[current_pos:].startswith("<PAColor"):
                        code_end = text.find(">", current_pos) + 1
                    else:
                        code_end = text.find("}", current_pos) + 1

                    if code_end > code_start:
                        code = text[code_start:code_end].split('(')[0]
                        code_positions.append((code, code_start, code_end))
                        current_pos = code_end
                    else:
                        current_pos += 1
                else:
                    # Move past any punctuation or other characters
                    current_pos += 1
                    break

            # Add codes to patterns
            if code_positions:
                first_code, _, _ = code_positions[0]
                patterns['start_codes'].add(first_code)

                # Process relationships between codes
                for i in range(len(code_positions) - 1):
                    current_code, _, _ = code_positions[i]
                    next_code, _, _ = code_positions[i+1]

                    key = tuple(cp[0] for cp in code_positions[:i+1])

                    if key not in patterns['next_levels']:
                        patterns['next_levels'][key] = set()
                    patterns['next_levels'][key].add(next_code)
        else:
            current_pos += 1

    return patterns


def extract_code_blocks(text: str) -> List[str]:
    """
    Extract all code blocks from text.

    Args:
        text: Text containing code blocks

    Returns:
        List of code blocks in order

    Example:
        >>> extract_code_blocks("{Code1}{Code2}Hello")
        ['{Code1}', '{Code2}']
        >>> extract_code_blocks("<PAColor>World<PAOldColor>")
        ['<PAColor>']
    """
    if not isinstance(text, str):
        return []

    codes = []
    current_pos = 0

    while current_pos < len(text):
        if text[current_pos:].startswith("<PAColor"):
            end_pos = text.find(">", current_pos)
            if end_pos != -1:
                codes.append(text[current_pos:end_pos+1])
                current_pos = end_pos + 1
            else:
                break
        elif text[current_pos] == '{':
            end_pos = text.find("}", current_pos)
            if end_pos != -1:
                codes.append(text[current_pos:end_pos+1])
                current_pos = end_pos + 1
            else:
                break
        else:
            break

    return codes


def simple_number_replace(original: str, translated: str) -> str:
    """
    Preserve code blocks from original text when replacing with translation.

    CRITICAL: This function preserves game codes like {ItemID:123} and <PAColor> tags.
    Must match original XLSTransfer0225.py implementation EXACTLY.

    Args:
        original: Original text with code blocks
        translated: Translated text (without code blocks)

    Returns:
        Translated text with code blocks preserved

    Example:
        >>> simple_number_replace("{Code}Hello", "World")
        '{Code}World'
        >>> simple_number_replace("<PAColor>Hi<PAOldColor>", "Bye")
        '<PAColor>Bye<PAOldColor>'
    """
    if not isinstance(original, str):
        return translated

    # Handle text + code(s) case (codes in middle of text)
    first_code_start = original.find("{")
    if first_code_start > 0 or original.startswith("<PAColor"):
        codes = []
        current_pos = first_code_start if first_code_start > 0 else 0

        while current_pos < len(original):
            if original[current_pos:].startswith("<PAColor"):
                end_pos = original.find(">", current_pos)
                if end_pos != -1:
                    codes.append(original[current_pos:end_pos+1])
                    current_pos = end_pos + 1
                else:
                    break
            elif original[current_pos] == '{':
                end_pos = original.find("}", current_pos)
                if end_pos != -1:
                    codes.append(original[current_pos:end_pos+1])
                    current_pos = end_pos + 1
                else:
                    break
            else:
                break

        if codes:
            return ''.join(codes) + translated

    # Extract only code blocks at the beginning (without punctuation)
    prefix = ""
    pos = 0

    while pos < len(original):
        if original[pos:].startswith("<PAColor") or original[pos] == '{':
            if original[pos:].startswith("<PAColor"):
                end_pos = original.find(">", pos) + 1
            else:
                end_pos = original.find("}", pos) + 1
            if end_pos > pos:
                prefix += original[pos:end_pos]
                pos = end_pos
            else:
                break
        else:
            # Stop as soon as we encounter anything that's not a code block
            break

    if prefix:
        result = prefix + translated
        if original.endswith("<PAOldColor>"):
            result += "<PAOldColor>"
        return result

    # Handle PAOldColor ending
    if original.endswith("<PAOldColor>"):
        translated += "<PAOldColor>"

    return translated


# ============================================
# Pattern Matching
# ============================================

def find_code_patterns_in_text(text: str) -> List[str]:
    """
    Find all code patterns matching configured patterns.

    Args:
        text: Text to search

    Returns:
        List of matched code patterns

    Example:
        >>> text = "{ItemID}Get {Amount} coins"
        >>> find_code_patterns_in_text(text)
        ['{ItemID}', '{Amount}']
    """
    matches = []

    for pattern in config.CODE_PATTERNS:
        found = re.findall(pattern, text)
        matches.extend(found)

    return matches


def strip_codes_from_text(text: str) -> str:
    """
    Remove all code patterns from text.

    Args:
        text: Text with code patterns

    Returns:
        Text with code patterns removed

    Example:
        >>> strip_codes_from_text("{Code}Hello World")
        'Hello World'
        >>> strip_codes_from_text("<PAColor>Test<PAOldColor>")
        'Test'
    """
    if not isinstance(text, str):
        return text

    result = text

    # Remove all code patterns
    for pattern in config.CODE_PATTERNS:
        result = re.sub(pattern, '', result)

    # Remove closing color tag
    result = result.replace('<PAOldColor>', '')

    # Clean up extra whitespace
    result = ' '.join(result.split())

    return result


# ============================================
# Newline Handling
# ============================================

def count_newlines(text: str) -> int:
    """
    Count the number of newline characters in text.
    MONOLITH LINE 822-823: Only counts literal \\n, NOT escaped \\\\n

    Args:
        text: Text to count newlines in

    Returns:
        Number of literal newlines

    Example:
        >>> count_newlines("Hello\\nWorld\\nTest")
        2
        >>> count_newlines("Single line")
        0
    """
    if not isinstance(text, str):
        return 0

    # MONOLITH: Only count literal newlines (line 822)
    # str(cell1).count('\n')
    return text.count('\n')


def normalize_newlines(text: str) -> str:
    """
    Normalize newlines to escaped format.

    Args:
        text: Text with various newline formats

    Returns:
        Text with normalized newlines

    Example:
        >>> normalize_newlines("Hello\\nWorld")
        'Hello\\\\nWorld'
    """
    if not isinstance(text, str):
        return text

    # Replace literal newlines with escaped format
    result = text.replace('\n', config.NEWLINE_ESCAPE)

    return result


# Example usage
if __name__ == "__main__":
    # Test text cleaning
    print("Text Cleaning:")
    print(clean_text("Hello_x000D_World"))

    # Test column conversion
    print("\nColumn Conversion:")
    print(f"A -> {excel_column_to_index('A')}")
    print(f"0 -> {index_to_excel_column(0)}")

    # Test code pattern detection
    print("\nCode Pattern Detection:")
    text = "{ItemID}Get {Amount} coins<PAColor>blue<PAOldColor>"
    patterns = analyze_code_patterns(text)
    print(f"Start codes: {patterns['start_codes']}")

    # Test code preservation
    print("\nCode Preservation:")
    result = simple_number_replace("{Code}Hello", "World")
    print(f"{result}")
