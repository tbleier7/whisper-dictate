from __future__ import annotations

from unittest import mock

import pytest

from whisper_dictate.window import AppState, FloatingWindow


@pytest.fixture
def window(qtbot, config):
    with mock.patch("whisper_dictate.config.Config.save"):
        w = FloatingWindow(config)
        qtbot.addWidget(w)
        yield w


def test_cycle_language_changes_active_language(window, config):
    config.active_language = "de"
    window.set_state(AppState.IDLE)

    window._cycle_language()

    assert config.active_language == "en"


def test_cycle_language_wraps_around(window, config):
    config.active_language = "en"
    window.set_state(AppState.IDLE)

    window._cycle_language()

    assert config.active_language == "de"


def test_cycle_language_persists_immediately(window, config):
    window.set_state(AppState.IDLE)

    with mock.patch.object(config, "save") as mock_save:
        window._cycle_language()
        mock_save.assert_called_once()


def test_cycle_language_ignored_outside_idle(window, config):
    config.active_language = "de"
    window.set_state(AppState.RECORDING)

    with mock.patch.object(config, "save") as mock_save:
        window._cycle_language()

    assert config.active_language == "de"
    mock_save.assert_not_called()


def test_push_amplitude_only_in_recording(window):
    window.set_state(AppState.IDLE)
    with mock.patch.object(window._waveform, "push_amplitude") as mock_push:
        window.push_amplitude(0.5)
        mock_push.assert_not_called()

    window.set_state(AppState.RECORDING)
    with mock.patch.object(window._waveform, "push_amplitude") as mock_push:
        window.push_amplitude(0.5)
        mock_push.assert_called_once_with(0.5)


def test_became_idle_emitted_after_success_flash(qtbot, window):
    window.set_state(AppState.IDLE)
    window.set_state(AppState.SUCCESS)

    with qtbot.waitSignal(window.became_idle, timeout=1000):
        pass

    assert window.state == AppState.IDLE


def test_became_idle_emitted_after_failure_flash(qtbot, window):
    window.set_state(AppState.IDLE)
    window.set_state(AppState.FAILURE)

    with qtbot.waitSignal(window.became_idle, timeout=1000):
        pass

    assert window.state == AppState.IDLE


def test_load_failed_state_is_persistent(qtbot, window):
    window.set_state(AppState.LOAD_FAILED)

    qtbot.wait(700)

    assert window.state == AppState.LOAD_FAILED
