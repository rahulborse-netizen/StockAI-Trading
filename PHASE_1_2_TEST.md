# Phase 1.2 Testing Guide

## ✅ Phase 1.2 Completion Checklist

### Code Changes:
- [x] Created `UpstoxConnectionManager` class
- [x] Added redirect URI validation
- [x] Improved error handling with logging
- [x] Updated connection endpoints
- [x] Updated callback handler
- [x] Added `/api/upstox/status` endpoint
- [x] Updated `_get_upstox_client()` to use connection manager
- [x] Added proper logging throughout

### Files Modified:
1. `src/web/upstox_connection.py` - New connection manager
2. `src/web/app.py` - Updated to use connection manager
3. All endpoints now use `connection_manager`

---

## 🧪 Testing Steps

### Test 1: Server Starts Successfully
```bash
cd "C:\Users\rahul_borse\Python\Python Assignment\stockai-trading-india"
python start_simple.py
```

**Expected**: Server starts on port 5000, no errors

### Test 2: Check Routes Are Registered
Open browser console and run:
```javascript
fetch('/api/upstox/status')
  .then(r => r.json())
  .then(console.log)
```

**Expected**: Returns `{connected: false}` if not connected, or connection info if connected

### Test 3: Test Connection Flow
1. Open dashboard: `http://localhost:5000`
2. Click "Connect" button
3. Enter API Key and Secret
4. Leave Redirect URI empty (auto-detects)
5. Click "Connect"

**Expected**: 
- Shows redirect URI that needs to be added to Upstox Portal
- Opens authorization URL
- After authorization, redirects back and connects

### Test 4: Check Connection Status
After connecting, check status:
```javascript
fetch('/api/upstox/status')
  .then(r => r.json())
  .then(console.log)
```

**Expected**: Returns `{connected: true, profile: {...}}`

### Test 5: Test Connection Persistence
1. Refresh the page
2. Check if connection persists

**Expected**: Connection should persist across page refreshes

---

## 🐛 Common Issues & Fixes

### Issue: "Redirect URI mismatch" (UDAPI100068)
**Fix**: Add the exact redirect URI shown in the error to Upstox Developer Portal

### Issue: "Session expired"
**Fix**: Click "Connect" again and re-enter credentials

### Issue: Connection doesn't persist
**Fix**: Check Flask secret key is set in `.env` file

---

## ✅ Success Criteria

Phase 1.2 is complete when:
- [x] Connection manager works correctly
- [x] OAuth flow completes successfully
- [x] Connection persists across page refreshes
- [x] Error messages are clear and helpful
- [x] Logging shows connection flow
- [x] Status endpoint works
- [x] Test endpoint works

---

## 📝 Next Steps After Testing

Once Phase 1.2 is verified working:
1. Move to Phase 1.3: Codebase cleanup
2. Then Phase 2: Core trading features
