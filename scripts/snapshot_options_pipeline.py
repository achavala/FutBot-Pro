#!/usr/bin/env python3
"""
Contract Snapshot Debugger for Options Pipeline.
Prints detailed information about candidate contracts, filters, alignment, and final decisions.

This is the tool traders use internally at prop firms.
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def snapshot_options_pipeline(
    symbol: str,
    days: int = 1,
    option_type: str = "put",
    testing_mode: bool = True
):
    """
    Take a snapshot of the options pipeline at a specific point in time.
    Shows top candidates, filters, alignment, and why trades did/didn't trigger.
    """
    print("=" * 80)
    print("OPTIONS PIPELINE SNAPSHOT DEBUGGER")
    print("=" * 80)
    print(f"Underlying: {symbol}")
    print(f"Option Type: {option_type.upper()}")
    print(f"Days: {days}")
    print(f"Testing Mode: {testing_mode}")
    print()
    
    try:
        from core.live.data_feed_cached import CachedDataFeed
        from core.live.options_data_feed import OptionsDataFeed
        from core.regime.engine import RegimeEngine
        from core.agents.trend_agent import TrendAgent
        from core.agents.mean_reversion_agent import MeanReversionAgent
        from core.agents.volatility_agent import VolatilityAgent
        from core.agents.options_agent import OptionsAgent
        from core.agents.options_selector import OptionsSelector
        from core.config.asset_profiles import get_asset_profile
        from core.settings_loader import load_settings
        from core.regime.types import MarketState
        
        # Load settings and asset profiles
        settings = load_settings()
        asset_profile = get_asset_profile(symbol, settings)
        
        if asset_profile.asset_type != "equity":
            print(f"❌ {symbol} is not an equity. Options pipeline requires equity underlying.")
            return False
        
        # Set testing mode if requested
        if testing_mode:
            asset_profile.options_risk_profile.testing_mode = True
        
        # Initialize data feeds
        cache_path = Path("data/cache.db")
        feed = CachedDataFeed(cache_path=cache_path, symbols=[symbol])
        
        # Initialize options data feed (for chain/quotes)
        api_key = settings.alpaca.api_key
        api_secret = settings.alpaca.secret_key
        base_url = settings.alpaca.base_url
        
        options_feed = OptionsDataFeed(
            api_key=api_key,
            api_secret=api_secret,
            base_url=base_url
        )
        
        if not options_feed.connect():
            print("⚠️  Could not connect to options data feed. Using cached data only.")
        
        # Initialize regime engine
        regime_engine = RegimeEngine()
        
        # Initialize base agents
        trend_agent = TrendAgent()
        mean_reversion_agent = MeanReversionAgent()
        volatility_agent = VolatilityAgent()
        
        # Initialize options agent
        options_risk_profile = asset_profile.options_risk_profile
        
        # Get options data feed for agent
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
        
        # Initialize options selector (will be created with underlying price)
        options_selector = None  # Will be created after we get current price
        
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
        
        # Process the most recent chunk (simulate current market state)
        chunk_size = 100  # Use last 100 bars
        chunk = bars.iloc[-chunk_size:]
        current_time = chunk.index[-1]
        current_price = chunk["close"].iloc[-1]
        
        print(f"Snapshot Time: {current_time}")
        print(f"Current Price: ${current_price:.2f}")
        print()
        
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
        print("=" * 80)
        print("REGIME ANALYSIS")
        print("=" * 80)
        regime_result = regime_engine.classify_bar(features)
        print(f"Regime: {regime_result.regime}")
        print(f"Confidence: {regime_result.confidence:.2%}")
        print()
        
        # Evaluate base agents
        print("=" * 80)
        print("BASE AGENT SIGNALS")
        print("=" * 80)
        trend_signal = trend_agent.evaluate(market_state)
        mr_signal = mean_reversion_agent.evaluate(market_state)
        vol_signal = volatility_agent.evaluate(market_state)
        
        print(f"Trend Agent: {trend_signal}")
        print(f"Mean Reversion Agent: {mr_signal}")
        print(f"Volatility Agent: {vol_signal}")
        print()
        
        # Check alignment
        alignment_count = sum([
            trend_signal is not None and trend_signal.bias is not None,
            mr_signal is not None and mr_signal.bias is not None,
            vol_signal is not None and vol_signal.bias is not None
        ])
        
        required_alignment = 1 if testing_mode else 2
        alignment_ok = alignment_count >= required_alignment
        
        print(f"Alignment: {alignment_count}/3 agents have signals")
        print(f"Required: {required_alignment}/3 (testing_mode={testing_mode})")
        print(f"Status: {'✅ PASS' if alignment_ok else '❌ FAIL'}")
        print()
        
        if not alignment_ok:
            print("⚠️  Pipeline stops here: Base agent alignment requirement not met")
            return False
        
        # Update options agent signals
        options_agent.trend_agent_signal = trend_signal
        options_agent.mean_reversion_agent_signal = mr_signal
        options_agent.volatility_agent_signal = vol_signal
        
        # Evaluate options agent (this will fetch chain and evaluate contracts)
        print("=" * 80)
        print("OPTIONS AGENT EVALUATION")
        print("=" * 80)
        
        # Enable verbose logging temporarily
        import logging
        logger = logging.getLogger("core.agents.options_agent")
        original_level = logger.level
        logger.setLevel(logging.DEBUG)
        
        # regime_result is already a RegimeSignal, use it directly
        regime_signal = regime_result
        
        market_state_dict = {
            "close": float(chunk["close"].iloc[-1]),
            "open": float(chunk["open"].iloc[-1]),
            "high": float(chunk["high"].iloc[-1]),
            "low": float(chunk["low"].iloc[-1]),
            "volume": float(chunk["volume"].iloc[-1]),
        }
        
        try:
            options_intents = options_agent.evaluate(regime_signal, market_state_dict)
        finally:
            logger.setLevel(original_level)
        
        print(f"Generated intents: {len(options_intents) if options_intents else 0}")
        print()
        
        # Show risk profile thresholds
        print("=" * 80)
        print("RISK PROFILE THRESHOLDS")
        print("=" * 80)
        profile = options_risk_profile
        print(f"Max Spread %: {profile.max_spread_pct:.1%}")
        print(f"Min Open Interest: {profile.min_open_interest}")
        print(f"Min Volume: {profile.min_volume}")
        print(f"Max Theta Decay %: {profile.max_theta_decay_allowed:.1%}")
        print(f"Delta Range: {profile.delta_range}")
        print(f"DTE Range: {profile.min_dte_for_entry} - {profile.max_dte_for_entry} days")
        print(f"IV Percentile Range: {profile.min_iv_percentile:.1%} - {profile.max_iv_percentile:.1%}")
        print()
        
        # If we have intents, show details
        if options_intents:
            print("=" * 80)
            print("GENERATED TRADE INTENTS")
            print("=" * 80)
            for i, intent in enumerate(options_intents[:10], 1):  # Show top 10
                print(f"\n{i}. {intent.symbol}")
                print(f"   Side: {intent.side}")
                print(f"   Quantity: {intent.quantity}")
                print(f"   Entry Price: ${intent.entry_price:.2f}" if hasattr(intent, 'entry_price') else "")
        else:
            print("=" * 80)
            print("NO TRADE INTENTS GENERATED")
            print("=" * 80)
            print("\nPossible reasons:")
            print("  1. No contracts passed validation filters")
            print("  2. Options chain fetch failed")
            print("  3. All contracts rejected by spread/OI/volume checks")
            print("  4. Theta decay too high")
            print("  5. Delta/DTE/IV out of range")
            print("\nCheck logs above for detailed REJECT reasons.")
        
        print()
        print("=" * 80)
        print("SNAPSHOT COMPLETE")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"❌ Error taking snapshot: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Take a snapshot of the options pipeline for debugging"
    )
    parser.add_argument(
        "--symbol", "-s",
        type=str,
        default="SPY",
        help="Underlying symbol"
    )
    parser.add_argument(
        "--days", "-d",
        type=int,
        default=1,
        help="Number of days of historical data to use"
    )
    parser.add_argument(
        "--option-type", "-t",
        type=str,
        choices=["put", "call"],
        default="put",
        help="Option type (put or call)"
    )
    parser.add_argument(
        "--testing-mode",
        action="store_true",
        default=True,
        help="Use testing mode (looser filters)"
    )
    parser.add_argument(
        "--production-mode",
        action="store_true",
        help="Use production mode (stricter filters)"
    )
    
    args = parser.parse_args()
    
    testing_mode = not args.production_mode if args.production_mode else args.testing_mode
    
    success = snapshot_options_pipeline(
        symbol=args.symbol,
        days=args.days,
        option_type=args.option_type,
        testing_mode=testing_mode
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

