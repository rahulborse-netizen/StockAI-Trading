"""
Enhanced Signal Generator
Provides more accurate and precise signals using live data and advanced techniques
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta

from src.web.ai_models.elite_signal_generator import EliteSignalGenerator
from src.web.data_source_manager import get_data_source_manager, DataSource

logger = logging.getLogger(__name__)


class EnhancedSignalGenerator(EliteSignalGenerator):
    """
    Enhanced signal generator with:
    - Live data prioritization
    - Intraday data integration
    - Improved confidence scoring
    - Better signal filtering
    - Real-time updates
    """
    
    def __init__(self):
        super().__init__()
        self.use_intraday_data = True
        self.min_confidence_threshold = 0.55  # Minimum confidence for actionable signals
        self.live_data_weight = 1.5  # Weight multiplier for live data signals
        
    def generate_signal(
        self,
        ticker: str,
        use_ensemble: bool = True,
        use_multi_timeframe: bool = True,
        instrument_key_override: Optional[str] = None,
        use_live_data: bool = True
    ) -> Dict:
        """
        Generate enhanced trading signal with live data prioritization
        
        Args:
            ticker: Stock ticker
            use_ensemble: Use ensemble of models
            use_multi_timeframe: Analyze multiple timeframes
            instrument_key_override: Upstox instrument key
            use_live_data: Prioritize live data from Upstox
        
        Returns:
            Enhanced signal dictionary with improved accuracy
        """
        try:
            # Step 1: Get live current price first (for real-time accuracy)
            current_price = None
            live_data_available = False
            
            if use_live_data:
                try:
                    dsm = get_data_source_manager()
                    quote, source = dsm.get_quote(ticker)
                    if quote and source == DataSource.UPSTOX:
                        current_price = quote.get('price') or quote.get('ltp') or quote.get('current_price')
                        live_data_available = True
                        logger.info(f"[Enhanced Signal] ✅ Got LIVE price for {ticker}: ₹{current_price:.2f}")
                    elif quote:
                        current_price = quote.get('price') or quote.get('ltp') or quote.get('current_price')
                        logger.info(f"[Enhanced Signal] Got price for {ticker}: ₹{current_price:.2f} (source: {source.name})")
                except Exception as e:
                    logger.debug(f"[Enhanced Signal] Live price fetch failed: {e}")
            
            # Step 2: Generate base signal using parent class
            signal = super().generate_signal(
                ticker=ticker,
                use_ensemble=use_ensemble,
                use_multi_timeframe=use_multi_timeframe,
                instrument_key_override=instrument_key_override
            )
            
            if 'error' in signal:
                return signal
            
            # Step 3: Enhance signal with live data and improved metrics
            enhanced_signal = self._enhance_signal_accuracy(
                signal, 
                ticker, 
                current_price, 
                live_data_available
            )
            
            # Step 4: Add intraday insights if available
            if self.use_intraday_data and live_data_available:
                try:
                    intraday_insights = self._get_intraday_insights(ticker, instrument_key_override)
                    if intraday_insights:
                        enhanced_signal['intraday_insights'] = intraday_insights
                        enhanced_signal['confidence'] = min(1.0, enhanced_signal.get('confidence', 0.5) * 1.1)
                except Exception as e:
                    logger.debug(f"[Enhanced Signal] Intraday insights skipped: {e}")
            
            # Step 5: Validate and filter signal quality
            enhanced_signal = self._validate_signal_quality(enhanced_signal)
            
            # Step 6: Add signal metadata
            enhanced_signal['signal_quality'] = self._calculate_signal_quality(enhanced_signal)
            enhanced_signal['data_freshness'] = 'live' if live_data_available else 'cached'
            enhanced_signal['last_updated'] = datetime.now().isoformat()
            
            return enhanced_signal
            
        except Exception as e:
            logger.error(f"[Enhanced Signal] Error generating signal for {ticker}: {e}", exc_info=True)
            return {'error': str(e), 'ticker': ticker}
    
    def _enhance_signal_accuracy(
        self, 
        signal: Dict, 
        ticker: str, 
        current_price: Optional[float],
        live_data_available: bool
    ) -> Dict:
        """Enhance signal with live price and improved confidence"""
        enhanced = signal.copy()
        
        # Update with live price if available
        if current_price and current_price > 0:
            enhanced['current_price'] = current_price
            
            # Recalculate entry/exit levels based on live price
            if 'entry_price' in enhanced and enhanced['entry_price']:
                # Adjust entry if price moved significantly
                price_diff_pct = abs(current_price - enhanced['entry_price']) / enhanced['entry_price']
                if price_diff_pct > 0.02:  # More than 2% difference
                    enhanced['entry_price'] = current_price
                    enhanced['entry_level'] = current_price
                    logger.info(f"[Enhanced Signal] Adjusted entry price to live price: ₹{current_price:.2f}")
        
        # Boost confidence for live data signals
        if live_data_available:
            base_confidence = enhanced.get('confidence', 0.5)
            enhanced['confidence'] = min(1.0, base_confidence * self.live_data_weight)
            enhanced['probability'] = min(1.0, enhanced.get('probability', 0.5) * 1.05)
            logger.info(f"[Enhanced Signal] Boosted confidence for live data: {base_confidence:.3f} -> {enhanced['confidence']:.3f}")
        
        # Improve signal strength calculation
        probability = enhanced.get('probability', 0.5)
        confidence = enhanced.get('confidence', 0.5)
        
        # Signal strength = probability * confidence (weighted)
        signal_strength = (probability * 0.6) + (confidence * 0.4)
        enhanced['signal_strength'] = float(signal_strength)
        
        # Determine signal quality tier
        if signal_strength >= 0.75:
            enhanced['signal_tier'] = 'high'
        elif signal_strength >= 0.60:
            enhanced['signal_tier'] = 'medium'
        else:
            enhanced['signal_tier'] = 'low'
        
        return enhanced
    
    def _get_intraday_insights(self, ticker: str, instrument_key_override: Optional[str] = None) -> Optional[Dict]:
        """Get intraday insights for better signal accuracy"""
        try:
            from src.web.intraday_data_manager import get_intraday_data_manager
            
            intraday_mgr = get_intraday_data_manager()
            
            # Get today's intraday data
            today = datetime.now().date()
            today_str = today.strftime('%Y-%m-%d')
            
            intraday_data = intraday_mgr.get_intraday_data(
                ticker=ticker,
                date=today_str,
                interval='15m',  # 15-minute candles
                instrument_key_override=instrument_key_override
            )
            
            if not intraday_data or len(intraday_data) < 4:
                return None
            
            df = pd.DataFrame(intraday_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            
            # Calculate intraday metrics
            current_price = float(df['close'].iloc[-1])
            open_price = float(df['open'].iloc[0])
            high_price = float(df['high'].max())
            low_price = float(df['low'].min())
            
            # Intraday trend
            price_change_pct = ((current_price - open_price) / open_price) * 100
            
            # Volume trend
            recent_volume = df['volume'].iloc[-4:].mean()
            early_volume = df['volume'].iloc[:4].mean() if len(df) >= 8 else recent_volume
            volume_trend = 'increasing' if recent_volume > early_volume * 1.2 else 'decreasing' if recent_volume < early_volume * 0.8 else 'stable'
            
            # Volatility
            returns = df['close'].pct_change().dropna()
            intraday_volatility = returns.std() * np.sqrt(16)  # Annualized (16 trading hours)
            
            insights = {
                'intraday_change_pct': round(price_change_pct, 2),
                'intraday_high': round(high_price, 2),
                'intraday_low': round(low_price, 2),
                'volume_trend': volume_trend,
                'intraday_volatility': round(intraday_volatility, 4),
                'candles_analyzed': len(df),
                'current_price': round(current_price, 2)
            }
            
            logger.info(f"[Enhanced Signal] Intraday insights for {ticker}: {price_change_pct:+.2f}%, volume: {volume_trend}")
            return insights
            
        except Exception as e:
            logger.debug(f"[Enhanced Signal] Intraday insights failed: {e}")
            return None
    
    def _validate_signal_quality(self, signal: Dict) -> Dict:
        """Validate and filter signals based on quality metrics"""
        validated = signal.copy()
        
        probability = validated.get('probability', 0.5)
        confidence = validated.get('confidence', 0.5)
        signal_strength = validated.get('signal_strength', 0.5)
        
        # Filter out low-quality signals
        if signal_strength < 0.45:
            validated['signal'] = 'HOLD'
            validated['actionable'] = False
            validated['quality_note'] = 'Signal strength too low for trading'
        elif signal_strength >= self.min_confidence_threshold:
            validated['actionable'] = True
            validated['quality_note'] = 'Signal meets quality threshold'
        else:
            validated['actionable'] = False
            validated['quality_note'] = 'Signal below recommended threshold'
        
        # Add confidence-based recommendations
        if validated.get('actionable', False):
            if confidence >= 0.75:
                validated['recommendation'] = 'Strong signal - Consider position sizing'
            elif confidence >= 0.60:
                validated['recommendation'] = 'Moderate signal - Use standard position size'
            else:
                validated['recommendation'] = 'Weak signal - Use smaller position size'
        else:
            validated['recommendation'] = 'Wait for better entry - Signal not actionable'
        
        return validated
    
    def _calculate_signal_quality(self, signal: Dict) -> str:
        """Calculate overall signal quality rating"""
        signal_strength = signal.get('signal_strength', 0.5)
        confidence = signal.get('confidence', 0.5)
        probability = signal.get('probability', 0.5)
        
        # Quality score (0-100)
        quality_score = (signal_strength * 40) + (confidence * 35) + (abs(probability - 0.5) * 50)
        
        if quality_score >= 80:
            return 'excellent'
        elif quality_score >= 65:
            return 'good'
        elif quality_score >= 50:
            return 'fair'
        else:
            return 'poor'
    
    def update_signal_with_live_price(
        self, 
        ticker: str, 
        live_price: float,
        instrument_key_override: Optional[str] = None
    ) -> Dict:
        """
        Update signal with live price for real-time accuracy
        """
        try:
            # Generate signal with live price
            signal = self.generate_signal(
                ticker=ticker,
                use_ensemble=True,
                use_multi_timeframe=True,
                instrument_key_override=instrument_key_override,
                use_live_data=True
            )
            
            # Override with provided live price if different
            if live_price and live_price > 0:
                signal['current_price'] = live_price
                
                # Recalculate levels based on live price
                if 'entry_price' in signal:
                    signal['entry_price'] = live_price
                    signal['entry_level'] = live_price
                
                logger.info(f"[Enhanced Signal] Updated signal for {ticker} with live price: ₹{live_price:.2f}")
            
            return signal
            
        except Exception as e:
            logger.error(f"[Enhanced Signal] Error updating signal with live price: {e}")
            return {'error': str(e), 'ticker': ticker}


# Global instance
_enhanced_signal_generator: Optional[EnhancedSignalGenerator] = None


def get_enhanced_signal_generator() -> EnhancedSignalGenerator:
    """Get global EnhancedSignalGenerator instance"""
    global _enhanced_signal_generator
    if _enhanced_signal_generator is None:
        _enhanced_signal_generator = EnhancedSignalGenerator()
    return _enhanced_signal_generator
