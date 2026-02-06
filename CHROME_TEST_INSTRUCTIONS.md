# Chrome Browser Test Instructions

## Quick Test in Chrome

### Method 1: Open Test Page (Easiest)

1. **Open the test page**:
   - File location: `test_in_browser.html`
   - Double-click the file, or
   - Right-click → Open with → Google Chrome
   - Or drag and drop into Chrome

2. **The page will automatically test**:
   - It will fetch the signal endpoint
   - Show you the results
   - Highlight if dates are correct or incorrect

3. **What you'll see**:
   - ✅ Green box = Date fix is working (dates: 2023-09-30 to 2024-09-30)
   - ❌ Red box = Still using old dates (dates: 2025-02-05 to 2026-02-05)

---

### Method 2: Direct URL Test

1. **Make sure server is running**:
   ```bash
   python run_web.py
   ```

2. **Open Chrome browser**

3. **Visit this URL**:
   ```
   http://localhost:5000/api/signals/RELIANCE.NS
   ```

4. **What you'll see**:
   - Chrome will display JSON response
   - Look for the date range in the error message
   - If you see `2023-09-30 to 2024-09-30` → ✅ Date fix working!
   - If you see `2025-02-05 to 2026-02-05` → ❌ Restart server

---

## What Success Looks Like

### ✅ Date Fix Working:
```json
{
  "error": "... Date range: 2023-09-30 to 2024-09-30 ..."
}
```
**Meaning**: Dates are correct! Date fix is working.

### ✅ Full Success (if data available):
```json
{
  "ticker": "RELIANCE.NS",
  "signal": "BUY",
  "probability": 0.65,
  "elite_system": true,
  ...
}
```
**Meaning**: Everything working perfectly!

---

## What Failure Looks Like

### ❌ Date Fix NOT Working:
```json
{
  "error": "... Date range: 2025-02-05 to 2026-02-05 ..."
}
```
**Meaning**: Server needs restart to load new code.

---

## Step-by-Step Chrome Test

1. **Start Server** (if not running):
   ```bash
   python run_web.py
   ```

2. **Open Chrome**

3. **Open Test Page**:
   - Navigate to project folder
   - Double-click `test_in_browser.html`
   - OR visit: `file:///C:/Users/rahul_borse/OneDrive%20-%20S&P%20Global/Python/Python%20Assignment/stockai-trading-india/test_in_browser.html`

4. **Or Visit Direct URL**:
   ```
   http://localhost:5000/api/signals/RELIANCE.NS
   ```

5. **Check Results**:
   - Look for date range in response
   - Verify dates are `2023-09-30 to 2024-09-30`
   - If correct → Date fix is working! ✅

---

## Troubleshooting

### Chrome Shows "Cannot connect"
- Make sure server is running
- Check URL is correct: `http://localhost:5000`
- Try: `http://127.0.0.1:5000/api/signals/RELIANCE.NS`

### Still Seeing Old Dates
- Stop server (Ctrl+C)
- Restart: `python run_web.py`
- Refresh Chrome page

### No Response
- Check server terminal for errors
- Verify port 5000 is not blocked
- Try a different browser

---

## Expected Result

When you open Chrome and test, you should see:
- ✅ Dates: `2023-09-30 to 2024-09-30` (correct!)
- ✅ No dates: `2025-02-05 to 2026-02-05` (old bug)

**This confirms the date fix is working!** 🎉
