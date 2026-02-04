"""
Trading Strategies Module
Provides strategy templates and configuration
"""
from .base_strategy import BaseStrategy
from .ml_strategy import MLStrategy

__all__ = ['BaseStrategy', 'MLStrategy']
