from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class TradingEvent:
    """Base class for trading events."""

    timestamp: datetime
    event_type: str = "trading_event"
    severity: str = "info"  # info, warning, error, critical

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class RegimeFlipEvent(TradingEvent):
    """Event when regime changes."""

    from_regime: str = field(default="")
    to_regime: str = field(default="")
    confidence: float = field(default=0.0)
    bar_count: int = field(default=0)
    event_type: str = "regime_flip"


@dataclass
class RiskEvent(TradingEvent):
    """Event when risk controls trigger."""

    risk_type: str = field(default="")  # soft_stop, hard_stop, circuit_breaker, daily_limit, drawdown_limit
    reason: str = field(default="")
    current_value: float = field(default=0.0)
    threshold: float = field(default=0.0)
    action_taken: str = field(default="")  # halted, throttled, position_closed
    event_type: str = "risk_event"


@dataclass
class WeightChangeEvent(TradingEvent):
    """Event when adaptive weights change significantly."""

    weight_type: str = field(default="")  # agent, regime, volatility, structure
    name: str = field(default="")
    old_weight: float = field(default=0.0)
    new_weight: float = field(default=0.0)
    change_pct: float = field(default=0.0)
    bar_count: int = field(default=0)
    event_type: str = "weight_change"


@dataclass
class OutlierPnLEvent(TradingEvent):
    """Event when PnL is an outlier."""

    pnl: float = field(default=0.0)
    pnl_pct: float = field(default=0.0)
    mean_pnl: float = field(default=0.0)
    std_dev: float = field(default=0.0)
    z_score: float = field(default=0.0)
    trade_id: Optional[str] = field(default=None)
    event_type: str = "outlier_pnl"


@dataclass
class NoTradeEvent(TradingEvent):
    """Event when controller decides not to trade despite strong signals."""

    reason: str = field(default="")
    regime_confidence: float = field(default=0.0)
    intent_confidence: float = field(default=0.0)
    agent_signals: Dict[str, float] = field(default_factory=dict)
    risk_status: Dict[str, Any] = field(default_factory=dict)
    event_type: str = "no_trade"


class EventLogger:
    """Structured event logger for trading system."""

    def __init__(self, log_file: Optional[Path] = None, enable_console: bool = True):
        self.log_file = log_file or Path("logs/trading_events.jsonl")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.enable_console = enable_console
        self.event_count = 0

    def log_event(self, event: TradingEvent) -> None:
        """Log a trading event."""
        self.event_count += 1

        # Write to file (JSONL format)
        with open(self.log_file, "a") as f:
            f.write(event.to_json() + "\n")

        # Log to console based on severity
        if self.enable_console:
            log_level = {
                "info": logging.INFO,
                "warning": logging.WARNING,
                "error": logging.ERROR,
                "critical": logging.CRITICAL,
            }.get(event.severity, logging.INFO)

            logger.log(log_level, f"[{event.event_type}] {event.to_json()}")

    def log_regime_flip(
        self, from_regime: str, to_regime: str, confidence: float, bar_count: int
    ) -> None:
        """Log regime flip event."""
        event = RegimeFlipEvent(
            timestamp=datetime.now(),
            from_regime=from_regime,
            to_regime=to_regime,
            confidence=confidence,
            bar_count=bar_count,
            severity="info",
        )
        self.log_event(event)

    def log_risk_event(
        self,
        risk_type: str,
        reason: str,
        current_value: float,
        threshold: float,
        action_taken: str,
        severity: str = "warning",
    ) -> None:
        """Log risk event."""
        event = RiskEvent(
            timestamp=datetime.now(),
            risk_type=risk_type,
            reason=reason,
            current_value=current_value,
            threshold=threshold,
            action_taken=action_taken,
            severity=severity,
        )
        self.log_event(event)

    def log_weight_change(
        self,
        weight_type: str,
        name: str,
        old_weight: float,
        new_weight: float,
        bar_count: int,
        change_threshold_pct: float = 5.0,
    ) -> None:
        """Log significant weight change."""
        change_pct = abs((new_weight - old_weight) / old_weight * 100.0) if old_weight != 0 else 0.0

        if change_pct >= change_threshold_pct:
            event = WeightChangeEvent(
                timestamp=datetime.now(),
                weight_type=weight_type,
                name=name,
                old_weight=old_weight,
                new_weight=new_weight,
                change_pct=change_pct,
                bar_count=bar_count,
                severity="info" if change_pct < 20.0 else "warning",
            )
            self.log_event(event)

    def log_outlier_pnl(
        self,
        pnl: float,
        pnl_pct: float,
        mean_pnl: float,
        std_dev: float,
        trade_id: Optional[str] = None,
        z_score_threshold: float = 2.0,
    ) -> None:
        """Log outlier PnL event."""
        if std_dev == 0:
            return

        z_score = abs((pnl - mean_pnl) / std_dev)

        if z_score >= z_score_threshold:
            event = OutlierPnLEvent(
                timestamp=datetime.now(),
                pnl=pnl,
                pnl_pct=pnl_pct,
                mean_pnl=mean_pnl,
                std_dev=std_dev,
                z_score=z_score,
                trade_id=trade_id,
                severity="warning" if z_score < 3.0 else "error",
            )
            self.log_event(event)

    def log_no_trade(
        self,
        reason: str,
        regime_confidence: float,
        intent_confidence: float,
        agent_signals: Dict[str, float],
        risk_status: Dict[str, Any],
    ) -> None:
        """Log when controller decides not to trade."""
        # Only log if signals were strong but trade was rejected
        if regime_confidence > 0.6 or intent_confidence > 0.6:
            event = NoTradeEvent(
                timestamp=datetime.now(),
                reason=reason,
                regime_confidence=regime_confidence,
                intent_confidence=intent_confidence,
                agent_signals=agent_signals,
                risk_status=risk_status,
                severity="info",
            )
            self.log_event(event)
