import json as _json
import logging
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import keyboard
import numpy as np
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication

from .audio import AudioRecorder
from .config import Config
from .hotkey import HotkeyManager
from .model import DecodeSettings, WhisperEngine
from .window import AppState, FloatingWindow

_STATE_PORT = 19876
# Delay before restoring the user's prior clipboard, so the target app has
# consumed the synthetic Ctrl+V paste before the previous contents return.
_RESTORE_CLIPBOARD_DELAY_MS = 100


def _paste_text(text: str) -> None:
    """Deliver text atomically via the clipboard and a single Ctrl+V.

    Per-character typing (keyboard.write) drops interior spaces and letters
    when the OS input queue can't keep up; one clipboard paste cannot.

    The user's prior clipboard contents are captured first and restored
    after a short delay, so dictation leaves the clipboard as it found it.
    """
    clipboard = QApplication.clipboard()
    saved = clipboard.text()
    clipboard.setText(text)
    keyboard.send("ctrl+v")
    QTimer.singleShot(_RESTORE_CLIPBOARD_DELAY_MS, lambda: clipboard.setText(saved))


def _start_state_server(get_state: callable, on_trigger: callable) -> None:
    def handler_factory(*args, **kwargs):
        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/state":
                    body = _json.dumps({"state": get_state()}).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_POST(self):
                if self.path == "/trigger":
                    on_trigger()
                    self.send_response(200)
                    self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, *args):
                pass

        return _Handler(*args, **kwargs)

    server = HTTPServer(("127.0.0.1", _STATE_PORT), handler_factory)
    threading.Thread(target=server.serve_forever, daemon=True).start()


class _Controller(QObject):
    _trigger = pyqtSignal()

    def __init__(self, config: Config, window: FloatingWindow) -> None:
        super().__init__()
        self._config = config
        self._window = window

        self._recorder = AudioRecorder(self)
        self._hotkey = HotkeyManager(self)
        self._engine = WhisperEngine(self)

        self._hotkey.chord_pressed.connect(self._on_chord_pressed)
        self._trigger.connect(self._on_chord_pressed)
        self._recorder.amplitude_ready.connect(window.push_amplitude)
        self._engine.model_ready.connect(self._on_model_ready)
        self._engine.model_load_failed.connect(self._on_model_load_failed)
        self._engine.transcription_done.connect(self._on_transcription_done)
        self._engine.transcription_failed.connect(self._on_transcription_failed)
        window.became_idle.connect(self._on_became_idle)
        window.quit_requested.connect(self._on_quit_requested)

        # Window starts in LOADING; hotkey enabled only after model is ready
        self._engine.start_loading()

    def _on_model_ready(self, device: str) -> None:
        self._window.set_device(device)
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
            lang = self._config.active_language
            settings = DecodeSettings(
                hotwords=self._config.hotwords.get(lang, ""),
                vad_filter=self._config.vad_filter,
                normalize=self._config.normalize_audio,
            )
            self._engine.transcribe(audio, lang, settings=settings)

    def _on_transcription_done(self, text: str) -> None:
        self._window.set_state(AppState.SUCCESS)
        # 100 ms lets held modifier keys release before the synthetic Ctrl+V
        # fires. Hotkey is already stopped (from _on_recording_stopped); it is
        # restarted only when the window reaches IDLE via _on_became_idle,
        # so synthetic keystrokes can never re-trigger recording.
        QTimer.singleShot(100, lambda: _paste_text(text))

    def _on_transcription_failed(self) -> None:
        self._window.set_state(AppState.FAILURE)

    def _on_became_idle(self) -> None:
        self._hotkey.start()

    def _on_quit_requested(self) -> None:
        logging.debug("Quit requested via close button")
        QApplication.instance().quit()

    def cleanup(self) -> None:
        self._hotkey.stop()
        self._recorder.stop()
        self._engine.cleanup()


def _setup_logging() -> None:
    log_dir = Path.home() / ".whisper-dictate"
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_dir / "app.log", encoding="utf-8")],
    )


def main() -> None:
    _setup_logging()
    config = Config.load()
    app = QApplication(sys.argv)
    window = FloatingWindow(config)
    window.show()

    controller = _Controller(config, window)
    _start_state_server(lambda: window.state.value, controller._trigger.emit)
    app.aboutToQuit.connect(controller.cleanup)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
