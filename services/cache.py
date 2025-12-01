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
        
        # Handle timestamp conversion - can be int (ms), Timestamp, or datetime
        def convert_timestamp(ts):
            if isinstance(ts, (int, float)):
                return int(ts)
            elif isinstance(ts, pd.Timestamp):
                return int(ts.timestamp() * 1000)  # Convert to milliseconds
            elif hasattr(ts, 'timestamp'):
                # datetime object
                return int(ts.timestamp() * 1000)
            else:
                # Try to convert string or other types
                return int(pd.to_datetime(ts).timestamp() * 1000)
        
        rows: List[tuple] = [
            (
                symbol,
                timeframe,
                convert_timestamp(row["timestamp"]),
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
    
    def get_available_dates(
        self,
        symbols: List[str],
        timeframe: str = "1min",
        interval_minutes: int = 30,
    ) -> List[dict]:
        """
        Get available dates and times from cache for given symbols.
        Returns list of dicts with 'date' (YYYY-MM-DD) and 'times' (list of HH:MM strings).
        Times are rounded to the specified interval (default: 30 minutes).
        
        Args:
            symbols: List of symbols to check
            timeframe: Timeframe to check (default: "1min")
            interval_minutes: Round times to this interval (default: 30 for 30-minute intervals)
            
        Returns:
            List of dicts: [{"date": "2025-11-24", "times": ["09:30", "10:00", "10:30", ...]}, ...]
        """
        from collections import defaultdict
        
        # Normalize timeframe
        timeframe = timeframe.lower().replace("minute", "min")
        
        # Query for all timestamps for these symbols
        placeholders = ",".join("?" * len(symbols))
        query = f"""
            SELECT DISTINCT ts
            FROM polygon_bars
            WHERE symbol IN ({placeholders}) AND timeframe = ?
            ORDER BY ts ASC
        """
        params = list(symbols) + [timeframe]
        
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        
        if not rows:
            return []
        
        # Group timestamps by date and round to interval
        dates_dict = defaultdict(set)
        for (ts_ms,) in rows:
            # Convert milliseconds to datetime
            dt = datetime.fromtimestamp(ts_ms / 1000.0)
            date_str = dt.strftime("%Y-%m-%d")
            
            # Round to nearest interval_minutes
            total_minutes = dt.hour * 60 + dt.minute
            rounded_minutes = (total_minutes // interval_minutes) * interval_minutes
            rounded_hour = rounded_minutes // 60
            rounded_min = rounded_minutes % 60
            
            # Format as HH:MM
            time_str = f"{rounded_hour:02d}:{rounded_min:02d}"
            
            # Only include market hours (9:30 AM to 4:00 PM)
            if rounded_hour < 9 or (rounded_hour == 9 and rounded_min < 30) or rounded_hour >= 16:
                continue
            
            dates_dict[date_str].add(time_str)
        
        # Convert to list of dicts, sorted by date (newest first)
        result = []
        for date_str in sorted(dates_dict.keys(), reverse=True):
            # Sort times
            times = sorted(dates_dict[date_str])
            result.append({
                "date": date_str,
                "times": times
            })
        
        return result


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

