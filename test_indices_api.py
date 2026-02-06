"""Quick test for market indices API"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.web.app import app

print("=" * 60)
print("Testing /api/market-indices endpoint")
print("=" * 60)

with app.test_client() as client:
    response = client.get('/api/market-indices')
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.get_json()
        print(f"\nResponse Keys: {list(data.keys())}")
        
        for key, value in data.items():
            if isinstance(value, dict):
                print(f"\n{key.upper()}:")
                for k, v in value.items():
                    if isinstance(v, float):
                        print(f"  {k}: {v:.2f}")
                    else:
                        print(f"  {k}: {v}")
        print("\n[SUCCESS] API endpoint is working!")
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(response.get_data(as_text=True))
