"""
Momentum Strategy
Trend-following strategy that buys winners and sells losers
"""
from typing import Dict
import numpy as np
from .base_strategy import BaseStrategy, StrategyResult


class MomentumStrategy(BaseStrategy):
    """
    Momentum strategy based on price trends and moving average crossovers
    
    Logic:
    - Buy when short-term MA crosses above long-term MA (Golden Cross)
    - Sell when short-term MA crosses below long-term MA (Death Cross)
    - Use MACD and ADX for trend strength confirmation
    """
    
    def __init__(self, parameters: Dict = None):
        super().__init__("Momentum Strategy", parameters)
        self.short_ma_period = parameters.get('short_ma_period', 10) if parameters else 10
        self.long_ma_period = parameters.get('long_ma_period', 50) if parameters else 50
        self.momentum_period = parameters.get('momentum_period', 20) if parameters else 20
        self.min_trend_strength = parameters.get('min_trend_strength', 25) if parameters else 25  # ADX threshold
    
    def execute(self, data: Dict) -> StrategyResult:
        """
        Execute momentum strategy
        
        Args:
            data: Dict with:
                - current_price: Current stock price
                - sma_10: 10-period moving average
                - sma_50: 50-period moving average
                - macd: MACD line
                - macd_signal: MACD signal line
                - macd_hist: MACD histogram
                - ret_5: 5-day return
                - ret_20: 20-day return (momentum)
                - adx: Average Directional Index (trend strength)
        
        Returns:
            StrategyResult with signal and levels
        """
        current_price = data.get('current_price', 0)
        sma_10 = data.get('sma_10', current_price)
        sma_50 = data.get('sma_50', current_price)
        macd = data.get('macd', 0)
        macd_signal = data.get('macd_signal', 0)
        macd_hist = data.get('macd_hist', 0)
        ret_5 = data.get('ret_5', 0)  # 5-day return
        ret_20 = data.get('ret_20', 0)  # 20-day momentum
        adx = data.get('adx', 20)  # Trend strength
        
        # Calculate momentum score (0-1 scale)
        momentum_score = self._calculate_momentum_score(ret_5, ret_20, macd_hist)
        
        # Calculate MA crossover
        ma_diff = (sma_10 - sma_50) / sma_50 * 100 if sma_50 > 0 else 0
        
        # Determine signal
        signal = 'HOLD'
        confidence = 0.5
        
        # STRONG BUY: Golden Cross + Positive MACD + Strong trend
        if (ma_diff > 0 and macd > macd_signal and 
            momentum_score > 0.6 and adx > self.min_trend_strength):
            signal = 'BUY'
            confidence = min(0.95, 0.6 + momentum_score * 0.3 + (adx - 25) / 100)
            entry_price = current_price * 1.002  # Buy on momentum
            stop_loss = sma_10 * 0.97  # Stop below short MA
            # Momentum targets are further out
            target_1 = current_price * 1.05     # 5% gain
            target_2 = current_price * 1.10     # 10% gain
            
        # STRONG SELL: Death Cross + Negative MACD
        elif (ma_diff < -2 and macd < macd_signal and 
              momentum_score < 0.4 and adx > self.min_trend_strength):
            signal = 'SELL'
            confidence = min(0.95, 0.6 + (1 - momentum_score) * 0.3 + (adx - 25) / 100)
            entry_price = current_price * 0.998
            stop_loss = sma_10 * 1.03
            target_1 = current_price * 0.95
            target_2 = current_price * 0.90
            
        # WEAK BUY: Positive momentum but weak trend
        elif momentum_score > 0.55 and ma_diff > 0:
            signal = 'BUY'
            confidence = 0.55 + momentum_score * 0.2
            entry_price = current_price * 1.001
            stop_loss = current_price * 0.97
            target_1 = current_price * 1.03
            target_2 = current_price * 1.05
            
        # HOLD: No clear momentum
        else:
            signal = 'HOLD'
            confidence = 0.5
            entry_price = current_price
            stop_loss = current_price * 0.97
            target_1 = current_price * 1.02
            target_2 = current_price * 1.04
        
        return StrategyResult(
            signal=signal,
            confidence=max(0.0, min(1.0, confidence)),
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_1=target_1,
            target_2=target_2,
            metadata={
                'strategy': self.name,
                'momentum_score': round(momentum_score, 3),
                'ma_diff_pct': round(ma_diff, 2),
                'macd_histogram': round(macd_hist, 4),
                'adx': round(adx, 2),
                'trend_strength': 'Strong' if adx > 25 else 'Weak',
                'parameters': self.parameters
            }
        )
    
    def _calculate_momentum_score(self, ret_5: float, ret_20: float, macd_hist: float) -> float:
        """
        Calculate momentum score (0-1 scale)
        
        Combines:
        - Short-term return (5-day)
        - Medium-term return (20-day)
        - MACD histogram
        """
        # Normalize returns to 0-1 scale
        # Assume ±10% return maps to 0-1
        ret_5_norm = (ret_5 / 10 + 1) / 2  # -10% -> 0, +10% -> 1
        ret_20_norm = (ret_20 / 20 + 1) / 2  # -20% -> 0, +20% -> 1
        
        # MACD histogram: positive = bullish
        macd_norm = 0.5 + np.tanh(macd_hist * 100) / 2  # Sigmoid-like normalization
        
        # Weighted combination
        momentum_score = (ret_5_norm * 0.4 + ret_20_norm * 0.4 + macd_norm * 0.2)
        
        return max(0.0, min(1.0, momentum_score))
    
    def validate_parameters(self) -> bool:
        """Validate strategy parameters"""
        if self.short_ma_period >= self.long_ma_period:
            return False
        if self.short_ma_period < 5 or self.long_ma_period > 200:
            return False
        if not (5 <= self.momentum_period <= 100):
            return False
        if not (0 <= self.min_trend_strength <= 100):
            return False
        return True
