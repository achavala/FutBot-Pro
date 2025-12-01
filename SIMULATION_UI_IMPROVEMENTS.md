# Simulation UI Improvements

## ✅ Changes Made

### 1. Symbol Selector Dropdown
- **Added**: Dropdown to choose between SPY or QQQ for simulation
- **Location**: Header controls, before date dropdown
- **Default**: SPY selected
- **Behavior**: Only the selected symbol is used in simulation (not both)

### 2. Date Dropdown (Last 3 Months)
- **Replaced**: Date input field with dropdown
- **Content**: Populates with weekdays (Mon-Fri) from the last 3 months
- **Format**: User-friendly format (e.g., "Mon, Nov 25, 2024")
- **Default**: "All Available Data" option (no date restriction)
- **Behavior**: Automatically populated on page load

### 3. Updated Simulation Function
- **Changed**: `startSimulation()` now uses selected symbol only
- **Before**: Always used both SPY and QQQ
- **After**: Uses only the symbol selected in dropdown
- **Date**: Uses selected date from dropdown (or null if "All Available Data")

## 🎯 User Experience

When clicking "Simulate" button, users now see:
1. **Symbol Selector**: Choose SPY or QQQ
2. **Date Dropdown**: Select a date from last 3 months (or "All Available Data")
3. **Replay Speed**: Choose replay speed (1x, 10x, 50x, 100x, 600x)

## 📋 Example Usage

1. Select **SPY** from symbol dropdown
2. Select **"Mon, Nov 25, 2024"** from date dropdown
3. Select **600x** replay speed
4. Click **"Simulate"** button

This will start a simulation with:
- Symbol: SPY only
- Start Date: 2024-11-25
- Replay Speed: 600x (0.1s per bar)

## 🔧 Technical Details

### Date Generation
- Generates dates from 3 months ago to today
- Filters to weekdays only (Monday-Friday)
- Formats dates as "Weekday, Month Day, Year"
- Stores actual date value as ISO format (YYYY-MM-DD) for API

### Symbol Selection
- Single symbol selection (SPY or QQQ)
- Defaults to SPY
- Passed as array to API: `["SPY"]` or `["QQQ"]`

### API Payload
```json
{
  "symbols": ["SPY"],
  "broker_type": "cached",
  "offline_mode": true,
  "start_date": "2024-11-25",
  "fixed_investment_amount": 10000.0,
  "replay_speed": 600.0
}
```

## 📝 Files Modified

- `ui/dashboard_modern.html`:
  - Added symbol selector dropdown
  - Replaced date input with dropdown
  - Added `populateDateDropdown()` function
  - Updated `startSimulation()` function


