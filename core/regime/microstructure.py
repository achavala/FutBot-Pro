"""Market Microstructure - Singleton for storing real-time market microstructure data."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional


class MarketMicrostructure:
    """
    Singleton class for storing and accessing market microstructure data.
    
    Stores GEX (Gamma Exposure) data and other microstructure indicators
    that are updated in real-time during trading.
    """
    
    _instance: Optional[MarketMicrostructure] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.data: Dict[str, Dict] = {}
        return cls._instance
    
    def update_gex(self, symbol: str, gex_data: Dict) -> None:
        """
        Update GEX data for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'SPY', 'QQQ')
            gex_data: Dict with gex_regime, gex_strength, total_gex_dollar, gex_coverage
        """
        self.data[symbol] = {
            **self.data.get(symbol, {}),
            **gex_data,
            'gex_updated_at': datetime.now().isoformat()
        }
    
    def get(self, symbol: str) -> Dict:
        """
        Get microstructure data for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dict with GEX data, defaults to NEUTRAL if not available
        """
        return self.data.get(symbol, {
            'gex_regime': 'NEUTRAL',
            'gex_strength': 0.0,
            'total_gex_dollar': 0.0,
            'gex_coverage': 0
        })
    
    def get_gex(self, symbol: str) -> Dict:
        """
        Get GEX data specifically for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dict with gex_regime, gex_strength, total_gex_dollar, gex_coverage
        """
        data = self.get(symbol)
        return {
            'gex_regime': data.get('gex_regime', 'NEUTRAL'),
            'gex_strength': data.get('gex_strength', 0.0),
            'total_gex_dollar': data.get('total_gex_dollar', 0.0),
            'gex_coverage': data.get('gex_coverage', 0)
        }
    
    def clear(self) -> None:
        """Clear all microstructure data (useful for testing or reset)."""
        self.data.clear()


