from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from wurkio_scanner import FilterConfig, ScanResult

from .services.preset_service import PresetService
from .services.scan_service import ScanService
from .services.export_service import ExportService
from .services.settings_service import SettingsService
from .state import AppState


class AppController:
    def __init__(self, state: AppState | None = None) -> None:
        self.state = state or AppState()
        self.presets = PresetService()
        self.scans = ScanService()
        self.exports = ExportService()
        self.settings = SettingsService()

    def available_presets(self) -> dict[str, Path]:
        return self.presets.list_presets()

    def load_preset(self, path: str | Path) -> FilterConfig:
        config = self.presets.load(path)
        self.state.config = config
        self.state.config_path = Path(path)
        return config

    def update_config(self, values: dict[str, Any]) -> FilterConfig:
        config = FilterConfig(**values)
        self.state.config = config
        return config

    def config_values(self) -> dict[str, Any]:
        return asdict(self.state.config)

    def set_input(self, path: str | Path) -> None:
        self.state.input_path = Path(path)

    def scan(self) -> list[ScanResult]:
        self.state.results, self.state.diagnostics = self.scans.scan(self.state.input_path, self.state.config)
        return self.state.results

    def save_preset(self, name: str, overwrite: bool = False) -> Path:
        path = self.presets.save(name, self.state.config, overwrite)
        self.state.config_path = path
        return path

    def load_settings(self) -> dict[str, Any]:
        return self.settings.load()

    def save_settings(self, settings: dict[str, Any]) -> Path:
        return self.settings.save(settings)

    def export_results(self, path: str | Path, format_name: str, preset: str) -> Path:
        if format_name == "csv":
            return self.exports.export_csv(path, self.state.results)
        if format_name == "json":
            return self.exports.export_json(path, self.state.results, preset)
        raise ValueError(f"Unsupported export format: {format_name}")
