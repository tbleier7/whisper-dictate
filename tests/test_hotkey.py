from __future__ import annotations

from types import SimpleNamespace
from unittest import mock

import pytest

from whisper_dictate import hotkey as hotkey_module
from whisper_dictate.hotkey import HotkeyManager


@pytest.fixture
def hooks(monkeypatch):
    """Patch the keyboard global hook/unhook and pin the resolved key names.

    The implementation registers a single global hook and routes every key
    event through one callback. Names are pinned so events are deterministic in
    CI regardless of what the OS keyboard backend reports for the VK codes.
    """
    monkeypatch.setattr(hotkey_module, "_RIGHT_CTRL_NAMES", frozenset({"right ctrl"}))
    monkeypatch.setattr(hotkey_module, "_RIGHT_SHIFT_NAMES", frozenset({"right shift"}))
    with (
        mock.patch("whisper_dictate.hotkey.keyboard.hook") as hook,
        mock.patch("whisper_dictate.hotkey.keyboard.unhook") as unhook,
    ):
        hook.side_effect = lambda callback, **kw: "global-hook"
        yield {"hook": hook, "unhook": unhook}


def _evt(name, event_type):
    return SimpleNamespace(name=name, event_type=event_type)


def _global_callback(hooks):
    if not hooks["hook"].call_args_list:
        raise AssertionError("keyboard.hook was not called")
    return hooks["hook"].call_args_list[0].args[0]


# --- registration / teardown -------------------------------------------------


def test_start_registers_single_global_hook(hooks):
    mgr = HotkeyManager()
    mgr.start()

    assert hooks["hook"].call_count == 1


def test_stop_unhooks_global_hook(hooks):
    mgr = HotkeyManager()
    mgr.start()
    mgr.stop()

    assert hooks["unhook"].call_count == 1
    hooks["unhook"].assert_called_once_with("global-hook")


def test_stop_is_idempotent(hooks):
    mgr = HotkeyManager()
    mgr.start()
    mgr.stop()
    mgr.stop()

    # Second stop is a no-op because the handle was already cleared.
    assert hooks["unhook"].call_count == 1


def test_stop_swallows_key_error_from_unhook(hooks):
    hooks["unhook"].side_effect = KeyError("hook already removed")
    mgr = HotkeyManager()
    mgr.start()

    mgr.stop()  # must not raise


def test_start_after_start_replaces_hook(hooks):
    mgr = HotkeyManager()
    mgr.start()
    mgr.start()

    # Second start() calls stop() first (unhook once) then re-registers.
    assert hooks["hook"].call_count == 2
    assert hooks["unhook"].call_count == 1


# --- chord emission ----------------------------------------------------------


def test_chord_emits_on_right_shift_release(qtbot, hooks):
    mgr = HotkeyManager()
    mgr.start()
    cb = _global_callback(hooks)

    cb(_evt("right ctrl", "down"))
    cb(_evt("right shift", "down"))

    with qtbot.waitSignal(mgr.chord_pressed, timeout=500):
        cb(_evt("right shift", "up"))


def test_chord_emits_on_right_ctrl_release(qtbot, hooks):
    mgr = HotkeyManager()
    mgr.start()
    cb = _global_callback(hooks)

    cb(_evt("right ctrl", "down"))
    cb(_evt("right shift", "down"))

    with qtbot.waitSignal(mgr.chord_pressed, timeout=500):
        cb(_evt("right ctrl", "up"))


def test_release_without_other_key_held_no_signal(qtbot, hooks):
    mgr = HotkeyManager()
    mgr.start()
    cb = _global_callback(hooks)

    cb(_evt("right shift", "down"))

    with qtbot.assertNotEmitted(mgr.chord_pressed, wait=200):
        cb(_evt("right shift", "up"))


def test_chord_emits_once_per_cycle(qtbot, hooks):
    mgr = HotkeyManager()
    mgr.start()
    cb = _global_callback(hooks)

    signals = []
    mgr.chord_pressed.connect(lambda: signals.append(True))

    cb(_evt("right ctrl", "down"))
    cb(_evt("right shift", "down"))
    cb(_evt("right shift", "up"))  # first release in the chord — emits
    cb(_evt("right ctrl", "up"))   # trailing release — must NOT emit again

    assert len(signals) == 1


def test_two_clean_chord_cycles_emit_twice(qtbot, hooks):
    mgr = HotkeyManager()
    mgr.start()
    cb = _global_callback(hooks)

    signals = []
    mgr.chord_pressed.connect(lambda: signals.append(True))

    for _ in range(2):
        cb(_evt("right ctrl", "down"))
        cb(_evt("right shift", "down"))
        cb(_evt("right shift", "up"))
        cb(_evt("right ctrl", "up"))

    assert len(signals) == 2


# --- pollution (non-chord key pressed mid-chord) -----------------------------


def test_polluted_chord_does_not_emit(qtbot, hooks):
    mgr = HotkeyManager()
    mgr.start()
    cb = _global_callback(hooks)

    signals = []
    mgr.chord_pressed.connect(lambda: signals.append(True))

    # Simulate ctrl+shift+T: a third key down while the chord is held.
    cb(_evt("right ctrl", "down"))
    cb(_evt("right shift", "down"))
    cb(_evt("t", "down"))
    cb(_evt("t", "up"))
    cb(_evt("right shift", "up"))
    cb(_evt("right ctrl", "up"))

    assert signals == []


def test_polluted_chord_blocks_emission_regardless_of_chord_release_order(qtbot, hooks):
    mgr = HotkeyManager()
    mgr.start()
    cb = _global_callback(hooks)

    signals = []
    mgr.chord_pressed.connect(lambda: signals.append(True))

    # Release ctrl before shift this time.
    cb(_evt("right ctrl", "down"))
    cb(_evt("right shift", "down"))
    cb(_evt("t", "down"))
    cb(_evt("t", "up"))
    cb(_evt("right ctrl", "up"))
    cb(_evt("right shift", "up"))

    assert signals == []


def test_polluted_then_clean_cycle_emits_once(qtbot, hooks):
    """State must reset after a polluted cycle so the next clean chord still fires."""
    mgr = HotkeyManager()
    mgr.start()
    cb = _global_callback(hooks)

    signals = []
    mgr.chord_pressed.connect(lambda: signals.append(True))

    # Polluted cycle
    cb(_evt("right ctrl", "down"))
    cb(_evt("right shift", "down"))
    cb(_evt("t", "down"))
    cb(_evt("right shift", "up"))
    cb(_evt("right ctrl", "up"))

    # Clean cycle
    cb(_evt("right ctrl", "down"))
    cb(_evt("right shift", "down"))
    cb(_evt("right shift", "up"))
    cb(_evt("right ctrl", "up"))

    assert signals == [True]


def test_chord_key_repeat_down_does_not_pollute(qtbot, hooks):
    """Auto-repeat 'down' events for the chord keys themselves are not pollution."""
    mgr = HotkeyManager()
    mgr.start()
    cb = _global_callback(hooks)

    cb(_evt("right ctrl", "down"))
    cb(_evt("right ctrl", "down"))  # key-repeat
    cb(_evt("right shift", "down"))

    with qtbot.waitSignal(mgr.chord_pressed, timeout=500):
        cb(_evt("right shift", "up"))


def test_up_event_of_non_chord_key_is_not_pollution(qtbot, hooks):
    """Only 'down' of a non-chord key pollutes; a stray 'up' mid-chord does not."""
    mgr = HotkeyManager()
    mgr.start()
    cb = _global_callback(hooks)

    cb(_evt("right ctrl", "down"))
    cb(_evt("right shift", "down"))
    cb(_evt("t", "up"))  # release of a previously-held key — not pollution

    with qtbot.waitSignal(mgr.chord_pressed, timeout=500):
        cb(_evt("right shift", "up"))


def test_pollution_outside_chord_is_ignored(qtbot, hooks):
    """A non-chord key pressed when no chord key is held does not block a later chord."""
    mgr = HotkeyManager()
    mgr.start()
    cb = _global_callback(hooks)

    # User types normally before reaching for the chord.
    cb(_evt("a", "down"))
    cb(_evt("a", "up"))

    cb(_evt("right ctrl", "down"))
    cb(_evt("right shift", "down"))
    with qtbot.waitSignal(mgr.chord_pressed, timeout=500):
        cb(_evt("right shift", "up"))
