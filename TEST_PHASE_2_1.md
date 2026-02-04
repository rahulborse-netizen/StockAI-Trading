# Phase 2.1 Testing Guide - Real-time Data Integration

## 🧪 Test Checklist

### Prerequisites
- [ ] Flask server is running (`python run_web.py`)
- [ ] Browser open to `http://localhost:5000`
- [ ] Upstox connection (optional - will fallback to cached data if not connected)

---

## Test 1: Verify Server is Running

**Action:**
1. Open browser to `http://localhost:5000`
2. Check if dashboard loads

**Expected:**
- Dashboard loads successfully
- No errors in browser console (F12)

---

## Test 2: Test Prices Endpoint (Without Upstox Connection)

**Action:**
1. Open browser console (F12)
2. Run:
```javascript
fetch('/api/prices')
  .then(r => r.json())
  .then(data => {
    console.log('Prices Response:', data);
    console.log('Source:', Object.values(data)[0]?.source || 'unknown');
  })
```

**Expected:**
- Returns price data for watchlist items
- `source: 'cached'` or `source: 'yahoo'` (since Upstox not connected)
- Prices are numbers
- Change and change_pct are calculated

---

## Test 3: Test Market Indices Endpoint

**Action:**
Run in browser console:
```javascript
fetch('/api/market_indices')
  .then(r => r.json())
  .then(data => {
    console.log('Market Indices:', data);
    console.log('NIFTY50:', data.NIFTY50);
    console.log('Source:', data.NIFTY50?.source || 'mock');
  })
```

**Expected:**
- Returns NIFTY50, BANKNIFTY, SENSEX data
- `source: 'mock'` (since Upstox not connected)
- Values are numbers

---

## Test 4: Connect to Upstox and Test Real-time Data

**Action:**
1. Click "Connect" button in dashboard
2. Enter Upstox API credentials
3. Connect successfully
4. Run Test 2 again

**Expected:**
- Connection successful
- Prices endpoint returns `source: 'upstox'` or real-time data
- Market indices endpoint returns real-time data
- Prices update with live market data

---

## Test 5: Test with Watchlist Items

**Action:**
1. Add stocks to watchlist (e.g., "RELIANCE.NS", "TCS.NS")
2. Check prices update
3. Verify instrument key mapping works

**Expected:**
- Watchlist items show prices
- Real-time data when Upstox connected
- Cached data when not connected

---

## Test 6: Error Handling

**Action:**
1. Disconnect from Upstox (if connected)
2. Test with invalid ticker
3. Check error messages

**Expected:**
- Graceful fallback to cached data
- Clear error messages
- No crashes

---

## 🐛 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'src.web.market_data'"
**Fix:** Make sure you're in the project root directory

### Issue: Prices show "error" or "N/A"
**Fix:** 
- Check if watchlist has valid tickers
- Verify cache directory exists
- Check network connection

### Issue: Real-time data not working after connecting
**Fix:**
- Verify Upstox connection is active
- Check browser console for API errors
- Verify instrument keys are correct

---

## ✅ Success Criteria

- [ ] Prices endpoint works without Upstox
- [ ] Market indices endpoint works
- [ ] Real-time data works when Upstox connected
- [ ] Fallback to cached data works
- [ ] Error handling is graceful
- [ ] No console errors

---

## 📊 Expected Results

### Without Upstox Connection:
```json
{
  "RELIANCE.NS": {
    "price": 2450.50,
    "change": 25.30,
    "change_pct": 1.04,
    "volume": 1234567,
    "timestamp": "2024-01-15T15:30:00",
    "source": "cached"
  }
}
```

### With Upstox Connection:
```json
{
  "RELIANCE.NS": {
    "price": 2452.75,
    "change": 27.55,
    "change_pct": 1.13,
    "volume": 1234567,
    "timestamp": "2024-01-15T16:45:00",
    "source": "upstox"
  }
}
```

---

## 🚀 Next Steps After Testing

If all tests pass:
- ✅ Phase 2.1 is working correctly
- ➡️ Proceed to Phase 2.2 (Order Management)

If issues found:
- Report specific errors
- Check logs in terminal
- Verify Upstox credentials
