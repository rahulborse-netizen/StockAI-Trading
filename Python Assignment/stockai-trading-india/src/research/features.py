from __future__ import annotations

import numpy as np
import pandas as pd


def compute_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=window).mean()
    rs = gain / loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def compute_macd(close: pd.Series, short_window: int = 12, long_window: int = 26, signal_window: int = 9) -> pd.DataFrame:
    short_ema = close.ewm(span=short_window, adjust=False).mean()
    long_ema = close.ewm(span=long_window, adjust=False).mean()
    macd = short_ema - long_ema
    signal = macd.ewm(span=signal_window, adjust=False).mean()
    hist = macd - signal
    return pd.DataFrame({"macd": macd, "macd_signal": signal, "macd_hist": hist})


def make_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Input: OHLCV dataframe with columns: open/high/low/close/volume.
    Output: dataframe with added feature columns (no label).
    """
    out = df.copy()

    out["ret_1"] = out["close"].pct_change(1)
    out["ret_5"] = out["close"].pct_change(5)
    out["vol_10"] = out["ret_1"].rolling(10).std()

    out["sma_10"] = out["close"].rolling(10).mean()
    out["sma_50"] = out["close"].rolling(50).mean()
    out["ema_20"] = out["close"].ewm(span=20, adjust=False).mean()

    out["rsi_14"] = compute_rsi(out["close"], window=14)

    macd = compute_macd(out["close"])
    out = out.join(macd)

    # volume features
    out["vol_chg_1"] = out["volume"].pct_change(1)
    out["vol_sma_20"] = out["volume"].rolling(20).mean()

    return out


def add_label_forward_return_up(df_with_features: pd.DataFrame, days: int = 1, threshold: float = 0.0) -> pd.DataFrame:
    """
    Binary label: 1 if forward return over `days` bars > threshold, else 0.
    """
    if days < 1:
        raise ValueError("days must be >= 1")
    out = df_with_features.copy()
    out[f"fwd_ret_{days}"] = out["close"].pct_change(days).shift(-days)
    out["label_up"] = (out[f"fwd_ret_{days}"] > threshold).astype(int)
    return out


def add_label_next_day_up(df_with_features: pd.DataFrame, threshold: float = 0.0) -> pd.DataFrame:
    # Backwards-compatible wrapper
    return add_label_forward_return_up(df_with_features, days=1, threshold=threshold)


def clean_ml_frame(df: pd.DataFrame, feature_cols: list[str], label_col: str) -> pd.DataFrame:
    cols = feature_cols + [label_col, "close"]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in ML frame: {missing}")
    out = df[cols].replace([np.inf, -np.inf], np.nan).dropna().copy()
    return out

