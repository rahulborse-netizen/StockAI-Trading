# Live Trading Signal Algorithm

A standalone algorithm that tracks live NSE/BSE data and generates buy/sell trading signals.

## Features

- ✅ **Live Data Tracking**: Fetches real-time data from NSE API
- ✅ **AI-Powered Signals**: Uses ELITE signal generator with multiple ML models
- ✅ **No Dashboard Required**: Pure algorithm output - just buy/sell calls
- ✅ **Multiple Modes**: Single scan or continuous monitoring
- ✅ **Flexible Input**: Scan specific tickers, watchlist file, or top N stocks
- ✅ **Confidence Filtering**: Only shows signals above confidence threshold

## Installation

No additional installation needed - uses existing project dependencies.

## Usage

### Basic Usage - Scan Specific Stocks

```bash
python scripts/live_trading_signals.py --tickers RELIANCE.NS TCS.NS INFY.NS
```

### Scan Top 50 Stocks by Volume

```bash
python scripts/live_trading_signals.py --top-n 50
```

### Use Watchlist File

Create a file `my_watchlist.txt` with one ticker per line:
```
RELIANCE.NS
TCS.NS
INFY.NS
HDFCBANK.NS
```

Then run:
```bash
python scripts/live_trading_signals.py --watchlist my_watchlist.txt
```

### Continuous Monitoring (During Market Hours)

Scan every 5 minutes and save results:
```bash
python scripts/live_trading_signals.py --continuous --interval 5 --output signals.csv
```

### Custom Confidence Threshold

Only show signals with confidence >= 0.65:
```bash
python scripts/live_trading_signals.py --min-confidence 0.65
```

## Command Line Options

```
--tickers TICKERS [TICKERS ...]
    List of tickers to scan (e.g., RELIANCE.NS TCS.NS)

--watchlist FILE
    File containing list of tickers (one per line)

--top-n N
    Scan top N stocks by volume (default: 50)

--min-confidence FLOAT
    Minimum confidence threshold (default: 0.55)
    Range: 0.0 to 1.0

--output FILE
    Output CSV file path (optional)

--continuous
    Run continuously (scan every N minutes during market hours)

--interval MINUTES
    Scan interval in minutes when using --continuous (default: 5)
```

## Output Format

### Console Output

```
================================================================================
TRADING SIGNALS - 2026-02-09 14:30:00 IST
================================================================================

🟢 BUY SIGNALS (3):
--------------------------------------------------------------------------------
  RELIANCE.NS     | Price: ₹2450.50 | Confidence: 72.50% | Change:  1.25% | Volume: 1,234,567
    → Strong elite_multi_tf signal with 72.50% confidence
  TCS.NS          | Price: ₹3850.75 | Confidence: 68.30% | Change:  0.85% | Volume: 987,654
    → Strong elite_multi_tf signal with 68.30% confidence

🔴 SELL SIGNALS (1):
--------------------------------------------------------------------------------
  INFY.NS         | Price: ₹1850.25 | Confidence: 65.20% | Change: -1.50% | Volume: 2,345,678
    → Strong elite_multi_tf signal with 65.20% confidence

================================================================================
```

### CSV Output

If `--output` is specified, signals are saved to CSV with columns:
- `ticker`: Stock ticker symbol
- `action`: BUY, SELL, or HOLD
- `signal`: Original signal type
- `confidence`: Confidence score (0.0 to 1.0)
- `price`: Current price
- `change_pct`: Price change percentage
- `volume`: Trading volume
- `reason`: Explanation of signal
- `model_id`: Model that generated signal
- `timestamp`: ISO timestamp

## Market Hours

The algorithm is aware of Indian market hours:
- **Market Open**: 9:15 AM IST
- **Market Close**: 3:30 PM IST

During market hours, it uses live NSE API data.
Outside market hours, it uses last close prices (may have delay).

## Signal Generation

The algorithm uses the **ELITE Signal Generator** which combines:
- Multi-timeframe analysis (5m, 15m, 1h, 1d)
- Multiple ML models (Logistic Regression, XGBoost, LSTM)
- Advanced feature engineering
- Ensemble predictions

### Signal Interpretation

- **BUY**: Strong upward momentum predicted
- **SELL**: Strong downward momentum predicted
- **HOLD**: Weak signal or low confidence

### Confidence Levels

- **High (≥0.70)**: Very strong signal
- **Medium (0.55-0.70)**: Moderate signal
- **Low (<0.55)**: Filtered out by default

## Examples

### Example 1: Quick Scan of Popular Stocks

```bash
python scripts/live_trading_signals.py \
  --tickers RELIANCE.NS TCS.NS HDFCBANK.NS INFY.NS \
  --min-confidence 0.60
```

### Example 2: Continuous Monitoring with Output

```bash
python scripts/live_trading_signals.py \
  --top-n 100 \
  --continuous \
  --interval 10 \
  --min-confidence 0.65 \
  --output trading_signals.csv
```

### Example 3: Custom Watchlist

```bash
# Create watchlist
echo "RELIANCE.NS" > watchlist.txt
echo "TCS.NS" >> watchlist.txt
echo "INFY.NS" >> watchlist.txt

# Run scan
python scripts/live_trading_signals.py \
  --watchlist watchlist.txt \
  --min-confidence 0.70 \
  --output results.csv
```

## Performance

- **Scan Speed**: ~0.5 seconds per stock (includes data fetch + signal generation)
- **Rate Limiting**: Built-in delays to avoid API rate limits
- **Caching**: Historical data is cached for faster subsequent scans

## Troubleshooting

### No Signals Found

- Lower `--min-confidence` threshold (try 0.50)
- Check if market is open (signals are more accurate during market hours)
- Verify ticker symbols are correct (must end with `.NS` for NSE or `.BO` for BSE)

### API Errors

- NSE API may have rate limits - algorithm includes delays
- If NSE API fails, falls back to Yahoo Finance (may have delay)
- Check internet connection

### Slow Performance

- Reduce number of tickers scanned
- Use `--top-n` with smaller number
- Increase `--interval` for continuous mode

## Integration

You can integrate this script into:
- **Cron jobs**: Run at specific times
- **Trading bots**: Use signals for automated trading
- **Alerts**: Send signals via email/SMS/webhook
- **Analysis**: Combine with other indicators

### Example: Python Integration

```python
from scripts.live_trading_signals import scan_stocks, EliteSignalGenerator, NSEDataClient

signal_generator = EliteSignalGenerator()
nse_client = NSEDataClient()

tickers = ['RELIANCE.NS', 'TCS.NS']
signals = scan_stocks(tickers, signal_generator, nse_client, min_confidence=0.60)

for signal in signals:
    print(f"{signal['ticker']}: {signal['action']} at ₹{signal['price']}")
```

## Notes

- ⚠️ **Not Financial Advice**: Signals are for informational purposes only
- ⚠️ **Backtest First**: Always backtest strategies before live trading
- ⚠️ **Risk Management**: Use stop-loss and position sizing
- ⚠️ **Market Conditions**: Signals may be less accurate during high volatility

## Support

For issues or questions:
1. Check logs for error messages
2. Verify ticker symbols are correct
3. Ensure market data APIs are accessible
4. Check network connectivity
