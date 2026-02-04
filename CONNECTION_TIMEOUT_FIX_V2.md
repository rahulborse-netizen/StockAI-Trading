# Connection Timeout Fix - Version 2

## Problem
User reported: "I'm able to click all the boxes but not able to connect to my upstok account, taking long time"

## Root Cause Analysis
The connection was hanging due to network detection functions that could block indefinitely on company laptops with restricted network access:

1. **`_get_local_ip()` function**: Connected to `8.8.8.8:80` without a timeout, which could hang indefinitely if:
   - Company firewall blocks external connections
   - Network requires proxy authentication
   - DNS resolution is slow or blocked

2. **Multiple calls to `_get_local_ip()`**: The function was called in several places:
   - `_get_base_url()` - when determining redirect URI
   - `connect_upstox()` - when getting suggested redirect URIs (twice)

## Fixes Applied

### 1. Added Timeout to `_get_local_ip()`
```python
def _get_local_ip():
    """Get local IP address for multi-device access (with timeout to prevent hanging)"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)  # 2 second timeout to prevent hanging
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except (socket.timeout, socket.error, OSError) as e:
        logger.debug(f"Could not determine local IP: {e}")
        return "127.0.0.1"  # Fast fallback
```

**Key improvements:**
- Added `s.settimeout(2)` - 2 second timeout prevents indefinite hanging
- Better exception handling for network errors
- Fast fallback to `127.0.0.1` if detection fails

### 2. Optimized `_get_base_url()`
- Added try-except wrapper for robustness
- Better error handling and logging
- Fast fallback to localhost if network detection fails

### 3. Protected `get_suggested_redirect_uris()` Calls
- Wrapped both calls in try-except blocks
- Added fallback to `['http://localhost:5000/callback']` if network detection fails
- Prevents the entire connection flow from hanging

## Testing
To test the fix:

1. **Refresh your browser** (Ctrl+F5) to ensure all changes are loaded
2. **Try connecting to Upstox** again
3. **Expected behavior:**
   - Connection should complete within 2-3 seconds (instead of hanging)
   - If network detection fails, it will fallback to localhost automatically
   - You should see either:
     - Success message (if access token is valid)
     - Authorization URL (if OAuth flow is needed)
     - Clear error message (if credentials are invalid)

## Additional Notes
- The 2-second timeout is a good balance between speed and reliability
- On company laptops with strict firewalls, the app will automatically use `localhost` instead of trying to detect network IP
- This fix maintains backward compatibility - existing connections will continue to work

## Next Steps
If connection still fails after this fix:
1. Check browser console (F12) for any JavaScript errors
2. Check Flask server logs for detailed error messages
3. Verify your Upstox API credentials are correct
4. Ensure the redirect URI in Upstox Developer Portal matches exactly
