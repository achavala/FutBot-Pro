"""Backtest options trading pipeline on historical data."""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.agents.options_agent import OptionsAgent
from core.agents.options_selector import OptionsSelector
from core.config.asset_profiles import OptionRiskProfile
from core.regime.engine import RegimeEngine
from core.regime.types import RegimeSignal, RegimeType, TrendDirection, VolatilityLevel, Bias

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run options backtest demo."""
    parser = argparse.ArgumentParser(description="Backtest options trading pipeline")
    parser.add_argument("--underlying", default="SPY", help="Underlying symbol")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--testing-mode", action="store_true", help="Use testing mode with relaxed filters")
    parser.add_argument("--testing_mode", action="store_true", help="Use testing mode (alternative flag)")
    
    args = parser.parse_args()
    
    start_date = datetime.strptime(args.start, "%Y-%m-%d")
    end_date = datetime.strptime(args.end, "%Y-%m-%d")
    
    # Handle both flag formats
    testing_mode = args.testing_mode or args.testing_mode
    
    logger.info(f"Options Backtest Demo: {args.underlying} from {args.start} to {args.end}")
    logger.info(f"Testing mode: {testing_mode}")
    
    # Create option risk profile
    option_risk_profile = OptionRiskProfile(testing_mode=testing_mode)
    
    # Create regime engine
    regime_engine = RegimeEngine()
    
    # Create options agent (without data feed for now - will simulate)
    options_agent = OptionsAgent(
        symbol=args.underlying,
        config={
            "min_confidence": 0.70,
        },
        options_data_feed=None,  # Will simulate options chain
        option_risk_profile=option_risk_profile,
    )
    
    # Simulate trading days
    current_date = start_date
    trades = []
    
    while current_date <= end_date:
        # Skip weekends
        if current_date.weekday() >= 5:
            current_date += timedelta(days=1)
            continue
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing {current_date.strftime('%Y-%m-%d')}")
        logger.info(f"{'='*60}")
        
        # Simulate market data (in real backtest, load from cache/API)
        # For demo, create a mock regime signal
        mock_signal = RegimeSignal(
            timestamp=current_date,
            trend_direction=TrendDirection.DOWN,  # Bearish for PUTs
            volatility_level=VolatilityLevel.MEDIUM,
            regime_type=RegimeType.TREND,
            bias=Bias.SHORT,
            confidence=0.75,
            is_valid=True,
        )
        
        mock_market_state = {
            "close": 450.0,  # Mock SPY price
            "atr_pct": 1.5,
        }
        
        # Evaluate options opportunity
        logger.info(f"Evaluating options opportunity...")
        intents = options_agent.evaluate(mock_signal, mock_market_state)
        
        if intents:
            for intent in intents:
                logger.info(f"\n✅ TRADE INTENT GENERATED:")
                logger.info(f"   Symbol: {intent.symbol}")
                logger.info(f"   Direction: {intent.direction.value}")
                logger.info(f"   Confidence: {intent.confidence:.2%}")
                logger.info(f"   Reason: {intent.reason}")
                logger.info(f"   Metadata: {intent.metadata}")
                trades.append({
                    "date": current_date,
                    "intent": intent,
                })
        else:
            logger.info("   No trade intents generated")
        
        current_date += timedelta(days=1)
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info(f"BACKTEST SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Period: {args.start} to {args.end}")
    logger.info(f"Underlying: {args.underlying}")
    logger.info(f"Total trades: {len(trades)}")
    logger.info(f"Testing mode: {testing_mode}")
    
    if trades:
        logger.info(f"\nTrades generated:")
        for i, trade in enumerate(trades, 1):
            logger.info(f"  {i}. {trade['date'].strftime('%Y-%m-%d')}: {trade['intent'].reason}")
    else:
        logger.info("\n⚠️  No trades generated. Check:")
        logger.info("   - Regime signals (need DOWNTREND + SHORT bias)")
        logger.info("   - Agent alignment (need 2-of-3 or 1-of-3 in testing mode)")
        logger.info("   - Options chain availability")
        logger.info("   - Filter thresholds (try testing mode)")


if __name__ == "__main__":
    main()

