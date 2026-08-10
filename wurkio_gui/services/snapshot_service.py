from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from wurkio_scanner import ScanResult
from ..state import ScanDiagnostics


class SnapshotService:
    def __init__(self, path: str | Path = "data/wurkio_history.db") -> None:
        self.path = Path(path)

    def save_scan(self, results: list[ScanResult], diagnostics: ScanDiagnostics, preset: str, source: str) -> int:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        try:
            self._create_schema(connection)
            cursor = connection.execute(
                """INSERT INTO scan_runs
                   (timestamp, preset, source, rows_processed, matches, rejected, duration_seconds)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (datetime.now().astimezone().isoformat(timespec="seconds"), preset, source,
                 diagnostics.rows_processed, diagnostics.matches, diagnostics.rejected,
                 diagnostics.duration_seconds),
            )
            run_id = int(cursor.lastrowid)
            for rank, result in enumerate(results, start=1):
                stock = result.stock
                context = {
                    "gap_percent": stock.gap_percent,
                    "premarket_percent_change": stock.premarket_percent_change,
                    "premarket_volume": stock.premarket_volume,
                    "above_vwap": stock.above_vwap,
                    "distance_from_vwap_percent": stock.distance_from_vwap_percent,
                    "above_sma_20": stock.above_sma_20,
                    "above_sma_50": stock.above_sma_50,
                    "above_sma_200": stock.above_sma_200,
                    "market_cap": stock.market_cap,
                    "short_float_percent": stock.short_float_percent,
                    "week_52_position": stock.week_52_position,
                    "day_range_position": stock.day_range_position,
                    "dollar_volume": stock.dollar_volume,
                    "float_rotation": stock.float_rotation,
                    "distance_from_high_percent": stock.distance_from_high_percent,
                    "distance_from_low_percent": stock.distance_from_low_percent,
                }
                connection.execute(
                    """INSERT INTO scan_results
                       (run_id, rank, ticker, price, score, score_breakdown_json,
                        evaluations_json, market_context_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (run_id, rank, stock.symbol, stock.price, result.score,
                     json.dumps([asdict(item) for item in result.score_breakdown]),
                     json.dumps([asdict(item) for item in result.evaluations]), json.dumps(context)),
                )
            connection.commit()
            return run_id
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _create_schema(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS scan_runs (
                id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, preset TEXT NOT NULL,
                source TEXT NOT NULL, rows_processed INTEGER NOT NULL, matches INTEGER NOT NULL,
                rejected INTEGER NOT NULL, duration_seconds REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS scan_results (
                id INTEGER PRIMARY KEY, run_id INTEGER NOT NULL REFERENCES scan_runs(id) ON DELETE CASCADE,
                rank INTEGER NOT NULL, ticker TEXT NOT NULL, price REAL NOT NULL, score INTEGER NOT NULL,
                score_breakdown_json TEXT NOT NULL, evaluations_json TEXT NOT NULL,
                market_context_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_scan_results_run_score ON scan_results(run_id, score DESC);
            CREATE INDEX IF NOT EXISTS idx_scan_results_ticker ON scan_results(ticker);
            CREATE TABLE IF NOT EXISTS outcome_jobs (
                id INTEGER PRIMARY KEY, scan_result_id INTEGER NOT NULL REFERENCES scan_results(id) ON DELETE CASCADE,
                ticker TEXT NOT NULL, reference_price REAL NOT NULL, scan_timestamp TEXT NOT NULL,
                target_timestamp TEXT NOT NULL, horizon TEXT NOT NULL, status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT,
                UNIQUE(scan_result_id, horizon)
            );
            CREATE TABLE IF NOT EXISTS outcome_observations (
                id INTEGER PRIMARY KEY, scan_result_id INTEGER NOT NULL REFERENCES scan_results(id) ON DELETE CASCADE,
                horizon TEXT NOT NULL, observed_timestamp TEXT NOT NULL, reference_price REAL NOT NULL,
                observed_price REAL NOT NULL, return_percent REAL NOT NULL,
                high_after_scan REAL NOT NULL, low_after_scan REAL NOT NULL,
                mfe_percent REAL NOT NULL, mae_percent REAL NOT NULL, data_source TEXT NOT NULL,
                UNIQUE(scan_result_id, horizon)
            );
            CREATE INDEX IF NOT EXISTS idx_outcome_jobs_due ON outcome_jobs(status, target_timestamp);
            """
        )
