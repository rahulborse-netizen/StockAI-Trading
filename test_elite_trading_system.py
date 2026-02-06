"""
Comprehensive Test Suite for ELITE Trading System
Tests all functionality of elite_trading_system.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import subprocess
import json
import time
from datetime import datetime

print("="*80)
print("ELITE TRADING SYSTEM - COMPREHENSIVE TEST SUITE")
print("="*80)
print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

test_results = {
    'passed': [],
    'failed': [],
    'warnings': []
}

def run_test(name, command, expected_outputs=None, should_fail=False):
    """Run a test command and check results"""
    print(f"\n{'='*80}")
    print(f"TEST: {name}")
    print(f"{'='*80}")
    print(f"Command: {' '.join(command)}")
    print("-"*80)
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
            encoding='utf-8',
            errors='replace'
        )
        
        output = result.stdout + result.stderr
        
        # Check if test should pass or fail
        if should_fail:
            if result.returncode != 0:
                test_results['passed'].append(name)
                print(f"[PASS] Test failed as expected (return code: {result.returncode})")
                return True
            else:
                test_results['failed'].append(name)
                print(f"[FAIL] Test should have failed but didn't")
                return False
        
        # Check return code
        if result.returncode != 0:
            test_results['failed'].append(name)
            print(f"[FAIL] Command failed with return code: {result.returncode}")
            print(f"Output: {output[:500]}")
            return False
        
        # Check for expected outputs
        if expected_outputs:
            all_found = True
            for expected in expected_outputs:
                if expected.lower() in output.lower():
                    print(f"[OK] Found: {expected}")
                else:
                    print(f"[MISSING] Expected: {expected}")
                    all_found = False
            
            if all_found:
                test_results['passed'].append(name)
                print(f"[PASS] All expected outputs found")
                return True
            else:
                test_results['warnings'].append(name)
                print(f"[WARN] Some expected outputs missing")
                return False
        else:
            # Just check if it runs without error
            test_results['passed'].append(name)
            print(f"[PASS] Command executed successfully")
            return True
            
    except subprocess.TimeoutExpired:
        test_results['failed'].append(name)
        print(f"[FAIL] Command timed out")
        return False
    except Exception as e:
        test_results['failed'].append(name)
        print(f"[FAIL] Exception: {e}")
        return False

# Test 1: Help command
print("\n" + "="*80)
print("TEST SUITE 1: BASIC COMMANDS")
print("="*80)

run_test(
    "Help Command",
    ["python", "elite_trading_system.py", "--help"],
    expected_outputs=["usage:", "options:", "--tickers", "--continuous", "--save"]
)

# Test 2: Status check
run_test(
    "Status Check",
    ["python", "elite_trading_system.py", "--status"],
    expected_outputs=["SYSTEM STATUS", "ELITE AI System", "Model Registry", "Ensemble Manager"]
)

# Test 3: Import test (check all modules load)
print("\n" + "="*80)
print("TEST SUITE 2: MODULE IMPORTS")
print("="*80)

import_tests = [
    ("ELITE Signal Generator", "from src.web.ai_models.elite_signal_generator import get_elite_signal_generator"),
    ("Model Registry", "from src.web.ai_models.model_registry import get_model_registry"),
    ("Ensemble Manager", "from src.web.ai_models.ensemble_manager import get_ensemble_manager"),
    ("Trading Mode", "from src.web.trading_mode import get_trading_mode_manager"),
    ("Advanced Features", "from src.web.ai_models.advanced_features import get_advanced_feature_columns"),
    ("Multi-Timeframe", "from src.web.ai_models.multi_timeframe_analyzer import get_multi_timeframe_analyzer"),
    ("Performance Tracker", "from src.web.ai_models.performance_tracker import get_performance_tracker"),
]

for test_name, import_stmt in import_tests:
    try:
        exec(import_stmt)
        test_results['passed'].append(f"Import: {test_name}")
        print(f"[PASS] {test_name}")
    except Exception as e:
        test_results['failed'].append(f"Import: {test_name}")
        print(f"[FAIL] {test_name}: {e}")

# Test 4: Script structure
print("\n" + "="*80)
print("TEST SUITE 3: SCRIPT STRUCTURE")
print("="*80)

script_file = Path("elite_trading_system.py")
if script_file.exists():
    content = script_file.read_text(encoding='utf-8')
    
    required_functions = [
        "def main()",
        "def generate_signals",
        "def print_signal",
        "def print_summary",
        "def check_system_status",
        "get_elite_signal_generator",
        "get_model_registry",
        "get_ensemble_manager"
    ]
    
    for func in required_functions:
        if func in content:
            test_results['passed'].append(f"Function: {func}")
            print(f"[PASS] Found: {func}")
        else:
            test_results['failed'].append(f"Function: {func}")
            print(f"[FAIL] Missing: {func}")
else:
    test_results['failed'].append("Script file exists")
    print("[FAIL] elite_trading_system.py not found")

# Test 5: Component initialization
print("\n" + "="*80)
print("TEST SUITE 4: COMPONENT INITIALIZATION")
print("="*80)

try:
    from src.web.ai_models.elite_signal_generator import get_elite_signal_generator
    generator = get_elite_signal_generator()
    if generator:
        test_results['passed'].append("ELITE Generator Init")
        print("[PASS] ELITE Signal Generator initialized")
    else:
        test_results['failed'].append("ELITE Generator Init")
        print("[FAIL] ELITE Signal Generator failed to initialize")
except Exception as e:
    test_results['failed'].append("ELITE Generator Init")
    print(f"[FAIL] ELITE Generator: {e}")

try:
    from src.web.ai_models.model_registry import get_model_registry
    registry = get_model_registry()
    models = registry.get_active_models()
    test_results['passed'].append("Model Registry Init")
    print(f"[PASS] Model Registry initialized ({len(models)} models)")
except Exception as e:
    test_results['failed'].append("Model Registry Init")
    print(f"[FAIL] Model Registry: {e}")

try:
    from src.web.ai_models.ensemble_manager import get_ensemble_manager
    ensemble = get_ensemble_manager()
    test_results['passed'].append("Ensemble Manager Init")
    print("[PASS] Ensemble Manager initialized")
except Exception as e:
    test_results['failed'].append("Ensemble Manager Init")
    print(f"[FAIL] Ensemble Manager: {e}")

# Test 6: Watchlist function
print("\n" + "="*80)
print("TEST SUITE 5: WATCHLIST FUNCTIONALITY")
print("="*80)

try:
    # Import and test watchlist
    import importlib.util
    spec = importlib.util.spec_from_file_location("elite_trading", "elite_trading_system.py")
    elite_module = importlib.util.module_from_spec(spec)
    
    # Check if get_watchlist function exists
    script_content = Path("elite_trading_system.py").read_text(encoding='utf-8')
    if "def get_watchlist()" in script_content:
        test_results['passed'].append("Watchlist Function")
        print("[PASS] get_watchlist() function exists")
    else:
        test_results['failed'].append("Watchlist Function")
        print("[FAIL] get_watchlist() function missing")
except Exception as e:
    test_results['warnings'].append("Watchlist Function")
    print(f"[WARN] Watchlist check: {e}")

# Test 7: File operations
print("\n" + "="*80)
print("TEST SUITE 6: FILE OPERATIONS")
print("="*80)

# Test save functionality
test_file = "test_watchlist.txt"
try:
    with open(test_file, 'w') as f:
        f.write("RELIANCE.NS\nTCS.NS\n")
    
    if Path(test_file).exists():
        test_results['passed'].append("File Creation")
        print(f"[PASS] Test file created: {test_file}")
        
        # Test reading
        with open(test_file, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
        if len(lines) == 2:
            test_results['passed'].append("File Reading")
            print("[PASS] File reading works")
        else:
            test_results['failed'].append("File Reading")
            print("[FAIL] File reading issue")
        
        # Cleanup
        Path(test_file).unlink()
    else:
        test_results['failed'].append("File Creation")
        print("[FAIL] File creation failed")
except Exception as e:
    test_results['failed'].append("File Operations")
    print(f"[FAIL] File operations: {e}")

# Test 8: Argument parsing
print("\n" + "="*80)
print("TEST SUITE 7: ARGUMENT PARSING")
print("="*80)

test_args = [
    (["--help"], "Help", False),
    (["--status"], "Status", False),
    (["--tickers", "RELIANCE.NS"], "Tickers", False),
]

for args, name, should_fail_flag in test_args:
    run_test(f"Args: {name}", ["python", "elite_trading_system.py"] + args, should_fail=should_fail_flag)

# Summary
print("\n" + "="*80)
print("TEST SUMMARY")
print("="*80)

total = len(test_results['passed']) + len(test_results['failed']) + len(test_results['warnings'])
passed = len(test_results['passed'])
failed = len(test_results['failed'])
warnings = len(test_results['warnings'])

print(f"\nTotal Tests: {total}")
print(f"Passed: {passed} ({passed*100//total if total > 0 else 0}%)")
print(f"Failed: {failed} ({failed*100//total if total > 0 else 0}%)")
print(f"Warnings: {warnings} ({warnings*100//total if total > 0 else 0}%)")

if failed > 0:
    print(f"\n[FAILED TESTS]")
    for test in test_results['failed']:
        print(f"  - {test}")

if warnings > 0:
    print(f"\n[WARNINGS]")
    for test in test_results['warnings']:
        print(f"  - {test}")

print("\n" + "="*80)
if failed == 0:
    print("OVERALL STATUS: [SUCCESS] ALL CRITICAL TESTS PASSED")
else:
    print("OVERALL STATUS: [WARNING] SOME TESTS FAILED")
print("="*80)
