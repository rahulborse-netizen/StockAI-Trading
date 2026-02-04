"""
Base Strategy Interface
All trading strategies should inherit from this
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class StrategyResult:
    """Result from strategy execution"""
    signal: str  # BUY, SELL, HOLD
    confidence: float  # 0-1
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    target_1: Optional[float] = None
    target_2: Optional[float] = None
    metadata: Dict = None


class BaseStrategy(ABC):
    """Base class for all trading strategies"""
    
    def __init__(self, name: str, parameters: Dict = None):
        self.name = name
        self.parameters = parameters or {}
    
    @abstractmethod
    def execute(self, data: Dict) -> StrategyResult:
        """
        Execute strategy and return signal
        
        Args:
            data: Market data and features
        
        Returns:
            StrategyResult with signal and levels
        """
        pass
    
    def get_parameters(self) -> Dict:
        """Get strategy parameters"""
        return self.parameters.copy()
    
    def set_parameters(self, parameters: Dict):
        """Update strategy parameters"""
        self.parameters.update(parameters)
    
    def validate_parameters(self) -> bool:
        """Validate strategy parameters"""
        return True  # Override in subclasses
