import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from wurkio_gui.services.snapshot_service import SnapshotService
from wurkio_gui.state import ScanDiagnostics
from wurkio_scanner import FilterConfig, Scanner, StockSnapshot


def context_stock(**changes):
    values = {
        "symbol": "CTX", "price": 12.0, "current_volume": 2_000_000,
        "avg_volume_20d": 1_000_000, "atr_14d": 0.8, "avg_volume_5d": 1_000_000,
        "latest_percent_change": 8.0, "float_shares": 10_000_000,
        "open_price": 11.5, "previous_close": 10.0, "day_high": 12.5, "day_low": 10.5,
        "vwap": 11.5, "sma_20": 11.0, "sma_50": 10.0, "sma_200": 13.0,
        "premarket_price": 11.0, "premarket_volume": 500_000, "market_cap": 120_000_000,
        "short_float_percent": 7.5, "week_52_high": 20.0, "week_52_low": 5.0,
    }
    values.update(changes)
    return StockSnapshot(**values)


class MarketIntelligenceTests(unittest.TestCase):
    def test_context_calculations(self) -> None:
        stock = context_stock()
        self.assertAlmostEqual(stock.gap_percent, 15.0)
        self.assertAlmostEqual(stock.premarket_percent_change, 10.0)
        self.assertAlmostEqual(stock.distance_from_vwap_percent, 4.347826, places=5)
        self.assertEqual(stock.dollar_volume, 24_000_000)
        self.assertEqual(stock.float_rotation, 0.2)
        self.assertEqual(stock.day_range_position, 75.0)
        self.assertAlmostEqual(stock.week_52_position, 46.666667, places=5)
        self.assertTrue(stock.above_vwap)
        self.assertFalse(stock.above_sma_200)

    def test_missing_context_is_none(self) -> None:
        stock = StockSnapshot("NONE", 5, 1_000_000, 1_000_000, 0.3, 1_000_000, 5, 10_000_000)
        self.assertIsNone(stock.gap_percent)
        self.assertIsNone(stock.above_vwap)
        self.assertIsNone(stock.week_52_position)

    def test_enabled_context_filter_rejects_missing_or_failed_value(self) -> None:
        scanner = Scanner(FilterConfig(above_vwap=True, gap_percent_min=10, day_range_position_min=70))
        self.assertTrue(scanner.passes(context_stock()))
        self.assertFalse(scanner.passes(context_stock(vwap=13)))
        self.assertFalse(scanner.passes(StockSnapshot("NONE", 5, 1_000_000, 1_000_000, 0.3, 1_000_000, 5, 10_000_000)))

    def test_snapshot_database_stores_context_and_explanations(self) -> None:
        result = Scanner(FilterConfig()).scan([context_stock()])
        diagnostics = ScanDiagnostics(1, 1, 1, 0, 0.01)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.db"
            run_id = SnapshotService(path).save_scan(result, diagnostics, "Test", "sample.csv")
            connection = sqlite3.connect(path)
            try:
                run = connection.execute("SELECT preset, matches FROM scan_runs WHERE id = ?", (run_id,)).fetchone()
                row = connection.execute("SELECT market_context_json FROM scan_results WHERE run_id = ?", (run_id,)).fetchone()
            finally:
                connection.close()
            self.assertEqual(run, ("Test", 1))
            context = json.loads(row[0])
            self.assertEqual(context["float_rotation"], 0.2)
            self.assertTrue(context["above_vwap"])


if __name__ == "__main__":
    unittest.main()
