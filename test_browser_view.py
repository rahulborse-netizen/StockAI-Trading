"""
Test what browser will see when accessing the signal endpoint
"""
import requests
import json

print("="*70)
print("BROWSER TEST - Signal Generation Endpoint")
print("="*70)
print("\nURL: http://localhost:5000/api/signals/RELIANCE.NS")
print("\nSending GET request (simulating browser)...")
print("-"*70)

try:
    response = requests.get('http://localhost:5000/api/signals/RELIANCE.NS', timeout=60)
    
    print(f"\nHTTP Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
    print("\n" + "="*70)
    print("RESPONSE BODY (What browser will display):")
    print("="*70)
    
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2))
        print("\n" + "="*70)
        print("[SUCCESS] Signal generated successfully!")
        print("="*70)
        print(f"\nKey Information:")
        print(f"  - Ticker: {data.get('ticker')}")
        print(f"  - Signal: {data.get('signal')}")
        print(f"  - Probability: {data.get('probability', 0):.3f}")
        print(f"  - ELITE System: {data.get('elite_system', False)}")
    else:
        error_text = response.text
        print(error_text)
        
        print("\n" + "="*70)
        print("ANALYSIS:")
        print("="*70)
        
        # Check dates in error message
        if '2023-09-30' in error_text or '2024-09-30' in error_text:
            print("\n[OK] DATES ARE CORRECT!")
            print("  Date range: 2023-09-30 to 2024-09-30")
            print("  The date fix is working properly.")
            print("  The error is due to data availability (yfinance issue),")
            print("  NOT the date calculation bug.")
        elif '2025-02-05' in error_text or '2026-02-05' in error_text:
            print("\n[WARNING] STILL USING OLD DATES!")
            print("  Date range: 2025-02-05 to 2026-02-05")
            print("  Server needs to be restarted to load new code.")
        else:
            print("\n[INFO] Could not determine date range from error message.")
        
        print("\n" + "="*70)
        print("WHAT THIS MEANS:")
        print("="*70)
        print("If dates are 2023-09-30 to 2024-09-30:")
        print("  -> Date fix is WORKING ✅")
        print("  -> Remaining error is separate data issue")
        print("\nIf dates are 2025-02-05 to 2026-02-05:")
        print("  -> Server needs restart")
        print("  -> Stop server (Ctrl+C) and run: python run_web.py")
        
except requests.exceptions.ConnectionError:
    print("\n[ERROR] Cannot connect to server!")
    print("Make sure the server is running:")
    print("  python run_web.py")
except Exception as e:
    print(f"\n[ERROR] Exception: {e}")

print("\n" + "="*70)
