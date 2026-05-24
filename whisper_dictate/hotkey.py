from __future__ import annotations

import logging

import keyboard
from PyQt6.QtCore import QObject, pyqtSignal

_RIGHT_CTRL = "right ctrl"
_RIGHT_SHIFT = "right shift"

_log = logging.getLogger(__name__)


class HotkeyManager(QObject):
    chord_pressed = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._right_ctrl_down = False
        self._right_shift_down = False
        self._both_seen = False
        self._polluted = False
        self._hook_ctrl_press = None
        self._hook_ctrl_release = None
        self._hook_shift_press = None
        self._hook_shift_release = None
        self._hook_global = None

    def start(self) -> None:
        self.stop()
        _log.info("hotkey start — registering hooks")
        # No suppress=True: ctrl/shift produce no characters on their own, and
        # combos like ctrl+shift+T must still reach the focused window.
        self._hook_ctrl_press = keyboard.on_press_key(_RIGHT_CTRL, self._on_ctrl_press)
        self._hook_ctrl_release = keyboard.on_release_key(_RIGHT_CTRL, self._on_ctrl_release)
        self._hook_shift_press = keyboard.on_press_key(_RIGHT_SHIFT, self._on_shift_press)
        self._hook_shift_release = keyboard.on_release_key(_RIGHT_SHIFT, self._on_shift_release)
        # Global hook flags the cycle as polluted if any non-chord key goes
        # down while a chord key is held, so ctrl+shift+T (and similar combos)
        # do not register as a clean toggle on chord release.
        self._hook_global = keyboard.hook(self._on_any_event)
        _log.info("hotkey hooks registered")

    def stop(self) -> None:
        # KeyError from unhook means the hook is already gone from `keyboard`'s
        # internal registry — same end state we want, so swallow it.
        for attr in (
            "_hook_ctrl_press",
            "_hook_ctrl_release",
            "_hook_shift_press",
            "_hook_shift_release",
            "_hook_global",
        ):
            handle = getattr(self, attr)
            if handle is not None:
                try:
                    keyboard.unhook(handle)
                except KeyError:
                    pass
                setattr(self, attr, None)
        self._right_ctrl_down = False
        self._right_shift_down = False
        self._both_seen = False
        self._polluted = False

    def _on_ctrl_press(self, _event) -> None:
        _log.debug("right ctrl down (shift_down=%s)", self._right_shift_down)
        self._right_ctrl_down = True
        if self._right_shift_down:
            self._both_seen = True

    def _on_shift_press(self, _event) -> None:
        _log.debug("right shift down (ctrl_down=%s)", self._right_ctrl_down)
        self._right_shift_down = True
        if self._right_ctrl_down:
            self._both_seen = True

    def _on_ctrl_release(self, _event) -> None:
        _log.debug("right ctrl release (both_seen=%s, polluted=%s)", self._both_seen, self._polluted)
        if self._both_seen and not self._polluted:
            _log.info("chord fired (ctrl release)")
            self.chord_pressed.emit()
        self._both_seen = False
        self._right_ctrl_down = False
        self._reset_cycle_if_chord_released()

    def _on_shift_release(self, _event) -> None:
        _log.debug("right shift release (both_seen=%s, polluted=%s)", self._both_seen, self._polluted)
        if self._both_seen and not self._polluted:
            _log.info("chord fired (shift release)")
            self.chord_pressed.emit()
        self._both_seen = False
        self._right_shift_down = False
        self._reset_cycle_if_chord_released()

    def _on_any_event(self, event) -> None:
        if getattr(event, "event_type", None) != "down":
            return
        name = getattr(event, "name", None)
        if name in (_RIGHT_CTRL, _RIGHT_SHIFT):
            return
        if self._right_ctrl_down or self._right_shift_down:
            _log.debug("chord polluted by key: %s", name)
            self._polluted = True

    def _reset_cycle_if_chord_released(self) -> None:
        if not self._right_ctrl_down and not self._right_shift_down:
            self._polluted = False
