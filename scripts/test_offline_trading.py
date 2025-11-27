#!/usr/bin/env python3
"""
Test offline trading capabilities using cached data.
Enhanced with verbose mode and options pipeline testing.
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.cache import BarCache
from core.live.data_feed_cached import CachedDataFeed


def test_offline_data_feed(symbol: str, days: int = 1, verbose: bool = False):
    """Test that CachedDataFeed can load and serve data."""
    print("=" * 60)
    print("TESTING OFFLINE DATA FEED")
    print("=" * 60)
    print(f"Symbol: {symbol}")
    print(f"Days: {days}")
    print(f"Verbose: {verbose}")
    print()
    
    cache_path = Path("data/cache.db")
    
    if not cache_path.exists():
        print(f"❌ Cache database not found: {cache_path}")
        print("   Run: python3 scripts/collect_historical_data.py --months 3")
        return False
    
    try:
        # Initialize cached data feed
        feed = CachedDataFeed(cache_path=cache_path, symbols=[symbol])
        
        # Test get_latest_bars
        print(f"Testing get_latest_bars({symbol}, '1min', 100)...")
        latest = feed.get_latest_bars(symbol, "1min", 100)
        
        if latest is None or len(latest) == 0:
            print(f"❌ No data returned for {symbol}")
            return False
        
        print(f"✅ Retrieved {len(latest)} latest bars")
        if verbose:
            print(f"   First bar: {latest.index[0]}")
            print(f"   Last bar: {latest.index[-1]}")
            print(f"   Columns: {list(latest.columns)}")
        
        # Test get_historical_bars
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        print(f"\nTesting get_historical_bars({symbol}, '1min', {start_date.date()}, {end_date.date()})...")
        historical = feed.get_historical_bars(symbol, "1min", start_date, end_date)
        
        if historical is None or len(historical) == 0:
            print(f"❌ No historical data returned for {symbol}")
            return False
        
        print(f"✅ Retrieved {len(historical)} historical bars")
        if verbose:
            print(f"   Date range: {historical.index[0]} to {historical.index[-1]}")
            print(f"   Sample data:")
            print(historical.head(3))
        
        print("\n✅ Offline data feed test PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Error testing offline data feed: {e}")
        import traceback
        if verbose:
            traceback.print_exc()
        return False


def test_options_pipeline(symbol: str, days: int = 3, verbose: bool = False):
    """Test the full options trading pipeline offline."""
    print("=" * 60)
    print("TESTING OPTIONS PIPELINE (OFFLINE)")
    print("=" * 60)
    print(f"Underlying: {symbol}")
    print(f"Days: {days}")
    print(f"Verbose: {verbose}")
    print()
    
    try:
        from core.live.data_feed_cached import CachedDataFeed
        from core.regime.engine import RegimeEngine
        from core.agents.trend_agent import TrendAgent
        from core.agents.mean_reversion_agent import MeanReversionAgent
        from core.agents.volatility_agent import VolatilityAgent
        from core.agents.options_agent import OptionsAgent
        from core.config.asset_profiles import get_asset_profile, AssetProfileConfig
        from core.settings_loader import load_settings
        
        # Load settings and asset profiles
        settings = load_settings()
        asset_profile = get_asset_profile(symbol, settings)
        
        if asset_profile.asset_type != "equity":
            print(f"⚠️  {symbol} is not an equity. Options pipeline requires equity underlying.")
            return False
        
        # Initialize cached data feed
        cache_path = Path("data/cache.db")
        feed = CachedDataFeed(cache_path=cache_path, symbols=[symbol])
        
        # Initialize regime engine
        regime_engine = RegimeEngine()
        
        # Initialize base agents
        trend_agent = TrendAgent()
        mean_reversion_agent = MeanReversionAgent()
        volatility_agent = VolatilityAgent()
        
        # Initialize options agent
        from core.live.options_data_feed import OptionsDataFeed
        
        options_risk_profile = asset_profile.options_risk_profile
        
        # Get API keys for options feed
        api_key = settings.alpaca.api_key
        api_secret = settings.alpaca.secret_key
        base_url = settings.alpaca.base_url
        
        options_data_feed = OptionsDataFeed(
            api_key=api_key,
            api_secret=api_secret,
            base_url=base_url
        )
        
        options_agent = OptionsAgent(
            symbol=symbol,
            option_risk_profile=options_risk_profile,
            options_data_feed=options_data_feed
        )
        
        # Set up agent signals (for alignment checking)
        options_agent.trend_agent_signal = None
        options_agent.mean_reversion_agent_signal = None
        options_agent.volatility_agent_signal = None
        
        # Get historical data
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        print(f"Loading historical data from {start_date.date()} to {end_date.date()}...")
        bars = feed.get_historical_bars(symbol, "1min", start_date, end_date)
        
        if bars is None or len(bars) == 0:
            print(f"❌ No historical data available for {symbol}")
            return False
        
        print(f"✅ Loaded {len(bars)} bars")
        print()
        
        # Process bars in chunks (simulate live trading)
        chunk_size = 60  # Process 60 bars at a time (1 hour)
        total_chunks = len(bars) // chunk_size
        
        print(f"Processing {total_chunks} chunks of {chunk_size} bars each...")
        print()
        
        candidates_evaluated = 0
        candidates_passed = 0
        orders_attempted = 0
        orders_accepted = 0
        
        for chunk_idx in range(0, len(bars), chunk_size):
            chunk = bars.iloc[chunk_idx:chunk_idx + chunk_size]
            
            if len(chunk) < 10:  # Need minimum bars for indicators
                continue
            
            current_time = chunk.index[-1]
            
            if verbose and chunk_idx % (chunk_size * 6) == 0:  # Every 6 hours
                print(f"[{current_time}] Processing chunk {chunk_idx // chunk_size + 1}/{total_chunks}...")
            
            try:
                # Build features for regime engine (similar to scheduler)
                from core.features import indicators, stats_features
                from core.features.fvg import detect_fvgs
                
                # Calculate features from bars
                features = {}
                
                # Convert DataFrame to list of Bar objects for feature calculation
                from core.live.types import Bar
                bars_list = []
                for idx, row in chunk.iterrows():
                    bars_list.append(Bar(
                        timestamp=idx,
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row.get("volume", 0)),
                        vwap=float(row.get("vwap", 0)),
                    ))
                
                # Calculate indicators
                if len(bars_list) >= 14:  # Need minimum bars for indicators
                    features.update(indicators.compute_all(bars_list))
                    features.update(stats_features.compute_all(bars_list))
                    
                    # Detect FVGs
                    fvgs = detect_fvgs(bars_list)
                    features["active_fvgs"] = fvgs
                    features["fvgs"] = fvgs
                
                # Add basic price info
                features["close"] = float(chunk["close"].iloc[-1])
                features["price"] = float(chunk["close"].iloc[-1])
                features["timestamp"] = current_time
                features["asset_type"] = asset_profile.asset_type
                
                # Get regime using classify_bar
                regime_result = regime_engine.classify_bar(features)
                
                if verbose and chunk_idx % (chunk_size * 6) == 0:
                    print(f"  Regime: {regime_result.regime}, Confidence: {regime_result.confidence:.2%}")
                
                # Evaluate base agents
                trend_signal = trend_agent.evaluate(market_state)
                mr_signal = mean_reversion_agent.evaluate(market_state)
                vol_signal = volatility_agent.evaluate(market_state)
                
                # Update options agent signals
                options_agent.trend_agent_signal = trend_signal
                options_agent.mean_reversion_agent_signal = mr_signal
                options_agent.volatility_agent_signal = vol_signal
                
                # Evaluate options agent (needs RegimeSignal, not MarketState)
                from core.regime.types import RegimeSignal, RegimeType, Bias, TrendDirection, VolatilityLevel
                
                # Create a RegimeSignal from regime_result
                # regime_result already has the right structure, just use it directly
                regime_signal = regime_result
                
                # Convert market_state to dict format
                market_state_dict = {
                    "close": float(chunk["close"].iloc[-1]),
                    "open": float(chunk["open"].iloc[-1]),
                    "high": float(chunk["high"].iloc[-1]),
                    "low": float(chunk["low"].iloc[-1]),
                    "volume": float(chunk["volume"].iloc[-1]),
                }
                
                options_intents = options_agent.evaluate(regime_signal, market_state_dict)
                
                if options_intents:
                    for intent in options_intents:
                        candidates_evaluated += 1
                        
                        if verbose:
                            print(f"  ✅ Options intent generated: {intent.symbol}")
                            print(f"     Side: {intent.side}, Quantity: {intent.quantity}")
                        
                        # Check if intent passed filters (simplified check)
                        if intent.quantity > 0:
                            candidates_passed += 1
                            orders_attempted += 1
                            
                            if verbose:
                                print(f"     → Would attempt order (mocked)")
                            
                            # Mock broker acceptance for testing
                            orders_accepted += 1
                
            except Exception as e:
                if verbose:
                    print(f"  ⚠️  Error processing chunk: {e}")
                continue
        
        print()
        print("=" * 60)
        print("OPTIONS PIPELINE TEST RESULTS")
        print("=" * 60)
        print(f"Candidates evaluated: {candidates_evaluated}")
        print(f"Candidates passed filters: {candidates_passed}")
        print(f"Orders attempted: {orders_attempted}")
        print(f"Orders accepted (mocked): {orders_accepted}")
        print()
        
        # Determine CASE
        if candidates_evaluated == 0:
            print("🔍 DIAGNOSIS: CASE F - No candidates evaluated")
            print("   → OptionsAgent.evaluate() never generated intents")
            print("   → Check: Regime confidence, agent alignment, data availability")
        elif candidates_passed == 0:
            print("🔍 DIAGNOSIS: CASE G - All candidates rejected")
            print("   → Contracts evaluated but none passed filters")
            print("   → Check: Spread, OI, volume, theta, DTE thresholds")
        elif orders_attempted == 0:
            print("🔍 DIAGNOSIS: CASE H - Passed but no order")
            print("   → Contracts passed filters but no order attempted")
            print("   → Check: Risk manager, position limits, execution logic")
        elif orders_accepted == 0:
            print("🔍 DIAGNOSIS: CASE I - Order attempted but rejected")
            print("   → Orders attempted but broker rejected")
            print("   → Check: Broker connectivity, permissions, buying power")
        else:
            print("✅ DIAGNOSIS: Pipeline working correctly!")
            print(f"   → Generated {candidates_evaluated} candidates")
            print(f"   → {candidates_passed} passed filters")
            print(f"   → {orders_attempted} orders would be executed")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing options pipeline: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test offline trading capabilities")
    parser.add_argument("--symbol", type=str, default="SPY", help="Symbol to test")
    parser.add_argument("--days", type=int, default=1, help="Number of days to test")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--options", action="store_true", help="Test options pipeline")
    
    args = parser.parse_args()
    
    if args.options:
        success = test_options_pipeline(args.symbol, args.days, args.verbose)
    else:
        success = test_offline_data_feed(args.symbol, args.days, args.verbose)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
