"""
XMLParsingEngine -- Centralized XML parsing with sanitization and recovery.

Ported from QuickTranslate sanitize_xml_content and QACompiler StringIdConsumer.
Provides:
- XML sanitizer (5-step pipeline for malformed game data)
- lxml parser with strict-first, recover=True fallback
- Language table discovery and parsing
- StringIdConsumer for document-order dedup
- Case-variant attribute constants and helpers
"""

from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

from loguru import logger
from lxml import etree


# =============================================================================
# Attribute Constants (case variants from real game data)
# =============================================================================

STRINGID_ATTRS: List[str] = ['StringId', 'StringID', 'stringid', 'STRINGID', 'Stringid', 'stringId']
STRORIGIN_ATTRS: List[str] = ['StrOrigin', 'strorigin', 'STRORIGIN', 'Strorigin', 'strOrigin']
STR_ATTRS: List[str] = ['Str', 'str', 'STR']
DESC_ATTRS: List[str] = ['Desc', 'desc', 'DESC']
DESCORIGIN_ATTRS: List[str] = ['DescOrigin', 'descorigin', 'DESCORIGIN', 'Descorigin', 'descOrigin']
LOCSTR_TAGS: List[str] = ['LocStr', 'locstr', 'LOCSTR', 'LOCStr', 'Locstr']


# =============================================================================
# Helpers
# =============================================================================


def get_attr(elem: etree._Element, attr_variants: List[str]) -> Optional[str]:
    """Case-variant attribute lookup. Returns first matching attribute value or None."""
    for attr in attr_variants:
        val = elem.get(attr)
        if val is not None:
            return val
    return None


def iter_locstr_elements(root: etree._Element) -> Iterator[etree._Element]:
    """Find all LocStr elements using all case variants."""
    for tag in LOCSTR_TAGS:
        yield from root.iter(tag)


# =============================================================================
# XMLParsingEngine
# =============================================================================


class XMLParsingEngine:
    """
    Centralized XML parsing engine with sanitization and recovery.

    5-step sanitizer pipeline (ported from QuickTranslate):
    1. Remove control characters
    2. Fix bare ampersands
    3. Preprocess newlines (seg handling)
    4. Fix unescaped < in attribute values
    5. Repair tag stack (unclosed tags)
    """

    # Control chars to strip (keep \t, \n, \r)
    _CONTROL_CHAR_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')

    # Bare ampersand: & not followed by a valid entity name or #
    _BARE_AMP_RE = re.compile(r'&(?!(?:amp|lt|gt|apos|quot|#\d+|#x[0-9a-fA-F]+);)')

    # Unescaped < inside attribute values
    _UNESCAPED_LT_IN_ATTR_RE = re.compile(r'(?<==")([^"]*?)<([^"]*?)(?=")')

    def sanitize(self, raw: str) -> str:
        """5-step sanitization pipeline for malformed XML."""
        text = raw

        # Step 1: Remove control characters
        text = self._CONTROL_CHAR_RE.sub('', text)

        # Step 2: Fix bare ampersands
        text = self._BARE_AMP_RE.sub('&amp;', text)

        # Step 3: Preprocess newlines (stub -- preserve as-is for now)
        text = self._preprocess_newlines(text)

        # Step 4: Fix unescaped < in attribute values
        text = self._fix_unescaped_lt_in_attrs(text)

        # Step 5: Repair tag stack (unclosed tags)
        text = self._repair_tag_stack(text)

        return text

    def _preprocess_newlines(self, text: str) -> str:
        """Preprocess newline handling. Simplified stub."""
        return text

    def _fix_unescaped_lt_in_attrs(self, text: str) -> str:
        """Fix unescaped < inside attribute values."""
        return self._UNESCAPED_LT_IN_ATTR_RE.sub(
            lambda m: m.group(1) + '&lt;' + m.group(2), text
        )

    def _repair_tag_stack(self, text: str) -> str:
        """Repair unclosed tags. Simplified stub -- lxml recover handles most cases."""
        return text

    def parse_file(self, path: Path) -> Optional[etree._Element]:
        """
        Parse XML file with strict-first, recover=True fallback.

        Returns root Element or None on total failure.
        """
        try:
            raw = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            try:
                raw = path.read_text(encoding='utf-16')
            except Exception:
                try:
                    raw = path.read_text(encoding='cp1252')
                except Exception as e:
                    logger.error(f"Cannot read {path}: {e}")
                    return None
        except Exception as e:
            logger.error(f"Cannot read {path}: {e}")
            return None

        sanitized = self.sanitize(raw)
        raw_bytes = sanitized.encode('utf-8')

        # Try strict parse first
        try:
            parser = etree.XMLParser(encoding='utf-8', huge_tree=True)
            root = etree.fromstring(raw_bytes, parser)
            return root
        except etree.XMLSyntaxError:
            pass

        # Fallback: recovery mode
        try:
            parser = etree.XMLParser(recover=True, encoding='utf-8', huge_tree=True)
            root = etree.fromstring(raw_bytes, parser)
            if root is not None:
                logger.warning(f"Parsed {path.name} with recovery mode (malformed XML)")
                return root
        except Exception:
            pass

        logger.error(f"Total parse failure for {path}")
        return None

    def parse_bytes(self, content: bytes, filename: str) -> Tuple[Optional[etree._Element], str]:
        """
        Parse XML from bytes with encoding detection.

        Returns (root, detected_encoding). Tries XML declaration encoding first,
        then cascades through common encodings.
        """
        detected_encoding = 'utf-8'
        text_content = None

        # Try to detect encoding from XML declaration
        decl_match = re.match(rb'<\?xml[^?]*encoding=["\']([^"\']+)["\']', content[:200])
        if decl_match:
            declared_enc = decl_match.group(1).decode('ascii', errors='ignore')
            try:
                text_content = content.decode(declared_enc)
                detected_encoding = declared_enc
            except (UnicodeDecodeError, LookupError):
                pass

        # Cascade through encodings
        if text_content is None:
            for enc in ['utf-8', 'utf-16', 'cp1252', 'iso-8859-1']:
                try:
                    text_content = content.decode(enc)
                    detected_encoding = enc
                    break
                except UnicodeDecodeError:
                    continue

        if text_content is None:
            logger.error(f"Could not decode file {filename}")
            return None, 'unknown'

        sanitized = self.sanitize(text_content)
        raw_bytes = sanitized.encode('utf-8')

        # Strict first
        try:
            parser = etree.XMLParser(encoding='utf-8', huge_tree=True)
            root = etree.fromstring(raw_bytes, parser)
            return root, detected_encoding
        except etree.XMLSyntaxError:
            pass

        # Recovery fallback
        try:
            parser = etree.XMLParser(recover=True, encoding='utf-8', huge_tree=True)
            root = etree.fromstring(raw_bytes, parser)
            if root is not None:
                logger.warning(f"Parsed {filename} with recovery mode")
                return root, detected_encoding
        except Exception:
            pass

        logger.error(f"Total parse failure for {filename}")
        return None, detected_encoding

    def discover_language_files(self, loc_folder: Path) -> Dict[str, Path]:
        """
        Discover language data files in a folder.

        Matches pattern: languagedata_*.xml
        Returns dict mapping language code to file path.
        """
        result: Dict[str, Path] = {}
        pattern = re.compile(r'languagedata_(\w+)\.xml', re.IGNORECASE)

        if not loc_folder.is_dir():
            return result

        for f in loc_folder.iterdir():
            match = pattern.match(f.name)
            if match and f.is_file():
                lang_code = match.group(1).lower()
                result[lang_code] = f

        return result

    def build_translation_lookup(self, lang_file: Path) -> Dict[str, Dict[str, str]]:
        """
        Parse a language file and return translation lookup.

        Returns {StringId: {Str, StrOrigin, Desc, DescOrigin}} for each LocStr element.
        """
        root = self.parse_file(lang_file)
        if root is None:
            return {}

        lookup: Dict[str, Dict[str, str]] = {}

        for elem in iter_locstr_elements(root):
            string_id = get_attr(elem, STRINGID_ATTRS)
            if not string_id:
                continue

            entry: Dict[str, str] = {}
            for attr_name, attr_variants in [
                ('Str', STR_ATTRS),
                ('StrOrigin', STRORIGIN_ATTRS),
                ('Desc', DESC_ATTRS),
                ('DescOrigin', DESCORIGIN_ATTRS),
            ]:
                val = get_attr(elem, attr_variants)
                if val is not None:
                    entry[attr_name] = val

            lookup[string_id] = entry

        return lookup


# =============================================================================
# StringIdConsumer
# =============================================================================


class StringIdConsumer:
    """
    Consumes StringIDs in document order with per-instance deduplication.

    Ported from QACompiler generators/base.py.
    Each instance maintains independent consumption pointers.
    """

    def __init__(self, ordered_index: Dict[str, Dict[str, List[str]]]):
        """
        Args:
            ordered_index: {export_key: {normalized_kor: [sid_list]}}
        """
        # Deep copy to ensure independent consumption per instance
        self._index: Dict[str, Dict[str, List[str]]] = deepcopy(ordered_index)
        self._pointers: Dict[str, Dict[str, int]] = {}

    def consume(self, normalized_kor: str, export_key: str) -> Optional[str]:
        """
        Return next StringID in document order for the given text.

        Advances pointer so next call returns the next one (dedup).
        Returns None if exhausted.
        """
        key_index = self._index.get(export_key)
        if not key_index:
            return None

        sid_list = key_index.get(normalized_kor)
        if not sid_list:
            return None

        # Get or init pointer for this export_key + normalized_kor
        if export_key not in self._pointers:
            self._pointers[export_key] = {}
        pointer_map = self._pointers[export_key]

        ptr = pointer_map.get(normalized_kor, 0)
        if ptr >= len(sid_list):
            return None

        result = sid_list[ptr]
        pointer_map[normalized_kor] = ptr + 1
        return result


# =============================================================================
# Singleton
# =============================================================================

_engine_instance: Optional[XMLParsingEngine] = None


def get_xml_parsing_engine() -> XMLParsingEngine:
    """Get or create the singleton XMLParsingEngine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = XMLParsingEngine()
    return _engine_instance
