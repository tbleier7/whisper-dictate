from __future__ import annotations

import pytest
from unittest import mock

from whisper_dictate.config import Config


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "slow: marks tests that load real models or hit real hardware "
        "(deselect with -m 'not slow')",
    )


@pytest.fixture
def config():
    return Config(
        languages=["de", "en"],
        active_language="de",
        window_position={"x": 0, "y": 0},
    )


class _FakeClipboard:
    """Minimal stand-in for QClipboard exposing text()/setText()."""

    def __init__(self, initial: str = "") -> None:
        self._text = initial

    def text(self) -> str:
        return self._text

    def setText(self, text: str) -> None:
        self._text = text


class _ClipboardCapture:
    def __init__(self, clipboard, keyboard):
        self.clipboard = clipboard
        self.keyboard = keyboard


@pytest.fixture
def clipboard_capture():
    """Isolate the paste path from the real OS clipboard and keyboard.

    Patches the clipboard accessor and keyboard module as used by
    whisper_dictate.app, so synthetic Ctrl+V never reaches the OS and the
    user's real clipboard is untouched during tests. Exposes the fake
    clipboard and the keyboard mock for assertions.
    """
    clipboard = _FakeClipboard()
    with (
        mock.patch("whisper_dictate.app.keyboard") as mock_keyboard,
        mock.patch(
            "whisper_dictate.app.QApplication.clipboard", return_value=clipboard
        ),
    ):
        yield _ClipboardCapture(clipboard, mock_keyboard)
