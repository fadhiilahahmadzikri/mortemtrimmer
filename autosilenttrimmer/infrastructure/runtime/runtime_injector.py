"""Runtime Pack Python path and native DLL directory activation helper."""

from __future__ import annotations

import os
import sys

_REGISTERED_PACK_DIRS: set[str] = set()
_DLL_HANDLES: list[object] = []


def activate_runtime_pack(pack_dir: str) -> None:
    """Register installed runtime pack site-packages and native DLL directories safely."""
    abs_dir = os.path.abspath(pack_dir)
    if abs_dir in _REGISTERED_PACK_DIRS or not os.path.isdir(abs_dir):
        return

    site_pkg = os.path.join(abs_dir, "site-packages")
    target_py_dir = site_pkg if os.path.isdir(site_pkg) else abs_dir
    if target_py_dir not in sys.path:
        sys.path.insert(0, target_py_dir)

    bin_dir = os.path.join(abs_dir, "bin")
    if os.path.isdir(bin_dir):
        os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            _DLL_HANDLES.append(os.add_dll_directory(bin_dir))

    _REGISTERED_PACK_DIRS.add(abs_dir)
