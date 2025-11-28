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


# Global bot manager instance (will be initialized by startup)
bot_manager: Optional[BotManager] = None
data_collector = None  # Will be initialized if needed


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup
    global bot_manager
    
    # Initialize bot manager if not already set
    if bot_manager is None:
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
            
            agents = [
                TrendAgent(symbol=symbol),
                MeanReversionAgent(symbol=symbol),
                VolatilityAgent(symbol=symbol),
                FVGAgent(symbol=symbol),
            ]
            
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
            
            logger.info("Bot manager initialized in lifespan startup")
        except Exception as e:
            logger.error(f"Failed to initialize bot manager: {e}", exc_info=True)
            # Continue without bot manager - some endpoints will return errors
    
    yield
    # Shutdown (if needed)


app = FastAPI(
    title="FutBot Trading System API",
    description="Control panel and monitoring API for the regime-aware trading bot",
    version="1.0.0"
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
    version="1.0.0",
    lifespan=lifespan,
)


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
    
    if webull_dashboard.exists():
        html_content = webull_dashboard.read_text(encoding='utf-8')
        return HTMLResponse(content=html_content, media_type="text/html")
    elif modern_dashboard.exists():
        html_content = modern_dashboard.read_text(encoding='utf-8')
        return HTMLResponse(content=html_content, media_type="text/html")
    elif dashboard_path.exists():
        html_content = dashboard_path.read_text(encoding='utf-8')
        return HTMLResponse(content=html_content, media_type="text/html")
    
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
async def dashboard():
    """Serve the dashboard HTML."""
    from pathlib import Path
    # Try modern dashboard first (has latest features), then webull, then fallback
    modern_dashboard = Path(__file__).parent / "dashboard_modern.html"
    webull_dashboard = Path(__file__).parent / "dashboard_webull.html"
    dashboard_path = Path(__file__).parent / "dashboard.html"
    
    if modern_dashboard.exists():
        html_content = modern_dashboard.read_text(encoding='utf-8')
        return HTMLResponse(content=html_content, media_type="text/html")
    elif webull_dashboard.exists():
        html_content = webull_dashboard.read_text(encoding='utf-8')
        return HTMLResponse(content=html_content, media_type="text/html")
    elif dashboard_path.exists():
        html_content = dashboard_path.read_text(encoding='utf-8')
        return HTMLResponse(content=html_content, media_type="text/html")
    raise HTTPException(status_code=404, detail="Dashboard not found")


@app.get("/health", response_model=HealthResponse)
async def get_health():
    """Get bot health status."""
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    health = bot_manager.get_health_status()
    status = "healthy" if health["is_running"] and not health.get("error") else "unhealthy"
    return HealthResponse(status=status, **health)


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
    trade_dicts = [
        {
            "symbol": t.symbol,
            "entry_time": t.entry_time.isoformat(),
            "exit_time": t.exit_time.isoformat(),
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "quantity": t.quantity,
            "pnl": t.pnl,
            "pnl_pct": t.pnl_pct,
            "reason": t.reason,
            "agent": t.agent,
        }
        for t in trades
    ]
    return TradeLogResponse(trades=trade_dicts, total_count=len(trade_dicts))


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
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")

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
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/live/stop")
async def stop_live_trading():
    """Stop live trading."""
    if not bot_manager:
        raise HTTPException(status_code=503, detail="Bot manager not initialized")
    bot_manager.stop_live_trading()
    return {"status": "stopped", "message": "Live trading stopped successfully"}


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
    """Get current options positions."""
    global bot_manager
    
    if not bot_manager or not bot_manager.live_loop:
        return {"positions": []}
    
    # Get options positions from broker
    if hasattr(bot_manager.live_loop.executor, "broker_client"):
        broker = bot_manager.live_loop.executor.broker_client
        if hasattr(broker, "get_options_positions"):
            positions = broker.get_options_positions()
            return {
                "positions": [
                    {
                        "symbol": p.symbol,
                        "quantity": p.quantity,
                        "avg_entry_price": p.avg_entry_price,
                        "current_price": p.current_price,
                        "market_value": p.market_value,
                    }
                    for p in positions
                ]
            }
    
    return {"positions": []}


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

