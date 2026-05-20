from __future__ import annotations

import keyboard
from PyQt6.QtCore import QObject, pyqtSignal

_LEFT_CTRL = "left ctrl"
_LEFT_SHIFT = "left shift"


class HotkeyManager(QObject):
    chord_pressed = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._left_ctrl_down = False
        self._left_shift_down = False
        self._both_seen = False
        self._hook_ctrl_press = None
        self._hook_ctrl_release = None
        self._hook_shift_press = None
        self._hook_shift_release = None

    def start(self) -> None:
        self.stop()
        # No suppress=True: ctrl/shift produce no characters on their own, and
        # combos like ctrl+shift+T must still reach the focused window.
        self._hook_ctrl_press = keyboard.on_press_key(_LEFT_CTRL, self._on_ctrl_press)
        self._hook_ctrl_release = keyboard.on_release_key(_LEFT_CTRL, self._on_ctrl_release)
        self._hook_shift_press = keyboard.on_press_key(_LEFT_SHIFT, self._on_shift_press)
        self._hook_shift_release = keyboard.on_release_key(_LEFT_SHIFT, self._on_shift_release)

    def stop(self) -> None:
        # KeyError from unhook means the hook is already gone from `keyboard`'s
        # internal registry — same end state we want, so swallow it.
        for attr in (
            "_hook_ctrl_press",
            "_hook_ctrl_release",
            "_hook_shift_press",
            "_hook_shift_release",
        ):
            handle = getattr(self, attr)
            if handle is not None:
                try:
                    keyboard.unhook(handle)
                except KeyError:
                    pass
                setattr(self, attr, None)
        self._left_ctrl_down = False
        self._left_shift_down = False
        self._both_seen = False

    def _on_ctrl_press(self, _event) -> None:
        self._left_ctrl_down = True
        if self._left_shift_down:
            self._both_seen = True

    def _on_shift_press(self, _event) -> None:
        self._left_shift_down = True
        if self._left_ctrl_down:
            self._both_seen = True

    def _on_ctrl_release(self, _event) -> None:
        if self._both_seen:
            self.chord_pressed.emit()
            self._both_seen = False
        self._left_ctrl_down = False

    def _on_shift_release(self, _event) -> None:
        if self._both_seen:
            self.chord_pressed.emit()
            self._both_seen = False
        self._left_shift_down = False
