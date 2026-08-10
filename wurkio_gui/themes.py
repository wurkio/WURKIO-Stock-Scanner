from __future__ import annotations

import json
from pathlib import Path


THEME_DIR = Path(__file__).with_name("themes")


def available_themes() -> dict[str, Path]:
    themes: dict[str, Path] = {}
    for path in sorted(THEME_DIR.glob("*.json")):
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
        themes[data["name"]] = path
    return themes


def load_theme(path: str | Path) -> dict[str, str]:
    with Path(path).open(encoding="utf-8") as file:
        return json.load(file)
