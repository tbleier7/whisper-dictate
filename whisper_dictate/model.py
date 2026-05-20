from __future__ import annotations

import numpy as np
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from faster_whisper import WhisperModel

_MODEL_NAME = "large-v3"
_COMPUTE_TYPE = "int8"
_BEAM_SIZE = 5


class _ModelLoaderThread(QThread):
    loaded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def run(self) -> None:
        try:
            model = WhisperModel(_MODEL_NAME, device="cuda", compute_type=_COMPUTE_TYPE)
        except Exception:
            try:
                model = WhisperModel(_MODEL_NAME, device="cpu", compute_type=_COMPUTE_TYPE)
            except Exception as e:
                self.failed.emit(str(e))
                return
        self.loaded.emit(model)


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
                self.transcribed.emit(text)
            else:
                self.failed.emit()
        except Exception:
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
