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
        self._hotkey = HotkeyManager(self)
        self._engine = WhisperEngine(self)

        self._hotkey.chord_pressed.connect(self._on_chord_pressed)
        self._recorder.amplitude_ready.connect(window.push_amplitude)
        self._engine.model_ready.connect(self._on_model_ready)
        self._engine.model_load_failed.connect(self._on_model_load_failed)
        self._engine.transcription_done.connect(self._on_transcription_done)
        self._engine.transcription_failed.connect(self._on_transcription_failed)
        window.became_idle.connect(self._on_became_idle)

        # Window starts in LOADING; hotkey enabled only after model is ready
        self._engine.start_loading()

    def _on_model_ready(self) -> None:
        self._window.set_state(AppState.IDLE)
        self._hotkey.start()

    def _on_model_load_failed(self, _error: str) -> None:
        self._window.set_state(AppState.LOAD_FAILED)

    def _on_chord_pressed(self) -> None:
        state = self._window.state
        if state == AppState.IDLE:
            self._window.set_state(AppState.RECORDING)
            self._recorder.start()
        elif state == AppState.RECORDING:
            self._hotkey.stop()
            audio = self._recorder.stop()
            self._window.set_state(AppState.LOADING)
            self._engine.transcribe(audio, self._config.active_language)

    def _on_transcription_done(self, text: str) -> None:
        self._window.set_state(AppState.SUCCESS)
        # 100 ms lets held modifier keys release before SendInput fires.
        # Hotkey is already stopped (from _on_recording_stopped); it is
        # restarted only when the window reaches IDLE via _on_became_idle,
        # so synthetic keystrokes in the text can never re-trigger recording.
        QTimer.singleShot(100, lambda: keyboard.write(text, delay=0))

    def _on_transcription_failed(self) -> None:
        self._window.set_state(AppState.FAILURE)

    def _on_became_idle(self) -> None:
        self._hotkey.start()

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
