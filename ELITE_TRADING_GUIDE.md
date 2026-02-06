# ELITE Trading System - User Guide

## Quick Start

### Basic Usage (Default Watchlist)
```bash
python elite_trading_system.py
```

This will:
- Check system status
- Analyze 10 default stocks (RELIANCE, TCS, INFY, etc.)
- Display best trading signals
- Show buy/sell opportunities

---

## Command Options

### 1. Analyze Specific Tickers
```bash
python elite_trading_system.py --tickers RELIANCE.NS TCS.NS INFY.NS
```

### 2. Use Custom Watchlist File
Create a file `my_watchlist.txt`:
```
RELIANCE.NS
TCS.NS
INFY.NS
HDFCBANK.NS
```

Then run:
```bash
python elite_trading_system.py --file my_watchlist.txt
```

### 3. Continuous Monitoring
Run every 60 minutes (default):
```bash
python elite_trading_system.py --continuous
```

Run every 30 minutes:
```bash
python elite_trading_system.py --continuous --interval 30
```

### 4. Save Signals to File
```bash
python elite_trading_system.py --save
```

Creates: `signals_YYYYMMDD_HHMMSS.json`

### 5. Check System Status Only
```bash
python elite_trading_system.py --status
```

### 6. Use Basic Mode (Disable ELITE)
```bash
python elite_trading_system.py --no-elite
```

---

## Output Explanation

### Signal Colors
- 🟢 **GREEN** = BUY or STRONG_BUY
- 🔴 **RED** = SELL or STRONG_SELL
- 🟡 **YELLOW** = HOLD

### Signal Information
For each ticker, you'll see:
- **Signal**: BUY/SELL/HOLD
- **Probability**: Chance of price going up (0-100%)
- **Confidence**: Model confidence in prediction (0-100%)
- **Current Price**: Latest price
- **Trading Levels**:
  - Entry: Recommended entry price
  - Stop Loss: Risk management level
  - Target 1: First profit target
  - Target 2: Second profit target
- **Risk/Reward**: Ratio showing potential profit vs risk

### Summary Section
- Total analyzed tickers
- Number of BUY signals
- Number of SELL signals
- Number of HOLD signals
- Top 5 buy opportunities (sorted by probability)

---

## Example Output

```
================================================================================
ELITE AI SIGNAL GENERATION
================================================================================

[1/10] Analyzing RELIANCE.NS...
────────────────────────────────────────────────────────────────────────────────
Ticker: RELIANCE.NS
Signal: BUY
Probability: 65.00%
Confidence: 75.00%
Current Price: ₹2450.50
ELITE System: Active (1 models)

Trading Levels:
  Entry: ₹2445.00
  Stop Loss: ₹2376.99
  Target 1: ₹2523.02
  Target 2: ₹2573.03

Risk/Reward:
  Target 1: 1.15:1
  Target 2: 1.88:1

================================================================================
SIGNAL SUMMARY
================================================================================
Total Analyzed: 10
Buy Signals: 4
Sell Signals: 1
Hold Signals: 5

TOP BUY OPPORTUNITIES:
  RELIANCE.NS: 65.0% prob, 75.0% confidence
  TCS.NS: 62.0% prob, 70.0% confidence
  ...
```

---

## Use Cases

### 1. Morning Market Analysis
```bash
python elite_trading_system.py --watchlist --save
```
- Analyze default watchlist
- Save results for later review
- Get signals before market opens

### 2. Continuous Monitoring
```bash
python elite_trading_system.py --continuous --interval 15
```
- Monitor every 15 minutes
- Get updated signals throughout the day
- Press Ctrl+C to stop

### 3. Focused Analysis
```bash
python elite_trading_system.py --tickers RELIANCE.NS TCS.NS
```
- Analyze specific stocks you're interested in
- Quick analysis for decision making

### 4. Portfolio Review
Create `portfolio.txt` with your holdings:
```
RELIANCE.NS
TCS.NS
INFY.NS
```

Then:
```bash
python elite_trading_system.py --file portfolio.txt --save
```

---

## System Requirements

### Required
- Python 3.8+
- All dependencies from `requirements.txt`
- Internet connection (for data)

### Optional (for better signals)
- XGBoost: `pip install xgboost`
- TensorFlow: `pip install tensorflow`

---

## Troubleshooting

### "Server not running" Error
The script doesn't need the web server. It runs standalone.

### "No data available" Error
- Check internet connection
- Update yfinance: `pip install --upgrade yfinance`
- Try different tickers

### "Module not found" Error
- Install dependencies: `pip install -r requirements.txt`
- Make sure you're in project root directory

---

## Tips for Best Results

1. **Use ELITE System** (default)
   - Combines multiple models
   - Better accuracy
   - Higher confidence scores

2. **Check System Status First**
   ```bash
   python elite_trading_system.py --status
   ```

3. **Save Important Signals**
   - Use `--save` flag
   - Review saved JSON files
   - Track signal accuracy over time

4. **Continuous Monitoring**
   - Run in background
   - Set appropriate interval (15-60 minutes)
   - Monitor for changes in signals

5. **Focus on High Confidence**
   - Signals with >70% confidence are more reliable
   - Combine with your own analysis
   - Always use stop loss

---

## Integration with Trading

### Paper Trading
- System defaults to PAPER mode
- Test signals without real money
- Validate strategy before live trading

### Live Trading
- Switch to LIVE mode (via web interface)
- Use signals as input for decisions
- Always set stop loss
- Never risk more than you can afford to lose

---

## Advanced Usage

### Custom Watchlist File Format
```
# Comments start with #
RELIANCE.NS
TCS.NS
# Add more tickers below
INFY.NS
```

### Combine with Other Tools
```bash
# Generate signals and save
python elite_trading_system.py --save > output.txt

# Continuous monitoring with logging
python elite_trading_system.py --continuous --interval 30 >> trading_log.txt 2>&1
```

---

## What Makes It ELITE?

1. **Multi-Model Ensemble**
   - Combines Logistic Regression, XGBoost, LSTM
   - Better predictions than single model

2. **50+ Technical Indicators**
   - Advanced feature engineering
   - Comprehensive market analysis

3. **Multi-Timeframe Analysis**
   - Analyzes 1m, 5m, 15m, 1h, 1d
   - Confirms signals across timeframes

4. **Confidence Scoring**
   - Know how confident the system is
   - Better risk management

5. **Risk/Reward Calculation**
   - Automatic stop loss and targets
   - Risk management built-in

---

## Quick Reference

```bash
# Basic usage
python elite_trading_system.py

# Custom tickers
python elite_trading_system.py -t RELIANCE.NS TCS.NS

# Watchlist file
python elite_trading_system.py -f my_stocks.txt

# Continuous (every 30 min)
python elite_trading_system.py -c -i 30

# Save results
python elite_trading_system.py --save

# Check status
python elite_trading_system.py --status
```

---

**Ready to trade!** 🚀

Run `python elite_trading_system.py` to get started!
