"""
Test signal endpoint with multiple tickers
"""
import requests
import json
import time

BASE_URL = "http://localhost:5000"

print("="*70)
print("Testing Signal Generation Endpoint")
print("="*70)

# Wait for server
print("\nWaiting for server...")
for i in range(10):
    try:
        r = requests.get(f"{BASE_URL}/", timeout=2)
        print("Server is running!")
        break
    except:
        time.sleep(1)
else:
    print("Server not responding!")
    exit(1)

# Test tickers
tickers = ['RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS']

print("\n" + "="*70)
print("Testing Multiple Tickers")
print("="*70)

for ticker in tickers:
    print(f"\nTesting: {ticker}")
    print("-" * 70)
    
    try:
        response = requests.get(f"{BASE_URL}/api/signals/{ticker}", timeout=60)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("[SUCCESS] Signal Generated!")
            print(f"  Ticker: {data.get('ticker')}")
            print(f"  Signal: {data.get('signal')}")
            print(f"  Probability: {data.get('probability', 0):.3f}")
            print(f"  Confidence: {data.get('confidence', 0):.3f}")
            print(f"  Current Price: {data.get('current_price', 0)}")
            print(f"  ELITE System: {data.get('elite_system', False)}")
            print(f"  Model Count: {data.get('model_count', 0)}")
            break  # Success, stop testing
        else:
            error_text = response.text[:300]
            print(f"[ERROR] Status {response.status_code}")
            print(f"  Error: {error_text}")
            
            # Check date range in error
            if '2023-12-20' in error_text or '2024-12-20' in error_text:
                print("  [OK] Dates are correct (2023-12-20 to 2024-12-20)")
                print("  [INFO] Data availability issue (not a date bug)")
            elif '2025-02-05' in error_text or '2026-02-05' in error_text:
                print("  [WARNING] Still using old dates!")
                
    except Exception as e:
        print(f"[EXCEPTION] {e}")

print("\n" + "="*70)
print("Test Complete")
print("="*70)
