from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent.parent / "config.json"

_DEFAULTS: dict = {
    "hotkey": "ctrl+alt+space",
    "languages": ["de", "en"],
    "active_language": "de",
    "window_position": {"x": 100, "y": 100},
}


@dataclass
class Config:
    hotkey: str = "ctrl+alt+space"
    languages: list[str] = field(default_factory=lambda: ["de", "en"])
    active_language: str = "de"
    window_position: dict = field(default_factory=lambda: {"x": 100, "y": 100})

    @classmethod
    def load(cls) -> "Config":
        if _CONFIG_PATH.exists():
            try:
                data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
                merged = {**_DEFAULTS, **data}
                return cls(
                    hotkey=merged["hotkey"],
                    languages=merged["languages"],
                    active_language=merged["active_language"],
                    window_position=merged["window_position"],
                )
            except Exception:
                pass
        return cls()

    def save(self) -> None:
        _CONFIG_PATH.write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
