from __future__ import annotations

import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QObject, pyqtSignal

_SAMPLE_RATE = 16_000
_BLOCK_SIZE = 1_024
_AMP_SCALE = 8.0  # scales RMS to 0–1 range for typical speech levels


class AudioRecorder(QObject):
    amplitude_ready = pyqtSignal(float)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._frames: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None

    def start(self) -> None:
        self._frames = []
        self._stream = sd.InputStream(
            samplerate=_SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=_BLOCK_SIZE,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if self._frames:
            return np.concatenate(self._frames).flatten()
        return np.zeros(0, dtype="float32")

    def _callback(
        self,
        indata: np.ndarray,
        frames: int,
        time,
        status,
    ) -> None:
        chunk = indata[:, 0].copy()
        self._frames.append(chunk)
        rms = float(np.sqrt(np.mean(chunk**2)))
        self.amplitude_ready.emit(min(1.0, rms * _AMP_SCALE))
