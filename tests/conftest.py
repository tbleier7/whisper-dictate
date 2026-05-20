from __future__ import annotations

import pytest

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
