from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd


class SQLiteCache:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_base()

    def _ensure_base(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        try:
            yield connection
        finally:
            connection.close()


class BarCache(SQLiteCache):
    def __init__(self, db_path: Path):
        super().__init__(db_path)
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS polygon_bars (
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    ts INTEGER NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL,
                    vwap REAL,
                    trades INTEGER,
                    PRIMARY KEY(symbol, timeframe, ts)
                );
                """
            )
            conn.commit()

    def store(self, symbol: str, timeframe: str, bars: pd.DataFrame) -> None:
        if bars.empty:
            return
        rows: List[tuple] = [
            (
                symbol,
                timeframe,
                int(row["timestamp"]),
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
                float(row.get("volume", 0)),
                float(row.get("vwap", 0)),
                int(row.get("trades", 0)),
            )
            for _, row in bars.iterrows()
        ]
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO polygon_bars
                (symbol, timeframe, ts, open, high, low, close, volume, vwap, trades)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                rows,
            )
            conn.commit()

    def count(self, symbol: str, timeframe: str, start_ts: Optional[int] = None, end_ts: Optional[int] = None) -> int:
        """Count bars for a symbol/timeframe range."""
        query = """
            SELECT COUNT(*) as count
            FROM polygon_bars
            WHERE symbol = ? AND timeframe = ?
        """
        params: List = [symbol, timeframe]
        if start_ts is not None:
            query += " AND ts >= ?"
            params.append(start_ts)
        if end_ts is not None:
            query += " AND ts <= ?"
            params.append(end_ts)
        
        with self._connect() as conn:
            result = conn.execute(query, params).fetchone()
            return result[0] if result else 0
    
    def load(
        self,
        symbol: str,
        timeframe: str,
        start_ts: Optional[int] = None,
        end_ts: Optional[int] = None,
    ) -> pd.DataFrame:
        query = """
            SELECT ts as timestamp, open, high, low, close, volume, vwap, trades
            FROM polygon_bars
            WHERE symbol = ? AND timeframe = ?
        """
        params: List = [symbol, timeframe]
        if start_ts is not None:
            query += " AND ts >= ?"
            params.append(start_ts)
        if end_ts is not None:
            query += " AND ts <= ?"
            params.append(end_ts)
        query += " ORDER BY ts ASC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(
            rows,
            columns=["timestamp", "open", "high", "low", "close", "volume", "vwap", "trades"],
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df.set_index("timestamp")


class NewsCache(SQLiteCache):
    def __init__(self, db_path: Path):
        super().__init__(db_path)
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS finnhub_news (
                    id TEXT PRIMARY KEY,
                    symbol TEXT,
                    headline TEXT,
                    summary TEXT,
                    sentiment REAL,
                    datetime TEXT
                );
                """
            )
            conn.commit()

    def store_articles(self, articles: Iterable[dict]) -> None:
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO finnhub_news
                (id, symbol, headline, summary, sentiment, datetime)
                VALUES (:id, :symbol, :headline, :summary, :sentiment, :datetime);
                """,
                articles,
            )
            conn.commit()

    def load_recent(self, symbol: str, limit: int = 50) -> pd.DataFrame:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, symbol, headline, summary, sentiment, datetime
                FROM finnhub_news
                WHERE symbol = ?
                ORDER BY datetime DESC
                LIMIT ?;
                """,
                (symbol, limit),
            ).fetchall()

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(
            rows,
            columns=["id", "symbol", "headline", "summary", "sentiment", "datetime"],
        )
        df["datetime"] = pd.to_datetime(df["datetime"])
        return df

