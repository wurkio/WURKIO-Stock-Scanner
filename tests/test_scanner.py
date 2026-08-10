import tempfile
import unittest
from pathlib import Path

from wurkio_scanner import FilterConfig, Scanner, StockSnapshot
from wurkio_scanner.io import load_config, load_stocks


def stock(symbol: str = "PASS", **changes: float) -> StockSnapshot:
    values = {
        "symbol": symbol, "price": 5.0, "current_volume": 2_000_000,
        "avg_volume_20d": 1_000_000, "atr_14d": 0.30,
        "avg_volume_5d": 1_000_000, "latest_percent_change": 8.0,
        "float_shares": 20_000_000,
    }
    values.update(changes)
    return StockSnapshot(**values)


class ScannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scanner = Scanner(FilterConfig())
        self.match = stock()

    def test_calculated_metrics(self) -> None:
        self.assertEqual(self.match.rvol, 2.0)
        self.assertEqual(self.match.atr_percent, 6.0)
        self.assertEqual(self.match.volume_percent_change, 100.0)

    def test_original_filters(self) -> None:
        self.assertTrue(self.scanner.passes(self.match))
        self.assertFalse(self.scanner.passes(stock(price=25.0)))
        self.assertFalse(self.scanner.passes(stock(current_volume=1_400_000)))
        self.assertFalse(self.scanner.passes(stock(current_volume=199_999, avg_volume_5d=100_000)))
        self.assertFalse(self.scanner.passes(stock(avg_volume_20d=999_999)))
        self.assertFalse(self.scanner.passes(stock(atr_14d=0.2)))

    def test_new_filters_and_optional_filters(self) -> None:
        config = FilterConfig(
            avg_volume_5d_min=900_000, latest_percent_change_min=5,
            volume_percent_change_min=30, float_min=10_000_000,
            float_max=50_000_000, atr_percent_max=7,
        )
        scanner = Scanner(config)
        self.assertTrue(scanner.passes(self.match))
        self.assertFalse(scanner.passes(stock(avg_volume_5d=800_000)))
        self.assertFalse(scanner.passes(stock(latest_percent_change=4.9)))
        self.assertFalse(scanner.passes(stock(current_volume=1_200_000)))
        self.assertFalse(scanner.passes(stock(float_shares=60_000_000)))
        self.assertFalse(scanner.passes(stock(atr_14d=0.4)))

    def test_null_disables_filter(self) -> None:
        scanner = Scanner(FilterConfig(rvol_min=None, avg_volume_20d_min=None, atr_percent_min=None))
        candidate = stock(current_volume=200_000, avg_volume_5d=1_000_000, avg_volume_20d=1, atr_14d=0)
        self.assertTrue(scanner.passes(candidate))

    def test_results_are_ranked_by_score(self) -> None:
        stronger = stock("STRONG", price=9.0, current_volume=5_000_000, avg_volume_20d=2_000_000, atr_14d=0.9)
        results = self.scanner.scan([self.match, stronger])
        self.assertEqual([result.stock.symbol for result in results], ["STRONG", "PASS"])

    def test_csv_requires_all_columns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_text("symbol,price\nABC,5\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing columns"):
                load_stocks(path)

    def test_all_screenshot_presets_load(self) -> None:
        preset_dir = Path(__file__).parents[1] / "presets"
        configs = [load_config(path) for path in preset_dir.glob("*.json")]
        self.assertEqual(len(configs), 11)


if __name__ == "__main__":
    unittest.main()
