# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for QuickSearch

import os

block_cipher = None

# Get the directory containing this spec file
spec_dir = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['main.py'],
    pathex=[spec_dir],
    binaries=[],
    datas=[
        ('config.py', '.'),
        ('README.md', '.'),
        ('USER_GUIDE.md', '.'),
        ('images', 'images'),
    ],
    hiddenimports=[
        'lxml',
        'lxml.etree',
        'pandas',
        'ahocorasick',
        'openpyxl',
        'pyperclip',
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'core',
        'core.xml_parser',
        'core.preprocessing',
        'core.line_check',
        'core.term_check',
        'core.glossary',
        'core.dictionary',
        'core.search',
        'gui',
        'gui.app',
        'gui.dialogs',
        'utils',
        'utils.filters',
        'utils.language_utils',
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

# Splash screen
splash = Splash(
    'images/QSsplash.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=(10, 290),
    text_size=10,
    text_color='black',
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    splash,
    splash.binaries,
    [],
    exclude_binaries=True,
    name='QuickSearch',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='images/QSico.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='QuickSearch',
)
