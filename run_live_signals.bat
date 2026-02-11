@echo off
REM Run trading signals on live NSE data (use when market is open)
cd /d "%~dp0"

REM UTF-8 encoding for emoji output on Windows
set PYTHONIOENCODING=utf-8

echo ============================================================
echo Live Trading Signals - NSE Data
echo ============================================================
echo.

REM Default: scan 5 stocks. Edit below to add/change stocks.
python trading_signals_nse_only.py --stocks RELIANCE TCS INFY HDFCBANK ICICIBANK --min-confidence 0.50

echo.
pause
