# Time-Windowed Historical Simulation

## ✅ Feature Overview

Added support for **start time** and **end time** controls to test historical data within a specific time window.

## 🎯 What Was Added

### 1. **UI Controls**
- **Start Time Input**: `datetime-local` input for selecting start date and time
- **End Time Input**: `datetime-local` input for selecting end date and time
- **Stop Button**: Already exists, now works for time-windowed simulations

### 2. **Backend Support**
- **API Parameters**: `start_time` and `end_time` (ISO format: `YYYY-MM-DDTHH:MM:SS`)
- **Data Filtering**: `CachedDataFeed` filters bars by time window
- **Auto-Stop**: `LiveTradingLoop` automatically stops when `end_time` is reached

### 3. **Validation**
- End time must be after start time
- Timezone-aware datetime handling
- Graceful error messages

## 📋 Usage

### Step 1: Select Time Window
1. **Start Time**: Choose date and time (e.g., `2024-11-01 09:30`)
2. **End Time**: Choose date and time (e.g., `2024-11-01 16:00`)
3. **Symbol**: Select SPY or QQQ
4. **Replay Speed**: Choose 1x to 600x

### Step 2: Start Simulation
- Click **"Simulate"** button
- Simulation runs from start_time to end_time
- Automatically stops at end_time

### Step 3: Stop Manually (Optional)
- Click **"Stop"** button to stop simulation early
- Results are preserved up to stop point

## 🔧 Technical Implementation

### Data Flow:
```
User selects start_time + end_time
    ↓
UI sends: { start_time: "2024-11-01T09:30:00", end_time: "2024-11-01T16:00:00" }
    ↓
FastAPI parses to datetime objects
    ↓
CachedDataFeed filters bars: start_time <= bar.timestamp <= end_time
    ↓
LiveTradingLoop processes bars
    ↓
Checks: if bar.timestamp > end_time → stop
    ↓
Simulation stops automatically
```

### Key Files Modified:

1. **`ui/dashboard_modern.html`**:
   - Replaced date dropdown with `datetime-local` inputs
   - Updated `startSimulation()` to send `start_time` and `end_time`
   - Added validation (end_time > start_time)
   - Added initialization for default values

2. **`ui/fastapi_app.py`**:
   - Added `start_time` and `end_time` to `LiveStartRequest`
   - Parse ISO datetime strings
   - Pass to `CachedDataFeed` as `start_date` and `end_date`

3. **`core/live/data_feed_cached.py`**:
   - Added `end_date` parameter to `__init__()`
   - Filter bars by time window in `subscribe()`
   - Store `end_date` for loop to check

4. **`core/live/scheduler.py`**:
   - Check `bar.timestamp > end_date` before processing
   - Set `stop_reason = "end_time_reached"` when end_time is hit
   - Stop loop gracefully

## 📊 Example Scenarios

### Scenario 1: Single Day Trading Session
- **Start**: `2024-11-01 09:30` (Market Open)
- **End**: `2024-11-01 16:00` (Market Close)
- **Result**: Tests one full trading day

### Scenario 2: Specific Time Window
- **Start**: `2024-11-01 10:00`
- **End**: `2024-11-01 14:00`
- **Result**: Tests 4-hour window (10 AM - 2 PM)

### Scenario 3: Multi-Day Period
- **Start**: `2024-11-01 09:30`
- **End**: `2024-11-05 16:00`
- **Result**: Tests Monday through Friday

## ⚠️ Important Notes

1. **Timezone**: All times are in local browser timezone, converted to UTC for backend
2. **Market Hours**: Default start time is 9:30 AM (market open)
3. **Validation**: End time must be after start time (enforced in UI and backend)
4. **Stop Button**: Works for both time-windowed and regular simulations

## 🚀 Next Steps (Future Enhancements)

1. **Market Hours Detection**: Auto-set to market open/close times
2. **Preset Windows**: Quick buttons for "Today", "This Week", "This Month"
3. **Time Zone Selector**: Allow choosing timezone (ET, UTC, etc.)
4. **Visual Timeline**: Show selected time window on a timeline chart

## ✅ Testing Checklist

- [x] Start time input appears in UI
- [x] End time input appears in UI
- [x] Default values set (3 months ago to now)
- [x] Validation: end_time > start_time
- [x] API accepts start_time and end_time
- [x] CachedDataFeed filters by time window
- [x] LiveTradingLoop stops at end_time
- [x] Stop button works during simulation
- [x] Results preserved on stop

---

**Status**: ✅ Complete and Ready for Testing

