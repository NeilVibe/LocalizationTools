"""
Translation Bank Core Module
============================
Core functionality for building and transferring translation banks.
"""

from .xml_parser import parse_xml, sanitize_xml, iter_xml_files
from .unique_key import generate_level1_key, generate_level2_key, generate_level3_key
from .bank_builder import build_bank, save_bank
from .bank_transfer import transfer_translations, load_bank

__all__ = [
    "parse_xml",
    "sanitize_xml",
    "iter_xml_files",
    "generate_level1_key",
    "generate_level2_key",
    "generate_level3_key",
    "build_bank",
    "save_bank",
    "transfer_translations",
    "load_bank",
]
