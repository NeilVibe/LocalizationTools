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

    for dll_dir in [torch_lib, torch_bin]:
        if os.path.isdir(dll_dir):
            os.environ['PATH'] = dll_dir + os.pathsep + os.environ.get('PATH', '')
            if hasattr(os, 'add_dll_directory'):
                os.add_dll_directory(dll_dir)
