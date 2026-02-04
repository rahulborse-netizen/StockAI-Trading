# Connection Troubleshooting - Redirect URI Correct But Still Not Working

## Your Redirect URI is Correct! ✓
You have: `http://localhost:5000/callback` - This is perfect!

## Common Issues When Redirect URI is Correct

### 1. **Did You SAVE the Redirect URI in Upstox Portal?**
   - ⚠️ **Most Common Issue**: Just entering the URI is not enough!
   - You must click **"Save"** or **"Update"** button in Upstox Portal
   - After saving, wait 10-30 seconds for changes to propagate

### 2. **Session Expired**
   - If you entered credentials earlier, the session might have expired
   - **Fix**: 
     1. Close the browser tab
     2. Go back to dashboard: http://localhost:5000
     3. Click "Connect" again
     4. Enter API Key and Secret again

### 3. **Flask Server Not Restarted**
   - If you made code changes, restart the server
   - **Fix**:
     1. Stop Flask server (Ctrl+C in terminal)
     2. Start again: `python start_simple.py`
     3. Refresh browser (Ctrl+F5)

### 4. **Browser Cache**
   - Old JavaScript might be cached
   - **Fix**: 
     - Press Ctrl+Shift+Delete to clear cache
     - Or use Incognito/Private window
     - Or hard refresh: Ctrl+F5

### 5. **Check Flask Terminal Logs**
   When you try to connect, watch the Flask terminal. You should see:
   ```
   [Phase 1.2] ===== CONNECT REQUEST RECEIVED =====
   [Phase 1.2] Starting OAuth flow...
   [Phase 1.2] Building authorization URL...
   [Phase 1.2] Returning auth_required response...
   ```
   
   If you see errors, note them down.

### 6. **After Authorization - Check Callback**
   After you login to Upstox and authorize, check Flask logs for:
   ```
   [Phase 1.2] Callback received - Code: Yes
   [Phase 1.2] Using redirect_uri: http://localhost:5000/callback
   [Phase 1.2] Attempting to authenticate with auth code...
   ```
   
   If you see "Invalid Credentials" error, it means:
   - Redirect URI in Upstox Portal doesn't match exactly
   - Or it wasn't saved properly

## Step-by-Step Fix

### Step 1: Verify Redirect URI is Saved
1. Go to: https://account.upstox.com/developer/apps
2. Click your app ("upstok api")
3. Check "Redirect URL" field
4. Should show: `http://localhost:5000/callback`
5. If it's different or empty, enter it and click **"Save"** or **"Update"**
6. Wait 30 seconds

### Step 2: Restart Flask Server
```bash
# Stop current server (Ctrl+C)
cd "C:\Users\rahul_borse\Python\Python Assignment\stockai-trading-india"
python start_simple.py
```

### Step 3: Clear Browser State
- Close all browser tabs with localhost:5000
- Clear cookies for localhost (or use Incognito)
- Open fresh: http://localhost:5000

### Step 4: Try Connecting Again
1. Click "Connect" button
2. Enter API Key and Secret
3. Leave Redirect URI empty (auto-detects)
4. Click "Connect"
5. Watch Flask terminal for logs

### Step 5: After Authorization
1. Login to Upstox in the popup
2. Click "Authorize" or "Allow"
3. Watch Flask terminal - should see success message
4. If error, check the exact error message

## What Error Are You Seeing?

### If you see "Connection timeout":
- Check Flask server is running
- Check internet connection
- Try again (might be temporary)

### If you see "Invalid Credentials" (UDAP1100016):
- Redirect URI mismatch (even if it looks correct)
- Make sure it's SAVED in Upstox Portal
- Try disconnecting and reconnecting

### If you see "Session expired":
- Close browser and restart Flask server
- Try connecting again

## Still Not Working?

1. **Check Flask Terminal Logs** - Share the last 10-20 lines
2. **Check Browser Console** (F12) - Any JavaScript errors?
3. **Try in Incognito Window** - Rules out cache issues
4. **Verify API Key/Secret** - Make sure they're correct from Upstox Portal

## Quick Test

Run this to verify everything:
```bash
python diagnose_connection_issue.py
```

This will check:
- Server is running
- Endpoint is working
- Redirect URI format is correct
