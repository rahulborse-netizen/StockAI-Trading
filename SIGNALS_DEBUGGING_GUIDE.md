# Trading Signals Debugging Guide

## 🔍 Current Status

**Good News:**
- ✅ Error message is now showing (improved UX)
- ✅ NIFTY and BANKNIFTY are working
- ✅ JavaScript errors are fixed

**Issues:**
- ⚠️ Trading signals not loading
- ⚠️ SENSEX and INDIA VIX still showing "--"

## 🐛 How to Debug

### Step 1: Check Browser Console
1. Open browser console: Press `F12`
2. Go to **Console** tab
3. Look for errors when clicking "Retry" button
4. Check **Network** tab for failed API calls

### Step 2: Test API Endpoint Directly
Open in browser:
```
http://localhost:5000/api/signals/RELIANCE.NS
```

**Expected Response:**
```json
{
  "signal": "BUY",
  "probability": 0.65,
  "current_price": 2450.50,
  ...
}
```

**If Error:**
- Check the error message
- Look at server logs in terminal

### Step 3: Check Server Logs
In your terminal where `run_web.py` is running, look for:
- `[Signals]` log messages
- `[ELITE Signal]` log messages
- Error tracebacks

### Step 4: Test with Python Script
Run the test script:
```bash
python test_signals_endpoint.py
```

This will test the signals endpoint and show what's failing.

## 🔧 Common Issues & Solutions

### Issue 1: "No data available"
**Cause:** Yahoo Finance data download failing
**Solutions:**
- Check internet connection
- Try connecting Upstox account
- Check if market is open (data may be stale outside hours)

### Issue 2: "Insufficient data"
**Cause:** Not enough historical data for the ticker
**Solutions:**
- Try a different, more popular stock (RELIANCE.NS, TCS.NS)
- Check if ticker symbol is correct

### Issue 3: SSL Certificate Error
**Cause:** Corporate network/proxy blocking Yahoo Finance
**Solutions:**
- Connect Upstox account (bypasses Yahoo Finance)
- Update certificates: `python -m pip install --upgrade certifi`

### Issue 4: Timeout
**Cause:** Signal generation taking too long
**Solutions:**
- Wait a bit longer (first request may be slow)
- Check server resources
- Try with `?elite=false` to use basic signals

## 💡 Quick Fixes

### Option 1: Use Basic Signals (Faster)
Add `?elite=false` to URL:
```
http://localhost:5000/api/signals/RELIANCE.NS?elite=false
```

### Option 2: Connect Upstox
1. Click "Connect" button in dashboard
2. Enter Upstox API credentials
3. Get real-time data (more reliable than Yahoo Finance)

### Option 3: Check Date Range
The system uses safe dates (2023-09-30 to 2024-09-30) to avoid system clock issues. If you need more recent data, you may need to:
- Fix system clock
- Or update the date range in code

## 📊 Expected Behavior

### When Working:
1. Click "Trading Signals" tab
2. See loading spinner
3. Signal cards appear with:
   - Stock name
   - BUY/SELL/HOLD signal
   - Current price
   - Entry level, stop loss
   - Confidence percentage

### When Failing:
1. Click "Trading Signals" tab
2. See loading spinner
3. Error message appears with:
   - Warning icon
   - Error description
   - Possible causes
   - Retry button

## 🚀 Next Steps

1. **Check Browser Console** (F12) for specific errors
2. **Test API Directly**: `http://localhost:5000/api/signals/RELIANCE.NS`
3. **Check Server Logs**: Look for error messages
4. **Run Test Script**: `python test_signals_endpoint.py`
5. **Share Error Details**: If still failing, share:
   - Browser console errors
   - Server log errors
   - API response from direct test

---

**The improved error handling should help identify the exact issue!** 🔍
