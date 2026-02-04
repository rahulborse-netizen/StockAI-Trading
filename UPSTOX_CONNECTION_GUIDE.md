# Upstox Connection Guide - Step by Step

## 🔒 Security Note
**NEVER share your API keys in chat or public places!** Always enter them directly in the app.

## Step-by-Step Connection Process

### Step 1: Get Your Upstox API Credentials

1. Go to [Upstox Developer Portal](https://upstox.com/developer)
2. Log in with your Upstox account
3. Click **"My Apps"** or **"Create App"**
4. Create a new application (or use existing)
5. Copy these details:
   - **API Key** (also called Client ID)
   - **API Secret** (also called Client Secret)

### Step 2: Configure Redirect URI

In your Upstox app settings:
1. Find **"Redirect URI"** field
2. Set it to exactly: `http://localhost:5000/callback`
3. **Save** the settings

### Step 3: Connect in the Dashboard

1. **Open the dashboard** in your browser: `http://localhost:5000`

2. **Click "Connect" button** in the top right (or "Connect Upstox" button)

3. **Enter your credentials:**
   - **API Key**: Paste your API Key
   - **API Secret**: Paste your API Secret
   - **Redirect URI**: Should already be `http://localhost:5000/callback`
   - **Access Token** (Optional): Leave empty for first-time setup

4. **Click "Connect" button**

### Step 4: Authorize the App

1. A **popup window** will open (or you'll see a URL)
2. If popup is blocked:
   - Allow popups for localhost
   - Or copy the URL and open in a new tab
3. **Log in to Upstox** in the popup
4. **Authorize the application**
5. The popup will close automatically
6. You should see **"Connected"** status in the dashboard

### Step 5: Verify Connection

After connecting:
- Status should show **"Connected"** (green)
- You can now:
  - View orders
  - Place orders
  - Check positions
  - View holdings

## Troubleshooting

### "Popup Blocked"
**Solution:**
- Allow popups for `localhost:5000`
- Or manually open the authorization URL shown in the notification

### "Connection Failed"
**Possible causes:**
1. **Wrong API Key/Secret** - Double-check you copied them correctly
2. **Redirect URI mismatch** - Must be exactly `http://localhost:5000/callback`
3. **Network issue** - Check internet connection
4. **Upstox API down** - Try again later

**Fix:**
- Verify credentials in Upstox Developer Portal
- Check Redirect URI matches exactly
- Try disconnecting and reconnecting

### "Authorization Failed"
**Solution:**
- Make sure you completed the authorization in the popup
- Check if you're logged into the correct Upstox account
- Try the connection process again

### Buttons Not Clickable
**Solution:**
- Refresh the page (Ctrl+F5)
- Check browser console for errors (F12)
- Make sure JavaScript is enabled
- Try a different browser

## Quick Test

After connecting, test by:
1. Click **"Orders"** tab - should show your orders (if any)
2. Click **"Place Order"** - should open order form
3. Status should show **"Connected"** in green

## Security Best Practices

✅ **DO:**
- Enter API keys directly in the app
- Keep API keys private
- Use different keys for testing vs production
- Revoke keys if compromised

❌ **DON'T:**
- Share API keys in chat/email
- Commit keys to git
- Use production keys for testing
- Leave keys in screenshots

## Need Help?

If you're still having issues:
1. Check browser console (F12) for errors
2. Check server logs for detailed error messages
3. Verify your Upstox app is active in Developer Portal
4. Make sure you're using Upstox API v2

---

**Ready to connect?** Open the dashboard and click "Connect"! 🚀
