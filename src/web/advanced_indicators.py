"""
Advanced Technical Indicators
Phase 2.2: Advanced Features - Candlestick patterns, support/resistance, volume-weighted indicators, multi-timeframe
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class CandlestickPatterns:
    """
    Detects advanced candlestick patterns.
    """
    
    @staticmethod
    def detect_patterns(ohlcv_df: pd.DataFrame) -> List[Dict[str, any]]:
        """
        Detect candlestick patterns in OHLCV data.
        
        Args:
            ohlcv_df: DataFrame with OHLCV data
        
        Returns:
            List of detected patterns
        """
        if ohlcv_df.empty or len(ohlcv_df) < 3:
            return []
        
        patterns = []
        df = ohlcv_df.copy()
        
        # Ensure we have required columns
        required_cols = ['open', 'high', 'low', 'close']
        if not all(col in df.columns for col in required_cols):
            return []
        
        # Get last few candles for pattern detection
        recent = df.tail(5)
        
        # Hammer pattern
        if len(recent) >= 1:
            last = recent.iloc[-1]
            body = abs(last['close'] - last['open'])
            lower_shadow = min(last['open'], last['close']) - last['low']
            upper_shadow = last['high'] - max(last['open'], last['close'])
            
            if lower_shadow > body * 2 and upper_shadow < body * 0.5:
                patterns.append({
                    'pattern': 'HAMMER',
                    'type': 'BULLISH',
                    'confidence': 0.7,
                    'candle_index': len(df) - 1,
                })
        
        # Doji pattern
        if len(recent) >= 1:
            last = recent.iloc[-1]
            body = abs(last['close'] - last['open'])
            total_range = last['high'] - last['low']
            
            if body < total_range * 0.1:  # Very small body
                patterns.append({
                    'pattern': 'DOJI',
                    'type': 'NEUTRAL',
                    'confidence': 0.6,
                    'candle_index': len(df) - 1,
                })
        
        # Engulfing pattern
        if len(recent) >= 2:
            prev = recent.iloc[-2]
            curr = recent.iloc[-1]
            
            # Bullish engulfing
            if (prev['close'] < prev['open'] and  # Previous was bearish
                curr['close'] > curr['open'] and  # Current is bullish
                curr['open'] < prev['close'] and  # Current opens below prev close
                curr['close'] > prev['open']):    # Current closes above prev open
                patterns.append({
                    'pattern': 'BULLISH_ENGULFING',
                    'type': 'BULLISH',
                    'confidence': 0.75,
                    'candle_index': len(df) - 1,
                })
            
            # Bearish engulfing
            if (prev['close'] > prev['open'] and  # Previous was bullish
                curr['close'] < curr['open'] and  # Current is bearish
                curr['open'] > prev['close'] and  # Current opens above prev close
                curr['close'] < prev['open']):    # Current closes below prev open
                patterns.append({
                    'pattern': 'BEARISH_ENGULFING',
                    'type': 'BEARISH',
                    'confidence': 0.75,
                    'candle_index': len(df) - 1,
                })
        
        # Three white soldiers / three black crows
        if len(recent) >= 3:
            candles = recent.tail(3)
            
            # Three white soldiers (bullish)
            if all(c['close'] > c['open'] for _, c in candles.iterrows()):
                if (candles.iloc[0]['close'] < candles.iloc[1]['close'] < candles.iloc[2]['close'] and
                    candles.iloc[0]['open'] < candles.iloc[1]['open'] < candles.iloc[2]['open']):
                    patterns.append({
                        'pattern': 'THREE_WHITE_SOLDIERS',
                        'type': 'BULLISH',
                        'confidence': 0.8,
                        'candle_index': len(df) - 1,
                    })
            
            # Three black crows (bearish)
            if all(c['close'] < c['open'] for _, c in candles.iterrows()):
                if (candles.iloc[0]['close'] > candles.iloc[1]['close'] > candles.iloc[2]['close'] and
                    candles.iloc[0]['open'] > candles.iloc[1]['open'] > candles.iloc[2]['open']):
                    patterns.append({
                        'pattern': 'THREE_BLACK_CROWS',
                        'type': 'BEARISH',
                        'confidence': 0.8,
                        'candle_index': len(df) - 1,
                    })
        
        return patterns


class SupportResistanceLevels:
    """
    Identifies support and resistance levels.
    """
    
    @staticmethod
    def find_levels(ohlcv_df: pd.DataFrame, lookback: int = 60, min_touches: int = 2) -> Dict[str, List[float]]:
        """
        Find support and resistance levels using pivot points.
        
        Args:
            ohlcv_df: DataFrame with OHLCV data
            lookback: Number of periods to look back
            min_touches: Minimum number of touches for a level to be valid
        
        Returns:
            Dictionary with support and resistance levels
        """
        if ohlcv_df.empty or len(ohlcv_df) < lookback:
            return {'support_levels': [], 'resistance_levels': []}
        
        df = ohlcv_df.tail(lookback).copy()
        
        # Find pivot highs (resistance) and pivot lows (support)
        pivot_window = 5
        
        pivot_highs = []
        pivot_lows = []
        
        for i in range(pivot_window, len(df) - pivot_window):
            high = df.iloc[i]['high']
            low = df.iloc[i]['low']
            
            # Check if it's a pivot high
            if all(df.iloc[i]['high'] >= df.iloc[j]['high'] 
                   for j in range(i - pivot_window, i + pivot_window + 1)):
                pivot_highs.append(high)
            
            # Check if it's a pivot low
            if all(df.iloc[i]['low'] <= df.iloc[j]['low'] 
                   for j in range(i - pivot_window, i + pivot_window + 1)):
                pivot_lows.append(low)
        
        # Cluster similar levels together
        def cluster_levels(levels: List[float], tolerance: float = 0.01) -> List[float]:
            if not levels:
                return []
            
            levels_sorted = sorted(levels)
            clusters = []
            current_cluster = [levels_sorted[0]]
            
            for level in levels_sorted[1:]:
                if abs(level - current_cluster[-1]) / current_cluster[-1] <= tolerance:
                    current_cluster.append(level)
                else:
                    if len(current_cluster) >= min_touches:
                        clusters.append(np.mean(current_cluster))
                    current_cluster = [level]
            
            if len(current_cluster) >= min_touches:
                clusters.append(np.mean(current_cluster))
            
            return sorted(clusters)
        
        current_price = float(df.iloc[-1]['close'])
        tolerance_pct = 0.02  # 2% tolerance
        
        resistance_levels = cluster_levels(pivot_highs, tolerance_pct)
        support_levels = cluster_levels(pivot_lows, tolerance_pct)
        
        # Filter levels near current price (within 20%)
        resistance_levels = [r for r in resistance_levels if r > current_price * 0.8]
        support_levels = [s for s in support_levels if s < current_price * 1.2]
        
        # Sort and get top 5
        resistance_levels = sorted(resistance_levels)[:5]
        support_levels = sorted(support_levels, reverse=True)[:5]
        
        return {
            'support_levels': [round(level, 2) for level in support_levels],
            'resistance_levels': [round(level, 2) for level in resistance_levels],
            'nearest_support': round(support_levels[0], 2) if support_levels else None,
            'nearest_resistance': round(resistance_levels[0], 2) if resistance_levels else None,
            'current_price': current_price,
        }


class VolumeWeightedIndicators:
    """
    Volume-weighted technical indicators.
    """
    
    @staticmethod
    def calculate_vwap(ohlcv_df: pd.DataFrame, period: int = 20) -> pd.Series:
        """
        Calculate Volume Weighted Average Price (VWAP).
        
        Args:
            ohlcv_df: DataFrame with OHLCV data
            period: Period for VWAP calculation
        
        Returns:
            VWAP series
        """
        if ohlcv_df.empty or 'volume' not in ohlcv_df.columns:
            return pd.Series()
        
        df = ohlcv_df.tail(period).copy()
        
        # Typical price
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        
        # VWAP = sum(typical_price * volume) / sum(volume)
        vwap = (df['typical_price'] * df['volume']).sum() / df['volume'].sum()
        
        return pd.Series([vwap] * len(df), index=df.index)
    
    @staticmethod
    def calculate_volume_profile_indicators(ohlcv_df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate volume-based indicators.
        
        Args:
            ohlcv_df: DataFrame with OHLCV data
        
        Returns:
            Volume profile indicators
        """
        if ohlcv_df.empty or len(ohlcv_df) < 20:
            return {}
        
        df = ohlcv_df.tail(60).copy()
        
        # Volume moving averages
        volume_ma_20 = df['volume'].tail(20).mean()
        volume_ma_60 = df['volume'].mean()
        
        # Current volume vs average
        current_volume = float(df.iloc[-1]['volume'])
        volume_ratio = current_volume / volume_ma_20 if volume_ma_20 > 0 else 1
        
        # Volume trend (increasing/decreasing)
        recent_volumes = df['volume'].tail(10).values
        volume_trend = 'INCREASING' if recent_volumes[-1] > recent_volumes[0] else 'DECREASING'
        
        # Price-volume divergence
        price_change = (df.iloc[-1]['close'] - df.iloc[-10]['close']) / df.iloc[-10]['close']
        volume_change = (recent_volumes[-1] - recent_volumes[0]) / recent_volumes[0] if recent_volumes[0] > 0 else 0
        
        # Bullish: price up + volume up, Bearish: price down + volume up
        divergence = 'NONE'
        if price_change > 0 and volume_change > 0:
            divergence = 'BULLISH_CONFIRMATION'
        elif price_change < 0 and volume_change > 0:
            divergence = 'BEARISH_CONFIRMATION'
        elif price_change > 0 and volume_change < 0:
            divergence = 'BULLISH_DIVERGENCE'  # Price up but volume down
        elif price_change < 0 and volume_change < 0:
            divergence = 'BEARISH_DIVERGENCE'  # Price down but volume down
        
        return {
            'volume_ma_20': round(volume_ma_20, 2),
            'volume_ma_60': round(volume_ma_60, 2),
            'current_volume': round(current_volume, 2),
            'volume_ratio': round(volume_ratio, 2),
            'volume_trend': volume_trend,
            'high_volume': volume_ratio > 1.5,
            'low_volume': volume_ratio < 0.5,
            'price_change_pct': round(price_change * 100, 2),
            'volume_change_pct': round(volume_change * 100, 2),
            'volume_divergence': divergence,
        }


class MultiTimeframeAnalyzer:
    """
    Multi-timeframe analysis for confluence.
    """
    
    @staticmethod
    def analyze_timeframes(ohlcv_data: Dict[str, pd.DataFrame], 
                          predictions: Dict[str, float]) -> Dict[str, any]:
        """
        Analyze multiple timeframes for confluence.
        
        Args:
            ohlcv_data: Dictionary of timeframe -> DataFrame
            predictions: Dictionary of timeframe -> prediction probability
        
        Returns:
            Multi-timeframe analysis
        """
        if not ohlcv_data or not predictions:
            return {}
        
        # Count bullish/bearish signals across timeframes
        bullish_count = sum(1 for p in predictions.values() if p > 0.55)
        bearish_count = sum(1 for p in predictions.values() if p < 0.45)
        neutral_count = len(predictions) - bullish_count - bearish_count
        
        # Calculate average prediction
        avg_prediction = np.mean(list(predictions.values())) if predictions else 0.5
        
        # Determine overall bias
        if bullish_count > bearish_count:
            overall_bias = 'BULLISH'
            confluence_score = bullish_count / len(predictions) if predictions else 0
        elif bearish_count > bullish_count:
            overall_bias = 'BEARISH'
            confluence_score = bearish_count / len(predictions) if predictions else 0
        else:
            overall_bias = 'NEUTRAL'
            confluence_score = 0.5
        
        # Strong confluence if >70% of timeframes agree
        strong_confluence = confluence_score >= 0.7
        
        return {
            'timeframes_analyzed': list(predictions.keys()),
            'bullish_timeframes': bullish_count,
            'bearish_timeframes': bearish_count,
            'neutral_timeframes': neutral_count,
            'average_prediction': round(avg_prediction, 3),
            'overall_bias': overall_bias,
            'confluence_score': round(confluence_score, 3),
            'strong_confluence': strong_confluence,
            'timeframe_predictions': predictions,
        }


class AdvancedIndicatorsManager:
    """
    Manages all advanced technical indicators.
    """
    
    def __init__(self):
        self.candlestick_patterns = CandlestickPatterns()
        self.support_resistance = SupportResistanceLevels()
        self.volume_indicators = VolumeWeightedIndicators()
        self.multi_timeframe = MultiTimeframeAnalyzer()
    
    def get_all_indicators(self, ohlcv_df: pd.DataFrame, 
                          multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None,
                          multi_timeframe_predictions: Optional[Dict[str, float]] = None) -> Dict[str, any]:
        """
        Get all advanced indicators.
        
        Args:
            ohlcv_df: Main OHLCV DataFrame
            multi_timeframe_data: Optional multi-timeframe OHLCV data
            multi_timeframe_predictions: Optional multi-timeframe predictions
        
        Returns:
            All advanced indicators
        """
        indicators = {
            'timestamp': datetime.now().isoformat(),
        }
        
        # Candlestick patterns
        patterns = self.candlestick_patterns.detect_patterns(ohlcv_df)
        indicators['candlestick_patterns'] = patterns
        if patterns:
            latest_pattern = patterns[-1]
            indicators['latest_pattern'] = latest_pattern['pattern']
            indicators['latest_pattern_type'] = latest_pattern['type']
            indicators['latest_pattern_confidence'] = latest_pattern['confidence']
        
        # Support and resistance levels
        sr_levels = self.support_resistance.find_levels(ohlcv_df)
        indicators.update(sr_levels)
        
        # Volume-weighted indicators
        volume_indicators = self.volume_indicators.calculate_volume_profile_indicators(ohlcv_df)
        indicators.update({f'volume_{k}': v for k, v in volume_indicators.items()})
        
        # VWAP
        vwap_series = self.volume_indicators.calculate_vwap(ohlcv_df)
        if not vwap_series.empty:
            indicators['vwap'] = round(float(vwap_series.iloc[-1]), 2)
            current_price = float(ohlcv_df.iloc[-1]['close'])
            indicators['price_vs_vwap'] = round((current_price - indicators['vwap']) / indicators['vwap'] * 100, 2)
            indicators['above_vwap'] = current_price > indicators['vwap']
        
        # Multi-timeframe analysis
        if multi_timeframe_data and multi_timeframe_predictions:
            mtf_analysis = self.multi_timeframe.analyze_timeframes(
                multi_timeframe_data,
                multi_timeframe_predictions
            )
            indicators.update({f'mtf_{k}': v for k, v in mtf_analysis.items()})
        
        return indicators


# Global instance
_advanced_indicators_manager: Optional[AdvancedIndicatorsManager] = None

def get_advanced_indicators_manager() -> AdvancedIndicatorsManager:
    """Get global AdvancedIndicatorsManager instance"""
    global _advanced_indicators_manager
    if _advanced_indicators_manager is None:
        _advanced_indicators_manager = AdvancedIndicatorsManager()
    return _advanced_indicators_manager
