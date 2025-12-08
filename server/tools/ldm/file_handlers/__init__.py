"""
LDM File Handlers - Parse localization files into database rows

Handlers:
- txt_handler: TXT/TSV files (index 5=source, index 6=target)
- xml_handler: XML LocStr format (StrOrigin=source, Str=target)
"""

__all__ = ['txt_handler', 'xml_handler']
