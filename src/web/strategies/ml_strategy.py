"""
ML-Based Trading Strategy
Uses machine learning models to generate signals
"""
from typing import Dict
from .base_strategy import BaseStrategy, StrategyResult


class MLStrategy(BaseStrategy):
    """Machine learning based trading strategy"""
    
    def __init__(self, parameters: Dict = None):
        super().__init__("ML Strategy", parameters)
        self.prob_threshold_buy = parameters.get('prob_threshold_buy', 0.60) if parameters else 0.60
        self.prob_threshold_sell = parameters.get('prob_threshold_sell', 0.40) if parameters else 0.40
    
    def execute(self, data: Dict) -> StrategyResult:
        """
        Execute ML strategy
        
        Args:
            data: Should contain 'probability' (prob_up) and 'current_price'
        
        Returns:
            StrategyResult
        """
        prob_up = data.get('probability', 0.5)
        current_price = data.get('current_price', 0)
        
        # Determine signal
        if prob_up >= self.prob_threshold_buy:
            signal = 'BUY'
            confidence = prob_up
            entry_price = current_price * 0.998
            stop_loss = current_price * 0.97
            target_1 = current_price * 1.03
            target_2 = current_price * 1.05
        elif prob_up <= self.prob_threshold_sell:
            signal = 'SELL'
            confidence = 1.0 - prob_up
            entry_price = current_price * 1.002
            stop_loss = current_price * 1.03
            target_1 = current_price * 0.97
            target_2 = current_price * 0.95
        else:
            signal = 'HOLD'
            confidence = abs(prob_up - 0.5) * 2  # Convert to 0-1 scale
            entry_price = current_price * 1.002
            stop_loss = current_price * 0.98
            target_1 = current_price * 1.02
            target_2 = current_price * 1.025
        
        return StrategyResult(
            signal=signal,
            confidence=confidence,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_1=target_1,
            target_2=target_2,
            metadata={
                'probability': prob_up,
                'strategy': self.name,
                'parameters': self.parameters
            }
        )
    
    def validate_parameters(self) -> bool:
        """Validate ML strategy parameters"""
        if not 0 < self.prob_threshold_buy <= 1:
            return False
        if not 0 <= self.prob_threshold_sell < 1:
            return False
        if self.prob_threshold_sell >= self.prob_threshold_buy:
            return False
        return True
