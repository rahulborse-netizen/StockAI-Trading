"""
Run `python start_trading_dashboard.py` from the project root, then open the
printed URL to view the trading dashboard with buy/sell signals.
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

if __name__ == '__main__':
    port = int(os.environ.get('FLASK_PORT', '5000'))
    url = f"http://localhost:{port}"

    print("=" * 59)
    print("Trading Dashboard")
    print("=" * 59)
    print("Open in browser (trading signals - Buy/Sell):")
    print(f"  {url}")
    print("=" * 59)

    try:
        from src.web.app import app, socketio
        socketio.run(
            app,
            debug=True,
            host='0.0.0.0',
            port=port,
            use_reloader=False
        )
    except Exception as e:
        print(f"Error starting server: {e}")
        print("\nTroubleshooting:")
        print("1. Run from project root: python start_trading_dashboard.py")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Check if the port is already in use")
        import traceback
        traceback.print_exc()
        sys.exit(1)


