from __future__ import annotations

import sqlite3
from datetime import datetime, time, timedelta
from pathlib import Path

from .market_data import MarketDataProvider


HORIZONS = (("5m", 5), ("15m", 15), ("30m", 30), ("1h", 60))


class OutcomeService:
    def __init__(self, path: str | Path = "data/wurkio_history.db") -> None:
        self.path = Path(path)

    def schedule_run(self, run_id: int) -> int:
        connection = sqlite3.connect(self.path)
        try:
            run = connection.execute("SELECT timestamp FROM scan_runs WHERE id = ?", (run_id,)).fetchone()
            if run is None:
                raise ValueError(f"Unknown scan run: {run_id}")
            scan_time = datetime.fromisoformat(run[0])
            candidates = connection.execute(
                "SELECT id, ticker, price FROM scan_results WHERE run_id = ?", (run_id,)
            ).fetchall()
            count = 0
            for result_id, ticker, reference_price in candidates:
                targets = [(label, scan_time + timedelta(minutes=minutes)) for label, minutes in HORIZONS]
                close_target = datetime.combine(scan_time.date(), time(16, 0), tzinfo=scan_time.tzinfo)
                if close_target <= scan_time:
                    close_target += timedelta(days=1)
                targets.append(("close", close_target))
                for horizon, target in targets:
                    connection.execute(
                        """INSERT OR IGNORE INTO outcome_jobs
                           (scan_result_id, ticker, reference_price, scan_timestamp,
                            target_timestamp, horizon, status, attempts)
                           VALUES (?, ?, ?, ?, ?, ?, 'pending', 0)""",
                        (result_id, ticker, reference_price, scan_time.isoformat(), target.isoformat(), horizon),
                    )
                    count += 1
            connection.commit()
            return count
        finally:
            connection.close()

    def process_due(self, provider: MarketDataProvider, now: datetime | None = None) -> int:
        observed_at = now or datetime.now().astimezone()
        connection = sqlite3.connect(self.path)
        processed = 0
        try:
            jobs = connection.execute(
                """SELECT id, scan_result_id, ticker, reference_price, scan_timestamp,
                          target_timestamp, horizon
                   FROM outcome_jobs
                   WHERE status IN ('pending', 'retry') AND target_timestamp <= ?
                   ORDER BY target_timestamp""",
                (observed_at.isoformat(),),
            ).fetchall()
            for job_id, result_id, ticker, reference, scan_text, target_text, horizon in jobs:
                try:
                    scan_time = datetime.fromisoformat(scan_text)
                    target_time = datetime.fromisoformat(target_text)
                    quote = provider.get_quote(ticker, target_time)
                    candles = provider.get_candles(ticker, scan_time, target_time)
                    highs = [candle.high for candle in candles] or [quote.price]
                    lows = [candle.low for candle in candles] or [quote.price]
                    high_after, low_after = max(highs), min(lows)
                    change = (quote.price - reference) / reference * 100
                    mfe = (high_after - reference) / reference * 100
                    mae = (low_after - reference) / reference * 100
                    connection.execute(
                        """INSERT OR REPLACE INTO outcome_observations
                           (scan_result_id, horizon, observed_timestamp, reference_price,
                            observed_price, return_percent, high_after_scan, low_after_scan,
                            mfe_percent, mae_percent, data_source)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (result_id, horizon, observed_at.isoformat(), reference, quote.price,
                         change, high_after, low_after, mfe, mae, provider.name),
                    )
                    connection.execute(
                        "UPDATE outcome_jobs SET status = 'complete', attempts = attempts + 1, last_error = NULL WHERE id = ?",
                        (job_id,),
                    )
                    processed += 1
                except Exception as exc:
                    connection.execute(
                        """UPDATE outcome_jobs SET status = CASE WHEN attempts >= 2 THEN 'failed' ELSE 'retry' END,
                           attempts = attempts + 1, last_error = ? WHERE id = ?""",
                        (str(exc)[:500], job_id),
                    )
            connection.commit()
            return processed
        finally:
            connection.close()

    def recent_runs(self, limit: int = 25) -> list[tuple]:
        if not self.path.exists():
            return []
        connection = sqlite3.connect(self.path)
        try:
            return connection.execute(
                """SELECT r.id, r.timestamp, r.preset, r.matches,
                          SUM(CASE WHEN j.status = 'complete' THEN 1 ELSE 0 END),
                          COUNT(j.id)
                   FROM scan_runs r
                   LEFT JOIN scan_results s ON s.run_id = r.id
                   LEFT JOIN outcome_jobs j ON j.scan_result_id = s.id
                   GROUP BY r.id ORDER BY r.id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        finally:
            connection.close()
