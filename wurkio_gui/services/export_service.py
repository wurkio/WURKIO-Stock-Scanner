from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from wurkio_scanner import ScanResult


class ExportService:
    HEADERS = (
        "rank", "symbol", "score", "price", "latest_percent_change", "rvol",
        "current_volume", "avg_volume_5d", "avg_volume_20d", "atr_percent",
        "volume_percent_change", "float_shares", "passed_filters",
    )

    @staticmethod
    def rows(results: list[ScanResult]) -> list[dict[str, object]]:
        return [
            {
                "rank": rank, "symbol": result.stock.symbol, "score": result.score,
                "price": result.stock.price,
                "latest_percent_change": result.stock.latest_percent_change,
                "rvol": round(result.stock.rvol, 4),
                "current_volume": result.stock.current_volume,
                "avg_volume_5d": result.stock.avg_volume_5d,
                "avg_volume_20d": result.stock.avg_volume_20d,
                "atr_percent": round(result.stock.atr_percent, 4),
                "volume_percent_change": round(result.stock.volume_percent_change, 4),
                "float_shares": result.stock.float_shares,
                "passed_filters": "; ".join(result.passed_filters),
            }
            for rank, result in enumerate(results, start=1)
        ]

    def export_csv(self, path: str | Path, results: list[ScanResult]) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=self.HEADERS)
            writer.writeheader()
            writer.writerows(self.rows(results))
        return destination

    def export_json(self, path: str | Path, results: list[ScanResult], preset: str) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "scan_timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "preset": preset,
            "result_count": len(results),
            "results": self.rows(results),
        }
        with destination.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)
            file.write("\n")
        return destination
