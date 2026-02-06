"""
Test Quantitative Trading Strategies
Quick test script to verify strategy integration
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:5000"

def print_section(title):
    """Print section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def test_available_strategies():
    """Test: Get available strategies"""
    print_section("1. Available Strategies")
    
    try:
        response = requests.get(f"{BASE_URL}/api/strategies/available", timeout=5)
        data = response.json()
        
        print(f"✅ Found {len(data['strategies'])} strategies:")
        for strategy in data['strategies']:
            info = data['details'][strategy]
            active = "⭐ ACTIVE" if info['is_active'] else ""
            print(f"  • {strategy:20s} - {info['name']:30s} {active}")
        
        return True
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to server. Is the Flask app running?")
        print("   Run: python run_web.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_single_strategy():
    """Test: Execute single strategy"""
    print_section("2. Test Single Strategy (Momentum)")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/strategies/execute",
            json={"ticker": "RELIANCE.NS", "strategy": "momentum"},
            timeout=10
        )
        result = response.json()
        
        if result.get('status') == 'success':
            print(f"✅ Strategy Signal for {result['ticker']}:")
            print(f"   Signal:     {result['signal']} 📊")
            print(f"   Confidence: {result['confidence']:.1%}")
            print(f"   Entry:      ₹{result['entry_price']:.2f}")
            print(f"   Stop Loss:  ₹{result['stop_loss']:.2f}")
            print(f"   Target 1:   ₹{result['target_1']:.2f}")
            print(f"   Target 2:   ₹{result['target_2']:.2f}")
            print(f"\n   Metadata:")
            for key, value in result['metadata'].items():
                if key != 'individual_strategies':
                    print(f"     {key}: {value}")
            return True
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_all_strategies():
    """Test: Compare all strategies"""
    print_section("3. Compare All Strategies")
    
    tickers = ["RELIANCE.NS", "TCS.NS", "INFY.NS"]
    strategies = ["ml", "mean_reversion", "momentum"]
    
    print(f"{'Ticker':<15} {'ML':<10} {'Mean Rev':<12} {'Momentum':<12}")
    print("-" * 50)
    
    for ticker in tickers:
        signals = [ticker[:12]]
        
        for strategy in strategies:
            try:
                response = requests.post(
                    f"{BASE_URL}/api/strategies/execute",
                    json={"ticker": ticker, "strategy": strategy},
                    timeout=10
                )
                result = response.json()
                
                if result.get('status') == 'success':
                    signal = result['signal']
                    confidence = result['confidence']
                    
                    # Format signal with emoji
                    if signal == 'BUY':
                        display = f"🟢 {signal} ({confidence:.0%})"
                    elif signal == 'SELL':
                        display = f"🔴 {signal} ({confidence:.0%})"
                    else:
                        display = f"⚪ {signal} ({confidence:.0%})"
                    
                    signals.append(display)
                else:
                    signals.append("❌ Error")
            except Exception as e:
                signals.append("⏸️ Timeout")
        
        print(f"{signals[0]:<15} {signals[1] if len(signals) > 1 else 'N/A':<10} " +
              f"{signals[2] if len(signals) > 2 else 'N/A':<12} " +
              f"{signals[3] if len(signals) > 3 else 'N/A':<12}")
    
    return True

def test_ensemble():
    """Test: Ensemble strategy"""
    print_section("4. Test Ensemble Strategy")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/strategies/execute",
            json={
                "ticker": "RELIANCE.NS",
                "method": "ensemble",
                "ensemble_method": "weighted_average"
            },
            timeout=10
        )
        result = response.json()
        
        if result.get('status') == 'success':
            print(f"✅ Ensemble Signal for {result['ticker']}:")
            print(f"   Signal:     {result['signal']} 🎯")
            print(f"   Confidence: {result['confidence']:.1%}")
            print(f"   Entry:      ₹{result['entry_price']:.2f}")
            print(f"   Stop Loss:  ₹{result['stop_loss']:.2f}")
            print(f"   Target 1:   ₹{result['target_1']:.2f}")
            print(f"   Target 2:   ₹{result['target_2']:.2f}")
            
            print(f"\n   Individual Strategies:")
            if 'individual_strategies' in result['metadata']:
                for strategy, data in result['metadata']['individual_strategies'].items():
                    print(f"     {strategy:15s}: {data['signal']:5s} ({data['confidence']:.1%})")
            
            return True
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_set_active_strategy():
    """Test: Set active strategy"""
    print_section("5. Set Active Strategy")
    
    try:
        # Set to momentum
        response = requests.post(
            f"{BASE_URL}/api/strategies/set_active",
            json={"strategy": "momentum"},
            timeout=5
        )
        result = response.json()
        
        if result.get('status') == 'success':
            print(f"✅ {result['message']}")
            
            # Set back to ml
            response = requests.post(
                f"{BASE_URL}/api/strategies/set_active",
                json={"strategy": "ml"},
                timeout=5
            )
            result = response.json()
            print(f"✅ {result['message']}")
            return True
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("  🚀 QUANTITATIVE STRATEGIES TEST SUITE")
    print("="*70)
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Server: {BASE_URL}")
    
    # Run tests
    tests = [
        test_available_strategies,
        test_single_strategy,
        test_all_strategies,
        test_ensemble,
        test_set_active_strategy
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except KeyboardInterrupt:
            print("\n\n⚠️ Test interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            results.append(False)
    
    # Summary
    print_section("Test Summary")
    passed = sum(1 for r in results if r)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All tests passed! Your quant strategies are working perfectly! 🎉")
    elif passed > 0:
        print(f"\n⚠️ Some tests failed. Check the errors above.")
    else:
        print("\n❌ All tests failed. Make sure:")
        print("   1. Flask app is running (python run_web.py)")
        print("   2. Strategies are properly installed")
        print("   3. Server is accessible at", BASE_URL)
    
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    main()
