"""Options data feed for Alpaca options trading."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd

from core.live.data_feed import BaseDataFeed
from core.live.types import Bar

logger = logging.getLogger(__name__)


class OptionsDataFeed(BaseDataFeed):
    """Data feed for options trading via Alpaca."""
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://paper-api.alpaca.markets",
    ):
        super().__init__()
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url  # Trading API base URL
        # Options data API uses different base URL
        self.data_base_url = "https://data.alpaca.markets/v1beta1"
        self.underlying_symbol: Optional[str] = None
        self.options_client = None
        self.market_data_client = None
        
    def connect(self) -> bool:
        """Connect to Alpaca options API."""
        try:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.requests import StockBarsRequest
            from alpaca.trading.client import TradingClient
            from alpaca.data import TimeFrame
            
            # For now, we'll use stock data for underlying
            # Alpaca options API may require different client
            # StockHistoricalDataClient doesn't accept base_url, use url_override instead
            self.market_data_client = StockHistoricalDataClient(
                api_key=self.api_key,
                secret_key=self.api_secret,
                url_override=self.base_url if self.base_url != "https://paper-api.alpaca.markets" else None,
            )
            
            # TradingClient doesn't accept base_url, use url_override instead
            self.trading_client = TradingClient(
                api_key=self.api_key,
                secret_key=self.api_secret,
                url_override=self.base_url if self.base_url != "https://paper-api.alpaca.markets" else None,
            )
            
            self.connected = True
            logger.info("Connected to Alpaca for options trading")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Alpaca options API: {e}")
            self.connected = False
            return False
    
    def subscribe(self, symbols: List[str], preload_bars: int = 60) -> bool:
        """Subscribe to underlying stock symbols for options trading."""
        if not self.connected:
            return False
        
        # For options, we subscribe to the underlying stock
        # Options chain will be fetched separately
        self.underlying_symbol = symbols[0] if symbols else None
        self.symbols = symbols
        logger.info(f"Subscribed to underlying: {self.underlying_symbol}")
        return True
    
    def get_next_bar(self, symbol: str, timeout: float = 5.0) -> Optional[Bar]:
        """Get next bar for underlying stock."""
        # This would get stock bars for the underlying
        # Options pricing would be fetched separately
        return None
    
    def get_options_chain(
        self,
        underlying_symbol: str,
        expiration_date: Optional[str] = None,
        option_type: Optional[str] = None,  # "call" or "put"
    ) -> List[Dict]:
        """
        Get options chain for underlying symbol.
        
        Tries Polygon.io first (more reliable), then falls back to Alpaca API.
        
        Args:
            underlying_symbol: Stock symbol (e.g., "SPY")
            expiration_date: Expiration date (YYYY-MM-DD) or None for all
            option_type: "call", "put", or None for both
        
        Returns:
            List of option contracts with symbol, strike, expiration, type, etc.
        """
        if not self.connected:
            logger.warning("OptionsDataFeed not connected")
            return []
        
        # Try Polygon.io first (more reliable for options data)
        contracts = self._get_options_chain_polygon(underlying_symbol, expiration_date, option_type)
        if contracts:
            logger.info(f"Fetched {len(contracts)} option contracts from Polygon for {underlying_symbol}")
            return contracts
        
        # Fallback to Alpaca API (if available)
        contracts = self._get_options_chain_alpaca(underlying_symbol, expiration_date, option_type)
        if contracts:
            logger.info(f"Fetched {len(contracts)} option contracts from Alpaca for {underlying_symbol}")
            return contracts
        
        logger.warning(f"No options contracts found for {underlying_symbol} (tried Polygon and Alpaca)")
        return []
    
    def _get_options_chain_polygon(
        self,
        underlying_symbol: str,
        expiration_date: Optional[str] = None,
        option_type: Optional[str] = None,
    ) -> List[Dict]:
        """Get options chain from Polygon.io."""
        try:
            from core.settings_loader import load_settings
            
            settings = load_settings()
            if not settings.polygon.api_key or settings.polygon.api_key == "YOUR_POLYGON_KEY":
                logger.debug("Polygon API key not configured")
                return []
            
            import requests
            
            # Try contracts endpoint first (has all contracts, not just active)
            # Fallback to snapshot if contracts endpoint doesn't work
            url = f"https://api.polygon.io/v3/reference/options/contracts"
            params = {
                "apiKey": settings.polygon.api_key,
                "underlying_ticker": underlying_symbol.upper(),
                "limit": 1000,  # Get up to 1000 contracts
            }
            
            # Filter by option type if specified
            if option_type:
                params["contract_type"] = option_type.lower()
            
            # Filter by expiration if specified
            if expiration_date:
                params["expiration_date"] = expiration_date
            
            response = requests.get(url, params=params, timeout=30)
            
            # If contracts endpoint works, use it
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                
                if results:
                    # Format contracts from contracts endpoint
                    formatted = []
                    for result in results:
                        ticker = result.get("ticker", "")
                        # Remove "O:" prefix if present
                        if ticker.startswith("O:"):
                            ticker = ticker[2:]
                        
                        contract_type = result.get("contract_type", "").lower()
                        strike = result.get("strike_price")
                        exp_date = result.get("expiration_date")
                        
                        try:
                            strike_price = float(strike) if strike else 0.0
                        except (ValueError, TypeError):
                            strike_price = 0.0
                        
                        formatted.append({
                            "symbol": ticker,
                            "underlying_symbol": underlying_symbol.upper(),
                            "type": contract_type,
                            "strike_price": strike_price,
                            "expiration_date": exp_date,
                            "root_symbol": underlying_symbol.upper(),
                            "id": ticker,
                        })
                    
                    return formatted
            
            # Fallback to snapshot endpoint (shows active contracts only)
            url = f"https://api.polygon.io/v3/snapshot/options/{underlying_symbol.upper()}"
            params = {
                "apiKey": settings.polygon.api_key,
            }
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                
                formatted = []
                for result in results:
                    # Polygon response structure:
                    # result = {
                    #   "details": {"ticker": "O:SPY251126C00500000", "contract_type": "call", ...},
                    #   "greeks": {...},
                    #   "day": {...},
                    #   ...
                    # }
                    details = result.get("details", {})
                    if not details:
                        continue
                    
                    # Ticker is in details.ticker (e.g., "O:SPY251126C00500000")
                    ticker = details.get("ticker", "")
                    if not ticker:
                        continue
                    
                    # Remove "O:" prefix if present (Polygon format)
                    if ticker.startswith("O:"):
                        ticker = ticker[2:]
                    
                    contract_type = details.get("contract_type", "").lower()
                    
                    # Filter by option type if specified
                    if option_type and contract_type != option_type.lower():
                        continue
                    
                    # Filter by expiration if specified
                    exp_date = details.get("expiration_date") or details.get("expiry_date")
                    if expiration_date and exp_date and exp_date != expiration_date:
                        continue
                    
                    strike = details.get("strike_price") or details.get("strike")
                    try:
                        strike_price = float(strike) if strike else 0.0
                    except (ValueError, TypeError):
                        strike_price = 0.0
                    
                    formatted.append({
                        "symbol": ticker,  # e.g., "SPY251126C00500000"
                        "underlying_symbol": underlying_symbol.upper(),
                        "type": contract_type,  # "call" or "put"
                        "strike_price": strike_price,
                        "expiration_date": exp_date,
                        "root_symbol": underlying_symbol.upper(),
                        "id": ticker,
                    })
                
                return formatted
            else:
                logger.debug(f"Polygon options API returned {response.status_code}: {response.text[:200]}")
                return []
        except Exception as e:
            logger.debug(f"Polygon options chain fetch failed: {e}")
            return []
    
    def _get_options_chain_alpaca(
        self,
        underlying_symbol: str,
        expiration_date: Optional[str] = None,
        option_type: Optional[str] = None,
    ) -> List[Dict]:
        """Get options chain from Alpaca API (if available)."""
        try:
            import requests
            
            # Alpaca options API endpoint (may return 404 if not available)
            url = f"{self.data_base_url}/options/contracts"
            headers = {
                "APCA-API-KEY-ID": self.api_key,
                "APCA-API-SECRET-KEY": self.api_secret,
            }
            
            params = {
                "underlying_symbols": underlying_symbol.upper(),
            }
            if expiration_date:
                params["expiry_date"] = expiration_date
            if option_type:
                params["type"] = option_type
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                batch = data.get("contracts", [])
                
                # Handle pagination
                contracts = batch[:]
                page_token = data.get("next_page_token")
                
                while page_token:
                    params["page_token"] = page_token
                    response = requests.get(url, headers=headers, params=params, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        contracts.extend(data.get("contracts", []))
                        page_token = data.get("next_page_token")
                    else:
                        break
                
                # Format contracts
                formatted = []
                for c in contracts:
                    formatted.append({
                        "symbol": c.get("symbol"),
                        "underlying_symbol": c.get("underlying_symbol"),
                        "type": c.get("type"),
                        "strike_price": float(c.get("strike_price", 0)),
                        "expiration_date": c.get("expiration_date"),
                        "root_symbol": c.get("root_symbol"),
                        "id": c.get("id"),
                    })
                
                return formatted
            else:
                logger.debug(f"Alpaca options API returned {response.status_code}: {response.text[:200]}")
                return []
        except Exception as e:
            logger.debug(f"Alpaca options chain fetch failed: {e}")
            return []
    
    def get_option_quote(
        self,
        option_symbol: str,
    ) -> Optional[Dict]:
        """
        Get current quote for an option contract.
        
        Uses Alpaca Data API v1beta1: https://data.alpaca.markets/v1beta1/options/quotes/latest
        
        Args:
            option_symbol: Full option symbol (e.g., "SPY251126P00673000")
        
        Returns:
            Dict with bid, ask, last, volume, open_interest, etc.
        """
        if not self.connected:
            return None
        
        try:
            import requests
            
            # Correct Alpaca options quotes endpoint
            url = f"{self.data_base_url}/options/quotes/latest"
            headers = {
                "APCA-API-KEY-ID": self.api_key,
                "APCA-API-SECRET-KEY": self.api_secret,
            }
            
            params = {"symbols": option_symbol}
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                quotes = data.get("quotes", {})
                quote = quotes.get(option_symbol)
                if quote:
                    logger.debug(f"Fetched quote for {option_symbol}: bid={quote.get('bp')}, ask={quote.get('ap')}")
                return quote
            else:
                error_msg = f"Failed to fetch option quote: HTTP {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f" - {error_detail}"
                except:
                    error_msg += f" - {response.text[:500]}"
                logger.warning(error_msg)
                return None
        except Exception as e:
            logger.error(f"Error fetching option quote: {e}", exc_info=True)
            return None
    
    def get_option_greeks(
        self,
        option_symbol: str,
    ) -> Optional[Dict]:
        """
        Get Greeks for an option contract.
        
        Returns:
            Dict with delta, gamma, theta, vega, implied_volatility
        """
        quote = self.get_option_quote(option_symbol)
        if quote:
            return {
                "delta": quote.get("delta"),
                "gamma": quote.get("gamma"),
                "theta": quote.get("theta"),
                "vega": quote.get("vega"),
                "implied_volatility": quote.get("implied_volatility"),
            }
        return None
    
    def close(self) -> None:
        """Close the options data feed."""
        self.connected = False
        self.underlying_symbol = None

