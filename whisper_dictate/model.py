from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
import numpy as np
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from faster_whisper import WhisperModel

_log = logging.getLogger(__name__)

_MODEL_NAME = "large-v3"
# Compute type per device: float16 is the fast path on a CUDA GPU (and fits
# large-v3 comfortably in modest VRAM), while int8 is the CPU-optimal type.
_COMPUTE_TYPE = {"cuda": "float16", "cpu": "int8"}
_BEAM_SIZE = 5


@dataclass
class DecodeSettings:
    """Decoder knobs forwarded to faster-whisper at transcription time."""

    hotwords: str = ""
    vad_filter: bool = False
    normalize: bool = False


def _add_nvidia_dll_dirs() -> None:
    """Put the nvidia-*-cu12 wheel ``bin`` directories on PATH for ctranslate2.

    The CUDA wheels (nvidia-cublas-cu12 and its dependency nvidia-cuda-nvrtc-cu12)
    install their DLLs under ``<site-packages>/nvidia/*/bin``. ctranslate2 loads
    those libraries via ``LoadLibraryA``, which searches PATH, so we prepend the
    directories before the first GPU load attempt.

    We locate them through the importable ``nvidia`` namespace package rather than
    guessing site-packages paths, so discovery works no matter where pip placed
    the wheels — venv, ``pipx``, ``pip install --user``, or a global install.
    Guessing site dirs was the cause of silent CPU fallbacks when the app ran from
    an interpreter whose layout ``site.getsitepackages()`` did not cover.
    """
    if sys.platform != "win32":
        return
    try:
        import nvidia  # namespace package provided by the nvidia-*-cu12 wheels
    except ImportError:
        _log.warning(
            "nvidia CUDA wheels not importable in this environment — GPU will be "
            "unavailable, falling back to CPU"
        )
        return
    from pathlib import Path
    dirs: list[str] = []
    for root in nvidia.__path__:
        for bin_dir in Path(root).glob("*/bin"):
            dirs.append(str(bin_dir))
            _log.debug("adding DLL dir to PATH: %s", bin_dir)
    if dirs:
        os.environ["PATH"] = ";".join(dirs) + ";" + os.environ.get("PATH", "")


class _ModelLoaderThread(QThread):
    loaded = pyqtSignal(object, str)
    failed = pyqtSignal(str)

    def run(self) -> None:
        _add_nvidia_dll_dirs()
        last_error = "unknown error"
        for device in ("cuda", "cpu"):
            compute_type = _COMPUTE_TYPE[device]
            try:
                model = WhisperModel(_MODEL_NAME, device=device, compute_type=compute_type)
                # CUDA may load without error but fail at inference time (missing DLLs).
                # Run a tiny test to catch that before we consider the model ready.
                list(model.transcribe(np.zeros(16000, dtype=np.float32), language="en")[0])
                if device == "cpu":
                    _log.warning(
                        "model loaded on CPU (compute_type=%s) — transcription will be SLOW; "
                        "GPU/CUDA was unavailable in this Python environment",
                        compute_type,
                    )
                else:
                    _log.info("model loaded on device=%s (compute_type=%s)", device, compute_type)
                self.loaded.emit(model, device)
                return
            except Exception as exc:
                last_error = str(exc)
                _log.warning("device=%s failed (%s), trying next", device, exc)
        self.failed.emit(f"Could not load model on any device: {last_error}")


class _TranscribeThread(QThread):
    transcribed = pyqtSignal(str)
    failed = pyqtSignal()

    def __init__(
        self,
        model: WhisperModel,
        audio: np.ndarray,
        language: str,
        settings: DecodeSettings,
    ) -> None:
        super().__init__()
        self._model = model
        self._audio = audio
        self._language = language
        self._settings = settings

    def run(self) -> None:
        from whisper_dictate.audio import peak_normalize

        try:
            audio = self._audio
            if self._settings.normalize:
                audio = peak_normalize(audio)
            segments, _ = self._model.transcribe(
                audio,
                language=self._language,
                beam_size=_BEAM_SIZE,
                hotwords=self._settings.hotwords or None,
                vad_filter=self._settings.vad_filter,
            )
            text = "".join(s.text for s in segments).strip()
            if text:
                _log.info("transcription: %r", text)
                self.transcribed.emit(text)
            else:
                _log.warning("transcription returned empty text")
                self.failed.emit()
        except Exception as exc:
            _log.exception("transcription raised: %s", exc)
            self.failed.emit()


class WhisperEngine(QObject):
    model_ready = pyqtSignal(str)
    model_load_failed = pyqtSignal(str)
    transcription_done = pyqtSignal(str)
    transcription_failed = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._model: WhisperModel | None = None
        self._device: str | None = None
        self._loader = _ModelLoaderThread()
        self._loader.loaded.connect(self._on_model_loaded)
        self._loader.failed.connect(self.model_load_failed)
        self._active_thread: _TranscribeThread | None = None

    def start_loading(self) -> None:
        self._loader.start()

    def _on_model_loaded(self, model: WhisperModel, device: str) -> None:
        self._model = model
        self._device = device
        self.model_ready.emit(device)

    def transcribe(
        self,
        audio: np.ndarray,
        language: str,
        settings: DecodeSettings | None = None,
    ) -> None:
        if settings is None:
            settings = DecodeSettings()
        thread = _TranscribeThread(self._model, audio, language, settings)
        thread.transcribed.connect(self.transcription_done)
        thread.failed.connect(self.transcription_failed)
        thread.finished.connect(thread.deleteLater)
        self._active_thread = thread
        thread.start()

    def cleanup(self) -> None:
        self._loader.wait()
        if self._active_thread is not None and self._active_thread.isRunning():
            self._active_thread.wait()
