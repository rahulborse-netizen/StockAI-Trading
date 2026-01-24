# StockAI Trading Tool

## Overview
StockAI is an AI-driven trading tool designed for real-time trading in the Indian stock market. This project aims to provide a comprehensive framework for data ingestion, strategy execution, and broker integration, enabling users to automate their trading processes effectively.

## Project Structure
The project is organized into several directories and files, each serving a specific purpose:

- **src/**: Contains the main application code.
  - **main.py**: Entry point for the application.
  - **app.py**: Main application logic.
  - **config.py**: Configuration settings.
  - **broker/**: Broker integration, including Zerodha adapter.
  - **data/**: Data ingestion and loading.
  - **strategies/**: Trading strategies implementation.
  - **models/**: Machine learning models for predictions.
  - **features/**: Feature engineering functions.
  - **realtime/**: Real-time data handling.
  - **utils/**: Utility functions and logging.
  - **schemas/**: Data schemas and types.

- **notebooks/**: Jupyter notebooks for exploratory data analysis and model experimentation.

- **tests/**: Unit tests for strategies and broker integration.

- **scripts/**: Shell scripts for running backtests and deployment.

- **docs/**: Documentation for the architecture of the trading tool.

- **configs/**: Configuration files in YAML format.

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
   - Example (NSE ticker via Yahoo Finance):
     ```
     python -m src.cli research --ticker RELIANCE.NS --start 2020-01-01 --end 2025-01-01 --outdir outputs/reliance
     ```
   - Outputs:
     - `model.joblib` (trained baseline model)
     - `predictions.csv` (test-set probabilities)
     - `equity_curve.csv` and `stats.json` (backtest results)

5. Run the (placeholder) real-time app:
   ```
   python src/main.py
   ```

## Safety / Disclaimer
This project is for **educational and research** purposes. Markets are risky; backtests can be misleading due to
overfitting, survivorship bias, and changing regimes. Use **paper trading** and strong risk controls before any live use.

## Usage
- Modify the strategies in the `src/strategies/` directory to implement your trading logic.
- Use the Jupyter notebooks in the `notebooks/` directory for data analysis and model experimentation.
- Run tests to ensure the functionality of your strategies and broker integration.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.