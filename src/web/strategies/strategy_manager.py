"""
Strategy Manager
Manages multiple trading strategies and combines their signals
"""
from typing import Dict, List, Optional
import logging
from .base_strategy import BaseStrategy, StrategyResult
from .ml_strategy import MLStrategy
from .mean_reversion_strategy import MeanReversionStrategy
from .momentum_strategy import MomentumStrategy
from .adaptive_elite_strategy import AdaptiveEliteStrategy

logger = logging.getLogger(__name__)


class StrategyManager:
    """
    Manages multiple trading strategies
    Can run strategies individually or combine them (ensemble)
    """
    
    AVAILABLE_STRATEGIES = {
        'ml': MLStrategy,
        'mean_reversion': MeanReversionStrategy,
        'momentum': MomentumStrategy,
        'adaptive_elite': AdaptiveEliteStrategy
    }
    
    def __init__(self):
        self.strategies: Dict[str, BaseStrategy] = {}
        self.active_strategy = 'ml'  # Default strategy
    
    def register_strategy(self, name: str, strategy: BaseStrategy):
        """Register a new strategy"""
        self.strategies[name] = strategy
        logger.info(f"✅ Registered strategy: {name} ({strategy.name})")
    
    def initialize_default_strategies(self):
        """Initialize default strategies with default parameters"""
        # ML Strategy (default)
        self.register_strategy('ml', MLStrategy({
            'prob_threshold_buy': 0.60,
            'prob_threshold_sell': 0.40
        }))
        
        # Mean Reversion Strategy
        self.register_strategy('mean_reversion', MeanReversionStrategy({
            'ma_period': 20,
            'std_multiplier': 2.0,
            'rsi_oversold': 30,
            'rsi_overbought': 70
        }))
        
        # Momentum Strategy
        self.register_strategy('momentum', MomentumStrategy({
            'short_ma_period': 10,
            'long_ma_period': 50,
            'momentum_period': 20,
            'min_trend_strength': 25
        }))
        
        # Adaptive Elite Strategy
        self.register_strategy('adaptive_elite', AdaptiveEliteStrategy({
            'min_confidence': 0.70,
            'use_ensemble': True,
            'use_multi_timeframe': True
        }))
        
        logger.info(f"✅ Initialized {len(self.strategies)} strategies")
    
    def set_active_strategy(self, strategy_name: str) -> bool:
        """Set the active strategy"""
        if strategy_name in self.strategies:
            self.active_strategy = strategy_name
            logger.info(f"✅ Active strategy set to: {strategy_name}")
            return True
        else:
            logger.error(f"❌ Strategy not found: {strategy_name}")
            return False
    
    def get_strategy(self, strategy_name: str = None) -> Optional[BaseStrategy]:
        """Get a strategy by name (or active strategy if not specified)"""
        if strategy_name is None:
            strategy_name = self.active_strategy
        return self.strategies.get(strategy_name)
    
    def execute_strategy(self, strategy_name: str, data: Dict) -> StrategyResult:
        """Execute a specific strategy"""
        strategy = self.get_strategy(strategy_name)
        if strategy:
            return strategy.execute(data)
        else:
            raise ValueError(f"Strategy not found: {strategy_name}")
    
    def execute_active_strategy(self, data: Dict) -> StrategyResult:
        """Execute the currently active strategy"""
        return self.execute_strategy(self.active_strategy, data)
    
    def execute_all_strategies(self, data: Dict) -> Dict[str, StrategyResult]:
        """Execute all registered strategies and return their results"""
        results = {}
        for name, strategy in self.strategies.items():
            try:
                results[name] = strategy.execute(data)
            except Exception as e:
                logger.error(f"Error executing strategy {name}: {e}")
        return results
    
    def combine_strategies(self, data: Dict, method: str = 'weighted_average') -> StrategyResult:
        """
        Combine multiple strategies into a single signal
        
        Args:
            data: Market data for strategies
            method: Combination method ('weighted_average', 'voting', 'best_performer')
        
        Returns:
            Combined StrategyResult
        """
        # Execute all strategies
        results = self.execute_all_strategies(data)
        
        if not results:
            raise ValueError("No strategies available")
        
        if method == 'weighted_average':
            return self._weighted_average_ensemble(results, data)
        elif method == 'voting':
            return self._voting_ensemble(results, data)
        elif method == 'best_performer':
            return self._best_performer_ensemble(results, data)
        else:
            raise ValueError(f"Unknown combination method: {method}")
    
    def _weighted_average_ensemble(self, results: Dict[str, StrategyResult], data: Dict) -> StrategyResult:
        """
        Combine strategies using weighted average based on confidence
        
        Weights:
        - ML Strategy: 0.4 (most reliable, trained on data)
        - Mean Reversion: 0.3 (good in range-bound markets)
        - Momentum: 0.3 (good in trending markets)
        """
        weights = {
            'ml': 0.4,
            'mean_reversion': 0.3,
            'momentum': 0.3
        }
        
        # Calculate signal scores: BUY=1, HOLD=0, SELL=-1
        signal_scores = {
            'BUY': 1.0,
            'HOLD': 0.0,
            'SELL': -1.0
        }
        
        weighted_signal = 0.0
        total_confidence = 0.0
        entry_prices = []
        stop_losses = []
        targets_1 = []
        targets_2 = []
        
        for strategy_name, result in results.items():
            weight = weights.get(strategy_name, 0.33)
            signal_score = signal_scores.get(result.signal, 0.0)
            
            # Weight by both strategy weight and confidence
            weighted_signal += signal_score * weight * result.confidence
            total_confidence += result.confidence * weight
            
            entry_prices.append(result.entry_price)
            stop_losses.append(result.stop_loss)
            targets_1.append(result.target_1)
            targets_2.append(result.target_2)
        
        # Determine final signal
        if weighted_signal > 0.2:  # Bullish consensus
            final_signal = 'BUY'
        elif weighted_signal < -0.2:  # Bearish consensus
            final_signal = 'SELL'
        else:
            final_signal = 'HOLD'
        
        # Average the levels
        current_price = data.get('current_price', 0)
        
        return StrategyResult(
            signal=final_signal,
            confidence=min(1.0, total_confidence / len(results)),
            entry_price=sum(entry_prices) / len(entry_prices) if entry_prices else current_price,
            stop_loss=sum(stop_losses) / len(stop_losses) if stop_losses else current_price * 0.97,
            target_1=sum(targets_1) / len(targets_1) if targets_1 else current_price * 1.02,
            target_2=sum(targets_2) / len(targets_2) if targets_2 else current_price * 1.04,
            metadata={
                'strategy': 'Ensemble (Weighted Average)',
                'weighted_signal_score': round(weighted_signal, 3),
                'individual_strategies': {
                    name: {
                        'signal': result.signal,
                        'confidence': round(result.confidence, 3)
                    }
                    for name, result in results.items()
                }
            }
        )
    
    def _voting_ensemble(self, results: Dict[str, StrategyResult], data: Dict) -> StrategyResult:
        """Simple voting: majority wins"""
        votes = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        
        for result in results.values():
            votes[result.signal] += 1
        
        final_signal = max(votes, key=votes.get)
        
        # Average confidence from strategies that voted for winning signal
        winning_confidences = [
            result.confidence 
            for result in results.values() 
            if result.signal == final_signal
        ]
        avg_confidence = sum(winning_confidences) / len(winning_confidences) if winning_confidences else 0.5
        
        current_price = data.get('current_price', 0)
        
        return StrategyResult(
            signal=final_signal,
            confidence=avg_confidence,
            entry_price=current_price,
            stop_loss=current_price * (0.97 if final_signal == 'BUY' else 1.03),
            target_1=current_price * (1.03 if final_signal == 'BUY' else 0.97),
            target_2=current_price * (1.05 if final_signal == 'BUY' else 0.95),
            metadata={
                'strategy': 'Ensemble (Voting)',
                'votes': votes,
                'individual_strategies': {
                    name: result.signal for name, result in results.items()
                }
            }
        )
    
    def _best_performer_ensemble(self, results: Dict[str, StrategyResult], data: Dict) -> StrategyResult:
        """Use the strategy with highest confidence"""
        best_strategy = max(results.items(), key=lambda x: x[1].confidence)
        result = best_strategy[1]
        
        # Add metadata about which strategy was chosen
        result.metadata['ensemble_method'] = 'Best Performer'
        result.metadata['chosen_strategy'] = best_strategy[0]
        
        return result
    
    def get_available_strategies(self) -> List[str]:
        """Get list of available strategy names"""
        return list(self.strategies.keys())
    
    def get_strategy_info(self, strategy_name: str = None) -> Dict:
        """Get information about a strategy"""
        strategy = self.get_strategy(strategy_name)
        if strategy:
            return {
                'name': strategy.name,
                'parameters': strategy.parameters,
                'is_active': strategy_name == self.active_strategy if strategy_name else True
            }
        return {}


# Global singleton
_strategy_manager = None


def get_strategy_manager() -> StrategyManager:
    """Get global strategy manager instance"""
    global _strategy_manager
    if _strategy_manager is None:
        _strategy_manager = StrategyManager()
        _strategy_manager.initialize_default_strategies()
    return _strategy_manager
