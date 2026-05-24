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


@pytest.fixture
def text_capture(tmp_path):
    """Patch keyboard.write to append injected text to a temp file.

    Yields the Path so tests can read and assert its contents.
    The file is deleted automatically when tmp_path is torn down.
    """
    out = tmp_path / "injected.txt"
    out.write_text("", encoding="utf-8")

    def _write(text, **kwargs):
        with out.open("a", encoding="utf-8") as f:
            f.write(text)

    with mock.patch("keyboard.write", side_effect=_write):
        yield out
