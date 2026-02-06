# StockAI Trading Tool

## Overview
StockAI is an AI-driven trading tool designed for real-time trading in the Indian stock market. This project aims to provide a comprehensive framework for data ingestion, strategy execution, and broker integration, enabling users to automate their trading processes effectively.

## Project Structure
The project is organized into several directories and files, each serving a specific purpose:

- **src/**: Contains the main application code.
  - **main.py**: Entry point for the application.
  - **app.py**: Main application logic.
  - **config.py**: Configuration settings.
  - **cli.py**: Command-line interface for research, batch, and paper trading.
  - **broker/**: Broker integration, including Zerodha adapter.
  - **data/**: Data ingestion and loading.
  - **strategies/**: Trading strategies implementation.
  - **models/**: Machine learning models for predictions.
  - **features/**: Feature engineering functions.
  - **realtime/**: Real-time data handling.
  - **utils/**: Utility functions and logging.
  - **schemas/**: Data schemas and types.
  - **research/**: Research and backtesting modules.
    - **backtest.py**: Single-asset backtesting.
    - **portfolio_backtest.py**: Multi-asset portfolio backtesting.
    - **batch.py**: Batch processing across universes.
    - **data.py**: Data download and validation.
    - **visualize.py**: Charting and HTML report generation.
    - **index_analysis.py**: Index vs constituents analysis.
    - **universe.py**: Universe file loading.

- **notebooks/**: Jupyter notebooks for exploratory data analysis and model experimentation.

- **tests/**: Unit tests for strategies and broker integration.

- **scripts/**: Shell scripts for running backtests and deployment.

- **docs/**: Documentation for the architecture of the trading tool.

- **configs/**: Configuration files including universe files.
  - **universe_nifty50.txt**: NIFTY50 stocks (50 constituents)
  - **universe_nifty50_index.txt**: NIFTY50 index and ETF
  - **universe_banknifty_index.txt**: BankNifty index and ETF
  - **universe_banknifty_stocks.txt**: BankNifty constituent stocks
  - **universe_sensex_index.txt**: Sensex index and ETF
  - **universe_sensex_stocks.txt**: Sensex stocks (30 constituents)

- **Dockerfile**: Docker image definition.

- **docker-compose.yml**: Docker service configurations.

- **requirements.txt**: List of Python dependencies.

- **.env.example**: Example environment variables.

- **.gitignore**: Files and directories to ignore in Git.

## Setup Instructions
1. Clone the repository:
   ```
   git clone <repository-url>
   cd stockai-trading-india
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. (Optional) Configure environment variables for live broker connectivity in a `.env` file (not required for research/backtesting).

4. Run research/backtests (no broker credentials required):
   
   **Single Stock Research:**
   - Example (NSE ticker via Yahoo Finance):
     ```
     python -m src.cli research --ticker RELIANCE.NS --start 2020-01-01 --end 2025-01-01 --outdir outputs/reliance
     ```
   - Outputs:
     - `model.joblib` (trained baseline model)
     - `predictions.csv` (test-set probabilities)
     - `equity_curve.csv` and `stats.json` (backtest results)

   **Index Trading:**
   - Backtest NIFTY50 index:
     ```
     python -m src.cli research --ticker ^NSEI --start 2020-01-01 --end 2025-01-01 --outdir outputs/nifty50_index
     ```
   - Backtest BankNifty ETF:
     ```
     python -m src.cli research --ticker BANKBEES.NS --start 2020-01-01 --end 2025-01-01 --outdir outputs/banknifty_etf
     ```
   - Use universe files for index/ETF backtesting:
     ```
     python -m src.cli batch --universe configs/universe_nifty50_index.txt --start 2020-01-01 --end 2025-01-01 --outdir outputs/index_batch
     ```

   **Batch Processing:**
   - Batch run across NIFTY50 stocks:
     ```
     python -m src.cli batch --universe configs/universe_nifty50_stocks.txt --start 2020-01-01 --end 2025-01-01 --outdir outputs/nifty_batch
     ```
     This writes `summary.csv` with per-ticker metrics.
   
   - Batch run across BankNifty stocks:
     ```
     python -m src.cli batch --universe configs/universe_banknifty_stocks.txt --start 2020-01-01 --end 2025-01-01 --outdir outputs/banknifty_batch
     ```

   **Paper Trading:**
   - Paper trading simulation (no broker; produces a trade blotter):
     ```
     python -m src.cli paper --ticker RELIANCE.NS --start 2020-01-01 --end 2025-01-01 --outdir outputs/paper_reliance
     ```

   **Portfolio Backtesting:**
   - Portfolio backtest (multiple positions simultaneously):
     ```
     python -m src.cli batch --universe configs/universe_nifty50_stocks.txt --start 2020-01-01 --end 2025-01-01 --outdir outputs/portfolio --portfolio-mode
     ```
   - Compare strategy vs index benchmark:
     ```
     python -m src.cli batch --universe configs/universe_nifty50_stocks.txt --start 2020-01-01 --end 2025-01-01 --outdir outputs/batch_with_index --compare-index ^NSEI
     ```
   - See `docs/index_trading_guide.md` for detailed examples and best practices.

   **Visualization:**
   - Generate HTML report with charts from existing backtest results:
     ```
     python -m src.cli visualize --outdir outputs/reliance --ticker RELIANCE.NS
     ```

5. Run the web dashboard:
   ```bash
   # First, run migration script for Phase 2 features
   python scripts/migrate_to_phase2.py
   
   # Then start the web server
   python run_web.py
   ```
   Open `http://localhost:5000` in your browser to access the dashboard.

6. (Optional) Run Phase 2 integration tests:
   ```bash
   pytest tests/test_phase2_integration.py -v
   ```

## Safety / Disclaimer
This project is for **educational and research** purposes. Markets are risky; backtests can be misleading due to
overfitting, survivorship bias, and changing regimes. Use **paper trading** and strong risk controls before any live use.

## Zerodha (optional, later)
Live trading is intentionally **not enabled by default**. If you want to integrate Zerodha later:
- Get API key/secret from Zerodha developer portal
- Generate an `access_token` via the official login flow
- Provide credentials via environment variables / `.env` (never commit secrets)

## Features

### Phase 2: Real-time Trading Enhancements ✅
- **Real-time WebSocket Data Streaming**: Live price updates via WebSocket with < 100ms latency
- **Enhanced Order Management**: Modify and cancel orders with status indicators
- **Real-time Position P&L**: Live P&L calculations and updates
- **Holdings Analytics**: Historical portfolio tracking with SQLite database
- **Portfolio Performance Charts**: Value over time, daily P&L, asset allocation, returns comparison
- **Paper Trading Mode Toggle**: Safe switching between paper and live trading modes
- **Order Confirmation System**: Risk warnings and two-step confirmation for market orders
- **Position Analytics**: Win/loss ratio, exit quality analysis, holding period returns

### Phase 3: ELITE AI Trading System ✅ (Tier 1 Complete)
- **Multi-Model Ensemble**: Combines Logistic Regression, XGBoost, and LSTM for superior predictions
- **Advanced Feature Engineering**: 50+ technical indicators (Bollinger Bands, ATR, ADX, Stochastic, Ichimoku, etc.)
- **Multi-Timeframe Analysis**: Analyzes 1m, 5m, 15m, 1h, 1d timeframes with weighted consensus
- **Model Performance Tracking**: Accuracy, win rate, Sharpe ratio tracking and comparison
- **ELITE Signal Generator**: Intelligent signal generation with confidence scoring
- **Model Registry**: Centralized model management and versioning
- **Performance Analytics**: Model comparison, rankings, and historical analysis

### Index Trading Support
- **NIFTY50, BankNifty, Sensex**: Full support for index and ETF tickers
- **Complete Constituent Lists**: All 50 NIFTY50 stocks, all BankNifty banks, all 30 Sensex stocks
- **Index Analysis**: Compare index performance vs constituents, relative strength analysis

### Portfolio Backtesting
- **Multi-Asset Backtesting**: Trade multiple stocks/indices simultaneously
- **Position Sizing**: Equal weight, market cap weight, or custom weighting
- **Portfolio Metrics**: Aggregated returns, Sharpe ratio, max drawdown across positions

### Visualization & Reporting
- **Equity Curves**: Strategy vs benchmark comparison
- **Drawdown Charts**: Visualize drawdown periods
- **Correlation Heatmaps**: Analyze asset correlations in portfolios
- **HTML Reports**: Auto-generated reports with charts and statistics

### Enhanced Data Handling
- **Robust Error Handling**: Better error messages and retry logic
- **Data Validation**: Check for gaps, outliers, and data quality issues
- **Index Data Support**: Handle indices (which may have zero volume)

### Web Dashboard
- **Real-time Price Updates**: WebSocket-based live price streaming
- **Order Management**: Place, modify, and cancel orders with visual feedback
- **Portfolio Analytics**: Comprehensive analytics dashboard with charts and metrics
- **Trading Mode Toggle**: Switch between paper and live trading with safety confirmations
- **Watchlist Management**: Monitor multiple stocks simultaneously
- **Trading Signals**: AI-generated buy/sell signals with probability scores

## Usage
- Modify the strategies in the `src/strategies/` directory to implement your trading logic.
- Use the Jupyter notebooks in the `notebooks/` directory for data analysis and model experimentation.
- Run tests to ensure the functionality of your strategies and broker integration.
- See `docs/index_trading_guide.md` for detailed index trading examples and best practices.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.