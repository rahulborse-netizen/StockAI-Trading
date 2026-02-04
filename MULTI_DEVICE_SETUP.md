# Multi-Device Setup Guide

## Access from Company Laptop AND Personal Device

This app is configured to work on **both your company laptop and personal device** on the same network.

### Quick Start

1. **Start the server** (on your company laptop or personal device):
   ```bash
   python start_simple.py
   # OR
   python run_web.py
   ```

2. **Note the network URL** shown in the console:
   ```
   Network access: http://192.168.1.100:5000
   ```

3. **On your other device** (phone/laptop), open:
   ```
   http://192.168.1.100:5000
   ```
   (Replace with your actual IP)

### Upstox Connection (Multi-Device)

When connecting Upstox:

1. **Leave Redirect URI empty** - it will auto-detect
2. The app will use your **network IP** automatically
3. **In Upstox Developer Portal**, add **BOTH** redirect URIs:
   - `http://localhost:5000/callback` (for localhost access)
   - `http://YOUR_IP:5000/callback` (for network access)
   
   Example:
   - `http://192.168.1.100:5000/callback`

### Finding Your IP Address

**Windows:**
```powershell
ipconfig
# Look for "IPv4 Address" under your active network adapter
```

**Mac/Linux:**
```bash
ifconfig | grep "inet "
# OR
hostname -I
```

### Firewall Settings

**Windows Firewall:**
1. Open Windows Defender Firewall
2. Click "Allow an app through firewall"
3. Add Python or allow port 5000

**Or via PowerShell (Admin):**
```powershell
New-NetFirewallRule -DisplayName "AI Trading App" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
```

### Environment Variables (Optional)

Create a `.env` file in the project root:

```env
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_SECRET_KEY=your-secret-key-here
```

### Troubleshooting

**Can't access from other device:**
- Check firewall settings
- Ensure both devices are on the same WiFi network
- Verify the IP address is correct
- Try `http://YOUR_IP:5000/api/network_info` to see connection info

**Upstox redirect fails:**
- Make sure you added the network redirect URI in Upstox Developer Portal
- Check that the IP hasn't changed (restart router = new IP usually)

**Connection works but orders fail:**
- Instrument master is downloading in background (first time only)
- Check browser console for errors
- Verify ticker format (e.g., `RELIANCE.NS` not `RELIANCE`)

---

**Ready to trade!** 🚀
