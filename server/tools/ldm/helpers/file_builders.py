"""
File building utilities.

TODO: Migrate from api.py lines 2623-2784
- _build_txt_file → build_txt_file
- _build_xml_file → build_xml_file
- _build_excel_file → build_excel_file
"""

from typing import List, Optional
from server.database.models import LDMRow


def build_txt_file(rows: List[LDMRow], file_metadata: dict = None) -> bytes:
    """Build a TXT file from rows. TODO: Migrate from api.py"""
    raise NotImplementedError("Migrate from api.py")


def build_xml_file(rows: List[LDMRow], file_metadata: dict = None) -> bytes:
    """Build an XML file from rows. TODO: Migrate from api.py"""
    raise NotImplementedError("Migrate from api.py")


def build_excel_file(rows: List[LDMRow], file_metadata: dict = None) -> bytes:
    """Build an Excel file from rows. TODO: Migrate from api.py"""
    raise NotImplementedError("Migrate from api.py")
