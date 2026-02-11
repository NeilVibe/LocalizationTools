"""PyInstaller runtime hook: fix torch DLL loading on Windows.

WinError 1114 occurs because PyInstaller places torch DLLs in _internal/torch/lib/
but Windows doesn't know to search there. This hook adds that directory to the
DLL search path BEFORE torch is imported.
"""

import os
import sys

if getattr(sys, 'frozen', False) and sys.platform == 'win32':
    base = sys._MEIPASS
    torch_lib = os.path.join(base, 'torch', 'lib')
    torch_bin = os.path.join(base, 'torch', 'bin')
    torch_root = os.path.join(base, 'torch')

    found_any = False
    for dll_dir in [torch_lib, torch_bin, torch_root]:
        if os.path.isdir(dll_dir):
            found_any = True
            os.environ['PATH'] = dll_dir + os.pathsep + os.environ.get('PATH', '')
            if hasattr(os, 'add_dll_directory'):
                try:
                    os.add_dll_directory(dll_dir)
                except OSError:
                    pass  # Windows version too old for add_dll_directory

    if not found_any:
        import warnings
        warnings.warn(
            f"runtime_hook_torch: No torch DLL directories found. "
            f"Searched: {torch_lib}, {torch_bin}, {torch_root}. "
            f"_MEIPASS={base}"
        )
