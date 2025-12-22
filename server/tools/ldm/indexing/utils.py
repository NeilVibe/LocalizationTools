"""
Indexing utilities - Text normalization for TM indexing.

Extracted from tm_indexer.py during P37 refactoring.
"""


def normalize_newlines_universal(text: str) -> str:
    """
    Universal newline normalization for ALL formats.

    Handles:
    - \\n (escaped newlines in TEXT files)
    - \r\n, \r (Windows/Mac line endings)
    - <br/>, <br /> (XML unescaped)
    - &lt;br/&gt;, &lt;br /&gt; (XML escaped)

    All converted to canonical \n for consistent matching.
    """
    if not text:
        return text

    # 1. Escaped \\n → \n (TEXT files store as literal backslash-n)
    text = text.replace('\\n', '\n')

    # 2. XML <br/> variants → \n
    text = text.replace('<br/>', '\n')
    text = text.replace('<br />', '\n')
    text = text.replace('<BR/>', '\n')
    text = text.replace('<BR />', '\n')

    # 3. HTML-escaped &lt;br/&gt; variants → \n
    text = text.replace('&lt;br/&gt;', '\n')
    text = text.replace('&lt;br /&gt;', '\n')
    text = text.replace('&LT;BR/&GT;', '\n')
    text = text.replace('&LT;BR /&GT;', '\n')

    # 4. Windows/Mac line endings → \n
    text = text.replace('\r\n', '\n')
    text = text.replace('\r', '\n')

    return text


def normalize_for_hash(text: str) -> str:
    """
    Normalize text for hash-based lookup.
    Handles newlines, whitespace, case.
    """
    if not text:
        return ""
    # Universal newline normalization first
    text = normalize_newlines_universal(text)
    # Lowercase for case-insensitive matching
    text = text.lower()
    # Normalize whitespace but preserve structure
    lines = [' '.join(line.split()) for line in text.split('\n')]
    return '\n'.join(lines)


def normalize_for_embedding(text: str) -> str:
    """
    Normalize text for embedding generation.
    Less aggressive than hash normalization.
    """
    if not text:
        return ""
    # Universal newline normalization
    text = normalize_newlines_universal(text)
    # Basic whitespace cleanup
    return ' '.join(text.split())
