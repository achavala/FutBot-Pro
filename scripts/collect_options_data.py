#!/usr/bin/env python3
"""Collect historical options chain data from Alpaca or Polygon APIs."""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from services.options_data_feed import OptionsDataFeed

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def collect_options_chain(
    symbol: str,
    api_provider: str = "alpaca",
    option_type: Optional[str] = None,
    expiration_date: Optional[str] = None,
    days_back: int = 30,
):
    """
    Collect options chain data for a symbol.
    
    Args:
        symbol: Underlying symbol (e.g., "SPY", "QQQ")
        api_provider: "alpaca" or "polygon"
        option_type: "call" or "put" (None for both)
        expiration_date: Specific expiration date (YYYY-MM-DD) or None for all
        days_back: Number of days to look back for expirations
    """
    # Get API credentials
    if api_provider == "alpaca":
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_API_SECRET")
        if not api_key or not api_secret:
            logger.error("❌ Alpaca API credentials not found in environment")
            return
    elif api_provider == "polygon":
        api_key = os.getenv("POLYGON_API_KEY") or os.getenv("MASSIVE_API_KEY")
        if not api_key:
            logger.error("❌ Polygon/Massive API key not found in environment")
            return
        api_secret = None
    else:
        logger.error(f"❌ Unsupported API provider: {api_provider}")
        return
    
    # Initialize options data feed
    try:
        feed = OptionsDataFeed(
            api_provider=api_provider,
            api_key=api_key,
            api_secret=api_secret,
        )
        logger.info(f"✅ Options data feed initialized ({api_provider})")
    except Exception as e:
        logger.error(f"❌ Failed to initialize options data feed: {e}")
        return
    
    # Fetch options chain
    logger.info(f"📊 Fetching options chain for {symbol}...")
    logger.info(f"   Option type: {option_type or 'all'}")
    logger.info(f"   Expiration: {expiration_date or 'all'}")
    
    try:
        contracts = feed.get_options_chain(
            underlying_symbol=symbol,
            option_type=option_type,
            expiration_date=expiration_date,
        )
        
        if not contracts:
            logger.warning(f"⚠️ No options contracts found for {symbol}")
            return
        
        logger.info(f"✅ Found {len(contracts)} options contracts")
        
        # Display sample contracts
        logger.info("\n📋 Sample contracts:")
        for i, contract in enumerate(contracts[:10]):
            logger.info(
                f"   {i+1}. {contract['symbol']} | "
                f"Strike: ${contract['strike_price']:.2f} | "
                f"Type: {contract['option_type'].upper()} | "
                f"Exp: {contract['expiration_date']}"
            )
        
        if len(contracts) > 10:
            logger.info(f"   ... and {len(contracts) - 10} more contracts")
        
        # Fetch quotes and Greeks for sample contracts
        logger.info("\n📊 Fetching quotes and Greeks for sample contracts...")
        sample_contracts = contracts[:5]  # Sample first 5
        
        for contract in sample_contracts:
            option_symbol = contract["symbol"]
            logger.info(f"\n   Analyzing {option_symbol}:")
            
            # Get quote
            quote = feed.get_option_quote(option_symbol)
            if quote:
                logger.info(
                    f"      Quote: Bid=${quote['bid']:.2f}, Ask=${quote['ask']:.2f}, "
                    f"Last=${quote['last']:.2f}, Volume={quote['volume']}, OI={quote['open_interest']}"
                )
            else:
                logger.warning(f"      ⚠️ No quote available")
            
            # Get Greeks
            greeks = feed.get_option_greeks(option_symbol)
            if greeks:
                logger.info(
                    f"      Greeks: Δ={greeks['delta']:.3f}, Γ={greeks['gamma']:.4f}, "
                    f"Θ={greeks['theta']:.4f}, ν={greeks['vega']:.4f}, IV={greeks['implied_volatility']:.2%}"
                )
            else:
                logger.warning(f"      ⚠️ No Greeks available")
        
        logger.info(f"\n✅ Options data collection complete for {symbol}")
        logger.info(f"   Total contracts: {len(contracts)}")
        
        return contracts
        
    except Exception as e:
        logger.error(f"❌ Error collecting options data: {e}", exc_info=True)
        return None


def main():
    parser = argparse.ArgumentParser(description="Collect options chain data")
    parser.add_argument("--symbol", required=True, help="Underlying symbol (e.g., SPY, QQQ)")
    parser.add_argument("--provider", default="alpaca", choices=["alpaca", "polygon"], help="API provider")
    parser.add_argument("--type", choices=["call", "put"], help="Option type filter")
    parser.add_argument("--expiration", help="Expiration date (YYYY-MM-DD)")
    parser.add_argument("--days-back", type=int, default=30, help="Days to look back for expirations")
    
    args = parser.parse_args()
    
    collect_options_chain(
        symbol=args.symbol,
        api_provider=args.provider,
        option_type=args.type,
        expiration_date=args.expiration,
        days_back=args.days_back,
    )


if __name__ == "__main__":
    main()

