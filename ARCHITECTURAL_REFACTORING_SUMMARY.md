# Architectural Refactoring Summary

## Overview

This document summarizes the architectural refactoring performed to make the crypto trading integration cleaner, more configurable, and future-proof.

## Goals Achieved

✅ **Config-Driven**: No hard-coded risk parameters (30/20 TP/SL)  
✅ **Asset-Aware**: System distinguishes between equity and crypto  
✅ **Future-Proof**: Easy to add new asset types  
✅ **Tested**: Basic tests for asset profiles and crypto integration  

## Changes Made

### 1. Protocol Interfaces (`core/live/interfaces.py`)

Created `DataFeed` and `Broker` protocols to define clear interfaces:

```python
class DataFeed(Protocol):
    def connect(self) -> bool: ...
    def subscribe(self, symbols: List[str], preload_bars: int = 60) -> bool: ...
    def get_next_bar(self, symbol: str, timeout: float = 5.0) -> Optional[Bar]: ...
    # ... more methods
```

**Benefits:**
- Clear contracts for data feeds and brokers
- Easy to add new implementations
- Type safety with Protocol

### 2. Asset Profile System (`core/config/asset_profiles.py`)

Created a comprehensive asset profile system:

- **`AssetProfile`**: Dataclass with risk parameters per symbol
- **`AssetProfileManager`**: Manages profiles with auto-detection
- **`AssetProfileConfig`**: Pydantic model for YAML validation

**Features:**
- Per-symbol risk configuration (TP/SL, risk per trade, etc.)
- Automatic asset type detection (equity vs crypto)
- Default profiles for each asset type
- Config loading from YAML

**Example Config:**
```yaml
symbols:
  QQQ:
    asset_type: equity
    risk_per_trade_pct: 1.0
    take_profit_pct: 0.30
    stop_loss_pct: 0.20
  BTC/USD:
    asset_type: crypto
    risk_per_trade_pct: 0.5
    take_profit_pct: 0.50
    stop_loss_pct: 0.25
```

### 3. Asset-Aware Regime Engine (`core/regime/engine.py`)

Updated regime engine to accept `asset_type` in features:

- Regime classification now aware of asset type
- Can branch logic for equity vs crypto in the future
- Asset type included in regime signal metrics

**Future Enhancement:**
- Skip equity-specific features (VIX, session gaps) for crypto
- Adjust thresholds based on asset type

### 4. Config-Driven Profit Manager (`core/live/profit_manager.py`)

Updated `ProfitManager` to use asset profiles:

- Accepts `asset_profiles` dict in constructor
- Uses profile-specific TP/SL values per symbol
- Falls back to default config if no profile

**Before:**
```python
# Hard-coded 30% TP, 20% SL for everything
if profit_pct >= 30.0:
    return True, "Take profit"
```

**After:**
```python
# Config-driven per symbol
profile = self.asset_profiles.get(symbol)
take_profit_pct = profile.take_profit_pct if profile else self.config.take_profit_pct
if profit_pct >= take_profit_pct:
    return True, "Take profit"
```

### 5. Orchestrator (`core/live/orchestrator.py`)

Created `TradingOrchestrator` to manage feeds/brokers:

- Groups symbols by asset type
- Creates appropriate data feeds (equity vs crypto)
- Provides centralized profile access

**Usage:**
```python
orchestrator = TradingOrchestrator(
    symbols=["QQQ", "BTC/USD"],
    asset_profile_manager=profile_manager,
    broker_type="alpaca",
)
```

### 6. Scheduler Integration (`core/live/scheduler.py`)

Updated scheduler to:

- Accept `asset_profiles` in `LiveTradingConfig`
- Pass asset type to regime engine
- Use asset profile for investment amount
- Pass profiles to profit manager

### 7. FastAPI Integration (`ui/fastapi_app.py`)

Updated FastAPI to:

- Load asset profiles from config
- Pass profiles to `LiveTradingConfig`
- Pass profiles to `bot_manager.start_live_trading()`

**Note:** FastAPI still has legacy symbol parsing logic for data feed selection. This can be refactored to use the orchestrator in the future.

### 8. Tests (`tests/`)

Added comprehensive tests:

- `test_asset_profiles.py`: Asset profile creation, detection, config loading
- `test_crypto_integration.py`: Orchestrator symbol grouping, profile access

## Configuration Example

Updated `config/settings.yaml`:

```yaml
symbols:
  QQQ:
    asset_type: equity
    risk_per_trade_pct: 1.0
    take_profit_pct: 0.30
    stop_loss_pct: 0.20
    fixed_investment_amount: 1000.0
  
  BTC/USD:
    asset_type: crypto
    risk_per_trade_pct: 0.5
    take_profit_pct: 0.50
    stop_loss_pct: 0.25
    fixed_investment_amount: 1000.0
```

## Benefits

### Before Refactoring

❌ Hard-coded 30/20 TP/SL for all symbols  
❌ No distinction between equity and crypto  
❌ Symbol parsing scattered across codebase  
❌ Difficult to add new asset types  

### After Refactoring

✅ Config-driven risk parameters per symbol  
✅ Asset-aware regime classification  
✅ Centralized profile management  
✅ Easy to extend (add forex, futures, etc.)  

## Future Enhancements

1. **Use Orchestrator in FastAPI**: Replace symbol parsing with orchestrator
2. **Asset-Specific Features**: Skip VIX/session features for crypto
3. **Multi-Feed Support**: Support different data feeds per symbol
4. **Backtesting Integration**: Use asset profiles in backtests
5. **Risk Scaling**: Adjust risk based on asset volatility

## Files Changed

### New Files
- `core/live/interfaces.py` - Protocol interfaces
- `core/config/asset_profiles.py` - Asset profile system
- `core/live/orchestrator.py` - Trading orchestrator
- `tests/test_asset_profiles.py` - Asset profile tests
- `tests/test_crypto_integration.py` - Crypto integration tests

### Modified Files
- `core/config.py` - Added `symbols` to Settings
- `config/settings.yaml` - Added symbols section
- `core/regime/engine.py` - Asset-aware regime classification
- `core/live/profit_manager.py` - Config-driven TP/SL
- `core/live/scheduler.py` - Asset profile integration
- `ui/bot_manager.py` - Asset profile loading
- `ui/fastapi_app.py` - Asset profile integration

## Testing

Run tests:
```bash
pytest tests/test_asset_profiles.py
pytest tests/test_crypto_integration.py
```

## Summary

The refactoring successfully:
1. ✅ Removed hard-coded risk parameters
2. ✅ Made system asset-aware
3. ✅ Centralized configuration
4. ✅ Added comprehensive tests
5. ✅ Made system extensible for future asset types

The system is now **cleaner, more configurable, and future-proof**! 🚀

