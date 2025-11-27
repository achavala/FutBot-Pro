#!/usr/bin/env python3
"""
Verify offline mode capabilities.
Checks that cached data is available and valid for offline testing.

Comprehensive validation including:
- Day-boundary alignment
- Bar interval integrity
- Data sanity metrics
- Timestamp order and timezone
- Gap detection
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Dict
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.cache import BarCache
from core.live.data_feed_cached import CachedDataFeed

# Colors for output
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'


def check_bar_coverage(cache: BarCache, symbol: str, timeframe: str) -> Tuple[bool, int, str]:
    """Check bar coverage for a symbol."""
    try:
        bars = cache.load(symbol, timeframe)
        
        if bars.empty:
            return False, 0, "No bars found"
        
        count = len(bars)
        
        # Check date range
        if count > 0:
            first_bar = bars.index[0]
            last_bar = bars.index[-1]
            date_range = f"{first_bar.date()} to {last_bar.date()}"
            
            return True, count, date_range
        else:
            return False, 0, "Empty DataFrame"
            
    except Exception as e:
        return False, 0, f"Error: {e}"


def check_day_boundary_alignment(bars, asset_type: str = "equity") -> Tuple[bool, List[str]]:
    """
    Check that bars align correctly at day boundaries.
    For equities: first bar should be 09:30:00, last bar 16:00:00
    For crypto: should have 1440 bars per UTC day (00:00:00 to 23:59:00)
    """
    if bars.empty or len(bars) < 2:
        return True, []
    
    issues = []
    
    # Group by day
    bars_by_day = bars.groupby(bars.index.date)
    
    for day, day_bars in list(bars_by_day)[:10]:  # Check first 10 days
        first_bar_time = day_bars.index[0].time()
        last_bar_time = day_bars.index[-1].time()
        
        if asset_type == "equity":
            # Equities: first bar should be 09:30:00, last bar 16:00:00
            expected_start = datetime.strptime("09:30:00", "%H:%M:%S").time()
            expected_end = datetime.strptime("16:00:00", "%H:%M:%S").time()
            
            if first_bar_time != expected_start:
                issues.append(f"{day}: First bar at {first_bar_time}, expected {expected_start}")
            if last_bar_time != expected_end:
                issues.append(f"{day}: Last bar at {last_bar_time}, expected {expected_end}")
        
        elif asset_type == "crypto":
            # Crypto: should have ~1440 bars per day (24 hours * 60 minutes)
            expected_bars_per_day = 1440
            actual_bars = len(day_bars)
            
            if actual_bars < expected_bars_per_day * 0.95:  # Allow 5% tolerance
                issues.append(f"{day}: Only {actual_bars} bars, expected ~{expected_bars_per_day}")
    
    return len(issues) == 0, issues


def check_bar_interval_integrity(bars) -> Tuple[bool, Dict]:
    """
    Verify that every timestamp difference is exactly 60 seconds.
    Returns: (is_valid, stats_dict)
    """
    if bars.empty or len(bars) < 2:
        return True, {}
    
    # Calculate time differences between consecutive bars
    timestamps = bars.index
    diffs = pd.Series(timestamps).diff().dropna()
    diff_seconds = diffs.dt.total_seconds()
    
    expected_interval = 60.0  # 60 seconds for 1-minute bars
    tolerance = 1.0  # Allow 1 second tolerance
    
    # Find intervals that are not exactly 60 seconds
    invalid_intervals = diff_seconds[
        (diff_seconds < expected_interval - tolerance) | 
        (diff_seconds > expected_interval + tolerance)
    ]
    
    stats = {
        "total_bars": len(bars),
        "total_intervals": len(diff_seconds),
        "invalid_intervals": len(invalid_intervals),
        "min_interval": float(diff_seconds.min()),
        "max_interval": float(diff_seconds.max()),
        "mean_interval": float(diff_seconds.mean()),
        "median_interval": float(diff_seconds.median()),
    }
    
    is_valid = len(invalid_intervals) == 0
    
    if not is_valid:
        stats["invalid_interval_details"] = [
            {
                "index": int(idx),
                "interval_seconds": float(val),
                "timestamp": str(timestamps[int(idx)])
            }
            for idx, val in invalid_intervals.head(10).items()
        ]
    
    return is_valid, stats


def check_duplicate_bars(bars) -> Tuple[bool, int]:
    """Check for duplicate timestamps."""
    if bars.empty:
        return True, 0
    
    duplicates = bars.index.duplicated()
    duplicate_count = duplicates.sum()
    
    return duplicate_count == 0, int(duplicate_count)


def check_data_sanity(bars, symbol: str) -> Tuple[bool, Dict]:
    """
    Comprehensive data sanity checks:
    - Missing bars percentage
    - Price sanity (no outliers)
    - Volume sanity
    - Spread between open/close
    """
    if bars.empty:
        return False, {"error": "No bars to check"}
    
    stats = {}
    issues = []
    
    # 1. Price sanity checks
    if "close" in bars.columns:
        close_prices = bars["close"]
        price_change_pct = close_prices.pct_change().abs() * 100
        
        # Check for extreme price changes (>50% in one minute is suspicious)
        extreme_changes = price_change_pct[price_change_pct > 50]
        if len(extreme_changes) > 0:
            issues.append(f"Found {len(extreme_changes)} bars with >50% price change")
        
        stats["price_stats"] = {
            "min": float(close_prices.min()),
            "max": float(close_prices.max()),
            "mean": float(close_prices.mean()),
            "extreme_changes": len(extreme_changes)
        }
    
    # 2. Volume sanity checks
    if "volume" in bars.columns:
        volumes = bars["volume"]
        zero_volume_count = (volumes == 0).sum()
        
        if zero_volume_count > len(bars) * 0.1:  # More than 10% zero volume
            issues.append(f"{zero_volume_count} bars ({zero_volume_count/len(bars)*100:.1f}%) have zero volume")
        
        stats["volume_stats"] = {
            "min": float(volumes.min()),
            "max": float(volumes.max()),
            "mean": float(volumes.mean()),
            "zero_volume_count": int(zero_volume_count)
        }
    
    # 3. Spread sanity (open vs close)
    if "open" in bars.columns and "close" in bars.columns:
        spreads = ((bars["close"] - bars["open"]) / bars["open"] * 100).abs()
        mean_spread = spreads.mean()
        
        if mean_spread > 10:  # Mean spread > 10% is suspicious
            issues.append(f"Mean spread between open/close is {mean_spread:.2f}% (suspicious)")
        
        stats["spread_stats"] = {
            "mean_pct": float(mean_spread),
            "max_pct": float(spreads.max())
        }
    
    # 4. Missing bars estimation
    if len(bars) > 1:
        first_ts = bars.index[0]
        last_ts = bars.index[-1]
        expected_minutes = (last_ts - first_ts).total_seconds() / 60
        actual_bars = len(bars)
        missing_pct = max(0, (1 - actual_bars / expected_minutes) * 100) if expected_minutes > 0 else 0
        
        stats["coverage"] = {
            "first_timestamp": str(first_ts),
            "last_timestamp": str(last_ts),
            "expected_bars": int(expected_minutes),
            "actual_bars": actual_bars,
            "missing_pct": round(missing_pct, 2)
        }
        
        if missing_pct > 5:  # More than 5% missing
            issues.append(f"Missing {missing_pct:.1f}% of expected bars")
    
    return len(issues) == 0, {"stats": stats, "issues": issues}


def check_timestamp_order(bars) -> Tuple[bool, str]:
    """Check that timestamps are in ascending order."""
    if bars.empty:
        return False, "No bars to check"
    
    if len(bars) < 2:
        return True, "OK"
    
    # Check if timestamps are increasing
    timestamps = bars.index
    for i in range(1, min(1000, len(timestamps))):  # Check first 1000 bars
        if timestamps[i] < timestamps[i-1]:
            return False, f"Timestamp out of order at index {i}"
    
    return True, "Timestamps in ascending order"


def check_timezone(bars) -> Tuple[bool, str]:
    """Check that timestamps are timezone-aware (UTC)."""
    if bars.empty:
        return False, "No bars to check"
    
    sample_timestamp = bars.index[0]
    
    if sample_timestamp.tzinfo is None:
        return False, "Timestamps are timezone-naive"
    
    if sample_timestamp.tzinfo != timezone.utc:
        return False, f"Timestamps not in UTC: {sample_timestamp.tzinfo}"
    
    return True, "Timestamps in UTC"


def check_data_feed(symbol: str) -> Tuple[bool, str]:
    """Check that CachedDataFeed can load data."""
    try:
        cache_path = Path("data/cache.db")
        feed = CachedDataFeed(cache_path=cache_path, symbols=[symbol])
        
        # Test get_latest_bars
        latest = feed.get_latest_bars(symbol, "1min", 10)
        if latest is None or len(latest) == 0:
            return False, "get_latest_bars() returned no data"
        
        # Test get_historical_bars
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)
        historical = feed.get_historical_bars(symbol, "1min", start_date, end_date)
        if historical is None or len(historical) == 0:
            return False, "get_historical_bars() returned no data"
        
        return True, f"get_latest_bars: {len(latest)} bars, get_historical_bars: {len(historical)} bars"
        
    except Exception as e:
        return False, f"Error: {e}"


def check_options_chains() -> Tuple[bool, int, str]:
    """Check that options chains are available."""
    options_cache_dir = Path("data/options_chains")
    
    if not options_cache_dir.exists():
        return False, 0, "Options cache directory not found"
    
    chain_files = list(options_cache_dir.glob("*.json"))
    
    if len(chain_files) == 0:
        return False, 0, "No options chain files found"
    
    return True, len(chain_files), f"Found {len(chain_files)} chain files"


def main():
    """Run offline mode verification."""
    print("=" * 60)
    print("OFFLINE MODE VERIFICATION")
    print("=" * 60)
    print()
    
    cache_path = Path("data/cache.db")
    
    if not cache_path.exists():
        print(f"{RED}❌ Cache database not found: {cache_path}{NC}")
        print("   Run: python3 scripts/collect_historical_data.py --months 3")
        sys.exit(1)
    
    cache = BarCache(cache_path)
    
    # Test symbols with asset types
    test_symbols = {
        "SPY": "equity",
        "QQQ": "equity",
        "BTC/USD": "crypto",
    }
    
    all_passed = True
    
    print("Checking bar data coverage...")
    print()
    
    for symbol, asset_type in test_symbols.items():
        print(f"{BLUE}{'='*60}{NC}")
        print(f"{BLUE}Testing {symbol} ({asset_type.upper()}){NC}")
        print(f"{BLUE}{'='*60}{NC}")
        
        # Check coverage
        has_data, count, info = check_bar_coverage(cache, symbol, "1min")
        
        if has_data:
            print(f"  {GREEN}✅ Coverage: {count} bars, {info}{NC}")
            
            # Load bars for validation
            bars = cache.load(symbol, "1min")
            
            # 1. Check timestamp order
            order_ok, order_msg = check_timestamp_order(bars)
            if order_ok:
                print(f"  {GREEN}✅ Timestamp order: {order_msg}{NC}")
            else:
                print(f"  {RED}❌ Timestamp order: {order_msg}{NC}")
                all_passed = False
            
            # 2. Check timezone
            tz_ok, tz_msg = check_timezone(bars)
            if tz_ok:
                print(f"  {GREEN}✅ Timezone: {tz_msg}{NC}")
            else:
                print(f"  {YELLOW}⚠️  Timezone: {tz_msg}{NC}")
            
            # 3. Check for duplicates
            dup_ok, dup_count = check_duplicate_bars(bars)
            if dup_ok:
                print(f"  {GREEN}✅ Duplicates: None found{NC}")
            else:
                print(f"  {RED}❌ Duplicates: Found {dup_count} duplicate timestamps{NC}")
                all_passed = False
            
            # 4. Check bar interval integrity
            interval_ok, interval_stats = check_bar_interval_integrity(bars)
            if interval_ok:
                print(f"  {GREEN}✅ Bar intervals: All {interval_stats['mean_interval']:.1f}s (expected 60s){NC}")
            else:
                print(f"  {RED}❌ Bar intervals: {interval_stats['invalid_intervals']} invalid intervals found{NC}")
                print(f"     Range: {interval_stats['min_interval']:.1f}s - {interval_stats['max_interval']:.1f}s")
                all_passed = False
            
            # 5. Check day boundary alignment
            boundary_ok, boundary_issues = check_day_boundary_alignment(bars, asset_type)
            if boundary_ok:
                print(f"  {GREEN}✅ Day boundaries: Aligned correctly{NC}")
            else:
                print(f"  {YELLOW}⚠️  Day boundaries: {len(boundary_issues)} issues found{NC}")
                for issue in boundary_issues[:3]:  # Show first 3
                    print(f"     - {issue}")
            
            # 6. Check data sanity
            sanity_ok, sanity_data = check_data_sanity(bars, symbol)
            if sanity_ok:
                print(f"  {GREEN}✅ Data sanity: All checks passed{NC}")
            else:
                print(f"  {YELLOW}⚠️  Data sanity: {len(sanity_data.get('issues', []))} issues found{NC}")
                for issue in sanity_data.get('issues', [])[:3]:  # Show first 3
                    print(f"     - {issue}")
            
            # Print sanity stats
            if "stats" in sanity_data:
                stats = sanity_data["stats"]
                if "coverage" in stats:
                    cov = stats["coverage"]
                    print(f"  {BLUE}📊 Coverage: {cov['actual_bars']}/{cov['expected_bars']} bars "
                          f"({100-cov['missing_pct']:.1f}% complete){NC}")
                if "price_stats" in stats:
                    price = stats["price_stats"]
                    print(f"  {BLUE}📊 Price range: ${price['min']:.2f} - ${price['max']:.2f} "
                          f"(mean: ${price['mean']:.2f}){NC}")
            
            # 7. Check data feed
            feed_ok, feed_msg = check_data_feed(symbol)
            if feed_ok:
                print(f"  {GREEN}✅ Data feed: {feed_msg}{NC}")
            else:
                print(f"  {RED}❌ Data feed: {feed_msg}{NC}")
                all_passed = False
        else:
            print(f"  {RED}❌ No data: {info}{NC}")
            all_passed = False
        
        print()
    
    # Check options chains
    print(f"{BLUE}{'='*60}{NC}")
    print(f"{BLUE}Checking options chains...{NC}")
    print(f"{BLUE}{'='*60}{NC}")
    has_options, count, info = check_options_chains()
    if has_options:
        print(f"  {GREEN}✅ Options chains: {info}{NC}")
    else:
        print(f"  {YELLOW}⚠️  Options chains: {info}{NC}")
        print("   (Options chains are optional for basic offline testing)")
    print()
    
    # Check metadata
    metadata_path = Path("data/metadata.json")
    if metadata_path.exists():
        import json
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            print(f"{BLUE}{'='*60}{NC}")
            print(f"{BLUE}Ingestion Metadata{NC}")
            print(f"{BLUE}{'='*60}{NC}")
            print(f"  Last ingestion: {metadata.get('last_ingestion', 'Unknown')}")
            print(f"  Months collected: {metadata.get('months_collected', 'Unknown')}")
            print(f"  API source: {metadata.get('api_source', 'Unknown')}")
            print(f"  Cache size: {metadata.get('cache_size_mb', 'Unknown')} MB")
            print()
        except:
            pass
    
    # Summary
    print("=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    if all_passed:
        print(f"{GREEN}✅ All critical checks passed!{NC}")
        print()
        print("System is ready for offline testing!")
        print()
        print("You can now:")
        print("  1. Use CachedDataFeed for offline trading")
        print("  2. Run backtests with cached data")
        print("  3. Test options strategies offline")
        print("  4. Debug and develop during market closure")
    else:
        print(f"{RED}❌ Some critical checks failed{NC}")
        print()
        print("Please:")
        print("  1. Run data collection: python3 scripts/collect_historical_data.py --months 3")
        print("  2. Check logs for errors")
        print("  3. Verify API keys are set")
    
    print()
    
    # Exit code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
