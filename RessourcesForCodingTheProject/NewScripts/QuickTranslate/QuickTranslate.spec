# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for QuickTranslate
#
# PATTERN: Use hidden-import + copy-metadata for packages with native DLLs.
#   collect_all ONLY for pure-Python packages that need data files (JSON, vocab).
#
# WHY: hidden-import lets PyInstaller's binary analysis place DLLs flat.
# This approach is based on the user's working PyInstaller command for
# XLSTransfer/KRSimilar monoliths (--hidden-import + --copy-metadata).

import os
from PyInstaller.utils.hooks import collect_all, copy_metadata

# Get the directory containing this spec file
spec_dir = os.path.dirname(os.path.abspath(SPEC))

# =============================================================================
# ML dependency collection - TWO strategies:
#
# Strategy 1: hidden-import + copy-metadata (for packages with DLLs)
#   → PyInstaller traces imports, binary analysis collects DLLs FLAT
#   → Used for: numpy, faiss, model2vec
#
# Strategy 2: collect_all (for pure-Python packages with data files)
#   → Collects ALL package files including configs, vocabs, etc.
# =============================================================================

ml_datas = []
ml_binaries = []
ml_hiddenimports = []

# --- Strategy 1: hidden-import + copy-metadata (packages with native DLLs) ---
# Let PyInstaller's binary analysis trace DLL deps and place them flat.
METADATA_PACKAGES = [
    'numpy',
    'tqdm',
    'requests',
    'urllib3',
    'certifi',
    'charset-normalizer',
    'idna',
    'packaging',
    'filelock',
    'tokenizers',
    'faiss-cpu',
    'safetensors',
    'model2vec',
]

for pkg in METADATA_PACKAGES:
    try:
        ml_datas += copy_metadata(pkg)
        print(f"  copy_metadata('{pkg}'): OK")
    except Exception as e:
        # Some packages may not have metadata - not fatal
        print(f"  copy_metadata('{pkg}'): skipped ({e})")

# --- Strategy 2: collect_all for pure-Python packages with data files ---
# These packages need their JSON configs, vocab files, etc. at runtime.
# ONLY pure-Python packages here -- NO native extensions (Rust/.pyd).
# tokenizers and safetensors have Rust binaries, so they stay in Strategy 1.
COLLECT_ALL_PACKAGES = [
    'requests',       # Pure Python, may be needed by tokenizers/model2vec
    'urllib3',        # requests dependency
    'certifi',        # requests dependency (SSL certificates)
    'charset_normalizer',  # requests dependency (encoding detection)
    'idna',           # requests dependency (internationalized domain names)
]

for pkg in COLLECT_ALL_PACKAGES:
    try:
        d, b, h = collect_all(pkg)
        ml_datas += d
        ml_binaries += b
        ml_hiddenimports += h
        print(f"  collect_all('{pkg}'): {len(d)} datas, {len(b)} binaries, {len(h)} hiddenimports")
    except Exception as e:
        raise RuntimeError(
            f"collect_all('{pkg}') FAILED: {e}\n"
            f"Make sure '{pkg}' is installed: pip install {pkg.replace('_', '-')}"
        )

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
        # User Guide — bundled with the app so users always have it
        ('docs/USER_GUIDE.md', '.'),
        ('images', 'images'),
    ] + ml_datas,
    hiddenimports=[
        # === Hidden imports for packages with native DLLs (flat placement) ===
        'safetensors',
        'numpy',
        'tqdm',
        'tqdm.auto',
        'requests',
        'requests.adapters',
        'requests.api',
        'requests.auth',
        'requests.cookies',
        'requests.exceptions',
        'requests.models',
        'requests.sessions',
        'requests.structures',
        'requests.utils',
        'urllib3',
        'urllib3.util',
        'urllib3.util.retry',
        'urllib3.util.ssl_',
        'urllib3.connectionpool',
        'urllib3.poolmanager',
        'urllib3.response',
        'certifi',
        'charset_normalizer',
        'idna',
        'packaging',
        'packaging.version',
        'filelock',
        'tokenizers',
        'typing_extensions',
        'yaml',
        # Model2Vec -- lightweight static embeddings
        'model2vec',
        # FAISS -- import name differs from distribution name
        'faiss',
        'faiss.swigfaiss',
        'faiss.swigfaiss_avx2',
        'faiss.loader',
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
        'tkinter.scrolledtext',
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
        # Exclude heavy packages not needed by Model2Vec/FAISS.
        'matplotlib',
        'pandas',
        'PIL',
        'cv2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='QuickTranslate',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,     # Avoid antivirus false positives + DLL corruption risk
    console=False,  # No console window for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='images/QTico.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,  # Never compress DLLs - causes WinError and AV false positives
    name='QuickTranslate',
)
