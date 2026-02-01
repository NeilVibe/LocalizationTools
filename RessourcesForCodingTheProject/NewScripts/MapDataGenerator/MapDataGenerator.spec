# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for MapDataGenerator

Build with:
    pyinstaller MapDataGenerator.spec
"""

import sys
from pathlib import Path

# Get the directory containing the spec file
spec_dir = Path(SPECPATH)

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[str(spec_dir)],
    binaries=[],
    datas=[
        ('tools', 'tools'),  # vgmstream audio converter
        # Include any data files if needed
    ],
    hiddenimports=[
        'PIL',
        'PIL.Image',
        'pillow_dds',
        'lxml',
        'lxml.etree',
        'matplotlib',
        'matplotlib.backends.backend_tkagg',
        'matplotlib.figure',
        # Tkinter submodules (required for GUI)
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pytest',
        'test',
        # DO NOT exclude 'unittest' or 'pyparsing.testing'!
        # pyparsing.__init__ unconditionally imports pyparsing.testing
        # pyparsing.testing needs unittest
        # Both are required for matplotlib to work
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Filter out unnecessary matplotlib backends
a.binaries = [x for x in a.binaries if 'mpl-data' not in x[0] or 'fonts' in x[0]]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Splash screen (optional)
splash = None
# Uncomment to enable splash screen:
# splash = Splash(
#     'splash.png',
#     binaries=a.binaries,
#     datas=a.datas,
#     text_pos=None,
#     text_size=12,
#     minify_script=True,
# )

exe = EXE(
    pyz,
    a.scripts,
    splash.binaries if splash else [],
    [],
    exclude_binaries=True,
    name='MapDataGenerator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if Path('icon.ico').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    splash.datas if splash else [],
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MapDataGenerator',
)
