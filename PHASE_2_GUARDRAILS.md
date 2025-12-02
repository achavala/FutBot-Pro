# Phase 2: Paper Live Guardrails

**Status:** Prepared for Phase 2 (after Phase 1 passes)

---

## 🛡️ **Risk Limits**

### **Per-Strategy Limits**

#### **Theta Harvester (Straddle Seller)**
- **Max Daily Open Risk:** $10,000 notional per symbol
- **Max Open Packages:** 3 per symbol
- **Max Daily Loss:** $2,000 per strategy
- **Position Size:** 1-3 contracts per trade (based on IV percentile)

#### **Gamma Scalper (Strangle Buyer)**
- **Max Daily Open Risk:** $5,000 notional per symbol
- **Max Open Packages:** 2 per symbol
- **Max Daily Loss:** $1,000 per strategy
- **Position Size:** 1-2 contracts per trade (based on GEX strength)

### **Global Limits**
- **Max Total Open Risk:** $20,000 notional across all strategies
- **Max Daily Loss:** $3,000 global
- **Max Open Packages:** 5 total across all symbols
- **Hard Stop:** Disable all new entries if daily loss > $3,000

---

## 🚨 **Circuit Breakers**

### **Daily Loss Circuit Breaker**
- **Threshold:** $3,000 daily loss
- **Action:** Hard stop - disable all new entries
- **Recovery:** Manual reset required
- **Logging:** Alert logged, UI shows "RISK-OFF" state

### **Per-Strategy Circuit Breaker**
- **Threshold:** Strategy daily loss > 50% of max
- **Action:** Disable new entries for that strategy
- **Recovery:** Auto-reset next day
- **Logging:** Strategy-specific alert logged

### **Position Size Circuit Breaker**
- **Threshold:** Position size > 3x base size
- **Action:** Cap position size, log warning
- **Recovery:** Auto-adjust
- **Logging:** Warning logged

---

## 🔒 **Paper-Only Safeguards**

### **Separate Credentials/Configs**
- **Different Keys:** Paper and live must use different API keys
- **Different Config Files:** Use separate config files (e.g., `config/paper.yaml` vs `config/live.yaml`)
- **Pre-Flight Check:** Hard-check broker mode from environment, not just a comment:
  ```python
  BROKER_MODE = os.getenv("BROKER_MODE", "PAPER")
  if BROKER_MODE != "PAPER":
      raise ValueError(f"Broker mode must be PAPER, got {BROKER_MODE}")
  ```

### **Account ID Validation**
- **Check:** Verify account ID is paper account (not live)
- **Action:** Reject orders if live account detected
- **Logging:** Error logged, order rejected

### **Broker Mode Check**
- **Check:** Verify broker client is paper trading mode
- **Action:** Reject orders if live mode detected
- **Logging:** Error logged, order rejected

### **Environment Variable Check**
- **Check:** Verify `ALPACA_BASE_URL` contains "paper-api"
- **Action:** Reject orders if live URL detected
- **Logging:** Error logged, order rejected

---

## 📊 **Enhanced Logging**

### **Paper vs Live Separation**
- **Prefix:** All paper orders logged with `[PAPER]` prefix
- **Separate Log File:** `logs/paper_trading.log`
- **Broker Tag:** All broker calls tagged with `paper=true`

### **Order Tracking**
- **Order ID:** Logged for every order
- **Broker Order ID:** Logged when received
- **Fill Confirmation:** Logged with broker confirmation
- **Rejection Reason:** Logged if order rejected

### **Position Reconciliation**
- **Frequency:** Every 5 minutes
- **Action:** Pull positions from broker, compare with local
- **Mismatch Handling:** Log alert, mark position for review
- **Recovery:** Auto-reconcile if possible, manual review if not

---

## 🔍 **Monitoring**

### **Real-Time Monitoring**
- **Dashboard:** Real-time position updates
- **Alerts:** Push notifications for:
  - Circuit breaker triggers
  - Daily loss limit hits
  - Position mismatches
  - Order rejections

### **Daily Reports**
- **Summary:** Daily P&L, trades, positions
- **Risk Metrics:** Max drawdown, VaR, exposure
- **Performance:** Win rate, avg P&L, best/worst trades
- **Issues:** Any errors, rejections, mismatches

---

## 🚦 **Entry Rules**

### **Pre-Entry Checks**
Before entering any multi-leg position:

1. **Risk Limits:**
   - [ ] Daily loss < max daily loss
   - [ ] Open risk < max open risk
   - [ ] Open packages < max open packages
   - [ ] Strategy daily loss < strategy max

2. **Account Status:**
   - [ ] Account is paper account
   - [ ] Broker is paper mode
   - [ ] No circuit breakers active

3. **Position Limits:**
   - [ ] Position size within limits
   - [ ] Notional within limits
   - [ ] No duplicate positions

### **Post-Entry Checks**
After entering position:

1. **Fill Verification:**
   - [ ] Both legs filled (or partial tracked)
   - [ ] Credit/debit matches expected (±10%)
   - [ ] Position created in portfolio

2. **Risk Update:**
   - [ ] Open risk updated
   - [ ] Daily loss updated
   - [ ] Position count updated

---

## 🛠️ **Failure Handling**

### **Kill Switch / Manual Override**
- **Ability to:**
  - Turn strategy off (disable Theta Harvester, Gamma Scalper individually)
  - Flatten all positions (paper) - single command/UI action
  - Emergency stop - disable all trading immediately
- **Implementation:**
  - API endpoint: `POST /live/emergency-stop`
  - UI button: "Emergency Stop" (red, prominent)
  - Command: `curl -X POST http://localhost:8000/live/emergency-stop`
- **Behavior:**
  - Immediately stops all new entries
  - Allows existing positions to exit (or manual close)
  - Logs emergency stop event
  - Requires manual reset to resume

### **Order Rate Limiting**
- **Guardrails around bursting:**
  - No more than N new packages per minute per strategy (e.g., 2 per minute)
  - No more than M total packages per hour (e.g., 10 per hour)
- **Implementation:**
  - Track package entry timestamps
  - Check rate limits before entry
  - Log rate limit hits
  - UI shows rate limit status
- **Very important when signals go crazy**

### **Order Rejection**
- **Action:** Log rejection reason
- **Position:** Mark as "rejected" or "broken"
- **Alert:** Send notification
- **Recovery:** Manual review required

### **Partial Fill**
- **Action:** Track partial fill
- **Position:** Mark as "pending"
- **Alert:** Log partial fill status
- **Recovery:** Wait for full fill or manual close

### **Network Error**
- **Action:** Retry with backoff (3 attempts)
- **Position:** Keep tracking locally
- **Alert:** Log retry attempts
- **Recovery:** Reconcile when connection restored

### **Broker Throttling**
- **Action:** Throttle requests
- **Position:** Continue tracking
- **Alert:** Log throttling events
- **Recovery:** Resume when throttling ends

---

## 📋 **Pre-Flight Checklist**

Before starting Phase 2:

- [ ] **Alpaca Credentials:**
  - [ ] API key set in `.env.local`
  - [ ] Secret key set in `.env.local`
  - [ ] Base URL is paper API (`https://paper-api.alpaca.markets`)

- [ ] **Account Verification:**
  - [ ] Paper account accessible
  - [ ] Account has buying power
  - [ ] Options trading enabled
  - [ ] **Broker mode: PAPER** hard-checked from environment (not just comment)
  - [ ] Separate config file for paper trading

- [ ] **Risk Limits:**
  - [ ] Daily loss limits configured
  - [ ] Position size limits configured
  - [ ] Circuit breakers enabled

- [ ] **Logging:**
  - [ ] Paper trading log file created
  - [ ] Logging level set to DEBUG
  - [ ] Alerts configured

- [ ] **Monitoring:**
  - [ ] Dashboard accessible
  - [ ] Real-time updates enabled
  - [ ] Notifications configured

---

## 🎯 **Phase 2 Success Criteria**

Phase 2 PASSES when:

- ✅ **Real Orders Execute:**
  - Orders submitted to Alpaca paper account
  - Fills match broker records
  - Positions sync correctly

- ✅ **Risk Limits Enforced:**
  - Daily loss limits respected
  - Position size limits respected
  - Circuit breakers trigger correctly

- ✅ **No Rejected Orders:**
  - All orders accepted by broker
  - No unsupported order types
  - No account errors

- ✅ **Reconciliation Works:**
  - Broker positions match local
  - P&L matches broker
  - No mismatches

- ✅ **Auto-Exit Works:**
  - Exits trigger correctly
  - Orders execute successfully
  - Positions close properly

---

## 📝 **Phase 2 Test Plan**

### **Day 1: Single Symbol Test**
- Start with SPY only
- Enter 1-2 positions
- Monitor fills and P&L
- Test auto-exit triggers

### **Day 2: Multi-Symbol Test**
- Add QQQ
- Enter positions on both
- Monitor risk limits
- Test circuit breakers

### **Day 3: Stress Test**
- Max position sizes
- Multiple entries/exits
- Network error simulation
- Reconciliation test

---

**Ready for Phase 2 after Phase 1 passes!** 🚀

