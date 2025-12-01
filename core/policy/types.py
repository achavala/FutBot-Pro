from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class FinalTradeIntent:
    """Unified action emitted by the meta-policy after arbitration."""

    position_delta: float
    confidence: float
    primary_agent: str
    contributing_agents: List[str] = field(default_factory=list)
    reason: str = ""
    is_valid: bool = True
    
    # Options support
    instrument_type: str = "stock"  # "stock" | "option"
    option_type: Optional[str] = None  # "call" | "put" | "straddle" | "strangle"
    moneyness: Optional[str] = None  # "atm" | "otm" | "itm"
    time_to_expiry_days: Optional[int] = None  # 0 (0DTE) | 1 | 2 | 5 | 7
    
    # Direction for options trades
    direction: str = "long"  # "long" | "short"
    
    # Metadata for multi-leg trades and additional info
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)

