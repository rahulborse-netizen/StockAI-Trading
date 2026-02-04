# 🚀 LIVE TRADING MODE - Full Function App

## ✅ What's Working Now

### **1. Live Trading Enabled**
- **No paper trading mode** - All orders execute with **real money**
- Orders go directly to Upstox exchange
- Full order management (place, cancel, modify)

### **2. Multi-Device Support**
- **Company laptop**: Access via `http://localhost:5000`
- **Personal device**: Access via `http://YOUR_IP:5000` (shown in console)
- Auto-detects network IP for redirect URI
- Works on same WiFi network

### **3. Complete Upstox Integration**
- ✅ OAuth2 authentication (with no-popup fallback for corporate browsers)
- ✅ Real holdings from your Upstox account
- ✅ Real positions tracking
- ✅ Order history
- ✅ Live order placement (MARKET, LIMIT, SL orders)
- ✅ Session persistence (survives page refresh)

### **4. AI Trading Signals**
- Real-time signal generation using ML model
- Entry/exit levels calculation
- Stop loss and target levels
- Probability-based BUY/HOLD signals

### **5. Full Dashboard Features**
- Market indices (NIFTY, SENSEX, BANKNIFTY, VIX)
- Watchlist management
- Price alerts
- Holdings tracking with P&L
- Positions monitoring
- Order management
- Trading signals with entry/exit levels

## 🔧 Setup Instructions

### **Step 1: Install Dependencies**
```bash
pip install -r requirements.txt
```

### **Step 2: Configure Environment (Optional)**
Create `.env` file:
```env
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_SECRET_KEY=your-secret-key-here
```

### **Step 3: Start the Server**
```bash
python start_simple.py
# OR
python run_web.py
```

You'll see:
```
============================================================
AI Trading Dashboard - LIVE TRADING MODE
============================================================
Local access:  http://localhost:5000
Network access: http://192.168.1.4:5000
============================================================
⚠️  LIVE TRADING ENABLED - Orders will execute with real money!
============================================================
```

### **Step 4: Connect Upstox**

1. **Get API Credentials:**
   - Go to https://upstox.com/developer
   - Create an app
   - Copy API Key and Secret

2. **Set Redirect URIs in Upstox Portal:**
   - `http://localhost:5000/callback` (for localhost)
   - `http://YOUR_IP:5000/callback` (for network access - use IP shown in console)

3. **Connect in Dashboard:**
   - Click "Connect" button (top right)
   - Enter API Key and Secret
   - Leave Redirect URI empty (auto-detects)
   - Click "Connect"
   - Authorize in popup (or use the link if popup blocked)

### **Step 5: Start Trading**

1. **Add stocks to watchlist**
2. **View AI signals** (click on any stock)
3. **Place orders** (click Buy/Sell buttons)
4. **Monitor holdings** and positions

## 📱 Access from Personal Device

1. **Find your computer's IP** (shown in console when server starts)
2. **On your phone/laptop**, open: `http://YOUR_IP:5000`
3. **Both devices must be on same WiFi**

## ⚠️ Important Notes

### **Live Trading Warning**
- **ALL ORDERS ARE REAL** - No paper trading mode
- Test with small quantities first
- Verify ticker format: `RELIANCE.NS` (not `RELIANCE`)
- Supported tickers: See `src/web/instrument_master.py` TICKER_MAP

### **Supported Tickers**
Currently supports **51+ NIFTY50 stocks** including:
- RELIANCE.NS, TCS.NS, HDFCBANK.NS, ICICIBANK.NS, INFY.NS
- LT.NS, SBIN.NS, KOTAKBANK.NS, AXISBANK.NS
- And more... (see code for full list)

**To add more tickers:**
- Edit `src/web/instrument_master.py` → `TICKER_MAP`
- Or use Upstox API search (requires authentication)

### **Instrument Key Resolution**
- First tries hardcoded map (fast)
- Falls back to instrument master download (if available)
- Shows helpful error if ticker not found

## 🐛 Troubleshooting

### **"Instrument key not found"**
- Check ticker format: Must end with `.NS` for NSE stocks
- Example: `RELIANCE.NS` ✅ (not `RELIANCE` ❌)
- Add ticker to `TICKER_MAP` if needed

### **"Connection failed"**
- Verify API Key/Secret are correct
- Check redirect URI matches exactly in Upstox portal
- Try disconnecting and reconnecting

### **"Can't access from personal device"**
- Check firewall allows port 5000
- Ensure both devices on same WiFi
- Verify IP address is correct

### **"Popup blocked" (corporate browsers)**
- Use the authorization link shown in modal
- Copy and open in new tab
- Or allow popups for localhost

## 📊 Current Features

✅ Live order placement  
✅ Real-time holdings  
✅ Positions tracking  
✅ Order history  
✅ AI trading signals  
✅ Price alerts  
✅ Watchlist management  
✅ Multi-device access  
✅ Mobile responsive  

## 🚧 Future Enhancements

- [ ] WebSocket real-time price updates
- [ ] Advanced order types (bracket, cover)
- [ ] Portfolio analytics
- [ ] Strategy backtesting UI
- [ ] More ticker mappings (auto-fetch from Upstox)

---

**Ready to trade!** 🎯

**Remember:** Start with small quantities and test thoroughly before scaling up.
