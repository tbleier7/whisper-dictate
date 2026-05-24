from whisper_dictate.model import _add_nvidia_dll_dirs

# nvidia-* packages install their CUDA DLLs (cublas64_12.dll and friends) under
# site-packages/nvidia/*/bin, which is not on PATH by default. Make them findable
# before the app starts. Delegates to the single canonical implementation in
# model.py so both entry points (`-m whisper_dictate` and `-m whisper_dictate.app`)
# behave identically.
_add_nvidia_dll_dirs()

from whisper_dictate.app import main  # noqa: E402

main()
