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


def _hook_warn(msg):
    """Write diagnostic to stderr. Invisible with console=False, but
    captured in debug mode or when running from terminal."""
    try:
        print(f"[runtime_hook_torch] {msg}", file=sys.stderr, flush=True)
    except Exception:
        pass


if getattr(sys, 'frozen', False) and sys.platform == 'win32':
    import ctypes

    base = getattr(sys, '_MEIPASS', None)
    if base is None:
        _hook_warn("WARNING: sys._MEIPASS not found, skipping DLL hook")
    else:
        torch_lib = os.path.join(base, 'torch', 'lib')

        # === Layer A: Register DLL search directories (save handles!) ===
        dll_dirs = [
            base,       # CRITICAL: VC++ runtime lives here
            torch_lib,  # torch core DLLs (c10.dll, torch_cpu.dll)
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

        # Build PATH prefix preserving priority order (base first)
        path_additions = [d for d in dll_dirs if os.path.isdir(d)]
        if path_additions:
            # Layer B: PATH modification (one prepend, correct priority)
            path_prefix = os.pathsep.join(path_additions)
            os.environ['PATH'] = path_prefix + os.pathsep + os.environ.get('PATH', '')

        # Layer A: add_dll_directory with handles saved
        for dll_dir in path_additions:
            if hasattr(os, 'add_dll_directory'):
                try:
                    handle = os.add_dll_directory(dll_dir)
                    _dll_dir_handles.append(handle)  # prevent GC
                except OSError as e:
                    _hook_warn(f"WARNING: add_dll_directory({dll_dir}) failed: {e}")

        # === Layer C: Pre-load critical DLLs into process memory ===
        # Once a DLL is loaded, ANY other DLL that depends on it will find it
        # in memory, regardless of directory search paths.
        #
        # Search BOTH _internal/ and torch/lib/ for each runtime DLL,
        # because PyInstaller may place them in either location.
        runtime_dlls = [
            'vcruntime140.dll',
            'vcruntime140_1.dll',
            'msvcp140.dll',
            'concrt140.dll',      # Concurrency Runtime (used by torch parallel ops)
            'libiomp5md.dll',     # Intel OpenMP (may be in base OR torch/lib)
            'vcomp140.dll',       # MSVC OpenMP runtime
        ]

        for dll_name in runtime_dlls:
            loaded = False
            for search_dir in [base, torch_lib]:
                dll_path = os.path.join(search_dir, dll_name)
                if os.path.exists(dll_path):
                    try:
                        ctypes.WinDLL(dll_path)
                        loaded = True
                        break  # found and loaded, move to next DLL
                    except OSError as e:
                        _hook_warn(f"WARNING: Failed to pre-load {dll_name} from {search_dir}: {e}")
            # Not an error if DLL doesn't exist (e.g. concrt140 may not be bundled)

        # Pre-load torch core DLLs in dependency order
        torch_core_dlls = ['c10.dll', 'torch_cpu.dll', 'torch_python.dll']
        for dll_name in torch_core_dlls:
            dll_path = os.path.join(torch_lib, dll_name)
            if os.path.exists(dll_path):
                try:
                    ctypes.WinDLL(dll_path)
                except OSError as e:
                    _hook_warn(f"CRITICAL: Failed to pre-load {dll_name}: {e}")

        # Pre-load faiss DLLs from faiss_cpu.libs
        faiss_libs = os.path.join(base, 'faiss_cpu.libs')
        if os.path.isdir(faiss_libs):
            for f in sorted(os.listdir(faiss_libs)):
                if f.endswith('.dll'):
                    try:
                        ctypes.WinDLL(os.path.join(faiss_libs, f))
                    except OSError as e:
                        _hook_warn(f"WARNING: Failed to pre-load faiss DLL {f}: {e}")

        _hook_warn(f"DLL hook complete: {len(_dll_dir_handles)} dirs registered, "
                   f"searched {len(path_additions)} directories")
