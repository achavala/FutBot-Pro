from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, validator


class CacheSettings(BaseModel):
    backend: str = "sqlite"
    path: Path


class DataSettings(BaseModel):
    default_symbol: str
    default_timeframe: str
    bar_lookback: int = 500
    cache: CacheSettings


class PolygonSettings(BaseModel):
    api_key: str
    rest_url: str
    rate_limit_per_min: int = 5


class FinnhubSettings(BaseModel):
    api_key: str
    rest_url: str
    sentiment_min_score: float = Field(0.2, ge=0, le=1)


class AgentThresholds(BaseModel):
    trend: dict
    mean_reversion: dict
    event_spike: dict


class RegimeEngineSettings(BaseModel):
    lookback_window: int = 120
    volatility_window: int = 30
    confidence_threshold: float = Field(0.6, ge=0, le=1)


class RiskSettings(BaseModel):
    max_daily_loss_pct: float = 3.0
    max_loss_streak: int = 4
    cvar_lookback: int = 50
    kill_switch: bool = False


class ExecutionSettings(BaseModel):
    default_order_size: int = 100
    slippage_bps: float = 1.5
    slippage_range_pct: float = 0.05


class BacktestSettings(BaseModel):
    db_path: Path
    trade_log_path: Path


class AppSettings(BaseModel):
    environment: str = "development"
    log_level: str = "INFO"
    data_path: Path


class Settings(BaseModel):
    app: AppSettings
    data: DataSettings
    polygon: PolygonSettings
    finnhub: FinnhubSettings
    agents: AgentThresholds
    regime_engine: RegimeEngineSettings
    risk: RiskSettings
    execution: ExecutionSettings
    backtest: BacktestSettings
    symbols: Optional[dict] = None  # Optional symbols configuration

    @validator("app")
    def ensure_data_path_exists(cls, value: AppSettings) -> AppSettings:
        value.data_path.mkdir(parents=True, exist_ok=True)
        return value


def load_settings(path: Optional[Path] = None) -> Settings:
    """Load YAML settings into strongly-typed Pydantic models."""
    settings_path = path or Path(__file__).resolve().parent.parent / "config" / "settings.yaml"
    with settings_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return Settings(**raw)

