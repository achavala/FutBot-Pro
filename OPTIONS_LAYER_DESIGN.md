# Options Layer Design - Synthetic Options Trading on SPY/QQQ

## Current Status ✅

### Part 1: Stock Trades - WORKING
- ✅ Simulation running successfully
- ✅ Trades executing with correct prices (~$605 for QQQ on Nov 24, 2025)
- ✅ P&L tracking working correctly
- ✅ Round-trip trades visible in API
- ⚠️ Position sizes are smaller than expected (needs investigation)

### Issues Identified
1. **Position Sizing**: Trades showing 0.068771 shares instead of ~16.7 for $10k investment
   - Likely cause: Risk manager capping positions or intent.position_delta being small
   - Fix: Review `advanced_risk.compute_advanced_position_size()` logic
   - Or: Ensure `intent.position_delta` represents full position, not incremental

2. **Trade Frequency**: Need more trades for visibility
   - Solution: Lower confidence thresholds in testing mode
   - Or: Adjust agent sensitivity settings

---

## Part 2: Options Layer Design

### Goal
Enable "options-style" trading on SPY/QQQ without requiring full options chain data initially. Use synthetic options pricing model based on underlying price movements.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Options Agent                            │
│  - Analyzes regime signals                                 │
│  - Decides: BUY CALL / BUY PUT / SELL CALL / SELL PUT     │
│  - Generates OptionTradeIntent with metadata              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Options Execution Layer                        │
│  - Detects instrument_type == "option"                    │
│  - Routes to OptionsBrokerClient (not PaperBrokerClient)  │
│  - Uses synthetic pricing model                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│            Options Portfolio Manager                        │
│  - OptionPosition dataclass (separate from Position)      │
│  - OptionTrade dataclass (separate from Trade)            │
│  - Tracks: strike, expiry, delta, theta, IV                │
│  - Calculates option P&L using Greeks                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Options Trade Log                              │
│  - GET /trades/options/roundtrips                          │
│  - Shows: option_type, strike, expiry, P&L                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Extend TradeIntent (Foundation)

**File: `core/policy/types.py`**

```python
@dataclass(frozen=True)
class FinalTradeIntent:
    """Unified action emitted by the meta-policy after arbitration."""
    
    position_delta: float
    confidence: float
    primary_agent: str
    contributing_agents: List[str] = field(default_factory=list)
    reason: str = ""
    is_valid: bool = True
    
    # NEW: Options support
    instrument_type: str = "stock"  # "stock" | "option"
    option_type: Optional[str] = None  # "call" | "put"
    option_metadata: Optional[Dict[str, Any]] = None  # strike, expiry, delta, etc.
```

**File: `core/agents/base.py`**

```python
@dataclass(frozen=True)
class TradeIntent:
    """Base trade intent from agents."""
    
    symbol: str
    agent_name: str
    direction: TradeDirection
    size: float
    confidence: float
    reason: str
    metadata: Optional[Dict[str, float]] = None
    
    # NEW: Options support
    instrument_type: str = "stock"  # "stock" | "option"
    option_type: Optional[str] = None  # "call" | "put"
```

### Phase 2: Options Portfolio Manager

**File: `core/portfolio/options_manager.py` (NEW)**

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict

@dataclass
class OptionPosition:
    """Represents an open options position."""
    
    symbol: str  # e.g., "QQQ"
    option_symbol: str  # e.g., "QQQ241129P600"
    option_type: str  # "call" | "put"
    strike: float
    expiration: datetime
    quantity: float  # Number of contracts
    entry_price: float  # Premium paid/received per contract
    entry_time: datetime
    current_price: float  # Current premium
    delta: float
    gamma: float
    theta: float
    vega: float
    iv: float  # Implied volatility
    unrealized_pnl: float = 0.0
    underlying_price: float  # Current underlying price
    
    def update_price(self, underlying_price: float, option_price: float, greeks: Dict[str, float]):
        """Update position with current prices and Greeks."""
        self.underlying_price = underlying_price
        self.current_price = option_price
        self.delta = greeks.get("delta", self.delta)
        self.gamma = greeks.get("gamma", self.gamma)
        self.theta = greeks.get("theta", self.theta)
        self.vega = greeks.get("vega", self.vega)
        self.iv = greeks.get("iv", self.iv)
        
        # Calculate unrealized P&L
        # For long options: (current_price - entry_price) * quantity * 100
        # For short options: (entry_price - current_price) * quantity * 100
        if self.quantity > 0:  # Long
            self.unrealized_pnl = (option_price - self.entry_price) * abs(self.quantity) * 100
        else:  # Short
            self.unrealized_pnl = (self.entry_price - option_price) * abs(self.quantity) * 100

@dataclass
class OptionTrade:
    """Represents a completed options trade."""
    
    symbol: str
    option_symbol: str
    option_type: str
    strike: float
    expiration: datetime
    quantity: float
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    pnl_pct: float
    reason: str
    agent: str
    delta_at_entry: float
    iv_at_entry: float
```

**File: `core/portfolio/options_portfolio.py` (NEW)**

```python
class OptionsPortfolioManager:
    """Manages options positions separately from stock positions."""
    
    def __init__(self):
        self.positions: Dict[str, OptionPosition] = {}  # key: option_symbol
        self.trades: List[OptionTrade] = []
    
    def add_position(
        self,
        symbol: str,
        option_symbol: str,
        option_type: str,
        strike: float,
        expiration: datetime,
        quantity: float,
        entry_price: float,
        entry_time: datetime,
        underlying_price: float,
        greeks: Dict[str, float],
    ) -> OptionPosition:
        """Add or update an options position."""
        # Implementation similar to stock portfolio
        pass
    
    def close_position(
        self,
        option_symbol: str,
        exit_price: float,
        exit_time: datetime,
        underlying_price: float,
        reason: str,
    ) -> Optional[OptionTrade]:
        """Close an options position."""
        # Implementation similar to stock portfolio
        pass
```

### Phase 3: Synthetic Options Pricing Model

**File: `core/options/pricing.py` (NEW)**

```python
from typing import Dict
import math

class SyntheticOptionsPricer:
    """Simple Black-Scholes-like model for synthetic options pricing."""
    
    @staticmethod
    def calculate_option_price(
        underlying_price: float,
        strike: float,
        time_to_expiry: float,  # In years
        iv: float,  # Implied volatility (0.15 = 15%)
        option_type: str,  # "call" | "put"
        risk_free_rate: float = 0.05,
    ) -> float:
        """
        Calculate option price using simplified Black-Scholes.
        
        For simplicity, we'll use a delta-based approximation:
        - For ATM options: price ≈ underlying * sqrt(time) * iv * 0.4
        - For ITM/OTM: adjust by moneyness
        """
        if time_to_expiry <= 0:
            # At expiration: intrinsic value only
            if option_type == "call":
                return max(0, underlying_price - strike)
            else:  # put
                return max(0, strike - underlying_price)
        
        # Moneyness
        moneyness = underlying_price / strike if strike > 0 else 1.0
        
        # Simplified pricing
        time_factor = math.sqrt(time_to_expiry)
        iv_factor = iv
        
        if option_type == "call":
            intrinsic = max(0, underlying_price - strike)
            extrinsic = underlying_price * time_factor * iv_factor * 0.4
            return intrinsic + extrinsic
        else:  # put
            intrinsic = max(0, strike - underlying_price)
            extrinsic = underlying_price * time_factor * iv_factor * 0.4
            return intrinsic + extrinsic
    
    @staticmethod
    def calculate_greeks(
        underlying_price: float,
        strike: float,
        time_to_expiry: float,
        iv: float,
        option_type: str,
        current_price: float,
    ) -> Dict[str, float]:
        """Calculate simplified Greeks."""
        moneyness = underlying_price / strike if strike > 0 else 1.0
        
        # Delta: For calls, positive; for puts, negative
        if option_type == "call":
            delta = 0.5 if abs(moneyness - 1.0) < 0.05 else (0.3 if moneyness < 1.0 else 0.7)
        else:  # put
            delta = -0.5 if abs(moneyness - 1.0) < 0.05 else (-0.3 if moneyness > 1.0 else -0.7)
        
        # Theta: Time decay (negative for long options)
        theta = -current_price * 0.01 / 365  # ~1% per day
        
        # Gamma: Rate of change of delta
        gamma = 0.01 if abs(moneyness - 1.0) < 0.05 else 0.005
        
        # Vega: Sensitivity to volatility
        vega = current_price * 0.1  # 10% of price per 1% IV change
        
        return {
            "delta": delta,
            "gamma": gamma,
            "theta": theta,
            "vega": vega,
            "iv": iv,
        }
```

### Phase 4: Options Broker Client

**File: `core/live/options_broker_client.py` (EXTEND EXISTING)**

```python
class OptionsBrokerClient:
    """Handles options order execution with synthetic pricing."""
    
    def __init__(self, pricer: SyntheticOptionsPricer):
        self.pricer = pricer
        self.positions: Dict[str, OptionPosition] = {}
        self.orders: List[Order] = []
    
    def submit_option_order(
        self,
        symbol: str,
        option_type: str,  # "call" | "put"
        strike: float,
        expiration: datetime,
        quantity: float,  # Number of contracts
        side: OrderSide,  # BUY or SELL
        underlying_price: float,
        iv: float,  # Current IV estimate
    ) -> Order:
        """Submit an options order."""
        # Generate option symbol (e.g., "QQQ241129P600")
        option_symbol = self._generate_option_symbol(symbol, option_type, strike, expiration)
        
        # Calculate option price using synthetic model
        time_to_expiry = (expiration - datetime.now()).days / 365.0
        option_price = self.pricer.calculate_option_price(
            underlying_price=underlying_price,
            strike=strike,
            time_to_expiry=time_to_expiry,
            iv=iv,
            option_type=option_type,
        )
        
        # Calculate Greeks
        greeks = self.pricer.calculate_greeks(
            underlying_price=underlying_price,
            strike=strike,
            time_to_expiry=time_to_expiry,
            iv=iv,
            option_type=option_type,
            current_price=option_price,
        )
        
        # Create order
        order = Order(
            order_id=str(uuid4()),
            symbol=option_symbol,
            side=side,
            quantity=quantity,
            order_type=OrderType.MARKET,
            filled_price=option_price,
            # ... other fields
        )
        
        return order
```

### Phase 5: Integrate into Scheduler

**File: `core/live/scheduler.py` (MODIFY)**

In `_process_bar()` method, after getting `intent`:

```python
# Check if this is an options trade
if intent.instrument_type == "option":
    # Route to options execution
    result = self.options_executor.execute_option_intent(
        intent=intent,
        symbol=symbol,
        underlying_price=bar.close,
        current_position=self.options_portfolio.get_position(intent.option_metadata.get("option_symbol")),
    )
    
    if result.success:
        # Update options portfolio
        self.options_portfolio.apply_position_delta(...)
else:
    # Existing stock execution logic
    # ...
```

### Phase 6: Options Agent Enhancement

**File: `core/agents/options_agent.py` (MODIFY)**

Update `evaluate()` to generate options intents:

```python
def evaluate(self, signal: RegimeSignal, market_state: Mapping[str, float]) -> List[TradeIntent]:
    # ... existing logic ...
    
    # Generate option intent instead of stock intent
    if is_bearish:
        # BUY PUT
        return [
            self._build_intent(
                direction=TradeDirection.LONG,  # Long PUT = bullish on volatility/bearish on underlying
                size=1.0,  # Number of contracts
                confidence=signal.confidence,
                reason=f"PUT opportunity: {regime_val} regime",
                metadata={
                    "instrument_type": "option",
                    "option_type": "put",
                    "strike": self._calculate_strike(market_state["close"], "put"),
                    "expiration": self._calculate_expiration(),
                    "delta": -0.5,  # Target delta
                    "iv": signal.metrics.get("iv", 0.20),
                },
            )
        ]
```

### Phase 7: API Endpoints

**File: `ui/fastapi_app.py` (ADD)**

```python
@app.get("/trades/options/roundtrips")
async def get_options_roundtrips(
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
):
    """Get completed options round-trip trades."""
    # Implementation similar to stock roundtrips
    pass
```

---

## Implementation Order

1. ✅ **Extend TradeIntent** - Add `instrument_type` and `option_metadata`
2. ✅ **Create Options Portfolio Manager** - Separate from stock positions
3. ✅ **Create Synthetic Pricing Model** - Simple Black-Scholes approximation
4. ✅ **Create Options Broker Client** - Handle options order execution
5. ✅ **Integrate into Scheduler** - Route options intents to options executor
6. ✅ **Enhance Options Agent** - Generate options intents with metadata
7. ✅ **Add API Endpoints** - `/trades/options/roundtrips`

---

## Testing Plan

1. **Unit Tests**: Synthetic pricing model accuracy
2. **Integration Tests**: Options agent → execution → portfolio flow
3. **Simulation Tests**: Run 1-day simulation with options enabled
4. **Validation**: Compare synthetic option P&L with expected behavior

---

## Future Enhancements (Level 2)

1. **Real Options Data**: Integrate actual options chain data
2. **Greeks-Aware Sizing**: Position sizing based on delta, not notional
3. **Theta Decay Modeling**: More accurate time decay
4. **IV Surface**: Use actual IV data instead of estimates
5. **Multi-Leg Strategies**: Spreads, straddles, etc.

---

## Notes

- This design allows options trading **without** requiring full options chain data
- Synthetic pricing is simplified but sufficient for strategy development
- Can be upgraded to real options data later without changing the architecture
- Options positions are tracked separately from stock positions for clarity


