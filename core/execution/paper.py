from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.policy.types import FinalTradeIntent


@dataclass
class ExecutionConfig:
    """Configuration for paper execution engine."""

    slippage_bps: float = 2.0  # 2 basis points fixed slippage
    slippage_pct_of_range: float = 0.1  # 10% of bar range as variable slippage
    commission_per_share: float = 0.0  # commission per share
    min_tick_size: float = 0.01  # minimum price increment


@dataclass
class Fill:
    """Represents a filled order."""

    symbol: str
    quantity: float
    fill_price: float
    timestamp: datetime
    slippage: float
    commission: float


class PaperExecutionEngine:
    """Simulates order execution with slippage and commission modeling."""

    def __init__(self, config: Optional[ExecutionConfig] = None):
        self.config = config or ExecutionConfig()

    def execute_intent(
        self,
        intent: FinalTradeIntent,
        symbol: str,
        current_price: float,
        bar_high: float,
        bar_low: float,
        timestamp: datetime,
    ) -> Optional[Fill]:
        """Execute a FinalTradeIntent and return a Fill if executed."""
        if not intent.is_valid or intent.position_delta == 0:
            return None

        # Calculate slippage
        bar_range = bar_high - bar_low if bar_high > bar_low else current_price * 0.001
        fixed_slippage = current_price * (self.config.slippage_bps / 10000.0)
        variable_slippage = bar_range * self.config.slippage_pct_of_range
        total_slippage = fixed_slippage + variable_slippage

        # Apply slippage (adverse for buys, favorable for sells)
        if intent.position_delta > 0:
            fill_price = current_price + total_slippage
        else:
            fill_price = current_price - total_slippage

        # Round to tick size
        fill_price = round(fill_price / self.config.min_tick_size) * self.config.min_tick_size

        quantity = abs(intent.position_delta)
        commission = quantity * self.config.commission_per_share

        return Fill(
            symbol=symbol,
            quantity=quantity * (1.0 if intent.position_delta > 0 else -1.0),
            fill_price=fill_price,
            timestamp=timestamp,
            slippage=total_slippage,
            commission=commission,
        )

    def calculate_slippage_cost(self, quantity: float, price: float, bar_range: float) -> float:
        """Calculate expected slippage cost for a given quantity."""
        fixed_slippage = price * (self.config.slippage_bps / 10000.0)
        variable_slippage = bar_range * self.config.slippage_pct_of_range
        return (fixed_slippage + variable_slippage) * abs(quantity)

