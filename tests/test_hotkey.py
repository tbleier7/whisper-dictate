from __future__ import annotations

from unittest import mock

import pytest

from whisper_dictate.hotkey import HotkeyManager


@pytest.fixture
def hooks():
    with (
        mock.patch("whisper_dictate.hotkey.keyboard.on_press_key") as on_press_key,
        mock.patch("whisper_dictate.hotkey.keyboard.on_release_key") as on_release_key,
        mock.patch("whisper_dictate.hotkey.keyboard.unhook") as unhook,
    ):
        on_press_key.side_effect = lambda key, callback, **kw: f"press:{key}"
        on_release_key.side_effect = lambda key, callback, **kw: f"release:{key}"
        yield {
            "on_press_key": on_press_key,
            "on_release_key": on_release_key,
            "unhook": unhook,
        }


def _callback_for(hooks, fn_key, key_name):
    for call in hooks[fn_key].call_args_list:
        if call.args[0] == key_name:
            return call.args[1]
    raise AssertionError(f"No {fn_key} call for {key_name}")


def test_start_hooks_left_ctrl_and_left_shift_press_release(hooks):
    mgr = HotkeyManager()
    mgr.start()

    press_keys = sorted(c.args[0] for c in hooks["on_press_key"].call_args_list)
    release_keys = sorted(c.args[0] for c in hooks["on_release_key"].call_args_list)
    assert press_keys == ["left ctrl", "left shift"]
    assert release_keys == ["left ctrl", "left shift"]

    # No suppression — ctrl/shift must reach the focused window so combos like
    # ctrl+shift+T still fire their app shortcuts.
    for call in hooks["on_press_key"].call_args_list:
        assert call.kwargs.get("suppress", False) is False
    for call in hooks["on_release_key"].call_args_list:
        assert call.kwargs.get("suppress", False) is False


def test_stop_unhooks_all_four_handles(hooks):
    mgr = HotkeyManager()
    mgr.start()
    mgr.stop()

    assert hooks["unhook"].call_count == 4
    hooks["unhook"].assert_any_call("press:left ctrl")
    hooks["unhook"].assert_any_call("release:left ctrl")
    hooks["unhook"].assert_any_call("press:left shift")
    hooks["unhook"].assert_any_call("release:left shift")


def test_stop_is_idempotent(hooks):
    mgr = HotkeyManager()
    mgr.start()
    mgr.stop()
    mgr.stop()

    # Second stop is a no-op; unhook still called only four times (once per handle).
    assert hooks["unhook"].call_count == 4


def test_stop_swallows_key_error_from_unhook(hooks):
    hooks["unhook"].side_effect = KeyError("hook already removed")
    mgr = HotkeyManager()
    mgr.start()

    mgr.stop()  # must not raise


def test_start_after_start_replaces_hooks(hooks):
    mgr = HotkeyManager()
    mgr.start()
    mgr.start()

    # First start: 2 press + 2 release hooks.
    # Second start: stop() unhooks all four, then registers a fresh four.
    assert hooks["on_press_key"].call_count == 4
    assert hooks["on_release_key"].call_count == 4
    assert hooks["unhook"].call_count == 4


def test_chord_emits_on_left_shift_release(qtbot, hooks):
    mgr = HotkeyManager()
    mgr.start()
    ctrl_press = _callback_for(hooks, "on_press_key", "left ctrl")
    shift_press = _callback_for(hooks, "on_press_key", "left shift")
    shift_release = _callback_for(hooks, "on_release_key", "left shift")

    ctrl_press(None)
    shift_press(None)

    with qtbot.waitSignal(mgr.chord_pressed, timeout=500):
        shift_release(None)


def test_chord_emits_on_left_ctrl_release(qtbot, hooks):
    mgr = HotkeyManager()
    mgr.start()
    ctrl_press = _callback_for(hooks, "on_press_key", "left ctrl")
    shift_press = _callback_for(hooks, "on_press_key", "left shift")
    ctrl_release = _callback_for(hooks, "on_release_key", "left ctrl")

    ctrl_press(None)
    shift_press(None)

    with qtbot.waitSignal(mgr.chord_pressed, timeout=500):
        ctrl_release(None)


def test_release_without_other_key_held_no_signal(qtbot, hooks):
    mgr = HotkeyManager()
    mgr.start()
    shift_press = _callback_for(hooks, "on_press_key", "left shift")
    shift_release = _callback_for(hooks, "on_release_key", "left shift")

    shift_press(None)

    with qtbot.assertNotEmitted(mgr.chord_pressed, wait=200):
        shift_release(None)


def test_chord_emits_once_per_cycle(qtbot, hooks):
    mgr = HotkeyManager()
    mgr.start()
    ctrl_press = _callback_for(hooks, "on_press_key", "left ctrl")
    shift_press = _callback_for(hooks, "on_press_key", "left shift")
    ctrl_release = _callback_for(hooks, "on_release_key", "left ctrl")
    shift_release = _callback_for(hooks, "on_release_key", "left shift")

    signals = []
    mgr.chord_pressed.connect(lambda: signals.append(True))

    ctrl_press(None)
    shift_press(None)
    shift_release(None)  # first release in the chord — emits
    ctrl_release(None)   # trailing release — must NOT emit again

    assert len(signals) == 1


def test_two_clean_chord_cycles_emit_twice(qtbot, hooks):
    mgr = HotkeyManager()
    mgr.start()
    ctrl_press = _callback_for(hooks, "on_press_key", "left ctrl")
    shift_press = _callback_for(hooks, "on_press_key", "left shift")
    ctrl_release = _callback_for(hooks, "on_release_key", "left ctrl")
    shift_release = _callback_for(hooks, "on_release_key", "left shift")

    signals = []
    mgr.chord_pressed.connect(lambda: signals.append(True))

    # Cycle 1
    ctrl_press(None)
    shift_press(None)
    shift_release(None)
    ctrl_release(None)

    # Cycle 2
    ctrl_press(None)
    shift_press(None)
    shift_release(None)
    ctrl_release(None)

    assert len(signals) == 2
