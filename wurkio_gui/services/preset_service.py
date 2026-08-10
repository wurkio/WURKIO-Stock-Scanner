from pathlib import Path
import json
import re
from dataclasses import asdict

from wurkio_scanner import FilterConfig
from wurkio_scanner.io import load_config


class PresetService:
    def __init__(self, preset_dir: str | Path = "presets") -> None:
        self.preset_dir = Path(preset_dir)

    def list_presets(self) -> dict[str, Path]:
        presets = {"WURKIO Default": Path("scanner_config.json")}
        presets.update(
            {path.stem.replace("_", " ").title(): path for path in sorted(self.preset_dir.glob("*.json"))}
        )
        return presets

    def load(self, path: str | Path) -> FilterConfig:
        return load_config(path)

    def save(self, name: str, config: FilterConfig, overwrite: bool = False) -> Path:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Preset name cannot be empty")
        slug = re.sub(r"[^a-z0-9]+", "_", clean_name.lower()).strip("_")
        if not slug:
            raise ValueError("Preset name must contain letters or numbers")
        path = self.preset_dir / f"{slug}.json"
        if path.exists() and not overwrite:
            raise FileExistsError(path)
        self.preset_dir.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(asdict(config), file, indent=2)
            file.write("\n")
        return path
