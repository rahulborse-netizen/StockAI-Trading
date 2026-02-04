"""
Quick diagnostic script to check for common connection errors
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("Connection Error Diagnostic")
print("=" * 60)

# Test 1: Check redirect URI validation
print("\n[1] Testing redirect URI validation...")
try:
    from src.web.upstox_connection import connection_manager
    
    test_uris = [
        'http://localhost:5000/callback',
        'https://127.0.0.1:88/stocktrading',  # Wrong format
        'http://localhost:5000/callback',  # Correct
    ]
    
    for uri in test_uris:
        is_valid, msg = connection_manager.validate_redirect_uri(uri)
        status = "OK" if is_valid else "INVALID"
        print(f"  {status}: {uri}")
        if not is_valid:
            print(f"    -> {msg}")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 2: Check UpstoxAPI initialization
print("\n[2] Testing UpstoxAPI initialization...")
try:
    from src.web.upstox_api import UpstoxAPI
    
    api = UpstoxAPI("test_key", "test_secret", "http://localhost:5000/callback")
    auth_url = api.build_authorize_url()
    print(f"  OK: Authorization URL generated")
    print(f"    Preview: {auth_url[:80]}...")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 3: Check app routes
print("\n[3] Testing Flask app routes...")
try:
    from src.web.app import app
    
    routes = [str(r.rule) for r in app.url_map.iter_rules() if 'upstox' in r.rule.lower() or 'callback' in r.rule.lower()]
    print(f"  Found {len(routes)} Upstox-related routes:")
    for route in routes[:5]:
        print(f"    - {route}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n" + "=" * 60)
print("Common Error Scenarios:")
print("=" * 60)
print("1. Redirect URI mismatch:")
print("   - Check: http://localhost:5000/callback in Upstox Portal")
print("   - Must match EXACTLY (including http:// not https://)")
print()
print("2. Invalid API credentials:")
print("   - Verify API Key and Secret from Upstox Portal")
print("   - Make sure app is active (not expired)")
print()
print("3. Network timeout:")
print("   - Check internet connection")
print("   - Try again (may be temporary Upstox API issue)")
print()
print("4. Session expired:")
print("   - Close browser and restart Flask server")
print("   - Try connecting again")
print("=" * 60)
