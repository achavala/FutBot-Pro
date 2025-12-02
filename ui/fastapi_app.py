from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from contextlib import asynccontextmanager
from typing import List, Optional

from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response, FileResponse, JSONResponse
from pydantic import BaseModel
import json
import yaml

# Load environment variables from .env file
load_dotenv()

# Don't start IBKR loop at import time - it conflicts with uvicorn's uvloop
# IBKR loop will be started lazily only when IBKRBrokerClient is actually used
# This allows uvicorn to use uvloop without conflicts

import logging

from ui.bot_manager import BotManager
from ui.metrics import generate_json_metrics, generate_prometheus_metrics

logger = logging.getLogger(__name__)
from ui.visualizations import (
    create_interactive_dashboard,
    plot_agent_fitness_evolution,
    plot_drawdown,
    plot_equity_curve,
    plot_regime_distribution,
    plot_volatility_pnl_heatmap,
    plot_weight_evolution,
    render_options_equity_curve,
    render_options_drawdown,
    render_options_pnl_by_symbol,
    render_options_vs_stock_equity,
)


class StartRequest(BaseModel):
    """Request to start the bot."""

    pass


class PauseRequest(BaseModel):
    """Request to pause/resume the bot."""

    pass


class KillSwitchRequest(BaseModel):
    """Request to engage/disengage kill switch."""

    engage: bool = True


class BacktestRequest(BaseModel):
    """Request to run a backtest."""

    symbol: str = "QQQ"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = 100000.0


class HealthResponse(BaseModel):
    """Health status response."""

    status: str
    is_running: bool
    is_paused: bool
    bar_count: int
    last_update: Optional[str]
    error: Optional[str]
    risk_status: Dict
    portfolio_healthy: bool


class RegimeResponse(BaseModel):
    """Current regime response."""

    regime_type: str
    trend_direction: str
    volatility_level: str
    bias: str
    confidence: float
    is_valid: bool
    active_fvg: Optional[Dict] = None


class StatsResponse(BaseModel):
    """Portfolio statistics response."""

    initial_capital: float
    current_capital: float
    total_value: float
    total_return_pct: float
    max_drawdown: float
    win_rate: float
    sharpe_ratio: float
    total_trades: int
    open_positions: int


class AgentResponse(BaseModel):
    """Agent state response."""

    agents: Dict[str, Dict[str, float]]


class TradeLogResponse(BaseModel):
    """Trade log response."""

    trades: List[Dict]
    total_count: int


# Global bot manager instance (will be initialized lazily on first request)
bot_manager: Optional[BotManager] = None
data_collector = None  # Will be initialized if needed

def _initialize_bot_manager() -> BotManager:
    """Lazy initialization of bot manager (prevents startup freeze)."""
    global bot_manager
    if bot_manager is not None:
        return bot_manager
    
    try:
        from core.agents.fvg_agent import FVGAgent
        from core.agents.mean_reversion_agent import MeanReversionAgent
        from core.agents.trend_agent import TrendAgent
        from core.agents.volatility_agent import VolatilityAgent
        from core.settings_loader import load_settings
        from core.policy.controller import MetaPolicyController
        from core.policy_adaptation.adaptor import PolicyAdaptor
        from core.portfolio.manager import PortfolioManager
        from core.regime.engine import RegimeEngine
        from core.reward.memory import RollingMemoryStore
        from core.reward.tracker import RewardTracker
        from core.risk.advanced import AdvancedRiskConfig, AdvancedRiskManager
        from core.risk.manager import RiskConfig, RiskManager
        
        symbol = "QQQ"
        initial_capital = 100000.0
        
        # Initialize components
        regime_engine = RegimeEngine()
        controller = MetaPolicyController()
        
        # Initialize options data feed for real options trading
        options_data_feed = None
        try:
            import os
            from services.options_data_feed import OptionsDataFeed
            
            # Try Alpaca first, then Polygon
            alpaca_key = os.getenv("ALPACA_API_KEY")
            alpaca_secret = os.getenv("ALPACA_API_SECRET")
            polygon_key = os.getenv("POLYGON_API_KEY") or os.getenv("MASSIVE_API_KEY")
            
            if alpaca_key and alpaca_secret:
                options_data_feed = OptionsDataFeed(
                    api_provider="alpaca",
                    api_key=alpaca_key,
                    api_secret=alpaca_secret,
                )
                logger.info("✅ Options data feed initialized (Alpaca)")
            elif polygon_key:
                options_data_feed = OptionsDataFeed(
                    api_provider="polygon",
                    api_key=polygon_key,
                )
                logger.info("✅ Options data feed initialized (Polygon)")
            else:
                logger.warning("⚠️ No options API credentials found - options agent will use synthetic pricing")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize options data feed: {e} - options agent will use synthetic pricing")
        
        # Create base agents
        base_agents = [
            TrendAgent(symbol=symbol),
            MeanReversionAgent(symbol=symbol),
            VolatilityAgent(symbol=symbol),
            FVGAgent(symbol=symbol),
        ]
        
        # Add options agent with real data feed if available
        from core.agents.options_agent import OptionsAgent
        from core.config.asset_profiles import OptionRiskProfile
        
        # PERFORMANCE: Enable testing_mode for 0DTE trading and lower thresholds
        option_risk_profile = OptionRiskProfile(
            testing_mode=True,  # Enable aggressive 0DTE trading
            min_dte_for_entry=0,  # Allow 0DTE
            max_dte_for_entry=45,
            min_iv_percentile=0.0,  # No IV filter in testing mode
            max_iv_percentile=100.0,
            max_spread_pct=20.0,  # More lenient spread
            min_open_interest=10,  # Lower OI requirement
            min_volume=1,  # Lower volume requirement
        )
        options_agent = OptionsAgent(
            symbol=symbol,
            options_data_feed=options_data_feed,  # Real options data feed
            option_risk_profile=option_risk_profile,
            config={"min_confidence": 0.30},  # Lower confidence threshold for more trades
        )
        
        agents = base_agents + [options_agent]
        logger.info(f"✅ Created {len(agents)} agents (including options agent with {'real' if options_data_feed else 'synthetic'} data)")
        
        portfolio = PortfolioManager(initial_capital=initial_capital, symbol=symbol)
        risk_manager = RiskManager(initial_capital=initial_capital)
        advanced_risk = AdvancedRiskManager(initial_capital=initial_capital)
        
        # Reward and adaptation
        memory_store = RollingMemoryStore()
        reward_tracker = RewardTracker(memory_store=memory_store)
        adaptor = PolicyAdaptor(memory_store=memory_store)
        
        # Update controller with adaptor
        controller = MetaPolicyController(adaptor=adaptor)
        
        # Create bot manager
        bot_manager = BotManager(
            agents=agents,
            regime_engine=regime_engine,
            controller=controller,
            portfolio=portfolio,
            risk_manager=risk_manager,
            reward_tracker=reward_tracker,
            adaptor=adaptor,
            advanced_risk_manager=advanced_risk,
        )
        
        logger.info("✅ Bot manager initialized (lazy initialization)")
        return bot_manager
    except Exception as e:
        logger.error(f"❌ Failed to initialize bot manager: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to initialize bot manager: {str(e)}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup - LAZY INITIALIZATION (don't initialize BotManager here to prevent startup freeze)
    global bot_manager
    
    # DO NOT initialize bot_manager here - it will be initialized lazily on first request
    # This prevents the server from freezing during startup
    logger.info("✅ Server started (lazy initialization enabled)")
    
    yield
    # Shutdown (if needed)
    if bot_manager:
        logger.info("Shutting down bot manager...")


app = FastAPI(
    title="FutBot Trading System API",
    description="Control panel and monitoring API for the regime-aware trading bot",
    version="1.0.0",
    lifespan=lifespan,
)

# Add version endpoint to confirm server is running new code
@app.get("/version")
async def get_version():
    """Get server version and build info."""
    return {
        "version": "1.0.0",
        "build_date": "2024-11-28",
        "features": [
            "synthetic_bar_fallback",
            "bars_per_symbol_preload_fix",
            "testing_mode",
            "aggressive_logging",
            "symbol_case_normalization"
        ],
        "status": "ready"
    }


def set_bot_manager(manager: BotManager) -> None:
    """Set the bot manager instance."""
    global bot_manager
    bot_manager = manager


@app.get("/")
async def root():
    """Root endpoint - serves Webull-style dashboard."""
    from pathlib import Path
    # Try Webull dashboard first, then modern, then fallback
    webull_dashboard = Path(__file__).parent / "dashboard_webull.html"
    modern_dashboard = Path(__file__).parent / "dashboard_modern.html"
    dashboard_path = Path(__file__).parent / "dashboard.html"
    
    # Add cache-busting headers to prevent browser caching
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }
    
    if webull_dashboard.exists():
        html_content = webull_dashboard.read_text(encoding='utf-8')
        return HTMLResponse(content=html_content, media_type="text/html", headers=headers)
    elif modern_dashboard.exists():
        html_content = modern_dashboard.read_text(encoding='utf-8')
        return HTMLResponse(content=html_content, media_type="text/html", headers=headers)
    elif dashboard_path.exists():
        html_content = dashboard_path.read_text(encoding='utf-8')
        return HTMLResponse(content=html_content, media_type="text/html", headers=headers)
    
    # Fallback: return simple HTML redirect message
    return HTMLResponse(
        content="""
    <html>
        <head><title>FutBot Dashboard</title></head>
        <body>
            <h1>FutBot Trading System</h1>
            <p>Dashboard file not found. Please check that ui/dashboard_webull.html exists.</p>
            <p><a href="/docs">API Documentation</a></p>
        </body>
    </html>
    """,
        media_type="text/html"
    )


@app.get("/manifest.json")
async def get_manifest():
    """Serve PWA manifest.json."""
    from pathlib import Path
    manifest_path = Path(__file__).parent / "manifest.json"
    if manifest_path.exists():
        manifest_content = manifest_path.read_text(encoding='utf-8')
        return JSONResponse(content=json.loads(manifest_content))
    else:
        raise HTTPException(status_code=404, detail="Manifest not found")


@app.get("/service-worker.js")
async def get_service_worker():
    """Serve PWA service worker."""
    from pathlib import Path
    sw_path = Path(__file__).parent / "service-worker.js"
    if sw_path.exists():
        sw_content = sw_path.read_text(encoding='utf-8')
        return Response(content=sw_content, media_type="application/javascript")
    else:
        raise HTTPException(status_code=404, detail="Service worker not found")


@app.get("/dashboard")
async def dashboard(v: Optional[str] = None):
    """Serve the dashboard HTML with cache-busting."""
    from pathlib import Path
    from datetime import datetime
    # Try modern dashboard first (has latest features), then webull, then fallback
    modern_dashboard = Path(__file__).parent / "dashboard_modern.html"
    webull_dashboard = Path(__file__).parent / "dashboard_webull.html"
    dashboard_path = Path(__file__).parent / "dashboard.html"
    
    # Add cache-busting headers to prevent browser caching
    # Also add timestamp to force fresh load
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
        "Last-Modified": datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT"),
        "ETag": f'"{timestamp}"'
    }
    
    if modern_dashboard.exists():
        html_content = modern_dashboard.read_text(encoding='utf-8')
        # Inject cache-busting script if not already present
        if 'caches.keys()' not in html_content:
            cache_script = '''<script>
        if ('caches' in window) {
            caches.keys().then(function(names) {
                for (let name of names) caches.delete(name);
            });
        }
        window.addEventListener('pageshow', function(e) {
            if (e.persisted) window.location.reload();
        });
    </script>'''
            html_content = html_content.replace('</head>', cache_script + '</head>', 1)
        return HTMLResponse(content=html_content, media_type="text/html", headers=headers)
    elif webull_dashboard.exists():
        html_content = webull_dashboard.read_text(encoding='utf-8')
        return HTMLResponse(content=html_content, media_type="text/html", headers=headers)
    elif dashboard_path.exists():
        html_content = dashboard_path.read_text(encoding='utf-8')
        return HTMLResponse(content=html_content, media_type="text/html", headers=headers)
    raise HTTPException(status_code=404, detail="Dashboard not found")


# Cache for health endpoint to prevent repeated heavy calculations
_health_cache = {"data": None, "timestamp": 0, "ttl": 2.0}  # 2 second cache

@app.get("/health", response_model=HealthResponse)
async def get_health():
    """Get bot health status (cached for 2 seconds to prevent blocking)."""
    import time
    current_time = time.time()
    
    # Return cached data if still valid
    if (_health_cache["data"] and 
        (current_time - _health_cache["timestamp"]) < _health_cache["ttl"]):
        return HealthResponse(**_health_cache["data"])
    
    # Lazy initialization - initialize bot_manager on first request
    if not bot_manager:
        _initialize_bot_manager()
    
    try:
        health = bot_manager.get_health_status()
        status = "healthy" if health["is_running"] and not health.get("error") else "unhealthy"
        result = {"status": status, **health}
        
        # Update cache
        _health_cache["data"] = result
        _health_cache["timestamp"] = current_time
        
        return HealthResponse(**result)
    except Exception as e:
        logger.error(f"Error getting health status: {e}", exc_info=True)
        # Return cached data if available, otherwise return error response
        if _health_cache["data"]:
            return HealthResponse(**_health_cache["data"])
        return HealthResponse(
            status="unhealthy",
            is_running=False,
            is_paused=False,
            bar_count=0,
            last_update=None,
            error=str(e),
            risk_status={},
            portfolio_healthy=False,
        )


@app.get("/regime", response_model=RegimeResponse)
async def get_regime():
    """Get current regime classification."""
    try:
        if not bot_manager:
            # Return default regime instead of error
            from core.regime.types import RegimeType, TrendDirection, VolatilityLevel, Bias
            return RegimeResponse(
                regime_type=RegimeType.COMPRESSION.value,
                trend_direction=TrendDirection.SIDEWAYS.value,
                volatility_level=VolatilityLevel.LOW.value,
                bias=Bias.NEUTRAL.value,
                confidence=0.0,
                is_valid=False,
                active_fvg=None,
            )
        regime = bot_manager.get_current_regime()
        if not regime:
            # Return a default/empty regime instead of 404 when no data is available yet
            from core.regime.types import RegimeType, TrendDirection, VolatilityLevel, Bias
            return RegimeResponse(
                regime_type=RegimeType.COMPRESSION.value,
                trend_direction=TrendDirection.SIDEWAYS.value,
                volatility_level=VolatilityLevel.LOW.value,
                bias=Bias.NEUTRAL.value,
                confidence=0.0,
                is_valid=False,
                active_fvg=None,
            )
        return RegimeResponse(
            regime_type=regime.regime_type.value,
            trend_direction=regime.trend_direction.value,
            volatility_level=regime.volatility_level.value,
            bias=regime.bias.value,
            confidence=regime.confidence,
            is_valid=regime.is_valid,
            active_fvg={
                "gap_type": regime.active_fvg.gap_type,
                "upper": regime.active_fvg.upper,
                "lower": regime.active_fvg.lower,
            }
            if regime.active_fvg
            else None,
        )
    except Exception as e:
        # Catch any errors and return default regime
        logger.error(f"Error getting regime: {e}", exc_info=True)
        from core.regime.types import RegimeType, TrendDirection, VolatilityLevel, Bias
        return RegimeResponse(
            regime_type=RegimeType.COMPRESSION.value,
            trend_direction=TrendDirection.SIDEWAYS.value,
            volatility_level=VolatilityLevel.LOW.value,
            bias=Bias.NEUTRAL.value,
            confidence=0.0,
            is_valid=False,
            active_fvg=None,
        )


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get portfolio performance statistics."""
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    stats = bot_manager.get_portfolio_stats()
    return StatsResponse(**stats)


@app.get("/agents", response_model=AgentResponse)
async def get_agents():
    """Get agent states and fitness metrics."""
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    agents = bot_manager.get_agent_fitness()
    return AgentResponse(agents=agents)


@app.get("/trade-log", response_model=TradeLogResponse)
async def get_trade_log(limit: int = 50):
    """Get recent trade log."""
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    trades = bot_manager.get_recent_trades(limit)
    
    # CRITICAL FIX: Convert timestamps to EST for display
    try:
        from zoneinfo import ZoneInfo
        est = ZoneInfo('America/New_York')
    except ImportError:
        import pytz
        est = pytz.timezone('America/New_York')
    
    trade_dicts = []
    for t in trades:
        # Convert entry_time to EST
        if t.entry_time.tzinfo is None:
            entry_time_utc = t.entry_time.replace(tzinfo=timezone.utc)
        else:
            entry_time_utc = t.entry_time.astimezone(timezone.utc)
        entry_time_est = entry_time_utc.astimezone(est)
        
        # Convert exit_time to EST
        if t.exit_time.tzinfo is None:
            exit_time_utc = t.exit_time.replace(tzinfo=timezone.utc)
        else:
            exit_time_utc = t.exit_time.astimezone(timezone.utc)
        exit_time_est = exit_time_utc.astimezone(est)
        
        trade_dicts.append({
            "symbol": t.symbol,
            "entry_time": entry_time_est.strftime("%Y-%m-%dT%H:%M:%S%z"),  # EST format
            "exit_time": exit_time_est.strftime("%Y-%m-%dT%H:%M:%S%z"),  # EST format
            "entry_time_est": entry_time_est.strftime("%Y-%m-%d %I:%M:%S %p %Z"),  # Human-readable EST
            "exit_time_est": exit_time_est.strftime("%Y-%m-%d %I:%M:%S %p %Z"),  # Human-readable EST
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "quantity": t.quantity,
            "pnl": t.pnl,
            "pnl_pct": t.pnl_pct,
            "reason": t.reason,
            "agent": t.agent,
        })
    return TradeLogResponse(trades=trade_dicts, total_count=len(trade_dicts))


@app.get("/trades/roundtrips")
async def get_roundtrip_trades(
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
):
    """
    Get round-trip trades with detailed entry/exit information.
    
    Each trade represents a complete round-trip (entry + exit) with:
    - Entry time and price
    - Exit time and price
    - Quantity and direction
    - P&L (gross and percentage)
    - Reason and agent
    
    Query parameters:
    - symbol: Filter by symbol (e.g., "QQQ", "SPY")
    - start_date: Filter from date (ISO format, e.g., "2025-11-26T00:00:00Z")
    - end_date: Filter to date (ISO format)
    - limit: Maximum number of trades to return (default: 100)
    """
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    
    # Parse dates if provided
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid start_date format: {start_date}. Use ISO format.")
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid end_date format: {end_date}. Use ISO format.")
    
    trades = bot_manager.get_roundtrip_trades(
        symbol=symbol,
        start_date=start_dt,
        end_date=end_dt,
        limit=limit
    )
    
    # Format trades with additional calculated fields
    trade_dicts = []
    for t in trades:
        # Calculate duration
        duration = t.exit_time - t.entry_time
        duration_minutes = duration.total_seconds() / 60.0
        
        # Determine direction
        direction = "LONG" if t.quantity > 0 else "SHORT"
        
        # CRITICAL FIX: Convert timestamps to EST and validate trading hours
        from datetime import timezone
        import pytz
        
        est = pytz.timezone('America/New_York')
        
        # Convert entry_time to EST
        if t.entry_time.tzinfo is None:
            entry_time_utc = t.entry_time.replace(tzinfo=timezone.utc)
        else:
            entry_time_utc = t.entry_time.astimezone(timezone.utc)
        entry_time_est = entry_time_utc.astimezone(est)
        
        # Convert exit_time to EST
        if t.exit_time.tzinfo is None:
            exit_time_utc = t.exit_time.replace(tzinfo=timezone.utc)
        else:
            exit_time_utc = t.exit_time.astimezone(timezone.utc)
        exit_time_est = exit_time_utc.astimezone(est)
        
        # Validate trading hours (9:30 AM - 4:00 PM EST)
        entry_hour = entry_time_est.hour
        entry_minute = entry_time_est.minute
        exit_hour = exit_time_est.hour
        exit_minute = exit_time_est.minute
        
        # Check if within market hours
        entry_in_hours = (entry_hour == 9 and entry_minute >= 30) or (9 < entry_hour < 16) or (entry_hour == 16 and exit_minute == 0)
        exit_in_hours = (exit_hour == 9 and exit_minute >= 30) or (9 < exit_hour < 16) or (exit_hour == 16 and exit_minute == 0)
        
        trade_dicts.append({
            "symbol": t.symbol,
            "direction": direction,
            "entry_time": entry_time_est.strftime("%Y-%m-%dT%H:%M:%S%z"),  # EST format
            "exit_time": exit_time_est.strftime("%Y-%m-%dT%H:%M:%S%z"),  # EST format
            "entry_time_est": entry_time_est.strftime("%Y-%m-%d %I:%M:%S %p %Z"),  # Human-readable EST
            "exit_time_est": exit_time_est.strftime("%Y-%m-%d %I:%M:%S %p %Z"),  # Human-readable EST
            "entry_price": round(t.entry_price, 2),
            "exit_price": round(t.exit_price, 2),
            "quantity": abs(round(t.quantity, 6)),
            "gross_pnl": round(t.pnl, 2),
            "pnl_pct": round(t.pnl_pct, 2),
            "duration_minutes": round(duration_minutes, 2),
            "reason": t.reason,
            "agent": t.agent,
            "regime_at_entry": t.regime_at_entry,
            "vol_bucket_at_entry": t.vol_bucket_at_entry,
            "entry_in_trading_hours": entry_in_hours,
            "exit_in_trading_hours": exit_in_hours,
        })
    
    return {
        "trades": trade_dicts,
        "total_count": len(trade_dicts),
        "filters": {
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
        }
    }


@app.get("/trades/options/roundtrips")
async def get_options_roundtrip_trades(
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
):
    """
    Get round-trip options trades with detailed entry/exit information.
    
    Each trade represents a complete options round-trip (entry + exit) with:
    - Entry time and premium
    - Exit time and premium
    - Option type (call/put)
    - Strike and expiration
    - Quantity (contracts)
    - P&L (gross and percentage)
    - Reason and agent
    - Regime & volatility at entry
    
    Query parameters:
    - symbol: Filter by underlying symbol (e.g., "QQQ", "SPY")
    - start_date: Filter from date (ISO format, e.g., "2025-11-26T00:00:00Z")
    - end_date: Filter to date (ISO format)
    - limit: Maximum number of trades to return (default: 100)
    """
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    
    # Parse dates if provided
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid start_date format: {start_date}. Use ISO format.")
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid end_date format: {end_date}. Use ISO format.")
    
    trades = bot_manager.get_options_roundtrip_trades(
        symbol=symbol,
        start_date=start_dt,
        end_date=end_dt,
        limit=limit
    )


@app.get("/trades/options/multi-leg")
async def get_multi_leg_trades(
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
):
    """
    Get completed multi-leg options trades (straddles and strangles).
    
    Returns trades with combined P&L across both legs.
    """
    if not bot_manager or not bot_manager.live_loop:
        return {"trades": []}
    
    if not hasattr(bot_manager.live_loop, 'options_portfolio'):
        return {"trades": []}
    
    # Parse dates if provided
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid start_date format: {start_date}")
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid end_date format: {end_date}")
    
    portfolio = bot_manager.live_loop.options_portfolio
    all_trades = portfolio.multi_leg_trades
    
    # Filter
    if symbol:
        all_trades = [t for t in all_trades if t.symbol == symbol]
    if start_dt:
        all_trades = [t for t in all_trades if t.entry_time >= start_dt]
    if end_dt:
        all_trades = [t for t in all_trades if t.exit_time <= end_dt]
    
    # Sort by exit time (most recent first)
    all_trades.sort(key=lambda t: t.exit_time, reverse=True)
    trades = all_trades[:limit]
    
    return {
        "trades": [
            {
                "multi_leg_id": trade.multi_leg_id,
                "symbol": trade.symbol,
                "trade_type": trade.trade_type,
                "direction": trade.direction,
                "call_strike": trade.call_strike,
                "put_strike": trade.put_strike,
                "call_quantity": trade.call_quantity,
                "put_quantity": trade.put_quantity,
                "call_entry_price": trade.call_entry_price,
                "put_entry_price": trade.put_entry_price,
                "call_exit_price": trade.call_exit_price,
                "put_exit_price": trade.put_exit_price,
                "entry_time": trade.entry_time.isoformat(),
                "exit_time": trade.exit_time.isoformat(),
                "combined_pnl": trade.combined_pnl,
                "combined_pnl_pct": trade.combined_pnl_pct,
                "net_premium": trade.net_premium,
                "duration_minutes": trade.duration_minutes,
                "reason": trade.reason,
                "agent": trade.agent,
            }
            for trade in trades
        ],
        "total_count": len(trades),
    }
    
    # Format trades with additional calculated fields
    trade_dicts = []
    for t in trades:
        trade_dicts.append({
            "symbol": t.symbol,
            "option_symbol": t.option_symbol,
            "option_type": t.option_type,
            "strike": round(t.strike, 2),
            "expiration": t.expiration.isoformat(),
            "quantity": round(t.quantity, 4),  # Number of contracts
            "entry_time": t.entry_time.isoformat(),
            "exit_time": t.exit_time.isoformat(),
            "entry_price": round(t.entry_price, 4),  # Premium per contract
            "exit_price": round(t.exit_price, 4),
            "gross_pnl": round(t.pnl, 2),
            "pnl_pct": round(t.pnl_pct, 2),
            "duration_minutes": round(t.duration_minutes, 2),
            "reason": t.reason,
            "agent": t.agent,
            "delta_at_entry": round(t.delta_at_entry, 4),
            "iv_at_entry": round(t.iv_at_entry, 4),
            "regime_at_entry": t.regime_at_entry,
            "vol_bucket_at_entry": t.vol_bucket_at_entry,
        })
    
    return {
        "trades": trade_dicts,
        "total_count": len(trade_dicts),
        "filters": {
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
        }
    }


@app.get("/regime-performance")
async def get_regime_performance():
    """Get performance metrics by regime."""
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    return bot_manager.get_regime_performance()


@app.get("/risk-status")
async def get_risk_status():
    """Get current risk management status."""
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    return bot_manager.get_risk_status()


@app.get("/risk-metrics")
async def get_risk_metrics():
    """Get advanced risk metrics (if advanced risk manager is enabled)."""
    if not bot_manager or not bot_manager.advanced_risk:
        raise HTTPException(status_code=503, detail="Advanced risk manager not available")
    return bot_manager.advanced_risk.get_risk_metrics()


@app.post("/start")
async def start_bot(request: StartRequest):
    """Start the trading bot."""
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    try:
        bot_manager.start()
        return {"status": "started", "message": "Bot started successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/stop")
async def stop_bot():
    """Stop the trading bot."""
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    bot_manager.stop()
    return {"status": "stopped", "message": "Bot stopped successfully"}


@app.post("/pause")
async def pause_bot(request: PauseRequest):
    """Pause the trading bot."""
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    try:
        bot_manager.pause()
        return {"status": "paused", "message": "Bot paused successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/resume")
async def resume_bot(request: PauseRequest):
    """Resume the trading bot."""
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    try:
        bot_manager.resume()
        return {"status": "resumed", "message": "Bot resumed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/kill")
async def kill_switch(request: KillSwitchRequest):
    """Engage or disengage kill switch."""
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    if request.engage:
        bot_manager.engage_kill_switch()
        return {"status": "kill_switch_engaged", "message": "Kill switch engaged"}
    else:
        bot_manager.disengage_kill_switch()
        return {"status": "kill_switch_disengaged", "message": "Kill switch disengaged"}


@app.post("/backtest")
async def run_backtest(request: BacktestRequest):
    """Trigger a backtest run."""
    # This would integrate with the backtesting runner
    # For now, return a placeholder
    return {
        "status": "queued",
        "message": "Backtest queued (implementation pending)",
        "config": request.dict(),
    }


@app.get("/weights")
async def get_weights():
    """Get current adaptive weights."""
    if not bot_manager or not bot_manager.adaptor:
        raise HTTPException(status_code=503, detail="Adaptor not available")
    return {
        "agent_weights": bot_manager.adaptor.agent_weights,
        "regime_weights": {k.value: v for k, v in bot_manager.adaptor.regime_weights.items()},
        "volatility_weights": {k.value: v for k, v in bot_manager.adaptor.volatility_weights.items()},
        "structure_weights": bot_manager.adaptor.structure_weights,
    }


@app.post("/weights/save")
async def save_weights():
    """Save current adaptive weights to config."""
    if not bot_manager or not bot_manager.adaptor:
        raise HTTPException(status_code=503, detail="Adaptor not available")
    bot_manager.adaptor.save_weights()
    return {"status": "saved", "message": "Weights saved successfully"}


@app.get("/visualizations/equity-curve-data")
async def get_equity_curve_data():
    """Get equity curve data as JSON for sparkline generation."""
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    equity_curve = list(bot_manager.portfolio.equity_curve) if bot_manager.portfolio.equity_curve else []
    if not equity_curve:
        return {"equity_curve": [], "initial_capital": bot_manager.portfolio.initial_capital if bot_manager.portfolio else 100000.0}
    return {
        "equity_curve": equity_curve,
        "initial_capital": bot_manager.portfolio.initial_capital
    }


@app.get("/visualizations/equity-curve")
async def get_equity_curve():
    """Get equity curve plot as PNG."""
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    equity_curve = bot_manager.portfolio.equity_curve
    if not equity_curve:
        raise HTTPException(status_code=404, detail="No equity curve data available")
    import base64
    img_base64 = plot_equity_curve(list(equity_curve), bot_manager.portfolio.initial_capital)
    img_bytes = base64.b64decode(img_base64)
    return Response(content=img_bytes, media_type="image/png")


@app.get("/visualizations/drawdown")
async def get_drawdown():
    """Get drawdown chart as PNG."""
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    equity_curve = bot_manager.portfolio.equity_curve
    if not equity_curve:
        raise HTTPException(status_code=404, detail="No equity curve data available")
    import base64
    img_base64 = plot_drawdown(list(equity_curve), bot_manager.portfolio.initial_capital)
    if not img_base64:
        raise HTTPException(status_code=404, detail="No drawdown data available")
    img_bytes = base64.b64decode(img_base64)
    return Response(content=img_bytes, media_type="image/png")


@app.get("/visualizations/agent-fitness")
async def get_agent_fitness_chart():
    """Get agent fitness evolution chart as PNG."""
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    import base64
    img_base64 = plot_agent_fitness_evolution(bot_manager.agent_fitness_history)
    if not img_base64:
        raise HTTPException(status_code=404, detail="No agent fitness data available")
    img_bytes = base64.b64decode(img_base64)
    return Response(content=img_bytes, media_type="image/png")


@app.get("/visualizations/regime-distribution")
async def get_regime_distribution_chart():
    """Get regime distribution pie chart as PNG."""
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    import base64
    regime_counts = bot_manager.get_regime_distribution()
    if not regime_counts:
        raise HTTPException(status_code=404, detail="No regime data available")
    img_base64 = plot_regime_distribution(regime_counts)
    img_bytes = base64.b64decode(img_base64)
    return Response(content=img_bytes, media_type="image/png")


@app.get("/visualizations/weight-evolution")
async def get_weight_evolution_chart():
    """Get adaptive weight evolution chart as PNG."""
    if not bot_manager or not bot_manager.adaptor:
        raise HTTPException(status_code=503, detail="Adaptor not available")
    import base64
    img_base64 = plot_weight_evolution(bot_manager.weight_history)
    if not img_base64:
        raise HTTPException(status_code=404, detail="No weight history data available")
    img_bytes = base64.b64decode(img_base64)
    return Response(content=img_bytes, media_type="image/png")


@app.get("/visualizations/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """Get interactive Plotly dashboard."""
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    equity_curve = list(bot_manager.portfolio.equity_curve) if bot_manager.portfolio.equity_curve else []
    drawdowns = []
    if equity_curve:
        peak = bot_manager.portfolio.initial_capital
        for value in equity_curve:
            if value > peak:
                peak = value
            dd = ((peak - value) / peak) * 100.0 if peak > 0 else 0.0
            drawdowns.append(dd)

    regime_counts = bot_manager.get_regime_distribution()
    html = create_interactive_dashboard(equity_curve, drawdowns, bot_manager.agent_fitness_history, regime_counts)
    return HTMLResponse(content=html)


@app.get("/visualizations/options-equity-curve")
async def get_options_equity_curve():
    """Get options equity curve plot as PNG."""
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    import base64
    equity_history = bot_manager.get_options_equity_history()
    initial_capital = bot_manager.options_initial_capital if bot_manager.options_initial_capital > 0 else 10000.0
    img_base64 = render_options_equity_curve(equity_history, initial_capital)
    img_bytes = base64.b64decode(img_base64)
    return Response(content=img_bytes, media_type="image/png")


@app.get("/visualizations/options-drawdown")
async def get_options_drawdown():
    """Get options drawdown chart as PNG."""
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    import base64
    equity_history = bot_manager.get_options_equity_history()
    initial_capital = bot_manager.options_initial_capital if bot_manager.options_initial_capital > 0 else 10000.0
    img_base64 = render_options_drawdown(equity_history, initial_capital)
    img_bytes = base64.b64decode(img_base64)
    return Response(content=img_bytes, media_type="image/png")


@app.get("/visualizations/options-pnl-by-symbol")
async def get_options_pnl_by_symbol():
    """Get options P&L by symbol bar chart as PNG."""
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    import base64
    pnl_by_symbol = bot_manager.get_options_pnl_by_symbol()
    img_base64 = render_options_pnl_by_symbol(pnl_by_symbol)
    img_bytes = base64.b64decode(img_base64)
    return Response(content=img_bytes, media_type="image/png")


@app.get("/visualizations/options-vs-stock")
async def get_options_vs_stock_equity():
    """Get options vs stock equity comparison chart as PNG."""
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    import base64
    stock_equity_curve = list(bot_manager.portfolio.equity_curve) if bot_manager.portfolio.equity_curve else []
    options_equity_history = bot_manager.get_options_equity_history()
    stock_initial_capital = bot_manager.portfolio.initial_capital
    options_initial_capital = bot_manager.options_initial_capital if bot_manager.options_initial_capital > 0 else 10000.0
    img_base64 = render_options_vs_stock_equity(
        stock_equity_curve, options_equity_history, stock_initial_capital, options_initial_capital
    )
    img_bytes = base64.b64decode(img_base64)
    return Response(content=img_bytes, media_type="image/png")


# Live Trading Endpoints
class LiveStartRequest(BaseModel):
    """Request to start live trading."""
    symbols: List[str] = ["QQQ", "SPY"]  # Default: trade both QQQ and SPY
    broker_type: str = "paper"  # "paper", "alpaca", "ibkr", or "cached" (offline)
    offline_mode: bool = False  # Use cached data instead of live data
    fixed_investment_amount: float = 1000.0  # $1000 per trade
    start_date: Optional[str] = None  # Start from specific date (YYYY-MM-DD) for offline trading, e.g., "2024-01-15"
    start_time: Optional[str] = None  # Start datetime (YYYY-MM-DDTHH:MM:SS) for time-windowed simulation
    end_time: Optional[str] = None  # End datetime (YYYY-MM-DDTHH:MM:SS) for time-windowed simulation
    replay_speed: Optional[float] = 600.0  # Replay speed multiplier: 1.0 = real-time, 600.0 = 600x speed (0.1s per bar)
    testing_mode: bool = False  # Force trading mode - allows trading with minimal bars (1 bar minimum)
    strict_data_mode: bool = False  # If True, fail hard when cached data is missing (production safety)
    # Alpaca credentials
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    base_url: Optional[str] = None  # Override ALPACA_BASE_URL: "https://paper-api.alpaca.markets" or "https://api.alpaca.markets"
    # IBKR connection parameters
    ibkr_host: str = "127.0.0.1"
    ibkr_port: int = 4002  # Common ports: 4002 (default), 7497 (paper), 7496 (live)
    ibkr_client_id: Optional[int] = None  # None will auto-generate random client ID
    ibkr_account_id: Optional[str] = None


@app.post("/live/start")
async def start_live_trading(request: LiveStartRequest):
    """Start live trading."""
    # Lazy initialization - initialize bot_manager on first request
    if not bot_manager:
        _initialize_bot_manager()

    from core.live import (
        AlpacaBrokerClient,
        AlpacaDataFeed,
        CryptoDataFeed,
        get_ibkr_broker_client,
        get_ibkr_data_feed,
        MockDataFeed,
        PaperBrokerClient,
        LiveTradingConfig,
    )
    import os

    # 🔍 DIAGNOSTIC LOGGING: Start request details
    logger.info(f"🔵 START REQUEST: broker_type={request.broker_type}, offline_mode={request.offline_mode}, symbols={request.symbols}")

    # Create broker client based on type
    if request.broker_type == "paper" or request.broker_type == "cached":
        # Use paper broker for both paper trading and cached/offline simulation
        broker_client = PaperBrokerClient(initial_cash=bot_manager.portfolio.initial_capital)
        if request.broker_type == "cached":
            logger.info("Using paper broker client for cached/offline simulation")
    elif request.broker_type == "ibkr":
        # Lazy import IBKR to avoid uvloop conflict
        IBKRBrokerClient = get_ibkr_broker_client()
        # Use provided client_id or None (will auto-generate random)
        broker_client = IBKRBrokerClient(
            host=request.ibkr_host,
            port=request.ibkr_port,
            client_id=request.ibkr_client_id if request.ibkr_client_id else None,
            account_id=request.ibkr_account_id,
        )
        # Connect to IBKR
        if not broker_client.connect():
            raise HTTPException(status_code=500, detail="Failed to connect to IBKR. Ensure TWS/IB Gateway is running.")
    elif request.broker_type == "alpaca":
        # Get Alpaca credentials from request or environment
        api_key = request.api_key or os.getenv("ALPACA_API_KEY")
        api_secret = request.api_secret or os.getenv("ALPACA_SECRET_KEY")
        # Use base_url from request, or environment, or default to paper
        base_url = request.base_url or os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
        
        if not api_key or not api_secret:
            raise HTTPException(
                status_code=400,
                detail="Alpaca API credentials required. Provide api_key and api_secret in request or set ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables."
            )
        
        broker_client = AlpacaBrokerClient(
            api_key=api_key,
            api_secret=api_secret,
            base_url=base_url,
        )
        is_paper = "paper-api" in base_url
        logger.info(f"Alpaca broker client created successfully (mode: {'paper' if is_paper else 'live'})")
    else:
        raise HTTPException(status_code=400, detail=f"Unknown broker type: {request.broker_type}")

    # Create data feed
    logger.info(f"🔵 Creating data feed: broker_type={request.broker_type}, offline_mode={request.offline_mode}")
    if request.broker_type == "cached" or request.offline_mode:
        # Use cached data feed for offline trading
        from core.live.data_feed_cached import CachedDataFeed
        from core.settings_loader import load_settings
        from pathlib import Path
        
        try:
            settings = load_settings()
            cache_path = Path(settings.data.cache.path)
            logger.info(f"🔵 Cache path: {cache_path}")
            
            # Parse start_time and end_time if provided (preferred over start_date)
            start_datetime_obj = None
            end_datetime_obj = None
            
            if request.start_time or request.end_time:
                # Use start_time/end_time if provided (more precise)
                from datetime import datetime
                try:
                    # datetime-local inputs are in user's local time, but for US markets (SPY, QQQ)
                    # we should interpret them as Eastern Time (EST/EDT)
                    # Check if symbols are US market symbols
                    us_market_symbols = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META']
                    is_us_market = any(s in request.symbols for s in us_market_symbols)
                    
                    # Use zoneinfo (Python 3.9+) or fallback to pytz
                    try:
                        from zoneinfo import ZoneInfo
                        def get_eastern_tz():
                            return ZoneInfo('US/Eastern')
                    except ImportError:
                        # Fallback for Python < 3.9
                        import pytz
                        def get_eastern_tz():
                            return pytz.timezone('US/Eastern')
                    
                    if request.start_time:
                        # Parse ISO format: YYYY-MM-DDTHH:MM:SS or YYYY-MM-DDTHH:MM
                        start_str = request.start_time
                        if 'T' in start_str and len(start_str.split('T')[1]) <= 5:
                            # Add seconds if missing (datetime-local format)
                            start_str = start_str + ':00'
                        
                        start_datetime_obj = datetime.fromisoformat(start_str)
                        
                        # If no timezone, assume US Eastern Time for US market symbols
                        if start_datetime_obj.tzinfo is None:
                            if is_us_market:
                                # Convert to US Eastern Time, then to UTC
                                eastern = get_eastern_tz()
                                # Localize naive datetime to Eastern time
                                if hasattr(eastern, 'localize'):
                                    # pytz style
                                    start_datetime_obj = eastern.localize(start_datetime_obj)
                                else:
                                    # zoneinfo style (Python 3.9+)
                                    start_datetime_obj = start_datetime_obj.replace(tzinfo=eastern)
                                start_datetime_obj = start_datetime_obj.astimezone(timezone.utc)
                            else:
                                # For non-US symbols, assume UTC
                                start_datetime_obj = start_datetime_obj.replace(tzinfo=timezone.utc)
                        
                        logger.info(f"🔵 Starting from datetime: {start_datetime_obj} (UTC) - interpreted as US Eastern if US market symbol")
                    
                    if request.end_time:
                        # Parse ISO format: YYYY-MM-DDTHH:MM:SS or YYYY-MM-DDTHH:MM
                        end_str = request.end_time
                        if 'T' in end_str and len(end_str.split('T')[1]) <= 5:
                            # Add seconds if missing (datetime-local format)
                            end_str = end_str + ':00'
                        
                        end_datetime_obj = datetime.fromisoformat(end_str)
                        
                        # If no timezone, assume US Eastern Time for US market symbols
                        if end_datetime_obj.tzinfo is None:
                            if is_us_market:
                                # Convert to US Eastern Time, then to UTC
                                eastern = get_eastern_tz()
                                # Localize naive datetime to Eastern time
                                if hasattr(eastern, 'localize'):
                                    # pytz style
                                    end_datetime_obj = eastern.localize(end_datetime_obj)
                                else:
                                    # zoneinfo style (Python 3.9+)
                                    end_datetime_obj = end_datetime_obj.replace(tzinfo=eastern)
                                end_datetime_obj = end_datetime_obj.astimezone(timezone.utc)
                            else:
                                # For non-US symbols, assume UTC
                                end_datetime_obj = end_datetime_obj.replace(tzinfo=timezone.utc)
                        
                        logger.info(f"🔵 Ending at datetime: {end_datetime_obj} (UTC) - interpreted as US Eastern if US market symbol")
                    
                    # Validate: end_time must be after start_time
                    if start_datetime_obj and end_datetime_obj and end_datetime_obj <= start_datetime_obj:
                        raise HTTPException(status_code=400, detail="end_time must be after start_time")
                        
                except ValueError as e:
                    logger.warning(f"Invalid datetime format: {e}")
                    raise HTTPException(status_code=400, detail=f"Invalid datetime format: {e}")
            elif request.start_date:
                # Fallback to start_date for backward compatibility
                from datetime import datetime
                try:
                    start_datetime_obj = datetime.strptime(request.start_date, "%Y-%m-%d")
                    # Set to market open time (9:30 AM ET = 13:30 UTC)
                    start_datetime_obj = start_datetime_obj.replace(hour=13, minute=30, second=0, microsecond=0)
                    if start_datetime_obj.tzinfo is None:
                        start_datetime_obj = start_datetime_obj.replace(tzinfo=timezone.utc)
                    logger.info(f"🔵 Starting from historical date: {start_datetime_obj}")
                except ValueError as e:
                    logger.warning(f"Invalid start_date format '{request.start_date}': {e}. Using all available data.")
            
            data_feed = CachedDataFeed(
                cache_path=cache_path,
                bar_size="1Min",
                symbols=request.symbols,
                start_date=start_datetime_obj,
                end_date=end_datetime_obj,
            )
            # Set strict_data_mode if requested (production safety)
            if request.strict_data_mode:
                data_feed.strict_data_mode = True
                logger.info("🔒 Strict data mode enabled - will fail hard if cached data is missing")
            logger.info(f"✅ CachedDataFeed created successfully for symbols: {request.symbols}")
        except Exception as e:
            logger.error(f"❌ Failed to create CachedDataFeed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to create cached data feed: {str(e)}")
    elif request.broker_type == "alpaca":
        # Get Alpaca credentials for data feed
        api_key = request.api_key or os.getenv("ALPACA_API_KEY")
        api_secret = request.api_secret or os.getenv("ALPACA_SECRET_KEY")
        # Use base_url from request, or environment, or default to paper
        base_url = request.base_url or os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
        
        # Check if any symbols are crypto (e.g., BTC/USD, ETH/USD)
        def is_crypto_symbol(symbol: str) -> bool:
            """Check if symbol is a crypto pair."""
            crypto_pairs = ["BTC", "ETH", "SOL", "AVAX", "MATIC", "LINK", "UNI", "AAVE", "ALGO", "DOGE"]
            return any(crypto in symbol.upper() for crypto in crypto_pairs) or "/USD" in symbol.upper()
        
        has_crypto = any(is_crypto_symbol(s) for s in request.symbols)
        
        if has_crypto:
            # Use crypto data feed for crypto symbols
            data_feed = CryptoDataFeed(
                api_key=api_key,
                api_secret=api_secret,
                base_url=base_url,
                bar_size="1Min",  # 1-minute bars
            )
            logger.info("Using crypto data feed for crypto symbols")
        else:
            # Use stock data feed for regular symbols
            data_feed = AlpacaDataFeed(
                api_key=api_key,
                api_secret=api_secret,
                base_url=base_url,
                bar_size="1Min",  # 1-minute bars (minimum available on Alpaca free tier)
            )
    elif request.broker_type == "ibkr":
        # Lazy import IBKR to avoid uvloop conflict
        IBKRDataFeed = get_ibkr_data_feed()
        from pathlib import Path
        
        # Try to load Polygon client and cache for faster preload
        polygon_client = None
        cache_path = None
        try:
            from core.settings_loader import load_settings
            from services.polygon_client import PolygonClient
            settings = load_settings()
            cache_path = settings.data.cache.path
            # Only create Polygon client if API key is configured
            if settings.polygon.api_key and settings.polygon.api_key != "YOUR_POLYGON_KEY":
                polygon_client = PolygonClient(settings.polygon, cache_path)
                logger.info("Polygon cache enabled for faster preload")
        except Exception as e:
            logger.debug(f"Could not load Polygon cache (optional): {e}")
        
        data_feed = IBKRDataFeed(
            broker_client=broker_client,
            bar_size="1 min",
            polygon_client=polygon_client,
            cache_path=cache_path,
        )
    else:
        # Use mock for other brokers (or implement their data feeds)
        data_feed = MockDataFeed(initial_price=100.0)

    # Load asset profiles from config
    from core.settings_loader import load_settings
    from core.config.asset_profiles import AssetProfileManager
    asset_profiles = None
    try:
        settings = load_settings()
        profile_manager = AssetProfileManager()
        if settings.symbols:
            profile_manager.load_from_config(settings.symbols)
        asset_profiles = {symbol: profile_manager.get_profile(symbol) for symbol in request.symbols}
        logger.info(f"Loaded asset profiles for {len(asset_profiles)} symbols")
    except Exception as e:
        logger.warning(f"Could not load asset profiles: {e}, using defaults")
    
    # Start live trading
    logger.info(f"🔵 Starting live trading with broker_client={type(broker_client).__name__}, data_feed={type(data_feed).__name__}")
    try:
        from core.live import LiveTradingConfig
        # Set minimum bars based on testing_mode
        min_bars = 1 if request.testing_mode else 10  # 1 bar for testing, 10 for relaxed mode
        
        live_config = LiveTradingConfig(
            symbols=request.symbols,
            fixed_investment_amount=request.fixed_investment_amount,
            enable_profit_taking=True,
            asset_profiles=asset_profiles,
            offline_mode=request.offline_mode or request.broker_type == "cached",
            replay_speed_multiplier=request.replay_speed or 600.0,  # Use provided speed or default 600x
            testing_mode=request.testing_mode,  # Force trading mode
            minimum_bars_required=min_bars,  # 1 for testing, 10 for relaxed
        )
        logger.info(f"🔵 Testing mode: {live_config.testing_mode}, Minimum bars: {live_config.minimum_bars_required}")
        logger.info(f"🔵 Replay speed: {live_config.replay_speed_multiplier}x")
        logger.info(f"🔵 LiveTradingConfig created, calling bot_manager.start_live_trading()...")
        bot_manager.start_live_trading(
            symbols=request.symbols,
            broker_client=broker_client,
            data_feed=data_feed,
            config=live_config,
            asset_profiles=asset_profiles,
        )
        logger.info(f"✅ bot_manager.start_live_trading() completed successfully")
        return {"status": "started", "message": "Live trading started successfully"}
    except ValueError as e:
        logger.error(f"❌ ValueError starting live trading: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Unexpected error starting live trading: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start live trading: {str(e)}")


@app.post("/live/stop")
async def stop_live_trading():
    """Stop live trading."""
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    bot_manager.stop_live_trading()
    return {"status": "stopped", "message": "Live trading stopped successfully"}


@app.get("/cache/available-dates")
async def get_available_cached_dates(
    symbols: Optional[str] = None,
    timeframe: str = "1min",
    interval_minutes: int = 30
):
    """
    Get available dates and times from cache (REAL DATA ONLY).
    Returns only dates/times where cached data actually exists.
    Times are rounded to 30-minute intervals by default (9:30, 10:00, 10:30, etc.).
    
    Query parameters:
    - symbols: Comma-separated list of symbols (e.g., "SPY,QQQ"). Defaults to SPY,QQQ if not provided.
    - timeframe: Timeframe to check (default: "1min")
    - interval_minutes: Round times to this interval (default: 30 for 30-minute intervals)
    
    Returns:
    {
        "available_dates": [
            {
                "date": "2025-11-24",
                "times": ["09:30", "10:00", "10:30", ...],
                "display": "Mon, Nov 24, 2025"
            },
            ...
        ],
        "symbols": ["SPY", "QQQ"],
        "timeframe": "1min",
        "interval_minutes": 30,
        "total_dates": 10
    }
    """
    from pathlib import Path
    from services.cache import BarCache
    from core.settings_loader import load_settings
    from datetime import datetime
    
    try:
        # Get cache path from settings
        settings = load_settings()
        cache_path = Path(settings.data.cache.path)
        
        # Parse symbols
        if symbols:
            symbol_list = [s.strip().upper() for s in symbols.split(",")]
        else:
            # Default to SPY and QQQ
            symbol_list = ["SPY", "QQQ"]
        
        # Get available dates from cache (with 30-minute interval rounding)
        cache = BarCache(cache_path)
        available_dates = cache.get_available_dates(symbol_list, timeframe, interval_minutes=interval_minutes)
        
        # CRITICAL: Filter out market holidays and non-trading days
        # Get market calendar to validate trading days
        from datetime import timezone, timedelta
        
        # Get date range from available dates
        if available_dates:
            min_date = min(datetime.strptime(d["date"], "%Y-%m-%d") for d in available_dates)
            max_date = max(datetime.strptime(d["date"], "%Y-%m-%d") for d in available_dates)
            
            # Get known holidays for this date range
            known_holidays = _get_known_holidays(min_date.replace(tzinfo=timezone.utc), max_date.replace(tzinfo=timezone.utc))
            logger.info(f"Filtering out holidays: {sorted(known_holidays)}")
        else:
            known_holidays = set()
        
        # Format for frontend and filter holidays
        formatted_dates = []
        for date_info in available_dates:
            date_str = date_info["date"]
            
            # SKIP if this is a known market holiday
            if date_str in known_holidays:
                logger.debug(f"Skipping holiday: {date_str}")
                continue
            
            # SKIP if this is a weekend (Saturday=5, Sunday=6)
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            if date_obj.weekday() >= 5:  # Saturday or Sunday
                logger.debug(f"Skipping weekend: {date_str}")
                continue
            
            times = date_info["times"]
            
            # Format display string
            display_str = date_obj.strftime("%a, %b %d, %Y")
            
            # Generate date/time options for this date
            date_time_options = []
            for time_str in sorted(times):
                # Times are already filtered to market hours and rounded to interval
                hour, minute = map(int, time_str.split(":"))
                
                # Format time display
                if hour < 12:
                    time_display = f"{hour}:{minute:02d} AM" if hour != 0 else f"12:{minute:02d} AM"
                elif hour == 12:
                    time_display = f"12:{minute:02d} PM"
                else:
                    time_display = f"{hour-12}:{minute:02d} PM"
                
                date_time_options.append({
                    "value": f"{date_str}T{time_str}:00",
                    "display": f"{display_str} {time_display}"
                })
            
            if date_time_options:  # Only add if there are valid market hours
                formatted_dates.append({
                    "date": date_str,
                    "times": sorted(times),
                    "display": display_str,
                    "options": date_time_options
                })
        
        return {
            "available_dates": formatted_dates,
            "symbols": symbol_list,
            "timeframe": timeframe,
            "interval_minutes": interval_minutes,
            "total_dates": len(formatted_dates)
        }
        
    except Exception as e:
        logger.error(f"Error getting available cached dates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error querying cache: {str(e)}")


@app.get("/market/calendar")
async def get_market_calendar(start_date: Optional[str] = None, end_date: Optional[str] = None):
    """
    Get market calendar with actual trading days and early closes from Alpaca.
    Returns dates that have actual trading data.
    """
    from datetime import datetime, timezone, timedelta
    import os
    
    # Default to last 3 months
    if not end_date:
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")
    
    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame
        
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_SECRET_KEY")
        
        if not api_key or not api_secret:
            # Fallback: return basic weekday calendar without holidays
            logger.warning("Alpaca credentials not found, using basic calendar")
            return await _get_basic_calendar(start_date, end_date)
        
        client = StockHistoricalDataClient(api_key=api_key, secret_key=api_secret)
        
        # Query SPY (most liquid) to get actual trading days
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        
        request = StockBarsRequest(
            symbol_or_symbols="SPY",
            timeframe=TimeFrame.Day,
            start=start_dt,
            end=end_dt,
        )
        
        # Get known holidays and early closes FIRST
        known_holidays = _get_known_holidays(start_dt, end_dt)
        early_close_dates = _get_known_early_closes(start_dt, end_dt)
        
        logger.info(f"Known holidays: {sorted(known_holidays)}")
        logger.info(f"Early closes: {early_close_dates}")
        
        # Check if we're querying future dates (beyond today's date)
        now = datetime.now(timezone.utc)
        is_future_query = start_dt.date() > now.date()
        
        if is_future_query:
            # For future dates, build calendar from weekdays and apply holiday/early close rules
            logger.info("Querying future dates - using calendar rules instead of Alpaca data")
            from datetime import date, timedelta
            trading_dates = {}
            current = start_dt.date()
            end_date_obj = end_dt.date()
            
            while current <= end_date_obj:
                # Only weekdays
                if current.weekday() < 5:
                    date_str = current.strftime("%Y-%m-%d")
                    # Skip holidays
                    if date_str not in known_holidays:
                        is_early_close = date_str in early_close_dates
                        close_time = early_close_dates.get(date_str, "16:00")
                        trading_dates[date_str] = {
                            "date": date_str,
                            "is_trading_day": True,
                            "early_close": is_early_close,
                            "close_time": close_time
                        }
                current += timedelta(days=1)
        else:
            # For past dates, use Alpaca data but filter holidays
            bars = client.get_stock_bars(request)
            # Alpaca returns BarSet, which can be accessed like a dict
            if hasattr(bars, 'get'):
                spy_bars = bars.get("SPY", [])
            elif hasattr(bars, '__iter__'):
                spy_bars = list(bars)
            else:
                spy_bars = []
            
            # Extract unique trading dates, filtering out holidays
            trading_dates = {}
            for bar in spy_bars:
                # Bar timestamp is in UTC, convert to date string
                if hasattr(bar.timestamp, 'date'):
                    bar_date = bar.timestamp.date()
                elif isinstance(bar.timestamp, datetime):
                    bar_date = bar.timestamp.date()
                else:
                    try:
                        bar_date = datetime.fromisoformat(str(bar.timestamp).replace('Z', '+00:00')).date()
                    except:
                        logger.warning(f"Could not parse bar timestamp: {bar.timestamp}")
                        continue
                
                date_str = bar_date.strftime("%Y-%m-%d")
                
                # Skip known holidays (even if Alpaca returns bars)
                if date_str in known_holidays:
                    logger.info(f"Skipping holiday: {date_str}")
                    continue
                
                # Check if it's an early close
                is_early_close = date_str in early_close_dates
                close_time = early_close_dates.get(date_str, "16:00")
                
                trading_dates[date_str] = {
                    "date": date_str,
                    "is_trading_day": True,
                    "early_close": is_early_close,
                    "close_time": close_time
                }
        
        # CRITICAL: After processing, ensure we haven't included any holidays
        # Remove any holidays that might have slipped through (Alpaca sometimes returns bars for holidays)
        logger.info(f"Before cleanup: {len(trading_dates)} trading dates")
        holidays_removed = []
        for holiday_date in known_holidays:
            if holiday_date in trading_dates:
                logger.warning(f"⚠️ Removing holiday that was in data: {holiday_date}")
                del trading_dates[holiday_date]
                holidays_removed.append(holiday_date)
        
        if holidays_removed:
            logger.info(f"Removed {len(holidays_removed)} holidays: {holidays_removed}")
        
        # Also ensure early closes are properly marked (override any incorrect data from Alpaca)
        early_closes_marked = []
        for early_close_date, close_time in early_close_dates.items():
            if early_close_date in trading_dates:
                trading_dates[early_close_date]["early_close"] = True
                trading_dates[early_close_date]["close_time"] = close_time
                early_closes_marked.append(early_close_date)
                logger.info(f"✅ Marked early close: {early_close_date} at {close_time}")
        
        if early_closes_marked:
            logger.info(f"Marked {len(early_closes_marked)} early closes: {early_closes_marked}")
        
        logger.info(f"After cleanup: {len(trading_dates)} trading dates")
        
        return {
            "trading_dates": list(trading_dates.keys()),
            "calendar": trading_dates,
            "start_date": start_date,
            "end_date": end_date
        }
        
    except Exception as e:
        logger.error(f"Error fetching market calendar from Alpaca: {e}")
        logger.info("Falling back to basic calendar with holiday filtering")
        # Fallback to basic calendar BUT still apply holiday/early close rules
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        known_holidays = _get_known_holidays(start_dt, end_dt)
        early_close_dates = _get_known_early_closes(start_dt, end_dt)
        
        # Get basic calendar
        basic_cal = await _get_basic_calendar(start_date, end_date)
        
        # Apply holiday filtering
        trading_dates = basic_cal["calendar"]
        for holiday_date in known_holidays:
            if holiday_date in trading_dates:
                logger.info(f"Removing holiday from fallback calendar: {holiday_date}")
                del trading_dates[holiday_date]
        
        # Apply early close rules
        for early_close_date, close_time in early_close_dates.items():
            if early_close_date in trading_dates:
                trading_dates[early_close_date]["early_close"] = True
                trading_dates[early_close_date]["close_time"] = close_time
                logger.info(f"Marked early close in fallback: {early_close_date} at {close_time}")
        
        return {
            "trading_dates": list(trading_dates.keys()),
            "calendar": trading_dates,
            "start_date": start_date,
            "end_date": end_date
        }


async def _get_basic_calendar(start_date: str, end_date: str):
    """Fallback: Generate basic weekday calendar without holidays."""
    from datetime import datetime, timedelta
    
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    trading_dates = {}
    current = start_dt
    while current <= end_dt:
        # Only weekdays
        if current.weekday() < 5:  # Monday=0, Friday=4
            date_str = current.strftime("%Y-%m-%d")
            trading_dates[date_str] = {
                "date": date_str,
                "is_trading_day": True,
                "early_close": False,
                "close_time": "16:00"
            }
        current += timedelta(days=1)
    
    return {
        "trading_dates": list(trading_dates.keys()),
        "calendar": trading_dates,
        "start_date": start_date,
        "end_date": end_date
    }


def _get_known_holidays(start_dt: datetime, end_dt: datetime) -> set:
    """Get known market holidays (market closed)."""
    from datetime import date, timedelta
    holidays = set()
    
    # Get all years in range
    years = set()
    current = start_dt
    while current <= end_dt:
        years.add(current.year)
        current += timedelta(days=365)
    
    for year in years:
        # New Year's Day (Jan 1, or Monday if Jan 1 is weekend)
        jan_1 = date(year, 1, 1)
        if jan_1.weekday() == 5:  # Saturday
            holidays.add((jan_1 + timedelta(days=2)).strftime("%Y-%m-%d"))  # Monday
        elif jan_1.weekday() == 6:  # Sunday
            holidays.add((jan_1 + timedelta(days=1)).strftime("%Y-%m-%d"))  # Monday
        else:
            holidays.add(jan_1.strftime("%Y-%m-%d"))
        
        # Martin Luther King Jr. Day (3rd Monday in January)
        jan_1 = date(year, 1, 1)
        days_until_monday = (0 - jan_1.weekday()) % 7
        first_monday = jan_1 + timedelta(days=days_until_monday)
        mlk_day = first_monday + timedelta(days=14)  # 3rd Monday
        holidays.add(mlk_day.strftime("%Y-%m-%d"))
        
        # Presidents Day (3rd Monday in February)
        feb_1 = date(year, 2, 1)
        days_until_monday = (0 - feb_1.weekday()) % 7
        first_monday = feb_1 + timedelta(days=days_until_monday)
        presidents_day = first_monday + timedelta(days=14)  # 3rd Monday
        holidays.add(presidents_day.strftime("%Y-%m-%d"))
        
        # Good Friday (varies, but approximate)
        # Easter calculation is complex, so we'll skip for now
        
        # Memorial Day (last Monday in May)
        may_31 = date(year, 5, 31)
        days_until_monday = (0 - may_31.weekday()) % 7
        memorial_day = may_31 - timedelta(days=days_until_monday)
        holidays.add(memorial_day.strftime("%Y-%m-%d"))
        
        # Juneteenth (June 19, or next weekday)
        jun_19 = date(year, 6, 19)
        if jun_19.weekday() == 5:  # Saturday
            holidays.add((jun_19 - timedelta(days=1)).strftime("%Y-%m-%d"))  # Friday
        elif jun_19.weekday() == 6:  # Sunday
            holidays.add((jun_19 + timedelta(days=1)).strftime("%Y-%m-%d"))  # Monday
        else:
            holidays.add(jun_19.strftime("%Y-%m-%d"))
        
        # Independence Day (July 4, or next weekday)
        jul_4 = date(year, 7, 4)
        if jul_4.weekday() == 5:  # Saturday
            holidays.add((jul_4 - timedelta(days=1)).strftime("%Y-%m-%d"))  # Friday
        elif jul_4.weekday() == 6:  # Sunday
            holidays.add((jul_4 + timedelta(days=1)).strftime("%Y-%m-%d"))  # Monday
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
        thanksgiving = first_thursday + timedelta(days=21)  # 4th Thursday
        holidays.add(thanksgiving.strftime("%Y-%m-%d"))
        
        # Day After Thanksgiving (Friday after Thanksgiving - market closed)
        day_after_thanksgiving = thanksgiving + timedelta(days=1)
        holidays.add(day_after_thanksgiving.strftime("%Y-%m-%d"))
        
        # Christmas (Dec 25, or next weekday)
        dec_25 = date(year, 12, 25)
        if dec_25.weekday() == 5:  # Saturday
            holidays.add((dec_25 - timedelta(days=1)).strftime("%Y-%m-%d"))  # Friday
        elif dec_25.weekday() == 6:  # Sunday
            holidays.add((dec_25 + timedelta(days=1)).strftime("%Y-%m-%d"))  # Monday
        else:
            holidays.add(dec_25.strftime("%Y-%m-%d"))
    
    return holidays


def _get_known_early_closes(start_dt: datetime, end_dt: datetime) -> dict:
    """Get known early close dates (1 PM ET)."""
    from datetime import date, timedelta
    early_closes = {}
    
    # Get all years in range
    years = set()
    current = start_dt
    while current <= end_dt:
        years.add(current.year)
        current += timedelta(days=365)
    
    for year in years:
        # Day after Thanksgiving (4th Thursday in November + 1 day = Friday)
        # Thanksgiving is 4th Thursday of November
        nov_1 = date(year, 11, 1)
        # Find first Thursday
        days_until_thursday = (3 - nov_1.weekday()) % 7
        first_thursday = nov_1 + timedelta(days=days_until_thursday)
        # 4th Thursday is 3 weeks later
        thanksgiving = first_thursday + timedelta(days=21)
        day_after = thanksgiving + timedelta(days=1)
        
        day_after_dt = datetime.combine(day_after, datetime.min.time()).replace(tzinfo=timezone.utc)
        if start_dt <= day_after_dt <= end_dt:
            early_closes[day_after.strftime("%Y-%m-%d")] = "13:00"  # 1 PM ET
        
        # Day before Christmas (Dec 24, if weekday)
        christmas_eve = date(year, 12, 24)
        if christmas_eve.weekday() < 5:  # Monday-Friday
            christmas_eve_dt = datetime.combine(christmas_eve, datetime.min.time()).replace(tzinfo=timezone.utc)
            if start_dt <= christmas_eve_dt <= end_dt:
                early_closes[christmas_eve.strftime("%Y-%m-%d")] = "13:00"  # 1 PM ET
    
    return early_closes


@app.get("/market/status")
async def get_market_status():
    """Check if US market is currently open (9:30 AM - 4:00 PM ET, weekdays only)."""
    from datetime import datetime, timezone, timedelta
    
    now_utc = datetime.now(timezone.utc)
    
    # Convert to ET (handles DST)
    # ET is UTC-5 (EST) or UTC-4 (EDT)
    # DST runs from second Sunday in March to first Sunday in November
    year = now_utc.year
    # Find second Sunday in March
    march_1 = datetime(year, 3, 1, tzinfo=timezone.utc)
    march_1_weekday = march_1.weekday()
    days_to_second_sunday = (6 - march_1_weekday) % 7 + 7  # First Sunday + 7 days
    dst_start = march_1 + timedelta(days=days_to_second_sunday)
    
    # Find first Sunday in November
    nov_1 = datetime(year, 11, 1, tzinfo=timezone.utc)
    nov_1_weekday = nov_1.weekday()
    days_to_first_sunday = (6 - nov_1_weekday) % 7
    dst_end = nov_1 + timedelta(days=days_to_first_sunday)
    
    # Determine if DST is active
    is_dst = dst_start <= now_utc < dst_end
    et_offset = -4 if is_dst else -5
    et_time = now_utc + timedelta(hours=et_offset)
    
    # Check if weekday (Monday=0, Sunday=6)
    is_weekday = et_time.weekday() < 5
    
    # Check time (9:30 AM - 4:00 PM ET)
    hour = et_time.hour
    minute = et_time.minute
    is_trading_hours = is_weekday and hour >= 9 and (hour < 16 or (hour == 9 and minute >= 30))
    
    return {
        "is_open": is_trading_hours,
        "current_time_et": et_time.strftime("%Y-%m-%d %H:%M:%S ET"),
        "current_time_utc": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "is_weekday": is_weekday,
        "trading_hours": "9:30 AM - 4:00 PM ET",
    }


@app.get("/live/status")
async def get_live_status():
    """Get live trading status."""
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    return bot_manager.get_live_status()


# Logging Configuration Endpoints
@app.get("/settings/logging")
async def get_logging_settings():
    """Get current logging configuration."""
    try:
        from pathlib import Path
        import yaml
        
        # Load settings directly from YAML file
        settings_path = Path("config/settings.yaml")
        if settings_path.exists():
            with open(settings_path, 'r') as f:
                settings_data = yaml.safe_load(f) or {}
            logging_config = settings_data.get('logging', {})
        else:
            logging_config = {}
        
        # Get current log level from root logger
        import logging
        root_logger = logging.getLogger()
        current_level = logging.getLevelName(root_logger.level)
        
        return {
            "log_level": logging_config.get("level", "INFO"),
            "enable_debug": logging_config.get("enable_debug", False),
            "current_level": current_level,
            "log_files": {
                "main": logging_config.get("log_file", "logs/futbot.log"),
                "api": logging_config.get("api_log_file", "logs/api_server.log"),
                "events": logging_config.get("event_log_file", "logs/trading_events.jsonl")
            }
        }
    except Exception as e:
        logger.error(f"Error getting logging settings: {e}")
        return {
            "log_level": "INFO",
            "enable_debug": False,
            "current_level": "INFO",
            "log_files": {}
        }


class LoggingSettingsRequest(BaseModel):
    """Request to update logging settings."""
    log_level: Optional[str] = None  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    enable_debug: Optional[bool] = None


@app.post("/settings/logging")
async def update_logging_settings(request: LoggingSettingsRequest):
    """Update logging configuration dynamically."""
    try:
        import logging
        from pathlib import Path
        import yaml
        
        # Update root logger level
        if request.log_level:
            level_map = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR,
                "CRITICAL": logging.CRITICAL
            }
            new_level = level_map.get(request.log_level.upper(), logging.INFO)
            logging.getLogger().setLevel(new_level)
            # Also update all child loggers
            for logger_name in logging.Logger.manager.loggerDict:
                logging.getLogger(logger_name).setLevel(new_level)
            logger.info(f"✅ Log level changed to {request.log_level}")
        
        # Update settings.yaml file
        settings_path = Path("config/settings.yaml")
        if settings_path.exists():
            with open(settings_path, 'r') as f:
                settings_data = yaml.safe_load(f) or {}
            
            if 'logging' not in settings_data:
                settings_data['logging'] = {}
            
            if request.log_level:
                settings_data['logging']['level'] = request.log_level.upper()
            if request.enable_debug is not None:
                settings_data['logging']['enable_debug'] = request.enable_debug
            
            with open(settings_path, 'w') as f:
                yaml.dump(settings_data, f, default_flow_style=False, sort_keys=False)
            logger.info(f"✅ Settings file updated")
        
        return {
            "success": True,
            "message": "Logging settings updated",
            "log_level": request.log_level or "unchanged",
            "enable_debug": request.enable_debug if request.enable_debug is not None else "unchanged"
        }
    except Exception as e:
        logger.error(f"Error updating logging settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update logging settings: {str(e)}")


@app.get("/logs")
async def get_logs(limit: int = 100, level: Optional[str] = None):
    """Get recent log entries from multiple log sources."""
    try:
        from pathlib import Path
        import os
        
        # Try multiple log file locations
        log_files = [
            Path("logs/futbot.log"),
            Path("logs/api_server.log"),
            Path("/tmp/futbot_server.log"),
            Path("logs/trading_events.jsonl"),  # JSONL format
        ]
        
        all_logs = []
        found_files = []
        
        for log_file in log_files:
            if not log_file.exists():
                continue
            
            found_files.append(str(log_file))
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    # Get last N lines
                    recent_lines = lines[-limit:] if len(lines) > limit else lines
                    
                    for line in recent_lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Handle JSONL format (trading_events.jsonl)
                        if log_file.suffix == '.jsonl':
                            try:
                                import json
                                event = json.loads(line)
                                log_entry = {
                                    "timestamp": event.get("timestamp", event.get("time", "")),
                                    "logger": event.get("logger", "trading_events"),
                                    "level": event.get("level", "INFO"),
                                    "message": event.get("message", str(event))
                                }
                            except json.JSONDecodeError:
                                continue
                        else:
                            # Parse standard log line (format: timestamp - logger - level - message)
                            # Example: 2024-11-29 14:15:30,123 - core.live.scheduler - INFO - Message
                            # Or uvicorn format: INFO:     127.0.0.1:50679 - "GET /regime HTTP/1.1" 200 OK
                            parts = line.split(' - ', 3)
                            if len(parts) >= 4:
                                timestamp = parts[0]
                                logger_name = parts[1]
                                log_level = parts[2]
                                message = parts[3]
                                log_entry = {
                                    "timestamp": timestamp,
                                    "logger": logger_name,
                                    "level": log_level,
                                    "message": message
                                }
                            elif line.startswith(('INFO:', 'WARNING:', 'ERROR:', 'DEBUG:', 'CRITICAL:')):
                                # Uvicorn format: INFO:     127.0.0.1:50679 - "GET /regime HTTP/1.1" 200 OK
                                level_end = line.find(':')
                                if level_end > 0:
                                    log_level = line[:level_end].strip()
                                    message = line[level_end + 1:].strip()
                                    log_entry = {
                                        "timestamp": "",
                                        "logger": "uvicorn",
                                        "level": log_level,
                                        "message": message
                                    }
                                else:
                                    log_entry = {
                                        "timestamp": "",
                                        "logger": "uvicorn",
                                        "level": "INFO",
                                        "message": line
                                    }
                            else:
                                # Fallback: just add the line
                                log_entry = {
                                    "timestamp": "",
                                    "logger": str(log_file.name),
                                    "level": "INFO",
                                    "message": line
                                }
                        
                        # Filter by level if specified
                        if level and log_entry.get("level", "").upper() != level.upper():
                            continue
                        
                        all_logs.append(log_entry)
            except Exception as e:
                logger.warning(f"Error reading {log_file}: {e}")
                continue
        
        # Sort by timestamp if available, otherwise keep order
        try:
            all_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        except:
            pass
        
        # Limit total results
        all_logs = all_logs[:limit]
        
        return {
            "logs": all_logs,
            "total": len(all_logs),
            "files_checked": found_files,
            "message": f"Found logs from {len(found_files)} file(s)" if found_files else "No log files found"
        }
    except Exception as e:
        logger.error(f"Error reading logs: {e}", exc_info=True)
        return {"logs": [], "error": str(e), "message": f"Error: {str(e)}"}


@app.get("/logs/download")
async def download_logs():
    """Download log file."""
    from pathlib import Path
    log_file = Path("logs/futbot.log")
    if not log_file.exists():
        raise HTTPException(status_code=404, detail="Log file not found")
    return FileResponse(
        path=str(log_file),
        filename="futbot.log",
        media_type="text/plain"
    )


@app.get("/live/portfolio")
async def get_live_portfolio():
    """Get live portfolio snapshot."""
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    return bot_manager.get_live_portfolio()


@app.get("/live/recent-trades")
async def get_live_recent_trades():
    """Get recent live trades."""
    if not bot_manager or not bot_manager.broker_client:
        raise HTTPException(status_code=503, detail="Broker client not available")
    fills = bot_manager.broker_client.get_recent_fills(limit=50)
    return {
        "trades": [
            {
                "order_id": fill.order_id,
                "symbol": fill.symbol,
                "side": fill.side.value,
                "quantity": fill.quantity,
                "price": fill.price,
                "timestamp": fill.timestamp.isoformat(),
                "commission": fill.commission,
            }
            for fill in fills
        ]
    }


@app.get("/metrics")
async def get_metrics():
    """Get Prometheus-formatted metrics."""
    from fastapi.responses import Response
    metrics_text = generate_prometheus_metrics(bot_manager)
    return Response(content=metrics_text, media_type="text/plain")


@app.get("/metrics/json")
async def get_metrics_json():
    """Get JSON-formatted metrics."""
    return generate_json_metrics(bot_manager)


# Data Collector Endpoints
@app.post("/data-collector/start")
async def start_data_collector(symbols: List[str] = ["QQQ"], bar_size: str = "1Min"):
    """Start background data collection service."""
    global data_collector
    
    if data_collector and data_collector.is_running:
        return {"status": "already_running", "message": "Data collector already running"}
    
    try:
        from services.data_collector import DataCollector
        from core.settings_loader import load_settings
        from pathlib import Path
        
        settings = load_settings()
        cache_path = Path(settings.data.cache.path)
        
        import os
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_SECRET_KEY")
        
        if not api_key or not api_secret:
            raise HTTPException(
                status_code=400,
                detail="Alpaca API keys required. Set ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables."
            )
        
        data_collector = DataCollector(
            symbols=symbols,
            bar_size=bar_size,
            cache_path=cache_path,
            api_key=api_key,
            api_secret=api_secret,
        )
        data_collector.start()
        
        return {
            "status": "started",
            "message": f"Data collector started for symbols: {symbols}",
            "symbols": symbols,
            "bar_size": bar_size,
        }
    except Exception as e:
        logger.error(f"Error starting data collector: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/data-collector/stop")
async def stop_data_collector():
    """Stop background data collection service."""
    global data_collector
    
    if not data_collector:
        return {"status": "not_running", "message": "Data collector not running"}
    
    if not data_collector.is_running:
        return {"status": "already_stopped", "message": "Data collector already stopped"}
    
    data_collector.stop()
    return {"status": "stopped", "message": "Data collector stopped successfully"}


# Challenge Mode Endpoints
challenge_tracker = None  # Global challenge tracker


class ChallengeStartRequest(BaseModel):
    """Request to start challenge mode."""
    initial_capital: float = 1000.0
    target_capital: float = 100000.0
    trading_days: int = 20
    symbols: List[str] = ["BTC/USD"]  # Default to crypto for volatility
    broker_type: str = "alpaca"
    profit_target_pct: float = 12.0
    stop_loss_pct: float = 6.0
    leverage_multiplier: float = 3.0
    max_trades_per_day: int = 5
    # Alpaca credentials
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    base_url: Optional[str] = None  # Override ALPACA_BASE_URL: "https://paper-api.alpaca.markets" or "https://api.alpaca.markets"


@app.post("/challenge/start")
async def start_challenge(request: ChallengeStartRequest):
    """Start 20-day challenge mode ($1K to $100K)."""
    global challenge_tracker, bot_manager
    
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    
    from core.live.challenge_mode import ChallengeConfig, ChallengeTracker
    from core.live.challenge_risk_manager import ChallengeRiskManager, ChallengeRiskConfig
    from core.agents.challenge_agent import ChallengeAgent
    from core.config.asset_profiles import AssetProfileManager, AssetProfile, AssetType
    from core.settings_loader import load_settings
    from core.regime.types import RegimeType
    
    # Create challenge config
    challenge_config = ChallengeConfig(
        initial_capital=request.initial_capital,
        target_capital=request.target_capital,
        trading_days=request.trading_days,
        profit_target_pct=request.profit_target_pct,
        stop_loss_pct=request.stop_loss_pct,
        leverage_multiplier=request.leverage_multiplier,
        max_trades_per_day=request.max_trades_per_day,
    )
    
    # Create challenge tracker
    challenge_tracker = ChallengeTracker(challenge_config)
    challenge_tracker.start()
    
    # Create defensive risk manager
    # Note: These are conservative settings. For testing, you can lower thresholds.
    risk_config = ChallengeRiskConfig(
        max_daily_drawdown_pct=10.0,  # Stop if down 10% in a day
        max_daily_loss_pct=15.0,  # Hard stop at 15%
        min_confidence_for_trade=0.70,  # Lowered to 70% for more trading opportunities (was 0.75)
        min_confidence_for_leverage=0.75,  # Lowered to 75% for leverage (was 0.80)
        allowed_regimes=[RegimeType.TREND, RegimeType.EXPANSION],  # Only trends/expansions
        blocked_regimes=[RegimeType.COMPRESSION],  # Only block compression (allow MR for testing)
        avoid_choppy_hours=False,  # Disabled for testing (can re-enable)
        avoid_weekend_crypto=False,  # Disabled for testing (can re-enable)
        avoid_market_open_close=False,  # Disabled for testing (can re-enable)
        enable_liquidation_cascade_detection=True,
        liquidation_cascade_threshold_pct=-5.0,  # Kill switch if -5% in 5 min
    )
    
    risk_manager = ChallengeRiskManager(risk_config)
    risk_manager.initialize(request.initial_capital)
    
    # Store globally for status endpoint
    global challenge_risk_manager
    challenge_risk_manager = risk_manager
    
    # Create challenge agent for each symbol (with risk manager)
    challenge_agents = []
    for symbol in request.symbols:
        agent = ChallengeAgent(
            symbol=symbol,
            config={
                "min_confidence": 0.75,  # Higher threshold
                "profit_target_pct": challenge_config.profit_target_pct,
                "stop_loss_pct": challenge_config.stop_loss_pct,
                "leverage_multiplier": challenge_config.leverage_multiplier,
                "max_trades_per_day": challenge_config.max_trades_per_day,
            },
            risk_manager=risk_manager,  # Pass risk manager to agent
        )
        challenge_agents.append(agent)
    
    # Create aggressive asset profiles for challenge mode
    profile_manager = AssetProfileManager()
    challenge_profiles = {}
    for symbol in request.symbols:
        # Detect asset type
        asset_type = profile_manager._detect_asset_type(symbol)
        
        # Create aggressive profile
        profile = AssetProfile(
            symbol=symbol,
            asset_type=asset_type,
            risk_per_trade_pct=50.0,  # Very aggressive - 50% per trade
            take_profit_pct=challenge_config.profit_target_pct,
            stop_loss_pct=challenge_config.stop_loss_pct,
            trailing_stop_pct=2.0,
            min_hold_bars=3,  # Very short holds
            max_hold_bars=100,
            fixed_investment_amount=None,  # Use percentage-based
            exit_on_regime_change=True,
            exit_on_bias_flip=True,
        )
        challenge_profiles[symbol] = profile
    
    # Start live trading with challenge agents and profiles
    from core.live import (
        AlpacaBrokerClient,
        AlpacaDataFeed,
        CryptoDataFeed,
        LiveTradingConfig,
    )
    import os
    
    # Create broker client
    if request.broker_type == "alpaca":
        api_key = request.api_key or os.getenv("ALPACA_API_KEY")
        api_secret = request.api_secret or os.getenv("ALPACA_SECRET_KEY")
        # Use base_url from request, or environment, or default to paper
        base_url = request.base_url or os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
        
        if not api_key or not api_secret:
            raise HTTPException(
                status_code=400,
                detail="Alpaca API credentials required for challenge mode"
            )
        
        broker_client = AlpacaBrokerClient(
            api_key=api_key,
            api_secret=api_secret,
            base_url=base_url,
        )
        is_paper = "paper-api" in base_url
        logger.info(f"Challenge mode Alpaca broker client created (mode: {'paper' if is_paper else 'live'})")
        
        # Create data feed (crypto or equity)
        def is_crypto_symbol(symbol: str) -> bool:
            crypto_pairs = ["BTC", "ETH", "SOL", "AVAX", "MATIC", "LINK", "UNI", "AAVE", "ALGO", "DOGE"]
            return any(crypto in symbol.upper() for crypto in crypto_pairs) or "/USD" in symbol.upper()
        
        has_crypto = any(is_crypto_symbol(s) for s in request.symbols)
        
        if has_crypto:
            data_feed = CryptoDataFeed(
                api_key=api_key,
                api_secret=api_secret,
                base_url=base_url,
                bar_size="1Min",
            )
        else:
            data_feed = AlpacaDataFeed(
                api_key=api_key,
                api_secret=api_secret,
                base_url=base_url,
                bar_size="1Min",
            )
    else:
        raise HTTPException(status_code=400, detail="Challenge mode currently only supports Alpaca")
    
    # Create live trading config with challenge settings
    live_config = LiveTradingConfig(
        symbols=request.symbols,
        fixed_investment_amount=None,  # Use percentage-based sizing
        enable_profit_taking=True,
        asset_profiles=challenge_profiles,
    )
    
    # Replace agents with challenge agents
    # Note: This is a simplified approach - in production, you'd want to mix challenge agents with regular agents
    try:
        bot_manager.start_live_trading(
            symbols=request.symbols,
            broker_client=broker_client,
            data_feed=data_feed,
            config=live_config,
            asset_profiles=challenge_profiles,
        )
        
        # Replace agents with challenge agents (hack - would need proper agent management)
        if bot_manager.live_loop:
            bot_manager.live_loop.agents = challenge_agents
            # Store risk manager reference for capital updates
            bot_manager.live_loop.challenge_risk_manager = risk_manager
        
        return {
            "status": "started",
            "message": f"Challenge mode started: ${request.initial_capital:.2f} → ${request.target_capital:.2f} in {request.trading_days} days",
            "challenge_config": {
                "initial_capital": request.initial_capital,
                "target_capital": request.target_capital,
                "trading_days": request.trading_days,
                "daily_return_target_pct": challenge_config.daily_return_target_pct,
                "profit_target_pct": challenge_config.profit_target_pct,
                "stop_loss_pct": challenge_config.stop_loss_pct,
                "leverage_multiplier": challenge_config.leverage_multiplier,
            }
        }
    except Exception as e:
        logger.error(f"Error starting challenge mode: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/challenge/status")
async def get_challenge_status():
    """Get challenge mode status and progress."""
    global challenge_tracker, challenge_risk_manager
    
    if not challenge_tracker:
        return {
            "status": "not_started",
            "message": "Challenge mode not started"
        }
    
    # Sync tracker with risk manager
    if challenge_risk_manager:
        challenge_tracker.sync_with_risk_manager(challenge_risk_manager)
    
    progress = challenge_tracker.get_progress()
    
    # Add risk manager status
    risk_status = {}
    if challenge_risk_manager:
        risk_status = challenge_risk_manager.get_risk_status()
        # Update tracker stats from risk manager
        progress["trades_today"] = risk_status.get("trades_today", 0)
    
    return {
        **progress,
        "risk_status": risk_status,
    }


# Options Trading Endpoints
@app.post("/options/start")
async def start_options_trading(request: dict):
    """Start options trading for a specific underlying."""
    global bot_manager
    
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    
    from core.live.options_data_feed import OptionsDataFeed
    from core.live.options_broker_client import OptionsBrokerClient
    from core.agents.options_agent import OptionsAgent
    import os
    
    underlying_symbol = request.get("underlying_symbol", "SPY")
    option_type = request.get("option_type", "put")  # "put" or "call"
    strike = request.get("strike")
    expiration = request.get("expiration")
    
    # Get Alpaca credentials
    api_key = os.getenv("ALPACA_API_KEY")
    api_secret = os.getenv("ALPACA_SECRET_KEY")
    base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
    
    if not api_key or not api_secret:
        raise HTTPException(
            status_code=400,
            detail="Alpaca API credentials required for options trading"
        )
    
    # Create options data feed
    options_feed = OptionsDataFeed(
        api_key=api_key,
        api_secret=api_secret,
        base_url=base_url,
    )
    
    if not options_feed.connect():
        raise HTTPException(status_code=500, detail="Failed to connect to Alpaca options API")
    
    # Create options broker client
    options_broker = OptionsBrokerClient(
        api_key=api_key,
        api_secret=api_secret,
        base_url=base_url,
    )
    
    # Get testing mode from request or default to False
    testing_mode = request.get("testing_mode", False)
    
    # Create option risk profile
    from core.config.asset_profiles import OptionRiskProfile
    option_risk_profile = OptionRiskProfile(
        testing_mode=testing_mode,
        max_spread_pct=20.0 if testing_mode else 10.0,
        min_open_interest=10 if testing_mode else 100,
        min_volume=1 if testing_mode else 10,
        min_iv_percentile=0.0 if testing_mode else 30.0,
        max_iv_percentile=100.0 if testing_mode else 90.0,
        min_dte_for_entry=3 if testing_mode else 7,
        max_dte_for_entry=60 if testing_mode else 45,
    )
    
    # Create options agent
    options_agent = OptionsAgent(
        symbol=underlying_symbol,
        config={
            "min_confidence": 0.70,
            "min_iv_percentile": option_risk_profile.min_iv_percentile,
            "max_iv_percentile": option_risk_profile.max_iv_percentile,
            "min_dte": option_risk_profile.min_dte_for_entry,
            "max_dte": option_risk_profile.max_dte_for_entry,
            "target_delta": -0.30 if option_type == "put" else 0.30,
        },
        options_data_feed=options_feed,
        option_risk_profile=option_risk_profile,
    )
    
    # Start regular trading with options agent
    # Note: This integrates options agent into regular trading loop
    try:
        bot_manager.start_live_trading(
            symbols=[underlying_symbol],
            broker_client=options_broker,
            data_feed=options_feed,  # Use options feed (which also handles underlying)
            config=None,  # Use default config
        )
        
        # Add options agent to the trading loop
        if bot_manager.live_loop:
            # Get existing agents to pass signals to options agent
            existing_agents = bot_manager.live_loop.agents
            
            # Find trend, mean reversion, and volatility agents
            trend_agent = next((a for a in existing_agents if 'trend' in a.name.lower()), None)
            mr_agent = next((a for a in existing_agents if 'mean' in a.name.lower() or 'reversion' in a.name.lower()), None)
            vol_agent = next((a for a in existing_agents if 'volatility' in a.name.lower() or 'vol' in a.name.lower()), None)
            
            # Update options agent with agent signals (will be updated each bar)
            # For now, we'll pass None and update in scheduler
            options_agent.trend_agent_signal = None  # Will be updated in scheduler
            options_agent.mean_reversion_agent_signal = None
            options_agent.volatility_agent_signal = None
            
            # Add options agent to existing agents
            bot_manager.live_loop.agents.append(options_agent)
            logger.info(f"Added OptionsAgent to trading loop. Total agents: {len(bot_manager.live_loop.agents)}")
        
        return {
            "status": "started",
            "underlying_symbol": underlying_symbol,
            "option_type": option_type,
            "testing_mode": testing_mode,
            "message": f"Options trading started (testing_mode={testing_mode})",
        }
    except Exception as e:
        logger.error(f"Failed to start options trading: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/options/positions")
async def get_options_positions():
    """Get current options positions (single-leg and multi-leg)."""
    global bot_manager
    
    if not bot_manager or not bot_manager.live_loop:
        return {"positions": [], "multi_leg_positions": []}
    
    # Get single-leg positions from portfolio
    single_leg_positions = []
    multi_leg_positions = []
    
    if hasattr(bot_manager.live_loop, 'options_portfolio'):
        portfolio = bot_manager.live_loop.options_portfolio
        single_leg_positions = portfolio.get_all_positions()
        multi_leg_positions = portfolio.get_all_multi_leg_positions()
    
    # Also check broker for real positions
    broker_positions = []
    if hasattr(bot_manager.live_loop.executor, "broker_client"):
        broker = bot_manager.live_loop.executor.broker_client
        if hasattr(broker, "get_options_positions"):
            broker_positions = broker.get_options_positions()
    
    return {
        "positions": [
            {
                "symbol": pos.symbol,
                "option_symbol": pos.option_symbol,
                "option_type": pos.option_type,
                "strike": pos.strike,
                "quantity": pos.quantity,
                "entry_price": pos.entry_price,
                "current_price": pos.current_price,
                "unrealized_pnl": pos.unrealized_pnl,
                "delta": pos.delta,
                "theta": pos.theta,
                "iv": pos.iv,
                "days_to_expiry": pos.days_to_expiry,
            }
            for pos in single_leg_positions
        ],
        "multi_leg_positions": [
            {
                "multi_leg_id": ml_pos.multi_leg_id,
                "symbol": ml_pos.symbol,
                "trade_type": ml_pos.trade_type,
                "direction": ml_pos.direction,
                "call_strike": ml_pos.call_strike,
                "put_strike": ml_pos.put_strike,
                "call_quantity": ml_pos.call_quantity,
                "put_quantity": ml_pos.put_quantity,
                "call_entry_price": ml_pos.call_entry_price,
                "put_entry_price": ml_pos.put_entry_price,
                "call_current_price": ml_pos.call_current_price,
                "put_current_price": ml_pos.put_current_price,
                "net_premium": ml_pos.net_premium,
                "combined_unrealized_pnl": ml_pos.combined_unrealized_pnl,
                "both_legs_filled": ml_pos.both_legs_filled,
                "entry_time": ml_pos.entry_time.isoformat(),
                "days_to_expiry": ml_pos.days_to_expiry,
                "call_fill_status": ml_pos.call_fill.status if ml_pos.call_fill else "pending",
                "put_fill_status": ml_pos.put_fill.status if ml_pos.put_fill else "pending",
            }
            for ml_pos in multi_leg_positions
        ],
        "broker_positions": [
            {
                "symbol": p.symbol,
                "quantity": p.quantity,
                "avg_entry_price": p.avg_entry_price,
                "current_price": p.current_price,
                "market_value": p.market_value,
            }
            for p in broker_positions
        ]
    }


@app.post("/options/close")
async def close_options_position(request: dict):
    """Close an options position."""
    global bot_manager
    
    if not bot_manager or not bot_manager.live_loop:
        raise HTTPException(status_code=503, detail="Trading not active")
    
    option_symbol = request.get("option_symbol")
    quantity = request.get("quantity", 1)
    
    if not option_symbol:
        raise HTTPException(status_code=400, detail="option_symbol required")
    
    # Close position via broker
    if hasattr(bot_manager.live_loop.executor, "broker_client"):
        broker = bot_manager.live_loop.executor.broker_client
        if hasattr(broker, "close_options_position"):
            success = broker.close_options_position(option_symbol, quantity)
            if success:
                return {"status": "closed", "option_symbol": option_symbol}
            else:
                raise HTTPException(status_code=500, detail="Failed to close position")
    
    raise HTTPException(status_code=400, detail="Options broker not available")


@app.post("/challenge/stop")
async def stop_challenge():
    """Stop challenge mode."""
    global challenge_tracker, bot_manager
    
    if not challenge_tracker:
        return {"status": "not_running", "message": "Challenge mode not running"}
    
    if bot_manager and bot_manager.live_loop:
        bot_manager.stop_live_trading()
    
    progress = challenge_tracker.get_progress()
    challenge_tracker = None
    
    return {
        "status": "stopped",
        "message": "Challenge mode stopped",
        "final_progress": progress
    }


# Options chain and quotes preview endpoints
@app.get("/options/chain")
async def get_options_chain(
    symbol: str,
    expiration: Optional[str] = None,
    option_type: Optional[str] = None,
):
    """Get options chain for preview/debugging."""
    global bot_manager
    
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    
    from core.live.options_data_feed import OptionsDataFeed
    import os
    
    api_key = os.getenv("ALPACA_API_KEY")
    api_secret = os.getenv("ALPACA_SECRET_KEY")
    base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
    
    if not api_key or not api_secret:
        raise HTTPException(status_code=400, detail="Alpaca API credentials required")
    
    feed = OptionsDataFeed(api_key=api_key, api_secret=api_secret, base_url=base_url)
    if not feed.connect():
        raise HTTPException(status_code=500, detail="Failed to connect to Alpaca")
    
    chain = feed.get_options_chain(
        underlying_symbol=symbol,
        expiration_date=expiration,
        option_type=option_type,
    )
    
    return {"symbol": symbol, "contracts": chain, "count": len(chain)}


@app.post("/data/collector/start")
async def start_data_collector(request: dict):
    """Start data collector service to gather market data for offline use."""
    from scripts.start_data_collector import DataCollector
    import threading
    
    symbols = request.get("symbols", ["SPY", "QQQ"])
    duration_hours = request.get("duration_hours", 24)
    
    def run_collector():
        try:
            collector = DataCollector(symbols=symbols, interval_seconds=60)
            collector.start(duration_hours=duration_hours)
        except Exception as e:
            logger.error(f"Data collector failed: {e}", exc_info=True)
    
    # Start collector in background thread
    thread = threading.Thread(target=run_collector, daemon=True)
    thread.start()
    
    return {
        "status": "started",
        "symbols": symbols,
        "duration_hours": duration_hours,
        "message": f"Data collector started for {duration_hours} hours"
    }


@app.get("/data/collector/status")
async def get_data_collector_status():
    """Get data collector status and cached data info."""
    from core.cache.bar_cache import BarCache
    from pathlib import Path
    
    cache = BarCache()
    cache_dir = Path("cache/bars")
    
    # Count cached files
    cached_files = list(cache_dir.glob("*.parquet")) if cache_dir.exists() else []
    
    # Get symbols from filenames
    symbols = set()
    for file in cached_files:
        # Extract symbol from filename (e.g., SPY_1min_2025-01-15.parquet)
        parts = file.stem.split("_")
        if len(parts) > 0:
            symbols.add(parts[0])
    
    return {
        "status": "active" if cached_files else "inactive",
        "cached_files": len(cached_files),
        "symbols": sorted(list(symbols)),
        "cache_directory": str(cache_dir),
    }


@app.post("/options/testing_mode")
async def set_options_testing_mode(request: dict):
    """Toggle options testing mode on/off."""
    testing_mode = request.get("enabled", False)
    
    # Store testing mode in a global or config
    # For now, return the setting
    return {
        "testing_mode": testing_mode,
        "message": f"Testing mode {'enabled' if testing_mode else 'disabled'}. "
                   f"Restart options trading to apply changes.",
        "note": "Testing mode uses relaxed filters: min_OI=10, min_volume=1, max_spread=20%, no IV filter, 1-of-3 agent alignment"
    }


@app.post("/options/force_buy")
async def force_buy_option(request: dict):
    """
    Force buy an option contract (bypasses all filters for testing).
    
    This is a debug endpoint to test broker connectivity and order execution.
    It works independently and doesn't require live_loop to be active.
    """
    global bot_manager
    
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    
    from core.live.options_broker_client import OptionsBrokerClient
    from core.live.types import OrderSide, OrderType
    import os
    
    option_symbol = request.get("option_symbol")
    quantity = request.get("qty", 1)
    limit_price = request.get("limit_price")
    
    if not option_symbol:
        raise HTTPException(status_code=400, detail="option_symbol required")
    
    api_key = os.getenv("ALPACA_API_KEY")
    api_secret = os.getenv("ALPACA_SECRET_KEY")
    base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
    
    if not api_key or not api_secret:
        raise HTTPException(status_code=400, detail="Alpaca API credentials required")
    
    # Create options broker client
    options_broker = OptionsBrokerClient(
        api_key=api_key,
        api_secret=api_secret,
        base_url=base_url,
    )
    
    # Determine order type
    order_type = OrderType.LIMIT if limit_price else OrderType.MARKET
    
    try:
        # Submit order
        order = options_broker.submit_options_order(
            option_symbol=option_symbol,
            side=OrderSide.BUY,
            quantity=int(quantity),
            order_type=order_type,
            limit_price=limit_price,
        )
        
        return {
            "status": "submitted",
            "order_id": order.order_id,
            "option_symbol": option_symbol,
            "quantity": quantity,
            "order_type": order_type.value,
            "limit_price": limit_price,
            "message": "Order submitted successfully (bypassed all filters)",
        }
    except Exception as e:
        logger.error(f"Force buy failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Order submission failed: {str(e)}")


@app.get("/options/quote")
async def get_option_quote(option_symbol: str):
    """Get option quote and Greeks for preview/debugging."""
    global bot_manager
    
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    
    from core.live.options_data_feed import OptionsDataFeed
    import os
    
    api_key = os.getenv("ALPACA_API_KEY")
    api_secret = os.getenv("ALPACA_SECRET_KEY")
    base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
    
    if not api_key or not api_secret:
        raise HTTPException(status_code=400, detail="Alpaca API credentials required")
    
    feed = OptionsDataFeed(api_key=api_key, api_secret=api_secret, base_url=base_url)
    if not feed.connect():
        raise HTTPException(status_code=500, detail="Failed to connect to Alpaca")
    
    quote = feed.get_option_quote(option_symbol)
    greeks = feed.get_option_greeks(option_symbol)
    
    return {
        "option_symbol": option_symbol,
        "quote": quote,
        "greeks": greeks,
    }


@app.get("/data-collector/status")
async def get_data_collector_status():
    """Get data collector status."""
    global data_collector
    
    if not data_collector:
        return {
            "status": "not_initialized",
            "is_running": False,
        }
    
    return data_collector.get_status()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

