"""
QuickSearch Parser - XML/TXT/TSV file parsing

Parses game translation files in various formats and extracts
Korean-Translation pairs with StringIDs.
"""

import xml.etree.ElementTree as ET
import pandas as pd
import csv
import os
import re
from typing import Tuple, Dict, List
from loguru import logger

# Factor Power: Use centralized text utils
from server.utils.text_utils import normalize_text


def tokenize(text: str) -> List[str]:
    """
    Tokenize text by newlines (EXACT COPY from original QuickSearch0818.py).

    Preserves original logic:
    - Check for string type and non-empty
    - Check for no tabs (returns empty if tabs present)
    - Split by \\n or \n

    Args:
        text: Text to tokenize

    Returns:
        List of tokens
    """
    if isinstance(text, str) and text.strip() != '' and '\t' not in text:
        return re.split(r'\\?\n|\n', text)
    else:
        return []


def parse_xml_file(xml_path: str) -> Tuple[List, List, List, List]:
    """
    Parse XML file and extract translation pairs.

    Args:
        xml_path: Path to XML file

    Returns:
        Tuple of (korean_lines_split, translation_lines_split,
                 korean_lines_whole, translation_lines_whole)
    """
    korean_lines_split = []
    translation_lines_split = []
    korean_lines_whole = []
    translation_lines_whole = []
    string_keys_split = []
    string_keys_whole = []

    try:
        tree = ET.parse(xml_path)
        root_el = tree.getroot()
    except Exception as e:
        logger.error(f"Failed to parse XML file {xml_path}: {e}")
        return korean_lines_split, translation_lines_split, korean_lines_whole, translation_lines_whole

    for loc in root_el.findall('LocStr'):
        korean = normalize_text(loc.get('StrOrigin', '') or '')
        translation = normalize_text(loc.get('Str', '') or '')
        string_id = loc.get('StringId', '') or ''

        if not korean or not translation:
            continue

        korean_tokens = tokenize(korean)
        translation_tokens = tokenize(translation)

        # If token counts match and both have tokens, use split mode
        if korean_tokens and len(korean_tokens) == len(translation_tokens):
            for k_tok, t_tok in zip(korean_tokens, translation_tokens):
                korean_lines_split.append(k_tok)
                translation_lines_split.append(t_tok)
                string_keys_split.append((k_tok, string_id))
        else:
            # Otherwise use whole mode
            korean_lines_whole.append(korean)
            translation_lines_whole.append(translation)
            string_keys_whole.append((korean, string_id))

    return (korean_lines_split, translation_lines_split, string_keys_split,
            korean_lines_whole, translation_lines_whole, string_keys_whole)


def parse_txt_file(txt_path: str) -> Tuple[List, List, List, List]:
    """
    Parse TXT/TSV file and extract translation pairs.

    TXT format: Tab-delimited with columns [0-6], where:
    - Columns 0-4: StringID components
    - Column 5: Korean text
    - Column 6: Translation text

    Args:
        txt_path: Path to TXT/TSV file

    Returns:
        Tuple of (korean_lines_split, translation_lines_split,
                 korean_lines_whole, translation_lines_whole)
    """
    korean_lines_split = []
    translation_lines_split = []
    korean_lines_whole = []
    translation_lines_whole = []
    string_keys_split = []
    string_keys_whole = []

    try:
        df = pd.read_csv(
            txt_path,
            delimiter="\t",
            header=None,
            usecols=range(7),
            dtype=str,
            quoting=csv.QUOTE_NONE,
            quotechar=None,
            escapechar=None,
            on_bad_lines='skip'  # Skip lines with wrong column count
        )
    except Exception as e:
        logger.error(f"Failed to read TXT file {txt_path}: {e}")
        # Return 6 empty lists to match successful return signature
        return (korean_lines_split, translation_lines_split, string_keys_split,
                korean_lines_whole, translation_lines_whole, string_keys_whole)

    for row_idx, row in df.iterrows():
        korean_text = normalize_text(row[5] or "")
        translation_text = normalize_text(row[6] or "")

        # Build StringID with normal spaces
        str_key = " ".join(str(x).strip() if x is not None else '' for x in row[0:5])

        if not korean_text or not translation_text:
            continue

        korean_tokens = tokenize(korean_text)
        translation_tokens = tokenize(translation_text)

        # If token counts match and both have tokens, use split mode
        if korean_tokens and len(korean_tokens) == len(translation_tokens):
            for k_tok, t_tok in zip(korean_tokens, translation_tokens):
                korean_lines_split.append(k_tok)
                translation_lines_split.append(t_tok)
                string_keys_split.append((k_tok, str_key))
        else:
            # Otherwise use whole mode
            korean_lines_whole.append(korean_text)
            translation_lines_whole.append(translation_text)
            string_keys_whole.append((korean_text, str_key))

    return (korean_lines_split, translation_lines_split, string_keys_split,
            korean_lines_whole, translation_lines_whole, string_keys_whole)


def process_files(file_paths: List[str]) -> Tuple[Dict, Dict, Dict, Dict]:
    """
    Process multiple XML/TXT/TSV files and build dictionaries.

    Args:
        file_paths: List of file paths to process

    Returns:
        Tuple of (split_dict, whole_dict, string_keys, stringid_to_entry)

    Dictionary format:
        split_dict: {korean_text: [(translation, string_id), ...]}
        whole_dict: {korean_text: [(translation, string_id), ...]}
        string_keys: {'split': [(korean, string_id), ...], 'whole': [(korean, string_id), ...]}
        stringid_to_entry: {string_id: (korean, translation)}
    """
    split_dict = {}
    whole_dict = {}
    stringid_to_entry = {}
    string_keys_split = []
    string_keys_whole = []

    if not file_paths:
        logger.warning("No files provided for processing")
        return split_dict, whole_dict, {}, stringid_to_entry

    # Detect file type from first file
    first_ext = os.path.splitext(file_paths[0])[1].lower()
    is_xml = first_ext == ".xml"
    is_txt = first_ext in (".txt", ".tsv")

    if not (is_xml or is_txt):
        logger.error(f"Unsupported file type: {first_ext}")
        return split_dict, whole_dict, {}, stringid_to_entry

    logger.info(f"Processing {len(file_paths)} {'XML' if is_xml else 'TXT'} files")

    # Process each file
    for idx, file_path in enumerate(file_paths, start=1):
        logger.info(f"Processing file {idx}/{len(file_paths)}: {os.path.basename(file_path)}")

        if is_xml:
            k_split, t_split, keys_split, k_whole, t_whole, keys_whole = parse_xml_file(file_path)
        else:
            k_split, t_split, keys_split, k_whole, t_whole, keys_whole = parse_txt_file(file_path)

        # Build split_dict and string_keys_split
        for k, t, key_data in zip(k_split, t_split, keys_split):
            split_dict.setdefault(k, []).append((t, key_data[1]))
            string_keys_split.append(key_data)  # Preserve original format: (korean, string_id)
            if key_data[1]:
                stringid_to_entry[key_data[1]] = (k, t)

        # Build whole_dict and string_keys_whole
        for k, t, key_data in zip(k_whole, t_whole, keys_whole):
            whole_dict.setdefault(k, []).append((t, key_data[1]))
            string_keys_whole.append(key_data)  # Preserve original format: (korean, string_id)
            if key_data[1]:
                stringid_to_entry[key_data[1]] = (k, t)

    # Build string_keys dict in original format
    string_keys = {'split': string_keys_split, 'whole': string_keys_whole}

    logger.success(f"Processed {len(file_paths)} files: {len(split_dict)} split pairs, {len(whole_dict)} whole pairs")

    return split_dict, whole_dict, string_keys, stringid_to_entry
