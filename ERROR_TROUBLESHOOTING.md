# Error Troubleshooting Guide

## Common Errors and Solutions

### 1. Redirect URI Mismatch Error

**Error Message:**
- "redirect_uri mismatch"
- "Invalid redirect URI"
- "UDAPI100068: Check your client_id and redirect_uri"

**Solution:**
1. Go to Upstox Developer Portal: https://account.upstox.com/developer/apps
2. Click on your app ("upstok api")
3. In "Redirect URL" field, enter EXACTLY:
   ```
   http://localhost:5000/callback
   ```
4. **Important:**
   - Must be `http://` (NOT `https://`)
   - Must be `localhost` (NOT `127.0.0.1`)
   - Must be port `5000` (NOT `88` or any other port)
   - Must end with `/callback` (NOT `/stocktrading` or anything else)
5. Click "Save" or "Update"
6. Try connecting again

### 2. Connection Timeout Error

**Error Message:**
- "Connection timeout"
- "Request took too long"
- "Connection failed"

**Solution:**
1. Check your internet connection
2. Make sure Flask server is running
3. Try refreshing the page (Ctrl+F5)
4. Check if Upstox API is accessible (try opening https://api.upstox.com in browser)
5. If on company network, check if firewall is blocking Upstox API

### 3. Invalid API Credentials

**Error Message:**
- "Invalid client_id"
- "Authentication failed"
- "Connection failed: Invalid credentials"

**Solution:**
1. Verify API Key from Upstox Portal:
   - Go to https://account.upstox.com/developer/apps
   - Click on your app
   - Copy the API Key (should look like: `c4599604-5513-4aea-b256-f725a41bcb11`)
2. Verify API Secret:
   - Click the eye icon to reveal the secret
   - Copy it exactly (should look like: `bw7zbs2u4e...`)
3. Make sure app is not expired (check expiry date)
4. Re-enter credentials in the app

### 4. Access Token Expired

**Error Message:**
- "Token expired"
- "Invalid access token"
- "Connection test failed"

**Solution:**
1. Don't use an old access token
2. Use the OAuth flow instead:
   - Leave "Access Token" field empty
   - Click "Connect"
   - Authorize in the popup window
   - The app will get a fresh token automatically

### 5. Session Expired

**Error Message:**
- "Session expired"
- "Missing credentials"
- "Please connect again"

**Solution:**
1. Close the browser tab
2. Restart Flask server (Ctrl+C, then `python start_simple.py`)
3. Open http://localhost:5000 again
4. Click "Connect" and enter credentials again

### 6. Popup Blocked

**Error Message:**
- "Popup blocked"
- "Authorization window not opening"

**Solution:**
1. Allow popups for localhost in your browser settings
2. Or use the "Copy" button in the modal to manually open the authorization URL
3. Paste the URL in a new tab and authorize

## Step-by-Step Connection Process

### Method 1: Using OAuth Flow (Recommended)

1. **In Upstox Portal:**
   - Add redirect URI: `http://localhost:5000/callback`
   - Save changes

2. **In the App:**
   - Enter API Key
   - Enter API Secret
   - Leave Redirect URI empty (auto-detects to `http://localhost:5000/callback`)
   - Leave Access Token empty
   - Click "Connect"

3. **Authorization:**
   - A popup window opens with Upstox login
   - Login with your Upstox credentials
   - Click "Authorize" or "Allow"
   - Window closes automatically
   - Connection should be successful

### Method 2: Using Direct Access Token

1. **In Upstox Portal:**
   - Click "Generate" button next to "Access Token"
   - Copy the generated token

2. **In the App:**
   - Enter API Key
   - Enter API Secret
   - Enter Redirect URI: `http://localhost:5000/callback`
   - Paste the Access Token
   - Click "Connect"

## Debugging Steps

### Check Flask Server Logs

Look at the terminal where Flask is running. You should see logs like:
```
[Phase 1.2] Connect request - API Key: c4599604..., Redirect URI: http://localhost:5000/callback
[Phase 1.2] Starting OAuth flow...
[Phase 1.2] Generated auth URL: https://api.upstox.com/v2/login/authorization/dialog?...
```

If you see errors, note them down.

### Check Browser Console

1. Press F12 to open Developer Tools
2. Go to "Console" tab
3. Look for red error messages
4. Common errors:
   - `AbortError`: Request timeout
   - `TypeError`: JavaScript error
   - `NetworkError`: Cannot reach server

### Verify Redirect URI

Run this command to test:
```bash
python check_errors.py
```

This will verify:
- Redirect URI validation
- API initialization
- Flask routes

## Still Having Issues?

1. **Check all requirements:**
   - Flask server is running
   - Browser is at http://localhost:5000
   - Upstox Portal has correct redirect URI
   - API Key and Secret are correct

2. **Try these steps:**
   - Clear browser cache (Ctrl+Shift+Delete)
   - Restart Flask server
   - Try in incognito/private window
   - Check if another app is using port 5000

3. **Get detailed error:**
   - Check Flask terminal for full error message
   - Check browser console (F12) for JavaScript errors
   - Share the exact error message for help
