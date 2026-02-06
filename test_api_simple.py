"""
Simple API Test - Tests ELITE AI endpoints
"""
import requests
import time
import json

BASE_URL = "http://localhost:5000"

print("="*70)
print("ELITE AI Trading System - API Endpoint Tests")
print("="*70)

# Wait for server
print("\nWaiting for server to start (10 seconds)...")
for i in range(10):
    try:
        response = requests.get(f"{BASE_URL}/", timeout=2)
        print(f"[OK] Server is running!")
        break
    except:
        print(f"  Waiting... ({i+1}/10)")
        time.sleep(1)
else:
    print("[FAIL] Server not responding. Please start it manually:")
    print("  python run_web.py")
    exit(1)

# Test 1: ELITE Signal
print("\n" + "="*70)
print("Test 1: ELITE Signal Generation")
print("="*70)
try:
    response = requests.get(f"{BASE_URL}/api/signals/RELIANCE.NS", timeout=30)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"[OK] Signal generated!")
        print(f"  Ticker: {data.get('ticker')}")
        print(f"  Signal: {data.get('signal')}")
        print(f"  Probability: {data.get('probability', 0):.3f}")
        print(f"  Confidence: {data.get('confidence', 0):.3f}")
        print(f"  ELITE System: {data.get('elite_system', False)}")
        print(f"  Model Count: {data.get('model_count', 0)}")
        if 'model_predictions' in data:
            print(f"  Model Predictions: {list(data['model_predictions'].keys())}")
    else:
        print(f"[FAIL] Status {response.status_code}: {response.text[:200]}")
except Exception as e:
    print(f"[FAIL] Error: {e}")

# Test 2: Model Registry
print("\n" + "="*70)
print("Test 2: Model Registry")
print("="*70)
try:
    response = requests.get(f"{BASE_URL}/api/ai/models", timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"[OK] Models retrieved!")
        print(f"  Model Count: {data.get('count', 0)}")
        if data.get('models'):
            for model in data['models'][:3]:  # Show first 3
                print(f"  - {model.get('model_id')} ({model.get('model_type')})")
    else:
        print(f"[FAIL] Status {response.status_code}: {response.text[:200]}")
except Exception as e:
    print(f"[FAIL] Error: {e}")

# Test 3: Model Performance
print("\n" + "="*70)
print("Test 3: Model Performance")
print("="*70)
try:
    response = requests.get(f"{BASE_URL}/api/ai/models/test_logistic_v1/performance?days=30", timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        if 'error' not in data:
            print(f"[OK] Performance metrics retrieved!")
            print(f"  Accuracy: {data.get('accuracy', 'N/A')}")
            print(f"  Win Rate: {data.get('win_rate', 'N/A')}")
            print(f"  Sharpe Ratio: {data.get('sharpe_ratio', 'N/A')}")
        else:
            print(f"  Info: {data.get('error', 'No data')}")
    else:
        print(f"[FAIL] Status {response.status_code}: {response.text[:200]}")
except Exception as e:
    print(f"[FAIL] Error: {e}")

# Test 4: Model Rankings
print("\n" + "="*70)
print("Test 4: Model Rankings")
print("="*70)
try:
    response = requests.get(f"{BASE_URL}/api/ai/models/rankings?days=30", timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"[OK] Rankings retrieved!")
        rankings = data.get('rankings', [])
        print(f"  Total Models Ranked: {len(rankings)}")
        for i, model in enumerate(rankings[:5], 1):  # Show top 5
            print(f"  {i}. {model.get('model_id')} - Accuracy: {model.get('accuracy', 'N/A')}")
    else:
        print(f"[FAIL] Status {response.status_code}: {response.text[:200]}")
except Exception as e:
    print(f"[FAIL] Error: {e}")

print("\n" + "="*70)
print("Test Complete!")
print("="*70)
