"""PyInstaller runtime hook: fix torch DLL loading on Windows.

WinError 1114 occurs because:
1. torch DLLs (c10.dll, torch_cpu.dll) live in _internal/torch/lib/
2. VC++ runtime DLLs (vcruntime140.dll, msvcp140.dll) live in _internal/
3. Python 3.8+ uses secure DLL search where PATH is IGNORED for DLL deps
4. Only os.add_dll_directory() works for implicit DLL dependency resolution

This hook adds ALL relevant directories to the DLL search path BEFORE
torch is imported, so c10.dll can find its VC++ runtime dependencies.
"""

import os
import sys

if getattr(sys, 'frozen', False) and sys.platform == 'win32':
    base = sys._MEIPASS  # = _internal/ directory

    # Directories to add to DLL search path:
    # - base (_internal/) = VC++ runtime, ucrtbase, api-ms-win-* DLLs
    # - torch/lib = c10.dll, torch_cpu.dll, torch_python.dll
    # - torch/bin = protoc.exe and other binaries
    # - torch/ = torch root
    # - *.libs/ = vendored DLLs from faiss-cpu, numpy, etc.
    dll_dirs = [
        base,  # CRITICAL: VC++ runtime lives here
        os.path.join(base, 'torch', 'lib'),
        os.path.join(base, 'torch', 'bin'),
        os.path.join(base, 'torch'),
    ]

    # Also add any *.libs directories (faiss_cpu.libs, numpy.libs, etc.)
    # These contain vendored DLLs like libopenblas, vcomp140, etc.
    try:
        for entry in os.listdir(base):
            if entry.endswith('.libs'):
                dll_dirs.append(os.path.join(base, entry))
    except OSError:
        pass

    found_any = False
    for dll_dir in dll_dirs:
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
            f"runtime_hook_torch: No DLL directories found in _MEIPASS={base}"
        )
