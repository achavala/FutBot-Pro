"""Delta hedging timeline logger for validation and debugging."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class HedgeTimelineEntry:
    """Single entry in delta hedging timeline."""
    
    timestamp: datetime
    bar: int
    price: float
    net_options_delta: float
    hedge_shares: float
    total_delta: float  # net_options_delta + hedge_shares (normalized)
    options_pnl: float
    hedge_unrealized_pnl: float
    hedge_realized_pnl: float
    total_pnl: float
    hedge_count: int
    notes: str = ""


class DeltaHedgeTimelineLogger:
    """
    Logs delta hedging timeline for validation and debugging.
    
    Creates a table-like log of:
    - time, price, net_options_delta, hedge_shares, total_delta
    - options_pnl, hedge_pnl, total_pnl
    
    Useful for validating hedge behavior in scenarios G-H1 through G-H4.
    """
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.timelines: Dict[str, List[HedgeTimelineEntry]] = {}  # key: multi_leg_id
    
    def log_entry(
        self,
        multi_leg_id: str,
        bar: int,
        price: float,
        net_options_delta: float,
        hedge_shares: float,
        options_pnl: float,
        hedge_unrealized_pnl: float,
        hedge_realized_pnl: float,
        notes: str = "",
    ) -> None:
        """Log a timeline entry for a position."""
        if not self.enabled:
            return
        
        if multi_leg_id not in self.timelines:
            self.timelines[multi_leg_id] = []
        
        # Calculate total delta (normalized: options delta + hedge shares / 100)
        # hedge_shares already accounts for contract multiplier, so normalize back
        total_delta = net_options_delta + (hedge_shares / 100.0)
        total_pnl = options_pnl + hedge_unrealized_pnl + hedge_realized_pnl
        
        # Get hedge count from manager (if available)
        hedge_count = len(self.timelines[multi_leg_id])
        
        entry = HedgeTimelineEntry(
            timestamp=datetime.now(),
            bar=bar,
            price=price,
            net_options_delta=net_options_delta,
            hedge_shares=hedge_shares,
            total_delta=total_delta,
            options_pnl=options_pnl,
            hedge_unrealized_pnl=hedge_unrealized_pnl,
            hedge_realized_pnl=hedge_realized_pnl,
            total_pnl=total_pnl,
            hedge_count=hedge_count,
            notes=notes,
        )
        
        self.timelines[multi_leg_id].append(entry)
        
        # Log formatted entry
        logger.debug(
            f"📊 [HedgeTimeline] {multi_leg_id} | "
            f"bar={bar:4d} | price=${price:7.2f} | "
            f"opt_delta={net_options_delta:+6.3f} | hedge={hedge_shares:+7.2f} | "
            f"total_delta={total_delta:+6.3f} | "
            f"opt_pnl=${options_pnl:+7.2f} | hedge_pnl=${hedge_unrealized_pnl:+7.2f} | "
            f"total_pnl=${total_pnl:+7.2f} | {notes}"
        )
    
    def get_timeline(self, multi_leg_id: str) -> List[HedgeTimelineEntry]:
        """Get timeline for a position."""
        return self.timelines.get(multi_leg_id, [])
    
    def export_timeline_table(self, multi_leg_id: str) -> str:
        """
        Export timeline as formatted table (for validation reports).
        
        Returns:
            Formatted table string
        """
        entries = self.get_timeline(multi_leg_id)
        if not entries:
            return f"No timeline entries for {multi_leg_id}"
        
        # Header
        lines = [
            f"\n{'='*120}",
            f"Delta Hedging Timeline: {multi_leg_id}",
            f"{'='*120}",
            f"{'Bar':<6} {'Price':<8} {'OptDelta':<10} {'Hedge':<8} {'TotDelta':<10} "
            f"{'OptP&L':<10} {'HedgeP&L':<10} {'TotP&L':<10} {'Notes':<20}",
            f"{'-'*120}",
        ]
        
        # Entries
        for entry in entries:
            lines.append(
                f"{entry.bar:<6} ${entry.price:<7.2f} {entry.net_options_delta:+9.3f} "
                f"{entry.hedge_shares:+7.2f} {entry.total_delta:+9.3f} "
                f"${entry.options_pnl:+9.2f} ${entry.hedge_unrealized_pnl:+9.2f} "
                f"${entry.total_pnl:+9.2f} {entry.notes:<20}"
            )
        
        lines.append(f"{'='*120}\n")
        
        return "\n".join(lines)
    
    def export_all_timelines(self) -> str:
        """Export all timelines."""
        if not self.timelines:
            return "No timelines recorded"
        
        lines = []
        for multi_leg_id in self.timelines:
            lines.append(self.export_timeline_table(multi_leg_id))
        
        return "\n".join(lines)
    
    def clear_timeline(self, multi_leg_id: str) -> None:
        """Clear timeline for a position."""
        if multi_leg_id in self.timelines:
            del self.timelines[multi_leg_id]
    
    def clear_all(self) -> None:
        """Clear all timelines."""
        self.timelines.clear()

