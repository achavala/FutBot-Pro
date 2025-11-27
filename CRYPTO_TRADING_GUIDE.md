# Crypto Trading Guide

This guide explains how to trade Bitcoin (BTC) and other cryptocurrencies using the FutBot trading system.

## Overview

The system now supports crypto trading through Alpaca's crypto API. You can trade:
- **Bitcoin (BTC/USD)**
- **Ethereum (ETH/USD)**
- **Solana (SOL/USD)**
- **And other Alpaca-supported cryptocurrencies**

## Features

✅ **Crypto Data Feed**: Real-time and historical crypto bar data  
✅ **Crypto Trading**: Buy/sell crypto through Alpaca  
✅ **24/7 Trading**: Crypto markets never close  
✅ **Same Strategy**: Uses the same regime-aware trading logic  
✅ **Risk Management**: Same risk controls apply to crypto  

## Setup

### 1. Alpaca Account

1. Sign up at https://alpaca.markets
2. Enable crypto trading in your account settings
3. Get your API keys (same keys work for stocks and crypto)

### 2. Environment Variables

Add to your `.env` file:

```bash
ALPACA_API_KEY=your_api_key
ALPACA_SECRET_KEY=your_secret_key
ALPACA_BASE_URL=https://paper-api.alpaca.markets  # Paper trading
# For live trading: https://api.alpaca.markets
```

### 3. Crypto Symbol Format

Alpaca uses the format: `SYMBOL/USD`

Examples:
- `BTC/USD` - Bitcoin
- `ETH/USD` - Ethereum
- `SOL/USD` - Solana
- `AVAX/USD` - Avalanche
- `MATIC/USD` - Polygon
- `LINK/USD` - Chainlink
- `UNI/USD` - Uniswap
- `AAVE/USD` - Aave
- `ALGO/USD` - Algorand
- `DOGE/USD` - Dogecoin

## Usage

### Start Crypto Trading

**Via API:**
```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["BTC/USD"],
    "broker_type": "alpaca",
    "fixed_investment_amount": 1000
  }'
```

**Trade Multiple Cryptos:**
```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["BTC/USD", "ETH/USD"],
    "broker_type": "alpaca",
    "fixed_investment_amount": 1000
  }'
```

**Mixed Trading (Stocks + Crypto):**
```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["QQQ", "BTC/USD"],
    "broker_type": "alpaca",
    "fixed_investment_amount": 1000
  }'
```

### Automatic Detection

The system automatically detects crypto symbols and uses the appropriate data feed:
- **Crypto symbols** (BTC/USD, ETH/USD, etc.) → Uses `CryptoDataFeed`
- **Stock symbols** (QQQ, SPY, etc.) → Uses `AlpacaDataFeed`

## Trading Logic

The same trading logic applies to crypto:

1. **Regime Classification**: Detects trend, mean-reversion, compression, expansion
2. **Multi-Agent System**: Specialized agents for different market conditions
3. **Risk Management**: Same risk controls (30% profit, 20% stop loss)
4. **Fixed Investment**: $1000 per trade (configurable)

## Crypto-Specific Considerations

### Volatility

Crypto markets are more volatile than stocks:
- Higher price swings
- Faster regime changes
- More frequent trading opportunities

### 24/7 Trading

Unlike stocks (9:30 AM - 4:00 PM ET), crypto trades 24/7:
- No market open/close
- Continuous data collection
- Always-on trading

### Data Collection

The data collector works for crypto too:

```bash
curl -X POST http://localhost:8000/data-collector/start \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["BTC/USD", "ETH/USD"], "bar_size": "1Min"}'
```

## Example Workflow

1. **Start Data Collector** (optional, for offline testing):
   ```bash
   curl -X POST http://localhost:8000/data-collector/start \
     -H "Content-Type: application/json" \
     -d '{"symbols": ["BTC/USD"], "bar_size": "1Min"}'
   ```

2. **Start Trading**:
   ```bash
   curl -X POST http://localhost:8000/live/start \
     -H "Content-Type: application/json" \
     -d '{"symbols": ["BTC/USD"], "broker_type": "alpaca", "fixed_investment_amount": 1000}'
   ```

3. **Monitor**:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/regime
   ```

4. **Check Trades**:
   ```bash
   curl http://localhost:8000/stats
   ```

## Supported Cryptocurrencies

Alpaca supports many cryptocurrencies. Common ones include:

- **BTC/USD** - Bitcoin
- **ETH/USD** - Ethereum
- **SOL/USD** - Solana
- **AVAX/USD** - Avalanche
- **MATIC/USD** - Polygon
- **LINK/USD** - Chainlink
- **UNI/USD** - Uniswap
- **AAVE/USD** - Aave
- **ALGO/USD** - Algorand
- **DOGE/USD** - Dogecoin

Check Alpaca's documentation for the full list: https://alpaca.markets/docs/market-data/crypto-pricing-data/

## Risk Management

The same risk controls apply:

- **30% Profit Target**: Takes profit at 30% gain
- **20% Stop Loss**: Stops loss at 20% loss
- **Trailing Stop**: 1.5% from peak
- **Regime-Based Exits**: Exits on unfavorable regime changes

## Troubleshooting

### "No bars returned for BTC/USD"

- Check if Alpaca account has crypto trading enabled
- Verify API keys are correct
- Ensure symbol format is correct (BTC/USD, not BTC)

### "Crypto trading not available"

- Enable crypto trading in Alpaca account settings
- Check if your account tier supports crypto
- Verify you're using the correct API endpoint

### "Order rejected"

- Check account balance
- Verify symbol is supported
- Check if market is open (crypto is 24/7, but some restrictions may apply)

## Best Practices

1. **Start Small**: Test with paper trading first
2. **Monitor Volatility**: Crypto is more volatile than stocks
3. **Use Stop Losses**: Essential for crypto trading
4. **Diversify**: Don't put all capital in one crypto
5. **24/7 Monitoring**: Consider setting up alerts

## Summary

✅ Crypto trading is now fully integrated  
✅ Supports BTC, ETH, SOL, and more  
✅ Same trading logic and risk management  
✅ 24/7 trading capability  
✅ Automatic symbol detection  

Start trading crypto with the same powerful regime-aware algorithm! 🚀

