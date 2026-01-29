"""
MapDataGenerator Core Module

Contains:
- xml_parser: XML parsing and sanitization
- language: Multi-language LOC support
- linkage: StrKey to UITextureName resolution
- search: Search engine
- dds_handler: DDS image loading
"""

from .xml_parser import parse_xml, sanitize_xml, iter_xml_files
from .language import load_language_tables, get_translation
from .linkage import LinkageResolver, DataMode, DataEntry
from .search import SearchEngine, SearchResult
from .dds_handler import DDSHandler

__all__ = [
    'parse_xml',
    'sanitize_xml',
    'iter_xml_files',
    'load_language_tables',
    'get_translation',
    'LinkageResolver',
    'DataMode',
    'DataEntry',
    'SearchEngine',
    'SearchResult',
    'DDSHandler',
]
