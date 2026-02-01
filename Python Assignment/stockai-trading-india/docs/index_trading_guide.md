# Index Trading Guide

This guide covers how to use StockAI for trading Indian indices (NIFTY50, BankNifty, Sensex) and analyzing their constituent stocks.

## Table of Contents

1. [Index vs Stocks](#index-vs-stocks)
2. [Trading Indices](#trading-indices)
3. [Analyzing Constituents](#analyzing-constituents)
4. [Portfolio Backtesting](#portfolio-backtesting)
5. [Index Comparison](#index-comparison)
6. [Best Practices](#best-practices)

## Index vs Stocks

### When to Trade Indices

**Trade indices when:**
- You want broad market exposure with a single position
- You prefer lower volatility and diversification
- You want to avoid stock-specific risks
- You're trading ETFs (NIFTYBEES, BANKBEES) which are more liquid than futures

**Trade individual stocks when:**
- You have strong conviction on specific companies
- You want higher potential returns (with higher risk)
- You're doing sector rotation strategies
- You want to exploit relative strength opportunities

### Index Tickers

**NIFTY50:**
- Index: `^NSEI` or `NSEI.NS`
- ETF: `NIFTYBEES.NS` (most liquid)

**BankNifty:**
- Index: `^NSEBANK` or `NSEBANK.NS`
- ETF: `BANKBEES.NS` (most liquid)

**Sensex:**
- Index: `^BSESN` or `BSESN.BO`
- ETF: `SENSEX.NS` (if available)

## Trading Indices

### Single Index Backtest

```bash
# Backtest NIFTY50 index
python -m src.cli research --ticker ^NSEI --start 2020-01-01 --end 2025-01-01 --outdir outputs/nifty50_index

# Backtest NIFTY50 ETF (more liquid)
python -m src.cli research --ticker NIFTYBEES.NS --start 2020-01-01 --end 2025-01-01 --outdir outputs/nifty50_etf

# Backtest BankNifty ETF
python -m src.cli research --ticker BANKBEES.NS --start 2020-01-01 --end 2025-01-01 --outdir outputs/banknifty_etf
```

### Batch Index/ETF Backtest

```bash
# Backtest all indices and ETFs
python -m src.cli batch --universe configs/universe_nifty50_index.txt --start 2020-01-01 --end 2025-01-01 --outdir outputs/index_batch
```

## Analyzing Constituents

### NIFTY50 Stocks

```bash
# Backtest all 50 NIFTY50 stocks individually
python -m src.cli batch --universe configs/universe_nifty50_stocks.txt --start 2020-01-01 --end 2025-01-01 --outdir outputs/nifty50_stocks

# Compare strategy returns vs NIFTY50 index
python -m src.cli batch --universe configs/universe_nifty50_stocks.txt --start 2020-01-01 --end 2025-01-01 --outdir outputs/nifty50_with_index --compare-index ^NSEI
```

The `--compare-index` flag adds correlation, beta, alpha, and R-squared metrics to the summary CSV.

### BankNifty Stocks

```bash
# Backtest all BankNifty constituent banks
python -m src.cli batch --universe configs/universe_banknifty_stocks.txt --start 2020-01-01 --end 2025-01-01 --outdir outputs/banknifty_stocks

# Compare vs BankNifty index
python -m src.cli batch --universe configs/universe_banknifty_stocks.txt --start 2020-01-01 --end 2025-01-01 --outdir outputs/banknifty_with_index --compare-index ^NSEBANK
```

### Sensex Stocks

```bash
# Backtest all 30 Sensex stocks
python -m src.cli batch --universe configs/universe_sensex_stocks.txt --start 2020-01-01 --end 2025-01-01 --outdir outputs/sensex_stocks
```

## Portfolio Backtesting

Portfolio backtesting allows you to trade multiple assets simultaneously with position sizing.

### Equal-Weight Portfolio

```bash
# Portfolio backtest with equal-weight position sizing
python -m src.cli batch --universe configs/universe_nifty50_stocks.txt --start 2020-01-01 --end 2025-01-01 --outdir outputs/portfolio_equal --portfolio-mode
```

This creates:
- `portfolio_equity_curve.csv`: Aggregated portfolio equity curve
- `portfolio_position_weights.csv`: Daily position weights for each asset
- `portfolio_stats.json`: Portfolio-level performance metrics
- `individual_summary.csv`: Per-asset backtest results

### Portfolio vs Individual Backtests

**Individual backtests** (`--portfolio-mode` not set):
- Each asset is backtested independently
- Results in `summary.csv` with per-asset metrics
- Useful for identifying best/worst performers

**Portfolio backtests** (`--portfolio-mode`):
- All assets traded simultaneously
- Position sizing applied (equal-weight by default)
- Portfolio-level metrics (aggregated returns, Sharpe, drawdown)
- More realistic for actual trading

## Index Comparison

### Relative Strength Analysis

Use the `index_analysis` module programmatically:

```python
from src.research.index_analysis import compare_index_vs_constituents, get_top_outperformers
from src.research.data import download_yahoo_ohlcv

# Download index data
index_data = download_yahoo_ohlcv("^NSEI", "2020-01-01", "2025-01-01")

# Download constituent data
constituent_data = {}
for ticker in ["RELIANCE.NS", "TCS.NS", "INFY.NS"]:
    constituent_data[ticker] = download_yahoo_ohlcv(ticker, "2020-01-01", "2025-01-01").df

# Compare
comparison = compare_index_vs_constituents(index_data.df, constituent_data)

# Get top outperformers
top_performers = get_top_outperformers(comparison.relative_strength, top_n=10)
print("Top 10 outperformers:", top_performers)
```

### Correlation Analysis

The comparison object includes a correlation matrix:

```python
# Correlation between index and constituents
print(comparison.correlation_matrix)
```

## Best Practices

### 1. Data Quality

- **Always validate data**: The system automatically checks for gaps, outliers, and data quality issues
- **Use cache**: Data is cached to avoid repeated downloads. Use `--refresh` only when needed
- **Check date ranges**: Ensure market was open during your date range

### 2. Walk-Forward Training

- **Use walk-forward by default**: More realistic than simple train/test split
- **Adjust min_train_size**: For shorter date ranges, the system auto-adjusts
- **Retrain frequency**: Default is every 20 days. Increase for more stable models, decrease for more adaptive models

### 3. Position Sizing

- **Equal-weight**: Simplest and most robust for diversified portfolios
- **Custom weights**: Use when you have strong conviction on specific assets
- **Rebalancing**: Portfolio mode rebalances daily. Consider transaction costs (`--fee-bps`)

### 4. Risk Management

- **Transaction costs**: Default is 10 bps per position change. Adjust based on your broker
- **Prob threshold**: Default is 0.55. Higher = fewer trades, lower = more trades
- **Label horizon**: Default is 1 day. Increase for longer-term strategies

### 5. Visualization

Always generate visualizations after backtests:

```bash
python -m src.cli visualize --outdir outputs/reliance --ticker RELIANCE.NS
```

This creates an HTML report with equity curves, drawdowns, and statistics.

### 6. Index vs ETF

**Use ETFs (NIFTYBEES.NS, BANKBEES.NS) when:**
- You want actual tradable instruments
- You need liquidity for larger positions
- You're doing paper trading or live trading

**Use indices (^NSEI, ^NSEBANK) when:**
- You're doing research/analysis
- You want the pure index performance (no ETF tracking error)
- You're comparing strategies vs benchmark

### 7. Portfolio Construction

**For NIFTY50:**
- Consider sector diversification (IT, Banking, Pharma, etc.)
- Use `--compare-index ^NSEI` to ensure you're beating the index
- Portfolio mode helps avoid over-concentration

**For BankNifty:**
- All constituents are banks, so less diversification
- Focus on relative strength vs index
- Consider correlation between banks (they tend to move together)

**For Sensex:**
- Only 30 stocks, so each position has more impact
- Use portfolio mode to manage risk
- Compare vs Sensex index for validation

## Example Workflow

1. **Research Phase:**
   ```bash
   # Backtest index
   python -m src.cli research --ticker ^NSEI --start 2020-01-01 --end 2025-01-01 --outdir outputs/research/nifty50
   
   # Backtest all constituents
   python -m src.cli batch --universe configs/universe_nifty50_stocks.txt --start 2020-01-01 --end 2025-01-01 --outdir outputs/research/constituents
   ```

2. **Analysis Phase:**
   ```bash
   # Compare vs index
   python -m src.cli batch --universe configs/universe_nifty50_stocks.txt --start 2020-01-01 --end 2025-01-01 --outdir outputs/analysis --compare-index ^NSEI
   
   # Generate visualizations
   python -m src.cli visualize --outdir outputs/research/nifty50 --ticker NIFTY50
   ```

3. **Portfolio Backtest:**
   ```bash
   # Portfolio backtest
   python -m src.cli batch --universe configs/universe_nifty50_stocks.txt --start 2020-01-01 --end 2025-01-01 --outdir outputs/portfolio --portfolio-mode
   ```

4. **Paper Trading:**
   ```bash
   # Paper trade the ETF
   python -m src.cli paper --ticker NIFTYBEES.NS --start 2024-01-01 --end 2025-01-01 --outdir outputs/paper/niftybees
   ```

## Troubleshooting

### "No data returned" error

- Check ticker symbol format (`.NS` for NSE, `.BO` for BSE, `^` for indices)
- Verify date range (market was open)
- Try `--refresh` to re-download

### SSL certificate errors

```bash
python -m pip install --upgrade certifi
```

### Portfolio mode fails

- Ensure all tickers have overlapping date ranges
- Check that data downloads successfully for all tickers
- Reduce number of tickers if memory is an issue

### Index comparison fails

- Ensure index ticker is valid (`^NSEI`, `^NSEBANK`, `^BSESN`)
- Check that index data downloads successfully
- Verify date ranges overlap with stock data

## Further Reading

- See `README.md` for general usage
- Check `src/research/index_analysis.py` for programmatic analysis
- Review `src/research/portfolio_backtest.py` for portfolio backtesting details
