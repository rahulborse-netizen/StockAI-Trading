"""
Diagnostic script to test Upstox holdings API
Run this after connecting to Upstox to see what data is being returned
"""
import requests
import json
import sys

BASE_URL = "http://localhost:5000"

def test_holdings():
    print("="*70)
    print("Testing Upstox Holdings API")
    print("="*70)
    print("\nNOTE: This script runs WITHOUT browser cookies/session.")
    print("If the app shows 'Connected' in browser, that's a different session.")
    print("This test checks the server's session state for a NEW request.\n")
    
    # Test 1: Check connection status
    print("\n[1] Checking Upstox connection status...")
    try:
        response = requests.get(f"{BASE_URL}/api/upstox/status", timeout=5)
        status = response.json()
        print(f"  Connected: {status.get('connected', False)}")
        print(f"  Has Token: {status.get('has_token', False)}")
        
        # Show debug info if available
        if 'debug' in status:
            debug = status['debug']
            print(f"\n  Debug Info:")
            print(f"    Has API Key: {debug.get('has_api_key', False)}")
            print(f"    Has API Secret: {debug.get('has_api_secret', False)}")
            print(f"    Has Token: {debug.get('has_token', False)}")
            print(f"    Session Keys: {debug.get('session_keys', [])}")
        
        if not status.get('connected'):
            print("\n  ⚠️  WARNING: Server shows not connected for THIS request.")
            print("  This is normal - the script doesn't have your browser's session cookies.")
            print("  If the browser shows 'Connected', check the browser console instead.")
            print("\n  To test from browser:")
            print("  1. Open browser Developer Tools (F12)")
            print("  2. Go to Console tab")
            print("  3. Type: fetch('/api/holdings').then(r => r.json()).then(console.log)")
            print("  4. This will show holdings data from YOUR browser session")
            return
    except Exception as e:
        print(f"  ERROR: Could not check status: {e}")
        return
    
    # Test 2: Fetch holdings
    print("\n[2] Fetching holdings from /api/holdings...")
    try:
        response = requests.get(f"{BASE_URL}/api/holdings", timeout=10)
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 200:
            holdings = response.json()
            print(f"  Number of holdings: {len(holdings)}")
            
            if len(holdings) > 0:
                print("\n  Sample holding (first one):")
                print(json.dumps(holdings[0], indent=2))
                
                print("\n  All holdings summary:")
                for i, h in enumerate(holdings, 1):
                    print(f"    {i}. {h.get('symbol', 'N/A')}: Qty={h.get('qty', 0)}, LTP={h.get('ltp', 0)}")
            else:
                print("  WARNING: No holdings returned (empty list)")
                print("  This could mean:")
                print("    - You have no holdings in your Upstox account")
                print("    - The API is returning empty data")
                print("    - There's an issue with the API response format")
        else:
            error = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            print(f"  ERROR: {error}")
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*70)
    print("Test complete!")
    print("="*70)

if __name__ == "__main__":
    test_holdings()
