"""
Test signal generation with fixed dates
"""
import requests
import json

print("Testing ELITE Signal Generation with Fixed Dates...")
print("="*70)

# Test the signal endpoint
try:
    response = requests.get('http://localhost:5000/api/signals/RELIANCE.NS', timeout=60)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("\n[SUCCESS] Signal Generated!")
        print(f"Ticker: {data.get('ticker')}")
        print(f"Signal: {data.get('signal')}")
        print(f"Probability: {data.get('probability', 0):.3f}")
        print(f"Confidence: {data.get('confidence', 0):.3f}")
        print(f"Current Price: {data.get('current_price', 0)}")
        print(f"ELITE System: {data.get('elite_system', False)}")
        print(f"Model Count: {data.get('model_count', 0)}")
        if 'model_predictions' in data:
            print(f"Models Used: {list(data['model_predictions'].keys())}")
    else:
        print(f"\n[ERROR] Status {response.status_code}")
        error_text = response.text[:500]
        print(f"Error: {error_text}")
        
        # Check if it's a date issue
        if '2025' in error_text or '2026' in error_text:
            print("\n⚠️  Date issue detected in error message")
            print("The server may need to be restarted to load the fixed code.")
        
except Exception as e:
    print(f"\n[ERROR] Exception: {e}")

print("\n" + "="*70)
