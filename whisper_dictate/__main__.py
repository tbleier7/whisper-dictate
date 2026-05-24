import os
import sys


def _add_nvidia_dll_dirs() -> None:
    """Add NVIDIA CUDA DLL directories to the Windows DLL search path.

    nvidia-* packages install their DLLs under site-packages/nvidia/*/bin,
    which is not on PATH by default.  ctranslate2 (used by faster-whisper)
    needs cublas64_12.dll and friends at import time.
    """
    if sys.platform != "win32":
        return
    import site
    from pathlib import Path

    for sp in site.getsitepackages():
        nvidia = Path(sp) / "nvidia"
        if nvidia.is_dir():
            for bin_dir in nvidia.glob("*/bin"):
                os.add_dll_directory(str(bin_dir))


_add_nvidia_dll_dirs()

from whisper_dictate.app import main  # noqa: E402

main()
