#!/usr/bin/env python3
"""
Clean up holiday data from cache database.
Removes bars stored for known market holidays (markets were closed).
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, date, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.cache import BarCache
from core.settings_loader import load_settings
import sqlite3

def get_known_holidays(start_year: int, end_year: int) -> set:
    """Get known market holidays."""
    holidays = set()
    
    for year in range(start_year, end_year + 1):
        # New Year's Day
        jan_1 = date(year, 1, 1)
        if jan_1.weekday() == 5:  # Saturday
            holidays.add((jan_1 + timedelta(days=2)).strftime("%Y-%m-%d"))
        elif jan_1.weekday() == 6:  # Sunday
            holidays.add((jan_1 + timedelta(days=1)).strftime("%Y-%m-%d"))
        else:
            holidays.add(jan_1.strftime("%Y-%m-%d"))
        
        # MLK Day (3rd Monday in January)
        jan_1 = date(year, 1, 1)
        days_until_monday = (0 - jan_1.weekday()) % 7
        first_monday = jan_1 + timedelta(days=days_until_monday)
        mlk_day = first_monday + timedelta(days=14)
        holidays.add(mlk_day.strftime("%Y-%m-%d"))
        
        # Presidents Day (3rd Monday in February)
        feb_1 = date(year, 2, 1)
        days_until_monday = (0 - feb_1.weekday()) % 7
        first_monday = feb_1 + timedelta(days=days_until_monday)
        presidents_day = first_monday + timedelta(days=14)
        holidays.add(presidents_day.strftime("%Y-%m-%d"))
        
        # Memorial Day (last Monday in May)
        may_31 = date(year, 5, 31)
        days_until_monday = (0 - may_31.weekday()) % 7
        memorial_day = may_31 - timedelta(days=days_until_monday)
        holidays.add(memorial_day.strftime("%Y-%m-%d"))
        
        # Juneteenth (June 19)
        jun_19 = date(year, 6, 19)
        if jun_19.weekday() == 5:  # Saturday
            holidays.add((jun_19 - timedelta(days=1)).strftime("%Y-%m-%d"))
        elif jun_19.weekday() == 6:  # Sunday
            holidays.add((jun_19 + timedelta(days=1)).strftime("%Y-%m-%d"))
        else:
            holidays.add(jun_19.strftime("%Y-%m-%d"))
        
        # Independence Day (July 4)
        jul_4 = date(year, 7, 4)
        if jul_4.weekday() == 5:  # Saturday
            holidays.add((jul_4 - timedelta(days=1)).strftime("%Y-%m-%d"))
        elif jul_4.weekday() == 6:  # Sunday
            holidays.add((jul_4 + timedelta(days=1)).strftime("%Y-%m-%d"))
        else:
            holidays.add(jul_4.strftime("%Y-%m-%d"))
        
        # Labor Day (1st Monday in September)
        sep_1 = date(year, 9, 1)
        days_until_monday = (0 - sep_1.weekday()) % 7
        labor_day = sep_1 + timedelta(days=days_until_monday)
        holidays.add(labor_day.strftime("%Y-%m-%d"))
        
        # Thanksgiving (4th Thursday in November)
        nov_1 = date(year, 11, 1)
        days_until_thursday = (3 - nov_1.weekday()) % 7
        first_thursday = nov_1 + timedelta(days=days_until_thursday)
        thanksgiving = first_thursday + timedelta(days=21)
        holidays.add(thanksgiving.strftime("%Y-%m-%d"))
        
        # Day After Thanksgiving
        day_after = thanksgiving + timedelta(days=1)
        holidays.add(day_after.strftime("%Y-%m-%d"))
        
        # Christmas (Dec 25)
        dec_25 = date(year, 12, 25)
        if dec_25.weekday() == 5:  # Saturday
            holidays.add((dec_25 - timedelta(days=1)).strftime("%Y-%m-%d"))
        elif dec_25.weekday() == 6:  # Sunday
            holidays.add((dec_25 + timedelta(days=1)).strftime("%Y-%m-%d"))
        else:
            holidays.add(dec_25.strftime("%Y-%m-%d"))
    
    return holidays

def cleanup_holiday_data(dry_run: bool = True):
    """Remove bars stored for market holidays."""
    settings = load_settings()
    cache_path = Path(settings.data.cache.path)
    
    if not cache_path.exists():
        print(f"❌ Cache file not found: {cache_path}")
        return
    
    print(f"📊 Analyzing cache: {cache_path}")
    
    # Get all unique dates in cache
    with sqlite3.connect(cache_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT DATE(datetime(ts/1000, 'unixepoch', 'localtime')) as date_str
            FROM polygon_bars
            ORDER BY date_str
        """)
        dates_in_cache = {row[0] for row in cursor.fetchall()}
    
    print(f"📅 Found {len(dates_in_cache)} unique dates in cache")
    
    # Get date range
    if dates_in_cache:
        min_year = min(int(d.split('-')[0]) for d in dates_in_cache)
        max_year = max(int(d.split('-')[0]) for d in dates_in_cache)
        holidays = get_known_holidays(min_year, max_year)
        
        print(f"🎄 Found {len(holidays)} known market holidays in range {min_year}-{max_year}")
        
        # Find holiday dates that exist in cache
        holiday_dates_in_cache = dates_in_cache.intersection(holidays)
        
        if holiday_dates_in_cache:
            print(f"\n⚠️  Found {len(holiday_dates_in_cache)} holiday dates with data in cache:")
            for holiday_date in sorted(holiday_dates_in_cache):
                # Count bars for this date
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM polygon_bars 
                    WHERE DATE(datetime(ts/1000, 'unixepoch', 'localtime')) = ?
                """, (holiday_date,))
                count = cursor.fetchone()[0]
                print(f"   - {holiday_date}: {count} bars (MARKET WAS CLOSED)")
            
            if not dry_run:
                print(f"\n🗑️  Removing holiday data...")
                total_removed = 0
                for holiday_date in holiday_dates_in_cache:
                    # Convert date to timestamp range
                    date_obj = datetime.strptime(holiday_date, "%Y-%m-%d")
                    start_ts = int(date_obj.replace(hour=0, minute=0, second=0).timestamp() * 1000)
                    end_ts = int((date_obj + timedelta(days=1)).replace(hour=0, minute=0, second=0).timestamp() * 1000)
                    
                    cursor.execute("""
                        DELETE FROM polygon_bars
                        WHERE ts >= ? AND ts < ?
                    """, (start_ts, end_ts))
                    removed = cursor.rowcount
                    total_removed += removed
                    print(f"   ✅ Removed {removed} bars for {holiday_date}")
                
                conn.commit()
                print(f"\n✅ Total removed: {total_removed} bars")
                print(f"✅ Cache cleaned!")
            else:
                print(f"\n💡 This was a DRY RUN. To actually remove, run with --execute flag")
        else:
            print(f"\n✅ No holiday data found in cache - all good!")
    else:
        print("⚠️  No dates found in cache")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Clean up holiday data from cache")
    parser.add_argument("--execute", action="store_true", help="Actually remove data (default is dry-run)")
    args = parser.parse_args()
    
    cleanup_holiday_data(dry_run=not args.execute)


