"""
Multi-Timeframe Analyzer
Analyze multiple timeframes simultaneously for better signals
"""
import logging
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MultiTimeframeAnalyzer:
    """Analyze stock across multiple timeframes"""
    
    def __init__(self):
        self.timeframes = ['1m', '5m', '15m', '1h', '1d']  # Minutes, hours, days
        self.timeframe_weights = {
            '1m': 0.1,   # Short-term noise
            '5m': 0.15,  # Short-term trend
            '15m': 0.25, # Medium-term trend
            '1h': 0.3,   # Medium-term trend
            '1d': 0.2    # Long-term trend
        }
    
    def analyze_timeframes(
        self,
        ticker: str,
        ohlcv_data: Dict[str, pd.DataFrame],
        predictions: Dict[str, float]
    ) -> Dict:
        """
        Analyze across multiple timeframes
        
        Args:
            ticker: Stock ticker
            ohlcv_data: Dictionary of timeframe -> OHLCV dataframe
            predictions: Dictionary of timeframe -> prediction probability
        
        Returns:
            Multi-timeframe analysis result
        """
        analysis = {
            'ticker': ticker,
            'timeframe_signals': {},
            'consensus_signal': None,
            'consensus_probability': 0.5,
            'trend_alignment': None,
            'confidence': 0.0,
            'timestamp': datetime.now().isoformat()
        }
        
        if not predictions:
            return analysis
        
        # Analyze each timeframe
        timeframe_signals = {}
        for tf, prob in predictions.items():
            if prob >= 0.6:
                signal = 'STRONG_BUY'
            elif prob >= 0.55:
                signal = 'BUY'
            elif prob >= 0.45:
                signal = 'NEUTRAL'
            elif prob >= 0.4:
                signal = 'SELL'
            else:
                signal = 'STRONG_SELL'
            
            timeframe_signals[tf] = {
                'signal': signal,
                'probability': prob,
                'confidence': abs(prob - 0.5) * 2  # 0-1 scale
            }
        
        analysis['timeframe_signals'] = timeframe_signals
        
        # Calculate weighted consensus
        consensus_prob = self._calculate_weighted_consensus(predictions)
        analysis['consensus_probability'] = consensus_prob
        
        # Determine consensus signal
        if consensus_prob >= 0.6:
            analysis['consensus_signal'] = 'BUY'
        elif consensus_prob <= 0.4:
            analysis['consensus_signal'] = 'SELL'
        else:
            analysis['consensus_signal'] = 'HOLD'
        
        # Check trend alignment
        trend_alignment = self._check_trend_alignment(timeframe_signals)
        analysis['trend_alignment'] = trend_alignment
        
        # Calculate overall confidence
        confidences = [sig['confidence'] for sig in timeframe_signals.values()]
        if confidences:
            analysis['confidence'] = np.mean(confidences) * trend_alignment['alignment_score']
        
        return analysis
    
    def _calculate_weighted_consensus(self, predictions: Dict[str, float]) -> float:
        """Calculate weighted average of predictions"""
        total_weight = 0
        weighted_sum = 0
        
        for tf, prob in predictions.items():
            weight = self.timeframe_weights.get(tf, 0.2)  # Default weight
            weighted_sum += prob * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.5
    
    def _check_trend_alignment(self, timeframe_signals: Dict) -> Dict:
        """Check if trends align across timeframes"""
        buy_count = 0
        sell_count = 0
        neutral_count = 0
        
        for tf_signal in timeframe_signals.values():
            signal = tf_signal['signal']
            if 'BUY' in signal:
                buy_count += 1
            elif 'SELL' in signal:
                sell_count += 1
            else:
                neutral_count += 1
        
        total = len(timeframe_signals)
        if total == 0:
            return {
                'aligned': False,
                'alignment_score': 0.0,
                'buy_ratio': 0.0,
                'sell_ratio': 0.0
            }
        
        buy_ratio = buy_count / total
        sell_ratio = sell_count / total
        
        # Alignment score: higher when one direction dominates
        alignment_score = max(buy_ratio, sell_ratio)
        
        # Consider aligned if > 60% agree
        aligned = alignment_score >= 0.6
        
        return {
            'aligned': aligned,
            'alignment_score': alignment_score,
            'buy_ratio': buy_ratio,
            'sell_ratio': sell_ratio,
            'buy_count': buy_count,
            'sell_count': sell_count,
            'neutral_count': neutral_count
        }
    
    def get_timeframe_priority(self) -> List[str]:
        """Get timeframes in priority order (most important first)"""
        return sorted(
            self.timeframes,
            key=lambda tf: self.timeframe_weights.get(tf, 0),
            reverse=True
        )
    
    def analyze_price_action(
        self,
        ohlcv_data: Dict[str, pd.DataFrame]
    ) -> Dict:
        """
        Analyze price action across timeframes
        
        Args:
            ohlcv_data: Dictionary of timeframe -> OHLCV dataframe
        
        Returns:
            Price action analysis
        """
        analysis = {
            'trend_strength': {},
            'volatility': {},
            'support_resistance': {},
            'breakouts': {}
        }
        
        for tf, df in ohlcv_data.items():
            if len(df) < 20:
                continue
            
            close = df['close']
            high = df['high']
            low = df['low']
            
            # Trend strength (using ADX-like calculation)
            price_change = close.diff()
            trend_strength = abs(price_change.rolling(14).mean()) / close.rolling(14).std()
            analysis['trend_strength'][tf] = float(trend_strength.iloc[-1]) if not trend_strength.empty else 0.0
            
            # Volatility
            returns = close.pct_change()
            volatility = returns.rolling(20).std() * np.sqrt(252)  # Annualized
            analysis['volatility'][tf] = float(volatility.iloc[-1]) if not volatility.empty else 0.0
            
            # Support/Resistance levels
            recent_high = float(high.tail(20).max())
            recent_low = float(low.tail(20).min())
            current_price = float(close.iloc[-1])
            
            analysis['support_resistance'][tf] = {
                'support': recent_low,
                'resistance': recent_high,
                'current_price': current_price,
                'distance_to_support': (current_price - recent_low) / recent_low * 100,
                'distance_to_resistance': (recent_high - current_price) / current_price * 100
            }
            
            # Breakout detection
            sma_20 = close.rolling(20).mean()
            sma_50 = close.rolling(50).mean() if len(df) >= 50 else None
            
            breakout_up = current_price > float(sma_20.iloc[-1])
            breakout_down = current_price < float(sma_20.iloc[-1])
            
            if sma_50 is not None:
                golden_cross = sma_20.iloc[-1] > sma_50.iloc[-1] and sma_20.iloc[-2] <= sma_50.iloc[-2]
                death_cross = sma_20.iloc[-1] < sma_50.iloc[-1] and sma_20.iloc[-2] >= sma_50.iloc[-2]
            else:
                golden_cross = False
                death_cross = False
            
            analysis['breakouts'][tf] = {
                'breakout_up': breakout_up,
                'breakout_down': breakout_down,
                'golden_cross': golden_cross,
                'death_cross': death_cross
            }
        
        return analysis


# Global instance
_multi_timeframe_analyzer: Optional[MultiTimeframeAnalyzer] = None


def get_multi_timeframe_analyzer() -> MultiTimeframeAnalyzer:
    """Get global multi-timeframe analyzer instance"""
    global _multi_timeframe_analyzer
    if _multi_timeframe_analyzer is None:
        _multi_timeframe_analyzer = MultiTimeframeAnalyzer()
    return _multi_timeframe_analyzer
