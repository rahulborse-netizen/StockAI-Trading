"""Test signals endpoint to diagnose issues"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.web.app import app

print("=" * 60)
print("Testing /api/signals endpoint")
print("=" * 60)

test_tickers = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS']

with app.test_client() as client:
    for ticker in test_tickers:
        print(f"\nTesting {ticker}...")
        try:
            response = client.get(f'/api/signals/{ticker}')
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.get_json()
                if 'error' in data:
                    print(f"  Error: {data['error']}")
                else:
                    print(f"  Signal: {data.get('signal', 'N/A')}")
                    print(f"  Probability: {data.get('probability', 0):.2%}")
                    print(f"  Current Price: ₹{data.get('current_price', 0):.2f}")
                    print("  ✅ Success!")
            else:
                error_data = response.get_data(as_text=True)
                print(f"  Error Response: {error_data[:200]}")
        except Exception as e:
            print(f"  Exception: {e}")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
