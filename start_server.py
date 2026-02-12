#!/usr/bin/env python3
"""
Start the AI Trading web server.
Run: python start_server.py
"""
import os
import sys
from pathlib import Path

# Add project root
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup error log file (logs/errors.log) before any other imports
try:
    from src.web.log_config import setup_log_file
    errors_log_path = setup_log_file()
    print(f"  Error log: {errors_log_path}")
except Exception as e:
    print(f"  Warning: Could not setup log file: {e}")

# Fix SSL before any HTTP calls (yfinance/curl uses CURL_CA_BUNDLE on Windows)
try:
    import certifi
    cert_path = certifi.where()
    os.environ.setdefault("SSL_CERT_FILE", cert_path)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", cert_path)
    os.environ.setdefault("CURL_CA_BUNDLE", cert_path)
except ImportError:
    pass

from src.web.app import app, socketio

DASHBOARD_URL = "http://localhost:5000"


def _start_signal_precompute():
    """Start background pre-computation of trading signals (runs on server start)."""
    try:
        from src.web.signal_precompute import start_precompute_background
        start_precompute_background(app=app)
        print("  Signal pre-compute: started in background (signals cached for next-day trading)")
    except Exception as e:
        print(f"  Signal pre-compute: skip ({e})")


if __name__ == "__main__":
    print()
    print("  AI Trading Dashboard")
    print("  --------------------")
    print(f"  Open in browser: {DASHBOARD_URL}")
    print("  Press Ctrl+C to stop")
    print()
    _start_signal_precompute()
    try:
        socketio.run(app, debug=True, host="0.0.0.0", port=5000, use_reloader=False)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
