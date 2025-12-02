# Phase 1 Validation Results

**Purpose:** Store all Phase 1 validation artifacts for audit trail

## Folder Structure

```
phase1_results/
├── trending_up/          # Period 1: Trending up market
├── trending_down/        # Period 2: Trending down market
├── choppy/               # Period 3: Choppy/compressed market
├── major_event/          # Period 4: Major event (FOMC/CPI)
├── expiry_week/         # Period 5: Options expiry week
└── README.md            # This file
```

## Artifacts Per Period

Each period folder should contain:

1. **run_config.json** - Auto-dumped config at startup
   - Strategy params
   - Seeds
   - Versions
   - Test period dates

2. **run_logs.txt** - Relevant log excerpts
   - Multi-leg execution
   - Exit triggers
   - Errors/warnings
   - Reconciliation results

3. **reconcile_report.json** - Reconciliation output
   - P&L mismatches (if any)
   - Orphan legs (if any)
   - State inconsistencies (if any)

4. **scenarios_results.md** - Manual scenario tracking
   - Which scenarios executed
   - Pass/fail status
   - Package IDs
   - Entry/exit details

5. **metrics_summary.json** - Final metrics for period
   - P&L accuracy metrics
   - Exit trigger counts
   - Error counts
   - Scenario coverage

6. **issues.md** - Issues found during this period
   - Issue descriptions
   - Package IDs
   - Fixes applied

## Usage

1. Start validation for a period
2. Run scenarios systematically
3. Save artifacts to appropriate folder
4. Run reconciliation
5. Score exit criteria
6. Document issues

## Example

```bash
# Start validation
./START_VALIDATION.sh

# Run scenarios for trending_up period
# Save artifacts to phase1_results/trending_up/

# Run reconciliation
python scripts/reconcile_multi_leg_positions.py > phase1_results/trending_up/reconcile_report.json

# Score exit criteria
# Document in phase1_results/trending_up/metrics_summary.json
```

