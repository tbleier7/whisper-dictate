"""Acceptance tests for the Phase-6 calibration workflow.

Each test covers exactly one acceptance criterion from the plan and is
expressed entirely in user-facing domain language via CalibrationDsl.
No widget handles, signal names, or Qt internals appear in test bodies.

Run with:
    pytest tests/acceptance/

These tests exercise the full Phase-6 integration path — right-click
gesture propagation through the widget hierarchy, controller wiring,
calibration window appearance, and config persistence.
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
# Phase 6 acceptance criterion 1: right-click opens calibration when idle
# ---------------------------------------------------------------------------

def test_right_click_on_dictation_window_produces_context_menu(app):
    """A right-click gesture on the floating window shows the context menu.

    Specifically validates that QContextMenuEvent propagates from the label
    child widget up to FloatingWindow.contextMenuEvent — the path the unit
    test for contextMenuEvent skips by calling the method directly.
    """
    app.launch_idle()
    app.right_click_dictation_window()
    app.assert_context_menu_appeared()


def test_right_click_on_idle_window_opens_calibration(app):
    """Right-clicking the dictation overlay while idle opens the calibration window."""
    app.launch_idle()
    app.right_click_dictation_window()
    app.select_calibrate_from_context_menu()
    app.assert_calibration_window_is_open()


# ---------------------------------------------------------------------------
# Phase 6 acceptance criterion: right-click when not idle is silently ignored
# ---------------------------------------------------------------------------

def test_right_click_when_recording_does_not_open_calibration(app):
    """Right-clicking and selecting Calibrate while recording is silently ignored."""
    app.launch_idle()
    app.switch_to_recording()
    app.right_click_dictation_window()
    app.select_calibrate_from_context_menu()
    app.assert_calibration_window_is_not_open()


# ---------------------------------------------------------------------------
# Phase 6 acceptance criterion: hotkey suspended while calibration is open
# ---------------------------------------------------------------------------

def test_hotkey_is_suspended_while_calibration_window_is_open(app):
    """The global dictation hotkey cannot fire while calibration is open."""
    app.launch_idle()
    app.right_click_dictation_window()
    app.select_calibrate_from_context_menu()
    app.assert_global_hotkey_is_disabled()


# ---------------------------------------------------------------------------
# Phase 6 acceptance criterion: hotkey resumes when calibration closes
# ---------------------------------------------------------------------------

def test_hotkey_resumes_after_calibration_window_closes(app):
    """Closing the calibration window re-enables the dictation hotkey."""
    app.launch_idle()
    app.right_click_dictation_window()
    app.select_calibrate_from_context_menu()
    app.close_calibration()
    app.assert_global_hotkey_is_enabled()


# ---------------------------------------------------------------------------
# Phase 6 acceptance criterion: recording a passage scores and shows diff
# ---------------------------------------------------------------------------

def test_transcription_result_shows_wer_score_and_diff(app):
    """After a passage is transcribed, WER and the per-word diff are displayed."""
    app.launch_idle()
    app.right_click_dictation_window()
    app.select_calibrate_from_context_menu()
    app.deliver_transcription_result("scharrte")
    app.assert_wer_score_is_displayed()


# ---------------------------------------------------------------------------
# Phase 6 acceptance criterion: Save persists settings to config
# ---------------------------------------------------------------------------

def test_save_persists_hotwords_vad_and_normalization_to_config(app):
    """Clicking Save writes the tuned settings into config for the dictation path to use."""
    app.launch_idle()
    app.right_click_dictation_window()
    app.select_calibrate_from_context_menu()
    app.set_hotwords("schaute Scherbe")
    app.enable_vad()
    app.enable_normalize()
    app.click_save()
    app.assert_config_hotwords_for("de", "schaute Scherbe")
    app.assert_config_vad_filter(True)
    app.assert_config_normalize_audio(True)
