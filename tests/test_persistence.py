import csv
import json
import tempfile
import unittest
from pathlib import Path

from wurkio_gui.services.export_service import ExportService
from wurkio_gui.services.preset_service import PresetService
from wurkio_gui.services.settings_service import SettingsService
from wurkio_scanner import FilterConfig, Scanner, StockSnapshot


class PersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        candidate = StockSnapshot("TEST", 5, 2_000_000, 1_000_000, 0.3, 1_000_000, 8, 20_000_000)
        self.results = Scanner(FilterConfig()).scan([candidate])

    def test_result_retains_passed_filter_names(self) -> None:
        self.assertIn("RVOL", self.results[0].passed_filters)
        self.assertIn("ATR% minimum", self.results[0].passed_filters)
        self.assertEqual(sum(item.earned for item in self.results[0].score_breakdown), self.results[0].score)
        self.assertTrue(any(not item.passed for item in self.results[0].evaluations if not item.required))

    def test_settings_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = SettingsService(Path(directory) / "settings.json")
            expected = {"theme": "Dark 2026", "last_csv": "data/example.csv"}
            service.save(expected)
            self.assertEqual(service.load(), expected)

    def test_preset_save_and_overwrite_protection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = PresetService(directory)
            path = service.save("My Momentum Scan", FilterConfig(rvol_min=2.5))
            self.assertEqual(service.load(path).rvol_min, 2.5)
            with self.assertRaises(FileExistsError):
                service.save("My Momentum Scan", FilterConfig())

    def test_csv_and_json_exports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = ExportService()
            csv_path = service.export_csv(Path(directory) / "results.csv", self.results)
            json_path = service.export_json(Path(directory) / "results.json", self.results, "Test Preset")
            with csv_path.open(encoding="utf-8-sig", newline="") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(rows[0]["symbol"], "TEST")
            with json_path.open(encoding="utf-8") as file:
                payload = json.load(file)
            self.assertEqual(payload["preset"], "Test Preset")
            self.assertEqual(payload["result_count"], 1)


if __name__ == "__main__":
    unittest.main()
