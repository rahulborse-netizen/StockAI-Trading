"""
Mean Reversion Strategy
Buys when price is below moving average, sells when above
"""
from typing import Dict
import numpy as np
from .base_strategy import BaseStrategy, StrategyResult


class MeanReversionStrategy(BaseStrategy):
    """
    Mean reversion strategy based on Bollinger Bands and moving averages
    
    Logic:
    - Buy when price is below lower Bollinger Band (oversold)
    - Sell when price is above upper Bollinger Band (overbought)
    - Use RSI for confirmation
    """
    
    def __init__(self, parameters: Dict = None):
        super().__init__("Mean Reversion Strategy", parameters)
        self.ma_period = parameters.get('ma_period', 20) if parameters else 20
        self.std_multiplier = parameters.get('std_multiplier', 2.0) if parameters else 2.0
        self.rsi_oversold = parameters.get('rsi_oversold', 30) if parameters else 30
        self.rsi_overbought = parameters.get('rsi_overbought', 70) if parameters else 70
    
    def execute(self, data: Dict) -> StrategyResult:
        """
        Execute mean reversion strategy
        
        Args:
            data: Dict with:
                - current_price: Current stock price
                - sma_20: 20-period simple moving average
                - price_std: Standard deviation of price
                - rsi_14: RSI indicator
                - bollinger_upper: Upper Bollinger Band
                - bollinger_lower: Lower Bollinger Band
        
        Returns:
            StrategyResult with signal and levels
        """
        current_price = data.get('current_price', 0)
        sma = data.get('sma_20', current_price)
        price_std = data.get('price_std', 0)
        rsi = data.get('rsi_14', 50)
        
        # Calculate Bollinger Bands if not provided
        bollinger_upper = data.get('bollinger_upper', sma + (self.std_multiplier * price_std))
        bollinger_lower = data.get('bollinger_lower', sma - (self.std_multiplier * price_std))
        
        # Calculate distance from mean
        distance_from_mean = (current_price - sma) / sma * 100 if sma > 0 else 0
        
        # Mean reversion logic
        signal = 'HOLD'
        confidence = 0.5
        
        # BUY Signal: Price below lower band + RSI oversold
        if current_price < bollinger_lower and rsi < self.rsi_oversold:
            signal = 'BUY'
            # Higher confidence when further below lower band
            confidence = min(0.95, 0.6 + abs(distance_from_mean) / 50)
            entry_price = current_price * 0.998  # Slightly below current
            stop_loss = current_price * 0.95     # 5% stop loss
            target_1 = sma                       # First target: mean
            target_2 = bollinger_upper           # Second target: upper band
            
        # SELL Signal: Price above upper band + RSI overbought
        elif current_price > bollinger_upper and rsi > self.rsi_overbought:
            signal = 'SELL'
            confidence = min(0.95, 0.6 + abs(distance_from_mean) / 50)
            entry_price = current_price * 1.002
            stop_loss = current_price * 1.05
            target_1 = sma
            target_2 = bollinger_lower
            
        # HOLD: Price near mean
        else:
            signal = 'HOLD'
            confidence = 0.5 - abs(distance_from_mean) / 100  # Lower confidence when near mean
            entry_price = current_price
            stop_loss = current_price * 0.97
            target_1 = bollinger_upper if distance_from_mean < 0 else bollinger_lower
            target_2 = target_1 * 1.02
        
        return StrategyResult(
            signal=signal,
            confidence=max(0.0, min(1.0, confidence)),  # Clamp to [0, 1]
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_1=target_1,
            target_2=target_2,
            metadata={
                'strategy': self.name,
                'bollinger_upper': bollinger_upper,
                'bollinger_lower': bollinger_lower,
                'sma': sma,
                'rsi': rsi,
                'distance_from_mean_pct': round(distance_from_mean, 2),
                'parameters': self.parameters
            }
        )
    
    def validate_parameters(self) -> bool:
        """Validate strategy parameters"""
        if self.ma_period < 5 or self.ma_period > 200:
            return False
        if self.std_multiplier < 1.0 or self.std_multiplier > 3.0:
            return False
        if not (0 < self.rsi_oversold < 50):
            return False
        if not (50 < self.rsi_overbought < 100):
            return False
        return True


def calculate_bollinger_bands(prices: list, period: int = 20, std_multiplier: float = 2.0) -> Dict:
    """
    Calculate Bollinger Bands
    
    Args:
        prices: List of historical prices
        period: Moving average period
        std_multiplier: Standard deviation multiplier
    
    Returns:
        Dict with upper, middle, lower bands
    """
    if len(prices) < period:
        return {'upper': 0, 'middle': 0, 'lower': 0, 'std': 0}
    
    prices_array = np.array(prices[-period:])
    middle = np.mean(prices_array)
    std = np.std(prices_array)
    
    upper = middle + (std_multiplier * std)
    lower = middle - (std_multiplier * std)
    
    return {
        'upper': float(upper),
        'middle': float(middle),
        'lower': float(lower),
        'std': float(std)
    }
