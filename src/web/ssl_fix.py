"""
SSL certificate fix - must be imported before any HTTP/HTTPS calls.
Configures certifi so yfinance, requests, and curl work without "unable to get local issuer certificate".
"""
import os

def _apply_ssl_fix():
    try:
        import certifi
        path = certifi.where()
        os.environ.setdefault('SSL_CERT_FILE', path)
        os.environ.setdefault('REQUESTS_CA_BUNDLE', path)
        os.environ.setdefault('CURL_CA_BUNDLE', path)
    except ImportError:
        pass

_apply_ssl_fix()


def get_yahoo_session():
    """Return a requests Session with certifi SSL verification for yfinance."""
    try:
        import requests
        import certifi
        s = requests.Session()
        s.verify = certifi.where()
        return s
    except Exception:
        return None
