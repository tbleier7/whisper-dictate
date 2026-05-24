from __future__ import annotations

import logging

import keyboard
from PyQt6.QtCore import QObject, pyqtSignal

_log = logging.getLogger(__name__)

# Windows virtual-key codes for the right-side modifier keys.
_VK_RCTRL = 163
_VK_RSHIFT = 161


def _names_for_vk(vk: int, fallback: str) -> frozenset[str]:
    """Return every event-side name the keyboard library associates with a VK code.

    On English Windows 'right ctrl' → VK 163.  On German Windows the same VK
    is also reachable via 'strg-rechts'.  We collect all aliases so that the
    event handler accepts whichever name the OS fires.
    """
    try:
        os_kb = keyboard._os_keyboard
        os_kb.init()
        names: set[str] = set()
        for name, entries in os_kb.from_name.items():
            for _priority, (sc, entry_vk, extended, modifiers) in entries:
                if entry_vk == vk and not modifiers:
                    names.add(name.lower())
        if names:
            _log.debug("VK %d resolved to names: %s", vk, names)
            return frozenset(names)
    except Exception as exc:
        _log.warning("VK name lookup failed (%s), using fallback '%s'", exc, fallback)
    return frozenset([fallback])


# Resolved once at import time; covers locale-specific aliases (e.g. German
# 'strg-rechts' alongside canonical 'right ctrl').
_RIGHT_CTRL_NAMES = _names_for_vk(_VK_RCTRL, "right ctrl")
_RIGHT_SHIFT_NAMES = _names_for_vk(_VK_RSHIFT, "right shift")


class HotkeyManager(QObject):
    chord_pressed = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._right_ctrl_down = False
        self._right_shift_down = False
        self._both_seen = False
        self._polluted = False
        self._hook = None

    def start(self) -> None:
        self.stop()
        _log.info(
            "hotkey start — ctrl_names=%s shift_names=%s",
            _RIGHT_CTRL_NAMES,
            _RIGHT_SHIFT_NAMES,
        )
        self._hook = keyboard.hook(self._on_any_event)
        _log.info("hotkey hook registered")

    def stop(self) -> None:
        if self._hook is not None:
            try:
                keyboard.unhook(self._hook)
            except KeyError:
                pass
            self._hook = None
        self._right_ctrl_down = False
        self._right_shift_down = False
        self._both_seen = False
        self._polluted = False

    def _on_any_event(self, event) -> None:
        et = getattr(event, "event_type", None)
        name = (getattr(event, "name", None) or "").lower()
        is_ctrl = name in _RIGHT_CTRL_NAMES
        is_shift = name in _RIGHT_SHIFT_NAMES

        if et == "down":
            if is_ctrl:
                _log.debug("right ctrl down (shift_down=%s)", self._right_shift_down)
                self._right_ctrl_down = True
                if self._right_shift_down:
                    self._both_seen = True
            elif is_shift:
                _log.debug("right shift down (ctrl_down=%s)", self._right_ctrl_down)
                self._right_shift_down = True
                if self._right_ctrl_down:
                    self._both_seen = True
            else:
                if self._right_ctrl_down or self._right_shift_down:
                    _log.debug("chord polluted by key: %s", getattr(event, "name", None))
                    self._polluted = True
        elif et == "up":
            if is_ctrl:
                _log.debug(
                    "right ctrl release (both_seen=%s, polluted=%s)",
                    self._both_seen,
                    self._polluted,
                )
                if self._both_seen and not self._polluted:
                    _log.info("chord fired (ctrl release)")
                    self.chord_pressed.emit()
                self._right_ctrl_down = False
                self._both_seen = False
                self._reset_cycle_if_chord_released()
            elif is_shift:
                _log.debug(
                    "right shift release (both_seen=%s, polluted=%s)",
                    self._both_seen,
                    self._polluted,
                )
                if self._both_seen and not self._polluted:
                    _log.info("chord fired (shift release)")
                    self.chord_pressed.emit()
                self._right_shift_down = False
                self._both_seen = False
                self._reset_cycle_if_chord_released()

    def _reset_cycle_if_chord_released(self) -> None:
        if not self._right_ctrl_down and not self._right_shift_down:
            self._polluted = False
