"""
Adaptive Feature Engineering
Market regime detection and enhanced features for adaptive trading
"""
import numpy as np
import pandas as pd
from typing import Dict, Tuple
from src.web.ai_models.advanced_features import compute_atr, compute_adx


def detect_market_regime(
    df: pd.DataFrame,
    adx_window: int = 14,
    atr_window: int = 14,
    lookback: int = 20
) -> Dict[str, float]:
    """
    Detect current market regime using multiple indicators
    
    Returns:
        Dict with:
        - regime_type: 'STRONG_TREND', 'WEAK_TREND', 'RANGING', 'HIGH_VOLATILITY'
        - trend_strength: 0-100 (ADX-based)
        - volatility_regime: 0-100 (ATR percentile)
        - market_phase: 'BULL', 'BEAR', 'NEUTRAL'
    """
    if len(df) < max(adx_window, atr_window, lookback):
        return {
            'regime_type': 'UNKNOWN',
            'trend_strength': 0.0,
            'volatility_regime': 50.0,
            'market_phase': 'NEUTRAL'
        }
    
    # Calculate ADX (trend strength)
    adx = compute_adx(df['high'], df['low'], df['close'], window=adx_window)
    current_adx = adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 25.0
    
    # Calculate ATR (volatility)
    atr = compute_atr(df['high'], df['low'], df['close'], window=atr_window)
    current_atr = atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else df['close'].iloc[-1] * 0.02
    atr_pct = (current_atr / df['close'].iloc[-1]) * 100 if df['close'].iloc[-1] > 0 else 2.0
    
    # Calculate ATR percentile (volatility regime)
    atr_history = atr.tail(lookback * 2)
    atr_percentile = (atr_history < current_atr).sum() / len(atr_history) * 100 if len(atr_history) > 0 else 50.0
    
    # Determine market phase (BULL/BEAR/NEUTRAL)
    sma_20 = df['close'].rolling(20).mean().iloc[-1]
    sma_50 = df['close'].rolling(50).mean().iloc[-1] if len(df) >= 50 else sma_20
    current_price = df['close'].iloc[-1]
    
    if current_price > sma_20 > sma_50:
        market_phase = 'BULL'
    elif current_price < sma_20 < sma_50:
        market_phase = 'BEAR'
    else:
        market_phase = 'NEUTRAL'
    
    # Classify regime
    if current_adx > 40 and atr_percentile < 70:
        regime_type = 'STRONG_TREND'
    elif current_adx > 25:
        regime_type = 'WEAK_TREND'
    elif atr_percentile > 80:
        regime_type = 'HIGH_VOLATILITY'
    else:
        regime_type = 'RANGING'
    
    return {
        'regime_type': regime_type,
        'trend_strength': float(current_adx),
        'volatility_regime': float(atr_percentile),
        'volatility_pct': float(atr_pct),
        'market_phase': market_phase,
        'adx': float(current_adx),
        'atr': float(current_atr),
        'atr_percentile': float(atr_percentile)
    }


def calculate_support_resistance(
    df: pd.DataFrame,
    lookback: int = 20
) -> Dict[str, float]:
    """
    Calculate support and resistance levels
    
    Returns:
        Dict with support, resistance, and pivot levels
    """
    if len(df) < lookback:
        current_price = df['close'].iloc[-1]
        return {
            'support': current_price * 0.95,
            'resistance': current_price * 1.05,
            'pivot': current_price
        }
    
    recent_data = df.tail(lookback)
    
    # Support: lowest low in lookback period
    support = float(recent_data['low'].min())
    
    # Resistance: highest high in lookback period
    resistance = float(recent_data['high'].max())
    
    # Pivot: typical price (high + low + close) / 3
    pivot = float((recent_data['high'].iloc[-1] + recent_data['low'].iloc[-1] + recent_data['close'].iloc[-1]) / 3)
    
    return {
        'support': support,
        'resistance': resistance,
        'pivot': pivot,
        'support_distance_pct': ((df['close'].iloc[-1] - support) / support * 100) if support > 0 else 0,
        'resistance_distance_pct': ((resistance - df['close'].iloc[-1]) / df['close'].iloc[-1] * 100) if df['close'].iloc[-1] > 0 else 0
    }


def calculate_volume_profile(df: pd.DataFrame, lookback: int = 20) -> Dict[str, float]:
    """
    Analyze volume profile for confirmation
    
    Returns:
        Dict with volume metrics
    """
    if len(df) < lookback:
        return {
            'volume_ratio': 1.0,
            'volume_trend': 'NEUTRAL',
            'unusual_volume': False
        }
    
    recent_volume = df['volume'].tail(lookback)
    avg_volume = recent_volume.mean()
    current_volume = df['volume'].iloc[-1]
    
    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
    
    # Volume trend (increasing/decreasing)
    volume_slope = np.polyfit(range(lookback), recent_volume.values, 1)[0]
    
    if volume_slope > 0:
        volume_trend = 'INCREASING'
    elif volume_slope < 0:
        volume_trend = 'DECREASING'
    else:
        volume_trend = 'NEUTRAL'
    
    # Unusual volume: > 1.5x average
    unusual_volume = volume_ratio > 1.5
    
    return {
        'volume_ratio': float(volume_ratio),
        'volume_trend': volume_trend,
        'unusual_volume': unusual_volume,
        'avg_volume': float(avg_volume),
        'current_volume': float(current_volume)
    }


def make_adaptive_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """
    Create adaptive features including market regime detection
    
    Args:
        df: OHLCV dataframe
        
    Returns:
        Tuple of (enhanced_df, regime_info)
    """
    # Start with advanced features
    from src.web.ai_models.advanced_features import make_advanced_features
    enhanced_df = make_advanced_features(df.copy())
    
    # Detect market regime
    regime_info = detect_market_regime(enhanced_df)
    
    # Calculate support/resistance
    sr_levels = calculate_support_resistance(enhanced_df)
    
    # Calculate volume profile
    volume_info = calculate_volume_profile(enhanced_df)
    
    # Add regime features to dataframe
    enhanced_df['regime_trend_strength'] = regime_info['trend_strength']
    enhanced_df['regime_volatility_pct'] = regime_info['volatility_pct']
    enhanced_df['volume_ratio'] = volume_info['volume_ratio']
    
    # Combine all regime info
    full_regime_info = {
        **regime_info,
        **sr_levels,
        **volume_info
    }
    
    return enhanced_df, full_regime_info
