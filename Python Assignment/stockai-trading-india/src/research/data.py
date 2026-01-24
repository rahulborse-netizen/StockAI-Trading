from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd
import time


@dataclass(frozen=True)
class OHLCV:
    df: pd.DataFrame  # index: DatetimeIndex (tz-naive), columns: open/high/low/close/volume


def _standardize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        raise ValueError("No data returned (empty dataframe). Check ticker/date range.")

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

    required = ["open", "high", "low", "close", "volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns: {missing}. Got: {list(df.columns)}")

    df = df[required].copy()
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


def download_yahoo_ohlcv(
    ticker: str,
    start: str,
    end: str,
    interval: str = "1d",
    cache_path: Optional[Path] = None,
    refresh: bool = False,
    retries: int = 3,
    retry_sleep_s: float = 1.0,
) -> OHLCV:
    """
    Download OHLCV data via Yahoo Finance.

    For Indian equities, tickers are typically:
    - NSE: `RELIANCE.NS`, `TCS.NS`
    - BSE: `RELIANCE.BO`
    """
    if cache_path and cache_path.exists() and not refresh:
        return load_cached_csv(cache_path)

    import yfinance as yf

    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
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
                break
            last_err = ValueError("No data returned (empty dataframe).")
        except Exception as e:  # noqa: BLE001
            last_err = e
        if attempt < retries:
            time.sleep(retry_sleep_s)
    else:
        raise RuntimeError(
            "Failed to download Yahoo Finance data after retries. "
            "If you're on a corporate network/proxy, this can be an SSL certificate issue. "
            "Try upgrading certifi (`python -m pip install --upgrade certifi`) or configuring "
            "`SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` to your organization's root CA."
        ) from last_err

    df = _standardize_ohlcv(df)
    ohlcv = OHLCV(df=df)

    if cache_path:
        save_cached_csv(ohlcv, cache_path)

    return ohlcv

