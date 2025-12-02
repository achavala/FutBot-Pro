# Multi-Leg Options Execution - Implementation Complete ✅

## Overview

Successfully implemented complete multi-leg execution system for straddles and strangles, enabling Theta Harvester and Gamma Scalper agents.

## Features Implemented

### 1. ✅ Two Orders Per Leg
- **Call Leg**: Separate order for call option
- **Put Leg**: Separate order for put option
- Both orders submitted simultaneously to broker
- Independent fill tracking for each leg

### 2. ✅ Fill Tracking
- `LegFill` dataclass tracks:
  - Leg type (call/put)
  - Option symbol
  - Strike price
  - Quantity filled
  - Fill price
  - Fill time
  - Order ID (from broker)
  - Fill status (pending, partially_filled, filled, rejected)

### 3. ✅ Combined P&L Calculation
- `MultiLegPosition` tracks both legs together
- Combined unrealized P&L = Call P&L + Put P&L
- `MultiLegTrade` records completed trades with:
  - Combined P&L in dollars
  - Combined P&L as percentage of net premium
  - Individual leg entry/exit prices

### 4. ✅ Credit/Debit Verification
- Calculates expected credit (for short positions) or debit (for long positions)
- Verifies actual fills match expected values
- Logs warnings if mismatch exceeds 10% tolerance
- Tracks net premium in `MultiLegPosition`

## Data Structures

### New Classes Added

1. **`LegFill`** - Tracks individual leg execution
   ```python
   @dataclass
   class LegFill:
       leg_type: str  # "call" or "put"
       option_symbol: str
       strike: float
       quantity: int
       fill_price: float
       fill_time: datetime
       order_id: Optional[str]
       status: str
   ```

2. **`MultiLegPosition`** - Tracks open multi-leg positions
   ```python
   @dataclass
   class MultiLegPosition:
       symbol: str
       trade_type: str  # "straddle" or "strangle"
       direction: str  # "long" or "short"
       call_fill: Optional[LegFill]
       put_fill: Optional[LegFill]
       both_legs_filled: bool
       total_credit: float
       total_debit: float
       combined_unrealized_pnl: float
   ```

3. **`MultiLegTrade`** - Records completed multi-leg trades
   ```python
   @dataclass
   class MultiLegTrade:
       combined_pnl: float
       combined_pnl_pct: float
       net_premium: float
       # ... individual leg details
   ```

## Execution Flow

### For Straddles (Theta Harvester):
1. Agent generates intent with `option_type="straddle"` and metadata:
   - `call_symbol`: Full option symbol for ATM call
   - `put_symbol`: Full option symbol for ATM put
   - `strike`: ATM strike price
   - `total_credit`: Expected credit for selling

2. Executor:
   - Submits SELL order for call leg
   - Submits SELL order for put leg
   - Tracks fills for both legs
   - Verifies total credit matches expected
   - Creates `MultiLegPosition` once both legs filled

### For Strangles (Gamma Scalper):
1. Agent generates intent with `option_type="strangle"` and metadata:
   - `call_symbol`: Full option symbol for OTM call
   - `put_symbol`: Full option symbol for OTM put
   - `call_strike`: OTM call strike
   - `put_strike`: OTM put strike
   - `total_debit`: Expected debit for buying

2. Executor:
   - Submits BUY order for call leg
   - Submits BUY order for put leg
   - Tracks fills for both legs
   - Verifies total debit matches expected
   - Creates `MultiLegPosition` once both legs filled

## Portfolio Management

### New Methods in `OptionsPortfolioManager`:

- `add_multi_leg_position()` - Creates new multi-leg position
- `update_multi_leg_fill()` - Updates position with leg fill
- `close_multi_leg_position()` - Closes position and creates trade record
- `get_multi_leg_position()` - Retrieves position by ID
- `get_all_multi_leg_positions()` - Gets all open multi-leg positions

### P&L Calculation:

**For Long Positions (Buying Premium):**
- Call P&L = (call_exit_price - call_entry_price) × quantity × 100
- Put P&L = (put_exit_price - put_entry_price) × quantity × 100
- Combined P&L = Call P&L + Put P&L

**For Short Positions (Selling Premium):**
- Call P&L = (call_entry_price - call_exit_price) × quantity × 100
- Put P&L = (put_entry_price - put_exit_price) × quantity × 100
- Combined P&L = Call P&L + Put P&L

## Credit/Debit Verification

The system verifies that actual fills match expected values:

```python
# For short positions (selling premium)
expected_credit = (call_bid + put_bid) × quantity × 100
actual_credit = call_fill.total_cost + put_fill.total_cost

# For long positions (buying premium)
expected_debit = (call_ask + put_ask) × quantity × 100
actual_debit = call_fill.total_cost + put_fill.total_cost
```

Warnings are logged if mismatch exceeds 10% tolerance.

## Integration with Agents

### Theta Harvester Agent
- Generates straddle intents with all required metadata
- Marks as `sim_only=True` for Alpaca paper trading (naked selling not supported)
- System executes both legs and tracks fills

### Gamma Scalper Agent
- Generates strangle intents with all required metadata
- System executes both legs and tracks fills
- Combined P&L calculated across both legs

## Real vs Synthetic Execution

### Real Alpaca Orders:
- Two separate orders submitted via `OptionsBrokerClient`
- Fill tracking from broker order status
- Actual fill prices from broker
- Credit/debit verification against real fills

### Synthetic Execution:
- Used when no broker client available
- Uses market quotes (bid/ask) for pricing
- Creates synthetic fills with expected prices
- Still tracks both legs separately

## Status Tracking

Each multi-leg position tracks:
- `call_fill.status` - Call leg fill status
- `put_fill.status` - Put leg fill status
- `both_legs_filled` - True when both legs are filled

This allows monitoring partial fills and handling edge cases.

## Next Steps

1. ✅ Multi-leg execution implemented
2. ✅ Fill tracking implemented
3. ✅ Combined P&L calculation implemented
4. ✅ Credit/debit verification implemented
5. ⏳ Testing with Theta Harvester and Gamma Scalper agents

## Usage Example

```python
# Theta Harvester generates intent:
intent = FinalTradeIntent(
    option_type="straddle",
    position_delta=-5,  # Negative = selling
    metadata={
        "call_symbol": "SPY251126C00673000",
        "put_symbol": "SPY251126P00673000",
        "strike": 673.0,
        "total_credit": 2.50,  # Per contract
    }
)

# Executor handles:
# 1. Submits 2 orders (call + put)
# 2. Tracks fills
# 3. Verifies credit
# 4. Creates MultiLegPosition
```

## Files Modified

1. `core/portfolio/options_manager.py`
   - Added `LegFill`, `MultiLegPosition`, `MultiLegTrade` classes
   - Added multi-leg position management methods

2. `core/live/executor_options.py`
   - Implemented `_execute_multi_leg_trade()` with full execution logic
   - Two orders per leg
   - Fill tracking
   - Credit/debit verification

## Testing Checklist

- [ ] Test straddle execution (Theta Harvester)
- [ ] Test strangle execution (Gamma Scalper)
- [ ] Verify fill tracking for both legs
- [ ] Verify combined P&L calculation
- [ ] Verify credit/debit verification
- [ ] Test with real Alpaca orders
- [ ] Test with synthetic execution
- [ ] Test partial fills handling
- [ ] Test position closing

---

**Status**: ✅ **COMPLETE** - Ready for testing with Theta Harvester and Gamma Scalper agents!


