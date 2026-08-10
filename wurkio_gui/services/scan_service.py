from pathlib import Path
from time import perf_counter

from wurkio_scanner import FilterConfig, ScanResult, Scanner
from wurkio_scanner.io import load_stocks
from ..state import ScanDiagnostics


class ScanService:
    def scan(self, input_path: str | Path, config: FilterConfig) -> tuple[list[ScanResult], ScanDiagnostics]:
        started = perf_counter()
        stocks = load_stocks(input_path)
        results = Scanner(config).scan(stocks)
        diagnostics = ScanDiagnostics(
            rows_loaded=len(stocks), rows_processed=len(stocks), matches=len(results),
            rejected=len(stocks) - len(results), duration_seconds=perf_counter() - started,
        )
        return results, diagnostics
