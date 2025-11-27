from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Tuple

import pandas as pd
import requests

from core.config import PolygonSettings
from services.cache import BarCache


logger = logging.getLogger(__name__)


class PolygonClient:
    def __init__(self, settings: PolygonSettings, cache_path: Path):
        self.settings = settings
        self.cache = BarCache(cache_path)

    def get_historical_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        start_ts = int(start.timestamp() * 1000)
        end_ts = int(end.timestamp() * 1000)

        cached = self.cache.load(symbol, timeframe, start_ts, end_ts)
        if not cached.empty and cached.index[0] <= start and cached.index[-1] >= end:
            return cached

        multiplier, timespan = self._parse_timeframe(timeframe)
        bars = self._fetch_polygon_bars(symbol, multiplier, timespan, start, end)
        self.cache.store(symbol, timeframe, bars)
        return self.cache.load(symbol, timeframe, start_ts, end_ts)

    def get_latest_bars(
        self,
        symbol: str,
        timeframe: str,
        lookback_n: int,
    ) -> pd.DataFrame:
        cached = self.cache.load(symbol, timeframe)
        if len(cached) >= lookback_n:
            return cached.tail(lookback_n)

        now = datetime.now(timezone.utc)
        days_back = max(lookback_n // 390 + 1, 1)
        start = now - timedelta(days=days_back)
        multiplier, timespan = self._parse_timeframe(timeframe)
        bars = self._fetch_polygon_bars(symbol, multiplier, timespan, start, now)
        self.cache.store(symbol, timeframe, bars)
        cached = self.cache.load(symbol, timeframe)
        return cached.tail(lookback_n)

    def _fetch_polygon_bars(
        self,
        symbol: str,
        multiplier: int,
        timespan: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        url = (
            f"{self.settings.rest_url}/v2/aggs/ticker/{symbol}/range/"
            f"{multiplier}/{timespan}/{start.date()}/{end.date()}"
        )
        params = {
            "adjusted": "true",
            "sort": "asc",
            "limit": 50000,
            "apiKey": self.settings.api_key,
        }
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()

        results = payload.get("results", [])
        if not results:
            logger.warning("Polygon returned no bars for %s %s", symbol, timespan)
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume", "vwap", "trades"])

        df = pd.DataFrame(results)
        df.rename(
            columns={
                "t": "timestamp",
                "o": "open",
                "h": "high",
                "l": "low",
                "c": "close",
                "v": "volume",
                "vw": "vwap",
                "n": "trades",
            },
            inplace=True,
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df

    @staticmethod
    def _parse_timeframe(timeframe: str) -> Tuple[int, str]:
        if timeframe.endswith("Min"):
            return int(timeframe.replace("Min", "")), "minute"
        if timeframe.endswith("Hour"):
            return int(timeframe.replace("Hour", "")), "hour"
        if timeframe.endswith("Day"):
            return int(timeframe.replace("Day", "")), "day"
        raise ValueError(f"Unsupported timeframe: {timeframe}")

