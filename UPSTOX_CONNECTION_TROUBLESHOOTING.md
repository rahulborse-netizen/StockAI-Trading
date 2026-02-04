# Upstox Connection Troubleshooting Guide

## ✅ What I Fixed

I've added comprehensive error logging and debugging throughout the Upstox connection flow:

1. **Enhanced Error Messages**: All errors now show detailed messages with helpful hints
2. **Debug Logging**: Console and server logs now show exactly what's happening at each step
3. **Better OAuth Flow**: Improved handling of authorization code exchange
4. **Session Management**: Better error messages when session expires
5. **Redirect URI Validation**: Clearer messages about redirect URI mismatches

## 🔍 How to Debug Connection Issues

### Step 1: Check Browser Console
1. Open your browser's Developer Tools (F12)
2. Go to the **Console** tab
3. Try connecting to Upstox
4. Look for messages starting with `[DEBUG]` or `[ERROR]`

### Step 2: Check Server Logs
The Flask server terminal will show detailed logs:
- `[DEBUG]` messages show the connection flow
- `[ERROR]` messages show what went wrong

### Step 3: Verify Upstox Developer Portal Settings

**Critical**: Your redirect URI must match **EXACTLY** in Upstox Portal:

1. Go to: https://account.upstox.com/developer/apps
2. Open your app
3. Check **Redirect URI** field
4. It should contain **BOTH**:
   ```
   http://localhost:5000/callback
   http://192.168.1.4:5000/callback
   ```
   (Replace `192.168.1.4` with your actual network IP if different)

### Step 4: Common Issues & Fixes

#### Issue: "Redirect URI mismatch"
**Fix**: 
- Copy the exact redirect URI shown in the error message
- Add it to Upstox Developer Portal
- Make sure there are no trailing slashes or extra characters

#### Issue: "Session expired"
**Fix**:
- Close the modal
- Click "Connect" again
- Re-enter your API Key and Secret

#### Issue: "Authentication failed" after authorization
**Fix**:
- Check server logs for the exact error
- Verify API Key and Secret are correct
- Make sure the redirect URI in Upstox Portal matches exactly

#### Issue: "Connection failed" with access token
**Fix**:
- The access token might be expired
- Try the OAuth flow instead (leave access token empty)
- Generate a new access token from Upstox

## 📋 Connection Checklist

Before connecting, verify:

- [ ] API Key is correct (starts with `c4599604-...`)
- [ ] API Secret is correct (long string)
- [ ] Redirect URI is added in Upstox Developer Portal
- [ ] Redirect URI matches exactly (no trailing slash)
- [ ] App is **Active** in Upstox Developer Portal
- [ ] Server is running on port 5000
- [ ] Browser console is open to see errors

## 🔧 Testing the Connection

### Method 1: Use Direct Access Token
1. Get access token from Upstox (if you have one)
2. Enter API Key, Secret, and Access Token
3. Click "Connect"
4. Should connect immediately

### Method 2: Use OAuth Flow
1. Enter API Key and Secret
2. Leave Access Token empty
3. Leave Redirect URI empty (auto-detects)
4. Click "Connect"
5. Authorize in the popup window
6. Should redirect back and connect

## 🐛 Debug Mode

To see even more details, check:

1. **Browser Console** (F12 → Console tab)
2. **Server Terminal** (where Flask is running)
3. **Network Tab** (F12 → Network tab) - see API requests/responses

## 📞 Still Having Issues?

If connection still fails after checking everything:

1. **Copy the exact error message** from:
   - Browser console
   - Server terminal
   - The notification popup

2. **Check these specific things**:
   - What redirect URI is shown in the error?
   - What redirect URI is in Upstox Portal?
   - Are they exactly the same (character-by-character)?

3. **Try this test**:
   - Open browser console
   - Run: `fetch('/api/network_info').then(r => r.json()).then(console.log)`
   - Check the `redirect_uri` value
   - Make sure this exact value is in Upstox Portal

## 🎯 Quick Test

Run this in browser console to test connection status:
```javascript
fetch('/api/upstox/test')
  .then(r => r.json())
  .then(console.log)
```

If you see `"Not connected"`, you need to connect first.
If you see an error, check the error message for details.
