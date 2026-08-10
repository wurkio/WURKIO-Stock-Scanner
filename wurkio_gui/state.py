from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from wurkio_scanner import FilterConfig, ScanResult


@dataclass(frozen=True)
class ScanDiagnostics:
    rows_loaded: int = 0
    rows_processed: int = 0
    matches: int = 0
    rejected: int = 0
    duration_seconds: float = 0.0


@dataclass
class AppState:
    config: FilterConfig = field(default_factory=FilterConfig)
    input_path: Path = Path("data/sample_stocks.csv")
    config_path: Path = Path("scanner_config.json")
    theme_name: str = "dark_2026"
    results: list[ScanResult] = field(default_factory=list)
    diagnostics: ScanDiagnostics = field(default_factory=ScanDiagnostics)
    last_run_id: int | None = None
