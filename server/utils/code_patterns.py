"""
Code Pattern Utilities - Centralized Game Code Handling

Factor Power: Single source for code pattern preservation.
Used by: LDM pretranslation, XLSTransfer

Migrated from: server/tools/xlstransfer/core.py
"""

from typing import List, Dict, Any, Optional


def extract_code_blocks(text: str) -> List[str]:
    """
    Extract all code blocks from the start of text.

    Extracts patterns like {Code}, <PAColor>, etc.

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
    patterns: Dict[str, Any] = {
        'start_codes': set(),
        'next_levels': {}
    }

    current_pos = 0

    while current_pos < len(text):
        if text[current_pos] == '{' or text[current_pos:].startswith("<PAColor"):
            code_positions = []

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
                    current_pos += 1
                    break

            if code_positions:
                first_code, _, _ = code_positions[0]
                patterns['start_codes'].add(first_code)

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


def adapt_structure(kr_text: str, translation: str) -> str:
    """
    Adapt translation structure to match Korean text line structure.

    Used when auto-translating to maintain line breaks and formatting.

    Args:
        kr_text: Original Korean text with line breaks
        translation: Translation text to adapt

    Returns:
        Adapted translation matching Korean structure

    Migrated from: server/tools/kr_similar/core.py
    """
    import re

    kr_lines = kr_text.split('\\n')
    total_lines = len(kr_lines)
    non_empty_lines = sum(1 for line in kr_lines if line.strip())

    if not translation.strip():
        return '\\n'.join([''] * total_lines)

    ideal_length = len(translation) / non_empty_lines if non_empty_lines > 0 else len(translation)
    threshold = int(ideal_length * 1.5)

    end_punct_pattern = r'[.!?]|\.\.\.'
    all_punct_pattern = r'[.!?,;:]|\.\.\.'

    adapted_lines = []
    start = 0

    for line in kr_lines:
        if line.strip():
            if start >= len(translation):
                adapted_lines.append('')
                continue

            matches = list(re.finditer(end_punct_pattern, translation[start:start + threshold]))

            if matches:
                closest_match = min(matches, key=lambda m: abs(m.end() - ideal_length))
                end = start + closest_match.end()
            else:
                matches = list(re.finditer(all_punct_pattern, translation[start:start + threshold]))
                if matches:
                    closest_match = min(matches, key=lambda m: abs(m.end() - ideal_length))
                    end = start + closest_match.end()
                else:
                    last_space = translation.rfind(' ', start + int(ideal_length) - 10, start + int(ideal_length) + 10)
                    if last_space != -1:
                        end = last_space + 1
                    else:
                        end = start + int(ideal_length)

            if translation[end-3:end] == '...':
                end += 1

            adapted_lines.append(translation[start:end].strip())
            start = end
        else:
            adapted_lines.append('')

    if start < len(translation):
        for i in range(len(adapted_lines) - 1, -1, -1):
            if adapted_lines[i]:
                adapted_lines[i] += ' ' + translation[start:].strip()
                break

    return '\\n'.join(adapted_lines)
