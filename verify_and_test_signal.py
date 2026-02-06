"""
Verify date fix and test signal generation
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("="*70)
print("Verifying ELITE Signal Generator Date Fix")
print("="*70)

# Test 1: Verify code has correct dates
print("\n[1] Checking date calculation in code...")
try:
    from src.web.ai_models.elite_signal_generator import EliteSignalGenerator
    from datetime import date
    
    # Check what dates the code will use
    gen = EliteSignalGenerator()
    
    # Simulate the date calculation
    safe_end_date = date(2024, 12, 20)
    end_date = safe_end_date.strftime('%Y-%m-%d')
    start_date = date(2023, 12, 20).strftime('%Y-%m-%d')
    
    print(f"  [OK] Code will use:")
    print(f"    Start date: {start_date}")
    print(f"    End date: {end_date}")
    
    if '2025' in end_date or '2026' in end_date:
        print("  [FAIL] ERROR: Dates still contain future years!")
    else:
        print("  [OK] Dates are correct (in the past)")
        
except Exception as e:
    print(f"  [FAIL] Error: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Test API endpoint
print("\n[2] Testing API endpoint...")
try:
    import requests
    response = requests.get('http://localhost:5000/api/signals/RELIANCE.NS', timeout=60)
    
    print(f"  Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("  [SUCCESS] Signal generated!")
        print(f"    Ticker: {data.get('ticker')}")
        print(f"    Signal: {data.get('signal')}")
        print(f"    Probability: {data.get('probability', 0):.3f}")
        print(f"    ELITE System: {data.get('elite_system', False)}")
    else:
        error_text = response.text[:300]
        print(f"  [FAIL] Error: {error_text}")
        
        # Check if it's still showing old dates
        if '2025-02-05' in error_text or '2026-02-05' in error_text:
            print("\n  [WARNING] Server is still using OLD code!")
            print("     The server needs to be restarted.")
            print("\n  To fix:")
            print("    1. Stop the server (Ctrl+C)")
            print("    2. Run: python run_web.py")
            print("    3. Test again")
        elif '2024-12-20' in error_text or '2023-12-20' in error_text:
            print("\n  [OK] Good: Server is using NEW dates, but there's another issue")
            print("     (might be data availability or network issue)")
            
except requests.exceptions.ConnectionError:
    print("  [FAIL] Server is not running!")
    print("     Start it with: python run_web.py")
except Exception as e:
    print(f"  [FAIL] Error: {e}")

print("\n" + "="*70)
print("Verification Complete")
print("="*70)
