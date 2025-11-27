"""Orchestrator for managing data feeds and brokers based on asset profiles."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from core.config.asset_profiles import AssetProfile, AssetProfileManager, AssetType
from core.live.broker_client import AlpacaBrokerClient, BaseBrokerClient, PaperBrokerClient
from core.live.data_feed import BaseDataFeed
from core.live.data_feed_alpaca import AlpacaDataFeed
from core.live.data_feed_crypto import CryptoDataFeed
from core.live.interfaces import Broker, DataFeed

logger = logging.getLogger(__name__)


class FeedBrokerPair:
    """Pair of data feed and broker for a symbol."""
    
    def __init__(self, symbol: str, data_feed: BaseDataFeed, broker: BaseBrokerClient, profile: AssetProfile):
        self.symbol = symbol
        self.data_feed = data_feed
        self.broker = broker
        self.profile = profile


class TradingOrchestrator:
    """Orchestrates data feeds and brokers based on asset profiles."""
    
    def __init__(
        self,
        symbols: List[str],
        asset_profile_manager: AssetProfileManager,
        broker_type: str = "alpaca",
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """
        Initialize orchestrator.
        
        Args:
            symbols: List of symbols to trade
            asset_profile_manager: Asset profile manager
            broker_type: Broker type ("alpaca", "paper", etc.)
            api_key: API key for broker
            api_secret: API secret for broker
            base_url: Base URL for broker API
        """
        self.symbols = symbols
        self.profile_manager = asset_profile_manager
        self.broker_type = broker_type
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        
        # Get profiles for all symbols
        self.profiles: Dict[str, AssetProfile] = {
            symbol: asset_profile_manager.get_profile(symbol) for symbol in symbols
        }
        
        # Group symbols by asset type
        self.equity_symbols = [s for s, p in self.profiles.items() if p.asset_type == AssetType.EQUITY]
        self.crypto_symbols = [s for s, p in self.profiles.items() if p.asset_type == AssetType.CRYPTO]
        
        logger.info(f"Orchestrator initialized: {len(self.equity_symbols)} equity, {len(self.crypto_symbols)} crypto")
    
    def create_broker_client(self) -> BaseBrokerClient:
        """
        Create broker client based on broker type.
        
        Returns:
            Broker client instance
        """
        if self.broker_type == "paper":
            from core.live.broker_client import PaperBrokerClient
            return PaperBrokerClient(initial_cash=100000.0)
        elif self.broker_type == "alpaca":
            if not self.api_key or not self.api_secret:
                raise ValueError("Alpaca API credentials required")
            return AlpacaBrokerClient(
                api_key=self.api_key,
                api_secret=self.api_secret,
                base_url=self.base_url or "https://paper-api.alpaca.markets",
            )
        else:
            raise ValueError(f"Unsupported broker type: {self.broker_type}")
    
    def create_data_feeds(self) -> Dict[str, BaseDataFeed]:
        """
        Create data feeds for symbols based on asset type.
        
        Returns:
            Dictionary mapping symbol -> data feed
        """
        feeds: Dict[str, BaseDataFeed] = {}
        
        # Create equity data feed if we have equity symbols
        if self.equity_symbols:
            if self.broker_type == "alpaca":
                if not self.api_key or not self.api_secret:
                    raise ValueError("Alpaca API credentials required")
                equity_feed = AlpacaDataFeed(
                    api_key=self.api_key,
                    api_secret=self.api_secret,
                    base_url=self.base_url or "https://paper-api.alpaca.markets",
                    bar_size="1Min",
                )
                for symbol in self.equity_symbols:
                    feeds[symbol] = equity_feed
                logger.info(f"Created equity data feed for {len(self.equity_symbols)} symbols")
        
        # Create crypto data feed if we have crypto symbols
        if self.crypto_symbols:
            if self.broker_type == "alpaca":
                if not self.api_key or not self.api_secret:
                    raise ValueError("Alpaca API credentials required")
                crypto_feed = CryptoDataFeed(
                    api_key=self.api_key,
                    api_secret=self.api_secret,
                    base_url=self.base_url or "https://paper-api.alpaca.markets",
                    bar_size="1Min",
                )
                for symbol in self.crypto_symbols:
                    feeds[symbol] = crypto_feed
                logger.info(f"Created crypto data feed for {len(self.crypto_symbols)} symbols")
        
        return feeds
    
    def get_profile(self, symbol: str) -> AssetProfile:
        """Get asset profile for symbol."""
        return self.profiles.get(symbol, self.profile_manager.get_profile(symbol))
    
    def get_asset_type(self, symbol: str) -> AssetType:
        """Get asset type for symbol."""
        return self.get_profile(symbol).asset_type

