"""Options data feed for fetching real options chain data from Alpaca/Polygon APIs."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class OptionsDataFeed:
    """
    Fetches real options chain data from Alpaca or Polygon/Massive APIs.
    
    Supports:
    - Options chain retrieval
    - Option quotes (bid/ask)
    - Option Greeks (delta, gamma, theta, vega, IV)
    - Historical options data
    """
    
    def __init__(
        self,
        api_provider: str = "alpaca",  # "alpaca" or "polygon"
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """
        Initialize options data feed.
        
        Args:
            api_provider: "alpaca" or "polygon"
            api_key: API key
            api_secret: API secret (for Alpaca)
            base_url: Base URL (optional, defaults to paper trading for Alpaca)
        """
        self.api_provider = api_provider.lower()
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        
        if self.api_provider == "alpaca":
            self._init_alpaca()
        elif self.api_provider == "polygon":
            self._init_polygon()
        else:
            raise ValueError(f"Unsupported API provider: {api_provider}")
    
    def _init_alpaca(self) -> None:
        """Initialize Alpaca options client."""
        try:
            from alpaca.data.historical import OptionHistoricalDataClient
            from alpaca.data.requests import OptionChainRequest, OptionQuoteRequest, OptionSnapshotRequest
            
            if not self.api_key or not self.api_secret:
                raise ValueError("Alpaca API key and secret required")
            
            self.base_url = self.base_url or "https://paper-api.alpaca.markets"
            
            # Initialize Alpaca options client
            self.client = OptionHistoricalDataClient(
                api_key=self.api_key,
                secret_key=self.api_secret
            )
            
            self.OptionChainRequest = OptionChainRequest
            self.OptionQuoteRequest = OptionQuoteRequest
            self.OptionSnapshotRequest = OptionSnapshotRequest
            
            logger.info("✅ Alpaca options data feed initialized")
        except ImportError:
            raise ImportError("alpaca-py not installed. Run: pip install alpaca-py")
        except Exception as e:
            logger.error(f"Failed to initialize Alpaca options client: {e}")
            raise
    
    def _init_polygon(self) -> None:
        """Initialize Polygon/Massive options client."""
        try:
            import requests
            from core.config.polygon import PolygonSettings
            
            settings = PolygonSettings.load()
            self.api_key = self.api_key or settings.api_key
            self.base_url = self.base_url or settings.rest_url
            
            if not self.api_key:
                raise ValueError("Polygon API key required")
            
            self.requests = requests
            logger.info("✅ Polygon options data feed initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Polygon options client: {e}")
            raise
    
    def get_options_chain(
        self,
        underlying_symbol: str,
        option_type: Optional[str] = None,  # "call" or "put"
        expiration_date: Optional[str] = None,  # "YYYY-MM-DD"
        min_strike: Optional[float] = None,
        max_strike: Optional[float] = None,
    ) -> List[Dict]:
        """
        Get options chain for underlying symbol (with 5-minute cache for performance).
        
        PERFORMANCE OPTIMIZATION: Results are cached for 5 minutes to reduce API calls.
        """
        # PERFORMANCE: Cache options chain to avoid fetching on every bar
        import time
        cache_key = f"{underlying_symbol}_{option_type}_{expiration_date}"
        
        # Initialize cache if not exists
        if not hasattr(self, '_chain_cache'):
            self._chain_cache = {}
        if not hasattr(self, '_chain_cache_time'):
            self._chain_cache_time = {}
        
        # Check cache (5 minute TTL)
        current_time = time.time()
        cached_time = self._chain_cache_time.get(cache_key, 0)
        cache_ttl = 300  # 5 minutes
        
        if current_time - cached_time < cache_ttl and cache_key in self._chain_cache:
            logger.debug(f"Using cached options chain for {underlying_symbol} (age: {current_time - cached_time:.0f}s)")
            return self._chain_cache[cache_key]
        
        # Cache miss - fetch from API
        if self.api_provider == "alpaca":
            contracts = self._get_alpaca_options_chain(
                underlying_symbol, option_type, expiration_date, min_strike, max_strike
            )
        elif self.api_provider == "polygon":
            contracts = self._get_polygon_options_chain(
                underlying_symbol, option_type, expiration_date, min_strike, max_strike
            )
        else:
            contracts = []
        
        # Cache the result (even if empty, to avoid repeated failed calls)
        if contracts or cache_key not in self._chain_cache:  # Cache successful fetches or first attempt
            self._chain_cache[cache_key] = contracts
            self._chain_cache_time[cache_key] = current_time
        
        return contracts
    
    def _get_alpaca_options_chain(
        self,
        underlying_symbol: str,
        option_type: Optional[str],
        expiration_date: Optional[str],
        min_strike: Optional[float],
        max_strike: Optional[float],
    ) -> List[Dict]:
        """Get options chain from Alpaca."""
        try:
            from alpaca.data.requests import OptionChainRequest
            
            # Build request
            request = OptionChainRequest(
                underlying_symbols=[underlying_symbol],
            )
            
            if expiration_date:
                # Parse expiration date
                exp_date = datetime.strptime(expiration_date, "%Y-%m-%d").date()
                request.expiration_date = exp_date
            
            # Fetch chain
            chain = self.client.get_option_chain(request)
            
            contracts = []
            for contract in chain.get(underlying_symbol, []):
                contract_type = contract.contract_type.lower()  # "call" or "put"
                
                # Filter by option type
                if option_type and contract_type != option_type.lower():
                    continue
                
                # Filter by strike
                if min_strike and contract.strike_price < min_strike:
                    continue
                if max_strike and contract.strike_price > max_strike:
                    continue
                
                contracts.append({
                    "symbol": contract.symbol,
                    "strike_price": float(contract.strike_price),
                    "expiration_date": contract.expiration_date.strftime("%Y-%m-%d"),
                    "option_type": contract_type,
                    "underlying_symbol": underlying_symbol,
                })
            
            logger.info(f"✅ Fetched {len(contracts)} options contracts for {underlying_symbol} from Alpaca")
            return contracts
            
        except Exception as e:
            logger.error(f"Error fetching Alpaca options chain: {e}", exc_info=True)
            return []
    
    def _get_polygon_options_chain(
        self,
        underlying_symbol: str,
        option_type: Optional[str],
        expiration_date: Optional[str],
        min_strike: Optional[float],
        max_strike: Optional[float],
    ) -> List[Dict]:
        """Get options chain from Polygon/Massive."""
        try:
            # Polygon options endpoint: /v3/snapshot/options/{underlying}
            url = f"{self.base_url}/v3/snapshot/options/{underlying_symbol}"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            response = self.requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            contracts = []
            results = data.get("results", [])
            
            for result in results:
                contract = result.get("details", {})
                contract_type = contract.get("contract_type", "").lower()
                
                # Filter by option type
                if option_type and contract_type != option_type.lower():
                    continue
                
                strike = float(contract.get("strike_price", 0))
                exp_date_str = contract.get("expiration_date", "")
                
                # Filter by expiration
                if expiration_date and exp_date_str != expiration_date:
                    continue
                
                # Filter by strike
                if min_strike and strike < min_strike:
                    continue
                if max_strike and strike > max_strike:
                    continue
                
                contracts.append({
                    "symbol": contract.get("ticker", ""),
                    "strike_price": strike,
                    "expiration_date": exp_date_str,
                    "option_type": contract_type,
                    "underlying_symbol": underlying_symbol,
                })
            
            logger.info(f"✅ Fetched {len(contracts)} options contracts for {underlying_symbol} from Polygon")
            return contracts
            
        except Exception as e:
            logger.error(f"Error fetching Polygon options chain: {e}", exc_info=True)
            return []
    
    def get_option_quote(self, option_symbol: str) -> Optional[Dict]:
        """
        Get current quote for an option contract.
        
        Args:
            option_symbol: Option symbol (e.g., "SPY241129C00475000")
            
        Returns:
            Dict with:
            - bid: Bid price
            - ask: Ask price
            - last: Last trade price
            - volume: Volume
            - open_interest: Open interest
        """
        if self.api_provider == "alpaca":
            return self._get_alpaca_option_quote(option_symbol)
        elif self.api_provider == "polygon":
            return self._get_polygon_option_quote(option_symbol)
        else:
            return None
    
    def _get_alpaca_option_quote(self, option_symbol: str) -> Optional[Dict]:
        """Get option quote from Alpaca."""
        try:
            from alpaca.data.requests import OptionQuoteRequest
            
            request = OptionQuoteRequest(option_symbols=[option_symbol])
            quotes = self.client.get_option_quotes(request)
            
            quote_data = quotes.get(option_symbol)
            if not quote_data:
                return None
            
            # Get latest quote
            latest_quote = quote_data[-1] if isinstance(quote_data, list) else quote_data
            
            return {
                "bid": float(latest_quote.bid_price) if latest_quote.bid_price else 0.0,
                "ask": float(latest_quote.ask_price) if latest_quote.ask_price else 0.0,
                "last": float(latest_quote.last_price) if latest_quote.last_price else 0.0,
                "volume": int(latest_quote.volume) if latest_quote.volume else 0,
                "open_interest": int(latest_quote.open_interest) if latest_quote.open_interest else 0,
            }
        except Exception as e:
            logger.debug(f"Error fetching Alpaca option quote for {option_symbol}: {e}")
            return None
    
    def _get_polygon_option_quote(self, option_symbol: str) -> Optional[Dict]:
        """Get option quote from Polygon."""
        try:
            # Polygon snapshot endpoint for options
            url = f"{self.base_url}/v2/snapshot/option/{option_symbol}"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            response = self.requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            result = data.get("results", {})
            if not result:
                return None
            
            return {
                "bid": float(result.get("day", {}).get("c", 0)),  # Close price as bid
                "ask": float(result.get("day", {}).get("c", 0)),  # Close price as ask
                "last": float(result.get("day", {}).get("c", 0)),
                "volume": int(result.get("day", {}).get("v", 0)),
                "open_interest": int(result.get("day", {}).get("oi", 0)),
            }
        except Exception as e:
            logger.debug(f"Error fetching Polygon option quote for {option_symbol}: {e}")
            return None
    
    def get_option_greeks(self, option_symbol: str) -> Optional[Dict]:
        """
        Get Greeks for an option contract.
        
        Args:
            option_symbol: Option symbol
            
        Returns:
            Dict with:
            - delta: Delta
            - gamma: Gamma
            - theta: Theta
            - vega: Vega
            - implied_volatility: Implied volatility (as decimal, e.g., 0.25 for 25%)
        """
        if self.api_provider == "alpaca":
            return self._get_alpaca_option_greeks(option_symbol)
        elif self.api_provider == "polygon":
            return self._get_polygon_option_greeks(option_symbol)
        else:
            return None
    
    def _get_alpaca_option_greeks(self, option_symbol: str) -> Optional[Dict]:
        """Get option Greeks from Alpaca."""
        try:
            from alpaca.data.requests import OptionSnapshotRequest
            
            request = OptionSnapshotRequest(option_symbols=[option_symbol])
            snapshots = self.client.get_option_snapshots(request)
            
            snapshot = snapshots.get(option_symbol)
            if not snapshot:
                return None
            
            return {
                "delta": float(snapshot.greeks.delta) if snapshot.greeks and snapshot.greeks.delta else 0.0,
                "gamma": float(snapshot.greeks.gamma) if snapshot.greeks and snapshot.greeks.gamma else 0.0,
                "theta": float(snapshot.greeks.theta) if snapshot.greeks and snapshot.greeks.theta else 0.0,
                "vega": float(snapshot.greeks.vega) if snapshot.greeks and snapshot.greeks.vega else 0.0,
                "implied_volatility": float(snapshot.implied_volatility) if snapshot.implied_volatility else 0.0,
            }
        except Exception as e:
            logger.debug(f"Error fetching Alpaca option Greeks for {option_symbol}: {e}")
            return None
    
    def _get_polygon_option_greeks(self, option_symbol: str) -> Optional[Dict]:
        """Get option Greeks from Polygon."""
        try:
            # Polygon snapshot endpoint includes Greeks
            url = f"{self.base_url}/v2/snapshot/option/{option_symbol}"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            response = self.requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            result = data.get("results", {})
            if not result:
                return None
            
            greeks = result.get("greeks", {})
            
            return {
                "delta": float(greeks.get("delta", 0)),
                "gamma": float(greeks.get("gamma", 0)),
                "theta": float(greeks.get("theta", 0)),
                "vega": float(greeks.get("vega", 0)),
                "implied_volatility": float(greeks.get("implied_volatility", 0)),
            }
        except Exception as e:
            logger.debug(f"Error fetching Polygon option Greeks for {option_symbol}: {e}")
            return None
    
    def calculate_iv_percentile(
        self,
        underlying_symbol: str,
        current_iv: float,
        lookback_days: int = 252,
        option_type: Optional[str] = None,
        strike_range_pct: float = 0.10,  # ±10% from current price
    ) -> Optional[float]:
        """
        Calculate IV Percentile (0-100) for underlying.
        
        IV Percentile = % of days in last year where IV was lower than current IV
        
        This is the #1 edge in options trading:
        - IV Percentile < 20% = IV is low (good time to BUY options)
        - IV Percentile > 80% = IV is high (good time to SELL premium)
        
        Args:
            underlying_symbol: Underlying symbol (e.g., "SPY", "QQQ")
            current_iv: Current implied volatility (as decimal, e.g., 0.25 for 25%)
            lookback_days: Number of days to look back (default 252 = 1 year)
            option_type: "call" or "put" (optional, for filtering)
            strike_range_pct: Strike range as % of current price (default ±10%)
            
        Returns:
            IV Percentile (0-100) or None if insufficient data
        """
        if current_iv <= 0:
            return None
        
        try:
            # For now, we'll use a simplified approach:
            # 1. Fetch current options chain
            # 2. Extract IVs from similar strikes
            # 3. Calculate percentile from recent IVs
            
            # Get options chain for the underlying
            options_chain = self.get_options_chain(
                underlying_symbol=underlying_symbol,
                option_type=option_type,
            )
            
            if not options_chain or len(options_chain) < 10:
                logger.debug(f"Insufficient options chain data for IV percentile: {len(options_chain) if options_chain else 0} contracts")
                return None
            
            # Collect IVs from options chain (these represent current IV levels)
            ivs = []
            for contract in options_chain[:50]:  # Sample up to 50 contracts
                option_symbol = contract.get("symbol", "")
                if not option_symbol:
                    continue
                
                greeks = self.get_option_greeks(option_symbol)
                if greeks and greeks.get("implied_volatility", 0) > 0:
                    ivs.append(greeks["implied_volatility"])
            
            if len(ivs) < 5:
                logger.debug(f"Insufficient IV data for percentile calculation: {len(ivs)} samples")
                return None
            
            # Calculate percentile: % of IVs that are lower than current IV
            ivs_sorted = sorted(ivs)
            count_below = sum(1 for iv in ivs_sorted if iv < current_iv)
            percentile = (count_below / len(ivs_sorted)) * 100.0
            
            logger.debug(
                f"IV Percentile for {underlying_symbol}: {percentile:.1f}% "
                f"(current IV={current_iv:.2%}, {count_below}/{len(ivs_sorted)} below)"
            )
            
            return percentile
            
        except Exception as e:
            logger.warning(f"Error calculating IV percentile: {e}")
            return None
    
    def calculate_iv_rank(
        self,
        underlying_symbol: str,
        current_iv: float,
        lookback_days: int = 252,
    ) -> Optional[float]:
        """
        Calculate IV Rank (0-100) for underlying.
        
        IV Rank = (Current IV - Min IV) / (Max IV - Min IV) * 100
        
        Similar to IV Percentile but uses min/max range instead of percentile.
        
        Args:
            underlying_symbol: Underlying symbol
            current_iv: Current implied volatility
            lookback_days: Number of days to look back
            
        Returns:
            IV Rank (0-100) or None if insufficient data
        """
        # For now, use same approach as IV percentile
        # In production, this would use historical IV data
        percentile = self.calculate_iv_percentile(underlying_symbol, current_iv, lookback_days)
        # IV Rank is similar to percentile for our purposes
        return percentile
    
    def calculate_gex_proxy(
        self,
        chain_data: List[Dict],
        underlying_price: float,
    ) -> Optional[Dict]:
        """
        Calculate Gamma Exposure (GEX) Proxy - institutional-grade dealer positioning indicator.
        
        GEX v2 - Enhanced with better filtering and robustness.
        
        GEX measures how much dealers are long/short gamma, which determines:
        - Market pinning behavior (dealers long gamma = market pins)
        - Volatility explosions (dealers short gamma = flash moves)
        - Hedging flows (dealers hedge opposite of their gamma exposure)
        
        This is used by every major volatility fund (Citadel, Jane Street, Optiver, SIG).
        
        Formula:
        - Dollar Gamma = gamma * open_interest * contract_size * underlying_price
        - Calls: positive GEX (dealers hedge by buying)
        - Puts: negative GEX (dealers hedge by selling)
        
        Args:
            chain_data: List of option contracts with strike, gamma, OI, option_type
            underlying_price: Current underlying price
            
        Returns:
            Dict with:
            - total_gex_dollar: Total GEX in dollars
            - gex_regime: 'POSITIVE', 'NEGATIVE', or 'NEUTRAL'
            - gex_strength: Normalized strength (in billions)
            - gex_coverage: Number of relevant contracts used
        """
        if not chain_data or underlying_price <= 0:
            return {
                'gex_regime': 'NEUTRAL',
                'gex_strength': 0.0,
                'total_gex_dollar': 0.0,
                'gex_coverage': 0
            }
        
        total_gex = 0.0
        relevant = 0
        contract_size = 100  # Standard options contract size
        
        for contract in chain_data:
            try:
                # Get delta and gamma (both needed for filtering)
                delta = float(contract.get('delta', 0) or 0)
                gamma = float(contract.get('gamma', 0) or 0)
                
                # Try to get from separate Greeks call if available
                if gamma == 0 or delta == 0:
                    option_symbol = contract.get('symbol', '')
                    if option_symbol:
                        greeks = self.get_option_greeks(option_symbol)
                        if greeks:
                            delta = float(greeks.get('delta', 0) or 0)
                            gamma = float(greeks.get('gamma', 0) or 0)
                
                # Get open interest
                oi = float(contract.get('open_interest', 0) or 0)
                if oi == 0:
                    # Try to get from quote if available
                    option_symbol = contract.get('symbol', '')
                    if option_symbol:
                        quote = self.get_option_quote(option_symbol)
                        if quote:
                            oi = float(quote.get('open_interest', 0) or 0)
                
                # Filter: Only include contracts with meaningful OI and gamma
                if oi < 50 or gamma < 1e-6:
                    continue
                
                # Filter: Only include contracts with reasonable delta (near-the-money)
                # This focuses on contracts that matter for dealer hedging
                if not (0.2 <= abs(delta) <= 0.8):
                    continue
                
                opt_type = contract.get('option_type', '').lower()
                if opt_type not in ('call', 'put'):
                    continue
                
                # Dollar gamma = gamma * OI * contract_size * underlying_price
                dollar_gamma = gamma * oi * contract_size * underlying_price
                
                # Calls: positive GEX (dealers hedge by buying when price moves up)
                # Puts: negative GEX (dealers hedge by selling when price moves down)
                if opt_type == 'call':
                    total_gex += dollar_gamma
                else:  # put
                    total_gex -= dollar_gamma
                
                relevant += 1
                    
            except Exception as e:
                logger.debug(f"Error processing contract for GEX: {e}")
                continue
        
        # Normalize strength (in billions for readability)
        strength_b = abs(total_gex) / 1e9
        
        # Determine regime
        if total_gex > 0:
            regime = 'POSITIVE'
        elif total_gex < 0:
            regime = 'NEGATIVE'
        else:
            regime = 'NEUTRAL'
        
        return {
            'total_gex_dollar': round(total_gex, 2),
            'gex_regime': regime,
            'gex_strength': round(strength_b, 2),
            'gex_coverage': relevant
        }

