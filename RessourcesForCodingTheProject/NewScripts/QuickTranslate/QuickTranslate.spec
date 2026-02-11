# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for QuickTranslate

import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# Get the directory containing this spec file
spec_dir = os.path.dirname(os.path.abspath(SPEC))

# =============================================================================
# Collect ML dependencies (sentence-transformers, torch, faiss, etc.)
# =============================================================================
ml_datas = []
ml_binaries = []
ml_hiddenimports = []

for pkg in ['sentence_transformers', 'transformers', 'torch', 'faiss', 'numpy',
            'tokenizers', 'huggingface_hub', 'safetensors']:
    try:
        d, b, h = collect_all(pkg)
        ml_datas += d
        ml_binaries += b
        ml_hiddenimports += h
    except Exception:
        pass  # Package not installed - skip

a = Analysis(
    ['main.py'],
    pathex=[spec_dir],
    binaries=ml_binaries,
    datas=[
        ('config.py', '.'),
        ('ai_hallucination_phrases.json', '.'),
        ('core', 'core'),
        ('gui', 'gui'),
        ('utils', 'utils'),
    ] + ml_datas,
    hiddenimports=[
        # Third-party
        'lxml',
        'lxml.etree',
        'openpyxl',
        'xlsxwriter',
        # Standard library GUI
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        # core/ - ALL modules
        'core',
        'core.category_mapper',
        'core.checker',
        'core.eventname_resolver',
        'core.excel_io',
        'core.failure_report',
        'core.fuzzy_matching',
        'core.indexing',
        'core.korean_detection',
        'core.language_loader',
        'core.matching',
        'core.missing_translation_finder',
        'core.postprocess',
        'core.quality_checker',
        'core.source_scanner',
        'core.text_utils',
        'core.xml_io',
        'core.xml_parser',
        'core.xml_transfer',
        # gui/ - ALL modules
        'gui',
        'gui.app',
        'gui.exclude_dialog',
        'gui.missing_params_dialog',
        # utils/ - ALL modules
        'utils',
        'utils.file_io',
    ] + ml_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude CUDA/GPU backends - we only need CPU inference
        'torch.cuda',
        'torch.distributed',
        'torch.testing',
        # Exclude heavy unused ML packages
        'scipy',
        'scikit-learn',
        'sklearn',
        'matplotlib',
        'pandas',
        'PIL',
        'cv2',
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
    name='QuickTranslate',
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='QuickTranslate',
)
