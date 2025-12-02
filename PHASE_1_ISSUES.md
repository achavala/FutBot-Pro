# Phase 1 Issues Log

**Purpose:** Track all issues found during Phase 1 validation

---

## Issue Template

```markdown
## Issue #X – [Brief Description]

- **Run ID:** run_YYYYMMDD_HHMMSS
- **Period:** [trending_up / trending_down / choppy / major_event / expiry_week]
- **Package ID:** [multi_leg_id] (if applicable)
- **Symbol:** [SPY/QQQ]
- **Date:** YYYY-MM-DD
- **Severity:** Critical / High / Medium / Low

**Expected:** [What should have happened]

**Observed:** [What actually happened]

**Logs:**
```
[Relevant log snippets]
```

**Fix:** [Fix applied or pending]

**Status:** Open / Fixed / Verified
```

---

## Issues

### Issue #1 – [Example: ThetaHarvester double exit on IV collapse]

- **Run ID:** run_20241201_trending_up_01
- **Period:** trending_up
- **Package ID:** SPY_STRADDLE_short_673_673_20241126
- **Symbol:** SPY
- **Date:** 2024-11-26
- **Severity:** High

**Expected:** Single IV_COLLAPSE exit, package closed once

**Observed:** Exit called twice, second attempt rejected by broker

**Logs:**
```
[MultiLegExit] Closing STRADDLE SPY_STRADDLE_short_673_673_20241126: Theta Harvester IV collapse: IV dropped 35.2%
[MultiLeg] Closing STRADDLE: CALL 3x @ $1.25 + PUT 3x @ $1.15
[MultiLeg] STRADDLE closed: Combined P&L: $720.00 (50.0%)
[MultiLegExit] Closing STRADDLE SPY_STRADDLE_short_673_673_20241126: Theta Harvester IV collapse: IV dropped 35.2%
[ERROR] Order rejected: Position already closed
```

**Fix:** [Pending - Add check to prevent double exit]

**Status:** Open

---

## Summary

**Total Issues:** 0  
**Critical:** 0  
**High:** 0  
**Medium:** 0  
**Low:** 0

**Fixed:** 0  
**Verified:** 0  
**Open:** 0

