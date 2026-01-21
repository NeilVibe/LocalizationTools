# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for LanguageDataExporter.

Builds a standalone Windows executable with all dependencies bundled.
"""

import sys
from pathlib import Path

block_cipher = None

# Paths
PROJECT_DIR = Path(SPECPATH)

a = Analysis(
    ['main.py'],
    pathex=[str(PROJECT_DIR)],
    binaries=[],
    datas=[
        # Configuration files ONLY (NOT Python modules!)
        ('category_clusters.json', '.'),
        ('README.md', '.'),
    ],
    hiddenimports=[
        # Our own packages (PyInstaller analyzes these, NOT copied as data)
        'config',
        'utils',
        'utils.language_utils',
        'utils.vrs_ordering',
        'exporter',
        'exporter.xml_parser',
        'exporter.category_mapper',
        'exporter.excel_writer',
        'reports',
        'reports.word_counter',
        'reports.report_generator',
        'reports.excel_report',
        'clustering',
        'clustering.tier_classifier',
        'clustering.dialog_clusterer',
        'clustering.sequencer_clusterer',
        'clustering.gamedata_clusterer',
        'gui',
        'gui.app',

        # Excel processing
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        'openpyxl.cell',
        'openpyxl.worksheet',
        'openpyxl.workbook',

        # XML parsing
        'lxml',
        'lxml.etree',
        'xml.etree.ElementTree',

        # GUI (tkinter)
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',

        # Standard library
        'json',
        'logging',
        'pathlib',
        're',
        'dataclasses',
        'collections',
        'argparse',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
        'torch',
        'tensorflow',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LanguageDataExporter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Keep console for CLI mode and progress output
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path if available
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LanguageDataExporter',
)
