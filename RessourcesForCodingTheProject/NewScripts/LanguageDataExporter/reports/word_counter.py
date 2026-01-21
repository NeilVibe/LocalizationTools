"""
Word Counter for Language Data.

Counts words (European/SEA) or characters (CJK) per category.
Identifies untranslated text by Korean detection.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

try:
    # When running as part of the package
    from ..utils.language_utils import (
        contains_korean,
        count_words,
        count_chars,
        is_word_count_language,
        is_char_count_language,
    )
except ImportError:
    # When running from within the package directory
    from utils.language_utils import (
        contains_korean,
        count_words,
        count_chars,
        is_word_count_language,
        is_char_count_language,
    )

logger = logging.getLogger(__name__)


@dataclass
class CategoryWordCount:
    """Word/character count data for a single category."""
    category: str
    korean_words: int = 0       # Words in Korean source (StrOrigin)
    translation_count: int = 0  # Words/chars in translation (Str)
    total_strings: int = 0      # Number of strings
    untranslated: int = 0       # Strings still containing Korean


@dataclass
class LanguageWordCount:
    """Word/character count data for a language."""
    lang_code: str
    categories: Dict[str, CategoryWordCount] = field(default_factory=dict)
    total_korean_words: int = 0
    total_translation_count: int = 0
    total_strings: int = 0
    total_untranslated: int = 0
    is_char_count: bool = False  # True for CJK languages

    def add_category(self, cat_count: CategoryWordCount):
        """Add category count to totals."""
        self.categories[cat_count.category] = cat_count
        self.total_korean_words += cat_count.korean_words
        self.total_translation_count += cat_count.translation_count
        self.total_strings += cat_count.total_strings
        self.total_untranslated += cat_count.untranslated


class WordCounter:
    """
    Counts words/characters in language data by category.

    - For European/SEA languages: counts words (space-separated)
    - For CJK languages: counts characters (excluding whitespace)
    - Identifies untranslated strings by Korean content detection
    """

    def __init__(self, lang_code: str):
        """
        Initialize word counter.

        Args:
            lang_code: Language code (e.g., "eng", "jpn")
        """
        self.lang_code = lang_code.lower()
        self.is_char_count = is_char_count_language(self.lang_code)

    def count_text(self, text: Optional[str]) -> int:
        """
        Count words or characters based on language type.

        Args:
            text: Text to count

        Returns:
            Word count (European/SEA) or character count (CJK)
        """
        if self.is_char_count:
            return count_chars(text)
        return count_words(text)

    def process_entries(
        self,
        entries: List[Dict],
        category_index: Dict[str, str],
        default_category: str = "Uncategorized"
    ) -> LanguageWordCount:
        """
        Process language entries and count by category.

        Args:
            entries: List of {"str_origin", "str", "string_id"} dicts
            category_index: StringID → Category mapping
            default_category: Category for unmapped StringIDs

        Returns:
            LanguageWordCount with category breakdown
        """
        result = LanguageWordCount(
            lang_code=self.lang_code,
            is_char_count=self.is_char_count
        )

        # Group counts by category
        category_data: Dict[str, CategoryWordCount] = {}

        for entry in entries:
            string_id = entry.get("string_id", "")
            str_origin = entry.get("str_origin", "")
            str_value = entry.get("str", "")

            # Get category
            category = category_index.get(string_id, default_category)

            # Initialize category if needed
            if category not in category_data:
                category_data[category] = CategoryWordCount(category=category)

            cat_count = category_data[category]
            cat_count.total_strings += 1

            # Count Korean source words
            if str_origin and not contains_korean(str_value):
                # Only count Korean if translation doesn't have Korean
                cat_count.korean_words += count_words(str_origin)

            # Count translation
            if str_value:
                if contains_korean(str_value):
                    # Translation still has Korean = untranslated
                    cat_count.untranslated += 1
                else:
                    cat_count.translation_count += self.count_text(str_value)

        # Add categories to result
        for cat_count in sorted(category_data.values(), key=lambda x: x.category):
            result.add_category(cat_count)

        return result

    def get_count_type_label(self) -> str:
        """Get label for count type (Words or Characters)."""
        return "Characters" if self.is_char_count else "Words"
