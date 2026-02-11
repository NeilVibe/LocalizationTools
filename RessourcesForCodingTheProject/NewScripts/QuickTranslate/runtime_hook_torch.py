"""PyInstaller runtime hook: fix torch DLL loading on Windows.

WinError 1114 occurs on FRESH machines (no VC++ Redistributable) because:
1. torch DLLs (c10.dll, torch_cpu.dll) live in _internal/torch/lib/
2. VC++ runtime DLLs (vcruntime140.dll, msvcp140.dll) live in _internal/
3. Python 3.8+ secure DLL search ignores PATH for DLL dependencies
4. Only os.add_dll_directory() works, BUT handles can be garbage collected

Fix: THREE layers of defense:
A) add_dll_directory with handles saved (prevents GC from removing dirs)
B) PATH modification (fallback for older Windows / ctypes loads)
C) Pre-load VC++ runtime DLLs into process memory via ctypes
   (once loaded, any DLL can find them regardless of search path)
"""

import os
import sys

# Global list to prevent garbage collection of DLL directory handles.
_dll_dir_handles = []

if getattr(sys, 'frozen', False) and sys.platform == 'win32':
    import ctypes

    base = sys._MEIPASS  # = _internal/ directory
    torch_lib = os.path.join(base, 'torch', 'lib')

    # === Layer A: Register DLL search directories (save handles!) ===
    dll_dirs = [
        base,  # CRITICAL: VC++ runtime lives here
        torch_lib,
        os.path.join(base, 'torch', 'bin'),
        os.path.join(base, 'torch'),
    ]

    # Add *.libs directories (faiss_cpu.libs, numpy.libs, etc.)
    try:
        for entry in os.listdir(base):
            if entry.endswith('.libs'):
                dll_dirs.append(os.path.join(base, entry))
    except OSError:
        pass

    for dll_dir in dll_dirs:
        if os.path.isdir(dll_dir):
            # Layer B: PATH modification
            os.environ['PATH'] = dll_dir + os.pathsep + os.environ.get('PATH', '')
            # Layer A: add_dll_directory with handle saved
            if hasattr(os, 'add_dll_directory'):
                try:
                    handle = os.add_dll_directory(dll_dir)
                    _dll_dir_handles.append(handle)  # PREVENT GC!
                except OSError:
                    pass

    # === Layer C: Pre-load critical DLLs into process memory ===
    # Once a DLL is loaded, ANY other DLL that depends on it will find it
    # in memory, regardless of directory search paths.
    for dll_name in ['vcruntime140.dll', 'vcruntime140_1.dll', 'msvcp140.dll',
                     'libiomp5md.dll']:
        dll_path = os.path.join(base, dll_name)
        if os.path.exists(dll_path):
            try:
                ctypes.WinDLL(dll_path)
            except OSError:
                pass

    # Pre-load torch core DLLs in dependency order
    for dll_name in ['c10.dll', 'torch_cpu.dll', 'torch_python.dll']:
        dll_path = os.path.join(torch_lib, dll_name)
        if os.path.exists(dll_path):
            try:
                ctypes.WinDLL(dll_path)
            except OSError:
                pass

    # Pre-load faiss DLLs from faiss_cpu.libs
    faiss_libs = os.path.join(base, 'faiss_cpu.libs')
    if os.path.isdir(faiss_libs):
        for f in os.listdir(faiss_libs):
            if f.endswith('.dll'):
                try:
                    ctypes.WinDLL(os.path.join(faiss_libs, f))
                except OSError:
                    pass
