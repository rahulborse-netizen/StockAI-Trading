# Upstox API Connection Guide

## Step-by-Step Setup

### Step 1: Get API Credentials

1. Go to [Upstox Developer Portal](https://upstox.com/developer)
2. Log in with your Upstox account
3. Click **"Create App"** or **"My Apps"**
4. Create a new application
5. Note down:
   - **API Key** (Client ID)
   - **API Secret** (Client Secret)

### Step 2: Configure Redirect URI

1. In your Upstox app settings, set the **Redirect URI** to:
   ```
   http://localhost:5000/callback
   ```
2. Save the settings

### Step 3: Connect in Dashboard

#### Option A: Using OAuth Flow (Recommended)

1. Open the dashboard
2. Click **"Connect Upstox"** button
3. Enter:
   - **API Key**: Your Client ID
   - **API Secret**: Your Client Secret
   - **Redirect URI**: `http://localhost:5000/callback`
4. Click **"Connect"**
5. A popup window will open asking you to authorize the app
6. Log in to Upstox and authorize
7. The window will close automatically
8. You should see "Connected" status

#### Option B: Using Access Token Directly

If you already have an access token:

1. Open the dashboard
2. Click **"Connect Upstox"** button
3. Enter:
   - **API Key**: Your Client ID
   - **API Secret**: Your Client Secret
   - **Access Token**: Your existing access token
4. Click **"Connect"**

### Step 4: Verify Connection

After connecting, you should see:
- Green "Connected" status in the top bar
- Orders section should load (if you have any)
- You can now place orders

## Troubleshooting

### Error: "Authorization Failed"

**Causes:**
- Redirect URI doesn't match in Upstox app settings
- Authorization code expired
- Invalid API credentials

**Solutions:**
1. Verify Redirect URI matches exactly: `http://localhost:5000/callback`
2. Make sure API Key and Secret are correct
3. Try the connection process again

### Error: "Connection Failed"

**Causes:**
- Invalid access token
- Token expired
- Network issues

**Solutions:**
1. Check your internet connection
2. Verify API credentials are correct
3. Try using OAuth flow instead of direct token
4. Check if Upstox API is accessible

### Error: "Not authenticated"

**Causes:**
- Access token not set
- Session expired

**Solutions:**
1. Reconnect using the Connect button
2. Make sure you completed the authorization flow

### Popup Window Blocked

**Solution:**
1. Allow popups for localhost in your browser
2. Or manually open the authorization URL from the error message

## API Endpoints Used

- **Authorization**: `https://account.upstox.com/developer/apps/{api_key}/authorize`
- **Token Exchange**: `https://api.upstox.com/v2/login/authorization/token`
- **Profile**: `https://api.upstox.com/v2/user/profile`
- **Orders**: `https://api.upstox.com/v2/order/retrieve-all`
- **Place Order**: `https://api.upstox.com/v2/order/place`

## Security Notes

⚠️ **Important:**
- Never share your API Secret or Access Token
- Access tokens expire - you may need to reconnect
- Use HTTPS in production (not HTTP)
- Store credentials securely

## Testing Connection

After connecting, you can test by:
1. Clicking "Place Order" button
2. Viewing orders in the Orders section
3. The connection status should show "Connected"

## Need Help?

If you're still having issues:
1. Check the browser console for errors (F12)
2. Check the server logs for detailed error messages
3. Verify your Upstox app is active in the developer portal
4. Make sure you're using the correct API version (v2)
