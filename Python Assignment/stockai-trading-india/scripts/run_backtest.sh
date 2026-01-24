#!/bin/bash

# This script runs backtests on trading strategies.

# Set the environment variables
source ../.env

# Activate the virtual environment
source venv/bin/activate

# Run the backtest using the main application script
python ../src/main.py --mode backtest --strategy example_strategy --data_path ../data/historical_data.csv

# Deactivate the virtual environment
deactivate

echo "Backtest completed."