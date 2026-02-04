"""
Simple startup script for web interface
Run this from the project root directory
"""
import sys
import os
from pathlib import Path

# Get the project root directory (where this file is located)
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Change to project root directory
os.chdir(project_root)

print("="*60)
print("AI Trading Dashboard")
print("="*60)
print(f"Project root: {project_root}")
print(f"Python path: {sys.executable}")
print("="*60)

try:
    from src.web.app import app
    # Avoid Unicode symbols on Windows terminals that default to cp1252
    print("[OK] Imports successful!")
    print("="*60)
    print("Starting web server...")
    print("Open your browser and go to: http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    print("="*60)
    app.run(debug=True, host='0.0.0.0', port=5000)
except ImportError as e:
    print(f"[ERROR] Import error: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure you're in the project root directory")
    print("2. Install dependencies: pip install -r requirements.txt")
    print("3. Check if all required files exist")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
