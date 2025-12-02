# Phase 1 Execution Playbook

**Step-by-step guide for running Phase 1 validation**

---

## Step 1: Freeze & Sanity Check ✅

```bash
# Run freeze script
./FREEZE_AND_TAG.sh

# Verify
git status          # should say: nothing to commit, working tree clean
git tag --list | grep v1.0.0-ml-multi-leg
git show v1.0.0-ml-multi-leg --stat
```

**Expected:**
- ✅ Git status is clean
- ✅ Tag exists and points to expected commit
- ✅ Baseline locked in

**From here:** Any code change = new tag (e.g., v1.0.1-...)

---

## Step 2: Create Results Structure ✅

```bash
mkdir -p phase1_results/{trending_up,trending_down,choppy,major_event,expiry_week}
```

**Structure created:**
- ✅ `phase1_results/trending_up/`
- ✅ `phase1_results/trending_down/`
- ✅ `phase1_results/choppy/`
- ✅ `phase1_results/major_event/`
- ✅ `phase1_results/expiry_week/`

---

## Step 3: Run Phase 1 Periods

### Period 1: Trending Up

#### 3.1 Start Engine

Start Engine

```bash
./START_VALIDATION.sh
```

**Verify at startup:**
- [ ] `run_id` logged (e.g., `run_20241201_143022`)
- [ ] `run_config.json` dumped to `phase1_results/trending_up/`
- [ ] Seeds logged in config
- [ ] Commit + tag logged in config
- [ ] UI shows SIM/historical mode
- [ ] Date range matches Test Matrix

#### 3.2. Execute Scenarios

**Happy-Path Scenarios:**

1. **Theta Harvester TP +50%**
   - Wait for package matching entry conditions
   - Let run until exit
   - Capture: package_id, entry/exit timestamps, P&L, exit_reason
   - Mark in `scenarios_results.md`

2. **Gamma Scalper TP +150%**
   - Same process

**Risk-Side Scenarios:**

3. **Theta Harvester SL -200%**
4. **Gamma Scalper SL -50%**
5. **IV Collapse Exit**
6. **GEX Reversal Exit**
7. **Time-Limit Exit**

**Edge Cases:**

8. **E1: Partial Fill**
9. **E2: Leg Rejection**
10. **E6: Engine Restart**
11. **E7: Clock Anomalies**

**After Each:**
- Check package status (no zombies)
- Check logs show clear reason/recovery
- Run reconciliation

#### 3.3. Run Reconciliation

```bash
# Run reconciliation script or endpoint
python scripts/reconcile_multi_leg_positions.py > phase1_results/trending_up/reconcile_report.json

# Or via API
curl http://localhost:8000/options/reconcile > phase1_results/trending_up/reconcile_report.json
```

#### 3.4. Save Artifacts

```bash
# Copy config
cp run_config.json phase1_results/trending_up/

# Extract relevant logs
tail -n 10000 logs/*.log | grep -i "multileg\|straddle\|strangle\|multilegexit" > phase1_results/trending_up/run_logs.txt

# Copy reconciliation report (already saved above)
# Copy scenarios results (manual)
# Generate metrics summary
```

#### 3.5. Score Exit Criteria

Open `PHASE_1_EXIT_CRITERIA.md` and score for this period:

- [ ] P&L mismatch metric → Pass/Fail
- [ ] Orphan legs → Pass/Fail
- [ ] Unhandled exceptions → Pass/Fail
- [ ] Scenario coverage → X/Y executed, X passed
- [ ] No-day-from-hell → Pass/Fail

**Record in:** `phase1_results/trending_up/metrics_summary.json`

---

### Period 2: Trending Down

**Repeat Steps 3.1-3.5** for trending_down period

---

### Period 3: Choppy/Compressed

**Repeat Steps 3.1-3.5** for choppy period

---

### Period 4: Major Event

**Repeat Steps 3.1-3.5** for major_event period

---

### Period 5: Options Expiry Week

**Repeat Steps 3.1-3.5** for expiry_week period

---

## Step 4: Handle Bugs

When something fails:

### 4.1. Capture Evidence

- run_id, package_id, logs snippet
- Add entry to `PHASE_1_ISSUES.md`

### 4.2. Create Fix Branch

```bash
git checkout -b fix/[issue-name] v1.0.0-ml-multi-leg
# implement fix, add unit test
git commit -am "Fix: [issue description]"
```

### 4.3. Tag New Build

```bash
git tag -a v1.0.1-ml-multi-leg -m "Phase 1 fixes: [issue]"
git push && git push --tags
```

### 4.4. Rerun Impacted Scenarios

- Rerun only subset where behavior changed
- Plus small regression slice

---

## Step 5: Finalize Phase 1

### 5.1. Check Exit Criteria

Based on `PHASE_1_EXIT_CRITERIA.md`, Phase 1 complete when:

- ✅ P&L mismatch metric = 0 (over all periods)
- ✅ Orphan legs = 0
- ✅ Unhandled ERROR/FATAL = 0
- ✅ 100% of planned scenarios executed
- ✅ ≥80% pass, all safety-critical pass
- ✅ No-day-from-hell without risk block

### 5.2. Create Final Tag

```bash
git tag -a v1.1.0-ml-multi-leg-phase1-passed -m "Phase 1 validation complete"
git push --tags
```

### 5.3. Generate Final Report

Create `PHASE_1_FINAL_REPORT.md`:

- Summarizes each period
- Lists fixes made
- Includes final metrics
- Sign-off before Phase 2

---

## Quick Reference

### Start Validation
```bash
./START_VALIDATION.sh
```

### Run Reconciliation
```bash
python scripts/reconcile_multi_leg_positions.py > phase1_results/[period]/reconcile_report.json
```

### Check Logs
```bash
tail -f logs/*.log | grep -i "multileg\|straddle\|strangle"
```

### Check API
```bash
curl http://localhost:8000/options/positions | python3 -m json.tool
curl http://localhost:8000/trades/options/multi-leg | python3 -m json.tool
```

---

**Ready to begin Phase 1!** 🚀

