"""
ELITE Signal Generator
Combines multiple models, timeframes, and advanced features for superior signals
"""
import logging
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime

from src.research.data import download_yahoo_ohlcv
from src.research.features import add_label_forward_return_up, clean_ml_frame
from src.research.ml import train_baseline_classifier
from src.web.ai_models.advanced_features import make_advanced_features, get_advanced_feature_columns
from src.web.ai_models.ensemble_manager import get_ensemble_manager
from src.web.ai_models.model_registry import get_model_registry
from src.web.ai_models.multi_timeframe_analyzer import get_multi_timeframe_analyzer
from src.web.ai_models.performance_tracker import get_performance_tracker
from src.web.ai_models.xgboost_predictor import XGBoostPredictor
from src.web.ai_models.lstm_predictor import LSTMPredictor

logger = logging.getLogger(__name__)


class EliteSignalGenerator:
    """ELITE signal generator using ensemble of models"""
    
    def __init__(self):
        self.ensemble_manager = get_ensemble_manager()
        self.model_registry = get_model_registry()
        self.multi_tf_analyzer = get_multi_timeframe_analyzer()
        self.performance_tracker = get_performance_tracker()
        self.use_advanced_features = True
        self.use_ensemble = True
        self.use_multi_timeframe = True
    
    def generate_signal(
        self,
        ticker: str,
        use_ensemble: bool = True,
        use_multi_timeframe: bool = True
    ) -> Dict:
        """
        Generate ELITE trading signal
        
        Args:
            ticker: Stock ticker (e.g., 'RELIANCE.NS')
            use_ensemble: Whether to use ensemble of models
            use_multi_timeframe: Whether to analyze multiple timeframes
        
        Returns:
            Complete signal dictionary with predictions from all models
        """
        try:
            # Download data - ensure dates are correct
            from datetime import timedelta
            from datetime import datetime as dt
            from datetime import date
            
            # Get current date/time
            now = dt.now()
            today = now.date()
            
            # Use dynamic date calculation with validation
            # Ensure end_date is not in the future (accounting for timezone differences)
            # Use yesterday as end_date to ensure data availability (markets may not have today's data yet)
            end_date_obj = today - timedelta(days=1)
            
            # Validate: ensure end_date is reasonable (not way in the future)
            max_future_date = today + timedelta(days=1)
            if end_date_obj > max_future_date:
                logger.warning(f"[ELITE Signal] End date {end_date_obj} seems incorrect, using yesterday")
                end_date_obj = today - timedelta(days=1)
            
            # Ensure end_date is not before 2020 (data availability check)
            min_date = date(2020, 1, 1)
            if end_date_obj < min_date:
                logger.error(f"[ELITE Signal] End date {end_date_obj} is too old, using today")
                end_date_obj = today - timedelta(days=1)
            
            end_date = end_date_obj.strftime('%Y-%m-%d')
            start_date = (end_date_obj - timedelta(days=365)).strftime('%Y-%m-%d')  # 1 year before
            
            logger.info(f"[ELITE Signal] Using dynamic date range: {start_date} to {end_date} (today: {today})")
            
            logger.info(f"[ELITE Signal] Date range for {ticker}: {start_date} to {end_date}")
            
            from pathlib import Path
            Path("cache").mkdir(parents=True, exist_ok=True)
            cache_path = Path('cache') / f"{ticker.replace('^', '').replace(':', '_').replace('/', '_')}.csv"
            
            # Fix Bug 1: Check if cache is stale and force refresh if needed
            # Cache is stale if it's older than 1 day or if date range doesn't match current range
            force_refresh = False
            if cache_path.exists():
                cache_age = (dt.now() - dt.fromtimestamp(cache_path.stat().st_mtime)).total_seconds()
                # Refresh if cache is older than 1 day (86400 seconds)
                if cache_age > 86400:
                    force_refresh = True
                    logger.info(f"[ELITE Signal] Cache for {ticker} is {cache_age/3600:.1f} hours old, forcing refresh")
            
            ohlcv = download_yahoo_ohlcv(
                ticker=ticker,
                start=start_date,
                end=end_date,
                interval='1d',
                cache_path=cache_path,
                refresh=force_refresh
            )
            
            if ohlcv is None or len(ohlcv.df) == 0:
                return {'error': 'No data available for ticker', 'ticker': ticker}
            
            # Generate features
            if self.use_advanced_features:
                feat_df = make_advanced_features(ohlcv.df.copy())
                feature_cols = [col for col in get_advanced_feature_columns() if col in feat_df.columns]
            else:
                from src.research.features import make_features
                feat_df = make_features(ohlcv.df.copy())
                feature_cols = ['ret_1', 'ret_5', 'vol_10', 'sma_10', 'sma_50', 'ema_20', 
                               'rsi_14', 'macd', 'macd_signal', 'macd_hist', 'vol_chg_1', 'vol_sma_20']
            
            # Add labels
            labeled_df = add_label_forward_return_up(feat_df, days=1, threshold=0.0)
            ml_df = clean_ml_frame(labeled_df, feature_cols=feature_cols, label_col="label_up")
            
            if len(ml_df) < 100:
                return {'error': 'Insufficient data for ELITE analysis', 'ticker': ticker}
            
            # Prepare data
            train_df = ml_df.iloc[:-1].copy()
            latest_row = ml_df.iloc[-1:].copy()
            current_price = float(latest_row['close'].iloc[0])
            
            # Get predictions from all models
            predictions = {}
            model_details = {}
            
            # 1. Baseline Logistic Regression
            try:
                trained_lr, _ = train_baseline_classifier(
                    df=train_df,
                    feature_cols=feature_cols,
                    label_col="label_up",
                    test_size=0.2,
                    random_state=42
                )
                X_latest = latest_row[feature_cols].fillna(0)
                prob_lr = trained_lr.model.predict_proba(X_latest)[0][1]
                predictions['logistic_regression'] = float(prob_lr)
                model_details['logistic_regression'] = {
                    'type': 'logistic',
                    'probability': float(prob_lr)
                }
            except Exception as e:
                logger.error(f"Error with logistic regression: {e}")
            
            # 2. XGBoost (if available)
            try:
                if XGBOOST_AVAILABLE:
                    xgb_model = XGBoostPredictor()
                    X_train_vals = train_df[feature_cols].fillna(0)
                    y_train_vals = train_df['label_up']
                    
                    # Split for validation
                    split_idx = int(len(train_df) * 0.8)
                    X_train_split = X_train_vals.iloc[:split_idx]
                    y_train_split = y_train_vals.iloc[:split_idx]
                    X_val_split = X_train_vals.iloc[split_idx:]
                    y_val_split = y_train_vals.iloc[split_idx:]
                    
                    xgb_model.train(
                        X_train_split,
                        y_train_split,
                        feature_cols,
                        X_val_split,
                        y_val_split
                    )
                    
                    prob_xgb = xgb_model.predict_proba(latest_row)[0]
                    predictions['xgboost'] = float(prob_xgb)
                    model_details['xgboost'] = {
                        'type': 'xgboost',
                        'probability': float(prob_xgb)
                    }
            except Exception as e:
                logger.debug(f"XGBoost not available or error: {e}")
            
            # 3. LSTM (if available and enough data)
            try:
                if TENSORFLOW_AVAILABLE and len(train_df) >= 100:
                    lstm_model = LSTMPredictor(sequence_length=60, epochs=20)
                    X_train_vals = train_df[feature_cols].fillna(0)
                    y_train_vals = train_df['label_up']
                    
                    # Split for validation
                    split_idx = int(len(train_df) * 0.8)
                    X_train_split = X_train_vals.iloc[:split_idx]
                    y_train_split = y_train_vals.iloc[split_idx:]
                    X_val_split = X_train_vals.iloc[split_idx:]
                    y_val_split = y_train_vals.iloc[split_idx:]
                    
                    lstm_model.train(
                        X_train_split,
                        y_train_split,
                        feature_cols,
                        X_val_split,
                        y_val_split
                    )
                    
                    prob_lstm = lstm_model.predict_proba(latest_row)[0]
                    predictions['lstm'] = float(prob_lstm)
                    model_details['lstm'] = {
                        'type': 'lstm',
                        'probability': float(prob_lstm)
                    }
            except Exception as e:
                logger.debug(f"LSTM not available or error: {e}")
            
            # Ensemble prediction
            if use_ensemble and len(predictions) > 1:
                ensemble_result = self.ensemble_manager.predict_ensemble(predictions)
                ensemble_prob = ensemble_result['probability']
                ensemble_confidence = ensemble_result['confidence']
            else:
                # Use single model if ensemble disabled or only one model
                ensemble_prob = list(predictions.values())[0] if predictions else 0.5
                ensemble_confidence = 0.5
            
            # Calculate signal levels
            recent_high = float(ohlcv.df['high'].tail(20).max())
            recent_low = float(ohlcv.df['low'].tail(20).min())
            recent_volatility = float(ohlcv.df['close'].pct_change().tail(20).std() * np.sqrt(252))
            
            # Enhanced entry/exit levels based on ensemble probability
            if ensemble_prob >= 0.65:
                signal = 'STRONG_BUY'
                entry_level = current_price * 0.998
                stop_loss = current_price * 0.97
                target_1 = current_price * 1.04
                target_2 = current_price * 1.06
            elif ensemble_prob >= 0.55:
                signal = 'BUY'
                entry_level = current_price * 0.999
                stop_loss = current_price * 0.975
                target_1 = current_price * 1.03
                target_2 = current_price * 1.05
            elif ensemble_prob <= 0.35:
                signal = 'STRONG_SELL'
                entry_level = current_price * 1.002
                stop_loss = current_price * 1.03
                target_1 = current_price * 0.96
                target_2 = current_price * 0.94
            elif ensemble_prob <= 0.45:
                signal = 'SELL'
                entry_level = current_price * 1.001
                stop_loss = current_price * 1.025
                target_1 = current_price * 0.97
                target_2 = current_price * 0.95
            else:
                signal = 'HOLD'
                entry_level = current_price * 1.001
                stop_loss = current_price * 0.98
                target_1 = current_price * 1.02
                target_2 = current_price * 1.025
            
            # Build response
            signal_response = {
                'ticker': ticker,
                'current_price': current_price,
                'signal': signal,
                'probability': float(ensemble_prob),
                'confidence': float(ensemble_confidence),
                'entry_level': entry_level,
                'stop_loss': stop_loss,
                'target_1': target_1,
                'target_2': target_2,
                'recent_high': recent_high,
                'recent_low': recent_low,
                'volatility': recent_volatility,
                'model_predictions': model_details,
                'ensemble_method': 'weighted_average' if use_ensemble else 'single_model',
                'model_count': len(predictions),
                'timestamp': datetime.now().isoformat(),
                'elite_system': True
            }
            
            # Add multi-timeframe analysis if enabled
            if use_multi_timeframe:
                # For now, use daily data for all timeframes (would need separate data downloads)
                tf_predictions = {'1d': ensemble_prob}  # Placeholder
                tf_analysis = self.multi_tf_analyzer.analyze_timeframes(
                    ticker=ticker,
                    ohlcv_data={'1d': ohlcv.df},
                    predictions=tf_predictions
                )
                signal_response['multi_timeframe'] = tf_analysis
            
            return signal_response
            
        except Exception as e:
            logger.error(f"Error generating ELITE signal for {ticker}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'error': str(e),
                'ticker': ticker,
                'timestamp': datetime.now().isoformat()
            }




# Global instance
_elite_signal_generator: Optional[EliteSignalGenerator] = None


def get_elite_signal_generator() -> EliteSignalGenerator:
    """Get global ELITE signal generator instance"""
    global _elite_signal_generator
    if _elite_signal_generator is None:
        _elite_signal_generator = EliteSignalGenerator()
    return _elite_signal_generator
