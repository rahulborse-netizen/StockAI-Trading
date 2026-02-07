# StockAI Trading Algorithm — Complete Setup & Usage Guide

> **One-stop reference** for anyone who wants to install, configure, and run this AI-powered Indian stock market trading platform on their own machine.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Installation](#2-installation)
3. [Project Structure](#3-project-structure)
4. [Configuration](#4-configuration)
5. [Running the Web Dashboard](#5-running-the-web-dashboard)
6. [Dashboard Features & How to Use Them](#6-dashboard-features--how-to-use-them)
7. [CLI Signal Tool (get_signals.py)](#7-cli-signal-tool-get_signalspy)
8. [Research & Backtesting (No Broker Needed)](#8-research--backtesting-no-broker-needed)
9. [Trading Strategies Explained](#9-trading-strategies-explained)
10. [Broker Integration (Upstox / Zerodha)](#10-broker-integration-upstox--zerodha)
11. [Paper Trading vs Live Trading](#11-paper-trading-vs-live-trading)
12. [API Endpoints Reference](#12-api-endpoints-reference)
13. [Troubleshooting](#13-troubleshooting)
14. [Safety & Disclaimer](#14-safety--disclaimer)

---

## 1. Prerequisites

| Requirement | Details |
|---|---|
| **Python** | 3.10 or 3.11 recommended (3.9+ works) |
| **pip** | Comes with Python; make sure it's up to date (`python -m pip install --upgrade pip`) |
| **Git** | For cloning the repository |
| **OS** | Windows 10/11 (tested), macOS, or Linux |
| **Browser** | Chrome, Edge, or Firefox (for the web dashboard) |
| **Internet** | Required for fetching live market data from Yahoo Finance / NSE / Upstox |

### Optional (for advanced AI models)

| Requirement | Details |
|---|---|
| **TensorFlow** | v2.13+ (for LSTM model) — CPU works fine; GPU is optional |
| **XGBoost** | v2.0+ (for gradient boosting model) |

> **Note:** These are listed in `requirements.txt` and will be installed automatically.

---

## 2. Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/rahulborse-netizen/StockAI-Trading.git
cd StockAI-Trading
```

### Step 2: (Recommended) Create a Virtual Environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs all necessary packages:

| Package | Purpose |
|---|---|
| `flask`, `flask-cors`, `flask-socketio` | Web dashboard backend |
| `eventlet`, `websocket-client` | Real-time WebSocket support |
| `pandas`, `numpy` | Data processing |
| `scikit-learn` | ML models (Logistic Regression) |
| `xgboost` | Gradient boosting model |
| `tensorflow` | LSTM deep learning model |
| `yfinance` | Free stock data from Yahoo Finance |
| `matplotlib`, `seaborn` | Charts & visualizations |
| `python-dotenv` | Environment variable management |
| `requests` | HTTP API calls |

### Step 4: (Optional) Set Up Environment Variables

If you plan to use **live broker integration** (Upstox or Zerodha), create a `.env` file in the project root:

```env
# Upstox Credentials
UPSTOX_API_KEY=your_api_key_here
UPSTOX_API_SECRET=your_api_secret_here
UPSTOX_REDIRECT_URI=http://localhost:5000/callback

# Zerodha Credentials (alternative)
ZERODHA_API_KEY=your_api_key_here
ZERODHA_API_SECRET=your_api_secret_here
```

> **Not required** for paper trading, research, or backtesting. The dashboard works fully without broker credentials using Yahoo Finance data.

---

## 3. Project Structure

```
StockAI-Trading/
├── run_web.py                  # Main entry point — starts the web dashboard
├── get_signals.py              # CLI tool — get trading signals from terminal
├── start_web.bat               # Windows shortcut — double-click to start
├── requirements.txt            # Python dependencies
├── README.md                   # Project overview
├── SETUP_GUIDE.md              # This file
│
├── configs/                    # Configuration files
│   ├── default.yaml            # Default settings (API keys, model params)
│   ├── trading_config.yaml     # Risk management & trading parameters
│   ├── universe_nifty50.txt    # NIFTY50 stock list
│   ├── universe_nifty50_stocks.txt
│   ├── universe_banknifty_stocks.txt
│   ├── universe_sensex_stocks.txt
│   └── ...                     # Other universe files
│
├── data/
│   └── watchlist.json          # Your saved watchlist
│
├── src/                        # All source code
│   ├── web/                    # Web dashboard application
│   │   ├── app.py              # Flask app with all API routes (main file)
│   │   ├── strategies/         # Trading strategies
│   │   │   ├── adaptive_elite_strategy.py  # Primary AI strategy
│   │   │   ├── adaptive_features.py        # Feature engineering
│   │   │   ├── signal_filter.py            # Signal quality filter
│   │   │   ├── ml_strategy.py              # ML-based strategy
│   │   │   ├── momentum_strategy.py        # Momentum strategy
│   │   │   ├── mean_reversion_strategy.py  # Mean reversion strategy
│   │   │   ├── strategy_manager.py         # Strategy orchestrator
│   │   │   └── backtest_adaptive.py        # Backtesting for adaptive strategy
│   │   │
│   │   ├── ai_models/          # AI/ML model implementations
│   │   │   ├── ensemble_manager.py         # Multi-model ensemble
│   │   │   ├── elite_signal_generator.py   # Signal generation engine
│   │   │   ├── xgboost_predictor.py        # XGBoost model
│   │   │   ├── lstm_predictor.py           # LSTM deep learning model
│   │   │   ├── multi_timeframe_analyzer.py # Multi-timeframe analysis
│   │   │   ├── performance_tracker.py      # Model performance tracking
│   │   │   ├── model_registry.py           # Model versioning & registry
│   │   │   └── advanced_features.py        # 50+ technical indicators
│   │   │
│   │   ├── static/             # Frontend assets (CSS, JavaScript)
│   │   │   ├── css/            # Stylesheets
│   │   │   └── js/             # JavaScript files
│   │   │       ├── dashboard.js            # Main dashboard logic
│   │   │       ├── trading-platform.js     # Trading interface
│   │   │       ├── charts.js               # Chart rendering
│   │   │       └── websocket-client.js     # Real-time updates
│   │   │
│   │   ├── templates/          # HTML templates
│   │   │   └── dashboard.html              # Main dashboard page
│   │   │
│   │   ├── upstox_api.py       # Upstox broker API client
│   │   ├── upstox_connection.py # Upstox connection manager
│   │   ├── market_data.py      # Market data fetcher
│   │   ├── paper_trading.py    # Paper trading engine
│   │   ├── risk_manager.py     # Risk management system
│   │   ├── position_sizing.py  # Position size calculator
│   │   ├── watchlist.py        # Watchlist manager
│   │   ├── alerts.py           # Price & signal alerts
│   │   ├── holdings_db.py      # SQLite holdings tracker
│   │   ├── trade_planner.py    # Trade planning tools
│   │   ├── trade_journal.py    # Trade journal logging
│   │   └── ...
│   │
│   ├── research/               # Research & backtesting modules
│   │   ├── backtest.py         # Single-asset backtesting
│   │   ├── portfolio_backtest.py # Portfolio backtesting
│   │   ├── data.py             # Data download utilities
│   │   ├── features.py         # Feature engineering
│   │   ├── ml.py               # ML model training
│   │   └── visualize.py        # Chart generation
│   │
│   ├── strategies/             # Core strategy implementations
│   ├── models/                 # ML model training & prediction
│   ├── broker/                 # Broker adapters (Zerodha)
│   └── data/                   # Data ingestion & loading
│
├── scripts/
│   └── migrate_to_phase2.py    # Database migration script
│
└── tests/                      # Organized test files
    ├── test_elite_tier1.py
    └── test_phase2_integration.py
```

---

## 4. Configuration

### Risk Management (`configs/trading_config.yaml`)

Edit this file to adjust risk parameters:

| Parameter | Default | Description |
|---|---|---|
| `max_risk_per_trade` | 2% | Maximum risk on a single trade |
| `max_position_size` | 20% | Max capital in one stock |
| `max_daily_risk` | 5% | Max daily loss allowed |
| `max_portfolio_risk` | 30% | Max total portfolio risk |
| `max_open_positions` | 10 | Max simultaneous positions |
| `min_risk_reward_ratio` | 1.5:1 | Minimum reward-to-risk ratio |

### Trading Type Defaults (same file)

| Type | Stop Loss | Target 1 | Target 2 |
|---|---|---|---|
| **Intraday** | 2% | 1% | 1.5% |
| **Swing** | 3% | 3% | 5% |
| **Positional** | 5% | 5% | 10% |

### Strategy Tuning

The Adaptive Elite Strategy (`src/web/strategies/adaptive_elite_strategy.py`) has these key parameters:

| Parameter | Default | What It Does |
|---|---|---|
| `min_confidence` | 0.70 (70%) | Minimum confidence threshold — only signals above this are shown |
| `use_ensemble` | True | Combines multiple ML models for better accuracy |
| `use_multi_timeframe` | True | Analyzes multiple timeframes (1m, 5m, 15m, 1h, 1d) |

---

## 5. Running the Web Dashboard

### Option A: Python Command (Recommended)

```bash
python run_web.py
```

### Option B: Windows Batch File

Double-click `start_web.bat` in the project folder.

### Option C: Run Migration First (First-Time Setup)

```bash
python scripts/migrate_to_phase2.py
python run_web.py
```

### Access the Dashboard

Once the server starts, open your browser and go to:

```
http://localhost:5000
```

The dashboard will be available at this URL. You should see:
- Live market overview with NIFTY, SENSEX, and Bank NIFTY indices
- Watchlist panel for your tracked stocks
- Trading signals section
- Portfolio & holdings overview
- Order placement interface

### Accessing from Other Devices on the Same Network

The server binds to `0.0.0.0`, so you can access it from any device on your local network:

```
http://<your-computer-ip>:5000
```

Find your IP with `ipconfig` (Windows) or `ifconfig` (Mac/Linux).

---

## 6. Dashboard Features & How to Use Them

### Watchlist
- **Add stocks:** Type a stock symbol (e.g., `RELIANCE.NS`) and click Add
- **View prices:** Real-time prices update automatically
- **Quick signals:** Each stock shows its current signal (BUY/SELL/HOLD)

### Trading Signals
- Signals are generated by the **Adaptive Elite Strategy** which:
  1. Detects current market regime (trending vs ranging)
  2. Selects the best sub-strategy for the regime
  3. Combines ML model predictions (Logistic Regression + XGBoost + LSTM)
  4. Filters for high-confidence signals only (≥70% confidence)
- Each signal includes: entry price, stop loss, target prices, confidence level

### Order Placement
- Select a stock from your watchlist
- Choose order type: Market / Limit
- Set quantity and price
- Choose trading mode: Paper (simulated) or Live (real broker)
- Review the order confirmation before submitting

### Portfolio & Holdings
- View current holdings and their P&L
- Track daily portfolio value changes
- Asset allocation chart shows diversification
- Historical performance comparison

### Paper Trading
- Practice trading without real money
- All orders are simulated locally
- P&L is tracked just like real trading
- Toggle between Paper and Live mode in the dashboard header

---

## 7. CLI Signal Tool (`get_signals.py`)

Get trading signals directly from your terminal (requires the web server to be running):

```bash
# Single stock
python get_signals.py RELIANCE.NS

# Multiple stocks
python get_signals.py TCS.NS INFY.NS HDFCBANK.NS

# All stocks in your watchlist
python get_signals.py --watchlist

# Top 10 popular stocks
python get_signals.py --all

# JSON output (for programmatic use)
python get_signals.py RELIANCE.NS --json

# Custom server URL (if running on different port/host)
python get_signals.py RELIANCE.NS --url http://192.168.1.100:5000
```

### Sample Output

```
============================================================
📊 Trading Signals - Adaptive Elite Strategy
============================================================

RELIANCE.NS
  🟢 Signal: BUY
  Confidence: 78%
  Current: ₹2,450.50
  Entry: ₹2,448.00 | Stop: ₹2,399.00 | Target: ₹2,520.00
  Target 2: ₹2,570.00
  Regime: TRENDING (BULLISH) | Trend: 65.2 | Vol: 1.8%
```

---

## 8. Research & Backtesting (No Broker Needed)

These features use **Yahoo Finance data** and don't need any broker credentials.

### Single Stock Research

```bash
python -m src.cli research --ticker RELIANCE.NS --start 2020-01-01 --end 2025-01-01 --outdir outputs/reliance
```

**Outputs:**
- `model.joblib` — Trained ML model
- `predictions.csv` — Test-set probability predictions
- `equity_curve.csv` + `stats.json` — Backtest results

### Batch Processing (Multiple Stocks)

```bash
# Run across all NIFTY50 stocks
python -m src.cli batch --universe configs/universe_nifty50_stocks.txt --start 2020-01-01 --end 2025-01-01 --outdir outputs/nifty_batch

# Run across BankNifty stocks
python -m src.cli batch --universe configs/universe_banknifty_stocks.txt --start 2020-01-01 --end 2025-01-01 --outdir outputs/banknifty_batch
```

### Index Backtesting

```bash
# NIFTY50 index
python -m src.cli research --ticker ^NSEI --start 2020-01-01 --end 2025-01-01 --outdir outputs/nifty50_index

# BankNifty ETF
python -m src.cli research --ticker BANKBEES.NS --start 2020-01-01 --end 2025-01-01 --outdir outputs/banknifty_etf
```

### Portfolio Backtesting

```bash
# Multi-asset portfolio mode
python -m src.cli batch --universe configs/universe_nifty50_stocks.txt --start 2020-01-01 --end 2025-01-01 --outdir outputs/portfolio --portfolio-mode

# Compare strategy vs NIFTY50 benchmark
python -m src.cli batch --universe configs/universe_nifty50_stocks.txt --start 2020-01-01 --end 2025-01-01 --outdir outputs/comparison --compare-index ^NSEI
```

### Paper Trading Simulation

```bash
python -m src.cli paper --ticker RELIANCE.NS --start 2020-01-01 --end 2025-01-01 --outdir outputs/paper_reliance
```

### Generate Visual Report

```bash
python -m src.cli visualize --outdir outputs/reliance --ticker RELIANCE.NS
```

---

## 9. Trading Strategies Explained

### Adaptive Elite Strategy (Primary — Recommended)

The main strategy that the dashboard uses. It intelligently adapts to market conditions:

| Market Condition | Strategy Used | How It Works |
|---|---|---|
| **Strong Uptrend** | Momentum Strategy | Rides the trend using moving average crossovers |
| **Strong Downtrend** | Momentum Strategy (Short) | Identifies sell signals in downtrends |
| **Ranging / Sideways** | Mean Reversion Strategy | Buys at support, sells at resistance using Bollinger Bands |
| **Uncertain** | ML Strategy | Uses machine learning models to find patterns |

**Signal Generation Pipeline:**
1. Download recent price data (Yahoo Finance / Upstox)
2. Calculate 50+ technical indicators (RSI, MACD, Bollinger Bands, ATR, ADX, Stochastic, Ichimoku, etc.)
3. Detect market regime (trending vs ranging) using ADX + volatility
4. Select the optimal sub-strategy for the detected regime
5. Run ML ensemble (Logistic Regression + XGBoost + LSTM) for probability prediction
6. Apply signal filters (minimum confidence, volume confirmation, trend alignment)
7. Generate final signal with entry, stop loss, and target prices

### Sub-Strategies

| Strategy | Best For | Key Indicators |
|---|---|---|
| **ML Strategy** | Pattern recognition | Logistic Regression on 50+ features |
| **Momentum Strategy** | Trending markets | MA crossovers, ADX, momentum |
| **Mean Reversion Strategy** | Sideways markets | Bollinger Bands, RSI, Z-score |

### AI Models (ELITE System)

| Model | Type | Strength |
|---|---|---|
| **Logistic Regression** | Traditional ML | Fast, interpretable, good baseline |
| **XGBoost** | Gradient Boosting | Excellent with tabular data, handles non-linearity |
| **LSTM** | Deep Learning | Captures sequential patterns in time-series data |
| **Ensemble** | Combined | Weighted average of all models for best accuracy |

---

## 10. Broker Integration (Upstox / Zerodha)

### Upstox (Primary Supported Broker)

1. **Get API credentials** from [Upstox Developer Portal](https://api.upstox.com/)
2. **Add to `.env` file:**
   ```env
   UPSTOX_API_KEY=your_api_key
   UPSTOX_API_SECRET=your_api_secret
   UPSTOX_REDIRECT_URI=http://localhost:5000/callback
   ```
3. **Start the dashboard** and click "Connect Broker" in the header
4. **Authorize** via the Upstox login page that opens
5. Once connected, you get:
   - Real-time price streaming via WebSocket
   - Live order placement and management
   - Real portfolio and holdings data

### Zerodha (Alternative)

1. Get API key/secret from [Zerodha Kite Developer](https://developers.kite.trade/)
2. Configure in `.env`:
   ```env
   ZERODHA_API_KEY=your_api_key
   ZERODHA_API_SECRET=your_api_secret
   ```
3. Follow the OAuth login flow to generate `access_token`

> **Important:** Broker integration is completely optional. The platform works fully with Yahoo Finance data for signals, research, and paper trading.

---

## 11. Paper Trading vs Live Trading

| Feature | Paper Trading | Live Trading |
|---|---|---|
| **Real money** | No | Yes |
| **Data source** | Yahoo Finance | Broker API (real-time) |
| **Order execution** | Simulated locally | Sent to broker exchange |
| **P&L tracking** | Full (simulated) | Full (real) |
| **Risk** | Zero | Real financial risk |
| **Requires broker** | No | Yes |

### How to Switch

- In the dashboard header, there's a **trading mode toggle**
- Switching to Live mode shows a **safety warning** requiring confirmation
- Paper trading is the **default mode** — no configuration needed

### Recommendation

1. **Start with Paper Trading** to understand how signals work
2. **Backtest** your strategy on historical data using the CLI tools
3. **Only switch to Live** after you're confident and have set up risk parameters in `configs/trading_config.yaml`

---

## 12. API Endpoints Reference

The Flask server exposes these REST API endpoints (base URL: `http://localhost:5000`):

### Market Data

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/market/indices` | Live NIFTY, SENSEX, Bank NIFTY data |
| GET | `/api/market/quote/<ticker>` | Quote for a specific stock |

### Trading Signals

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/trading/signals` | Generate signal for a stock (`{"ticker": "RELIANCE.NS"}`) |
| GET | `/api/signals/batch` | Batch signals for watchlist stocks |

### Watchlist

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/watchlist` | Get current watchlist |
| POST | `/api/watchlist/add` | Add stock to watchlist (`{"ticker": "RELIANCE.NS"}`) |
| POST | `/api/watchlist/remove` | Remove stock from watchlist |

### Orders & Trading

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/orders/place` | Place a new order |
| GET | `/api/orders` | Get order history |
| POST | `/api/orders/modify` | Modify an existing order |
| POST | `/api/orders/cancel` | Cancel an order |

### Portfolio

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/holdings` | Get current holdings |
| GET | `/api/positions` | Get open positions |
| GET | `/api/portfolio/history` | Historical portfolio data |

### Broker Connection

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/connection/status` | Check broker connection status |
| GET | `/auth/login` | Initiate Upstox OAuth login |
| GET | `/callback` | OAuth callback handler |

---

## 13. Troubleshooting

### "Module not found" Errors

```bash
# Make sure you're in the project root directory
cd StockAI-Trading

# Reinstall all dependencies
pip install -r requirements.txt
```

### Port 5000 Already in Use

```bash
# Check what's using port 5000
# Windows:
netstat -ano | findstr :5000

# Kill the process or use a different port:
# Edit run_web.py line: socketio.run(app, port=5001)
```

### TensorFlow / XGBoost Installation Issues

If TensorFlow fails to install (common on some systems):

```bash
# Install TensorFlow separately
pip install tensorflow --no-cache-dir

# If GPU issues, use CPU-only version
pip install tensorflow-cpu
```

If XGBoost fails:

```bash
pip install xgboost --no-cache-dir
```

> The algorithm still works without these — it falls back to Logistic Regression for signals.

### No Data / Empty Signals

1. Check internet connection (Yahoo Finance requires internet)
2. Verify the ticker format: use `.NS` suffix for NSE stocks (e.g., `RELIANCE.NS`, `TCS.NS`)
3. Markets may be closed — try on a weekday between 9:15 AM and 3:30 PM IST for live data
4. Historical data always works regardless of market hours

### Dashboard Not Loading

1. Check the terminal for error messages
2. Make sure no other app is using port 5000
3. Try accessing `http://127.0.0.1:5000` instead of `localhost`
4. Clear browser cache (Ctrl+Shift+Delete)

### Broker Connection Issues

1. Verify API credentials in `.env` file
2. Check if the access token has expired (Upstox tokens expire daily)
3. Re-authenticate by visiting `http://localhost:5000/auth/login`

---

## 14. Safety & Disclaimer

> **This software is for EDUCATIONAL and RESEARCH purposes only.**

- **Markets are risky.** You can lose money. Past performance does not guarantee future results.
- **Backtests can be misleading** due to overfitting, survivorship bias, and changing market regimes.
- **Always use Paper Trading first** to understand how the algorithm behaves.
- **Set strict risk limits** in `configs/trading_config.yaml` before any live trading.
- **Never invest money you cannot afford to lose.**
- **The developers are not responsible** for any financial losses incurred while using this software.
- **Consult a financial advisor** before making investment decisions.

---

## Quick Start Cheatsheet

```bash
# 1. Clone & install
git clone https://github.com/rahulborse-netizen/StockAI-Trading.git
cd StockAI-Trading
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt

# 2. Start dashboard
python run_web.py
# Open http://localhost:5000

# 3. Get signals from terminal (with server running)
python get_signals.py RELIANCE.NS
python get_signals.py --all

# 4. Run a backtest
python -m src.cli research --ticker RELIANCE.NS --start 2020-01-01 --end 2025-01-01 --outdir outputs/reliance
```

---

*Last updated: February 2026*
