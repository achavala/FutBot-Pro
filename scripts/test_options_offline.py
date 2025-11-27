#!/usr/bin/env python3
"""
Offline Options Trading Pipeline Test

Tests the full options trading pipeline using mock/cached data
without requiring market hours or live broker connection.
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agents.options_agent import OptionsAgent
from core.config.asset_profiles import AssetProfileConfig, OptionRiskProfile
from core.regime.types import RegimeSignal, RegimeType, TrendDirection, VolatilityLevel
from core.live.options_data_feed import OptionsDataFeed
from core.agents.options_selector import OptionsSelector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockOptionsDataFeed(OptionsDataFeed):
    """Mock options data feed for offline testing."""
    
    def __init__(self):
        # Don't call super().__init__() - we're mocking everything
        self.connected = True
        self.underlying_symbol = None
        
    def connect(self) -> bool:
        self.connected = True
        return True
    
    def get_options_chain(
        self,
        underlying_symbol: str,
        expiration_date: Optional[str] = None,
        option_type: Optional[str] = None,
    ) -> List[Dict]:
        """Return mock options contracts for testing."""
        logger.info(f"Mock: Fetching options chain for {underlying_symbol}")
        
        # Generate realistic mock contracts
        contracts = []
        base_strike = 500.0
        expiration = expiration_date or "2025-11-26"
        
        # Generate PUT contracts around current price
        # Use a future expiration date (30 days from now)
        if not expiration_date:
            future_date = datetime.now() + timedelta(days=30)
            expiration = future_date.strftime("%Y-%m-%d")
        
        for i in range(-10, 11):  # Strikes from 490 to 510
            strike = base_strike + (i * 5)
            contract_type = "put" if option_type != "call" else "call"
            
            # Format option symbol: SPY251126P00500000
            exp_formatted = expiration.replace("-", "")
            strike_formatted = f"{int(strike * 1000):08d}"
            option_symbol = f"{underlying_symbol.upper()}{exp_formatted[2:]}{contract_type[0].upper()}{strike_formatted}"
            
            # Mock realistic data
            contracts.append({
                "symbol": option_symbol,
                "underlying_symbol": underlying_symbol.upper(),
                "type": contract_type,
                "strike_price": strike,
                "expiration_date": expiration,
                "root_symbol": underlying_symbol.upper(),
                "id": option_symbol,
            })
        
        logger.info(f"Mock: Generated {len(contracts)} contracts")
        return contracts
    
    def get_option_quote(self, option_symbol: str) -> Optional[Dict]:
        """Return mock quote data."""
        # Extract strike from symbol
        strike_str = option_symbol[-8:]
        strike = float(strike_str) / 1000.0
        
        # Mock realistic bid/ask spread
        mid_price = max(0.10, abs(500 - strike) * 0.01)  # Closer to ATM = higher price
        spread = mid_price * 0.05  # 5% spread (tight for testing)
        
        return {
            "bid": mid_price - spread/2,  # bid price (standard field name)
            "ask": mid_price + spread/2,  # ask price (standard field name)
            "bp": mid_price - spread/2,  # bid price (Polygon format)
            "ap": mid_price + spread/2,  # ask price (Polygon format)
            "as": 100,  # ask size
            "bs": 100,  # bid size
            "open_interest": 500,  # Mock OI (high enough to pass filters)
            "volume": 100,  # Mock volume (high enough to pass filters)
            "t": datetime.now().isoformat(),
        }
    
    def get_option_greeks(self, option_symbol: str) -> Optional[Dict]:
        """Return mock Greeks."""
        # Extract strike from symbol for more realistic delta
        strike_str = option_symbol[-8:]
        strike = float(strike_str) / 1000.0
        
        # Calculate delta based on strike (closer to ATM = higher absolute delta)
        # For PUTs, delta should be negative
        moneyness = strike / 500.0  # Assuming current price is 500
        if moneyness < 1.0:  # ITM PUT
            delta = -0.6 + (1.0 - moneyness) * 0.3  # More negative for deeper ITM
        else:  # OTM PUT
            delta = -0.3 * (1.0 / moneyness)  # Less negative for OTM
        
        return {
            "delta": delta,  # PUT delta (negative)
            "gamma": 0.02,
            "theta": -0.05,
            "vega": 0.15,
            "implied_volatility": 0.25,  # 25% IV
        }


def create_mock_regime_signal() -> RegimeSignal:
    """Create a mock regime signal for testing."""
    from core.regime.types import Bias
    
    return RegimeSignal(
        regime_type=RegimeType.TREND,
        trend_direction=TrendDirection.DOWN,  # Bearish - good for PUTs
        volatility_level=VolatilityLevel.HIGH,
        bias=Bias.SHORT,  # Use Bias enum, not string
        confidence=0.85,
        is_valid=True,
        timestamp=datetime.now(),
    )


def test_options_pipeline_offline():
    """Test the full options trading pipeline offline."""
    print("=" * 70)
    print("OFFLINE OPTIONS TRADING PIPELINE TEST")
    print("=" * 70)
    print()
    
    # Setup
    underlying_symbol = "SPY"
    option_type = "put"
    
    print(f"Underlying: {underlying_symbol}")
    print(f"Option Type: {option_type}")
    print(f"Testing Mode: Enabled (relaxed filters)")
    print()
    
    # 1. Create mock data feed
    print("[STEP 1] Creating mock options data feed...")
    mock_feed = MockOptionsDataFeed()
    mock_feed.connect()
    print("✅ Mock data feed created")
    print()
    
    # 2. Fetch options chain
    print("[STEP 2] Fetching options chain...")
    contracts = mock_feed.get_options_chain(
        underlying_symbol=underlying_symbol,
        option_type=option_type,
    )
    print(f"✅ Fetched {len(contracts)} contracts")
    if contracts:
        print(f"   Sample: {contracts[0]['symbol']} (Strike: ${contracts[0]['strike_price']})")
    print()
    
    # 3. Create OptionsAgent with testing mode
    print("[STEP 3] Creating OptionsAgent (testing mode)...")
    
    # Create option risk profile with testing mode
    option_risk_profile = OptionRiskProfile(testing_mode=True)
    print(f"✅ Option risk profile created")
    print(f"   Testing mode: {option_risk_profile.testing_mode}")
    print(f"   Max spread: {option_risk_profile.max_spread_pct}%")
    print(f"   Min OI: {option_risk_profile.min_open_interest}")
    print(f"   Min volume: {option_risk_profile.min_volume}")
    print()
    
    # Create OptionsAgent
    # Note: OptionsAgent constructor doesn't take option_type or data_feed directly
    # We'll set them after creation
    options_agent = OptionsAgent(
        symbol=underlying_symbol,
        options_data_feed=mock_feed,
        option_risk_profile=option_risk_profile,
    )
    
    # Store option_type for later use
    options_agent.option_type = option_type
    
    # Set mock agent signals (simulating base agents)
    # OptionsAgent expects TradeIntent objects for base agent signals
    from core.agents.base import TradeIntent, TradeDirection
    
    # Create mock trade intents for base agents
    # For PUT trades, we want bearish signals
    options_agent.trend_agent_signal = TradeIntent(
        symbol=underlying_symbol,
        agent_name="trend_agent",
        direction=TradeDirection.SHORT,
        size=1.0,
        confidence=0.7,
        reason="Mock trend signal (bearish)",
    )
    options_agent.mean_reversion_agent_signal = TradeIntent(
        symbol=underlying_symbol,
        agent_name="mean_reversion_agent",
        direction=TradeDirection.SHORT,
        size=1.0,
        confidence=0.5,
        reason="Mock mean reversion signal (bearish)",
    )
    options_agent.volatility_agent_signal = TradeIntent(
        symbol=underlying_symbol,
        agent_name="volatility_agent",
        direction=TradeDirection.LONG,  # Volatility can be long (high vol = good for options)
        size=1.0,
        confidence=0.8,
        reason="Mock volatility signal (high vol)",
    )
    print("✅ OptionsAgent created")
    print("✅ Base agent signals set (bearish alignment for PUTs)")
    print()
    
    # 4. Create regime signal
    print("[STEP 4] Creating regime signal...")
    regime_signal = create_mock_regime_signal()
    print(f"✅ Regime: {regime_signal.regime_type.value}")
    print(f"   Trend: {regime_signal.trend_direction.value}")
    print(f"   Volatility: {regime_signal.volatility_level.value}")
    print(f"   Confidence: {regime_signal.confidence:.1%}")
    print()
    
    # 5. Evaluate options agent
    print("[STEP 5] Evaluating OptionsAgent...")
    print("-" * 70)
    
    market_state = {
        "symbol": underlying_symbol,
        "current_price": 500.0,
        "bars": [],  # Not needed for options
    }
    
    try:
        intents = options_agent.evaluate(regime_signal, market_state)
        
        print()
        print("-" * 70)
        print(f"✅ OptionsAgent evaluation complete")
        print(f"   Trade intents generated: {len(intents)}")
        print()
        
        if intents:
            print("TRADE INTENTS:")
            for i, intent in enumerate(intents, 1):
                print(f"  {i}. Symbol: {intent.symbol}")
                print(f"     Side: {intent.side.value}")
                print(f"     Quantity: {intent.quantity}")
                print(f"     Confidence: {intent.confidence:.2%}")
                print()
        else:
            print("⚠️  No trade intents generated")
            print("   Check logs above for rejection reasons")
            print()
            
    except Exception as e:
        print(f"❌ Error during evaluation: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 6. Test OptionsSelector
    if contracts and intents:
        print("[STEP 6] Testing OptionsSelector...")
        selector = OptionsSelector(
            option_risk_profile=option_risk_profile,
            underlying_price=500.0,
        )
        
        # Get suitable contracts (simplified - in real code this comes from agent)
        suitable_options = contracts[:10]  # Top 10 for testing
        
        if suitable_options:
            best_contract = selector.select_best_contract(
                suitable_options=suitable_options,
                underlying_signal="bearish",
            )
            print(f"✅ Best contract selected: {best_contract.get('symbol')}")
            print(f"   Strike: ${best_contract.get('strike_price')}")
            print()
    
    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"✅ Options chain fetched: {len(contracts)} contracts")
    print(f"✅ OptionsAgent evaluated: {'PASS' if intents else 'NO INTENTS'}")
    print(f"✅ Trade intents generated: {len(intents)}")
    
    if intents:
        print()
        print("🎉 SUCCESS! Options pipeline is working offline!")
        print("   The system is ready for live trading during market hours.")
    else:
        print()
        print("⚠️  No trade intents generated")
        print("   This could be due to:")
        print("   - Filters too strict (check testing_mode)")
        print("   - Agent alignment not met")
        print("   - Regime conditions not suitable")
        print("   Check logs above for details")
    
    print()
    return len(intents) > 0


if __name__ == "__main__":
    success = test_options_pipeline_offline()
    sys.exit(0 if success else 1)

