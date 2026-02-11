from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from datetime import timedelta

import numpy as np
import pandas as pd
import time
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OHLCV:
    df: pd.DataFrame  # index: DatetimeIndex (tz-naive), columns: open/high/low/close/volume


def _is_index_ticker(ticker: str) -> bool:
    """Check if ticker is an index (starts with ^)"""
    return ticker.startswith("^")


def _validate_ohlcv_data(df: pd.DataFrame, ticker: str) -> None:
    """
    Validate OHLCV data for gaps, outliers, and data quality issues.
    Raises ValueError with descriptive messages if issues are found.
    """
    if df.empty:
        raise ValueError(f"No data returned for ticker {ticker}. Check ticker symbol and date range.")

    # Check for required columns
    required = ["open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required columns for {ticker}: {missing}. "
            f"Available columns: {list(df.columns)}"
        )

    # Check for all NaN rows
    all_nan_rows = df[required].isna().all(axis=1)
    if all_nan_rows.any():
        nan_count = all_nan_rows.sum()
        logger.warning(f"{ticker}: Found {nan_count} rows with all NaN values. These will be dropped.")

    # Check for negative prices (shouldn't happen)
    price_cols = ["open", "high", "low", "close"]
    for col in price_cols:
        if (df[col] < 0).any():
            neg_count = (df[col] < 0).sum()
            raise ValueError(
                f"{ticker}: Found {neg_count} negative values in {col}. "
                "This indicates corrupted data."
            )

    # Check OHLC consistency (high >= low, high >= open, high >= close, low <= open, low <= close)
    invalid_ohlc = (
        (df["high"] < df["low"]) |
        (df["high"] < df["open"]) |
        (df["high"] < df["close"]) |
        (df["low"] > df["open"]) |
        (df["low"] > df["close"])
    )
    if invalid_ohlc.any():
        invalid_count = invalid_ohlc.sum()
        logger.warning(
            f"{ticker}: Found {invalid_count} rows with invalid OHLC relationships "
            "(e.g., high < low). These may indicate data quality issues."
        )

    # Check for large gaps (timeframe-dependent)
    if len(df) > 1:
        date_diff = df.index.to_series().diff()
        # Determine expected gap based on data frequency
        # For daily data, gaps > 7 days are suspicious
        # For intraday data, gaps > 1 day are suspicious (market closed)
        # This is a simple heuristic - could be improved with actual interval detection
        if len(df) > 10:
            median_gap = date_diff.median()
            # If median gap is < 1 day, likely intraday data
            if median_gap < pd.Timedelta(days=1):
                # Intraday: gaps > 1 day are suspicious
                large_gaps = date_diff > pd.Timedelta(days=1)
                gap_threshold = "1 day"
            else:
                # Daily: gaps > 7 days are suspicious
                large_gaps = date_diff > pd.Timedelta(days=7)
                gap_threshold = "7 days"
            
            if large_gaps.any():
                gap_count = large_gaps.sum()
                logger.warning(
                    f"{ticker}: Found {gap_count} gaps larger than {gap_threshold}. "
                    "This may indicate missing data or market holidays."
                )

    # Check for zero or very small prices (might indicate stock split issues)
    very_small_prices = (df["close"] > 0) & (df["close"] < 0.01)
    if very_small_prices.any():
        small_count = very_small_prices.sum()
        logger.warning(
            f"{ticker}: Found {small_count} rows with very small prices (< 0.01). "
            "This might indicate data normalization issues."
        )


def _standardize_ohlcv(df: pd.DataFrame, ticker: str = "") -> pd.DataFrame:
    """
    Standardize OHLCV dataframe from yfinance format.
    
    Args:
        df: Raw dataframe from yfinance
        ticker: Ticker symbol for error messages
        
    Returns:
        Standardized dataframe with columns: open, high, low, close, volume
    """
    if df.empty:
        raise ValueError(
            f"No data returned for ticker {ticker} (empty dataframe). "
            "Check ticker symbol (use .NS for NSE, .BO for BSE, ^ for indices) and date range."
        )

    # yfinance may return MultiIndex columns (field, ticker) depending on version/settings
    if isinstance(df.columns, pd.MultiIndex):
        lvl0 = df.columns.get_level_values(0)
        lvl1 = df.columns.get_level_values(1)

        # Prefer the level that contains OHLCV field names
        field_names = {"Open", "High", "Low", "Close", "Volume", "Adj Close"}
        if set(lvl0).intersection(field_names):
            df = df.copy()
            df.columns = [str(c) for c in lvl0]
        elif set(lvl1).intersection(field_names):
            df = df.copy()
            df.columns = [str(c) for c in lvl1]
        else:
            # Fallback: join levels
            df = df.copy()
            df.columns = ["_".join(map(str, c)).strip() for c in df.columns.to_list()]

    # yfinance returns columns like: Open High Low Close Adj Close Volume
    rename = {c: c.lower().replace(" ", "_") for c in df.columns}
    df = df.rename(columns=rename)

    # For indices, volume may be missing or zero - handle gracefully
    is_index = _is_index_ticker(ticker) if ticker else False
    
    required = ["open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required columns for {ticker}: {missing}. "
            f"Got columns: {list(df.columns)}. "
            "This might indicate an invalid ticker symbol or data source issue."
        )

    # Handle volume - indices may not have volume
    if "volume" not in df.columns:
        if is_index:
            logger.info(f"{ticker}: No volume data available (index ticker). Using zero volume.")
            df["volume"] = 0.0
        else:
            logger.warning(
                f"{ticker}: No volume column found. This is unusual for stocks. "
                "Using zero volume as fallback."
            )
            df["volume"] = 0.0

    # Select required columns
    df = df[required + ["volume"]].copy()
    
    # Drop rows where all OHLC are NaN
    df = df.dropna(subset=required, how="all")
    
    df.index = pd.to_datetime(df.index)
    # drop timezone to keep downstream simple
    if getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_convert(None)
    df = df.sort_index()
    
    return df


def load_cached_csv(path: Path) -> OHLCV:
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.set_index("date").sort_index()
    return OHLCV(df=df)


def save_cached_csv(ohlcv: OHLCV, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = ohlcv.df.copy()
    out.insert(0, "date", out.index)
    out.to_csv(path, index=False)


def _is_intraday_interval(interval: str) -> bool:
    """Check if interval is intraday (not daily or longer)"""
    intraday_intervals = {'1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h'}
    return interval.lower() in intraday_intervals


def download_yahoo_ohlcv(
    ticker: str,
    start: str,
    end: str,
    interval: str = "1d",
    cache_path: Optional[Path] = None,
    refresh: bool = False,
    retries: int = 3,
    retry_sleep_s: float = 1.0,
    validate: bool = True,
) -> OHLCV:
    """
    Download OHLCV data via Yahoo Finance with enhanced error handling and validation.
    Supports both daily and intraday intervals (5m, 15m, 1h, etc.).

    Args:
        ticker: Yahoo Finance ticker symbol
            - NSE stocks: `RELIANCE.NS`, `TCS.NS`
            - BSE stocks: `RELIANCE.BO`
            - Indices: `^NSEI`, `^NSEBANK`, `^BSESN`
        start: Start date in YYYY-MM-DD format
        end: End date in YYYY-MM-DD format
        interval: Data interval
            - Daily: "1d" (default)
            - Intraday: "1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h"
            - Note: Intraday data limited to last 60 days by Yahoo Finance
        cache_path: Optional path to cache CSV file
        refresh: If True, re-download even if cache exists
        retries: Number of retry attempts (default: 3)
        retry_sleep_s: Base sleep time between retries in seconds (default: 1.0)
            Uses exponential backoff: sleep_time = retry_sleep_s * (2 ** (attempt - 1))
        validate: If True, validate data quality (gaps, outliers, etc.)

    Returns:
        OHLCV dataclass with standardized dataframe

    Raises:
        RuntimeError: If download fails after all retries
        ValueError: If data validation fails or data is invalid
    """
    # Validate ticker format
    ticker = ticker.strip()
    if not ticker:
        raise ValueError("Ticker cannot be empty")
    
    # Validate interval
    interval = interval.lower()
    valid_intervals = {'1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '1wk', '1mo'}
    if interval not in valid_intervals:
        raise ValueError(
            f"Invalid interval '{interval}'. "
            f"Supported intervals: {', '.join(sorted(valid_intervals))}"
        )
    
    is_intraday = _is_intraday_interval(interval)
    
    # Validate and fix dates to prevent future date issues
    from datetime import datetime as dt
    try:
        start_dt = dt.strptime(start, '%Y-%m-%d')
        end_dt = dt.strptime(end, '%Y-%m-%d')
        today_dt = dt.now()
        
        # Ensure end date is not more than 1 day in the future
        if end_dt > today_dt + timedelta(days=1):
            logger.warning(f"End date {end} is in the future! Adjusting to today.")
            end = today_dt.strftime('%Y-%m-%d')
            end_dt = dt.strptime(end, '%Y-%m-%d')
        
        # For intraday intervals, enforce 60-day limit
        if is_intraday:
            max_intraday_days = 60
            days_diff = (end_dt - start_dt).days
            if days_diff > max_intraday_days:
                logger.warning(
                    f"Intraday interval '{interval}' requested for {days_diff} days. "
                    f"Yahoo Finance limits intraday data to {max_intraday_days} days. "
                    f"Adjusting start date to {max_intraday_days} days before end date."
                )
                start_dt = end_dt - timedelta(days=max_intraday_days)
                start = start_dt.strftime('%Y-%m-%d')
            elif end_dt > today_dt:
                # For intraday, end date should be today or earlier
                end = today_dt.strftime('%Y-%m-%d')
                end_dt = today_dt
        
        # Ensure start < end
        if start_dt >= end_dt:
            if is_intraday:
                # For intraday, default to last 20 days
                default_days = 20
                start_dt = end_dt - timedelta(days=default_days)
                start = start_dt.strftime('%Y-%m-%d')
                logger.warning(
                    f"Start date {start} >= End date {end}! "
                    f"Adjusting start date to {default_days} days before end date."
                )
            else:
                logger.warning(f"Start date {start} >= End date {end}! Adjusting start date.")
                start = (end_dt - timedelta(days=365)).strftime('%Y-%m-%d')
        
        logger.info(f"Validated dates for {ticker} ({interval}): {start} to {end}")
    except Exception as date_err:
        logger.error(f"Date validation error: {date_err}. Using dates as-is: {start} to {end}")

    # Check cache first
    if cache_path and cache_path.exists() and not refresh:
        try:
            cached = load_cached_csv(cache_path)
            if validate:
                _validate_ohlcv_data(cached.df, ticker)
            logger.info(f"Loaded cached data for {ticker} from {cache_path}")
            return cached
        except Exception as e:
            logger.warning(f"Failed to load cache for {ticker}: {e}. Re-downloading...")

    import yfinance as yf

    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Downloading {ticker} (attempt {attempt}/{retries})...")
            
            df = yf.download(
                tickers=ticker,
                start=start,
                end=end,
                interval=interval,
                auto_adjust=False,
                progress=False,
                threads=False,  # more stable on some networks
                group_by="column",
            )
            
            if df is not None and not df.empty:
                logger.info(f"Successfully downloaded {len(df)} rows for {ticker}")
                break
                
            last_err = ValueError(
                f"No data returned for {ticker} (empty dataframe). "
                f"Date range: {start} to {end}. "
                "Possible causes: invalid ticker, market holidays, or data source issue."
            )
        except Exception as e:  # noqa: BLE001
            last_err = e
            error_msg = str(e)
            logger.warning(
                f"Attempt {attempt}/{retries} failed for {ticker}: {error_msg}"
            )
            
            # Provide helpful error messages for common issues
            if "certificate" in error_msg.lower() or "ssl" in error_msg.lower():
                logger.warning(
                    "SSL certificate issue detected. Try: "
                    "`python -m pip install --upgrade certifi`"
                )
            elif "timeout" in error_msg.lower() or "connection" in error_msg.lower():
                logger.warning("Network/connection issue detected. Will retry...")
        
        # Exponential backoff: sleep longer on each retry
        if attempt < retries:
            sleep_time = retry_sleep_s * (2 ** (attempt - 1))
            logger.info(f"Waiting {sleep_time:.1f}s before retry...")
            time.sleep(sleep_time)
    else:
        # All retries exhausted
        error_details = []
        if last_err:
            error_details.append(f"Last error: {str(last_err)}")
        error_details.append(f"Ticker: {ticker}")
        error_details.append(f"Date range: {start} to {end}")
        error_details.append(f"Interval: {interval}")
        
        raise RuntimeError(
            f"Failed to download Yahoo Finance data for {ticker} after {retries} retries.\n"
            + "\n".join(f"  - {detail}" for detail in error_details) + "\n\n"
            "Troubleshooting tips:\n"
            "  1. Verify ticker symbol (use .NS for NSE, .BO for BSE, ^ for indices)\n"
            "  2. Check date range (ensure market was open during this period)\n"
            "  3. If on corporate network/proxy, try:\n"
            "     - `python -m pip install --upgrade certifi`\n"
            "     - Set SSL_CERT_FILE or REQUESTS_CA_BUNDLE environment variables\n"
            "  4. Check internet connection and firewall settings\n"
            "  5. Try again later (Yahoo Finance may be temporarily unavailable)"
        ) from last_err

    # Standardize and validate data
    try:
        df = _standardize_ohlcv(df, ticker=ticker)
        
        if validate:
            _validate_ohlcv_data(df, ticker)
        
        ohlcv = OHLCV(df=df)
        
        # Save to cache
        if cache_path:
            try:
                save_cached_csv(ohlcv, cache_path)
                logger.info(f"Cached data for {ticker} to {cache_path}")
            except Exception as e:
                logger.warning(f"Failed to cache data for {ticker}: {e}")
        
        return ohlcv
        
    except Exception as e:
        raise ValueError(
            f"Data validation/standardization failed for {ticker}: {str(e)}\n"
            "This might indicate corrupted data or an unsupported ticker format."
        ) from e

