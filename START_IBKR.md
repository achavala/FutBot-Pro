# Starting FutBot with IBKR

## Step 1: Make Sure IB Gateway is Running

✅ IB Gateway should be open and logged in
✅ API should be enabled (not read-only if you want to trade)
✅ Port should be 4002 (or whatever you configured)

## Step 2: Start FutBot API Server

```bash
cd /Users/chavala/FutBot
source .venv/bin/activate
export PATH="/opt/homebrew/opt/openjdk/bin:$PATH"
python main.py --mode api --port 8000
```

You should see:
```
Starting FutBot API server on 0.0.0.0:8000
API docs available at http://0.0.0.0:8000/docs
Health check at http://0.0.0.0:8000/health
```

## Step 3: Test Connection (Optional)

In another terminal:
```bash
# Test health
curl http://localhost:8000/health

# Test IBKR connection
python scripts/check_ibkr_connection.py
```

## Step 4: Start Live Trading

Once the server is running, start live trading:

```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["QQQ"],
    "broker_type": "ibkr",
    "ibkr_host": "127.0.0.1",
    "ibkr_port": 4002,
    "ibkr_client_id": 1
  }'
```

You should get:
```json
{
  "status": "started",
  "message": "Live trading started successfully"
}
```

## Step 5: Monitor

```bash
# Check status
curl http://localhost:8000/live/status

# Check portfolio
curl http://localhost:8000/live/portfolio

# Check risk
curl http://localhost:8000/risk-status
```

## Troubleshooting

### "Not Found" Error
- **Cause**: Server was started before live endpoints were added
- **Fix**: Restart the server (stop with Ctrl+C, then start again)

### "Failed to connect to IBKR"
- **Cause**: IB Gateway not running or API not enabled
- **Fix**: Check IB Gateway is running and API is enabled

### "Connection timeout"
- **Cause**: Wrong port or firewall blocking
- **Fix**: Verify port in IB Gateway matches what you're using (4002)

## Quick Reference

- **API Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health
- **Status**: http://localhost:8000/live/status
- **Portfolio**: http://localhost:8000/live/portfolio

