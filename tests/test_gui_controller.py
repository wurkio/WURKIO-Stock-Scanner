import unittest
from pathlib import Path

from wurkio_gui.controller import AppController
from wurkio_gui.themes import available_themes, load_theme


class GuiControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = AppController()

    def test_default_scan_reaches_engine(self) -> None:
        self.controller.set_input("data/sample_stocks.csv")
        results = self.controller.scan()
        self.assertEqual([result.stock.symbol for result in results], ["ABCD", "XYZ", "WXYZ"])

    def test_preset_updates_shared_state(self) -> None:
        config = self.controller.load_preset("presets/bigfish_scalper_v01.json")
        self.assertEqual(config.rvol_min, 2.0)
        self.assertEqual(self.controller.state.config, config)

    def test_all_gui_themes_are_valid(self) -> None:
        themes = available_themes()
        self.assertEqual(len(themes), 6)
        required = {"name", "layout", "window", "panel", "text", "accent"}
        for path in themes.values():
            self.assertTrue(required.issubset(load_theme(path)))

    def test_filter_changes_affect_results(self) -> None:
        values = self.controller.config_values()
        values["rvol_min"] = 2.1
        self.controller.update_config(values)
        results = self.controller.scan()
        self.assertEqual([result.stock.symbol for result in results], ["ABCD"])


if __name__ == "__main__":
    unittest.main()
