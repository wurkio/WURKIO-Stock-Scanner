from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator, Callable, Iterable
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .market_data import Candle, Quote


class AlpacaConfigurationError(ValueError):
    pass


class AlpacaAPIError(RuntimeError):
    pass


class AlpacaMarketDataProvider:
    """Alpaca stock market-data adapter. Credentials are never persisted."""

    name = "alpaca"
    rest_base_url = "https://data.alpaca.markets"

    def __init__(
        self, api_key: str | None = None, api_secret: str | None = None,
        feed: str = "iex", timeout: float = 15.0,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        self.api_key = api_key or os.environ.get("APCA_API_KEY_ID", "")
        self.api_secret = api_secret or os.environ.get("APCA_API_SECRET_KEY", "")
        if not self.api_key or not self.api_secret:
            raise AlpacaConfigurationError(
                "Set APCA_API_KEY_ID and APCA_API_SECRET_KEY before enabling Alpaca."
            )
        if feed not in {"iex", "sip", "delayed_sip", "boats", "overnight", "otc"}:
            raise AlpacaConfigurationError(f"Unsupported Alpaca feed: {feed}")
        self.feed = feed
        self.timeout = timeout
        self._opener = opener
        self.is_realtime = feed in {"iex", "sip", "boats", "overnight"}
        self.is_simulated = False

    @property
    def websocket_url(self) -> str:
        return f"wss://stream.data.alpaca.markets/v2/{self.feed}"

    def get_quote(self, symbol: str, at: datetime | None = None) -> Quote:
        if at is not None:
            bars = self.get_bars(symbol, "1Min", at, at)
            if not bars:
                raise AlpacaAPIError(f"No Alpaca bar available for {symbol} at {at.isoformat()}")
            bar = bars[-1]
            return Quote(bar.symbol, bar.close, None, None, bar.volume, bar.timestamp, self.name, self.feed, False, False)
        data = self._request(f"/v2/stocks/{symbol.upper()}/snapshot", {"feed": self.feed})
        return self._snapshot_to_quote(symbol, data)

    def get_quotes(self, symbols: Iterable[str]) -> dict[str, Quote]:
        normalized = sorted({symbol.strip().upper() for symbol in symbols if symbol.strip()})
        if not normalized:
            return {}
        data = self._request("/v2/stocks/snapshots", {"symbols": ",".join(normalized), "feed": self.feed})
        snapshots = data.get("snapshots", data)
        return {symbol: self._snapshot_to_quote(symbol, snapshots[symbol]) for symbol in normalized if symbol in snapshots}

    def get_candles(self, symbol: str, start: datetime, end: datetime) -> list[Candle]:
        return self.get_bars(symbol, "1Min", start, end)

    def get_bars(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> list[Candle]:
        symbol = symbol.upper()
        params: dict[str, Any] = {
            "symbols": symbol, "timeframe": timeframe,
            "start": start.isoformat(), "end": end.isoformat(),
            "feed": self.feed, "limit": 10_000, "sort": "asc",
        }
        bars: list[Candle] = []
        while True:
            data = self._request("/v2/stocks/bars", params)
            for bar in data.get("bars", {}).get(symbol, []):
                bars.append(Candle(
                    symbol=symbol, timestamp=self._timestamp(bar["t"]),
                    open=float(bar["o"]), high=float(bar["h"]), low=float(bar["l"]),
                    close=float(bar["c"]), volume=int(bar["v"]), source=self.name,
                    feed=self.feed, is_realtime=False, is_simulated=False,
                ))
            token = data.get("next_page_token")
            if not token:
                break
            params["page_token"] = token
        return bars

    async def stream_quotes(self, symbols: Iterable[str]) -> AsyncIterator[dict[str, Any]]:
        async for event in self._stream("quotes", symbols):
            yield event

    async def stream_trades(self, symbols: Iterable[str]) -> AsyncIterator[dict[str, Any]]:
        async for event in self._stream("trades", symbols):
            yield event

    async def stream_bars(self, symbols: Iterable[str]) -> AsyncIterator[dict[str, Any]]:
        async for event in self._stream("bars", symbols):
            yield event

    async def _stream(self, channel: str, symbols: Iterable[str]) -> AsyncIterator[dict[str, Any]]:
        try:
            from websockets.asyncio.client import connect
        except ImportError as exc:
            raise AlpacaConfigurationError(
                "WebSocket streaming requires: python -m pip install -r requirements.txt"
            ) from exc
        normalized = sorted({symbol.strip().upper() for symbol in symbols if symbol.strip()})
        if not normalized:
            raise ValueError("At least one symbol is required")
        async with connect(self.websocket_url, open_timeout=self.timeout) as websocket:
            await websocket.send(json.dumps({"action": "auth", "key": self.api_key, "secret": self.api_secret}))
            auth_messages = json.loads(await websocket.recv())
            if not any(item.get("T") == "success" and item.get("msg") == "authenticated" for item in auth_messages):
                raise AlpacaAPIError("Alpaca WebSocket authentication failed")
            await websocket.send(json.dumps({"action": "subscribe", channel: normalized}))
            async for message in websocket:
                for event in json.loads(message):
                    if event.get("T") not in {"success", "subscription"}:
                        yield {
                            **event, "provider": self.name, "feed": self.feed,
                            "is_realtime": self.is_realtime, "is_simulated": False,
                        }

    def _snapshot_to_quote(self, symbol: str, data: dict[str, Any]) -> Quote:
        trade = data.get("latestTrade") or {}
        quote = data.get("latestQuote") or {}
        price = trade.get("p")
        if price is None and quote.get("bp") is not None and quote.get("ap") is not None:
            price = (float(quote["bp"]) + float(quote["ap"])) / 2
        if price is None:
            raise AlpacaAPIError(f"Alpaca returned no usable price for {symbol.upper()}")
        timestamp = trade.get("t") or quote.get("t")
        return Quote(
            symbol.upper(), float(price), self._optional_float(quote.get("bp")),
            self._optional_float(quote.get("ap")),
            int((data.get("dailyBar") or {}).get("v", 0)) or None,
            self._timestamp(timestamp) if timestamp else datetime.now().astimezone(),
            self.name, self.feed, self.is_realtime, False,
        )

    def _request(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        query = urlencode(params)
        request = Request(
            f"{self.rest_base_url}{path}?{query}",
            headers={
                "APCA-API-KEY-ID": self.api_key,
                "APCA-API-SECRET-KEY": self.api_secret,
                "Accept": "application/json",
                "User-Agent": "WURKIO-Scanner/0.5.1",
            },
        )
        try:
            with self._opener(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            request_id = exc.headers.get("X-Request-ID", "unknown") if exc.headers else "unknown"
            raise AlpacaAPIError(f"Alpaca HTTP {exc.code}; request ID {request_id}") from exc
        except URLError as exc:
            raise AlpacaAPIError(f"Unable to reach Alpaca: {exc.reason}") from exc

    @staticmethod
    def _timestamp(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        return None if value is None else float(value)
