"""
Advanced Feature Engineering
Enhanced technical indicators and features for ELITE AI system
"""
import numpy as np
import pandas as pd
from typing import Dict, List


def compute_bollinger_bands(close: pd.Series, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """Compute Bollinger Bands"""
    sma = close.rolling(window=window).mean()
    std = close.rolling(window=window).std()
    
    upper_band = sma + (std * num_std)
    lower_band = sma - (std * num_std)
    
    return pd.DataFrame({
        'bb_upper': upper_band,
        'bb_middle': sma,
        'bb_lower': lower_band,
        'bb_width': (upper_band - lower_band) / sma,
        'bb_position': (close - lower_band) / (upper_band - lower_band)
    })


def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """Compute Average True Range"""
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=window).mean()
    
    return atr


def compute_adx(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """Compute Average Directional Index"""
    # Calculate True Range
    atr = compute_atr(high, low, close, window)
    
    # Calculate +DM and -DM
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    # Calculate smoothed +DI and -DI
    plus_di = 100 * (plus_dm.rolling(window=window).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=window).mean() / atr)
    
    # Calculate DX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    
    # Calculate ADX
    adx = dx.rolling(window=window).mean()
    
    return adx


def compute_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k_window: int = 14, d_window: int = 3) -> pd.DataFrame:
    """Compute Stochastic Oscillator"""
    lowest_low = low.rolling(window=k_window).min()
    highest_high = high.rolling(window=k_window).max()
    
    k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
    d_percent = k_percent.rolling(window=d_window).mean()
    
    return pd.DataFrame({
        'stoch_k': k_percent,
        'stoch_d': d_percent
    })


def compute_williams_r(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """Compute Williams %R"""
    highest_high = high.rolling(window=window).max()
    lowest_low = low.rolling(window=window).min()
    
    wr = -100 * ((highest_high - close) / (highest_high - lowest_low))
    return wr


def compute_cci(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 20) -> pd.Series:
    """Compute Commodity Channel Index"""
    typical_price = (high + low + close) / 3
    sma_tp = typical_price.rolling(window=window).mean()
    mad = typical_price.rolling(window=window).apply(lambda x: np.abs(x - x.mean()).mean())
    
    cci = (typical_price - sma_tp) / (0.015 * mad)
    return cci


def compute_momentum(close: pd.Series, window: int = 10) -> pd.Series:
    """Compute Momentum"""
    return close.diff(window)


def compute_rate_of_change(close: pd.Series, window: int = 10) -> pd.Series:
    """Compute Rate of Change"""
    return close.pct_change(window) * 100


def compute_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """Compute On-Balance Volume"""
    obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
    return obv


def compute_vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, 
                 group_by_date: bool = True) -> pd.Series:
    """
    Compute Volume Weighted Average Price (VWAP).
    
    Args:
        high: High prices
        low: Low prices
        close: Close prices
        volume: Volume
        group_by_date: If True, resets VWAP at start of each trading day
    
    Returns:
        VWAP series
    """
    typical_price = (high + low + close) / 3
    price_volume = typical_price * volume
    
    if group_by_date and isinstance(high.index, pd.DatetimeIndex):
        # Reset VWAP at start of each day
        vwap = price_volume.groupby(high.index.date).cumsum() / volume.groupby(high.index.date).cumsum()
    else:
        # Cumulative VWAP
        vwap = price_volume.cumsum() / volume.cumsum()
    
    return vwap


def compute_opening_range(high: pd.Series, low: pd.Series, close: pd.Series, 
                        volume: pd.Series, minutes: int = 15) -> pd.DataFrame:
    """
    Compute opening range breakout features.
    
    Args:
        high: High prices
        low: Low prices
        close: Close prices
        volume: Volume
        minutes: Opening range duration in minutes (default: 15)
    
    Returns:
        DataFrame with opening range features
    """
    if not isinstance(high.index, pd.DatetimeIndex):
        # If not datetime index, return empty features
        return pd.DataFrame({
            'or_high': pd.Series(index=high.index),
            'or_low': pd.Series(index=high.index),
            'or_range': pd.Series(index=high.index),
            'or_breakout_up': pd.Series(index=high.index),
            'or_breakout_down': pd.Series(index=high.index),
            'or_volume': pd.Series(index=high.index)
        })
    
    # Group by date
    daily_groups = high.groupby(high.index.date)
    
    or_high = pd.Series(index=high.index, dtype=float)
    or_low = pd.Series(index=high.index, dtype=float)
    or_range = pd.Series(index=high.index, dtype=float)
    or_breakout_up = pd.Series(index=high.index, dtype=bool)
    or_breakout_down = pd.Series(index=high.index, dtype=bool)
    or_volume = pd.Series(index=high.index, dtype=float)
    
    for date, group_indices in daily_groups.groups.items():
        day_data = high.loc[group_indices]
        
        # Get first N minutes (assuming intraday data)
        # For daily data, use first bar
        if len(day_data) > 0:
            # Simplified: use first bar as opening range
            or_start_idx = day_data.index[0]
            or_end_idx = day_data.index[min(minutes, len(day_data) - 1)]
            
            or_high.loc[or_start_idx:or_end_idx] = high.loc[or_start_idx:or_end_idx].max()
            or_low.loc[or_start_idx:or_end_idx] = low.loc[or_start_idx:or_end_idx].min()
            or_range.loc[or_start_idx:or_end_idx] = or_high.loc[or_start_idx] - or_low.loc[or_start_idx]
            or_volume.loc[or_start_idx:or_end_idx] = volume.loc[or_start_idx:or_end_idx].sum()
            
            # Check for breakouts after opening range
            for idx in day_data.index:
                if idx > or_end_idx:
                    or_breakout_up.loc[idx] = high.loc[idx] > or_high.loc[or_start_idx]
                    or_breakout_down.loc[idx] = low.loc[idx] < or_low.loc[or_start_idx]
    
    return pd.DataFrame({
        'or_high': or_high,
        'or_low': or_low,
        'or_range': or_range,
        'or_breakout_up': or_breakout_up.astype(float),
        'or_breakout_down': or_breakout_down.astype(float),
        'or_volume': or_volume
    })


def compute_volume_profile(high: pd.Series, low: pd.Series, close: pd.Series, 
                          volume: pd.Series, bins: int = 20) -> pd.DataFrame:
    """
    Compute volume profile features (simplified version).
    
    Args:
        high: High prices
        low: Low prices
        close: Close prices
        volume: Volume
        bins: Number of price bins for volume profile
    
    Returns:
        DataFrame with volume profile features
    """
    # Price range
    price_range = high.max() - low.min()
    bin_size = price_range / bins if bins > 0 else price_range
    
    # Volume-weighted price
    typical_price = (high + low + close) / 3
    vwap = (typical_price * volume).sum() / volume.sum() if volume.sum() > 0 else close.mean()
    
    # Price position relative to range
    price_position = (close - low.min()) / price_range if price_range > 0 else 0.5
    
    # Volume concentration (simplified)
    # Count how much volume is near current price
    price_deviation = abs(typical_price - close) / close
    volume_near_price = volume[price_deviation < 0.01].sum() / volume.sum() if volume.sum() > 0 else 0
    
    return pd.DataFrame({
        'vp_vwap': vwap,
        'vp_price_position': price_position,
        'vp_volume_concentration': volume_near_price,
        'vp_range': price_range,
        'vp_bin_size': bin_size
    }, index=high.index)


def compute_intraday_momentum(close: pd.Series, volume: pd.Series, 
                             window: int = 5) -> pd.Series:
    """
    Compute intraday momentum (price change weighted by volume).
    
    Args:
        close: Close prices
        volume: Volume
        window: Lookback window
    
    Returns:
        Intraday momentum series
    """
    price_change = close.diff(window)
    volume_weighted_change = (price_change * volume.rolling(window).mean()) / volume.rolling(window).mean()
    return volume_weighted_change.fillna(0)


def compute_ichimoku(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    tenkan_period: int = 9,
    kijun_period: int = 26,
    senkou_b_period: int = 52
) -> pd.DataFrame:
    """Compute Ichimoku Cloud components"""
    # Tenkan-sen (Conversion Line)
    tenkan_sen = (high.rolling(window=tenkan_period).max() + low.rolling(window=tenkan_period).min()) / 2
    
    # Kijun-sen (Base Line)
    kijun_sen = (high.rolling(window=kijun_period).max() + low.rolling(window=kijun_period).min()) / 2
    
    # Senkou Span A (Leading Span A)
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun_period)
    
    # Senkou Span B (Leading Span B)
    senkou_span_b = ((high.rolling(window=senkou_b_period).max() + low.rolling(window=senkou_b_period).min()) / 2).shift(kijun_period)
    
    # Chikou Span (Lagging Span)
    chikou_span = close.shift(-kijun_period)
    
    return pd.DataFrame({
        'ichimoku_tenkan': tenkan_sen,
        'ichimoku_kijun': kijun_sen,
        'ichimoku_senkou_a': senkou_span_a,
        'ichimoku_senkou_b': senkou_span_b,
        'ichimoku_chikou': chikou_span,
        'ichimoku_cloud_top': pd.concat([senkou_span_a, senkou_span_b], axis=1).max(axis=1),
        'ichimoku_cloud_bottom': pd.concat([senkou_span_a, senkou_span_b], axis=1).min(axis=1)
    })


def make_advanced_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create advanced features for ELITE AI system
    
    Args:
        df: OHLCV dataframe with columns: open/high/low/close/volume
    
    Returns:
        Dataframe with advanced features added
    """
    out = df.copy()
    
    # Basic features (from original make_features)
    out["ret_1"] = out["close"].pct_change(1)
    out["ret_5"] = out["close"].pct_change(5)
    out["ret_10"] = out["close"].pct_change(10)
    out["ret_20"] = out["close"].pct_change(20)
    out["vol_10"] = out["ret_1"].rolling(10).std()
    out["vol_20"] = out["ret_1"].rolling(20).std()
    
    # Moving averages
    out["sma_10"] = out["close"].rolling(10).mean()
    out["sma_20"] = out["close"].rolling(20).mean()
    out["sma_50"] = out["close"].rolling(50).mean()
    out["sma_200"] = out["close"].rolling(200).mean()
    out["ema_12"] = out["close"].ewm(span=12, adjust=False).mean()
    out["ema_20"] = out["close"].ewm(span=20, adjust=False).mean()
    out["ema_26"] = out["close"].ewm(span=26, adjust=False).mean()
    out["ema_50"] = out["close"].ewm(span=50, adjust=False).mean()
    
    # Price position relative to MAs
    out["price_sma10_ratio"] = out["close"] / out["sma_10"]
    out["price_sma50_ratio"] = out["close"] / out["sma_50"]
    out["sma10_sma50_ratio"] = out["sma_10"] / out["sma_50"]
    
    # RSI
    from src.research.features import compute_rsi
    out["rsi_14"] = compute_rsi(out["close"], window=14)
    out["rsi_7"] = compute_rsi(out["close"], window=7)
    out["rsi_21"] = compute_rsi(out["close"], window=21)
    
    # MACD
    from src.research.features import compute_macd
    macd = compute_macd(out["close"])
    out = out.join(macd)
    
    # Bollinger Bands
    bb = compute_bollinger_bands(out["close"])
    out = out.join(bb)
    
    # ATR
    out["atr_14"] = compute_atr(out["high"], out["low"], out["close"])
    out["atr_pct"] = out["atr_14"] / out["close"] * 100
    
    # ADX
    out["adx_14"] = compute_adx(out["high"], out["low"], out["close"])
    
    # Stochastic
    stoch = compute_stochastic(out["high"], out["low"], out["close"])
    out = out.join(stoch)
    
    # Williams %R
    out["williams_r"] = compute_williams_r(out["high"], out["low"], out["close"])
    
    # CCI
    out["cci_20"] = compute_cci(out["high"], out["low"], out["close"])
    
    # Momentum
    out["momentum_10"] = compute_momentum(out["close"], window=10)
    out["momentum_20"] = compute_momentum(out["close"], window=20)
    
    # Rate of Change
    out["roc_10"] = compute_rate_of_change(out["close"], window=10)
    out["roc_20"] = compute_rate_of_change(out["close"], window=20)
    
    # Volume features
    out["vol_chg_1"] = out["volume"].pct_change(1)
    out["vol_chg_5"] = out["volume"].pct_change(5)
    out["vol_sma_20"] = out["volume"].rolling(20).mean()
    out["vol_ratio"] = out["volume"] / out["vol_sma_20"]
    
    # On-Balance Volume
    out["obv"] = compute_obv(out["close"], out["volume"])
    out["obv_ema"] = out["obv"].ewm(span=20, adjust=False).mean()
    
    # Price patterns
    out["high_low_ratio"] = out["high"] / out["low"]
    out["close_position"] = (out["close"] - out["low"]) / (out["high"] - out["low"])
    
    # Ichimoku Cloud (if enough data)
    if len(out) >= 52:
        ichimoku = compute_ichimoku(out["high"], out["low"], out["close"])
        out = out.join(ichimoku)
    
    # Intraday-specific features (VWAP, Opening Range, Volume Profile)
    # Check if this is intraday data (has time component in index)
    is_intraday = isinstance(out.index, pd.DatetimeIndex) and any(
        pd.Timestamp(idx).time() != pd.Timestamp(idx).normalize().time() 
        for idx in out.index[:min(10, len(out))]
    )
    
    if is_intraday or len(out) > 100:  # Also compute for daily data as reference
        # VWAP
        vwap = compute_vwap(out["high"], out["low"], out["close"], out["volume"], group_by_date=is_intraday)
        out["vwap"] = vwap
        out["price_vwap_ratio"] = out["close"] / vwap.replace(0, np.nan)
        out["price_vwap_diff"] = out["close"] - vwap
        
        # Opening Range
        or_features = compute_opening_range(out["high"], out["low"], out["close"], out["volume"])
        out = out.join(or_features)
        
        # Volume Profile
        vp_features = compute_volume_profile(out["high"], out["low"], out["close"], out["volume"])
        out = out.join(vp_features)
        
        # Intraday Momentum
        out["intraday_momentum"] = compute_intraday_momentum(out["close"], out["volume"])
    
    return out


def get_advanced_feature_columns() -> List[str]:
    """Get list of advanced feature column names"""
    return [
        # Returns
        'ret_1', 'ret_5', 'ret_10', 'ret_20',
        'vol_10', 'vol_20',
        
        # Moving Averages
        'sma_10', 'sma_20', 'sma_50', 'sma_200',
        'ema_12', 'ema_20', 'ema_26', 'ema_50',
        'price_sma10_ratio', 'price_sma50_ratio', 'sma10_sma50_ratio',
        
        # RSI
        'rsi_7', 'rsi_14', 'rsi_21',
        
        # MACD
        'macd', 'macd_signal', 'macd_hist',
        
        # Bollinger Bands
        'bb_upper', 'bb_middle', 'bb_lower', 'bb_width', 'bb_position',
        
        # Volatility
        'atr_14', 'atr_pct', 'adx_14',
        
        # Oscillators
        'stoch_k', 'stoch_d', 'williams_r', 'cci_20',
        
        # Momentum
        'momentum_10', 'momentum_20', 'roc_10', 'roc_20',
        
        # Volume
        'vol_chg_1', 'vol_chg_5', 'vol_sma_20', 'vol_ratio',
        'obv', 'obv_ema',
        
        # Price patterns
        'high_low_ratio', 'close_position',
        
        # Ichimoku (if available)
        'ichimoku_tenkan', 'ichimoku_kijun',
        'ichimoku_senkou_a', 'ichimoku_senkou_b',
        'ichimoku_cloud_top', 'ichimoku_cloud_bottom',
        
        # Intraday features (if available)
        'vwap', 'price_vwap_ratio', 'price_vwap_diff',
        'or_high', 'or_low', 'or_range', 'or_breakout_up', 'or_breakout_down', 'or_volume',
        'vp_vwap', 'vp_price_position', 'vp_volume_concentration', 'vp_range', 'vp_bin_size',
        'intraday_momentum'
    ]
