/**
 * WebSocket Client for Real-time Market Data
 * Phase 2.1: Client-side WebSocket connection to Flask-SocketIO
 */

class MarketDataWebSocket {
    constructor() {
        this.socket = null;
        this.connected = false;
        this.subscriptions = new Set();
        this.priceCallbacks = new Map(); // ticker -> callback function
        this.connectionCallbacks = [];
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000; // 3 seconds
    }

    /**
     * Connect to Flask-SocketIO server
     */
    connect() {
        if (this.socket && this.connected) {
            console.log('📡 WebSocket already connected');
            return;
        }

        try {
            console.log('📡 Connecting to WebSocket server...');
            
            // Initialize Socket.IO connection
            this.socket = io({
                transports: ['websocket', 'polling'],
                upgrade: true,
                reconnection: true,
                reconnectionDelay: this.reconnectDelay,
                reconnectionAttempts: this.maxReconnectAttempts
            });

            // Connection event handlers
            this.socket.on('connect', () => {
                console.log('✅ Connected to WebSocket server');
                this.connected = true;
                this.reconnectAttempts = 0;
                this._notifyConnectionCallbacks('connected');
                
                // Resubscribe to instruments after reconnection
                if (this.subscriptions.size > 0) {
                    this._resubscribeAll();
                }
            });

            this.socket.on('disconnect', (reason) => {
                console.warn('⚠️ Disconnected from WebSocket:', reason);
                this.connected = false;
                this._notifyConnectionCallbacks('disconnected');
            });

            this.socket.on('connect_error', (error) => {
                console.error('❌ WebSocket connection error:', error);
                this._notifyConnectionCallbacks('error', error);
            });

            // Server response handlers
            this.socket.on('connection_response', (data) => {
                console.log('📡 Connection response:', data);
            });

            this.socket.on('subscription_response', (data) => {
                console.log('📊 Subscription response:', data);
                if (data.status === 'error') {
                    console.error('Subscription error:', data.message);
                }
            });

            this.socket.on('unsubscription_response', (data) => {
                console.log('📊 Unsubscription response:', data);
            });

            this.socket.on('ws_status', (data) => {
                console.log('📊 WebSocket status:', data);
            });

            // Price update handler - THE MAIN EVENT
            this.socket.on('price_update', (data) => {
                this._handlePriceUpdate(data);
            });

        } catch (error) {
            console.error('❌ Error initializing WebSocket:', error);
            this._notifyConnectionCallbacks('error', error);
        }
    }

    /**
     * Disconnect from WebSocket server
     */
    disconnect() {
        if (this.socket) {
            console.log('📡 Disconnecting WebSocket...');
            this.socket.disconnect();
            this.connected = false;
            this.subscriptions.clear();
            this._notifyConnectionCallbacks('disconnected');
        }
    }

    /**
     * Subscribe to price updates for instruments
     * @param {Array<string>} instrumentKeys - Array of Upstox instrument keys
     * @param {Function} callback - Callback function(instrumentKey, priceData)
     */
    subscribe(instrumentKeys, callback = null) {
        if (!this.connected) {
            console.warn('⚠️ Cannot subscribe: WebSocket not connected');
            return false;
        }

        if (!Array.isArray(instrumentKeys)) {
            instrumentKeys = [instrumentKeys];
        }

        // Add to subscriptions
        instrumentKeys.forEach(key => {
            this.subscriptions.add(key);
            if (callback) {
                this.priceCallbacks.set(key, callback);
            }
        });

        // Send subscription request to server
        this.socket.emit('subscribe_instruments', {
            instrument_keys: instrumentKeys
        });

        console.log(`📊 Subscribed to ${instrumentKeys.length} instruments`);
        return true;
    }

    /**
     * Unsubscribe from instrument updates
     * @param {Array<string>} instrumentKeys - Array of instrument keys
     */
    unsubscribe(instrumentKeys) {
        if (!this.connected) {
            console.warn('⚠️ Cannot unsubscribe: WebSocket not connected');
            return false;
        }

        if (!Array.isArray(instrumentKeys)) {
            instrumentKeys = [instrumentKeys];
        }

        // Remove from subscriptions
        instrumentKeys.forEach(key => {
            this.subscriptions.delete(key);
            this.priceCallbacks.delete(key);
        });

        // Send unsubscription request to server
        this.socket.emit('unsubscribe_instruments', {
            instrument_keys: instrumentKeys
        });

        console.log(`📊 Unsubscribed from ${instrumentKeys.length} instruments`);
        return true;
    }

    /**
     * Register a callback for price updates
     * @param {string} instrumentKey - Instrument key
     * @param {Function} callback - Callback function(instrumentKey, priceData)
     */
    onPriceUpdate(instrumentKey, callback) {
        this.priceCallbacks.set(instrumentKey, callback);
    }

    /**
     * Register a callback for connection status changes
     * @param {Function} callback - Callback function(status, error)
     */
    onConnectionChange(callback) {
        this.connectionCallbacks.push(callback);
    }

    /**
     * Get WebSocket connection status from server
     */
    getStatus() {
        if (this.connected && this.socket) {
            this.socket.emit('get_ws_status');
        }
    }

    /**
     * Check if currently connected
     */
    isConnected() {
        return this.connected;
    }

    /**
     * Get list of subscribed instruments
     */
    getSubscriptions() {
        return Array.from(this.subscriptions);
    }

    /**
     * Handle incoming price updates
     * @private
     */
    _handlePriceUpdate(data) {
        try {
            const { instrument_key, data: priceData } = data;
            
            // Log price update (can be disabled for performance)
            // console.log(`💹 Price update: ${instrument_key}`, priceData);

            // Call specific callback if registered
            if (this.priceCallbacks.has(instrument_key)) {
                const callback = this.priceCallbacks.get(instrument_key);
                callback(instrument_key, priceData);
            }

            // Trigger global price update event
            const event = new CustomEvent('priceUpdate', {
                detail: { instrument_key, priceData }
            });
            window.dispatchEvent(event);

        } catch (error) {
            console.error('❌ Error handling price update:', error);
        }
    }

    /**
     * Resubscribe to all instruments (after reconnection)
     * @private
     */
    _resubscribeAll() {
        if (this.subscriptions.size > 0) {
            const instruments = Array.from(this.subscriptions);
            console.log(`🔄 Resubscribing to ${instruments.length} instruments...`);
            
            this.socket.emit('subscribe_instruments', {
                instrument_keys: instruments
            });
        }
    }

    /**
     * Notify connection callbacks of status change
     * @private
     */
    _notifyConnectionCallbacks(status, error = null) {
        this.connectionCallbacks.forEach(callback => {
            try {
                callback(status, error);
            } catch (err) {
                console.error('Error in connection callback:', err);
            }
        });
    }
}

// Create global instance
window.marketDataWS = new MarketDataWebSocket();

// Auto-connect on page load (optional - can be triggered manually)
document.addEventListener('DOMContentLoaded', () => {
    console.log('📡 Market Data WebSocket client initialized');
    // Don't auto-connect - let dashboard.js decide when to connect
    // window.marketDataWS.connect();
});

/**
 * Utility: Start real-time streaming for watchlist
 * @param {Array<string>} tickers - Array of tickers (e.g., ['RELIANCE.NS'])
 */
async function startMarketDataStream(tickers) {
    try {
        console.log(`🚀 Starting market data stream for ${tickers.length} tickers...`);
        
        const response = await fetch('/api/market/start_stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tickers: tickers
            })
        });

        const data = await response.json();
        
        if (data.status === 'success') {
            console.log('✅ Market data stream started:', data);
            return data;
        } else {
            console.error('❌ Failed to start stream:', data.error);
            return null;
        }

    } catch (error) {
        console.error('❌ Error starting market data stream:', error);
        return null;
    }
}

/**
 * Utility: Stop real-time streaming
 */
async function stopMarketDataStream() {
    try {
        console.log('🛑 Stopping market data stream...');
        
        const response = await fetch('/api/market/stop_stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();
        
        if (data.status === 'success') {
            console.log('✅ Market data stream stopped');
            return data;
        } else {
            console.error('❌ Failed to stop stream:', data.error);
            return null;
        }

    } catch (error) {
        console.error('❌ Error stopping market data stream:', error);
        return null;
    }
}

/**
 * Utility: Get WebSocket status from server
 */
async function getWebSocketStatus() {
    try {
        const response = await fetch('/api/market/ws_status');
        const data = await response.json();
        console.log('📊 WebSocket status:', data);
        return data;
    } catch (error) {
        console.error('❌ Error getting WebSocket status:', error);
        return null;
    }
}
