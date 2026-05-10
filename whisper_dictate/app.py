import sys

import keyboard
import numpy as np
from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QApplication

from .audio import AudioRecorder
from .config import Config
from .hotkey import HotkeyManager
from .model import WhisperEngine
from .window import AppState, FloatingWindow


class _Controller(QObject):
    def __init__(self, config: Config, window: FloatingWindow) -> None:
        super().__init__()
        self._config = config
        self._window = window

        self._recorder = AudioRecorder(self)
        self._hotkey = HotkeyManager(config.hotkey, self)
        self._engine = WhisperEngine(self)

        self._hotkey.recording_started.connect(self._on_recording_started)
        self._hotkey.recording_stopped.connect(self._on_recording_stopped)
        self._recorder.amplitude_ready.connect(window.push_amplitude)
        self._engine.model_ready.connect(self._on_model_ready)
        self._engine.transcription_done.connect(self._on_transcription_done)
        self._engine.transcription_failed.connect(self._on_transcription_failed)

        # Window starts in LOADING; hotkey enabled only after model is ready
        self._engine.start_loading()

    def _on_model_ready(self) -> None:
        self._window.set_state(AppState.IDLE)
        self._hotkey.start()

    def _on_recording_started(self) -> None:
        if self._window.state != AppState.IDLE:
            return
        self._window.set_state(AppState.RECORDING)
        self._recorder.start()

    def _on_recording_stopped(self) -> None:
        if self._window.state != AppState.RECORDING:
            return
        audio = self._recorder.stop()
        self._window.set_state(AppState.LOADING)
        self._engine.transcribe(audio, self._config.active_language)

    def _on_transcription_done(self, text: str) -> None:
        self._window.set_state(AppState.SUCCESS)
        # Delay lets any held modifier keys fully release before SendInput events fire.
        # Stop hotkey hooks during injection so synthetic keystrokes (e.g. space in the
        # transcribed text) cannot re-trigger the recording hotkey while Ctrl+Alt are
        # still physically held — which would cause a spurious second transcription cycle.
        def _inject() -> None:
            self._hotkey.stop()
            try:
                keyboard.write(text, delay=0)
            finally:
                self._hotkey.start()
        QTimer.singleShot(100, _inject)

    def _on_transcription_failed(self) -> None:
        self._window.set_state(AppState.FAILURE)

    def cleanup(self) -> None:
        self._hotkey.stop()
        self._recorder.stop()
        self._engine.cleanup()


def main() -> None:
    config = Config.load()
    app = QApplication(sys.argv)
    window = FloatingWindow(config)
    window.show()

    controller = _Controller(config, window)
    app.aboutToQuit.connect(controller.cleanup)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
