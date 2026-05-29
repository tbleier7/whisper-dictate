from __future__ import annotations

from unittest import mock

import whisper_dictate.app as app


class _FakeClipboard:
    """Minimal stand-in for QClipboard exposing text()/setText()."""

    def __init__(self, initial: str = "") -> None:
        self._text = initial

    def text(self) -> str:
        return self._text

    def setText(self, text: str) -> None:
        self._text = text


def test_atomic_paste_sets_clipboard_and_emits_single_ctrl_v(qtbot):
    clipboard = _FakeClipboard()
    sentence = "Mary had a little lamb whose fleece was white as snow"

    with (
        mock.patch("whisper_dictate.app.keyboard") as mock_keyboard,
        mock.patch(
            "whisper_dictate.app.QApplication.clipboard", return_value=clipboard
        ),
    ):
        app._paste_text(sentence)

    assert clipboard.text() == sentence
    mock_keyboard.send.assert_called_once_with("ctrl+v")
    mock_keyboard.write.assert_not_called()
