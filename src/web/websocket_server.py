"""
WebSocket Server for Upstox Market Data Streaming
Phase 2.1: Real-time data integration.
Uses Upstox "Get Market Data Feed Authorize" API to obtain a one-time wss URL (required for connection).
"""
import logging
import json
import threading
import time
from typing import Dict, Set, Optional, Callable
import websocket
from datetime import datetime

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)

# Upstox REST base for authorize endpoint (v2 discontinued; use v3)
UPSTOX_FEED_AUTHORIZE_URL = "https://api.upstox.com/v3/feed/market-data-feed/authorize"


class UpstoxWebSocketManager:
    """
    Manages WebSocket connection to Upstox for real-time market data streaming.
    Connects using the authorized one-time wss URL from Upstox API.
    """
    
    def __init__(self, access_token: str = None):
        self.access_token = access_token
        self.ws = None
        self.connected = False
        self.subscribed_instruments: Set[str] = set()
        self.price_callbacks = []
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # seconds
        self._ws_thread = None
        self._stop_flag = threading.Event()
        self._lock = threading.Lock()
        self.last_connect_error: Optional[str] = None

    def get_last_connect_error(self) -> Optional[str]:
        """Return last connection failure reason for API feedback."""
        return self.last_connect_error

    def set_access_token(self, access_token: str):
        """Update access token"""
        self.access_token = access_token

    def _get_authorized_ws_url(self) -> Optional[str]:
        """
        Get one-time WebSocket URL from Upstox Market Data Feed Authorize API.
        Required: Upstox expects Bearer auth and returns a wss URL with a single-use code.
        """
        if not self.access_token or not requests:
            return None
        try:
            resp = requests.get(
                UPSTOX_FEED_AUTHORIZE_URL,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Accept": "application/json",
                },
                timeout=15,
            )
            if resp.status_code != 200:
                self.last_connect_error = f"Authorize API returned {resp.status_code}"
                logger.warning("Feed authorize API: %s %s", resp.status_code, resp.text[:200])
                return None
            data = resp.json()
            payload = data.get("data") or {}
            url = payload.get("authorized_redirect_uri") or payload.get("authorizedRedirectUri")
            if not url or not url.startswith("wss://"):
                self.last_connect_error = "No authorized wss URL in response"
                return None
            return url
        except Exception as e:
            self.last_connect_error = str(e)[:200]
            logger.warning("Failed to get authorized WebSocket URL: %s", e)
            return None

    def add_price_callback(self, callback: Callable):
        """
        Register a callback function to be called when price updates are received
        Callback signature: callback(instrument_key: str, price_data: dict)
        """
        with self._lock:
            if callback not in self.price_callbacks:
                self.price_callbacks.append(callback)
                logger.info(f"Added price callback: {callback.__name__}")
    
    def remove_price_callback(self, callback: Callable):
        """Remove a price callback"""
        with self._lock:
            if callback in self.price_callbacks:
                self.price_callbacks.remove(callback)
                logger.info(f"Removed price callback: {callback.__name__}")
    
    def connect(self) -> bool:
        """
        Establish WebSocket connection to Upstox using authorized one-time URL.
        Returns True if connection successful. Tries once with optional retry.
        """
        if not self.access_token:
            self.last_connect_error = "No access token"
            logger.error("Cannot connect: No access token provided")
            return False

        self.last_connect_error = None
        for attempt in range(2):  # initial + one retry
            if attempt > 0:
                logger.info("Retrying WebSocket connection in 2s...")
                time.sleep(2)
            ws_url = self._get_authorized_ws_url()
            if not ws_url:
                continue
            try:
                self.connected = False
                # WebSocket callbacks
                def on_open(ws):
                    logger.info("✅ WebSocket connection opened")
                    self.connected = True
                    self.reconnect_attempts = 0

                def on_message(ws, message):
                    self._handle_message(message)

                def on_error(ws, error):
                    err_str = str(error) if error else "unknown"
                    logger.error("❌ WebSocket error: %s", err_str)
                    self.last_connect_error = err_str[:200]

                def on_close(ws, close_status_code, close_msg):
                    logger.warning("WebSocket closed: %s - %s", close_status_code, close_msg)
                    self.connected = False
                    if not self._stop_flag.is_set():
                        self._attempt_reconnect()

                self.ws = websocket.WebSocketApp(
                    ws_url,
                    on_open=on_open,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close
                )
                self._ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
                self._ws_thread.start()
                # Wait for connection (max 10 seconds)
                for _ in range(100):
                    if self.connected:
                        return True
                    time.sleep(0.1)
                self.last_connect_error = "Connection timeout (10s)"
                logger.warning("WebSocket connection timeout")
            except Exception as e:
                self.last_connect_error = str(e)[:200]
                logger.error("Error connecting to WebSocket: %s", e)
        return False
    
    def _run_websocket(self):
        """Run WebSocket connection (called in separate thread)"""
        try:
            self.ws.run_forever()
        except Exception as e:
            logger.error(f"WebSocket run_forever error: {e}")
    
    def _attempt_reconnect(self):
        """Attempt to reconnect to WebSocket"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(f"Max reconnect attempts ({self.max_reconnect_attempts}) reached")
            return
            
        self.reconnect_attempts += 1
        logger.info(f"Attempting reconnect #{self.reconnect_attempts} in {self.reconnect_delay} seconds...")
        time.sleep(self.reconnect_delay)
        
        if not self._stop_flag.is_set():
            self.connect()
    
    def disconnect(self):
        """Close WebSocket connection"""
        logger.info("Disconnecting WebSocket...")
        self._stop_flag.set()
        self.connected = False
        
        if self.ws:
            try:
                self.ws.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
        
        if self._ws_thread and self._ws_thread.is_alive():
            self._ws_thread.join(timeout=2)
    
    def subscribe_instruments(self, instrument_keys: list):
        """
        Subscribe to real-time updates for instruments
        
        Args:
            instrument_keys: List of Upstox instrument keys (e.g., ['NSE_EQ|INE467B01029'])
        """
        if not self.connected:
            logger.warning("Cannot subscribe: WebSocket not connected")
            return False
            
        try:
            # Upstox subscription message format
            subscribe_msg = {
                "guid": "someguid",
                "method": "sub",
                "data": {
                    "mode": "full",
                    "instrumentKeys": instrument_keys
                }
            }
            
            self.ws.send(json.dumps(subscribe_msg))
            
            with self._lock:
                for key in instrument_keys:
                    self.subscribed_instruments.add(key)
            
            logger.info(f"Subscribed to {len(instrument_keys)} instruments")
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing to instruments: {e}")
            return False
    
    def unsubscribe_instruments(self, instrument_keys: list):
        """
        Unsubscribe from instrument updates
        
        Args:
            instrument_keys: List of instrument keys to unsubscribe
        """
        if not self.connected:
            logger.warning("Cannot unsubscribe: WebSocket not connected")
            return False
            
        try:
            # Upstox unsubscribe message format
            unsubscribe_msg = {
                "guid": "someguid",
                "method": "unsub",
                "data": {
                    "mode": "full",
                    "instrumentKeys": instrument_keys
                }
            }
            
            self.ws.send(json.dumps(unsubscribe_msg))
            
            with self._lock:
                for key in instrument_keys:
                    self.subscribed_instruments.discard(key)
            
            logger.info(f"Unsubscribed from {len(instrument_keys)} instruments")
            return True
            
        except Exception as e:
            logger.error(f"Error unsubscribing from instruments: {e}")
            return False
    
    def _handle_message(self, message):
        """
        Handle incoming WebSocket messages. Upstox sends JSON with top-level 'feeds' (no 'type').
        Parse and broadcast price updates to registered callbacks.
        """
        try:
            if isinstance(message, bytes):
                logger.debug("Received binary message (protobuf)")
                return

            data = json.loads(message) if isinstance(message, str) else message
            # Upstox response: { "feeds": { "NSE_EQ|INE...": { "ltpc": {...} or "ff": { "marketFF": { "ltpc": {...} } } } }, "currentTs": "..." }
            feeds = data.get("feeds") or data.get("feed") or {}
            if isinstance(feeds, dict):
                for instrument_key, feed_data in feeds.items():
                    self._process_price_update(instrument_key, feed_data)
                return
            msg_type = data.get("type")
            if msg_type == "error":
                logger.error("WebSocket error message: %s", data.get("message"))
            elif msg_type == "success":
                logger.info("WebSocket success: %s", data.get("message"))
        except json.JSONDecodeError as e:
            logger.error("Error decoding WebSocket message: %s", e)
        except Exception as e:
            logger.error("Error handling WebSocket message: %s", e)
    
    def _process_price_update(self, instrument_key: str, feed_data: dict):
        """
        Process price update. Supports ltpc mode (top-level ltpc) and full mode (ff.marketFF.ltpc).
        """
        try:
            ltpc = feed_data.get("ltpc") or {}
            market_ff = feed_data.get("ff") or {}
            if market_ff and not ltpc:
                market_ff = market_ff.get("marketFF") or market_ff
                ltpc = market_ff.get("ltpc") or ltpc
            ohlc = (market_ff.get("marketOHLC") or {}).get("ohlc") or []
            ohlc_1d = next((c for c in ohlc if isinstance(c, dict) and c.get("interval") == "1d"), {})
            close = ltpc.get("cp") if isinstance(ltpc.get("cp"), (int, float)) else (ohlc_1d.get("close") or 0)
            try:
                close = float(close)
            except (TypeError, ValueError):
                close = 0
            price_data = {
                "instrument_key": instrument_key,
                "ltp": ltpc.get("ltp") if isinstance(ltpc.get("ltp"), (int, float)) else 0,
                "ltq": ltpc.get("ltq", 0),
                "ltt": ltpc.get("ltt", ""),
                "close": close,
                "close_price": close,
                "open": ohlc_1d.get("open", 0) if isinstance(ohlc_1d.get("open"), (int, float)) else 0,
                "high": ohlc_1d.get("high", 0) if isinstance(ohlc_1d.get("high"), (int, float)) else 0,
                "low": ohlc_1d.get("low", 0) if isinstance(ohlc_1d.get("low"), (int, float)) else 0,
                "volume": ohlc_1d.get("volume", 0) or 0,
                "oi": (market_ff.get("eFeedDetails") or {}).get("oi", 0) or 0,
                "timestamp": datetime.now().isoformat(),
            }
            if not isinstance(price_data["ltp"], (int, float)) or price_data["ltp"] <= 0:
                price_data["ltp"] = close
            with self._lock:
                for callback in self.price_callbacks:
                    try:
                        callback(instrument_key, price_data)
                    except Exception as e:
                        logger.error("Error in price callback %s: %s", getattr(callback, "__name__", ""), e)
        except Exception as e:
            logger.error("Error processing price update: %s", e)
    
    def get_status(self) -> Dict:
        """Get current WebSocket connection status"""
        return {
            'connected': self.connected,
            'subscribed_instruments': len(self.subscribed_instruments),
            'callbacks_registered': len(self.price_callbacks),
            'reconnect_attempts': self.reconnect_attempts
        }
    
    def is_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self.connected
    
    def get_subscribed_instruments(self) -> Set[str]:
        """Get set of currently subscribed instruments"""
        with self._lock:
            return self.subscribed_instruments.copy()


# Global WebSocket manager instance
_ws_manager = None
_ws_lock = threading.Lock()

# instrument_key -> ticker mapping (for including ticker in price_update broadcast)
_key_to_ticker: Dict[str, str] = {}


def update_key_to_ticker_map(ticker_to_key: dict):
    """Update instrument_key -> ticker mapping (called from start_stream)."""
    global _key_to_ticker
    _key_to_ticker = {v: k for k, v in (ticker_to_key or {}).items()}


def get_ticker_for_key(instrument_key: str) -> Optional[str]:
    """Get ticker for instrument_key from the mapping."""
    return _key_to_ticker.get(instrument_key)


def get_websocket_manager() -> UpstoxWebSocketManager:
    """Get global WebSocket manager instance (singleton)"""
    global _ws_manager
    with _ws_lock:
        if _ws_manager is None:
            _ws_manager = UpstoxWebSocketManager()
        return _ws_manager


def reset_websocket_manager():
    """Reset global WebSocket manager (useful for testing)"""
    global _ws_manager
    with _ws_lock:
        if _ws_manager:
            _ws_manager.disconnect()
        _ws_manager = None


def get_ws_manager() -> UpstoxWebSocketManager:
    """Alias for get_websocket_manager()"""
    return get_websocket_manager()


# Global Socket.IO instance for broadcasting
_socketio_instance = None

def set_socketio_instance(socketio_instance):
    """Set global Socket.IO instance for broadcasting"""
    global _socketio_instance
    _socketio_instance = socketio_instance

def init_websocket_handlers(socketio_instance):
    """
    Initialize WebSocket event handlers for Flask-SocketIO
    This function is called from Flask app initialization
    
    Args:
        socketio_instance: Flask-SocketIO instance
    """
    global _socketio_instance
    _socketio_instance = socketio_instance
    
    from flask import session
    from flask_socketio import emit
    
    # Get WebSocket manager and register broadcast callback
    ws_manager = get_ws_manager()
    
    def broadcast_price_update(instrument_key: str, price_data: dict):
        """Broadcast price update to all connected Socket.IO clients"""
        if _socketio_instance:
            try:
                ticker = get_ticker_for_key(instrument_key)
                payload = {
                    'instrument_key': instrument_key,
                    'price_data': price_data,
                    'ticker': ticker
                }
                _socketio_instance.emit('price_update', payload, broadcast=True)
            except Exception as e:
                logger.error(f"Error broadcasting price update: {e}")
    
    # Register broadcast callback
    ws_manager.add_price_callback(broadcast_price_update)
    
    @socketio_instance.on('connect')
    def handle_connect():
        """Handle client connection"""
        logger.info(f"✅ Client connected to Flask-SocketIO")
        emit('connection_response', {'status': 'connected', 'message': 'Connected to trading server'})
    
    @socketio_instance.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        logger.info("Client disconnected from Flask-SocketIO")
    
    @socketio_instance.on('subscribe_instruments')
    def handle_subscribe(data):
        """
        Handle instrument subscription request from client
        
        Expected data: {
            'instrument_keys': ['NSE_EQ|INE467B01029', ...]
        }
        """
        try:
            instrument_keys = data.get('instrument_keys', [])
            logger.info(f"Client requesting subscription to {len(instrument_keys)} instruments")
            
            ws_manager = get_websocket_manager()
            
            # Subscribe to Upstox WebSocket
            if ws_manager.is_connected():
                success = ws_manager.subscribe_instruments(instrument_keys)
                if success:
                    emit('subscription_response', {
                        'status': 'success',
                        'message': f'Subscribed to {len(instrument_keys)} instruments',
                        'instruments': instrument_keys
                    })
                else:
                    emit('subscription_response', {
                        'status': 'error',
                        'message': 'Failed to subscribe to instruments'
                    })
            else:
                emit('subscription_response', {
                    'status': 'error',
                    'message': 'WebSocket not connected to Upstox. Please connect first.'
                })
                
        except Exception as e:
            logger.error(f"Error handling subscription: {e}")
            emit('subscription_response', {
                'status': 'error',
                'message': str(e)
            })
    
    @socketio_instance.on('unsubscribe_instruments')
    def handle_unsubscribe(data):
        """
        Handle instrument unsubscription request
        
        Expected data: {
            'instrument_keys': ['NSE_EQ|INE467B01029', ...]
        }
        """
        try:
            instrument_keys = data.get('instrument_keys', [])
            logger.info(f"Client requesting unsubscription from {len(instrument_keys)} instruments")
            
            ws_manager = get_websocket_manager()
            
            if ws_manager.is_connected():
                success = ws_manager.unsubscribe_instruments(instrument_keys)
                if success:
                    emit('unsubscription_response', {
                        'status': 'success',
                        'message': f'Unsubscribed from {len(instrument_keys)} instruments'
                    })
                else:
                    emit('unsubscription_response', {
                        'status': 'error',
                        'message': 'Failed to unsubscribe from instruments'
                    })
            else:
                emit('unsubscription_response', {
                    'status': 'error',
                    'message': 'WebSocket not connected'
                })
                
        except Exception as e:
            logger.error(f"Error handling unsubscription: {e}")
            emit('unsubscription_response', {
                'status': 'error',
                'message': str(e)
            })
    
    @socketio_instance.on('get_ws_status')
    def handle_get_status():
        """Get WebSocket connection status"""
        try:
            ws_manager = get_websocket_manager()
            status = ws_manager.get_status()
            emit('ws_status', status)
        except Exception as e:
            logger.error(f"Error getting WebSocket status: {e}")
            emit('ws_status', {'error': str(e)})
    
    logger.info("✅ WebSocket event handlers initialized")
