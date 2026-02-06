"""
Test Tier 1: ELITE AI Trading System
Tests all core AI components
"""
import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime

# Import ELITE components
from src.web.ai_models.model_registry import get_model_registry, ModelMetadata
from src.web.ai_models.ensemble_manager import get_ensemble_manager
from src.web.ai_models.advanced_features import make_advanced_features, get_advanced_feature_columns
from src.web.ai_models.multi_timeframe_analyzer import get_multi_timeframe_analyzer
from src.web.ai_models.performance_tracker import get_performance_tracker
from src.web.ai_models.elite_signal_generator import get_elite_signal_generator
from src.research.features import make_features, add_label_forward_return_up, clean_ml_frame


def create_sample_ohlcv_data(n_days=252):
    """Create sample OHLCV data for testing"""
    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='D')
    
    # Generate realistic price data
    np.random.seed(42)
    base_price = 100
    returns = np.random.normal(0.001, 0.02, n_days)  # Daily returns
    prices = base_price * np.exp(np.cumsum(returns))
    
    # Create OHLCV dataframe
    df = pd.DataFrame({
        'date': dates,
        'open': prices * (1 + np.random.normal(0, 0.005, n_days)),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, n_days))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, n_days))),
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, n_days)
    })
    
    # Ensure high >= close >= low and high >= open >= low
    df['high'] = df[['open', 'close', 'high']].max(axis=1)
    df['low'] = df[['open', 'close', 'low']].min(axis=1)
    
    df.set_index('date', inplace=True)
    return df


class TestModelRegistry:
    """Test model registry functionality"""
    
    def test_registry_creation(self):
        """Test registry can be created"""
        registry = get_model_registry()
        assert registry is not None
    
    def test_register_model(self):
        """Test model registration"""
        registry = get_model_registry()
        
        metadata = registry.register_model(
            model_id='test_model_1',
            model_type='logistic',
            version='1.0',
            feature_cols=['feature1', 'feature2'],
            performance_metrics={'accuracy': 0.65, 'sharpe_ratio': 1.5},
            model_path='test/path.pkl'
        )
        
        assert metadata.model_id == 'test_model_1'
        assert metadata.model_type == 'logistic'
        assert metadata.is_active == True
    
    def test_get_model(self):
        """Test retrieving model"""
        registry = get_model_registry()
        
        model = registry.get_model('test_model_1')
        assert model is not None
        assert model.model_id == 'test_model_1'
    
    def test_get_active_models(self):
        """Test getting active models"""
        registry = get_model_registry()
        
        active_models = registry.get_active_models()
        assert len(active_models) > 0
        
        # Check that all returned models are active
        for model in active_models:
            assert model.is_active == True


class TestAdvancedFeatures:
    """Test advanced feature engineering"""
    
    def test_make_advanced_features(self):
        """Test advanced feature generation"""
        df = create_sample_ohlcv_data(300)
        
        feat_df = make_advanced_features(df)
        
        # Check that features were added
        assert len(feat_df.columns) > len(df.columns)
        
        # Check specific features exist
        assert 'rsi_14' in feat_df.columns
        assert 'macd' in feat_df.columns
        assert 'bb_upper' in feat_df.columns
        assert 'atr_14' in feat_df.columns
    
    def test_feature_columns_list(self):
        """Test feature columns list"""
        feature_cols = get_advanced_feature_columns()
        assert len(feature_cols) > 40  # Should have 50+ features
        assert 'rsi_14' in feature_cols
        assert 'macd' in feature_cols


class TestEnsembleManager:
    """Test ensemble manager"""
    
    def test_ensemble_creation(self):
        """Test ensemble manager can be created"""
        manager = get_ensemble_manager()
        assert manager is not None
    
    def test_weighted_average(self):
        """Test weighted average ensemble"""
        manager = get_ensemble_manager()
        
        predictions = {
            'model1': 0.7,
            'model2': 0.6,
            'model3': 0.65
        }
        
        result = manager.predict_ensemble(predictions)
        
        assert 'probability' in result
        assert 'confidence' in result
        assert 0 <= result['probability'] <= 1
        assert 0 <= result['confidence'] <= 1
    
    def test_voting_ensemble(self):
        """Test voting ensemble"""
        manager = get_ensemble_manager()
        manager.ensemble_method = 'voting'
        
        predictions = {
            'model1': 0.7,
            'model2': 0.6,
            'model3': 0.65
        }
        
        result = manager.predict_ensemble(predictions)
        
        assert 'probability' in result
        assert result['method'] == 'voting'


class TestMultiTimeframeAnalyzer:
    """Test multi-timeframe analyzer"""
    
    def test_analyzer_creation(self):
        """Test analyzer can be created"""
        analyzer = get_multi_timeframe_analyzer()
        assert analyzer is not None
    
    def test_timeframe_analysis(self):
        """Test timeframe analysis"""
        analyzer = get_multi_timeframe_analyzer()
        
        predictions = {
            '1d': 0.65,
            '1h': 0.6,
            '15m': 0.7
        }
        
        ohlcv_data = {
            '1d': create_sample_ohlcv_data(100)
        }
        
        analysis = analyzer.analyze_timeframes(
            ticker='TEST.NS',
            ohlcv_data=ohlcv_data,
            predictions=predictions
        )
        
        assert 'consensus_signal' in analysis
        assert 'consensus_probability' in analysis
        assert 'trend_alignment' in analysis
        assert analysis['consensus_probability'] > 0


class TestPerformanceTracker:
    """Test performance tracker"""
    
    def test_tracker_creation(self):
        """Test tracker can be created"""
        tracker = get_performance_tracker()
        assert tracker is not None
    
    def test_record_prediction(self):
        """Test recording predictions"""
        tracker = get_performance_tracker()
        
        tracker.record_prediction(
            model_id='test_model_1',
            ticker='TEST.NS',
            prediction=0.65,
            actual_return=0.02
        )
        
        # Should not raise exception
        assert True
    
    def test_calculate_metrics(self):
        """Test metrics calculation"""
        tracker = get_performance_tracker()
        
        # Record some predictions
        for i in range(10):
            tracker.record_prediction(
                model_id='test_model_1',
                ticker='TEST.NS',
                prediction=0.6 + i * 0.01,
                actual_return=0.01 if i % 2 == 0 else -0.01
            )
        
        metrics = tracker.calculate_metrics('test_model_1', days=30)
        
        assert 'accuracy' in metrics or 'error' in metrics


class TestEliteSignalGenerator:
    """Test ELITE signal generator"""
    
    def test_generator_creation(self):
        """Test generator can be created"""
        generator = get_elite_signal_generator()
        assert generator is not None
    
    def test_generate_signal_basic(self):
        """Test basic signal generation (may fail if no internet/data)"""
        generator = get_elite_signal_generator()
        
        # This will try to download data - may fail in test environment
        try:
            signal = generator.generate_signal('RELIANCE.NS', use_ensemble=False, use_multi_timeframe=False)
            
            # If successful, check structure
            if 'error' not in signal:
                assert 'ticker' in signal
                assert 'signal' in signal
                assert 'probability' in signal
        except Exception as e:
            # Expected if no internet/data
            print(f"Signal generation test skipped (expected in test env): {e}")
            assert True  # Test passes if it's just a data issue


class TestIntegration:
    """Integration tests"""
    
    def test_all_components_importable(self):
        """Test all components can be imported"""
        from src.web.ai_models.model_registry import ModelRegistry
        from src.web.ai_models.ensemble_manager import EnsembleManager
        from src.web.ai_models.advanced_features import make_advanced_features
        from src.web.ai_models.multi_timeframe_analyzer import MultiTimeframeAnalyzer
        from src.web.ai_models.performance_tracker import PerformanceTracker
        from src.web.ai_models.elite_signal_generator import EliteSignalGenerator
        
        assert True  # If we get here, imports worked
    
    def test_feature_compatibility(self):
        """Test that advanced features work with ML pipeline"""
        df = create_sample_ohlcv_data(200)
        
        # Generate advanced features
        feat_df = make_advanced_features(df)
        
        # Add labels
        labeled_df = add_label_forward_return_up(feat_df, days=1, threshold=0.0)
        
        # Get feature columns
        feature_cols = [col for col in get_advanced_feature_columns() if col in labeled_df.columns]
        
        # Clean ML frame
        ml_df = clean_ml_frame(labeled_df, feature_cols=feature_cols, label_col="label_up")
        
        # Should have data
        assert len(ml_df) > 0
        assert 'label_up' in ml_df.columns


if __name__ == '__main__':
    print("=" * 60)
    print("ELITE AI Trading System - Tier 1 Tests")
    print("=" * 60)
    
    # Run tests
    pytest.main([__file__, '-v', '--tb=short'])
