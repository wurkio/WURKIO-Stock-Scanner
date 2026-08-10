import json
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from wurkio_gui.services.alpaca_market_data import (
    AlpacaConfigurationError,
    AlpacaMarketDataProvider,
)
from wurkio_gui.controller import AppController


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


class QueueOpener:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        return FakeResponse(self.payloads.pop(0))


class AlpacaProviderTests(unittest.TestCase):
    def test_credentials_are_required(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(AlpacaConfigurationError):
                AlpacaMarketDataProvider()

    def test_snapshot_quote_has_explicit_attribution(self):
        opener = QueueOpener([{
            "latestTrade": {"p": 187.25, "t": "2026-08-09T14:30:00Z"},
            "latestQuote": {"bp": 187.24, "ap": 187.26},
            "dailyBar": {"v": 1234567},
        }])
        provider = AlpacaMarketDataProvider("key", "secret", feed="iex", opener=opener)
        quote = provider.get_quote("aapl")
        self.assertEqual(quote.symbol, "AAPL")
        self.assertEqual(quote.price, 187.25)
        self.assertEqual(quote.feed, "iex")
        self.assertTrue(quote.is_realtime)
        self.assertFalse(quote.is_simulated)
        headers = dict(opener.requests[0][0].header_items())
        self.assertIn("Apca-api-key-id", headers)

    def test_bars_follow_pagination(self):
        bar = {"t": "2026-08-09T14:30:00Z", "o": 10, "h": 11, "l": 9, "c": 10.5, "v": 1000}
        opener = QueueOpener([
            {"bars": {"TEST": [bar]}, "next_page_token": "next"},
            {"bars": {"TEST": [{**bar, "t": "2026-08-09T14:31:00Z", "c": 10.75}]}, "next_page_token": None},
        ])
        provider = AlpacaMarketDataProvider("key", "secret", opener=opener)
        bars = provider.get_bars(
            "TEST", "1Min", datetime(2026, 8, 9, 14, 30, tzinfo=timezone.utc),
            datetime(2026, 8, 9, 14, 31, tzinfo=timezone.utc),
        )
        self.assertEqual(len(bars), 2)
        self.assertEqual(bars[-1].close, 10.75)
        self.assertIn("page_token=next", opener.requests[-1][0].full_url)

    def test_controller_only_enables_alpaca_explicitly(self):
        environment = {
            "WURKIO_MARKET_DATA_PROVIDER": "alpaca", "WURKIO_ALPACA_FEED": "iex",
            "APCA_API_KEY_ID": "key", "APCA_API_SECRET_KEY": "secret",
        }
        with patch.dict(os.environ, environment, clear=True):
            controller = AppController()
        self.assertEqual(controller.state.provider_name, "alpaca")
        self.assertEqual(controller.state.provider_feed, "iex")
        self.assertFalse(controller.state.provider_connected)


if __name__ == "__main__":
    unittest.main()
