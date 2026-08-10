import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from wurkio_gui.services.market_data import SimulatedMarketDataProvider
from wurkio_gui.services.outcome_service import OutcomeService
from wurkio_gui.services.snapshot_service import SnapshotService
from wurkio_gui.state import ScanDiagnostics
from wurkio_scanner import FilterConfig, Scanner, StockSnapshot


class OutcomeTests(unittest.TestCase):
    def setUp(self) -> None:
        stock = StockSnapshot("TEST", 10, 2_000_000, 1_000_000, 0.6, 1_000_000, 8, 10_000_000)
        self.results = Scanner(FilterConfig()).scan([stock])

    def test_jobs_are_restart_safe_and_outcomes_are_calculated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.db"
            run_id = SnapshotService(path).save_scan(
                self.results, ScanDiagnostics(1, 1, 1, 0, 0.01), "Test", "test.csv"
            )
            outcomes = OutcomeService(path)
            outcomes.schedule_run(run_id)
            outcomes.schedule_run(run_id)
            connection = sqlite3.connect(path)
            try:
                job_count = connection.execute("SELECT COUNT(*) FROM outcome_jobs").fetchone()[0]
                latest_target = connection.execute(
                    "SELECT MAX(target_timestamp) FROM outcome_jobs WHERE horizon != 'close'"
                ).fetchone()[0]
            finally:
                connection.close()
            self.assertEqual(job_count, 5)

            now = datetime.fromisoformat(latest_target) + timedelta(minutes=1)
            processed = outcomes.process_due(SimulatedMarketDataProvider({"TEST": 10}), now)
            self.assertEqual(processed, 4)

            connection = sqlite3.connect(path)
            try:
                observations = connection.execute(
                    "SELECT return_percent, mfe_percent, mae_percent, data_source FROM outcome_observations"
                ).fetchall()
                pending_close = connection.execute(
                    "SELECT COUNT(*) FROM outcome_jobs WHERE horizon = 'close' AND status = 'pending'"
                ).fetchone()[0]
            finally:
                connection.close()
            self.assertEqual(len(observations), 4)
            self.assertEqual(pending_close, 1)
            self.assertTrue(all(row[1] >= row[0] >= row[2] for row in observations))
            self.assertTrue(all(row[3] == "simulated" for row in observations))


if __name__ == "__main__":
    unittest.main()
