# How to Run - Trading Signals & Dashboard

## 🎯 Two Ways to Get Trading Signals

### Option 1: Command-Line Script (Quick Signals) ⚡
**Best for**: Quick signal analysis, no browser needed

```bash
python elite_trading_system.py
```

**What you get:**
- ✅ Trading signals in terminal
- ✅ BUY/SELL/HOLD recommendations
- ✅ Entry, stop loss, targets
- ✅ Risk/reward ratios
- ✅ Top opportunities summary

**No browser needed** - Everything in terminal!

---

### Option 2: Web Dashboard (Full Interface) 🌐
**Best for**: Full dashboard, charts, real-time updates

```bash
python run_web.py
```

Then open browser:
```
http://localhost:5000
```

**What you get:**
- ✅ Full web dashboard
- ✅ Trading signals on dashboard
- ✅ Real-time price updates
- ✅ Charts and analytics
- ✅ Order management
- ✅ Portfolio tracking
- ✅ Interactive interface

---

## 📋 Quick Comparison

| Feature | Command-Line Script | Web Dashboard |
|---------|-------------------|---------------|
| **Script** | `elite_trading_system.py` | `run_web.py` |
| **Signals** | ✅ Yes | ✅ Yes |
| **Charts** | ❌ No | ✅ Yes |
| **Real-time Data** | ❌ No | ✅ Yes |
| **Order Management** | ❌ No | ✅ Yes |
| **Portfolio View** | ❌ No | ✅ Yes |
| **Browser Needed** | ❌ No | ✅ Yes |
| **Speed** | ⚡ Fast | 🐢 Slower (web server) |

---

## 🚀 Recommended Usage

### For Quick Signal Check:
```bash
python elite_trading_system.py
```
- Fast
- No setup needed
- Get signals immediately

### For Full Trading Experience:
```bash
python run_web.py
```
Then visit: `http://localhost:5000`
- Complete dashboard
- All features
- Best user experience

---

## 📝 Step-by-Step Instructions

### Method 1: Command-Line (Signals Only)

1. **Open terminal/command prompt**
2. **Navigate to project folder**:
   ```bash
   cd "C:\Users\rahul_borse\OneDrive - S&P Global\Python\Python Assignment\stockai-trading-india"
   ```
3. **Run the script**:
   ```bash
   python elite_trading_system.py
   ```
4. **See signals** in terminal output

**Options:**
```bash
# Specific stocks
python elite_trading_system.py --tickers RELIANCE.NS TCS.NS

# Save results
python elite_trading_system.py --save

# Continuous monitoring
python elite_trading_system.py --continuous --interval 30
```

---

### Method 2: Web Dashboard (Full Interface)

1. **Open terminal/command prompt**
2. **Navigate to project folder**:
   ```bash
   cd "C:\Users\rahul_borse\OneDrive - S&P Global\Python\Python Assignment\stockai-trading-india"
   ```
3. **Start the web server**:
   ```bash
   python run_web.py
   ```
4. **Wait for server to start** (you'll see):
   ```
   ============================================================
   AI Trading Dashboard
   ============================================================
   Starting web server...
   Open your browser and go to: http://localhost:5000
   ============================================================
   ```
5. **Open your browser** (Chrome, Firefox, Edge)
6. **Visit**: `http://localhost:5000`
7. **See the dashboard** with:
   - Trading signals
   - Real-time prices
   - Charts
   - Order management
   - Portfolio analytics

---

## 🎯 Which One Should You Use?

### Use Command-Line Script (`elite_trading_system.py`) if:
- ✅ You want quick signals
- ✅ You don't need charts
- ✅ You prefer terminal/command-line
- ✅ You want fast analysis
- ✅ You're doing automated trading

### Use Web Dashboard (`run_web.py`) if:
- ✅ You want full interface
- ✅ You need charts and visuals
- ✅ You want real-time updates
- ✅ You need order management
- ✅ You want portfolio tracking
- ✅ You prefer web interface

---

## 💡 Pro Tip: Use Both!

1. **Morning**: Run command-line script for quick signals
   ```bash
   python elite_trading_system.py --save
   ```

2. **During Trading**: Use web dashboard for full experience
   ```bash
   python run_web.py
   ```

---

## 📊 What You'll See

### Command-Line Output:
```
================================================================================
                    ELITE AI TRADING SYSTEM                                   
              Best Trading Signals - All-in-One Script                      
================================================================================

[1/10] Analyzing RELIANCE.NS...
────────────────────────────────────────────────────────────────────────────────
Ticker: RELIANCE.NS
Signal: BUY
Probability: 65.00%
Confidence: 75.00%
Current Price: ₹2450.50
...
```

### Web Dashboard:
- Beautiful web interface
- Interactive charts
- Real-time price updates
- Signal indicators
- Order placement
- Portfolio view

---

## 🔧 Troubleshooting

### Command-Line Script Not Working:
```bash
# Check if script exists
dir elite_trading_system.py

# Run with Python
python elite_trading_system.py --status
```

### Web Dashboard Not Starting:
```bash
# Check if server file exists
dir run_web.py

# Start server
python run_web.py

# If port 5000 is busy, change port in run_web.py
```

### Can't Access Dashboard:
- Make sure server is running
- Check URL: `http://localhost:5000`
- Try: `http://127.0.0.1:5000`
- Check firewall settings

---

## 📚 Quick Reference

### For Signals Only:
```bash
python elite_trading_system.py
```

### For Full Dashboard:
```bash
python run_web.py
# Then visit: http://localhost:5000
```

---

## ✅ Summary

**For Trading Signals (Quick):**
→ Run: `python elite_trading_system.py`

**For Dashboard (Full Interface):**
→ Run: `python run_web.py`  
→ Then visit: `http://localhost:5000`

**Both work! Choose based on your needs!** 🎯
