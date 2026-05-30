from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path


def _user_config_dir() -> Path:
    """Return the per-user config directory for whisper-dictate.

    Uses the platform-conventional location so config works identically whether
    installed editable (``pip install -e .``) or from source
    (``pip install git+...``) — instead of writing next to the package, which
    lands in site-packages for a non-editable install.
    """
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "whisper-dictate"


_CONFIG_PATH = _user_config_dir() / "config.json"

# Pre-0.2 installs kept config.json in the repo root next to the package.
# Read it as a fallback so existing settings migrate to the user dir on save.
_LEGACY_CONFIG_PATH = Path(__file__).parent.parent / "config.json"

_DEFAULTS: dict = {
    "languages": ["de", "en"],
    "active_language": "de",
    "window_position": {"x": 100, "y": 100},
    "hotwords": {"de": "", "en": ""},
    "vad_filter": False,
    "normalize_audio": False,
}


@dataclass
class Config:
    languages: list[str] = field(default_factory=lambda: ["de", "en"])
    active_language: str = "de"
    window_position: dict = field(default_factory=lambda: {"x": 100, "y": 100})
    hotwords: dict = field(default_factory=lambda: {"de": "", "en": ""})
    vad_filter: bool = False
    normalize_audio: bool = False

    @classmethod
    def load(cls) -> "Config":
        path = _CONFIG_PATH if _CONFIG_PATH.exists() else _LEGACY_CONFIG_PATH
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                merged = {**_DEFAULTS, **data}
                return cls(
                    languages=merged["languages"],
                    active_language=merged["active_language"],
                    window_position=merged["window_position"],
                    hotwords=merged["hotwords"],
                    vad_filter=merged["vad_filter"],
                    normalize_audio=merged["normalize_audio"],
                )
            except Exception:
                pass
        return cls()

    def save(self) -> None:
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CONFIG_PATH.write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
