from __future__ import annotations

import keyboard
from PyQt6.QtCore import QObject, pyqtSignal


class HotkeyManager(QObject):
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()

    def __init__(self, hotkey: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        parts = hotkey.lower().split("+")
        self._trigger_key = parts[-1]
        self._modifiers = parts[:-1]
        self._active = False
        self._hook_press = None
        self._hook_release = None

    def start(self) -> None:
        self.stop()
        self._hook_press = keyboard.on_press_key(self._trigger_key, self._on_press)
        self._hook_release = keyboard.on_release_key(self._trigger_key, self._on_release)

    def stop(self) -> None:
        if self._hook_press is not None:
            keyboard.unhook(self._hook_press)
            self._hook_press = None
        if self._hook_release is not None:
            keyboard.unhook(self._hook_release)
            self._hook_release = None
        self._active = False

    def _modifiers_held(self) -> bool:
        return all(keyboard.is_pressed(m) for m in self._modifiers)

    def _on_press(self, _event) -> None:
        if not self._active and self._modifiers_held():
            self._active = True
            self.recording_started.emit()

    def _on_release(self, _event) -> None:
        if self._active:
            self._active = False
            self.recording_stopped.emit()
