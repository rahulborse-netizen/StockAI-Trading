"""
Test script to simulate the Upstox connection request and see what errors occur
"""
import sys
import requests
import json
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("Testing Upstox Connection Endpoint")
print("=" * 60)

# Test data (using your actual API key from the image)
test_data = {
    'api_key': 'c4599604-5513-4aea-b256-f725a41bcb11',
    'api_secret': 'bw7zbs2u4e',  # Partial - you'll need full secret
    'redirect_uri': 'http://localhost:5000/callback',
    'access_token': None
}

print("\n[1] Testing server is running...")
try:
    response = requests.get('http://localhost:5000/api/upstox/test', timeout=5)
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")
except Exception as e:
    print(f"  ERROR: {e}")
    print("  Server is not running or not accessible")
    sys.exit(1)

print("\n[2] Testing /api/upstox/connect endpoint...")
try:
    response = requests.post(
        'http://localhost:5000/api/upstox/connect',
        json=test_data,
        headers={'Content-Type': 'application/json'},
        timeout=30
    )
    print(f"  Status Code: {response.status_code}")
    print(f"  Content Type: {response.headers.get('content-type', 'unknown')}")
    
    # Check if response is JSON
    try:
        result = response.json()
        print(f"  Response (JSON):")
        print(json.dumps(result, indent=2))
    except ValueError as e:
        print(f"  ERROR: Response is not JSON!")
        print(f"  Response text (first 500 chars): {response.text[:500]}")
        print(f"  This is the issue - server returned HTML instead of JSON")
        
except requests.exceptions.Timeout:
    print("  ERROR: Request timed out after 30 seconds")
    print("  This matches the timeout error you're seeing in the browser")
except requests.exceptions.ConnectionError as e:
    print(f"  ERROR: Connection error: {e}")
except Exception as e:
    print(f"  ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
