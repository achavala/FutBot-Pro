#!/usr/bin/env python3
"""Export delta hedging timeline tables for validation."""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.live.delta_hedge_logger import DeltaHedgeTimelineLogger


def export_timelines_from_live_loop(live_loop, output_dir: Path, run_id: Optional[str] = None):
    """
    Export all timeline tables from a live trading loop.
    
    Args:
        live_loop: LiveTradingLoop instance with hedge_timeline_logger
        output_dir: Base directory to save timeline files
        run_id: Optional run ID to organize exports (e.g., "2024-12-01_SPY")
    """
    # Create run-specific subdirectory if run_id provided
    if run_id:
        output_dir = output_dir / run_id
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not hasattr(live_loop, 'hedge_timeline_logger'):
        print("⚠️ No hedge timeline logger found in live loop")
        return
    
    timeline_logger = live_loop.hedge_timeline_logger
    
    # Get all multi-leg positions
    if hasattr(live_loop, 'options_portfolio'):
        multi_leg_positions = live_loop.options_portfolio.get_all_multi_leg_positions()
    else:
        multi_leg_positions = []
    
    exported_count = 0
    
    if not multi_leg_positions:
        print(f"⚠️ No multi-leg positions found to export")
        return 0
    
    for ml_pos in multi_leg_positions:
        multi_leg_id = ml_pos.multi_leg_id
        
        # Export timeline table
        timeline_table = timeline_logger.export_timeline_table(multi_leg_id)
        
        if timeline_table and "No timeline entries" not in timeline_table:
            # Save timeline table
            timeline_file = output_dir / f"{multi_leg_id}_timeline.txt"
            with open(timeline_file, "w") as f:
                f.write(timeline_table)
            
            # Get final metrics
            hedge_pos = live_loop.delta_hedge_manager.get_hedge_position(multi_leg_id) if hasattr(live_loop, 'delta_hedge_manager') else None
            
            metrics = {
                "multi_leg_id": multi_leg_id,
                "symbol": ml_pos.symbol,
                "trade_type": ml_pos.trade_type,
                "direction": ml_pos.direction,
                "entry_time": ml_pos.entry_time.isoformat() if hasattr(ml_pos, 'entry_time') else None,
                "final_options_pnl": ml_pos.combined_unrealized_pnl,
                "final_hedge_realized_pnl": hedge_pos.hedge_realized_pnl if hedge_pos else 0.0,
                "final_hedge_unrealized_pnl": hedge_pos.hedge_unrealized_pnl if hedge_pos else 0.0,
                "final_total_pnl": ml_pos.combined_unrealized_pnl + (hedge_pos.hedge_realized_pnl + hedge_pos.hedge_unrealized_pnl if hedge_pos else 0.0),
                "hedge_shares": hedge_pos.hedge_shares if hedge_pos else 0.0,
                "hedge_count": hedge_pos.hedge_count if hedge_pos else 0,
                "total_shares_traded": hedge_pos.total_shares_traded if hedge_pos else 0.0,
            }
            
            # Save metrics JSON
            metrics_file = output_dir / f"{multi_leg_id}_metrics.json"
            with open(metrics_file, "w") as f:
                json.dump(metrics, f, indent=2)
            
            print(f"✅ Exported timeline for {multi_leg_id}")
            print(f"   Timeline: {timeline_file}")
            print(f"   Metrics: {metrics_file}")
            exported_count += 1
    
    # Export all timelines summary
    all_timelines = timeline_logger.export_all_timelines()
    if all_timelines and "No timelines" not in all_timelines:
        summary_file = output_dir / "all_timelines_summary.txt"
        with open(summary_file, "w") as f:
            f.write(all_timelines)
        print(f"✅ Exported all timelines summary: {summary_file}")
    
    # Export run metadata
    run_metadata = {
        "run_id": run_id or "default",
        "export_timestamp": datetime.now().isoformat(),
        "exported_count": exported_count,
        "multi_leg_ids": [ml_pos.multi_leg_id for ml_pos in multi_leg_positions],
    }
    metadata_file = output_dir / "run_metadata.json"
    with open(metadata_file, "w") as f:
        json.dump(run_metadata, f, indent=2)
    print(f"✅ Exported run metadata: {metadata_file}")
    
    print(f"\n📊 Exported {exported_count} timeline(s) to {output_dir}")
    return exported_count


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Export delta hedging timeline tables")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="phase1_results/gamma_only",
        help="Output directory for timeline files",
    )
    parser.add_argument(
        "--from-api",
        action="store_true",
        help="Fetch from running API server instead of live loop",
    )
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if args.from_api:
        # TODO: Fetch from API endpoint
        print("⚠️ API export not yet implemented")
        print("   Use --from-api=false and pass live_loop instance")
        return
    
    print("="*80)
    print("DELTA HEDGING TIMELINE EXPORT")
    print("="*80)
    print(f"Output directory: {output_dir}")
    print("")
    print("Usage:")
    print("  from code:")
    print("    from scripts.export_hedge_timelines import export_timelines_from_live_loop")
    print("    export_timelines_from_live_loop(live_loop, Path('phase1_results/gamma_only'))")
    print("")
    print("  or call this script after simulation completes")
    print("="*80)


if __name__ == "__main__":
    main()

