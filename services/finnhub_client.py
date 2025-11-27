from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

from core.config import FinnhubSettings
from services.cache import NewsCache


logger = logging.getLogger(__name__)


class FinnhubClient:
    def __init__(self, settings: FinnhubSettings, cache_path: Path):
        self.settings = settings
        self.cache = NewsCache(cache_path)

    def fetch_latest_news(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        now = datetime.now(timezone.utc)
        end = end or now
        start = start or (end - timedelta(days=7))

        url = f"{self.settings.rest_url}/company-news"
        params = {
            "symbol": symbol,
            "from": start.date().isoformat(),
            "to": end.date().isoformat(),
            "token": self.settings.api_key,
        }
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        articles = response.json()

        parsed = [
            {
                "id": str(article.get("id", article.get("headline", "")) or f"{symbol}-{article.get('datetime', 0)}"),
                "symbol": symbol,
                "headline": article.get("headline", ""),
                "summary": article.get("summary", ""),
                "sentiment": self._score_sentiment(article.get("summary", "")),
                "datetime": datetime.fromtimestamp(article.get("datetime", 0), tz=timezone.utc).isoformat(),
            }
            for article in articles
        ]
        self.cache.store_articles(parsed)
        return pd.DataFrame(parsed)

    def get_cached_news(self, symbol: str, limit: int = 50) -> pd.DataFrame:
        return self.cache.load_recent(symbol, limit)

    def get_sentiment_score(self, symbol: str, lookback_minutes: int = 60) -> float:
        df = self.get_cached_news(symbol)
        if df.empty:
            return 0.0
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
        recent = df[df["datetime"] >= cutoff]
        if recent.empty:
            return 0.0
        score = recent["sentiment"].mean()
        return float(score)

    def _score_sentiment(self, text: str) -> float:
        if not text:
            return 0.0
        positives = ["upgrade", "beats", "growth", "bullish", "surge", "record"]
        negatives = ["downgrade", "misses", "loss", "bearish", "drop", "fraud"]
        text_lower = text.lower()

        score = 0
        for word in positives:
            if word in text_lower:
                score += 1
        for word in negatives:
            if word in text_lower:
                score -= 1

        normalized = max(min(score / 5, 1), -1)
        return normalized

