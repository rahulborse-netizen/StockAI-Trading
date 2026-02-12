"""
Run the web interface for AI Trading Algorithm
"""
import sys
from pathlib import Path

# Add project root to path FIRST so ssl_fix can be found
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Fix SSL certificate - must run before any HTTP calls
import src.web.ssl_fix  # noqa: F401

from src.web.app import app

if __name__ == '__main__':
    print("="*60)
    print("AI Trading Dashboard (src.web.app)")
    print("="*60)
    print("Main dashboard:  http://localhost:5000")
    print("Auto Trading:   http://localhost:5000/auto-trading")
    print("="*60)
    print("Starting web server...")
    try:
        from src.web.signal_precompute import start_precompute_background
        start_precompute_background(app=app)
        print("Signal pre-compute: started in background")
    except Exception as e:
        print(f"Signal pre-compute: skip ({e})")
    print("="*60)
    try:
        # Import socketio for WebSocket support
        from src.web.app import socketio
        # use_reloader=False to avoid duplicate processes and route issues
        socketio.run(app, debug=True, host='0.0.0.0', port=5000, use_reloader=False)
    except Exception as e:
        print(f"Error starting server: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure you're in the project root directory")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Check if port 5000 is already in use")
        import traceback
        traceback.print_exc()
        sys.exit(1)
