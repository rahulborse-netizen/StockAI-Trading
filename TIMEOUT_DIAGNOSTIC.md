# Connection Timeout Diagnostic Guide

## Current Issue
Connection timeout after 15-30 seconds when trying to connect to Upstox.

## What I Fixed

### 1. Removed Slow Network Detection from OAuth Flow
- Removed `_get_local_ip()` call that was causing 2-second delays
- OAuth flow now returns immediately (just builds a URL string)

### 2. Increased Timeout
- Frontend timeout increased from 15 to 30 seconds
- Should give more time for slow networks

### 3. Added Detailed Logging
- Every step of the connection process is now logged
- Check Flask terminal to see exactly where it hangs

### 4. Added Test Endpoint
- New endpoint: `/api/upstox/test` (GET)
- Use this to verify server is responding

## Diagnostic Steps

### Step 1: Test Server Response
Open in browser:
```
http://localhost:5000/api/upstox/test
```

**Expected:** JSON response like:
```json
{
  "status": "success",
  "message": "Server is responding",
  "timestamp": "2024-..."
}
```

**If this fails:**
- Flask server is not running or crashed
- Restart with: `python start_simple.py`

### Step 2: Check Flask Server Logs
When you click "Connect", watch the Flask terminal. You should see:
```
[Phase 1.2] ===== CONNECT REQUEST RECEIVED =====
[Phase 1.2] Request method: POST
[Phase 1.2] Parsing request JSON...
[Phase 1.2] JSON parsed successfully
[Phase 1.2] Connect request - API Key: c4599604..., Redirect URI: http://localhost:5000/callback
[Phase 1.2] Starting OAuth flow...
[Phase 1.2] Creating UpstoxAPI instance...
[Phase 1.2] UpstoxAPI instance created
[Phase 1.2] Saving connection to session...
[Phase 1.2] Connection saved to session
[Phase 1.2] Building authorization URL...
[Phase 1.2] Authorization URL generated: https://api.upstox.com/v2/login/authorization/dialog?...
[Phase 1.2] Returning auth_required response...
```

**If logs stop at a specific step:**
- That's where the hang is occurring
- Share the last log line you see

### Step 3: Check Browser Console
Press F12 → Console tab. Look for:
- `[DEBUG] Connect response:` - Should show the response
- `[TIMEOUT]` - Indicates timeout occurred
- Any red error messages

### Step 4: Verify Redirect URI in Upstox Portal
1. Go to: https://account.upstox.com/developer/apps
2. Click your app
3. Verify Redirect URL is exactly: `http://localhost:5000/callback`
4. Must match EXACTLY (case-sensitive, no trailing spaces)

## Common Causes

### 1. Flask Server Not Responding
**Symptoms:**
- Timeout immediately
- No logs in Flask terminal
- Test endpoint doesn't work

**Fix:**
- Restart Flask server
- Check for Python errors in terminal
- Verify port 5000 is not in use

### 2. Network/Firewall Blocking
**Symptoms:**
- Timeout after a few seconds
- Logs show "Starting OAuth flow..." but nothing after

**Fix:**
- Check company firewall settings
- Try from different network
- Check if Upstox API is accessible: https://api.upstox.com

### 3. Import/Module Error
**Symptoms:**
- Flask server crashes on startup
- Error in terminal about missing module

**Fix:**
- Run: `pip install -r requirements.txt`
- Check all imports in `app.py`

### 4. Session/Flask Issue
**Symptoms:**
- Logs show "Saving connection to session..." but hangs

**Fix:**
- Clear browser cookies for localhost
- Restart Flask server
- Try in incognito window

## Next Steps

1. **Restart Flask server** with new code
2. **Refresh browser** (Ctrl+F5)
3. **Test endpoint first**: http://localhost:5000/api/upstox/test
4. **Try connecting** and watch Flask logs
5. **Share the last log line** you see before timeout

This will help identify exactly where the hang is occurring.
