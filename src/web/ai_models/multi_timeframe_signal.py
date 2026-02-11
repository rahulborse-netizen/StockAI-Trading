"""
Multi-Timeframe Signal Aggregator
Combines signals from multiple timeframes (5m, 15m, 1h, 1d) into unified signals
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional
from datetime import datetime
import numpy as np

from src.web.ai_models.elite_signal_generator import get_elite_signal_generator

logger = logging.getLogger(__name__)


class MultiTimeframeSignalAggregator:
    """
    Aggregates signals from multiple timeframes using weighted consensus.
    Higher weight for shorter timeframes during intraday trading.
    """
    
    def __init__(self):
        self.elite_generator = get_elite_signal_generator()
        
        # Default weights for different timeframes
        # During intraday hours, shorter timeframes get higher weight
        self.intraday_weights = {
            '5m': 0.35,   # Highest weight during intraday
            '15m': 0.30,  # High weight
            '1h': 0.25,   # Medium weight
            '1d': 0.10    # Lower weight (trend context)
        }
        
        # For daily/end-of-day analysis, daily gets higher weight
        self.daily_weights = {
            '5m': 0.10,   # Lower weight
            '15m': 0.15,  # Medium weight
            '1h': 0.25,   # Medium-high weight
            '1d': 0.50    # Highest weight (trend context)
        }
    
    def generate_multi_timeframe_signal(
        self,
        ticker: str,
        timeframes: Optional[List[str]] = None,
        is_intraday: bool = True,
        use_ensemble: bool = True,
        min_confidence: float = 0.7
    ) -> Dict:
        """
        Generate unified signal from multiple timeframes.
        
        Args:
            ticker: Stock ticker (e.g., 'RELIANCE.NS')
            timeframes: List of timeframes to analyze (default: ['5m', '15m', '1h', '1d'])
            is_intraday: Whether currently in intraday trading hours
            use_ensemble: Whether to use ensemble models for each timeframe
            min_confidence: Minimum confidence threshold for execution
        
        Returns:
            Unified signal dictionary with aggregated predictions
        """
        if timeframes is None:
            timeframes = ['5m', '15m', '1h', '1d']
        
        # Validate timeframes
        valid_timeframes = {'5m', '15m', '1h', '1d'}
        invalid = [tf for tf in timeframes if tf not in valid_timeframes]
        if invalid:
            return {
                'error': f'Invalid timeframes: {invalid}. Supported: {valid_timeframes}',
                'ticker': ticker
            }
        
        # Select weights based on trading session
        weights = self.intraday_weights if is_intraday else self.daily_weights
        
        # Normalize weights for selected timeframes
        selected_weights = {tf: weights.get(tf, 0.0) for tf in timeframes}
        total_weight = sum(selected_weights.values())
        if total_weight > 0:
            selected_weights = {tf: w / total_weight for tf, w in selected_weights.items()}
        else:
            # Equal weights if no weights defined
            selected_weights = {tf: 1.0 / len(timeframes) for tf in timeframes}
        
        logger.info(f"[Multi-TF] Generating signals for {ticker} across {timeframes} (intraday={is_intraday})")
        
        # Generate signals for each timeframe
        timeframe_signals = {}
        timeframe_errors = {}
        
        for timeframe in timeframes:
            try:
                signal = self.elite_generator.generate_intraday_signal(
                    ticker=ticker,
                    timeframe=timeframe,
                    use_ensemble=use_ensemble
                )
                
                if 'error' in signal:
                    timeframe_errors[timeframe] = signal['error']
                    logger.warning(f"[Multi-TF] Error for {ticker} ({timeframe}): {signal['error']}")
                else:
                    timeframe_signals[timeframe] = signal
                    logger.debug(f"[Multi-TF] {ticker} ({timeframe}): signal={signal.get('signal')}, prob={signal.get('probability', 0):.3f}")
            
            except Exception as e:
                timeframe_errors[timeframe] = str(e)
                logger.error(f"[Multi-TF] Exception generating signal for {ticker} ({timeframe}): {e}")
        
        if not timeframe_signals:
            return {
                'error': 'Failed to generate signals for any timeframe',
                'ticker': ticker,
                'timeframe_errors': timeframe_errors
            }
        
        # Aggregate probabilities using weighted average
        weighted_prob = 0.0
        total_weight_used = 0.0
        
        for timeframe, signal in timeframe_signals.items():
            prob = signal.get('probability', 0.5)
            weight = selected_weights.get(timeframe, 0.0)
            weighted_prob += prob * weight
            total_weight_used += weight
        
        if total_weight_used > 0:
            final_probability = weighted_prob / total_weight_used
        else:
            # Fallback: simple average
            final_probability = np.mean([s.get('probability', 0.5) for s in timeframe_signals.values()])
        
        # Aggregate confidence (weighted average)
        weighted_conf = 0.0
        for timeframe, signal in timeframe_signals.items():
            conf = signal.get('confidence', 0.5)
            weight = selected_weights.get(timeframe, 0.0)
            weighted_conf += conf * weight
        
        if total_weight_used > 0:
            final_confidence = weighted_conf / total_weight_used
        else:
            final_confidence = np.mean([s.get('confidence', 0.5) for s in timeframe_signals.values()])
        
        # Determine consensus signal
        # Count signals by type
        signal_counts = {}
        for signal in timeframe_signals.values():
            sig = signal.get('signal', 'HOLD')
            signal_counts[sig] = signal_counts.get(sig, 0) + 1
        
        # Determine consensus based on probability and signal counts
        if final_probability >= 0.65:
            consensus_signal = 'STRONG_BUY'
        elif final_probability >= 0.55:
            consensus_signal = 'BUY'
        elif final_probability <= 0.35:
            consensus_signal = 'STRONG_SELL'
        elif final_probability <= 0.45:
            consensus_signal = 'SELL'
        else:
            consensus_signal = 'HOLD'
        
        # Override with signal count consensus if strong agreement
        if len(timeframe_signals) >= 3:
            buy_count = signal_counts.get('BUY', 0) + signal_counts.get('STRONG_BUY', 0)
            sell_count = signal_counts.get('SELL', 0) + signal_counts.get('STRONG_SELL', 0)
            
            if buy_count >= len(timeframe_signals) * 0.75:  # 75% agreement
                consensus_signal = 'STRONG_BUY'
            elif buy_count >= len(timeframe_signals) * 0.5:  # 50% agreement
                consensus_signal = 'BUY'
            elif sell_count >= len(timeframe_signals) * 0.75:
                consensus_signal = 'STRONG_SELL'
            elif sell_count >= len(timeframe_signals) * 0.5:
                consensus_signal = 'SELL'
        
        # Get entry/exit levels from most recent timeframe (prefer shorter for intraday)
        if is_intraday:
            priority_order = ['5m', '15m', '1h', '1d']
        else:
            priority_order = ['1d', '1h', '15m', '5m']
        
        entry_level = None
        stop_loss = None
        target_1 = None
        target_2 = None
        current_price = None
        
        for tf in priority_order:
            if tf in timeframe_signals:
                sig = timeframe_signals[tf]
                entry_level = sig.get('entry_level')
                stop_loss = sig.get('stop_loss')
                target_1 = sig.get('target_1')
                target_2 = sig.get('target_2')
                current_price = sig.get('current_price')
                break
        
        # Calculate aggregate metrics
        all_prices = [s.get('current_price') for s in timeframe_signals.values() if s.get('current_price')]
        all_highs = [s.get('recent_high') for s in timeframe_signals.values() if s.get('recent_high')]
        all_lows = [s.get('recent_low') for s in timeframe_signals.values() if s.get('recent_low')]
        all_volatilities = [s.get('volatility') for s in timeframe_signals.values() if s.get('volatility')]
        
        # Build response
        response = {
            'ticker': ticker,
            'consensus_signal': consensus_signal,
            'probability': float(final_probability),
            'confidence': float(final_confidence),
            'meets_threshold': final_probability >= min_confidence or final_probability <= (1 - min_confidence),
            'current_price': current_price or (np.mean(all_prices) if all_prices else None),
            'entry_level': entry_level,
            'stop_loss': stop_loss,
            'target_1': target_1,
            'target_2': target_2,
            'recent_high': np.max(all_highs) if all_highs else None,
            'recent_low': np.min(all_lows) if all_lows else None,
            'volatility': np.mean(all_volatilities) if all_volatilities else None,
            'timeframe_signals': {
                tf: {
                    'signal': sig.get('signal'),
                    'probability': sig.get('probability'),
                    'confidence': sig.get('confidence'),
                    'weight': selected_weights.get(tf, 0.0)
                }
                for tf, sig in timeframe_signals.items()
            },
            'timeframe_weights': selected_weights,
            'timeframe_errors': timeframe_errors,
            'is_intraday': is_intraday,
            'timestamp': datetime.now().isoformat(),
            'multi_timeframe': True
        }
        
        return response
    
    def should_execute(self, signal: Dict, min_confidence: float = 0.7) -> bool:
        """
        Determine if signal meets execution criteria.
        
        Args:
            signal: Multi-timeframe signal dictionary
            min_confidence: Minimum confidence threshold
        
        Returns:
            True if signal should be executed
        """
        if 'error' in signal:
            return False
        
        prob = signal.get('probability', 0.5)
        conf = signal.get('confidence', 0.5)
        consensus = signal.get('consensus_signal', 'HOLD')
        
        # Must be BUY or SELL signal (not HOLD)
        if consensus == 'HOLD':
            return False
        
        # Must meet probability threshold
        if prob < min_confidence and prob > (1 - min_confidence):
            return False
        
        # Must have reasonable confidence
        if conf < 0.4:
            return False
        
        return True


# Global instance
_multi_tf_aggregator: Optional[MultiTimeframeSignalAggregator] = None


def get_multi_timeframe_aggregator() -> MultiTimeframeSignalAggregator:
    """Get global multi-timeframe aggregator instance"""
    global _multi_tf_aggregator
    if _multi_tf_aggregator is None:
        _multi_tf_aggregator = MultiTimeframeSignalAggregator()
    return _multi_tf_aggregator
