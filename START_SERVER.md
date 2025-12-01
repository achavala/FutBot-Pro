# How to Start the Server

## ✅ Quick Start (Recommended)

**Always activate the virtual environment first:**

```bash
# Activate virtual environment
source .venv/bin/activate

# Start server
python main.py --mode api --port 8000
```

**OR use uvicorn directly:**

```bash
# Activate virtual environment
source .venv/bin/activate

# Start server with uvicorn
uvicorn ui.fastapi_app:app --host 0.0.0.0 --port 8000 --reload
```

**OR use python module syntax (works without PATH):**

```bash
# Activate virtual environment
source .venv/bin/activate

# Start server
python -m uvicorn ui.fastapi_app:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🔍 Verify Server is Running

```bash
# Check health
curl http://localhost:8000/health

# Check status
curl http://localhost:8000/live/status | python3 -m json.tool
```

---

## 🛑 Stop the Server

```bash
# Find and kill the process
pkill -f "uvicorn.*fastapi"

# OR find the PID and kill it
ps aux | grep uvicorn
kill <PID>
```

---

## ⚠️ Common Issues

### Issue: `ModuleNotFoundError: No module named 'uvicorn'`

**Solution:** You forgot to activate the virtual environment!

```bash
source .venv/bin/activate
# Then try again
```

### Issue: Port 8000 already in use

**Solution:** Kill the existing process or use a different port:

```bash
# Kill existing process
pkill -f "uvicorn.*fastapi"

# OR use different port
uvicorn ui.fastapi_app:app --host 0.0.0.0 --port 8001 --reload
```

---

## 📝 Notes

- The virtual environment (`.venv`) contains all required dependencies
- Always activate it before running the server
- The `--reload` flag enables auto-reload on code changes (useful for development)
- Server runs on `http://localhost:8000` by default


