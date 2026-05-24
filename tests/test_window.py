from __future__ import annotations

import math
from unittest import mock

import pytest

from whisper_dictate.window import (
    AppState,
    FloatingWindow,
    RecDotWidget,
    _GripHandle,
    REC_DOT_OPACITY_MAX,
    REC_DOT_OPACITY_MIN,
    REC_DOT_PULSE_INTERVAL_MS,
    REC_DOT_PULSE_PERIOD_MS,
)


@pytest.fixture
def window(qtbot, config):
    with mock.patch("whisper_dictate.config.Config.save"):
        w = FloatingWindow(config)
        qtbot.addWidget(w)
        yield w


def test_window_size(window):
    assert window.width() == 140
    assert window.height() == 44


@pytest.mark.parametrize(
    "state",
    [
        AppState.IDLE,
        AppState.LOADING,
        AppState.RECORDING,
        AppState.SUCCESS,
        AppState.FAILURE,
        AppState.LOAD_FAILED,
    ],
)
def test_grip_visible_in_all_states(qtbot, window, state):
    window.show()
    qtbot.waitExposed(window)
    window.set_state(state)

    grip_handles = [
        child for child in window.findChildren(_GripHandle)
    ]
    assert len(grip_handles) == 1, "Expected exactly one _GripHandle child"
    assert grip_handles[0].isVisible(), f"_GripHandle should be visible in state {state}"


def test_grip_drag_moves_window(qtbot, window):
    """Dragging the grip handle repositions the window."""
    from PyQt6.QtCore import QPoint
    from PyQt6.QtGui import QMouseEvent
    from PyQt6.QtCore import QPointF
    from PyQt6.QtCore import Qt

    window.show()
    qtbot.waitExposed(window)
    window.move(100, 100)

    grip = window._grip

    # Simulate press at grip center (in global coords)
    grip_global = grip.mapToGlobal(QPoint(grip.width() // 2, grip.height() // 2))

    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(grip.width() // 2, grip.height() // 2),
        QPointF(grip_global),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    grip.mousePressEvent(press_event)

    # Simulate move 30px right and 20px down
    new_global = QPointF(grip_global.x() + 30, grip_global.y() + 20)
    move_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(grip.width() // 2 + 30, grip.height() // 2 + 20),
        new_global,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    grip.mouseMoveEvent(move_event)

    assert window.pos().x() == pytest.approx(130, abs=2)
    assert window.pos().y() == pytest.approx(120, abs=2)


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


class TestRecDotWidget:
    @pytest.fixture
    def dot(self, qtbot):
        widget = RecDotWidget()
        qtbot.addWidget(widget)
        return widget

    def test_pulse_phase_starts_at_zero_after_start_pulse(self, dot):
        dot.start_pulse()

        assert dot.pulse_phase == 0.0

    def test_pulse_phase_advances_on_tick(self, dot):
        dot.start_pulse()
        increment = REC_DOT_PULSE_INTERVAL_MS / REC_DOT_PULSE_PERIOD_MS
        n = 5

        for _ in range(n):
            dot._tick()

        assert dot.pulse_phase == pytest.approx(n * increment)

    def test_pulse_completes_full_cycle_in_one_second_worth_of_ticks(self, dot):
        dot.start_pulse()
        increment = REC_DOT_PULSE_INTERVAL_MS / REC_DOT_PULSE_PERIOD_MS
        ticks_for_full_cycle = math.ceil(REC_DOT_PULSE_PERIOD_MS / REC_DOT_PULSE_INTERVAL_MS)

        for _ in range(ticks_for_full_cycle):
            dot._tick()

        # After one period's worth of ticks, phase has wrapped back near 0.
        assert 0.0 <= dot.pulse_phase < increment

    def test_opacity_is_max_at_peak_phase(self, dot):
        dot.pulse_phase = 0.25  # sin(2π·0.25) = 1 → peak

        assert dot._current_opacity() == pytest.approx(REC_DOT_OPACITY_MAX)

    def test_opacity_is_min_at_trough_phase(self, dot):
        dot.pulse_phase = 0.75  # sin(2π·0.75) = -1 → trough

        assert dot._current_opacity() == pytest.approx(REC_DOT_OPACITY_MIN)

    def test_stop_pulse_deactivates_timer(self, dot):
        dot.start_pulse()
        assert dot._timer.isActive()

        dot.stop_pulse()

        assert not dot._timer.isActive()


class TestRecDotIntegration:
    def test_rec_dot_is_visible_and_pulsing_in_recording_state(self, qtbot, window):
        window.show()
        qtbot.waitExposed(window)

        window.set_state(AppState.RECORDING)

        assert window._rec_dot.isVisible()
        assert window._rec_dot._timer.isActive()

    def test_rec_dot_is_hidden_and_stopped_in_idle_state(self, window):
        window.set_state(AppState.RECORDING)
        window.set_state(AppState.IDLE)

        assert window._stack.currentIndex() == 0
        assert not window._rec_dot._timer.isActive()

    @pytest.mark.parametrize(
        "target_state",
        [
            AppState.LOADING,
            AppState.IDLE,
            AppState.SUCCESS,
            AppState.FAILURE,
            AppState.LOAD_FAILED,
        ],
    )
    def test_rec_dot_stopped_on_each_non_recording_state(self, window, target_state):
        window.set_state(AppState.RECORDING)
        assert window._rec_dot._timer.isActive()

        window.set_state(target_state)

        assert not window._rec_dot._timer.isActive()

    def test_pulse_tick_does_not_trigger_waveform_update(self, window):
        window.set_state(AppState.RECORDING)

        with mock.patch.object(window._waveform, "update") as mock_update:
            for _ in range(5):
                window._rec_dot._tick()

            mock_update.assert_not_called()

    def test_amplitude_pipeline_unchanged_during_recording(self, window):
        window.set_state(AppState.RECORDING)

        with mock.patch.object(window._waveform, "push_amplitude") as mock_push:
            window.push_amplitude(0.5)

            mock_push.assert_called_once_with(0.5)
