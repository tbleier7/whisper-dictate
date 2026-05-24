from __future__ import annotations

import logging
import numpy as np
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from faster_whisper import WhisperModel

_log = logging.getLogger(__name__)

_MODEL_NAME = "large-v3"
_COMPUTE_TYPE = "int8"
_BEAM_SIZE = 5


class _ModelLoaderThread(QThread):
    loaded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def run(self) -> None:
        for device in ("cuda", "cpu"):
            try:
                model = WhisperModel(_MODEL_NAME, device=device, compute_type=_COMPUTE_TYPE)
                # CUDA may load without error but fail at inference time (missing DLLs).
                # Run a tiny test to catch that before we consider the model ready.
                list(model.transcribe(np.zeros(16000, dtype=np.float32), language="en")[0])
                _log.info("model loaded on device=%s", device)
                self.loaded.emit(model)
                return
            except Exception as exc:
                _log.warning("device=%s failed (%s), trying next", device, exc)
        self.failed.emit("Could not load model on any device")


class _TranscribeThread(QThread):
    transcribed = pyqtSignal(str)
    failed = pyqtSignal()

    def __init__(self, model: WhisperModel, audio: np.ndarray, language: str) -> None:
        super().__init__()
        self._model = model
        self._audio = audio
        self._language = language

    def run(self) -> None:
        try:
            segments, _ = self._model.transcribe(
                self._audio, language=self._language, beam_size=_BEAM_SIZE
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
    model_ready = pyqtSignal()
    model_load_failed = pyqtSignal(str)
    transcription_done = pyqtSignal(str)
    transcription_failed = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._model: WhisperModel | None = None
        self._loader = _ModelLoaderThread()
        self._loader.loaded.connect(self._on_model_loaded)
        self._loader.failed.connect(self.model_load_failed)
        self._active_thread: _TranscribeThread | None = None

    def start_loading(self) -> None:
        self._loader.start()

    def _on_model_loaded(self, model: WhisperModel) -> None:
        self._model = model
        self.model_ready.emit()

    def transcribe(self, audio: np.ndarray, language: str) -> None:
        thread = _TranscribeThread(self._model, audio, language)
        thread.transcribed.connect(self.transcription_done)
        thread.failed.connect(self.transcription_failed)
        thread.finished.connect(thread.deleteLater)
        self._active_thread = thread
        thread.start()

    def cleanup(self) -> None:
        self._loader.wait()
        if self._active_thread is not None and self._active_thread.isRunning():
            self._active_thread.wait()
