# Fix UDAPI100068 Error - Redirect URI Mismatch

## 🔴 The Problem

You're seeing this error:
```json
{
  "status": "error",
  "errors": [{
    "errorCode": "UDAPI100068",
    "message": "Check your client_id' and 'redirect_uri'; one or both are Incorrect."
  }]
}
```

This means the **redirect URI** in your code doesn't match what's registered in Upstox Developer Portal.

## ✅ The Solution (Step-by-Step)

### Step 1: Find Your Exact Redirect URI

When you click "Connect" in the app, it will show you the redirect URI being used. Look for:
- A notification showing the redirect URI
- The redirect URI field in the modal (auto-filled)
- Browser console message: `[DEBUG] Redirect URI being used: ...`

**Common redirect URIs:**
- `http://localhost:5000/callback` (if using same computer)
- `http://192.168.1.4:5000/callback` (if using network IP - your IP may differ)

### Step 2: Add Redirect URI to Upstox Portal

1. **Go to Upstox Developer Portal:**
   - https://account.upstox.com/developer/apps

2. **Open your app** (or create one if you haven't)

3. **Find "Redirect URI" or "Callback URL" field**

4. **Add the EXACT redirect URI** shown in Step 1
   - Must match **EXACTLY** (character-by-character)
   - No trailing slashes
   - Exact IP address (if using network IP)
   - Exact port number (5000)

5. **Save the changes**

### Step 3: Verify API Key

While you're in Upstox Portal, verify:
- Your **API Key** matches what you entered in the app
- Your **API Secret** matches what you entered
- The app status is **Active**

### Step 4: Try Connecting Again

1. Go back to your trading app
2. Click "Connect" again
3. The redirect URI should now match and authorization should work

## 🎯 Quick Checklist

Before clicking "Connect", verify:

- [ ] Redirect URI is added in Upstox Developer Portal
- [ ] Redirect URI matches EXACTLY (no extra spaces, exact IP, exact port)
- [ ] API Key is correct (starts with `c4599604-...`)
- [ ] API Secret is correct
- [ ] App is **Active** in Upstox Portal

## 💡 Pro Tip: Add Both Redirect URIs

To avoid issues, add **BOTH** redirect URIs in Upstox Portal:

1. `http://localhost:5000/callback` (for same computer)
2. `http://192.168.1.4:5000/callback` (for network access - replace with your IP)

This way, it works whether you access from the same computer or from your phone/other device.

## 🔍 How to Find Your Network IP

If you need to find your network IP:

1. **In the app:** Click "Connect" and check the redirect URI shown
2. **Or run this in terminal:**
   ```powershell
   cd "C:\Users\rahul_borse\Python\Python Assignment\stockai-trading-india"
   python -c "import requests; r=requests.get('http://127.0.0.1:5000/api/network_info'); print(r.json()['redirect_uri'])"
   ```

## ⚠️ Common Mistakes

1. **Trailing slash:** `http://localhost:5000/callback/` ❌ (extra slash)
   - Correct: `http://localhost:5000/callback` ✅

2. **Wrong IP:** Using `127.0.0.1` instead of `localhost` or network IP
   - Both work, but must match what's in Portal

3. **Wrong port:** Using port `8080` instead of `5000`
   - Must match exactly

4. **HTTPS vs HTTP:** Using `https://` when app uses `http://`
   - Must match exactly

## 🆘 Still Not Working?

If you've added the redirect URI and it still fails:

1. **Double-check character-by-character:**
   - Copy the redirect URI from the app
   - Paste it into Upstox Portal
   - Make sure there are no extra spaces or characters

2. **Check browser console (F12):**
   - Look for `[DEBUG] Redirect URI being used: ...`
   - Copy that exact value

3. **Check server terminal:**
   - Look for `[DEBUG] Using Redirect URI: ...`
   - Copy that exact value

4. **Try with localhost only first:**
   - Add `http://localhost:5000/callback` to Portal
   - Use `http://localhost:5000/callback` in the app
   - Once that works, add network IP

## 📞 Need More Help?

If it still doesn't work after following these steps:
1. Share the exact redirect URI shown in the app
2. Share a screenshot of your Upstox Portal redirect URI field
3. Check if there are any other errors in browser console (F12)
