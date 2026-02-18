from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from datetime import timedelta

import numpy as np
import pandas as pd
import time
import logging
import threading

# Set SSL certs for yfinance/curl before any HTTP (avoids "unable to get local issuer certificate")
try:
    import certifi
    _ca = certifi.where()
    # Force set so curl_cffi/libcurl pick up the bundle (setdefault can leave wrong value)
    os.environ["SSL_CERT_FILE"] = _ca
    os.environ["REQUESTS_CA_BUNDLE"] = _ca
    os.environ["CURL_CA_BUNDLE"] = _ca
except ImportError:
    pass

logger = logging.getLogger(__name__)

# Rate limiter for Yahoo Finance API - throttle requests to avoid 429 errors
_yahoo_rate_limiter_lock = threading.Lock()
_yahoo_last_request_time = 0.0
_yahoo_min_interval = 2.0  # Minimum 2 seconds between requests (0.5 req/sec max) to avoid rate limits
_yahoo_rate_limit_active = False  # Global flag if we're currently rate limited


def _wait_for_rate_limit():
    """Wait if needed to respect Yahoo Finance rate limits."""
    global _yahoo_last_request_time, _yahoo_rate_limit_active
    with _yahoo_rate_limiter_lock:
        # If we're rate limited, wait longer
        if _yahoo_rate_limit_active:
            wait_time = 30.0  # Wait 30 seconds if rate limited
            elapsed = time.time() - _yahoo_last_request_time
            if elapsed < wait_time:
                sleep_time = wait_time - elapsed
                logger.debug(f"Rate limit active, waiting {sleep_time:.1f}s...")
                time.sleep(sleep_time)
        else:
            # Normal rate limiting
            elapsed = time.time() - _yahoo_last_request_time
            if elapsed < _yahoo_min_interval:
                sleep_time = _yahoo_min_interval - elapsed
                time.sleep(sleep_time)
        _yahoo_last_request_time = time.time()


@dataclass(frozen=True)
class OHLCV:
    df: pd.DataFrame  # index: DatetimeIndex (tz-naive), columns: open/high/low/close/volume


def _is_index_ticker(ticker: str) -> bool:
    """Check if ticker is an index (starts with ^)"""
    return ticker.startswith("^")


# Map index names to Yahoo tickers - never append .NS to these
_YAHOO_INDEX_MAP = {
    'nifty': '^NSEI',
    'nifty50': '^NSEI',
    'banknifty': '^NSEBANK',
    'sensex': '^BSESN',
    'vix': '^INDIAVIX',
    'indiavix': '^INDIAVIX',
    'niftysmallcap': '^CNXSMALLCAP',
    'nifty100': '^CNX100',
    'nifty500': '^CNX500',
    'niftyit': '^CNXIT',
    'niftyfmcg': '^CNXFMCG',
    'niftypharma': '^CNXPHARMA',
    'niftyauto': '^CNXAUTO',
    'niftymetal': '^CNXMETAL',
    'niftyenergy': '^CNXENERGY',
    'niftyrealty': '^CNXREALTY',
    'niftypsu': '^CNXPSU',
    'niftymidcap': '^CNXMID',
}


def _yahoo_ticker(symbol: str) -> str:
    """Return correct Yahoo ticker. Indices map to ^NSEI etc; NSE stocks get .NS."""
    s = str(symbol or "").strip().lower()
    if not s:
        return s
    if s.startswith("^"):
        return symbol.strip()  # Preserve original case for ^
    mapped = _YAHOO_INDEX_MAP.get(s)
    if mapped:
        return mapped
    s_orig = str(symbol or "").strip()
    if "." in s_orig:
        return s_orig
    return f"{s_orig}.NS"


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
    if df is None or not isinstance(df, pd.DataFrame):
        raise ValueError(
            f"No data returned for {ticker} (invalid or None dataframe). "
            "Check ticker symbol and date range. Yahoo Finance may have returned an invalid structure."
        )
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
    *,
    _raw_ticker: Optional[str] = None,
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
    # Declare global variables for rate limiting
    global _yahoo_rate_limit_active
    
    # Validate and normalize ticker for Yahoo Finance (skip when using alternate index ticker)
    if _raw_ticker is not None:
        ticker = str(_raw_ticker).strip()
    else:
        ticker = _yahoo_ticker(ticker.strip())
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
    
    # Try to import YFRateLimitError for direct exception catching
    try:
        from yfinance.exceptions import YFRateLimitError
    except ImportError:
        YFRateLimitError = None

    # Optional: skip SSL verify for corporate proxies (set YFINANCE_INSECURE_SSL=1)
    _session = None
    _ssl_error_detected = False
    _rate_limit_detected = False
    if os.environ.get("YFINANCE_INSECURE_SSL", "").strip() == "1":
        try:
            from curl_cffi import requests as ccurl
            _session = ccurl.Session(impersonate="chrome", verify=False)
            logger.warning("YFINANCE_INSECURE_SSL=1: SSL verification disabled for yfinance (insecure).")
        except Exception as e:
            logger.warning("YFINANCE_INSECURE_SSL=1 but curl_cffi session failed: %s", e)

    last_err: Exception | None = None
    df = None
    for attempt in range(1, retries + 1):
        # Rate limit throttling - wait before each request
        _wait_for_rate_limit()
        
        try:
            logger.info(f"Downloading {ticker} (attempt {attempt}/{retries})...")
            kw = dict(
                tickers=ticker,
                start=start,
                end=end,
                interval=interval,
                auto_adjust=False,
                progress=False,
                threads=False,
                group_by="column",
            )
            if _session is not None:
                kw["session"] = _session
            
            # Check if we're currently rate limited before making request
            if _yahoo_rate_limit_active:
                wait_time = 30.0
                logger.warning(f"Rate limit is active, waiting {wait_time}s before request for {ticker}...")
                time.sleep(wait_time)
                _yahoo_rate_limit_active = False  # Reset after waiting
            
            df = yf.download(**kw)
            if df is not None and not df.empty:
                logger.info(f"Successfully downloaded {len(df)} rows for {ticker}")
                break
            if df is None:
                df = pd.DataFrame()
            last_err = ValueError(
                f"No data returned for {ticker} (empty dataframe). "
                f"Date range: {start} to {end}. "
                "Possible causes: invalid ticker, market holidays, or data source issue."
            )
        except ValueError as e:
            # yfinance can raise "No objects to concatenate" when all fetches fail (e.g. SSL)
            last_err = e
            df = pd.DataFrame()
            err_str = str(e).lower()
            err_type = type(e).__name__
            
            # Check for rate limiting in ValueError too
            if ("ratelimit" in err_str or "rate limit" in err_str or "too many requests" in err_str or 
                "429" in err_str or "YFRateLimitError" in err_type):
                _rate_limit_detected = True
                _yahoo_rate_limit_active = True
                logger.warning(f"Rate limit detected for {ticker} (ValueError). Will use longer backoff (30s+).")
            
            if "ssl" in err_str or "certificate" in err_str or "curl" in err_str:
                _ssl_error_detected = True
            if "No objects to concatenate" in str(e):
                # This usually means yfinance failed (often SSL) - treat as SSL issue for auto-retry
                _ssl_error_detected = True
                logger.warning(
                    "Attempt %s/%s failed for %s: No data (likely SSL or empty response).",
                    attempt, retries, ticker
                )
            else:
                logger.warning("Attempt %s/%s failed for %s: %s", attempt, retries, ticker, e)
        except Exception as e:  # noqa: BLE001
            last_err = e
            df = pd.DataFrame()
            err_str = str(e).lower()
            err_type = type(e).__name__
            err_module = type(e).__module__
            
            # Detect rate limiting - check if it's YFRateLimitError directly first
            is_rate_limit = False
            if YFRateLimitError and isinstance(e, YFRateLimitError):
                is_rate_limit = True
                logger.warning(f"YFRateLimitError caught directly for {ticker}. Will use longer backoff (30s+).")
            elif (
                "ratelimit" in err_str or 
                "rate limit" in err_str or 
                "too many requests" in err_str or 
                "429" in err_str or 
                "YFRateLimitError" in err_type or
                "YFRateLimitError" in str(type(e)) or
                "RateLimitError" in err_type
            ):
                is_rate_limit = True
            
            if is_rate_limit:
                _rate_limit_detected = True
                _yahoo_rate_limit_active = True
                logger.warning(f"Rate limit detected for {ticker} (type: {err_type}, module: {err_module}). Will use longer backoff (30s+).")
            else:
                # Debug: log exception details when not detected as rate limit
                if "rate" in err_str or "limit" in err_str or "429" in err_str:
                    logger.debug(f"Possible rate limit not detected: type={err_type}, str={err_str[:100]}")
            
            if "ssl" in err_str or "certificate" in err_str or "curl" in err_str or "60" in err_str:
                _ssl_error_detected = True
                if _session is None and attempt == 1:
                    logger.warning(
                        "SSL certificate error detected. Set YFINANCE_INSECURE_SSL=1 to disable SSL verify (insecure)."
                    )
            logger.warning(
                f"Attempt {attempt}/{retries} failed for {ticker}: {e}"
            )
        
        # If SSL error detected and no session yet, create one with verify=False for remaining retries
        if _ssl_error_detected and _session is None and attempt < retries:
            try:
                from curl_cffi import requests as ccurl
                _session = ccurl.Session(impersonate="chrome", verify=False)
                logger.warning(
                    "SSL error detected: Automatically retrying with SSL verify disabled (insecure). "
                    "Set YFINANCE_INSECURE_SSL=1 to enable this by default."
                )
            except Exception:
                pass  # curl_cffi not available, continue with normal retries
        
        # Exponential backoff: sleep longer on each retry
        # Use much longer backoff if rate limited (30-60 seconds)
        if attempt < retries:
            if _rate_limit_detected:
                # Rate limit backoff: 30s, 60s, 90s
                sleep_time = 30 * attempt
                logger.warning(f"Rate limited. Waiting {sleep_time:.1f}s before retry...")
                time.sleep(sleep_time)
                # Reset rate limit flag after waiting (will be set again if still rate limited)
                _yahoo_rate_limit_active = False
            else:
                sleep_time = retry_sleep_s * (2 ** (attempt - 1))
                logger.info(f"Waiting {sleep_time:.1f}s before retry...")
                time.sleep(sleep_time)
    else:
        # All retries exhausted for primary ticker
        # If SSL error was detected but we haven't tried with verify=False yet, do one more attempt
        if _ssl_error_detected and _session is None:
            try:
                from curl_cffi import requests as ccurl
                _session = ccurl.Session(impersonate="chrome", verify=False)
                logger.warning(
                    "SSL error detected on final attempt: Retrying once more with SSL verify disabled (insecure)."
                )
                # Do one final attempt with verify=False
                try:
                    logger.info(f"Downloading {ticker} (final SSL-retry attempt)...")
                    kw = dict(
                        tickers=ticker,
                        start=start,
                        end=end,
                        interval=interval,
                        auto_adjust=False,
                        progress=False,
                        threads=False,
                        group_by="column",
                        session=_session,
                    )
                    df = yf.download(**kw)
                    if df is not None and not df.empty:
                        df = _standardize_ohlcv(df, ticker)
                        if df is not None and not df.empty:
                            if validate:
                                df = _validate_ohlcv(df, ticker, start, end)
                            if cache_path and df is not None and not df.empty:
                                df.to_csv(cache_path)
                            return OHLCV(df=df)
                except Exception as final_err:
                    logger.debug(f"Final SSL-retry attempt failed: {final_err}")
            except Exception:
                pass  # curl_cffi not available, continue to error
        # For index tickers (^NSEI etc.), yfinance sometimes raises TypeError internally;
        # try once with ticker without ^ (e.g. NSEI) before giving up.
        if ticker.startswith("^"):
            alt_ticker = ticker[1:]
            logger.info(
                "Trying alternate index ticker %s (without ^) after primary %s failed",
                alt_ticker,
                ticker,
            )
            try:
                return download_yahoo_ohlcv(
                    ticker,  # original ticker for cache_path/logging
                    start=start,
                    end=end,
                    interval=interval,
                    cache_path=cache_path,
                    refresh=refresh,
                    retries=1,
                    retry_sleep_s=retry_sleep_s,
                    validate=validate,
                    _raw_ticker=alt_ticker,
                )
            except Exception:
                pass  # fall through to raise with primary ticker

        error_details = []
        if last_err:
            error_details.append(f"Last error: {str(last_err)}")
        error_details.append(f"Ticker: {ticker}")
        error_details.append(f"Date range: {start} to {end}")
        error_details.append(f"Interval: {interval}")
        if _ssl_error_detected and _session is not None:
            error_details.append("Note: SSL verification was automatically disabled due to certificate errors.")
        
        raise RuntimeError(
            f"Failed to download Yahoo Finance data for {ticker} after {retries} retries.\n"
            + "\n".join(f"  - {detail}" for detail in error_details) + "\n\n"
            "Troubleshooting tips:\n"
            "  1. Verify ticker symbol (use .NS for NSE, .BO for BSE, ^ for indices)\n"
            "  2. Check date range (ensure market was open during this period)\n"
            "  3. If on corporate network/proxy, try:\n"
            "     - `python -m pip install --upgrade certifi`\n"
            "     - Set SSL_CERT_FILE / REQUESTS_CA_BUNDLE / CURL_CA_BUNDLE to certifi.where()\n"
            "     - Or set YFINANCE_INSECURE_SSL=1 to skip SSL verify (insecure, last resort)\n"
            "  4. Check internet connection and firewall settings\n"
            "  5. Try again later (Yahoo Finance may be temporarily unavailable)"
        ) from last_err

    # Guard: yfinance can still return None in edge cases
    if df is None:
        df = pd.DataFrame()
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

