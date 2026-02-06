# Restart Server Instructions

## Issue
The server is still using old code with incorrect date calculations. The fix has been applied, but the server needs to be restarted.

## Steps to Restart

1. **Stop the current server**
   - In the terminal where `run_web.py` is running, press `Ctrl+C`
   - Wait for the server to stop completely

2. **Restart the server**
   ```bash
   python run_web.py
   ```

3. **Wait for server to start**
   - You should see:
     ```
     ============================================================
     AI Trading Dashboard
     ============================================================
     Starting web server...
     ```

4. **Test the endpoint**
   - Visit: http://localhost:5000/api/signals/RELIANCE.NS
   - Or use curl:
     ```bash
     curl http://localhost:5000/api/signals/RELIANCE.NS
     ```

## Expected Result After Restart

The signal generation should now:
- ✅ Use correct dates (not in the future)
- ✅ Successfully fetch data from Yahoo Finance
- ✅ Return ELITE signal with probability and confidence

## What Was Fixed

1. **Date calculation**: Changed to use conservative dates (7 days ago, or hardcoded dates if system clock is wrong)
2. **System clock detection**: Detects if system date is in the future and uses safe fallback dates
3. **Better error handling**: More robust date validation

## If Still Having Issues

If the error persists after restart:
1. Check server logs for date range messages
2. Verify the system date is correct
3. Try a different ticker (e.g., `TCS.NS`, `INFY.NS`)
