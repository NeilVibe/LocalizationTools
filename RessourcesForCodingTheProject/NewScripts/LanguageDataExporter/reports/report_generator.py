"""
Report Generator for Word Count Reports.

Generates structured report data for multiple languages.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .word_counter import WordCounter, LanguageWordCount, CategoryWordCount

logger = logging.getLogger(__name__)


@dataclass
class LanguageReport:
    """Report data for a single language."""
    lang_code: str
    display_name: str
    word_count: LanguageWordCount
    count_type: str  # "Words" or "Characters"


@dataclass
class WordCountReport:
    """Complete word count report for all languages."""
    languages: Dict[str, LanguageReport] = field(default_factory=dict)
    categories: List[str] = field(default_factory=list)
    total_strings: int = 0

    def add_language(self, report: LanguageReport):
        """Add language report."""
        self.languages[report.lang_code] = report

        # Update category list
        for category in report.word_count.categories.keys():
            if category not in self.categories:
                self.categories.append(category)

    def get_sorted_categories(self) -> List[str]:
        """Get categories sorted alphabetically."""
        return sorted(self.categories)


class ReportGenerator:
    """
    Generates word count reports for multiple languages.

    Produces structured data that can be exported to Excel or other formats.
    """

    def __init__(self, category_index: Dict[str, str], default_category: str = "Uncategorized"):
        """
        Initialize report generator.

        Args:
            category_index: StringID → Category mapping
            default_category: Category for unmapped StringIDs
        """
        self.category_index = category_index
        self.default_category = default_category

    def generate_language_report(
        self,
        lang_code: str,
        lang_data: List[Dict],
        display_name: Optional[str] = None
    ) -> LanguageReport:
        """
        Generate report for a single language.

        Args:
            lang_code: Language code (e.g., "eng", "jpn")
            lang_data: List of {"str_origin", "str", "string_id"} dicts
            display_name: Display name for language (default: uppercase code)

        Returns:
            LanguageReport with word count breakdown
        """
        if display_name is None:
            display_name = lang_code.upper()

        counter = WordCounter(lang_code)
        word_count = counter.process_entries(
            lang_data,
            self.category_index,
            self.default_category
        )

        return LanguageReport(
            lang_code=lang_code.lower(),
            display_name=display_name,
            word_count=word_count,
            count_type=counter.get_count_type_label()
        )

    def generate_full_report(
        self,
        language_data: Dict[str, List[Dict]],
        language_names: Optional[Dict[str, str]] = None
    ) -> WordCountReport:
        """
        Generate complete report for all languages.

        Args:
            language_data: {lang_code: [entries]} mapping
            language_names: {lang_code: display_name} mapping

        Returns:
            WordCountReport with all languages
        """
        if language_names is None:
            language_names = {}

        report = WordCountReport()

        for lang_code, entries in sorted(language_data.items()):
            display_name = language_names.get(lang_code.lower(), lang_code.upper())

            lang_report = self.generate_language_report(
                lang_code,
                entries,
                display_name
            )
            report.add_language(lang_report)

            # Track total strings (should be same for all languages)
            if report.total_strings == 0:
                report.total_strings = lang_report.word_count.total_strings

        logger.info(f"Generated report for {len(report.languages)} languages, "
                   f"{len(report.categories)} categories")

        return report

    def get_category_summary(self, report: WordCountReport) -> Dict[str, Dict]:
        """
        Get summary of all categories across languages.

        Args:
            report: Complete word count report

        Returns:
            {category: {lang_code: count}} nested dict
        """
        summary: Dict[str, Dict] = {}

        for category in report.get_sorted_categories():
            summary[category] = {}
            for lang_code, lang_report in report.languages.items():
                cat_count = lang_report.word_count.categories.get(category)
                if cat_count:
                    summary[category][lang_code] = cat_count.translation_count
                else:
                    summary[category][lang_code] = 0

        return summary
