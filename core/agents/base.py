from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional

from core.regime.types import Bias, RegimeSignal


class TradeDirection(str):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


@dataclass(frozen=True)
class TradeIntent:
    """Desired action produced by an agent before risk/execution."""

    symbol: str
    agent_name: str
    direction: TradeDirection
    size: float
    confidence: float
    reason: str
    metadata: Optional[Dict[str, float]] = None
    
    # Options support
    instrument_type: str = "stock"  # "stock" | "option"
    option_type: Optional[str] = None  # "call" | "put"
    moneyness: Optional[str] = None  # "atm" | "otm" | "itm"
    time_to_expiry_days: Optional[int] = None  # 0 (0DTE) | 1 | 2 | 5 | 7


class BaseAgent(ABC):
    """Base class for all decision agents."""

    def __init__(self, name: str, symbol: str, config: Optional[Mapping[str, float]] = None):
        self.name = name
        self.symbol = symbol
        self.config = dict(config or {})

    @abstractmethod
    def evaluate(self, signal: RegimeSignal, market_state: Mapping[str, float]) -> List[TradeIntent]:
        """Return trade intents based on the regime signal and current market state."""

    def _build_intent(
        self, 
        direction: TradeDirection, 
        size: float, 
        confidence: float, 
        reason: str, 
        metadata: Optional[Dict[str, float]] = None,
        instrument_type: str = "stock",
        option_type: Optional[str] = None,
        moneyness: Optional[str] = None,
        time_to_expiry_days: Optional[int] = None,
    ) -> TradeIntent:
        return TradeIntent(
            symbol=self.symbol,
            agent_name=self.name,
            direction=direction,
            size=size,
            confidence=confidence,
            reason=reason,
            metadata=metadata or {},
            instrument_type=instrument_type,
            option_type=option_type,
            moneyness=moneyness,
            time_to_expiry_days=time_to_expiry_days,
        )

