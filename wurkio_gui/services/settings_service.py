from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SettingsService:
    def __init__(self, path: str | Path = "settings/user_settings.json") -> None:
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        with self.path.open(encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise ValueError("User settings must contain a JSON object")
        return data

    def save(self, settings: dict[str, Any]) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(settings, file, indent=2)
            file.write("\n")
        return self.path
