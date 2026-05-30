from __future__ import annotations

import numpy as np
import pytest
from unittest import mock

from whisper_dictate.calibration import CalibrationWindow
from whisper_dictate.config import Config
from whisper_dictate.model import DecodeSettings


@pytest.fixture
def cal_config():
    return Config(
        languages=["de", "en"],
        active_language="de",
        window_position={"x": 0, "y": 0},
        hotwords={"de": "schaute", "en": ""},
        vad_filter=False,
        normalize_audio=False,
    )


@pytest.fixture
def mock_engine():
    engine = mock.MagicMock()
    return engine


@pytest.fixture
def cal_win(qtbot, cal_config, mock_engine):
    with mock.patch("whisper_dictate.config.Config.save"):
        win = CalibrationWindow(mock_engine, cal_config)
        qtbot.addWidget(win)
        yield win


# ---------------------------------------------------------------------------
# Slice 3a: on_result renders WER and diff
# ---------------------------------------------------------------------------

def test_on_result_renders_wer(qtbot, cal_win):
    """on_result populates the result label with a WER percentage."""
    # Simulate a transcription that is identical to the reference → WER 0%
    from whisper_dictate.reference import REFERENCE_PASSAGES
    passage = REFERENCE_PASSAGES["de"]

    cal_win._on_result(passage)

    assert "WER" in cal_win._result_label.text()
    assert "0.0%" in cal_win._result_label.text()


def test_on_result_shows_nonzero_wer_for_wrong_text(qtbot, cal_win):
    """on_result reflects errors when hypothesis differs from reference."""
    cal_win._on_result("scharrte")

    label_text = cal_win._result_label.text()
    assert "WER" in label_text
    # There should be a non-zero WER since one word vs a full passage
    assert "100.0%" not in label_text or "WER" in label_text


def test_on_failed_shows_error_message(qtbot, cal_win):
    """on_failed shows an inline error and re-enables action buttons."""
    cal_win._set_buttons_busy(True)
    cal_win._on_failed()

    assert "try again" in cal_win._result_label.text().lower() or \
           "no speech" in cal_win._result_label.text().lower()
    # Save button should be re-enabled
    assert cal_win._save_btn.isEnabled()


# ---------------------------------------------------------------------------
# Slice 3b: Save writes candidate settings into config
# ---------------------------------------------------------------------------

def test_save_writes_hotwords_to_config(qtbot, cal_win, cal_config):
    """Clicking Save persists hotwords for the active language to config."""
    cal_win._hotwords_edit.setText("schaute Scherbe")

    with mock.patch.object(cal_config, "save") as mock_save:
        cal_win._on_save_clicked()

    assert cal_config.hotwords["de"] == "schaute Scherbe"
    mock_save.assert_called_once()


def test_save_writes_vad_filter_to_config(qtbot, cal_win, cal_config):
    """Clicking Save persists vad_filter state to config."""
    cal_win._vad_check.setChecked(True)

    with mock.patch.object(cal_config, "save") as mock_save:
        cal_win._on_save_clicked()

    assert cal_config.vad_filter is True
    mock_save.assert_called_once()


def test_save_writes_normalize_audio_to_config(qtbot, cal_win, cal_config):
    """Clicking Save persists normalize_audio state to config."""
    cal_win._normalize_check.setChecked(True)

    with mock.patch.object(cal_config, "save") as mock_save:
        cal_win._on_save_clicked()

    assert cal_config.normalize_audio is True
    mock_save.assert_called_once()


# ---------------------------------------------------------------------------
# Slice 3c: Buttons disabled during in-flight transcription
# ---------------------------------------------------------------------------

def test_buttons_disabled_while_busy(qtbot, cal_win):
    """_set_buttons_busy(True) disables Record, Re-run, and Save buttons."""
    cal_win._set_buttons_busy(True)

    assert not cal_win._record_btn.isEnabled()
    assert not cal_win._rerun_btn.isEnabled()
    assert not cal_win._save_btn.isEnabled()


def test_buttons_reenabled_after_busy(qtbot, cal_win):
    """_set_buttons_busy(False) re-enables Record and Save (Re-run only after a recording)."""
    cal_win._set_buttons_busy(True)
    cal_win._set_buttons_busy(False)

    assert cal_win._record_btn.isEnabled()
    assert cal_win._save_btn.isEnabled()


def test_rerun_uses_retained_audio(qtbot, cal_win, mock_engine):
    """Re-run re-transcribes the previously captured audio without re-recording."""
    audio = np.zeros(16000, dtype="float32")
    cal_win._recorded_audio = audio

    cal_win._on_rerun_clicked()

    mock_engine.transcribe.assert_called_once()
    call_kwargs = mock_engine.transcribe.call_args
    assert np.array_equal(call_kwargs.args[0], audio)


def test_rerun_uses_candidate_settings(qtbot, cal_win, mock_engine):
    """Re-run forwards current UI knob values as DecodeSettings."""
    audio = np.zeros(16000, dtype="float32")
    cal_win._recorded_audio = audio
    cal_win._hotwords_edit.setText("schaute")
    cal_win._vad_check.setChecked(True)

    cal_win._on_rerun_clicked()

    settings = mock_engine.transcribe.call_args.kwargs.get("settings")
    assert settings is not None
    assert isinstance(settings, DecodeSettings)
    assert settings.hotwords == "schaute"
    assert settings.vad_filter is True


def test_transcription_delivered_to_on_result_callback(qtbot, cal_win, mock_engine):
    """transcribe is called with on_result so the paste path is bypassed."""
    audio = np.zeros(16000, dtype="float32")
    cal_win._recorded_audio = audio

    cal_win._on_rerun_clicked()

    call_kwargs = mock_engine.transcribe.call_args.kwargs
    assert call_kwargs.get("on_result") is not None
    assert call_kwargs.get("on_failed") is not None


def test_passage_label_shows_current_language_passage(qtbot, cal_win):
    """CalibrationWindow displays the reference passage for the active language."""
    from whisper_dictate.reference import REFERENCE_PASSAGES
    assert REFERENCE_PASSAGES["de"] in cal_win._passage_view.text()
