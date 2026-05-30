from __future__ import annotations

from unittest import mock

import numpy as np
import pytest

from whisper_dictate.audio import AudioRecorder, peak_normalize


@pytest.fixture
def stream():
    with mock.patch("whisper_dictate.audio.sd.InputStream") as MockStream:
        instance = mock.MagicMock()
        MockStream.return_value = instance
        yield MockStream, instance


def _captured_callback(MockStream):
    return MockStream.call_args.kwargs["callback"]


def test_stop_without_start_returns_empty_array(qtbot):
    recorder = AudioRecorder()
    audio = recorder.stop()

    assert isinstance(audio, np.ndarray)
    assert audio.shape == (0,)
    assert audio.dtype == np.float32


def test_start_creates_and_starts_input_stream(qtbot, stream):
    MockStream, instance = stream
    recorder = AudioRecorder()
    recorder.start()

    MockStream.assert_called_once()
    instance.start.assert_called_once()


def test_stop_returns_concatenated_frames(qtbot, stream):
    MockStream, _ = stream
    recorder = AudioRecorder()
    recorder.start()
    callback = _captured_callback(MockStream)

    block_a = np.full((1024, 1), 0.1, dtype=np.float32)
    block_b = np.full((1024, 1), 0.2, dtype=np.float32)
    callback(block_a, 1024, None, None)
    callback(block_b, 1024, None, None)

    audio = recorder.stop()

    assert audio.shape == (2048,)
    assert np.allclose(audio[:1024], 0.1)
    assert np.allclose(audio[1024:], 0.2)


def test_amplitude_emitted_from_callback(qtbot, stream):
    MockStream, _ = stream
    recorder = AudioRecorder()
    recorder.start()
    callback = _captured_callback(MockStream)

    block = np.full((1024, 1), 0.05, dtype=np.float32)

    with qtbot.waitSignal(recorder.amplitude_ready, timeout=500) as blocker:
        callback(block, 1024, None, None)

    amplitude = blocker.args[0]
    assert 0.0 <= amplitude <= 1.0
    assert amplitude == pytest.approx(0.05 * 8.0, rel=1e-3)


def test_amplitude_clamped_to_one(qtbot, stream):
    MockStream, _ = stream
    recorder = AudioRecorder()
    recorder.start()
    callback = _captured_callback(MockStream)

    loud_block = np.full((1024, 1), 0.9, dtype=np.float32)

    with qtbot.waitSignal(recorder.amplitude_ready, timeout=500) as blocker:
        callback(loud_block, 1024, None, None)

    assert blocker.args[0] == 1.0


def test_stop_closes_stream(qtbot, stream):
    _, instance = stream
    recorder = AudioRecorder()
    recorder.start()
    recorder.stop()

    instance.stop.assert_called_once()
    instance.close.assert_called_once()


def test_peak_normalize_scales_quiet_signal_to_near_095(qtbot):
    audio = np.full(100, 0.1, dtype=np.float32)
    result = peak_normalize(audio)
    assert result.max() == pytest.approx(0.95, rel=1e-4)


def test_peak_normalize_leaves_silence_unchanged(qtbot):
    silence = np.zeros(100, dtype=np.float32)
    result = peak_normalize(silence)
    assert np.all(result == 0.0)


def test_peak_normalize_leaves_empty_array_unchanged(qtbot):
    empty = np.zeros(0, dtype=np.float32)
    result = peak_normalize(empty)
    assert result.shape == (0,)


def test_peak_normalize_does_not_clip_loud_signal(qtbot):
    # A signal already near peak 1.0 should scale down to 0.95, never exceed 1.0
    audio = np.full(100, 0.9, dtype=np.float32)
    result = peak_normalize(audio)
    assert float(np.abs(result).max()) <= 1.0
    assert result.max() == pytest.approx(0.95, rel=1e-4)


def test_start_after_stop_resets_frames(qtbot, stream):
    MockStream, _ = stream
    recorder = AudioRecorder()
    recorder.start()
    callback = _captured_callback(MockStream)

    callback(np.full((1024, 1), 0.1, dtype=np.float32), 1024, None, None)
    recorder.stop()

    recorder.start()
    callback = _captured_callback(MockStream)
    callback(np.full((512, 1), 0.2, dtype=np.float32), 512, None, None)

    audio = recorder.stop()
    assert audio.shape == (512,)
    assert np.allclose(audio, 0.2)
