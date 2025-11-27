# FutBot Dashboard Guide

## Overview

The FutBot Dashboard is a modern, real-time web-based GUI that provides comprehensive monitoring and control of your trading bot.

## Accessing the Dashboard

1. **Start the FastAPI server** (if not already running):
   ```bash
   python main.py --mode api --port 8000
   ```

2. **Open your web browser** and navigate to:
   ```
   http://localhost:8000
   ```
   or
   ```
   http://localhost:8000/dashboard
   ```

## Dashboard Features

### 1. **Header Section**
- **Bot Status Badge**: Shows current state (Running/Stopped/Paused)
- **Control Buttons**:
  - **Start**: Start the trading bot
  - **Stop**: Stop the trading bot
  - **Pause**: Pause the bot (keeps connection alive)
  - **Kill Switch**: Emergency stop that disables all trading

### 2. **System Health Card**
- Overall system status
- Number of bars collected
- Error messages (if any)
- Kill switch status

### 3. **Current Regime Card**
- **Regime Type**: TREND, MEAN_REVERSION, EXPANSION, COMPRESSION
- **Trend Direction**: UP, DOWN, SIDEWAYS
- **Volatility Level**: LOW, MEDIUM, HIGH
- **Market Bias**: BULLISH, BEARISH, NEUTRAL
- **Confidence Score**: Visual bar showing regime confidence (0-100%)

### 4. **Portfolio Stats Card**
- Current capital
- Initial capital
- Total return (percentage)
- Sharpe ratio
- Win rate

### 5. **Risk Management Card**
- Kill switch status
- Daily loss percentage
- Maximum drawdown
- Loss streak count

### 6. **Agent Weights Card**
- List of all trading agents
- Current weight/importance of each agent
- Shows how the system is allocating resources

### 7. **Equity Curve Chart**
- Visual representation of portfolio performance over time
- Real-time updates as trades execute

### 8. **Recent Trades Log**
- Last 20 trades with details:
  - Symbol
  - Entry/Exit prices
  - P&L (profit/loss)
  - Trade duration
  - Agent responsible
  - Trade reason
- Color-coded: Green for profits, Red for losses

## Real-Time Updates

The dashboard automatically refreshes every **5 seconds** to show the latest:
- Bot status
- Current regime
- Portfolio performance
- Risk metrics
- Agent weights
- Trade log

## Color Coding

- **Green**: Profitable trades, positive metrics, healthy status
- **Red**: Losses, errors, danger states
- **Blue**: Neutral information, regime badges
- **Orange/Yellow**: Warnings, paused state

## Responsive Design

The dashboard is fully responsive and works on:
- Desktop computers
- Tablets
- Mobile devices

## Browser Compatibility

Works best with modern browsers:
- Chrome/Edge (recommended)
- Firefox
- Safari
- Opera

## Troubleshooting

### Dashboard not loading?
1. Check if the FastAPI server is running
2. Verify the server is accessible at `http://localhost:8000`
3. Check browser console for errors (F12)
4. Ensure `ui/dashboard.html` exists

### Data not updating?
1. Check browser console for API errors
2. Verify the bot manager is initialized
3. Check FastAPI server logs for errors
4. Ensure CORS is not blocking requests (shouldn't be an issue for localhost)

### Charts not showing?
1. Ensure Chart.js CDN is accessible
2. Check browser console for JavaScript errors
3. Verify portfolio stats endpoint returns equity_history data

## Keyboard Shortcuts

- **F5**: Refresh page
- **Ctrl+R / Cmd+R**: Reload dashboard

## Security Notes

- The dashboard is designed for **local use** only
- If exposing to the internet, add authentication
- Never expose API endpoints without proper security
- Consider using HTTPS in production

## Customization

You can customize the dashboard by editing `ui/dashboard.html`:
- Change update interval (default: 5000ms)
- Modify color scheme
- Add/remove cards
- Customize chart options

## API Endpoints Used

The dashboard uses these FastAPI endpoints:
- `GET /health` - System health
- `GET /regime` - Current regime
- `GET /stats` - Portfolio statistics
- `GET /risk-status` - Risk management status
- `GET /agents` - Agent weights
- `GET /trade-log` - Recent trades
- `POST /start` - Start bot
- `POST /stop` - Stop bot
- `POST /pause` - Pause bot
- `POST /kill` - Toggle kill switch

## Next Steps

1. Start the bot using the dashboard controls
2. Monitor regime changes in real-time
3. Watch agent weights evolve as the system learns
4. Review trade log for performance analysis
5. Use kill switch if needed for emergency stop

Enjoy your FutBot Dashboard! 🚀

