from __future__ import annotations

import numpy as np
import pytest
from unittest import mock

from whisper_dictate.app import _Controller
from whisper_dictate.window import AppState, FloatingWindow


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
        controller._on_model_ready("cuda")
        yield controller, window


def test_text_injected_after_transcription(qtbot, ctrl, clipboard_capture):
    controller, _ = ctrl
    controller._on_chord_pressed()  # IDLE -> RECORDING
    controller._on_chord_pressed()  # RECORDING -> LOADING

    controller._on_transcription_done("hello world")
    # The paste fires ~100 ms after transcription; sample before the restore
    # timer returns the prior clipboard contents.
    qtbot.waitUntil(
        lambda: clipboard_capture.clipboard.text() == "hello world", timeout=1000
    )
    clipboard_capture.keyboard.send.assert_called_once_with("ctrl+v")


def test_window_returns_to_idle_after_success(qtbot, ctrl, clipboard_capture):
    controller, window = ctrl
    controller._on_chord_pressed()
    controller._on_chord_pressed()

    controller._on_transcription_done("hello world")
    qtbot.wait(700)
    assert window.state == AppState.IDLE


def test_window_returns_to_idle_after_failure(qtbot, ctrl):
    controller, window = ctrl
    controller._on_chord_pressed()
    controller._on_chord_pressed()

    controller._on_transcription_failed()
    qtbot.wait(700)
    assert window.state == AppState.IDLE


def test_new_recording_accepted_after_full_cycle(qtbot, ctrl, clipboard_capture):
    controller, window = ctrl
    controller._on_chord_pressed()
    controller._on_chord_pressed()

    controller._on_transcription_done("hello world")
    qtbot.wait(700)

    controller._on_chord_pressed()
    assert window.state == AppState.RECORDING


def test_hotkey_stopped_during_transcription(ctrl):
    controller, _ = ctrl
    mock_hotkey = controller._hotkey

    controller._on_chord_pressed()
    controller._on_chord_pressed()

    mock_hotkey.stop.assert_called_once()


def test_hotkey_restarted_after_idle(qtbot, ctrl, clipboard_capture):
    controller, _ = ctrl
    mock_hotkey = controller._hotkey

    controller._on_chord_pressed()
    controller._on_chord_pressed()

    controller._on_transcription_done("hello")
    qtbot.wait(700)

    # start() called once at model ready + once after idle transition
    assert mock_hotkey.start.call_count == 2


def test_window_enters_load_failed_when_model_load_fails(qtbot, config):
    with (
        mock.patch("whisper_dictate.app.WhisperEngine"),
        mock.patch("whisper_dictate.app.AudioRecorder"),
        mock.patch("whisper_dictate.app.HotkeyManager"),
        mock.patch("whisper_dictate.config.Config.save"),
    ):
        window = FloatingWindow(config)
        qtbot.addWidget(window)
        controller = _Controller(config, window)

        controller._on_model_load_failed("cuda missing")

        assert window.state == AppState.LOAD_FAILED


def test_hotkey_not_started_when_model_load_fails(qtbot, config):
    with (
        mock.patch("whisper_dictate.app.WhisperEngine"),
        mock.patch("whisper_dictate.app.AudioRecorder"),
        mock.patch("whisper_dictate.app.HotkeyManager"),
        mock.patch("whisper_dictate.config.Config.save"),
    ):
        window = FloatingWindow(config)
        qtbot.addWidget(window)
        controller = _Controller(config, window)

        controller._on_model_load_failed("cuda missing")

        controller._hotkey.start.assert_not_called()


def test_hotkey_restarted_after_failure_path(qtbot, ctrl, clipboard_capture):
    controller, window = ctrl
    mock_hotkey = controller._hotkey

    controller._on_chord_pressed()
    controller._on_chord_pressed()
    controller._on_transcription_failed()
    qtbot.wait(700)

    assert window.state == AppState.IDLE
    # start() called once at model ready + once after idle transition from failure flash
    assert mock_hotkey.start.call_count == 2


def test_chord_ignored_during_non_idle_non_recording_states(qtbot, ctrl, clipboard_capture):
    controller, window = ctrl

    controller._on_chord_pressed()  # IDLE -> RECORDING
    controller._on_chord_pressed()  # RECORDING -> LOADING
    assert window.state == AppState.LOADING

    # Chord during LOADING is ignored.
    controller._on_chord_pressed()
    assert window.state == AppState.LOADING

    controller._on_transcription_done("hello")
    # SUCCESS flash — chord must not re-trigger recording.
    controller._on_chord_pressed()
    assert window.state == AppState.SUCCESS


def test_language_click_during_loading_is_ignored(qtbot, ctrl):
    controller, window = ctrl

    controller._on_chord_pressed()
    controller._on_chord_pressed()
    assert window.state == AppState.LOADING

    original_lang = controller._config.active_language
    window._cycle_language()

    assert controller._config.active_language == original_lang


def test_language_click_during_recording_is_ignored(qtbot, ctrl):
    controller, window = ctrl

    controller._on_chord_pressed()
    assert window.state == AppState.RECORDING

    original_lang = controller._config.active_language
    window._cycle_language()

    assert controller._config.active_language == original_lang


def test_quit_requested_quits_application(qtbot, ctrl):
    controller, window = ctrl

    with mock.patch("whisper_dictate.app.QApplication") as MockQApp:
        window.quit_requested.emit()

    MockQApp.instance.return_value.quit.assert_called_once()


def test_cleanup_stops_all_subsystems(ctrl):
    controller, _ = ctrl

    controller.cleanup()

    controller._hotkey.stop.assert_called()
    controller._recorder.stop.assert_called()
    controller._engine.cleanup.assert_called()


def test_transcribe_receives_decode_settings_from_config(ctrl):
    """Pressing hotkey twice passes a DecodeSettings built from config."""
    from whisper_dictate.model import DecodeSettings

    controller, _ = ctrl
    # Set recognisable values on config so we can assert they're forwarded.
    controller._config.hotwords = {"de": "schaute Scherbe", "en": ""}
    controller._config.vad_filter = True
    controller._config.normalize_audio = True
    controller._config.active_language = "de"

    controller._on_chord_pressed()  # IDLE -> RECORDING
    controller._on_chord_pressed()  # RECORDING -> LOADING (fires transcribe)

    call_kwargs = controller._engine.transcribe.call_args.kwargs
    settings = call_kwargs.get("settings")
    assert settings is not None, "transcribe was not called with a settings= kwarg"
    assert isinstance(settings, DecodeSettings)
    assert settings.hotwords == "schaute Scherbe"
    assert settings.vad_filter is True
    assert settings.normalize is True


def test_transcribe_settings_use_active_language_hotwords(ctrl):
    """The active language's hotwords slice is extracted, not the full dict."""
    from whisper_dictate.model import DecodeSettings

    controller, _ = ctrl
    controller._config.hotwords = {"de": "schaute", "en": "shard"}
    controller._config.active_language = "en"

    controller._on_chord_pressed()
    controller._on_chord_pressed()

    settings = controller._engine.transcribe.call_args.kwargs.get("settings")
    assert isinstance(settings, DecodeSettings)
    assert settings.hotwords == "shard"


def test_calibrate_requested_while_idle_stops_hotkey(qtbot, ctrl):
    """calibrate_requested while idle stops the global hotkey."""
    controller, window = ctrl
    mock_hotkey = controller._hotkey
    mock_hotkey.stop.reset_mock()

    # Patch CalibrationWindow so it doesn't actually open a real window.
    with mock.patch("whisper_dictate.app.CalibrationWindow") as MockCalWin:
        MockCalWin.return_value.show = mock.Mock()
        window.calibrate_requested.emit()

    mock_hotkey.stop.assert_called()


def test_calibrate_requested_ignored_when_not_idle(qtbot, ctrl):
    """calibrate_requested while recording is silently ignored."""
    controller, window = ctrl
    mock_hotkey = controller._hotkey
    mock_hotkey.stop.reset_mock()

    controller._on_chord_pressed()  # IDLE -> RECORDING
    assert window.state == AppState.RECORDING

    stop_count_before = mock_hotkey.stop.call_count
    with mock.patch("whisper_dictate.app.CalibrationWindow"):
        window.calibrate_requested.emit()

    # stop should not have been called again for calibration
    assert mock_hotkey.stop.call_count == stop_count_before


def test_hotkey_restarted_when_calibration_window_closes(qtbot, ctrl):
    """Closing the calibration window re-enables the global hotkey."""
    controller, window = ctrl
    mock_hotkey = controller._hotkey
    mock_hotkey.start.reset_mock()

    cal_win_instance = None

    def capture_cal_win(*args, **kwargs):
        nonlocal cal_win_instance
        cal_win_instance = mock.MagicMock()
        cal_win_instance.show = mock.Mock()
        # Wire destroyed signal so controller can reconnect
        from PyQt6.QtCore import QObject, pyqtSignal
        return cal_win_instance

    with mock.patch("whisper_dictate.app.CalibrationWindow", side_effect=capture_cal_win):
        window.calibrate_requested.emit()

    assert cal_win_instance is not None
    # Simulate the window being closed: controller should restart hotkey
    # The controller connects to cal_win.destroyed or closeEvent; simulate via close callback
    controller._on_calibration_closed()

    mock_hotkey.start.assert_called()
