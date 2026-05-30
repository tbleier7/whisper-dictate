from __future__ import annotations

from unittest import mock

import numpy as np
from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QContextMenuEvent
from PyQt6.QtWidgets import QApplication, QMenu

from whisper_dictate.app import _Controller
from whisper_dictate.config import Config
from whisper_dictate.window import AppState, FloatingWindow


class CalibrationDriver:
    """Protocol driver: translates domain actions into direct widget interactions."""

    def __init__(self, qtbot) -> None:
        self._qtbot = qtbot
        self._patches: list = []
        self._controller: _Controller | None = None
        self._window: FloatingWindow | None = None
        self._config: Config | None = None
        self._captured_menu: QMenu | None = None

    # ------------------------------------------------------------------
    # App lifecycle
    # ------------------------------------------------------------------

    def build_idle_app_stack(self, config: Config) -> None:
        self._config = config
        patches = [
            mock.patch("whisper_dictate.app.WhisperEngine"),
            mock.patch("whisper_dictate.app.AudioRecorder"),
            mock.patch("whisper_dictate.app.HotkeyManager"),
            mock.patch("whisper_dictate.config.Config.save"),
        ]
        mocks = [p.start() for p in patches]
        self._patches = patches
        mocks[1].return_value.stop.return_value = np.zeros(0, dtype="float32")

        self._window = FloatingWindow(config)
        self._qtbot.addWidget(self._window)
        self._controller = _Controller(config, self._window)
        self._controller._on_model_ready("cuda")
        self._controller._hotkey.reset_mock()

    def cleanup(self) -> None:
        for p in self._patches:
            p.stop()
        self._patches = []

    # ------------------------------------------------------------------
    # Gesture simulation
    # ------------------------------------------------------------------

    def right_click_label_child(self) -> None:
        """Send QContextMenuEvent to the label child widget.

        Tests that the event propagates up to FloatingWindow — the path an
        actual mouse right-click travels through the Qt widget hierarchy.
        """
        target = self._window._label
        event = QContextMenuEvent(
            QContextMenuEvent.Reason.Mouse,
            QPoint(target.width() // 2, target.height() // 2),
        )
        captured: dict = {}

        def patched_popup(menu_self, pos, *args):
            captured["menu"] = menu_self

        with mock.patch.object(QMenu, "popup", patched_popup):
            QApplication.sendEvent(target, event)

        self._captured_menu = captured.get("menu")

    def trigger_calibrate_action(self) -> None:
        assert self._captured_menu is not None, (
            "No menu captured — call right_click_label_child() first"
        )
        calibrate = next(
            (a for a in self._captured_menu.actions() if "Calibrate" in a.text()),
            None,
        )
        assert calibrate is not None, (
            f"No 'Calibrate…' action; menu has: "
            f"{[a.text() for a in self._captured_menu.actions()]}"
        )
        calibrate.trigger()
        self._qtbot.wait(50)

    # ------------------------------------------------------------------
    # App state
    # ------------------------------------------------------------------

    def set_app_state(self, state: AppState) -> None:
        self._window.set_state(state)

    def close_calibration_window(self) -> None:
        cal = self._controller._cal_window
        if cal is not None:
            cal.close()
            self._qtbot.wait(50)

    # ------------------------------------------------------------------
    # Calibration window interactions
    # ------------------------------------------------------------------

    def deliver_transcription_to_calibration(self, text: str) -> None:
        assert self._controller._cal_window is not None
        self._controller._cal_window._on_result(text)

    def set_hotwords_in_calibration(self, text: str) -> None:
        self._controller._cal_window._hotwords_edit.setText(text)

    def enable_vad_in_calibration(self) -> None:
        self._controller._cal_window._vad_check.setChecked(True)

    def enable_normalize_in_calibration(self) -> None:
        self._controller._cal_window._normalize_check.setChecked(True)

    def click_save_in_calibration(self) -> None:
        self._controller._cal_window._save_btn.click()

    # ------------------------------------------------------------------
    # Assertions (return values for DSL to assert on)
    # ------------------------------------------------------------------

    def calibration_window_is_visible(self) -> bool:
        cal = self._controller._cal_window
        return cal is not None and cal.isVisible()

    def hotkey_stop_was_called(self) -> bool:
        return self._controller._hotkey.stop.called

    def hotkey_start_was_called(self) -> bool:
        return self._controller._hotkey.start.called

    def wer_is_shown_in_result_panel(self) -> bool:
        cal = self._controller._cal_window
        return cal is not None and "WER" in cal._result_label.text()

    def config_hotwords_for(self, lang: str) -> str:
        return self._config.hotwords.get(lang, "")

    def config_vad_filter(self) -> bool:
        return self._config.vad_filter

    def config_normalize_audio(self) -> bool:
        return self._config.normalize_audio

    def context_menu_was_captured(self) -> bool:
        return self._captured_menu is not None
