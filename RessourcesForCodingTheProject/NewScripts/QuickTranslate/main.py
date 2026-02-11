#!/usr/bin/env python3
"""
QuickTranslate - Find translations for Korean text by matching StrOrigin.

Entry point for QuickTranslate application.

Features:
    - Multiple match types: Substring, StringID-only, Strict, Special Key
    - Multiple input modes: File (single) or Folder (recursive)
    - Multiple formats: Excel (.xlsx) or XML (.xml)
    - Branch selection: mainline or cd_lambda
    - StringID lookup
    - Reverse lookup (any language -> all languages)
    - ToSubmit folder integration

Usage:
    python main.py          # Launch GUI
    python main.py --help   # Show help
"""

import argparse
import logging
import sys
import traceback
from pathlib import Path

# PyInstaller compatibility - ensure we can find our modules
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    BASE_DIR = Path(sys.executable).parent
    sys.path.insert(0, str(BASE_DIR))

    # Crash logging: write errors to file since console=False hides them
    _crash_log = BASE_DIR / "QuickTranslate_crash.log"
    try:
        sys.stderr = open(str(_crash_log), 'a', encoding='utf-8')
    except Exception:
        pass
else:
    # Running as script
    BASE_DIR = Path(__file__).parent
    sys.path.insert(0, str(BASE_DIR))


# Setup logging
def setup_logging(verbose: bool = False):
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger('QuickTranslate')


def run_smoke_test():
    """Run comprehensive smoke test of all critical imports and operations.

    Used by CI to verify the built exe actually works. Tests every single
    dependency that has caused runtime failures in the past.
    Exit 0 = all good. Exit 1 = something is broken.
    """
    results = []
    failures = []

    def test(name, fn):
        try:
            fn()
            results.append(f"  PASS: {name}")
        except Exception as e:
            results.append(f"  FAIL: {name} -> {e}")
            failures.append(name)

    print("=" * 60, file=sys.stderr)
    print("QUICKTRANSLATE SMOKE TEST", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # --- 1. Core Python imports ---
    test("import os", lambda: __import__('os'))
    test("import json", lambda: __import__('json'))
    test("import pathlib", lambda: __import__('pathlib'))
    test("import logging", lambda: __import__('logging'))
    test("import threading", lambda: __import__('threading'))
    test("import tkinter", lambda: __import__('tkinter'))
    test("import tkinter.ttk", lambda: __import__('tkinter.ttk'))
    test("import tkinter.scrolledtext", lambda: __import__('tkinter.scrolledtext'))

    # --- 2. Third-party non-ML imports ---
    test("import lxml", lambda: __import__('lxml'))
    test("import lxml.etree", lambda: __import__('lxml.etree'))
    test("import openpyxl", lambda: __import__('openpyxl'))
    test("import xlsxwriter", lambda: __import__('xlsxwriter'))

    # --- 3. ML CORE: torch (THE critical dependency) ---
    test("import torch", lambda: __import__('torch'))
    test("import torch.cuda", lambda: __import__('torch.cuda'))
    test("import torch.nn", lambda: __import__('torch.nn'))
    test("import torch.backends", lambda: __import__('torch.backends'))

    def check_torch_cpu():
        import torch
        assert not torch.cuda.is_available(), "CUDA should NOT be available (CPU-only build)"
        v = torch.__version__
        print(f"  torch version: {v}", file=sys.stderr)
    test("torch.cuda.is_available() == False", check_torch_cpu)

    def check_torch_tensor():
        import torch
        t = torch.zeros(3, 3)
        assert t.shape == (3, 3), f"Expected (3,3) got {t.shape}"
        assert str(t.device) == 'cpu', f"Expected cpu got {t.device}"
    test("torch.zeros on CPU", check_torch_tensor)

    # --- 4. ML: numpy ---
    test("import numpy", lambda: __import__('numpy'))

    def check_numpy():
        import numpy as np
        a = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        assert a.shape == (3,), f"Expected (3,) got {a.shape}"
    test("numpy array creation", check_numpy)

    # --- 5. ML: FAISS ---
    test("import faiss", lambda: __import__('faiss'))

    def check_faiss_index():
        import faiss
        import numpy as np
        dim = 8
        index = faiss.IndexFlatIP(dim)
        vecs = np.random.randn(5, dim).astype(np.float32)
        faiss.normalize_L2(vecs)
        index.add(vecs)
        assert index.ntotal == 5, f"Expected 5 vectors, got {index.ntotal}"
        D, I = index.search(vecs[:1], 1)
        assert I[0][0] == 0, "Self-search should return index 0"
    test("FAISS IndexFlatIP create + add + search", check_faiss_index)

    # --- 6. ML: sentence-transformers ---
    test("import sentence_transformers", lambda: __import__('sentence_transformers'))

    def check_st_class():
        from sentence_transformers import SentenceTransformer
        assert SentenceTransformer is not None
    test("from sentence_transformers import SentenceTransformer", check_st_class)

    # --- 7. ML: transformers (huggingface) ---
    test("import transformers", lambda: __import__('transformers'))

    def check_transformers():
        from transformers import AutoTokenizer, AutoModel
        assert AutoTokenizer is not None
        assert AutoModel is not None
    test("from transformers import AutoTokenizer, AutoModel", check_transformers)

    # --- 8. ML transitive deps ---
    test("import tokenizers", lambda: __import__('tokenizers'))
    test("import safetensors", lambda: __import__('safetensors'))
    test("import huggingface_hub", lambda: __import__('huggingface_hub'))
    test("import tqdm", lambda: __import__('tqdm'))
    test("import regex", lambda: __import__('regex'))
    test("import requests", lambda: __import__('requests'))
    test("import packaging", lambda: __import__('packaging'))
    test("import filelock", lambda: __import__('filelock'))
    test("import scipy", lambda: __import__('scipy'))
    test("import sklearn", lambda: __import__('sklearn'))

    # --- 9. torch submodules (previously excluded, caused crashes) ---
    test("import torch.cuda", lambda: __import__('torch.cuda'))
    test("import torch.distributed", lambda: __import__('torch.distributed'))
    test("import torch._dynamo", lambda: __import__('torch._dynamo'))
    test("import torch.fx", lambda: __import__('torch.fx'))
    test("import torch.backends.cudnn", lambda: __import__('torch.backends.cudnn'))
    test("import torch.compiler", lambda: __import__('torch.compiler'))

    # --- 10. QuickTranslate own modules ---
    test("import config", lambda: __import__('config'))

    def check_config():
        import config
        assert hasattr(config, 'MATCHING_MODES')
        assert hasattr(config, 'LANGUAGE_ORDER')
        assert hasattr(config, 'KRTRANSFORMER_PATH')
    test("config attributes", check_config)

    test("import core.xml_parser", lambda: __import__('core.xml_parser'))
    test("import core.matching", lambda: __import__('core.matching'))
    test("import core.indexing", lambda: __import__('core.indexing'))
    test("import core.fuzzy_matching", lambda: __import__('core.fuzzy_matching'))
    test("import core.korean_detection", lambda: __import__('core.korean_detection'))
    test("import core.excel_io", lambda: __import__('core.excel_io'))
    test("import core.xml_io", lambda: __import__('core.xml_io'))
    test("import core.xml_transfer", lambda: __import__('core.xml_transfer'))
    test("import core.quality_checker", lambda: __import__('core.quality_checker'))
    test("import core.text_utils", lambda: __import__('core.text_utils'))
    test("import core.source_scanner", lambda: __import__('core.source_scanner'))
    test("import core.missing_translation_finder", lambda: __import__('core.missing_translation_finder'))
    test("import gui.app", lambda: __import__('gui.app'))
    test("import utils.file_io", lambda: __import__('utils.file_io'))

    # --- Print results ---
    print("", file=sys.stderr)
    for r in results:
        print(r, file=sys.stderr)
    print("", file=sys.stderr)
    print(f"TOTAL: {len(results)} tests, {len(results) - len(failures)} passed, {len(failures)} failed", file=sys.stderr)
    print("", file=sys.stderr)

    if failures:
        print("SMOKE TEST FAILED", file=sys.stderr)
        print(f"Failed: {', '.join(failures)}", file=sys.stderr)
        sys.exit(1)
    else:
        print("SMOKE_TEST_PASSED", file=sys.stderr)
        sys.exit(0)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='QuickTranslate - Find translations for Korean text',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py                  # Launch GUI
    python main.py --verbose        # Launch GUI with verbose logging

For GUI usage:
    1. Select format (Excel or XML)
    2. Select mode (File or Folder)
    3. Select match type
    4. Choose source file/folder
    5. Click Generate
        """
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='QuickTranslate 2.0.0'
    )
    parser.add_argument(
        '--smoke-test',
        action='store_true',
        help='Run smoke test of all imports and exit'
    )

    args = parser.parse_args()

    # Smoke test mode - test all imports and exit
    if args.smoke_test:
        run_smoke_test()
        return

    # Setup logging
    logger = setup_logging(args.verbose)
    logger.info("Starting QuickTranslate...")

    # Import and run GUI
    try:
        from gui import QuickTranslateApp
        if QuickTranslateApp is None:
            logger.error("GUI not available (tkinter not installed)")
            print("ERROR: tkinter not available.")
            print("  - Windows: Reinstall Python with 'tcl/tk' checkbox enabled")
            print("  - Linux:   sudo apt install python3-tk")
            sys.exit(1)

        import tkinter as tk
        root = tk.Tk()
        app = QuickTranslateApp(root)
        logger.info("GUI initialized successfully")
        root.mainloop()

    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        tb = traceback.format_exc()
        logger.exception(f"Fatal error: {e}")

        # Write to crash log
        try:
            with open(str(BASE_DIR / "QuickTranslate_crash.log"), 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n{error_msg}\n{tb}\n")
        except Exception:
            pass

        # Show error dialog (visible even with console=False)
        try:
            import tkinter as _tk
            from tkinter import messagebox as _mb
            _root = _tk.Tk()
            _root.withdraw()
            _mb.showerror(
                "QuickTranslate Error",
                f"Fatal error:\n\n{error_msg}\n\n"
                f"Details written to QuickTranslate_crash.log"
            )
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
