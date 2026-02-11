# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for QuickTranslate
#
# PATTERN: Use hidden-import + copy-metadata for packages with native DLLs.
#   collect_all ONLY for pure-Python packages that need data files (JSON, vocab).
#
# WHY: collect_all('torch') preserves torch/lib/c10.dll in a subdirectory,
# but vcruntime140.dll is in _internal/. Windows can't find it across dirs.
# hidden-import lets PyInstaller's binary analysis place DLLs flat.
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
#   → Used for: torch, numpy, faiss
#
# Strategy 2: collect_all (for pure-Python packages with data files)
#   → Collects ALL package files including configs, vocabs, etc.
#   → Used for: sentence_transformers, transformers, huggingface_hub, etc.
# =============================================================================

ml_datas = []
ml_binaries = []
ml_hiddenimports = []

# --- Strategy 1: hidden-import + copy-metadata (packages with native DLLs) ---
# Let PyInstaller's binary analysis trace DLL deps and place them flat.
METADATA_PACKAGES = [
    'torch',
    'numpy',
    'tqdm',
    'regex',
    'requests',
    'packaging',
    'filelock',
    'tokenizers',
    'faiss-cpu',
    'sentence-transformers',
    'transformers',
    'huggingface-hub',
    'safetensors',
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
    'sentence_transformers',
    'transformers',
    'huggingface_hub',
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
    ] + ml_datas,
    hiddenimports=[
        # === Hidden imports for packages with native DLLs (flat placement) ===
        'torch',
        'safetensors',
        'safetensors.torch',
        'numpy',
        'tqdm',
        'tqdm.auto',
        'regex',
        'requests',
        'packaging',
        'packaging.version',
        'filelock',
        'tokenizers',
        'typing_extensions',
        'yaml',
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
    runtime_hooks=[os.path.join(spec_dir, 'runtime_hook_torch.py')],
    excludes=[
        # Exclude heavy unused ML packages
        'scipy',
        'scikit-learn',
        'sklearn',
        'matplotlib',
        'pandas',
        'PIL',
        'cv2',
        # Exclude torch subpackages we don't need (CPU-only app, saves ~100MB+)
        'torch.distributed',
        'torch.testing',
        'torch.cuda',
        'torch.backends.cudnn',
        'torch.onnx',
        'torch.utils.tensorboard',
        'torch._dynamo',
        'torch.compiler',
        'torch.fx',
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
