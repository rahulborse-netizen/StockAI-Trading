# Configuration settings for the AI trading tool

import os

class Config:
    # API keys and tokens
    ZERODHA_API_KEY = os.getenv("ZERODHA_API_KEY", "your_api_key_here")
    ZERODHA_API_SECRET = os.getenv("ZERODHA_API_SECRET", "your_api_secret_here")

    # Trading parameters
    TRADING_SYMBOL = "NSE:RELIANCE"  # Example trading symbol
    ORDER_QUANTITY = 1  # Number of shares to trade
    STOP_LOSS_PERCENTAGE = 0.02  # Stop loss percentage
    TAKE_PROFIT_PERCENTAGE = 0.05  # Take profit percentage

    # Data settings
    DATA_SOURCE = "API"  # Options: API, CSV, etc.
    HISTORICAL_DATA_DAYS = 30  # Number of days of historical data to load

    # Logging settings
    LOG_LEVEL = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

    # Other settings
    ENABLE_REAL_TIME_TRADING = True  # Set to False for backtesting
    BACKTEST_START_DATE = "2022-01-01"  # Start date for backtesting
    BACKTEST_END_DATE = "2022-12-31"  # End date for backtesting

    @staticmethod
    def init_app(app):
        pass  # Additional initialization can be done here if needed