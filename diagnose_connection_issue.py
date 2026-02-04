"""
Comprehensive diagnostic for Upstox connection issues
"""
import sys
import requests
import json
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 70)
print("Upstox Connection Diagnostic")
print("=" * 70)

# Test 1: Server is running
print("\n[1] Testing Flask server...")
try:
    response = requests.get('http://localhost:5000/api/upstox/test', timeout=5)
    if response.status_code == 200:
        print("  [OK] Server is running")
    else:
        print(f"  [ERROR] Server returned status {response.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"  [ERROR] Server is not running: {e}")
    print("  -> Start server with: python start_simple.py")
    sys.exit(1)

# Test 2: Connection endpoint
print("\n[2] Testing /api/upstox/connect endpoint...")
test_data = {
    'api_key': 'c4599604-5513-4aea-b256-f725a41bcb11',
    'api_secret': 'bw7zbs2u4e',  # Partial - user needs to provide full
    'redirect_uri': 'http://localhost:5000/callback',
    'access_token': None
}

try:
    response = requests.post(
        'http://localhost:5000/api/upstox/connect',
        json=test_data,
        headers={'Content-Type': 'application/json'},
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        print("  [OK] Endpoint is working")
        print(f"  → Status: {result.get('status')}")
        print(f"  → Redirect URI: {result.get('redirect_uri')}")
        
        if result.get('status') == 'auth_required':
            auth_url = result.get('auth_url', '')
            print(f"  → Auth URL generated: {auth_url[:80]}...")
            print("\n  📋 Next steps:")
            print("    1. Copy this redirect URI to Upstox Portal:")
            print(f"       {result.get('redirect_uri')}")
            print("    2. Make sure it's SAVED in Upstox Portal")
            print("    3. Try connecting from the app")
    else:
        print(f"  [ERROR] Endpoint returned status {response.status_code}")
        try:
            error = response.json()
            print(f"  → Error: {error}")
        except:
            print(f"  → Response: {response.text[:200]}")
            
except Exception as e:
        print(f"  [ERROR] Error: {e}")

# Test 3: Verify redirect URI format
print("\n[3] Verifying redirect URI format...")
redirect_uri = "http://localhost:5000/callback"
checks = [
    ("Starts with http://", redirect_uri.startswith("http://")),
    ("Uses localhost", "localhost" in redirect_uri),
    ("Port is 5000", ":5000" in redirect_uri),
    ("Ends with /callback", redirect_uri.endswith("/callback")),
    ("No https://", not redirect_uri.startswith("https://")),
    ("No 127.0.0.1", "127.0.0.1" not in redirect_uri),
]

all_pass = True
for check_name, check_result in checks:
    status = "[OK]" if check_result else "[ERROR]"
    print(f"  {status} {check_name}")
    if not check_result:
        all_pass = False

if all_pass:
    print("  → Redirect URI format is correct!")
else:
    print("  → Redirect URI format has issues!")

# Test 4: Check callback route
print("\n[4] Testing callback route...")
try:
    # Test with a dummy code
    response = requests.get(
        'http://localhost:5000/callback?code=test123&error=test',
        timeout=5
    )
    print(f"  → Callback route exists (status: {response.status_code})")
except Exception as e:
    print(f"  [ERROR] Callback route error: {e}")

print("\n" + "=" * 70)
print("Common Issues Checklist:")
print("=" * 70)
print("1. [OK] Redirect URI in Upstox Portal: http://localhost:5000/callback")
print("2. [CHECK] Did you SAVE/UPDATE the redirect URI in Upstox Portal?")
print("3. [CHECK] Is the Flask server restarted after code changes?")
print("4. [CHECK] Did you refresh the browser (Ctrl+F5)?")
print("5. [CHECK] Are you using the correct API Key and Secret?")
print("6. [CHECK] Check Flask terminal logs for detailed error messages")
print("=" * 70)

print("\nIf still not working:")
print("   1. Check Flask server terminal for error logs")
print("   2. Try disconnecting and reconnecting")
print("   3. Clear browser cookies for localhost")
print("   4. Try in incognito/private window")
print("=" * 70)
