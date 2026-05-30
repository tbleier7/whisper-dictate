from __future__ import annotations

from unittest import mock

import numpy as np
import pytest

from whisper_dictate.model import WhisperEngine, DecodeSettings


def _segment(text: str):
    seg = mock.MagicMock()
    seg.text = text
    return seg


def _make_engine_with_loaded_model(qtbot, model_mock):
    with mock.patch("whisper_dictate.model.WhisperModel") as MockModel:
        MockModel.return_value = model_mock
        engine = WhisperEngine()
        with qtbot.waitSignal(engine.model_ready, timeout=5000):
            engine.start_loading()
    return engine


def test_model_ready_emitted_on_successful_load(qtbot):
    with mock.patch("whisper_dictate.model.WhisperModel") as MockModel:
        MockModel.return_value = mock.MagicMock()
        engine = WhisperEngine()
        with qtbot.waitSignal(engine.model_ready, timeout=5000):
            engine.start_loading()


def test_loads_on_cuda_when_available(qtbot):
    with mock.patch("whisper_dictate.model.WhisperModel") as MockModel:
        MockModel.return_value = mock.MagicMock()
        engine = WhisperEngine()
        with qtbot.waitSignal(engine.model_ready, timeout=5000):
            engine.start_loading()
        assert MockModel.call_count == 1
        assert MockModel.call_args.kwargs["device"] == "cuda"


def test_falls_back_to_cpu_when_cuda_fails(qtbot):
    with mock.patch("whisper_dictate.model.WhisperModel") as MockModel:
        MockModel.side_effect = [RuntimeError("no cuda"), mock.MagicMock()]
        engine = WhisperEngine()
        with qtbot.waitSignal(engine.model_ready, timeout=5000):
            engine.start_loading()
        assert MockModel.call_count == 2
        assert MockModel.call_args_list[0].kwargs["device"] == "cuda"
        assert MockModel.call_args_list[1].kwargs["device"] == "cpu"


def test_load_failed_when_both_cuda_and_cpu_fail(qtbot):
    with mock.patch("whisper_dictate.model.WhisperModel") as MockModel:
        MockModel.side_effect = [RuntimeError("no cuda"), RuntimeError("cpu broken")]
        engine = WhisperEngine()
        with qtbot.waitSignal(engine.model_load_failed, timeout=5000) as blocker:
            engine.start_loading()
        assert MockModel.call_count == 2
        assert "cpu broken" in blocker.args[0]


def test_model_load_failed_emitted_when_constructor_raises(qtbot):
    with mock.patch("whisper_dictate.model.WhisperModel", side_effect=RuntimeError("no cuda")):
        engine = WhisperEngine()
        with qtbot.waitSignal(engine.model_load_failed, timeout=5000) as blocker:
            engine.start_loading()
        assert "no cuda" in blocker.args[0]


def test_model_ready_not_emitted_when_load_fails(qtbot):
    with mock.patch("whisper_dictate.model.WhisperModel", side_effect=RuntimeError("boom")):
        engine = WhisperEngine()
        with qtbot.assertNotEmitted(engine.model_ready, wait=500):
            with qtbot.waitSignal(engine.model_load_failed, timeout=5000):
                engine.start_loading()


def test_transcribe_emits_done_with_concatenated_text(qtbot):
    model = mock.MagicMock()
    model.transcribe.return_value = (
        [_segment("hello "), _segment("world")],
        None,
    )
    engine = _make_engine_with_loaded_model(qtbot, model)

    audio = np.zeros(16000, dtype=np.float32)
    with qtbot.waitSignal(engine.transcription_done, timeout=5000) as blocker:
        engine.transcribe(audio, "de")

    assert blocker.args[0] == "hello world"


def test_transcribe_emits_failed_when_segments_empty(qtbot):
    model = mock.MagicMock()
    model.transcribe.return_value = ([], None)
    engine = _make_engine_with_loaded_model(qtbot, model)

    audio = np.zeros(16000, dtype=np.float32)
    with qtbot.waitSignal(engine.transcription_failed, timeout=5000):
        engine.transcribe(audio, "de")


def test_transcribe_emits_failed_when_segments_only_whitespace(qtbot):
    model = mock.MagicMock()
    model.transcribe.return_value = ([_segment("  "), _segment("\n")], None)
    engine = _make_engine_with_loaded_model(qtbot, model)

    audio = np.zeros(16000, dtype=np.float32)
    with qtbot.waitSignal(engine.transcription_failed, timeout=5000):
        engine.transcribe(audio, "de")


def test_transcribe_emits_failed_when_model_raises(qtbot):
    model = mock.MagicMock()
    # First call is the loader's validation transcribe (must succeed so the
    # model loads); the real transcribe call then raises.
    model.transcribe.side_effect = [
        ([_segment("warmup")], None),
        RuntimeError("inference exploded"),
    ]
    engine = _make_engine_with_loaded_model(qtbot, model)

    audio = np.zeros(16000, dtype=np.float32)
    with qtbot.waitSignal(engine.transcription_failed, timeout=5000):
        engine.transcribe(audio, "de")


def test_transcribe_passes_language_to_model(qtbot):
    model = mock.MagicMock()
    model.transcribe.return_value = ([_segment("ok")], None)
    engine = _make_engine_with_loaded_model(qtbot, model)

    audio = np.zeros(16000, dtype=np.float32)
    with qtbot.waitSignal(engine.transcription_done, timeout=5000):
        engine.transcribe(audio, "fr")

    assert model.transcribe.call_args.kwargs["language"] == "fr"


def test_transcribe_forwards_hotwords_from_decode_settings(qtbot):
    model = mock.MagicMock()
    model.transcribe.return_value = ([_segment("schaute")], None)
    engine = _make_engine_with_loaded_model(qtbot, model)

    audio = np.zeros(16000, dtype=np.float32)
    settings = DecodeSettings(hotwords="schaute Scherbe", vad_filter=False, normalize=False)
    with qtbot.waitSignal(engine.transcription_done, timeout=5000):
        engine.transcribe(audio, "de", settings=settings)

    assert model.transcribe.call_args.kwargs["hotwords"] == "schaute Scherbe"


def test_transcribe_forwards_vad_filter_from_decode_settings(qtbot):
    model = mock.MagicMock()
    model.transcribe.return_value = ([_segment("ok")], None)
    engine = _make_engine_with_loaded_model(qtbot, model)

    audio = np.zeros(16000, dtype=np.float32)
    settings = DecodeSettings(hotwords="", vad_filter=True, normalize=False)
    with qtbot.waitSignal(engine.transcription_done, timeout=5000):
        engine.transcribe(audio, "de", settings=settings)

    assert model.transcribe.call_args.kwargs["vad_filter"] is True


def test_transcribe_peak_normalizes_audio_when_normalize_is_set(qtbot):
    model = mock.MagicMock()
    model.transcribe.return_value = ([_segment("ok")], None)
    engine = _make_engine_with_loaded_model(qtbot, model)

    # Audio with peak 0.1 — should be scaled to ~0.95 before reaching model
    audio = np.full(16000, 0.1, dtype=np.float32)
    settings = DecodeSettings(hotwords="", vad_filter=False, normalize=True)
    with qtbot.waitSignal(engine.transcription_done, timeout=5000):
        engine.transcribe(audio, "de", settings=settings)

    forwarded_audio = model.transcribe.call_args.args[0]
    assert float(np.abs(forwarded_audio).max()) == pytest.approx(0.95, rel=1e-4)


def test_transcribe_does_not_normalize_when_normalize_is_false(qtbot):
    model = mock.MagicMock()
    model.transcribe.return_value = ([_segment("ok")], None)
    engine = _make_engine_with_loaded_model(qtbot, model)

    audio = np.full(16000, 0.1, dtype=np.float32)
    settings = DecodeSettings(hotwords="", vad_filter=False, normalize=False)
    with qtbot.waitSignal(engine.transcription_done, timeout=5000):
        engine.transcribe(audio, "de", settings=settings)

    forwarded_audio = model.transcribe.call_args.args[0]
    assert float(np.abs(forwarded_audio).max()) == pytest.approx(0.1, rel=1e-4)
