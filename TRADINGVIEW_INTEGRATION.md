# TradingView Chart Integration

## Overview

The FutBot dashboard now includes a **TradingView chart widget** in the Performance Analytics tab, allowing you to visualize real-time price action alongside your trading bot's performance metrics.

## Features

- **Real-time charting** with TradingView's professional charting library
- **Dark theme** matching the FutBot dashboard
- **Technical indicators** pre-loaded:
  - RSI (Relative Strength Index)
  - MACD (Moving Average Convergence Divergence)
  - Volume
- **Symbol switching** - Chart automatically updates when you change the symbol selector
- **Full TradingView features**:
  - Drawing tools
  - Multiple timeframes
  - Additional indicators
  - Chart analysis tools

## How to Use

1. **Navigate to Analytics** → **Performance** tab
2. The TradingView chart will automatically load for the currently selected symbol (SPY or QQQ)
3. **Change symbol**: Use the symbol dropdown in the header - the chart will update automatically
4. **Full-screen mode**: Click the popup button to open the chart in a larger window

## Chart Configuration

The chart is configured with:
- **Timezone**: America/Chicago (CST)
- **Interval**: 1 minute (matches bot's bar interval)
- **Theme**: Dark (matches dashboard)
- **Symbol format**: `NASDAQ:SPY` or `NASDAQ:QQQ`

## Troubleshooting

### Chart not loading?
- Check browser console for errors
- Ensure you have internet connection (TradingView widget loads from CDN)
- Try refreshing the page

### Chart shows wrong symbol?
- The chart syncs with the symbol selector in the header
- If it doesn't update, manually refresh the Performance tab

### Want to add more indicators?
The TradingView widget supports all TradingView indicators. You can modify the `studies` array in `dashboard_modern.html` to add more indicators.

## Technical Details

- **Widget Library**: TradingView's official widget library (tv.js)
- **Container**: `#tradingview-widget` div in Performance tab
- **Auto-load**: Chart loads when Performance tab is opened
- **Symbol sync**: Updates when `simSymbol` dropdown changes

## Future Enhancements

Potential improvements:
- [ ] Add bot trade markers on chart
- [ ] Show entry/exit points visually
- [ ] Add regime indicators overlay
- [ ] Custom TradingView Pine Script integration
- [ ] Multiple chart layouts (side-by-side comparison)


