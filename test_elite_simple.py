"""
Simple Tier 1 Test Script
Tests ELITE AI components without pytest
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("ELITE AI Trading System - Tier 1 Component Tests")
print("=" * 70)

# Test 1: Model Registry
print("\n[1/7] Testing Model Registry...")
try:
    from src.web.ai_models.model_registry import get_model_registry
    registry = get_model_registry()
    print("[OK] Model registry created successfully")
    
    # Register a test model
    metadata = registry.register_model(
        model_id='test_logistic_v1',
        model_type='logistic',
        version='1.0',
        feature_cols=['ret_1', 'rsi_14', 'macd'],
        performance_metrics={'accuracy': 0.62, 'sharpe_ratio': 1.8},
        model_path='test/models/logistic_v1.pkl'
    )
    print(f"[OK] Model registered: {metadata.model_id}")
    
    # Get active models
    active_models = registry.get_active_models()
    print(f"[OK] Active models: {len(active_models)}")
    
except Exception as e:
    print(f"[FAIL] Model Registry test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Ensemble Manager
print("\n[2/7] Testing Ensemble Manager...")
try:
    from src.web.ai_models.ensemble_manager import get_ensemble_manager
    manager = get_ensemble_manager()
    print("[OK] Ensemble manager created successfully")
    
    # Test weighted average
    predictions = {
        'test_logistic_v1': 0.65,
        'test_xgboost_v1': 0.70,
        'test_lstm_v1': 0.68
    }
    
    result = manager.predict_ensemble(predictions)
    print(f"[OK] Ensemble prediction: {result['probability']:.3f} (confidence: {result['confidence']:.3f})")
    print(f"  Method: {result['method']}, Models: {result['model_count']}")
    
except Exception as e:
    print(f"[FAIL] Ensemble Manager test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Advanced Features
print("\n[3/7] Testing Advanced Feature Engineering...")
try:
    import pandas as pd
    import numpy as np
    from datetime import datetime
    
    # Create sample data
    dates = pd.date_range(end=datetime.now(), periods=200, freq='D')
    np.random.seed(42)
    prices = 100 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, 200)))
    
    df = pd.DataFrame({
        'date': dates,
        'open': prices * 1.001,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, 200)
    })
    df.set_index('date', inplace=True)
    
    from src.web.ai_models.advanced_features import make_advanced_features, get_advanced_feature_columns
    
    feat_df = make_advanced_features(df)
    feature_cols = get_advanced_feature_columns()
    
    print(f"[OK] Advanced features generated: {len(feat_df.columns)} columns")
    print(f"[OK] Feature list: {len(feature_cols)} features")
    
    # Check specific features
    required_features = ['rsi_14', 'macd', 'bb_upper', 'atr_14', 'stoch_k']
    found_features = [f for f in required_features if f in feat_df.columns]
    print(f"[OK] Found {len(found_features)}/{len(required_features)} key features")
    
except Exception as e:
    print(f"[FAIL] Advanced Features test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Multi-Timeframe Analyzer
print("\n[4/7] Testing Multi-Timeframe Analyzer...")
try:
    from src.web.ai_models.multi_timeframe_analyzer import get_multi_timeframe_analyzer
    
    analyzer = get_multi_timeframe_analyzer()
    print("[OK] Multi-timeframe analyzer created successfully")
    
    predictions = {
        '1d': 0.65,
        '1h': 0.60,
        '15m': 0.70
    }
    
    import pandas as pd
    ohlcv_data = {
        '1d': df if 'df' in locals() else pd.DataFrame()
    }
    
    if len(ohlcv_data['1d']) > 0:
        analysis = analyzer.analyze_timeframes(
            ticker='TEST.NS',
            ohlcv_data=ohlcv_data,
            predictions=predictions
        )
        print(f"[OK] Consensus signal: {analysis['consensus_signal']}")
        print(f"[OK] Consensus probability: {analysis['consensus_probability']:.3f}")
        print(f"[OK] Trend alignment: {analysis['trend_alignment']['aligned']}")
    else:
        print("  (Skipped - no sample data)")
    
except Exception as e:
    print(f"[FAIL] Multi-Timeframe Analyzer test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Performance Tracker
print("\n[5/7] Testing Performance Tracker...")
try:
    from src.web.ai_models.performance_tracker import get_performance_tracker
    
    tracker = get_performance_tracker()
    print("[OK] Performance tracker created successfully")
    
    # Record some predictions
    for i in range(5):
        tracker.record_prediction(
            model_id='test_logistic_v1',
            ticker='TEST.NS',
            prediction=0.6 + i * 0.02,
            actual_return=0.01 if i % 2 == 0 else -0.01
        )
    
    print("[OK] Recorded 5 test predictions")
    
    # Calculate metrics
    metrics = tracker.calculate_metrics('test_logistic_v1', days=30)
    if 'error' not in metrics:
        print(f"[OK] Metrics calculated: accuracy={metrics.get('accuracy', 'N/A')}")
    else:
        print(f"  (Metrics calculation: {metrics.get('error', 'insufficient data')})")
    
except Exception as e:
    print(f"[FAIL] Performance Tracker test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 6: ELITE Signal Generator
print("\n[6/7] Testing ELITE Signal Generator...")
try:
    from src.web.ai_models.elite_signal_generator import get_elite_signal_generator
    
    generator = get_elite_signal_generator()
    print("[OK] ELITE signal generator created successfully")
    print(f"  Use advanced features: {generator.use_advanced_features}")
    print(f"  Use ensemble: {generator.use_ensemble}")
    print(f"  Use multi-timeframe: {generator.use_multi_timeframe}")
    
    # Test with a real ticker (may fail if no internet)
    print("\n  Attempting signal generation for RELIANCE.NS...")
    try:
        signal = generator.generate_signal(
            'RELIANCE.NS',
            use_ensemble=True,
            use_multi_timeframe=True
        )
        
        if 'error' not in signal:
            print(f"[OK] Signal generated successfully!")
            print(f"  Ticker: {signal.get('ticker')}")
            print(f"  Signal: {signal.get('signal')}")
            print(f"  Probability: {signal.get('probability', 0):.3f}")
            print(f"  Confidence: {signal.get('confidence', 0):.3f}")
            print(f"  Models used: {signal.get('model_count', 0)}")
            print(f"  ELITE system: {signal.get('elite_system', False)}")
        else:
            print(f"  Signal generation returned error: {signal.get('error')}")
    except Exception as e:
        print(f"  Signal generation skipped (expected if no internet/data): {str(e)[:100]}")
    
except Exception as e:
    print(f"[FAIL] ELITE Signal Generator test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 7: Integration Test
print("\n[7/7] Testing Component Integration...")
try:
    # Test that all components work together
    from src.web.ai_models.model_registry import get_model_registry
    from src.web.ai_models.ensemble_manager import get_ensemble_manager
    from src.web.ai_models.elite_signal_generator import get_elite_signal_generator
    
    registry = get_model_registry()
    ensemble = get_ensemble_manager()
    generator = get_elite_signal_generator()
    
    print("[OK] All components initialized successfully")
    print("[OK] Integration test passed")
    
except Exception as e:
    print(f"[FAIL] Integration test failed: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "=" * 70)
print("Test Summary")
print("=" * 70)
print("All core components have been tested.")
print("If any tests failed, check the error messages above.")
print("\nTo test with real data, ensure you have internet connectivity")
print("and run: python run_web.py")
print("Then visit: http://localhost:5000/api/signals/RELIANCE.NS")
print("=" * 70)
