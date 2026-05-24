from __future__ import annotations

import json
from pathlib import Path

import pytest

from whisper_dictate import config as config_module
from whisper_dictate.config import Config


@pytest.fixture
def config_path(tmp_path, monkeypatch) -> Path:
    path = tmp_path / "config.json"
    monkeypatch.setattr(config_module, "_CONFIG_PATH", path)
    # Point the legacy fallback at a path that does not exist so these tests
    # exercise only the user-dir config, not whatever sits in the repo root.
    monkeypatch.setattr(config_module, "_LEGACY_CONFIG_PATH", tmp_path / "legacy.json")
    return path


def test_load_returns_defaults_when_file_missing(config_path):
    assert not config_path.exists()

    cfg = Config.load()

    assert cfg.languages == ["de", "en"]
    assert cfg.active_language == "de"
    assert cfg.window_position == {"x": 100, "y": 100}


def test_load_returns_defaults_when_json_corrupt(config_path):
    config_path.write_text("not json {", encoding="utf-8")

    cfg = Config.load()

    assert cfg.active_language == "de"
    assert cfg.languages == ["de", "en"]


def test_load_merges_partial_keys_with_defaults(config_path):
    config_path.write_text(
        json.dumps({"active_language": "en"}),
        encoding="utf-8",
    )

    cfg = Config.load()

    assert cfg.active_language == "en"
    assert cfg.languages == ["de", "en"]


def test_save_then_load_roundtrip(config_path):
    cfg = Config(
        languages=["en", "fr"],
        active_language="fr",
        window_position={"x": 250, "y": 380},
    )
    cfg.save()

    loaded = Config.load()

    assert loaded.languages == ["en", "fr"]
    assert loaded.active_language == "fr"
    assert loaded.window_position == {"x": 250, "y": 380}


def test_save_writes_human_readable_json(config_path):
    Config().save()

    text = config_path.read_text(encoding="utf-8")
    parsed = json.loads(text)

    assert "\n" in text
    assert parsed["active_language"] == "de"


def test_save_creates_missing_config_dir(tmp_path, monkeypatch):
    nested = tmp_path / "whisper-dictate" / "config.json"
    monkeypatch.setattr(config_module, "_CONFIG_PATH", nested)
    monkeypatch.setattr(config_module, "_LEGACY_CONFIG_PATH", tmp_path / "legacy.json")
    assert not nested.parent.exists()

    Config(active_language="fr").save()

    assert json.loads(nested.read_text(encoding="utf-8"))["active_language"] == "fr"


def test_load_falls_back_to_legacy_when_user_config_missing(tmp_path, monkeypatch):
    """Existing repo-root config migrates: load reads legacy, save writes user dir."""
    user = tmp_path / "user" / "config.json"
    legacy = tmp_path / "legacy.json"
    legacy.write_text(
        json.dumps({"active_language": "en", "window_position": {"x": 7, "y": 9}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "_CONFIG_PATH", user)
    monkeypatch.setattr(config_module, "_LEGACY_CONFIG_PATH", legacy)

    cfg = Config.load()
    assert cfg.active_language == "en"
    assert cfg.window_position == {"x": 7, "y": 9}

    cfg.save()
    assert user.exists()
    assert json.loads(user.read_text(encoding="utf-8"))["active_language"] == "en"


def test_user_config_takes_precedence_over_legacy(tmp_path, monkeypatch):
    user = tmp_path / "config.json"
    legacy = tmp_path / "legacy.json"
    user.write_text(json.dumps({"active_language": "ja"}), encoding="utf-8")
    legacy.write_text(json.dumps({"active_language": "en"}), encoding="utf-8")
    monkeypatch.setattr(config_module, "_CONFIG_PATH", user)
    monkeypatch.setattr(config_module, "_LEGACY_CONFIG_PATH", legacy)

    assert Config.load().active_language == "ja"
