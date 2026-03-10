# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for QuickCheck

import os
import importlib

block_cipher = None

# Get the directory containing this spec file
spec_dir = os.path.dirname(os.path.abspath(SPEC))

# Bundle fast_langdetect resources (lite model .ftz + full model .bin if present)
_fl_datas = []
try:
    _fl_pkg = importlib.import_module('fast_langdetect')
    _fl_res = os.path.join(os.path.dirname(_fl_pkg.__file__), 'resources')
    if os.path.isdir(_fl_res):
        _fl_datas.append((_fl_res, 'fast_langdetect/resources'))
except ImportError:
    pass

# Also bundle full model from temp cache if downloaded during CI
_full_model = os.path.join(os.environ.get('TEMP', '/tmp'), 'fasttext-langdetect', 'lid.176.bin')
if os.path.isfile(_full_model):
    _fl_datas.append((_full_model, 'fast_langdetect/resources'))

a = Analysis(
    ['main.py'],
    pathex=[spec_dir],
    binaries=[],
    datas=_fl_datas,
    hiddenimports=[
        'lxml',
        'lxml.etree',
        'ahocorasick',
        'xlsxwriter',
        'openpyxl',
        'fast_langdetect',
        'ftlangdetect',
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'logging.handlers',
        'core',
        'core.xml_parser',
        'core.preprocessing',
        'core.scanner',
        'core.line_check',
        'core.term_check',
        'core.glossary_extractor',
        'core.lang_check',
        'gui',
        'gui.app',
        'utils',
        'utils.filters',
        'utils.language_utils',
        'utils.excel_writer',
        'utils.unicode_utils',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='QuickCheck',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='QuickCheck',
)
