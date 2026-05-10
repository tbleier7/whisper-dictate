from __future__ import annotations

import numpy as np
import pytest
from unittest import mock

from whisper_dictate.app import _Controller
from whisper_dictate.config import Config
from whisper_dictate.window import AppState, FloatingWindow


@pytest.fixture
def config():
    return Config(
        hotkey="ctrl+alt+space",
        languages=["de", "en"],
        active_language="de",
        window_position={"x": 0, "y": 0},
    )


@pytest.fixture
def ctrl(qtbot, config):
    with (
        mock.patch("whisper_dictate.app.WhisperEngine"),
        mock.patch("whisper_dictate.app.AudioRecorder") as MockRecorder,
        mock.patch("whisper_dictate.app.HotkeyManager"),
        mock.patch("whisper_dictate.config.Config.save"),
    ):
        MockRecorder.return_value.stop.return_value = np.zeros(0, dtype="float32")
        window = FloatingWindow(config)
        qtbot.addWidget(window)
        controller = _Controller(config, window)
        controller._on_model_ready()
        yield controller, window


def test_text_injected_after_transcription(qtbot, ctrl):
    controller, _ = ctrl
    controller._on_recording_started()
    controller._on_recording_stopped()

    with mock.patch("keyboard.write") as mock_write:
        controller._on_transcription_done("hello world")
        qtbot.wait(200)
        mock_write.assert_called_once_with("hello world", delay=0)


def test_window_returns_to_idle_after_success(qtbot, ctrl):
    controller, window = ctrl
    controller._on_recording_started()
    controller._on_recording_stopped()

    with mock.patch("keyboard.write"):
        controller._on_transcription_done("hello world")
        qtbot.wait(700)
        assert window.state == AppState.IDLE


def test_window_returns_to_idle_after_failure(qtbot, ctrl):
    controller, window = ctrl
    controller._on_recording_started()
    controller._on_recording_stopped()

    controller._on_transcription_failed()
    qtbot.wait(700)
    assert window.state == AppState.IDLE


def test_new_recording_accepted_after_full_cycle(qtbot, ctrl):
    controller, window = ctrl
    controller._on_recording_started()
    controller._on_recording_stopped()

    with mock.patch("keyboard.write"):
        controller._on_transcription_done("hello world")
        qtbot.wait(700)

    controller._on_recording_started()
    assert window.state == AppState.RECORDING


def test_hotkey_stopped_during_transcription(ctrl):
    controller, _ = ctrl
    mock_hotkey = controller._hotkey

    controller._on_recording_started()
    controller._on_recording_stopped()

    mock_hotkey.stop.assert_called_once()


def test_hotkey_restarted_after_idle(qtbot, ctrl):
    controller, _ = ctrl
    mock_hotkey = controller._hotkey

    controller._on_recording_started()
    controller._on_recording_stopped()

    with mock.patch("keyboard.write"):
        controller._on_transcription_done("hello")
        qtbot.wait(700)

    # start() called once at model ready + once after idle transition
    assert mock_hotkey.start.call_count == 2
