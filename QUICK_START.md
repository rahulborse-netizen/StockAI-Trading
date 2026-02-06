# Quick Start - ELITE Trading System

## 🚀 One Command to Get Best Trading Signals

### Basic Usage (Recommended)
```bash
python elite_trading_system.py
```

**What it does:**
- ✅ Analyzes 10 top stocks automatically
- ✅ Shows BUY/SELL/HOLD signals
- ✅ Displays entry, stop loss, and targets
- ✅ Calculates risk/reward ratios
- ✅ Shows top opportunities

---

## 📋 Common Commands

### 1. Analyze Your Stocks
```bash
python elite_trading_system.py --tickers RELIANCE.NS TCS.NS INFY.NS
```

### 2. Use Your Watchlist
Create `my_stocks.txt`:
```
RELIANCE.NS
TCS.NS
INFY.NS
```

Then:
```bash
python elite_trading_system.py --file my_stocks.txt
```

### 3. Continuous Monitoring
```bash
python elite_trading_system.py --continuous --interval 30
```
- Runs every 30 minutes
- Press Ctrl+C to stop

### 4. Save Results
```bash
python elite_trading_system.py --save
```
- Saves to `signals_YYYYMMDD_HHMMSS.json`

### 5. Check System
```bash
python elite_trading_system.py --status
```

---

## 📊 What You'll See

### For Each Stock:
- **Signal**: BUY (green) / SELL (red) / HOLD (yellow)
- **Probability**: % chance price goes up
- **Confidence**: How confident the AI is
- **Current Price**: Latest market price
- **Entry Level**: Where to enter
- **Stop Loss**: Risk management
- **Targets**: Profit targets
- **Risk/Reward**: Potential profit vs risk

### Summary:
- Total stocks analyzed
- Number of BUY signals
- Number of SELL signals
- Top 5 buy opportunities

---

## 💡 Pro Tips

1. **Run in the morning** before market opens
2. **Use --save** to track signals over time
3. **Focus on high confidence** (>70%) signals
4. **Always use stop loss** (provided in output)
5. **Combine with your analysis** - AI is a tool, not a guarantee

---

## ⚡ Quick Examples

```bash
# Morning analysis
python elite_trading_system.py --watchlist --save

# Monitor specific stocks
python elite_trading_system.py -t RELIANCE.NS TCS.NS

# Continuous watch
python elite_trading_system.py -c -i 15
```

---

**That's it!** Just run `python elite_trading_system.py` and get the best trading signals! 🎯
