from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Tuple

import pandas as pd
import requests

from core.config.polygon import PolygonSettings
from services.cache import BarCache


logger = logging.getLogger(__name__)


class PolygonClient:
    def __init__(self, settings: PolygonSettings, cache_path: Path):
        self.settings = settings
        self.cache = BarCache(cache_path)
        # Massive API base URL (Polygon migrated to Massive)
        self.base_url = settings.rest_url

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
        if not cached.empty:
            # Make timezone-aware comparison (cached index might be naive)
            cached_start = cached.index[0]
            cached_end = cached.index[-1]
            # Ensure both are timezone-aware for comparison
            if cached_start.tzinfo is None:
                cached_start = cached_start.replace(tzinfo=timezone.utc)
            if cached_end.tzinfo is None:
                cached_end = cached_end.replace(tzinfo=timezone.utc)
            if cached_start <= start and cached_end >= end:
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
        # Massive API endpoint format: /v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{start}/{end}
        # Note: timespan should be "minute" (not "min") for Massive API
        timespan_massive = "minute" if timespan == "minute" else timespan
        
        url = (
            f"{self.base_url}/v2/aggs/ticker/{symbol}/range/"
            f"{multiplier}/{timespan_massive}/{start.date()}/{end.date()}"
        )
        params = {
            "adjusted": "true",
            "sort": "asc",
            "limit": 50000,
        }
        # Massive API uses Bearer token authentication in headers (not query param)
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}"
        }
        response = requests.get(url, params=params, headers=headers, timeout=30)
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
        """Parse timeframe string to multiplier and timespan for Polygon API.
        
        Supports formats:
        - "1Min", "5Min", "15Min" (capital M)
        - "1min", "5min", "15min" (lowercase m)
        - "1Hour", "1Hour" (capital H)
        - "1hour", "1hour" (lowercase h)
        - "1Day", "1Day" (capital D)
        - "1day", "1day" (lowercase d)
        """
        # Normalize to handle both cases
        timeframe_lower = timeframe.lower()
        
        if timeframe_lower.endswith("min"):
            multiplier_str = timeframe_lower.replace("min", "")
            return int(multiplier_str), "minute"
        if timeframe_lower.endswith("hour"):
            multiplier_str = timeframe_lower.replace("hour", "")
            return int(multiplier_str), "hour"
        if timeframe_lower.endswith("day"):
            multiplier_str = timeframe_lower.replace("day", "")
            return int(multiplier_str), "day"
        raise ValueError(f"Unsupported timeframe: {timeframe}")

