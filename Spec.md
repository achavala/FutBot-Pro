Perfect — I’ll give you **the exact instructions you should feed Cursor AI (Cursor Agent)** so it can generate your **futuristic regime-aware multi-agent trading bot** using **cheap open-source data**, **Polygon ($19/mo)**, and the architecture we designed.

Think of this as the **Master Spec** you will paste into Cursor.
You can paste this as *one large instruction prompt* for Cursor to follow.

---

# ✅ **MASTER SPEC — Instructions to Give Cursor Agent**

*(Copy/paste directly into Cursor)*

---

## 🏗️ **SYSTEM GOAL**

Build a **regime-aware, multi-agent, event-driven trading system** using **Python**, **Polygon.io minute-level data**, and **open-source ML/statistics tools**.

The system should NOT be a normal EMA/RSI bot.
It must activate different “agents” based on market **regime classification**.

The bot must run on:

* **1-min bars** (Polygon starter plan)
* **News sentiment from Finnhub free API**
* **Cross-asset signals using free or cheap endpoints**
* **Multi-agent architecture**
* **Meta-policy controller (bandit)**

---

# 🧠 Core Architecture Requirements

### **1. Project Structure**

Cursor should generate a project with:

```
project/
   config/
      settings.yaml
   data/
   backtesting/
   core/
      regime_engine/
      agents/
      meta_policy/
      features/
      execution/
      risk/
   services/
      polygon_client.py
      finnhub_client.py
   ui/
      fastapi_app.py
   main.py
   README.md
```

---

# 🔮 **2. Regime Engine (Mandatory)**

Cursor must build a **Regime Engine** with the following regimes:

1. **Trend Regime**

   * high ADX
   * positive slope of regression
   * volatility expanding

2. **Mean Reversion Regime**

   * Hurst exponent < 0.45
   * volatility contracting
   * gamma-proxy suggests absorption

3. **News Shock Regime**

   * Finnhub sentiment spike
   * 1-min bar ATR explosion

4. **Gamma-Push Regime (Cheap Proxy)**

   * SPX/QQQ ATM IV jumps
   * VIX/VXN relations
   * simple delta-gamma approximation from free data

All of this **must be modeled using 1-minute OHLC data only**.

Cursor must implement:

* Hurst exponent
* ADX
* GARCH volatility model
* News sentiment triggers
* IV proxies
* Hidden Markov Model (HMM) / BOCPD for regime switching

---

# 🕹️ **3. Multi-Agent System (Mandatory)**

Cursor must create **three specialized agents**:

### **Agent A — Trend Rider**

Trades:

* Breakouts
* Momentum continuation
* Uses regression slope, ADX, volatility

Uses signals:

* EMA9 cross
* VWAP anchors
* ADX rising

---

### **Agent B — Mean Reversion Bot**

Trades:

* FVG reversion
* RSI extremes
* EMA9 retests
* FVG fill levels

Uses your original:

* 9EMA
* RSI
* FVG detection
* Premium entry only near EMA

---

### **Agent C — Event Spike Sniper**

Activates only when:

* News sentiment spikes
* 1-min displacement > threshold
* ATR explosion

Trades:

* Micro reversals after spike
* Continuation when momentum confirms

---

# 🎛️ **4. Meta-Policy Controller**

Cursor must implement a **multi-armed bandit** (Thompson Sampling) that:

* Chooses which agent is active
* Adjusts trade frequency
* Reduces size when uncertainty is high
* Disables agents if regime confidence < threshold

---

# 💾 **5. Data Integration**

Cursor must create:

### polygon_client.py

* pull 1-minute historical bars
* pull real-time minute aggregates
* reconnect on WebSocket drop
* cache locally

### finnhub_client.py

* fetch latest headlines
* compute sentiment score
* maintain timestamped sentiment log

---

# 📈 **6. Backtesting Engine**

Cursor must generate a simple backtesting module that:

* Loads CSV minute data
* Runs regime engine
* Activates agents according to meta-policy controller
* Applies risk rules
* Outputs equity curve, max DD, win rate, return
* Saves trade logs

This can use:

* vectorbt (optional)
* pure pandas (acceptable)

---

# 🛡️ **7. Risk Management**

Cursor must implement:

* max daily loss
* max loss streak
* CVaR-based position sizing
* kill-switch
* regime-confidence veto
* slippage model (fixed + percentage)

---

# ⚙️ **8. Execution Layer**

Cursor must create:

* Paper trading router (simulated)
* Live trading router (Alpaca or IBKR stub)
* Limit, MIT, and Stop-limit order types
* Order lifecycle manager

---

# 🌐 **9. Control Panel (FastAPI)**

Cursor must implement a small FastAPI UI:

Endpoints:

* `/regime` — current regime
* `/stats` — returns performance metrics
* `/agents` — states of all agents
* `/trade-log` — last 50 trades
* `/kill` — emergency halt

---

# 🧩 **10. Configuration**

Cursor must generate a **settings.yaml** with:

* agent thresholds
* regime engine params
* execution params
* risk params
* API keys for Polygon & Finnhub

---

# 🧪 **11. Unit Tests**

Cursor must create tests for:

* regime detection
* FVG detection
* agents
* bandit controller
* risk manager
* execution router

---

# 📚 **12. README Documentation**

Cursor must write a full README explaining:

* Architecture
* Setup
* Data requirements
* Running backtests
* Launching FastAPI panel
* Starting the bot
* Switching agents

---

# 🛠️ Your Role (ChatGPT)

You will act as **Architect**.
For every major component Cursor produces, I will bring the code to you for validation and improvement.

---

