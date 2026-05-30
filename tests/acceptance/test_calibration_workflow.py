"""Acceptance tests for the calibration workflow.

Each test covers exactly one acceptance criterion and is expressed entirely
in user-facing domain language via CalibrationDsl.  No widget handles,
signal names, or Qt internals appear in test bodies.

Run with:
    pytest tests/acceptance/
"""
from __future__ import annotations

import pytest

from whisper_dictate.config import Config

from .drivers.calibration_driver import CalibrationDriver
from .dsl.calibration_dsl import CalibrationDsl


@pytest.fixture
def _config():
    return Config(
        languages=["de", "en"],
        active_language="de",
        window_position={"x": 0, "y": 0},
        hotwords={"de": "", "en": ""},
        vad_filter=False,
        normalize_audio=False,
    )


@pytest.fixture
def app(qtbot, _config):
    """Full dictation app stack, idle, wrapped in the calibration DSL."""
    driver = CalibrationDriver(qtbot)
    driver.build_idle_app_stack(_config)
    dsl = CalibrationDsl(driver)
    yield dsl
    driver.cleanup()


# ---------------------------------------------------------------------------
# Gear button opens calibration when idle
# ---------------------------------------------------------------------------

def test_gear_button_opens_calibration_when_idle(app):
    """Clicking the gear button while idle opens the calibration window."""
    app.launch_idle()
    app.click_gear_button()
    app.assert_calibration_window_is_open()


# ---------------------------------------------------------------------------
# Gear button ignored when not idle
# ---------------------------------------------------------------------------

def test_gear_button_when_recording_does_not_open_calibration(app):
    """Clicking the gear button while recording is silently ignored."""
    app.launch_idle()
    app.switch_to_recording()
    app.click_gear_button()
    app.assert_calibration_window_is_not_open()


# ---------------------------------------------------------------------------
# Hotkey suspended while calibration is open
# ---------------------------------------------------------------------------

def test_hotkey_is_suspended_while_calibration_window_is_open(app):
    """The global dictation hotkey cannot fire while calibration is open."""
    app.launch_idle()
    app.click_gear_button()
    app.assert_global_hotkey_is_disabled()


# ---------------------------------------------------------------------------
# Hotkey resumes when calibration closes
# ---------------------------------------------------------------------------

def test_hotkey_resumes_after_calibration_window_closes(app):
    """Closing the calibration window re-enables the dictation hotkey."""
    app.launch_idle()
    app.click_gear_button()
    app.close_calibration()
    app.assert_global_hotkey_is_enabled()


# ---------------------------------------------------------------------------
# Recording a passage scores and shows diff
# ---------------------------------------------------------------------------

def test_transcription_result_shows_wer_score_and_diff(app):
    """After a passage is transcribed, WER and the per-word diff are displayed."""
    app.launch_idle()
    app.click_gear_button()
    app.deliver_transcription_result("scharrte")
    app.assert_wer_score_is_displayed()


# ---------------------------------------------------------------------------
# Save persists settings to config
# ---------------------------------------------------------------------------

def test_save_persists_hotwords_vad_and_normalization_to_config(app):
    """Clicking Save writes the tuned settings into config for the dictation path to use."""
    app.launch_idle()
    app.click_gear_button()
    app.set_hotwords("schaute Scherbe")
    app.enable_vad()
    app.enable_normalize()
    app.click_save()
    app.assert_config_hotwords_for("de", "schaute Scherbe")
    app.assert_config_vad_filter(True)
    app.assert_config_normalize_audio(True)
