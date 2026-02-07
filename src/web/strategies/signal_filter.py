"""
Signal Filtering System
Strict filters to ensure only high-confidence signals are generated
"""
from typing import Dict, List, Optional
from .base_strategy import StrategyResult
import logging

logger = logging.getLogger(__name__)


class SignalFilter:
    """
    Filters trading signals to ensure high accuracy
    
    Filters applied:
    - Confidence threshold (minimum 70% for BUY/SELL)
    - Multi-model agreement (at least 2/3 models must agree)
    - Risk-adjusted signals (consider volatility)
    - Trend confirmation (price must align with signal)
    - Volume confirmation (unusual volume for entry)
    """
    
    def __init__(self, parameters: Dict = None):
        self.min_confidence_buy_sell = parameters.get('min_confidence_buy_sell', 0.70) if parameters else 0.70
        self.min_confidence_hold = parameters.get('min_confidence_hold', 0.60) if parameters else 0.60
        self.require_model_agreement = parameters.get('require_model_agreement', True) if parameters else True
        self.min_models_agree = parameters.get('min_models_agree', 2) if parameters else 2
        self.require_volume_confirmation = parameters.get('require_volume_confirmation', True) if parameters else True
        self.require_trend_confirmation = parameters.get('require_trend_confirmation', True) if parameters else True
    
    def filter_signal(
        self,
        signal_result: StrategyResult,
        market_data: Dict,
        model_predictions: Optional[Dict[str, float]] = None,
        regime_info: Optional[Dict] = None
    ) -> Optional[StrategyResult]:
        """
        Filter a signal based on multiple criteria
        
        Args:
            signal_result: Original strategy result
            market_data: Market data (current_price, indicators, etc.)
            model_predictions: Dict of model predictions {'model_name': probability}
            regime_info: Market regime information
            
        Returns:
            Filtered StrategyResult or None if signal doesn't pass filters
        """
        # Check confidence threshold
        if not self._check_confidence(signal_result):
            logger.debug(f"Signal filtered: Low confidence ({signal_result.confidence:.2%})")
            return None
        
        # Check multi-model agreement
        if self.require_model_agreement and model_predictions:
            if not self._check_model_agreement(signal_result, model_predictions):
                logger.debug(f"Signal filtered: Models don't agree")
                return None
        
        # Check trend confirmation
        if self.require_trend_confirmation:
            if not self._check_trend_confirmation(signal_result, market_data):
                logger.debug(f"Signal filtered: Trend doesn't confirm")
                return None
        
        # Check volume confirmation
        if self.require_volume_confirmation and signal_result.signal in ['BUY', 'SELL']:
            if not self._check_volume_confirmation(market_data, regime_info):
                logger.debug(f"Signal filtered: Volume doesn't confirm")
                return None
        
        # Adjust confidence based on filters passed
        adjusted_confidence = self._adjust_confidence(
            signal_result.confidence,
            market_data,
            regime_info
        )
        
        # Create filtered result
        existing_metadata = signal_result.metadata or {}
        filtered_result = StrategyResult(
            signal=signal_result.signal,
            confidence=adjusted_confidence,
            entry_price=signal_result.entry_price,
            stop_loss=signal_result.stop_loss,
            target_1=signal_result.target_1,
            target_2=signal_result.target_2,
            metadata={
                **existing_metadata,
                'filtered': True,
                'original_confidence': signal_result.confidence,
                'filters_passed': True
            }
        )
        
        logger.info(f"Signal passed filters: {signal_result.signal} (confidence: {adjusted_confidence:.2%})")
        return filtered_result
    
    def _check_confidence(self, signal_result: StrategyResult) -> bool:
        """Check if signal meets minimum confidence threshold"""
        if signal_result.signal in ['BUY', 'SELL']:
            return signal_result.confidence >= self.min_confidence_buy_sell
        else:  # HOLD
            return signal_result.confidence >= self.min_confidence_hold
    
    def _check_model_agreement(
        self,
        signal_result: StrategyResult,
        model_predictions: Dict[str, float]
    ) -> bool:
        """
        Check if multiple models agree on the signal
        
        For BUY: at least min_models_agree models should have prob > 0.55
        For SELL: at least min_models_agree models should have prob < 0.45
        For HOLD: models should be mixed (no strong consensus)
        """
        if len(model_predictions) < self.min_models_agree:
            return True  # Not enough models to check agreement
        
        probs = list(model_predictions.values())
        
        if signal_result.signal == 'BUY':
            # Count models predicting up (prob > 0.55)
            bullish_count = sum(1 for p in probs if p > 0.55)
            return bullish_count >= self.min_models_agree
        
        elif signal_result.signal == 'SELL':
            # Count models predicting down (prob < 0.45)
            bearish_count = sum(1 for p in probs if p < 0.45)
            return bearish_count >= self.min_models_agree
        
        else:  # HOLD
            # For HOLD, we want mixed signals (not strong consensus either way)
            bullish_count = sum(1 for p in probs if p > 0.55)
            bearish_count = sum(1 for p in probs if p < 0.45)
            # HOLD is valid if no strong consensus
            return bullish_count < self.min_models_agree and bearish_count < self.min_models_agree
    
    def _check_trend_confirmation(
        self,
        signal_result: StrategyResult,
        market_data: Dict
    ) -> bool:
        """
        Check if price action confirms the signal direction
        
        BUY: Price should be above key moving averages or showing upward momentum
        SELL: Price should be below key moving averages or showing downward momentum
        """
        current_price = market_data.get('current_price', 0)
        sma_20 = market_data.get('sma_20', current_price)
        sma_50 = market_data.get('sma_50', current_price)
        macd = market_data.get('macd', 0)
        macd_signal = market_data.get('macd_signal', 0)
        
        if signal_result.signal == 'BUY':
            # Price should be above SMA20 or MACD bullish
            price_above_ma = current_price > sma_20 * 0.98  # Allow 2% tolerance
            macd_bullish = macd > macd_signal
            return price_above_ma or macd_bullish
        
        elif signal_result.signal == 'SELL':
            # Price should be below SMA20 or MACD bearish
            price_below_ma = current_price < sma_20 * 1.02  # Allow 2% tolerance
            macd_bearish = macd < macd_signal
            return price_below_ma or macd_bearish
        
        else:  # HOLD
            return True  # HOLD doesn't need trend confirmation
    
    def _check_volume_confirmation(
        self,
        market_data: Dict,
        regime_info: Optional[Dict]
    ) -> bool:
        """
        Check if volume confirms the signal
        
        For entry signals (BUY/SELL), we want unusual volume (>1.2x average)
        """
        if regime_info:
            volume_ratio = regime_info.get('volume_ratio', 1.0)
            unusual_volume = regime_info.get('unusual_volume', False)
            # Require at least 1.2x average volume for entry signals
            return volume_ratio >= 1.2 or unusual_volume
        
        # Fallback: check volume from market_data
        volume_ratio = market_data.get('volume_ratio', 1.0)
        return volume_ratio >= 1.2
    
    def _adjust_confidence(
        self,
        base_confidence: float,
        market_data: Dict,
        regime_info: Optional[Dict]
    ) -> float:
        """
        Adjust confidence based on market conditions
        
        Factors:
        - Volatility (higher volatility = lower confidence)
        - Trend strength (stronger trend = higher confidence)
        - Volume (unusual volume = higher confidence)
        """
        adjusted = base_confidence
        
        if regime_info:
            # Adjust for volatility (high volatility reduces confidence)
            volatility_pct = regime_info.get('volatility_pct', 2.0)
            if volatility_pct > 5.0:  # Very high volatility
                adjusted *= 0.9
            elif volatility_pct < 1.5:  # Low volatility (good)
                adjusted *= 1.05
            
            # Adjust for trend strength (stronger trend = higher confidence)
            trend_strength = regime_info.get('trend_strength', 25.0)
            if trend_strength > 40:  # Very strong trend
                adjusted *= 1.1
            elif trend_strength < 20:  # Weak trend
                adjusted *= 0.95
            
            # Adjust for volume (unusual volume = higher confidence)
            if regime_info.get('unusual_volume', False):
                adjusted *= 1.05
        
        # Clamp to [0, 1]
        return max(0.0, min(1.0, adjusted))


def get_signal_filter(parameters: Dict = None) -> SignalFilter:
    """Get global signal filter instance"""
    return SignalFilter(parameters)
