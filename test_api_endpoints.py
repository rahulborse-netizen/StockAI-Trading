"""
Test ELITE AI API Endpoints
Tests all Tier 1 API endpoints
"""
import requests
import time
import json

BASE_URL = "http://localhost:5000"

def test_endpoint(name, url, method="GET", data=None):
    """Test an API endpoint"""
    print(f"\n{'='*70}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"{'='*70}")
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=30)
        else:
            print(f"[SKIP] Unknown method: {method}")
            return False
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"[OK] Response received")
                print(f"Response (first 500 chars):")
                print(json.dumps(result, indent=2)[:500])
                if len(json.dumps(result)) > 500:
                    print("... (truncated)")
                return True
            except:
                print(f"[OK] Response received (not JSON):")
                print(response.text[:200])
                return True
        else:
            print(f"[FAIL] Status: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"[FAIL] Could not connect to server. Is it running?")
        return False
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False

def main():
    print("="*70)
    print("ELITE AI Trading System - API Endpoint Tests")
    print("="*70)
    print(f"\nWaiting for server to start...")
    time.sleep(3)  # Wait for server to start
    
    # Test server health
    print("\n[1/6] Testing Server Health...")
    test_endpoint("Server Health", f"{BASE_URL}/")
    
    # Test ELITE Signal Generation
    print("\n[2/6] Testing ELITE Signal Generation...")
    test_endpoint(
        "ELITE Signal for RELIANCE.NS",
        f"{BASE_URL}/api/signals/RELIANCE.NS"
    )
    
    # Test Basic Signal (fallback)
    print("\n[3/6] Testing Basic Signal (fallback)...")
    test_endpoint(
        "Basic Signal (elite=false)",
        f"{BASE_URL}/api/signals/RELIANCE.NS?elite=false"
    )
    
    # Test Model Registry
    print("\n[4/6] Testing Model Registry...")
    test_endpoint(
        "List All Models",
        f"{BASE_URL}/api/ai/models"
    )
    
    # Test Model Performance
    print("\n[5/6] Testing Model Performance...")
    test_endpoint(
        "Model Performance (test model)",
        f"{BASE_URL}/api/ai/models/test_logistic_v1/performance?days=30"
    )
    
    # Test Model Rankings
    print("\n[6/6] Testing Model Rankings...")
    test_endpoint(
        "Model Rankings",
        f"{BASE_URL}/api/ai/models/rankings?days=30"
    )
    
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    print("All API endpoints have been tested.")
    print("Check the results above for any failures.")
    print("="*70)

if __name__ == "__main__":
    main()
