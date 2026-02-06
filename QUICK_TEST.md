# Quick Test - 3 Steps

## Fastest Way to Check if It's Working

### Step 1: Restart Server
```bash
# Stop: Press Ctrl+C in server terminal
# Start: 
python run_web.py
```

### Step 2: Open Browser
Visit: `http://localhost:5000/api/signals/RELIANCE.NS`

### Step 3: Check Result

**✅ WORKING** = You see JSON with:
- `"signal": "BUY"` (or SELL/HOLD)
- `"probability": 0.65` (or similar)
- `"elite_system": true`
- NO error message

**❌ NOT WORKING** = You see:
- Error message
- Dates like `2025-02-05` or `2026-02-05`
- Status 500 error

---

## That's It!

If you see JSON with signal data → **It's working!** ✅
If you see an error → **Restart server and try again** 🔄
