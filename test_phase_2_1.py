"""
Quick test script for Phase 2.1: Real-time Data Integration
Run this to verify the implementation works
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    try:
        from src.web.market_data import MarketDataClient
        print("[OK] MarketDataClient imported")
        
        from src.web.app import app
        print("[OK] Flask app imported")
        
        from src.web.instrument_master import InstrumentMaster
        print("[OK] InstrumentMaster imported")
        
        return True
    except Exception as e:
        print(f"[ERROR] Import error: {e}")
        return False

def test_market_data_client():
    """Test MarketDataClient initialization"""
    print("\nTesting MarketDataClient...")
    try:
        from src.web.market_data import MarketDataClient
        
        # Test with dummy token (won't work, but should initialize)
        client = MarketDataClient("dummy_token")
        print("[OK] MarketDataClient initialized")
        
        # Test parse_quote with sample data
        sample_quote = {
            'ohlc': {'open': 100, 'high': 105, 'low': 98, 'close': 102},
            'last_price': 103,
            'volume': 1000000
        }
        parsed = client.parse_quote(sample_quote)
        assert 'price' in parsed
        assert 'change' in parsed
        assert 'change_pct' in parsed
        print("[OK] parse_quote() works correctly")
        
        return True
    except Exception as e:
        print(f"[ERROR] MarketDataClient test error: {e}")
        return False

def test_app_routes():
    """Test that app routes are registered"""
    print("\nTesting Flask routes...")
    try:
        from src.web.app import app
        
        routes = [r.rule for r in app.url_map.iter_rules() if 'api' in r.rule]
        
        required_routes = ['/api/prices', '/api/market_indices']
        for route in required_routes:
            if route in routes:
                print(f"[OK] Route {route} registered")
            else:
                print(f"[ERROR] Route {route} NOT found")
                return False
        
        return True
    except Exception as e:
        print(f"[ERROR] Route test error: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Phase 2.1 Testing - Real-time Data Integration")
    print("=" * 60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("MarketDataClient", test_market_data_client()))
    results.append(("App Routes", test_app_routes()))
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("[SUCCESS] All tests passed! Phase 2.1 is ready to test in browser.")
        print("\nNext steps:")
        print("1. Start server: python run_web.py")
        print("2. Open browser: http://localhost:5000")
        print("3. Test endpoints in browser console (see TEST_PHASE_2_1.md)")
    else:
        print("[FAILED] Some tests failed. Please fix errors before testing in browser.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
