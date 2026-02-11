// Modern Dashboard JavaScript with Enhanced Interactivity
// Phase 2.1: Real-time WebSocket updates

let priceUpdateInterval = null;
let selectedTicker = null;
let currentTheme = 'dark';
let marketDataWS = null;
let lastPrices = {}; // Store last prices for change detection

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'dark';
    setTheme(savedTheme);
    
    // Phase 2.1: Initialize WebSocket client
    if (window.marketDataWS) {
        marketDataWS = window.marketDataWS;
        
        // Connect to WebSocket server
        marketDataWS.connect();
        
        // Monitor connection status
        marketDataWS.onConnectionChange((status, error) => {
            updateWebSocketStatus(status, error);
        });
        
        // Listen for global price updates
        window.addEventListener('priceUpdate', (event) => {
            handleRealtimePriceUpdate(event.detail.instrument_key, event.detail.priceData);
        });
        
        // Start WebSocket stream when watchlist is loaded
        setTimeout(() => {
            startWebSocketStream();
        }, 2000);
    }
    
    // Initialize components
    loadWatchlist();
    loadTopStocks();
    loadAlerts();
    loadOrders();
    updateStats();
    updatePortfolioSummary();
    
    // Initialize auto trading card visibility
    const savedAutoTrading = localStorage.getItem('autoTradingCardVisible');
    if (savedAutoTrading === 'true') {
        setTimeout(() => {
            autoTradingCardVisible = true;
            const card = document.getElementById('auto-trading-card');
            const btn = document.getElementById('auto-trading-toggle-btn');
            if (card) card.style.display = 'block';
            if (btn) btn.classList.add('active');
            updateAutoTradingStatus();
            if (!autoTradingStatusInterval) {
                autoTradingStatusInterval = setInterval(updateAutoTradingStatus, 3000);
            }
        }, 500);
    }
    
    // Fallback: Auto-refresh prices every 30 seconds if WebSocket fails
    priceUpdateInterval = setInterval(() => {
        if (!marketDataWS || !marketDataWS.isConnected()) {
            updatePrices();
            updateStats();
        }
        // Always update portfolio summary (includes P&L from database)
        updatePortfolioSummary();
    }, 30000);
    
    // Show price input when order type changes
    document.getElementById('order-order-type')?.addEventListener('change', function() {
        const priceContainer = document.getElementById('price-input-container');
        if (this.value === 'LIMIT' || this.value === 'SL') {
            priceContainer.style.display = 'block';
        } else {
            priceContainer.style.display = 'none';
        }
    });
    
    // Add smooth animations
    document.querySelectorAll('.card-modern').forEach(card => {
        card.classList.add('fade-in');
    });
});

// Theme Toggle - Make functions globally available
function toggleTheme() {
    currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
    setTheme(currentTheme);
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    const themeIcon = document.getElementById('theme-icon');
    if (themeIcon) {
        themeIcon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
}

// Make functions globally available
window.setTheme = setTheme;
window.toggleTheme = toggleTheme;

// Update Stats
async function updateStats() {
    try {
        // Update portfolio summary (Overall P&L and Day P&L)
        await updatePortfolioSummary();
        
        // Update watchlist prices
        const response = await fetch('/api/prices');
        const prices = await response.json();
        
        let totalValue = 0;
        let totalChange = 0;
        let positiveCount = 0;
        let totalCount = 0;
        
        Object.values(prices).forEach(price => {
            if (price.price) {
                totalValue += price.price;
                totalChange += price.change || 0;
                totalCount++;
                if (price.change > 0) positiveCount++;
            }
        });
        
        // Update today's P&L (if element exists - old element ID)
        const pnlEl = document.getElementById('today-pnl');
        if (pnlEl) {
            const pnlClass = totalChange >= 0 ? 'price-up' : 'price-down';
            pnlEl.className = `stat-value ${pnlClass}`;
            pnlEl.textContent = `${totalChange >= 0 ? '+' : ''}₹${totalChange.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        }
        
        // Update win rate
        const winRateEl = document.getElementById('win-rate');
        if (winRateEl && totalCount > 0) {
            const winRate = (positiveCount / totalCount * 100).toFixed(1);
            winRateEl.textContent = `${winRate}%`;
        }
        
        // Update active alerts
        const alertsResponse = await fetch('/api/alerts');
        const alerts = await alertsResponse.json();
        const activeAlerts = alerts.filter(a => a.active && !a.triggered).length;
        const alertsEl = document.getElementById('active-alerts');
        if (alertsEl) {
            alertsEl.textContent = activeAlerts;
        }
    } catch (error) {
        console.error('Error updating stats:', error);
    }
}

// Load watchlist
async function loadWatchlist() {
    try {
        const response = await fetch('/api/watchlist');
        const watchlist = await response.json();
        const container = document.getElementById('watchlist-container');
        container.innerHTML = '';
        
        if (watchlist.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-star"></i>
                    <p>No stocks in watchlist. Add some stocks to monitor.</p>
                </div>
            `;
            return;
        }
        
        watchlist.forEach(ticker => {
            const item = createWatchlistItem(ticker);
            container.appendChild(item);
        });
        
        // Load prices for watchlist
        updatePrices();
        
        // Phase 2.1: Subscribe to WebSocket updates for new watchlist items
        if (marketDataWS && marketDataWS.isConnected()) {
            marketDataWS.subscribe(watchlist);
        }
    } catch (error) {
        console.error('Error loading watchlist:', error);
    }
}

// Create modern watchlist item
function createWatchlistItem(ticker) {
    const col = document.createElement('div');
    col.className = 'watchlist-item fade-in';
    col.setAttribute('data-ticker', ticker);
    col.innerHTML = `
        <div class="watchlist-item-header">
            <h6>${ticker}</h6>
            <button class="btn-modern btn-icon-sm" onclick="removeFromWatchlist('${ticker}')" title="Remove">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="price-info" id="price-${ticker}">
            <div class="spinner-border spinner-border-sm" role="status"></div>
        </div>
        <div class="watchlist-actions">
            <button class="btn-modern btn-primary w-100 mt-2" onclick="showLevels('${ticker}')">
                <i class="fas fa-crosshairs"></i> <span class="mobile-hide">View Levels</span>
            </button>
            <button class="btn-modern btn-success w-100 mt-2" onclick="quickOrder('${ticker}', 'BUY')" style="display: none;" id="quick-buy-${ticker}">
                <i class="fas fa-arrow-up"></i> <span class="mobile-hide">Buy</span>
            </button>
            <button class="btn-modern btn-danger w-100 mt-2" onclick="quickOrder('${ticker}', 'SELL')" style="display: none;" id="quick-sell-${ticker}">
                <i class="fas fa-arrow-down"></i> <span class="mobile-hide">Sell</span>
            </button>
        </div>
    `;
    return col;
}

// Add to watchlist
async function addToWatchlist() {
    const ticker = document.getElementById('new-ticker').value.trim();
    if (!ticker) {
        showNotification('Please enter a ticker', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/watchlist/add', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ticker: ticker})
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            document.getElementById('new-ticker').value = '';
            loadWatchlist();
            showNotification(`${ticker} added to watchlist`, 'success');
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        console.error('Error adding to watchlist:', error);
        showNotification('Error adding ticker', 'error');
    }
}

// Remove from watchlist
async function removeFromWatchlist(ticker) {
    try {
        const response = await fetch('/api/watchlist/remove', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ticker: ticker})
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            loadWatchlist();
            showNotification(`${ticker} removed from watchlist`, 'success');
        }
    } catch (error) {
        console.error('Error removing from watchlist:', error);
    }
}

// Phase 2.1: Start WebSocket stream for watchlist
async function startWebSocketStream() {
    try {
        const response = await fetch('/api/watchlist');
        const watchlist = await response.json();
        
        if (watchlist.length > 0 && marketDataWS && marketDataWS.isConnected()) {
            // Subscribe to watchlist tickers via WebSocket
            marketDataWS.subscribe(watchlist);
            
            // Also start stream on server side
            const streamResponse = await fetch('/api/market/start_stream', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({tickers: watchlist})
            });
            
            if (!streamResponse.ok) {
                const errorData = await streamResponse.json().catch(() => ({}));
                console.error('Error starting market stream:', errorData.error || streamResponse.statusText);
                if (errorData.message) {
                    console.error('Details:', errorData.message);
                }
            }
        }
    } catch (error) {
        console.error('Error starting WebSocket stream:', error);
    }
}

// Phase 2.1: Handle real-time price updates from WebSocket
function handleRealtimePriceUpdate(instrumentKey, priceData) {
    try {
        // Map instrument key to ticker (simplified - you may need instrument master)
        // For now, update all watchlist items and match by instrument key
        
        // Update display with real-time data
        const formattedData = {
            price: priceData.ltp || 0,
            open: priceData.open || 0,
            high: priceData.high || 0,
            low: priceData.low || 0,
            close: priceData.close || 0,
            volume: priceData.volume || 0,
            change: (priceData.ltp - priceData.close) || 0,
            change_pct: priceData.close > 0 ? ((priceData.ltp - priceData.close) / priceData.close * 100) : 0
        };
        
        // Store instrument key mapping (you may need to enhance this)
        // For now, try to match against watchlist items
        const watchlistItems = document.querySelectorAll('.watchlist-item');
        watchlistItems.forEach(item => {
            const ticker = item.getAttribute('data-ticker');
            const itemInstrumentKey = item.getAttribute('data-instrument-key');
            
            if (itemInstrumentKey === instrumentKey) {
                updatePriceDisplay(ticker, formattedData, true);
            }
        });
        
        // Update positions P&L if affected
        updatePositionsPnL(instrumentKey, priceData.ltp);
        
    } catch (error) {
        console.error('Error handling real-time price update:', error);
    }
}

// Phase 2.1: Update WebSocket connection status indicator
function updateWebSocketStatus(status, error = null) {
    const statusEl = document.getElementById('ws-connection-status');
    if (!statusEl) return;
    
    const statusMessages = {
        'connected': '🟢 Live',
        'disconnected': '🔴 Offline',
        'error': '🟠 Error'
    };
    
    statusEl.innerHTML = statusMessages[status] || '⚫ Unknown';
    
    if (status === 'connected') {
        statusEl.style.color = 'var(--success-color)';
    } else if (status === 'error') {
        statusEl.style.color = 'var(--warning-color)';
        if (error) {
            console.error('WebSocket error:', error);
        }
    } else {
        statusEl.style.color = 'var(--danger-color)';
    }
}

// Phase 2.1: Update price display with animation
function updatePriceDisplay(ticker, priceData, isRealtime = false) {
    const priceInfo = document.getElementById(`price-${ticker}`);
    if (!priceInfo) return;
    
    if (priceData.error) {
        const errorMsg = priceData.error.length > 60 
            ? priceData.error.substring(0, 60) + '...' 
            : priceData.error;
        priceInfo.innerHTML = `
            <div class="price-value" style="color: var(--text-muted); font-size: 1.25rem;">N/A</div>
            <div class="price-change" style="color: var(--danger-color); font-size: 0.75rem; margin-top: 0.5rem;">
                <i class="fas fa-exclamation-triangle"></i>
                <span style="display: block; margin-top: 0.25rem;">${errorMsg}</span>
            </div>
        `;
        return;
    }
    
    const price = priceData.price || priceData.ltp || 0;
    const change = priceData.change || 0;
    const changePct = priceData.change_pct || 0;
    const volume = priceData.volume || 0;
    
    // Detect price change for animation
    const lastPrice = lastPrices[ticker];
    let flashClass = '';
    if (lastPrice && isRealtime) {
        if (price > lastPrice.price) {
            flashClass = 'price-flash-up';
        } else if (price < lastPrice.price) {
            flashClass = 'price-flash-down';
        }
    }
    lastPrices[ticker] = {price, change, changePct};
    
    const changeClass = change >= 0 ? 'price-up' : 'price-down';
    const changeIcon = change >= 0 ? 'fa-arrow-up' : 'fa-arrow-down';
    
    priceInfo.innerHTML = `
        <div class="price-value ${flashClass}">₹${price.toFixed(2)}</div>
        <div class="price-change ${changeClass}">
            <i class="fas ${changeIcon}"></i>
            <span>${change >= 0 ? '+' : ''}${change.toFixed(2)} (${changePct >= 0 ? '+' : ''}${changePct.toFixed(2)}%)</span>
        </div>
        <small class="text-muted">Vol: ${volume.toLocaleString()}</small>
        ${isRealtime ? '<small class="text-success" style="font-size: 0.65rem;"><i class="fas fa-circle"></i> Live</small>' : ''}
    `;
    
    // Remove flash class after animation
    if (flashClass) {
        setTimeout(() => {
            const priceValue = priceInfo.querySelector('.price-value');
            if (priceValue) {
                priceValue.classList.remove(flashClass);
            }
        }, 500);
    }
}

// Update prices with modern display (fallback for non-WebSocket)
async function updatePrices() {
    try {
        const response = await fetch('/api/prices');
        const prices = await response.json();
        
        Object.keys(prices).forEach(ticker => {
            updatePriceDisplay(ticker, prices[ticker], false);
        });
    } catch (error) {
        console.error('Error updating prices:', error);
    }
}

// Show entry/exit levels with modern design
async function showLevels(ticker) {
    selectedTicker = ticker;
    
    // Switch to signals tab if not already there
    if (typeof switchTab === 'function') {
        switchTab('signals');
    }
    
    // Find the appropriate container
    let container = document.getElementById('levels-container');
    if (!container) {
        container = document.getElementById('signals-container');
    }
    
    if (!container) {
        console.error('Levels container not found');
        return;
    }
    
    container.innerHTML = '<div class="spinner-border" role="status"></div>';
    
    try {
        const response = await fetch(`/api/signals/${ticker}`);
        const signal = await response.json();
        
        if (signal.error) {
            container.innerHTML = `<div class="empty-state"><i class="fas fa-exclamation-triangle"></i><p>${signal.error}</p></div>`;
            return;
        }
        
        const signalClass = signal.signal === 'BUY' ? 'success' : 'warning';
        const signalIcon = signal.signal === 'BUY' ? 'fa-arrow-up' : 'fa-pause';
        
        container.innerHTML = `
            <div class="fade-in">
                <div class="level-item entry mb-3">
                    <div class="level-label">Current Price</div>
                    <div class="level-value">₹${signal.current_price.toFixed(2)}</div>
                </div>
                <div class="d-flex align-items-center gap-2 mb-3 p-2" style="background: var(--bg-secondary); border-radius: 8px;">
                    <div class="stat-icon" style="width: 40px; height: 40px;">
                        <i class="fas ${signalIcon}"></i>
                    </div>
                    <div>
                        <div class="level-label">Signal</div>
                        <div class="level-value" style="font-size: 1.25rem;">
                            <span class="badge bg-${signalClass}">${signal.signal}</span>
                            <span class="ms-2" style="font-size: 0.875rem; color: var(--text-muted);">
                                ${(signal.probability * 100).toFixed(1)}% confidence
                            </span>
                        </div>
                    </div>
                </div>
                <div class="level-item entry">
                    <div class="level-label">Entry Level</div>
                    <div class="level-value">₹${signal.entry_level.toFixed(2)}</div>
                </div>
                <div class="level-item stop-loss">
                    <div class="level-label">Stop Loss</div>
                    <div class="level-value">₹${signal.stop_loss.toFixed(2)} 
                        <span style="font-size: 0.875rem; color: var(--text-muted);">
                            (${((signal.stop_loss - signal.current_price) / signal.current_price * 100).toFixed(2)}%)
                        </span>
                    </div>
                </div>
                <div class="level-item target">
                    <div class="level-label">Target 1</div>
                    <div class="level-value">₹${signal.target_1.toFixed(2)} (+2.0%)</div>
                </div>
                <div class="level-item target">
                    <div class="level-label">Target 2</div>
                    <div class="level-value">₹${signal.target_2.toFixed(2)} (+2.5%)</div>
                </div>
                <div class="mt-3 p-2" style="background: var(--bg-secondary); border-radius: 8px; font-size: 0.875rem;">
                    <div class="d-flex justify-content-between mb-1">
                        <span class="text-muted">Recent High:</span>
                        <span>₹${signal.recent_high.toFixed(2)}</span>
                    </div>
                    <div class="d-flex justify-content-between mb-1">
                        <span class="text-muted">Recent Low:</span>
                        <span>₹${signal.recent_low.toFixed(2)}</span>
                    </div>
                    <div class="d-flex justify-content-between">
                        <span class="text-muted">Volatility:</span>
                        <span>${(signal.volatility * 100).toFixed(2)}%</span>
                    </div>
                </div>
                <div class="mt-3">
                    <h6 class="mb-2">Generate Trade Plan:</h6>
                    <div class="d-flex gap-2 flex-wrap">
                        <button class="btn-modern btn-primary btn-sm" onclick="generateTradePlan('${ticker}', 'intraday')" title="Intraday Trading">
                            <i class="fas fa-clock"></i> Intraday
                        </button>
                        <button class="btn-modern btn-info btn-sm" onclick="generateTradePlan('${ticker}', 'swing')" title="Swing Trading">
                            <i class="fas fa-chart-line"></i> Swing
                        </button>
                        <button class="btn-modern btn-warning btn-sm" onclick="generateTradePlan('${ticker}', 'position')" title="Position Trading">
                            <i class="fas fa-chart-area"></i> Position
                        </button>
                    </div>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Error loading levels:', error);
        container.innerHTML = '<div class="empty-state"><i class="fas fa-exclamation-triangle"></i><p>Error loading levels</p></div>';
    }
}

// Load top stocks with modern cards
async function loadTopStocks() {
    try {
        const response = await fetch('/api/top_stocks');
        const stocks = await response.json();
        const container = document.getElementById('top-stocks-container');
        container.innerHTML = '';
        
        stocks.forEach((stock, index) => {
            const card = document.createElement('div');
            card.className = 'top-stock-card fade-in';
            card.style.animationDelay = `${index * 0.1}s`;
            card.innerHTML = `
                <div class="stat-icon" style="width: 48px; height: 48px; margin: 0 auto 0.5rem;">
                    <i class="fas fa-trophy"></i>
                </div>
                <h6>${stock.name}</h6>
                <div class="ticker">${stock.ticker}</div>
                <div class="return">+${stock.return}%</div>
                <small class="text-muted">Sharpe: ${stock.sharpe}</small>
                <button class="btn-modern btn-primary btn-sm mt-2 w-100" onclick="addToWatchlistFromTop('${stock.ticker}')">
                    <i class="fas fa-plus"></i> Add
                </button>
            `;
            container.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading top stocks:', error);
    }
}

function addToWatchlistFromTop(ticker) {
    document.getElementById('new-ticker').value = ticker;
    addToWatchlist();
}

// Load alerts
async function loadAlerts() {
    try {
        const response = await fetch('/api/alerts');
        const alerts = await response.json();
        const container = document.getElementById('alerts-container');
        container.innerHTML = '';
        
        if (alerts.length === 0) {
            container.innerHTML = '<div class="empty-state"><i class="fas fa-bell-slash"></i><p>No alerts set. Add alerts to get notified.</p></div>';
            return;
        }
        
        alerts.forEach(alert => {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert-item fade-in ${alert.triggered ? 'triggered' : ''}`;
            alertDiv.innerHTML = `
                <div>
                    <strong>${alert.ticker}</strong> - ${alert.condition} ${alert.value}
                    ${alert.triggered ? '<span class="badge bg-success ms-2">Triggered</span>' : ''}
                </div>
                <button class="btn-modern btn-icon-sm" onclick="removeAlert(${alert.id})" title="Remove">
                    <i class="fas fa-times"></i>
                </button>
            `;
            container.appendChild(alertDiv);
        });
    } catch (error) {
        console.error('Error loading alerts:', error);
    }
}

// Show add alert modal
function showAddAlertModal() {
    const modalElement = document.getElementById('alertModal');
    if (!modalElement) return;
    
    const modal = new bootstrap.Modal(modalElement, {
        backdrop: true,
        keyboard: true,
        focus: true
    });
    modal.show();
    
    setTimeout(() => {
        modalElement.querySelectorAll('input, select, textarea, button').forEach(el => {
            el.style.pointerEvents = 'auto';
            el.disabled = false;
        });
        const firstInput = modalElement.querySelector('input');
        if (firstInput) firstInput.focus();
    }, 300);
}

// Add alert
async function addAlert() {
    const ticker = document.getElementById('alert-ticker').value;
    const condition = document.getElementById('alert-condition').value;
    const value = parseFloat(document.getElementById('alert-value').value);
    
    try {
        const response = await fetch('/api/alerts/add', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ticker, condition, value})
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            bootstrap.Modal.getInstance(document.getElementById('alertModal')).hide();
            document.getElementById('alert-form').reset();
            loadAlerts();
            showNotification('Alert added successfully', 'success');
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        console.error('Error adding alert:', error);
        showNotification('Error adding alert', 'error');
    }
}

// Remove alert
async function removeAlert(alertId) {
    try {
        const response = await fetch('/api/alerts/remove', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({alert_id: alertId})
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            loadAlerts();
            showNotification('Alert removed', 'success');
        }
    } catch (error) {
        console.error('Error removing alert:', error);
    }
}

// Show Upstox modal
function showUpstoxModal() {
    const modalElement = document.getElementById('upstoxModal');
    if (!modalElement) {
        console.error('Modal element not found');
        return;
    }
    
    // If any old overlay is blocking clicks, disable it.
    const mobileOverlay = document.getElementById('mobile-overlay');
    if (mobileOverlay) {
        mobileOverlay.classList.remove('active');
        mobileOverlay.style.pointerEvents = 'none';
    }

    // Ensure modal is properly initialized
    const modal = new bootstrap.Modal(modalElement, {
        backdrop: true,
        keyboard: true,
        focus: true
    });
    
    // Show modal
    modal.show();
    
    // Ensure backdrop never swallows clicks (common "Tab works but mouse doesn't" symptom)
    setTimeout(() => {
        // Remove mobile overlay if it exists
        document.querySelectorAll('.mobile-overlay, #mobile-overlay').forEach(overlay => {
            overlay.style.display = 'none';
            overlay.style.pointerEvents = 'none';
            overlay.style.zIndex = '-1';
            overlay.classList.remove('active');
        });
        
        // Fix backdrop
        document.querySelectorAll('.modal-backdrop').forEach(bd => {
            bd.style.pointerEvents = 'none';
            bd.style.zIndex = '1990';
        });
        modalElement.style.zIndex = '2000';
        
        // CRITICAL: Force all inputs to be clickable immediately
        const inputs = ['api-key', 'api-secret', 'redirect-uri', 'access-token'];
        inputs.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.style.setProperty('pointer-events', 'auto', 'important');
                el.style.setProperty('z-index', '99999', 'important');
                el.style.setProperty('position', 'relative', 'important');
                el.style.setProperty('cursor', 'text', 'important');
            }
        });
    }, 0);

    // Force enable all interactive elements - AGGRESSIVE FIX
    setTimeout(() => {
        // Remove ALL overlays that might block
        document.querySelectorAll('.overlay, .backdrop, [class*="overlay"], [class*="backdrop"]').forEach(overlay => {
            if (!overlay.classList.contains('modal-backdrop') && !overlay.closest('.modal')) {
                overlay.style.pointerEvents = 'none';
                overlay.style.display = 'none';
            }
        });
        
        // Force all inputs to be clickable
        const allInputs = modalElement.querySelectorAll('input, select, textarea, button, a, label');
        allInputs.forEach(el => {
            el.style.pointerEvents = 'auto';
            el.style.zIndex = '99999';
            el.style.position = 'relative';
            el.disabled = false;
            el.readOnly = false;
            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                el.style.cursor = 'text';
            } else {
                el.style.cursor = 'pointer';
            }
        });
        
        // Specifically target the form inputs
        ['api-key', 'api-secret', 'redirect-uri', 'access-token'].forEach(id => {
            const input = document.getElementById(id);
            if (input) {
                input.style.pointerEvents = 'auto';
                input.style.zIndex = '99999';
                input.style.position = 'relative';
                input.style.cursor = 'text';
                input.disabled = false;
                input.readOnly = false;
            }
        });
        
        // Focus first input and make it clickable
        const apiKeyInput = document.getElementById('api-key');
        if (apiKeyInput) {
            apiKeyInput.style.pointerEvents = 'auto';
            apiKeyInput.style.zIndex = '99999';
            apiKeyInput.style.position = 'relative';
            apiKeyInput.style.cursor = 'text';
            apiKeyInput.focus();
        }
        
        // Ensure modal body is clickable
        const modalBody = modalElement.querySelector('.modal-body-modern, .modal-body');
        if (modalBody) {
            modalBody.style.pointerEvents = 'auto';
            modalBody.style.zIndex = '1';
        }
    }, 50);
    
    // Also try after a longer delay for stubborn cases
    setTimeout(() => {
        modalElement.querySelectorAll('input, select, textarea, button, a').forEach(el => {
            el.style.pointerEvents = 'auto';
            el.style.zIndex = '99999';
            el.style.position = 'relative';
            el.style.cursor = el.tagName === 'INPUT' || el.tagName === 'SELECT' || el.tagName === 'TEXTAREA' ? 'text' : 'pointer';
            el.disabled = false;
            el.readOnly = false;
        });
    }, 200);
    
    // Final aggressive fix after modal is fully shown
    setTimeout(() => {
        const inputs = ['api-key', 'api-secret', 'redirect-uri', 'access-token'];
        inputs.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.style.setProperty('pointer-events', 'auto', 'important');
                el.style.setProperty('z-index', '99999', 'important');
                el.style.setProperty('position', 'relative', 'important');
                el.style.setProperty('cursor', 'text', 'important');
            }
        });
    }, 500);
}

// Connect Upstox
// Update API key preview in modal
function updateApiKeyPreview() {
    const apiKey = document.getElementById('api-key')?.value || '';
    const preview = document.getElementById('api-key-preview');
    if (preview) {
        preview.textContent = apiKey ? (apiKey.substring(0, 8) + '...') : 'your key';
    }
}

async function connectUpstox() {
    const apiKeyEl = document.getElementById('api-key');
    const apiSecretEl = document.getElementById('api-secret');
    const redirectUriEl = document.getElementById('redirect-uri');
    const accessTokenEl = document.getElementById('access-token');

    if (!apiKeyEl || !apiSecretEl) {
        showNotification('Connect form not ready. Please refresh the page (Ctrl+F5).', 'error');
        return;
    }

    const apiKey = apiKeyEl.value.trim();
    const apiSecret = apiSecretEl.value.trim();
    
    // Auto-detect redirect URI if not provided (fast - defaults to localhost)
    let redirectUri = redirectUriEl?.value?.trim();
    if (!redirectUri) {
        // Fast path: use localhost immediately to avoid delays
        // Network detection is slow and can cause timeouts
        redirectUri = 'http://localhost:5000/callback';
        if (redirectUriEl) {
            redirectUriEl.value = redirectUri;
            redirectUriEl.placeholder = redirectUri;
        }
        console.log('[DEBUG] Auto-detected redirect URI:', redirectUri);
    }
    
    const accessToken = accessTokenEl?.value?.trim() || null;
    
    if (!apiKey || !apiSecret) {
        showNotification('Please enter API Key and Secret', 'warning');
        (apiKey ? apiSecretEl : apiKeyEl).focus();
        return;
    }
    
    const connectBtn = document.getElementById('upstox-connect-btn');
    if (connectBtn) {
        connectBtn.disabled = true;
        connectBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Connecting...';
    }

    try {
        // Hide any previous auth URL box
        const authBox = document.getElementById('upstox-auth-box');
        if (authBox) authBox.style.display = 'none';

        // Add timeout to fetch request (30 seconds - OAuth flow should be instant, connection test is 10s)
        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
            console.warn('[TIMEOUT] Connection request taking too long, aborting...');
            console.warn('[TIMEOUT] This might indicate:');
            console.warn('[TIMEOUT] 1. Redirect URI mismatch (most common cause)');
            console.warn('[TIMEOUT] 2. Upstox API is slow');
            console.warn('[TIMEOUT] 3. Network issue');
            console.warn('[TIMEOUT] 4. Server error (check Flask terminal)');
            console.warn('[TIMEOUT] Expected redirect URI: ' + redirectUri);
            controller.abort();
        }, 30000);  // 30 seconds should be enough (OAuth is instant, connection test is 10s max)
        
        let response;
        try {
            response = await fetch('/api/upstox/connect', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    api_key: apiKey, 
                    api_secret: apiSecret, 
                    redirect_uri: redirectUri,
                    access_token: accessToken
                }),
                signal: controller.signal
            });
        } finally {
            clearTimeout(timeoutId);
        }
        
        // Check if response is OK and is JSON
        if (!response.ok) {
            const errorText = await response.text();
            console.error('[ERROR] Server error:', response.status, errorText);
            throw new Error(`Server error (${response.status}): ${errorText.substring(0, 200)}`);
        }
        
        // Check content type before parsing JSON
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const errorText = await response.text();
            console.error('[ERROR] Non-JSON response:', contentType, errorText.substring(0, 200));
            throw new Error(`Server returned HTML instead of JSON. This usually means the Flask server has an error. Check the server terminal for details.`);
        }
        
        const result = await response.json();
        console.log('[DEBUG] Connect response:', result);
        
        if (result.status === 'success') {
            const statusEl = document.getElementById('connection-status');
            if (statusEl) {
                statusEl.innerHTML = '<i class="fas fa-circle"></i><span class="mobile-hide">Connected</span>';
                statusEl.classList.add('connected');
            }
            const modal = bootstrap.Modal.getInstance(document.getElementById('upstoxModal'));
            if (modal) modal.hide();
            loadOrders();
            loadHoldings();
            showNotification('✅ Upstox connected successfully!', 'success');
        } else if (result.status === 'auth_required') {
            // IMPORTANT: Restore button immediately - OAuth requires user action, not waiting
            if (connectBtn) {
                connectBtn.disabled = false;
                connectBtn.innerHTML = '<i class="fas fa-plug"></i> Connect';
            }
            
            // Show critical redirect URI warning
            if (result.redirect_uri) {
                const redirectWarning = `⚠️ CRITICAL: Add this EXACT redirect URI in Upstox Portal:\n\n${result.redirect_uri}\n\nPortal: ${result.upstox_portal_url || 'https://account.upstox.com/developer/apps'}`;
                console.warn('[CRITICAL] Redirect URI check:', redirectWarning);
                
                // Show detailed warning with copy button
                const warningMsg = `⚠️ Before continuing, add this redirect URI in Upstox Portal:\n${result.redirect_uri}`;
                showNotification(warningMsg, 'warning');
                
                // Show redirect URI in modal for easy copying
                const redirectInput = document.getElementById('redirect-uri');
                if (redirectInput && !redirectInput.value) {
                    redirectInput.value = result.redirect_uri;
                    redirectInput.style.borderColor = '#f59e0b';
                    redirectInput.title = 'Copy this exact value to Upstox Developer Portal';
                }
                
                // Ask user to confirm before opening auth URL
                const proceed = confirm(
                    `⚠️ IMPORTANT: Before clicking OK, verify:\n\n` +
                    `1. Redirect URI "${result.redirect_uri}" is added in Upstox Developer Portal\n` +
                    `2. API Key "${result.api_key || 'your key'}" is correct\n\n` +
                    `Click OK to open authorization page, or Cancel to check settings first.`
                );
                
                if (!proceed) {
                    if (connectBtn) {
                        connectBtn.disabled = false;
                        connectBtn.innerHTML = '<i class="fas fa-plug"></i> Connect';
                    }
                    showNotification('ℹ️ Please verify redirect URI in Upstox Portal first', 'info');
                    return;
                }
            }
            
            // Show authorization URL
            console.log('[DEBUG] Opening auth URL:', result.auth_url);
            console.log('[DEBUG] Redirect URI being used:', result.redirect_uri);
            console.log('[DEBUG] API Key (first 8 chars):', result.api_key);
            
            const authWindow = window.open(result.auth_url, 'Upstox Authorization', 'width=600,height=700,scrollbars=yes');
            if (!authWindow) {
                // Corporate browsers often block popups: show in-modal fallback
                const urlInput = document.getElementById('upstox-auth-url');
                const box = document.getElementById('upstox-auth-box');
                if (urlInput && box) {
                    urlInput.value = result.auth_url;
                    box.style.display = 'block';
                }
                showNotification('⚠️ Popup blocked. Click "Copy" button to open authorization URL manually.', 'warning');
                return;
            }
            
            // Monitor for callback
            let checkCount = 0;
            const maxChecks = 300; // 5 minutes max
            const checkInterval = setInterval(() => {
                checkCount++;
                if (authWindow.closed) {
                    clearInterval(checkInterval);
                    console.log('[DEBUG] Auth window closed, testing connection...');
                    // Test connection after window closes
                    setTimeout(() => {
                        testUpstoxConnection();
                    }, 1000);
                } else if (checkCount >= maxChecks) {
                    clearInterval(checkInterval);
                    showNotification('Authorization window open too long. Please complete authorization or close manually.', 'warning');
                }
            }, 1000);
            
            showNotification('🔐 Please authorize the app in the popup window', 'info');
        } else {
            const errorMsg = result.message || result.error || 'Connection failed';
            const errorDetails = result.details || result.error_type || '';
            console.error('[ERROR] Connection failed:', errorMsg, errorDetails);
            showNotification(`❌ ${errorMsg}${errorDetails ? ' (' + errorDetails + ')' : ''}`, 'error');
            
            // Show helpful hints with exact redirect URI
            if (errorMsg.includes('redirect') || errorMsg.includes('URI') || errorMsg.includes('mismatch')) {
                setTimeout(() => {
                    const redirectUri = result.redirect_uri || 'http://localhost:5000/callback';
                    const tipMessage = `💡 Tip: Add this EXACT redirect URI in Upstox Portal: ${redirectUri}\nPortal: https://account.upstox.com/developer/apps`;
                    showNotification(tipMessage, 'warning', 10000); // Show for 10 seconds
                }, 2000);
            }
        }
    } catch (error) {
        console.error('[ERROR] Connect exception:', error);
        
        let errorMsg = 'Connection failed';
        if (error.name === 'AbortError') {
            const redirectInput = document.getElementById('redirect-uri');
            const redirectUri = redirectInput?.value || 'http://localhost:5000/callback';
            errorMsg = `Connection timeout - Request took too long.\n\nMost common cause: Redirect URI mismatch\n\n✅ Verify in Upstox Portal:\n1. Go to: https://account.upstox.com/developer/apps\n2. Find your app (API Key: ${apiKey.substring(0, 8)}...)\n3. Add this EXACT redirect URI:\n   ${redirectUri}\n4. Save and try connecting again\n\nNote: The URI must match EXACTLY (including http:// and /callback)`;
        } else if (error.message.includes('fetch')) {
            errorMsg = `Network error: ${error.message}. Make sure the server is running on port 5000.`;
        } else {
            errorMsg = `Error: ${error.message}`;
        }
        
        showNotification(`❌ ${errorMsg}`, 'error', 15000); // Show longer for timeout errors
        
        // Show helpful hints with exact redirect URI
        if (error.name === 'AbortError') {
            setTimeout(() => {
                const redirectInput = document.getElementById('redirect-uri');
                const redirectUri = redirectInput?.value || 'http://localhost:5000/callback';
                const tipMessage = `💡 Quick Fix: Copy this EXACT URI to Upstox Portal:\n${redirectUri}\n\nPortal: https://account.upstox.com/developer/apps`;
                showNotification(tipMessage, 'warning', 12000);
            }, 2000);
        }
    } finally {
        // Restore button
        if (connectBtn) {
            connectBtn.disabled = false;
            connectBtn.innerHTML = '<i class="fas fa-plug"></i> Connect';
        }
    }
}

function copyUpstoxAuthUrl() {
    const input = document.getElementById('upstox-auth-url');
    if (!input || !input.value) return;
    input.select();
    input.setSelectionRange(0, 99999);
    try {
        document.execCommand('copy');
        showNotification('Authorization link copied', 'success');
    } catch (e) {
        showNotification('Copy failed. Please copy manually.', 'warning');
    }
}

function openUpstoxAuthUrl() {
    const input = document.getElementById('upstox-auth-url');
    if (!input || !input.value) return;
    window.open(input.value, '_blank', 'noopener,noreferrer');
}

// Debug helper: on company laptops, hidden overlays can swallow clicks.
// Enable by appending ?debug=1 to the dashboard URL.
(function attachClickInspector() {
    try {
        const params = new URLSearchParams(window.location.search);
        if (!params.has('debug')) return;

        document.addEventListener('click', (e) => {
            const el = document.elementFromPoint(e.clientX, e.clientY);
            if (!el) return;
            const cs = window.getComputedStyle(el);
            const msg = `Top element: ${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''}${el.className ? '.' + String(el.className).trim().split(/\s+/).join('.') : ''} | z=${cs.zIndex} | pe=${cs.pointerEvents}`;
            // Log to console and show small toast
            console.log('[click-inspector]', msg, el);
            showNotification(msg, 'info');
        }, true);

        showNotification('Debug click-inspector enabled (?debug=1). Click anywhere to see top element.', 'info');
    } catch (e) {
        // ignore
    }
})();

// Test Upstox connection
async function testUpstoxConnection() {
    try {
        const response = await fetch('/api/upstox/test');
        const result = await response.json();
        
        if (result.status === 'success') {
            const statusEl = document.getElementById('connection-status');
            statusEl.innerHTML = '<i class="fas fa-circle"></i><span>Connected</span>';
            statusEl.classList.add('connected');
            loadOrders();
            showNotification('Upstox connection verified', 'success');
        } else {
            showNotification('Connection test failed: ' + result.message, 'error');
        }
    } catch (error) {
        console.error('Error testing connection:', error);
    }
}

// Load orders
// Phase 2.2: Enhanced order loading with status indicators and actions
async function loadOrders() {
    try {
        const response = await fetch('/api/upstox/orders');
        const orders = await response.json();
        const tbody = document.getElementById('orders-table-body');
        
        if (!tbody) {
            console.error('Orders table body not found');
            return;
        }
        
        if (orders.error) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted">${orders.error}</td></tr>`;
            return;
        }
        
        if (!orders || orders.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No orders found</td></tr>';
            return;
        }
        
        let html = '';
        orders.forEach(order => {
            const orderId = order.order_id || order.orderId || order.instrument_token || 'N/A';
            const symbol = order.tradingsymbol || order.symbol || order.instrument_token || 'N/A';
            const type = order.transaction_type || order.type || 'N/A';
            const qty = order.quantity || order.qty || 0;
            const price = order.price || order.limit_price || order.trigger_price || '-';
            const status = order.status || 'PENDING';
            const timestamp = order.order_timestamp || order.timestamp || '-';
            
            // Phase 2.2: Status indicator class
            const statusClass = getOrderStatusClass(status);
            const statusText = getOrderStatusText(status);
            
            // Phase 2.2: Action buttons (only for pending orders)
            const canModify = status === 'PENDING' || status === 'OPEN' || status === 'TRANSIT';
            const canCancel = canModify;
            
            html += `
                <tr class="fade-in">
                    <td>${orderId}</td>
                    <td>${symbol}</td>
                    <td>${type}</td>
                    <td>${qty}</td>
                    <td>${price === '-' ? '-' : '₹' + parseFloat(price).toFixed(2)}</td>
                    <td><span class="order-status ${statusClass}">${statusText}</span></td>
                    <td>${formatTimestamp(timestamp)}</td>
                    <td>
                        <div class="order-actions">
                            ${canModify ? `<button class="btn-modern btn-icon-sm btn-primary" onclick="showModifyOrderModal('${orderId}')" title="Modify">
                                <i class="fas fa-edit"></i>
                            </button>` : ''}
                            ${canCancel ? `<button class="btn-modern btn-icon-sm btn-danger" onclick="cancelOrder('${orderId}')" title="Cancel">
                                <i class="fas fa-times"></i>
                            </button>` : ''}
                            <button class="btn-modern btn-icon-sm btn-secondary" onclick="viewOrderDetails('${orderId}')" title="View Details">
                                <i class="fas fa-eye"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        });
        tbody.innerHTML = html;
    } catch (error) {
        console.error('Error loading orders:', error);
        const tbody = document.getElementById('orders-table-body');
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">Error loading orders: ${error.message}</td></tr>`;
        }
    }
}

// Phase 2.2: Get order status CSS class
function getOrderStatusClass(status) {
    const statusUpper = (status || '').toUpperCase();
    if (statusUpper === 'COMPLETE' || statusUpper === 'EXECUTED' || statusUpper === 'FILLED') {
        return 'executed';
    } else if (statusUpper === 'CANCELLED' || statusUpper === 'CANCELED') {
        return 'cancelled';
    } else if (statusUpper === 'REJECTED' || statusUpper === 'FAILED') {
        return 'rejected';
    } else {
        return 'pending';
    }
}

// Phase 2.2: Get order status display text
function getOrderStatusText(status) {
    const statusUpper = (status || '').toUpperCase();
    if (statusUpper === 'COMPLETE' || statusUpper === 'EXECUTED' || statusUpper === 'FILLED') {
        return 'EXECUTED';
    } else if (statusUpper === 'CANCELLED' || statusUpper === 'CANCELED') {
        return 'CANCELLED';
    } else if (statusUpper === 'REJECTED' || statusUpper === 'FAILED') {
        return 'REJECTED';
    } else {
        return 'PENDING';
    }
}

// Phase 2.2: Format timestamp
function formatTimestamp(timestamp) {
    if (!timestamp || timestamp === '-') return '-';
    try {
        const date = new Date(timestamp);
        return date.toLocaleString('en-IN', { 
            day: '2-digit', 
            month: '2-digit', 
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        return timestamp;
    }
}

// Phase 2.2: Show modify order modal
function showModifyOrderModal(orderId) {
    // Fetch order details first
    fetch(`/api/orders/${orderId}`)
        .then(response => response.json())
        .then(order => {
            if (order.error) {
                showNotification(order.error, 'error');
                return;
            }
            
            // Populate modal
            document.getElementById('modify-order-id').value = orderId;
            document.getElementById('modify-symbol').value = order.tradingsymbol || order.symbol || '';
            document.getElementById('modify-quantity').value = order.quantity || order.qty || '';
            document.getElementById('modify-order-type').value = order.order_type || order.orderType || 'MARKET';
            document.getElementById('modify-price').value = order.price || order.limit_price || '';
            
            // Show/hide price input based on order type
            const orderType = document.getElementById('modify-order-type').value;
            const priceContainer = document.getElementById('modify-price-container');
            if (orderType === 'MARKET') {
                priceContainer.style.display = 'none';
            } else {
                priceContainer.style.display = 'block';
            }
            
            // Show modal
            const modalElement = document.getElementById('orderModifyModal');
            const modal = new bootstrap.Modal(modalElement, {
                backdrop: true,
                keyboard: true,
                focus: true
            });
            modal.show();
        })
        .catch(error => {
            console.error('Error fetching order details:', error);
            showNotification('Error loading order details', 'error');
        });
    
    // Handle order type change
    document.getElementById('modify-order-type').addEventListener('change', function() {
        const priceContainer = document.getElementById('modify-price-container');
        if (this.value === 'MARKET') {
            priceContainer.style.display = 'none';
        } else {
            priceContainer.style.display = 'block';
        }
    });
}

// Phase 2.2: Submit order modification
async function submitOrderModification() {
    const orderId = document.getElementById('modify-order-id').value;
    const quantity = parseInt(document.getElementById('modify-quantity').value);
    const orderType = document.getElementById('modify-order-type').value;
    const price = document.getElementById('modify-price').value ? parseFloat(document.getElementById('modify-price').value) : null;
    
    if (!orderId || !quantity) {
        showNotification('Please fill all required fields', 'warning');
        return;
    }
    
    if ((orderType === 'LIMIT' || orderType === 'SL') && !price) {
        showNotification('Price is required for LIMIT and SL orders', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`/api/orders/${orderId}/modify`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                quantity: quantity,
                order_type: orderType,
                price: price
            })
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            bootstrap.Modal.getInstance(document.getElementById('orderModifyModal')).hide();
            showNotification('Order modified successfully', 'success');
            loadOrders();
        } else {
            showNotification(result.error || 'Failed to modify order', 'error');
        }
    } catch (error) {
        console.error('Error modifying order:', error);
        showNotification('Error modifying order: ' + error.message, 'error');
    }
}

// Phase 2.2: Cancel order
async function cancelOrder(orderId) {
    if (!confirm('Are you sure you want to cancel this order?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/orders/${orderId}/cancel`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showNotification('Order cancelled successfully', 'success');
            loadOrders();
        } else {
            showNotification(result.error || 'Failed to cancel order', 'error');
        }
    } catch (error) {
        console.error('Error cancelling order:', error);
        showNotification('Error cancelling order: ' + error.message, 'error');
    }
}

// Phase 2.2: View order details
async function viewOrderDetails(orderId) {
    try {
        const response = await fetch(`/api/orders/${orderId}`);
        const order = await response.json();
        
        if (order.error) {
            showNotification(order.error, 'error');
            return;
        }
        
        // Show order details in a modal or alert
        const details = `
Order ID: ${order.order_id || orderId}
Symbol: ${order.tradingsymbol || order.symbol || 'N/A'}
Type: ${order.transaction_type || order.type || 'N/A'}
Quantity: ${order.quantity || order.qty || 'N/A'}
Price: ${order.price || order.limit_price || 'N/A'}
Status: ${order.status || 'N/A'}
Timestamp: ${order.order_timestamp || order.timestamp || 'N/A'}
        `;
        
        alert(details);
    } catch (error) {
        console.error('Error fetching order details:', error);
        showNotification('Error loading order details', 'error');
    }
}

// Show place order modal
function showPlaceOrderModal() {
    const modalElement = document.getElementById('orderModal');
    if (!modalElement) return;
    
    if (selectedTicker) {
        const tickerInput = document.getElementById('order-ticker');
        if (tickerInput) tickerInput.value = selectedTicker;
    }
    
    const modal = new bootstrap.Modal(modalElement, {
        backdrop: true,
        keyboard: true,
        focus: true
    });
    modal.show();
    
    setTimeout(() => {
        modalElement.querySelectorAll('input, select, textarea, button').forEach(el => {
            el.style.pointerEvents = 'auto';
            el.disabled = false;
        });
        const firstInput = modalElement.querySelector('input');
        if (firstInput) firstInput.focus();
    }, 300);
}

// Place order
// Phase 2.2: Place order with confirmation
async function placeOrder() {
    const ticker = document.getElementById('order-ticker').value;
    const transactionType = document.getElementById('order-type').value;
    const quantity = parseInt(document.getElementById('order-quantity').value);
    const orderType = document.getElementById('order-order-type').value;
    const price = document.getElementById('order-price').value ? parseFloat(document.getElementById('order-price').value) : null;
    
    if (!ticker || !quantity) {
        showNotification('Please fill all required fields', 'warning');
        return;
    }
    
    // Get current price for cost estimation
    let currentPrice = price;
    if (!currentPrice) {
        try {
            const priceResponse = await fetch(`/api/prices`);
            const prices = await priceResponse.json();
            if (prices[ticker] && prices[ticker].price) {
                currentPrice = prices[ticker].price;
            } else {
                // Ticker not found in prices response - use fallback
                currentPrice = price || 100;
            }
        } catch (e) {
            // Use price from input or default
            currentPrice = price || 100;
        }
    }
    
    // Ensure currentPrice is a valid number
    if (isNaN(currentPrice) || currentPrice <= 0) {
        currentPrice = price || 100;
    }
    
    const estimatedCost = currentPrice * quantity;
    const estimatedCharges = estimatedCost * 0.001; // 0.1% brokerage estimate
    
    // Check paper trading mode
    let paperMode = false;
    try {
        const statusResponse = await fetch('/api/paper-trading/status');
        const statusData = await statusResponse.json();
        paperMode = statusData.paper_trading_mode;
    } catch (e) {
        // Default to false if check fails
    }
    
    // Prepare order details for confirmation
    const orderDetails = {
        ticker,
        transaction_type: transactionType,
        quantity,
        order_type: orderType,
        price: currentPrice,
        estimated_cost: estimatedCost,
        estimated_charges: estimatedCharges,
        risk_warning: paperMode ? null : '⚠️ LIVE TRADING MODE: This order will execute with REAL MONEY.'
    };
    
    // Show confirmation dialog
    const onConfirm = async () => {
        try {
            const response = await fetch('/api/upstox/place_order', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ticker, transaction_type: transactionType, quantity, order_type: orderType, price})
            });
            
            const result = await response.json();
            if (result.status === 'success') {
                bootstrap.Modal.getInstance(document.getElementById('orderModal')).hide();
                document.getElementById('order-form').reset();
                loadOrders();
                loadHoldings(); // Refresh holdings after order
                if (result.paper_trading) {
                    showNotification(result.message || 'Paper order executed!', 'info');
                    // Show portfolio summary
                    if (result.portfolio) {
                        const portfolio = result.portfolio;
                        setTimeout(() => {
                            showNotification(
                                `Paper Portfolio: Cash: ₹${portfolio.cash_balance.toFixed(2)} | Positions: ₹${portfolio.position_value.toFixed(2)} | Total: ₹${portfolio.total_value.toFixed(2)} | P&L: ${portfolio.total_pnl_pct >= 0 ? '+' : ''}${portfolio.total_pnl_pct.toFixed(2)}%`,
                                'info'
                            );
                        }, 1000);
                    }
                } else {
                    showNotification(result.message || '✅ LIVE ORDER PLACED SUCCESSFULLY!', 'success');
                }
            } else {
                showNotification(result.error || 'Failed to place order', 'error');
            }
        } catch (error) {
            console.error('Error placing order:', error);
            showNotification('Error placing order: ' + error.message, 'error');
        }
    };
    
    // Use two-step confirmation for market orders
    if (orderType === 'MARKET' && typeof orderConfirmation !== 'undefined') {
        orderConfirmation.showTwoStepConfirmation(orderDetails, onConfirm);
    } else if (typeof orderConfirmation !== 'undefined') {
        orderConfirmation.showConfirmation(orderDetails, onConfirm);
    } else {
        // Fallback to simple confirmation
        if (!paperMode && !confirm('⚠️ LIVE TRADING MODE\n\nThis will place a REAL order with REAL money.\n\nAre you sure you want to proceed?')) {
            return;
        }
        onConfirm();
    }
}

// Refresh signals
function refreshSignals() {
    if (selectedTicker) {
        showLevels(selectedTicker);
    }
}

// Notification system - Make globally available
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type} fade-in`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-left: 4px solid ${type === 'success' ? 'var(--success-color)' : type === 'error' ? 'var(--danger-color)' : 'var(--info-color)'};
        border-radius: 8px;
        padding: 1rem 1.5rem;
        box-shadow: var(--shadow-lg);
        z-index: 10000;
        max-width: 400px;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => notification.remove(), 300);
        }, 3000);
}

// Refresh Holdings
async function refreshHoldings() {
    try {
        showNotification('Refreshing holdings...', 'info');
        
        // Update portfolio summary
        await updatePortfolioSummary();
        
        // Record a portfolio snapshot
        try {
            await fetch('/api/portfolio/record_snapshot', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            });
        } catch (e) {
            console.log('Note: Could not record snapshot (may need holdings data)');
        }
        
        // Refresh prices
        await updatePrices();
        
        showNotification('✅ Holdings refreshed!', 'success');
    } catch (error) {
        console.error('Error refreshing holdings:', error);
        showNotification('❌ Error refreshing holdings', 'error');
    }
}

// Make functions globally available for other scripts
window.showNotification = showNotification;
window.showUpstoxModal = showUpstoxModal;
window.setTheme = setTheme;
window.toggleTheme = toggleTheme;
window.refreshHoldings = refreshHoldings;
window.updatePortfolioSummary = updatePortfolioSummary;

// Update Portfolio Summary (Overall P&L and Day P&L)
async function updatePortfolioSummary() {
    try {
        const response = await fetch('/api/portfolio/summary');
        const data = await response.json();
        
        if (data.status === 'success') {
            // Update Overall P&L
            const overallPnlEl = document.getElementById('overall-pnl');
            if (overallPnlEl) {
                const pnl = data.total_pnl || 0;
                const pnlPct = data.total_pnl_pct || 0;
                const pnlClass = pnl >= 0 ? 'price-up' : 'price-down';
                const sign = pnl >= 0 ? '+' : '';
                
                overallPnlEl.innerHTML = `<span class="${pnlClass}">${sign}₹${Math.abs(pnl).toFixed(2)} (${sign}${pnlPct.toFixed(2)}%)</span>`;
            }
            
            // Update Day P&L
            const dayPnlEl = document.getElementById('day-pnl');
            if (dayPnlEl) {
                const dayPnl = data.day_pnl || 0;
                const dayPnlPct = data.day_pnl_pct || 0;
                const pnlClass = dayPnl >= 0 ? 'price-up' : 'price-down';
                const sign = dayPnl >= 0 ? '+' : '';
                
                dayPnlEl.innerHTML = `<span class="${pnlClass}">${sign}₹${Math.abs(dayPnl).toFixed(2)} (${sign}${dayPnlPct.toFixed(2)}%)</span>`;
            }
            
            // Update portfolio value if element exists
            const portfolioValueEl = document.getElementById('portfolio-value');
            if (portfolioValueEl) {
                portfolioValueEl.textContent = `₹${(data.total_value || 0).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
            }
            
            // Update cash balance if element exists
            const cashBalanceEl = document.getElementById('cash-balance');
            if (cashBalanceEl) {
                cashBalanceEl.textContent = `₹${(data.cash_balance || 0).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
            }
        }
    } catch (error) {
        console.error('Error updating portfolio summary:', error);
        // Set default values on error
        const dayPnlEl = document.getElementById('day-pnl');
        if (dayPnlEl) {
            dayPnlEl.innerHTML = '<span class="text-muted">₹0.00 (+0.00%)</span>';
        }
    }
}

// Phase 2.3: Update positions P&L with real-time prices (placeholder - will be implemented in position-pnl task)
function updatePositionsPnL(instrumentKey, currentPrice) {
    // TODO: Implement real-time P&L calculation
    // This will be properly implemented in the position P&L calculator module
    try {
        const positionsTable = document.querySelector('#positions-table tbody');
        if (!positionsTable) return;
        
        const rows = positionsTable.querySelectorAll('tr');
        rows.forEach(row => {
            const rowInstrumentKey = row.getAttribute('data-instrument-key');
            if (rowInstrumentKey === instrumentKey) {
                const avgPrice = parseFloat(row.getAttribute('data-avg-price') || 0);
                const quantity = parseFloat(row.getAttribute('data-quantity') || 0);
                
                // Fix Bug 2: Include short positions (negative quantities) in P&L updates
                if (avgPrice > 0 && quantity != 0) {
                    const pnl = (currentPrice - avgPrice) * quantity;
                    const pnlPct = ((currentPrice - avgPrice) / avgPrice) * 100;
                    
                    const pnlCell = row.querySelector('.pnl-cell');
                    if (pnlCell) {
                        const pnlClass = pnl >= 0 ? 'text-success' : 'text-danger';
                        pnlCell.className = `pnl-cell ${pnlClass}`;
                        pnlCell.textContent = `₹${pnl.toFixed(2)} (${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}%)`;
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error updating positions P&L:', error);
    }
}

// Auto Trading Controls
let autoTradingStatusInterval = null;
let autoTradingCardVisible = false;

function toggleAutoTrading() {
    const card = document.getElementById('auto-trading-card');
    const btn = document.getElementById('auto-trading-toggle-btn');
    const label = document.getElementById('auto-trading-label');
    
    if (!card) return;
    
    autoTradingCardVisible = !autoTradingCardVisible;
    card.style.display = autoTradingCardVisible ? 'block' : 'none';
    
    if (autoTradingCardVisible) {
        btn.classList.add('active');
        updateAutoTradingStatus();
        if (!autoTradingStatusInterval) {
            autoTradingStatusInterval = setInterval(updateAutoTradingStatus, 3000);
        }
    } else {
        btn.classList.remove('active');
        if (autoTradingStatusInterval) {
            clearInterval(autoTradingStatusInterval);
            autoTradingStatusInterval = null;
        }
    }
}

async function startAutoTrading() {
    try {
        const response = await fetch('/api/auto-trading/start', { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            showNotification(data.message || 'Auto trading started', 'success');
            updateAutoTradingStatus();
        } else {
            showNotification(data.message || data.error || 'Failed to start', 'error');
        }
    } catch (error) {
        showNotification('Error starting auto trading: ' + error.message, 'error');
    }
}

async function stopAutoTrading() {
    if (!confirm('Stop auto trading? This will halt all automated trading activities.')) {
        return;
    }
    try {
        const response = await fetch('/api/auto-trading/stop', { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            showNotification(data.message || 'Auto trading stopped', 'success');
            updateAutoTradingStatus();
        } else {
            showNotification(data.message || data.error || 'Failed to stop', 'error');
        }
    } catch (error) {
        showNotification('Error stopping auto trading: ' + error.message, 'error');
    }
}

async function pauseAutoTrading() {
    try {
        const response = await fetch('/api/auto-trading/pause', { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            showNotification(data.message || 'Auto trading paused', 'warning');
            updateAutoTradingStatus();
        } else {
            showNotification(data.message || data.error || 'Failed to pause', 'error');
        }
    } catch (error) {
        showNotification('Error pausing auto trading: ' + error.message, 'error');
    }
}

async function updateAutoTradingStatus() {
    try {
        const response = await fetch('/api/auto-trading/status');
        const data = await response.json();
        
        if (!data) return;
        
        const isRunning = data.is_running || false;
        const indicator = document.getElementById('auto-trading-status-indicator');
        const statusText = document.getElementById('auto-trading-status-text');
        const icon = document.getElementById('auto-trading-icon');
        const label = document.getElementById('auto-trading-label');
        const btnStart = document.getElementById('btn-auto-start');
        const btnPause = document.getElementById('btn-auto-pause');
        const btnStop = document.getElementById('btn-auto-stop');
        
        if (indicator && statusText) {
            if (isRunning) {
                indicator.querySelector('i').style.color = '#28a745';
                statusText.textContent = 'Running';
                if (icon) icon.style.color = '#28a745';
                if (label) label.textContent = 'Auto: ON';
                if (btnStart) btnStart.style.display = 'none';
                if (btnPause) btnPause.style.display = 'inline-block';
                if (btnStop) btnStop.style.display = 'inline-block';
            } else {
                indicator.querySelector('i').style.color = '#dc3545';
                statusText.textContent = 'Stopped';
                if (icon) icon.style.color = '#dc3545';
                if (label) label.textContent = 'Auto: OFF';
                if (btnStart) btnStart.style.display = 'inline-block';
                if (btnPause) btnPause.style.display = 'none';
                if (btnStop) btnStop.style.display = 'none';
            }
        }
        
        // Update metrics
        const signalsEl = document.getElementById('auto-trading-signals');
        const executedEl = document.getElementById('auto-trading-executed');
        const accuracyEl = document.getElementById('auto-trading-accuracy');
        const winrateEl = document.getElementById('auto-trading-winrate');
        const positionsEl = document.getElementById('auto-trading-positions');
        const signalSourceEl = document.getElementById('auto-trading-signal-source');
        const confidenceEl = document.getElementById('auto-trading-confidence');
        
        if (signalsEl) signalsEl.textContent = data.signals_generated || 0;
        if (executedEl) executedEl.textContent = data.executed_signals_count || 0;
        if (accuracyEl) {
            const acc = data.accuracy_30d;
            accuracyEl.textContent = acc != null ? acc.toFixed(1) + '%' : '—';
        }
        if (winrateEl) {
            const wr = data.win_rate_30d;
            winrateEl.textContent = wr != null ? wr.toFixed(1) + '%' : '—';
        }
        if (positionsEl) positionsEl.textContent = data.open_positions || 0;
        if (signalSourceEl) {
            const src = (data.signal_source || 'elite').toUpperCase();
            signalSourceEl.textContent = src === 'QUANT_ENSEMBLE' ? 'QUANT (All)' : src;
        }
        if (confidenceEl) {
            confidenceEl.textContent = (data.confidence_threshold || 0.70).toFixed(2);
        }
    } catch (error) {
        console.error('Error updating auto trading status:', error);
    }
}

// Verify Redirect URI format
async function verifyRedirectURI() {
    const apiKey = document.getElementById('api-key')?.value || '';
    const redirectUri = document.getElementById('redirect-uri')?.value || 'http://localhost:5000/callback';
    
    try {
        const response = await fetch('/api/upstox/verify-redirect-uri', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({redirect_uri: redirectUri, api_key: apiKey})
        });
        const result = await response.json();
        
        if (result.status === 'success') {
            let msg = '✅ Redirect URI format is valid!\n\n';
            msg += 'Next steps:\n';
            msg += `1. Go to: ${result.instructions.step1}\n`;
            msg += `2. ${result.instructions.step2}\n`;
            msg += `3. ${result.instructions.step3}\n`;
            msg += `4. ${result.instructions.step4}\n`;
            msg += `   ${result.instructions.redirect_uri}\n`;
            msg += `5. ${result.instructions.step5}\n`;
            msg += `6. ${result.instructions.step6}\n`;
            showNotification(msg, 'success', 15000);
        } else {
            showNotification(`❌ ${result.message}`, 'error');
        }
    } catch (error) {
        showNotification('Error verifying redirect URI: ' + error.message, 'error');
    }
}

// Copy to clipboard helper
function copyToClipboard(text, element) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            const original = element.textContent;
            element.textContent = '✓ Copied!';
            element.style.background = '#d1fae5';
            setTimeout(() => {
                element.textContent = original;
                element.style.background = '#fff';
            }, 2000);
        }).catch(() => {
            fallbackCopy(text, element);
        });
    } else {
        fallbackCopy(text, element);
    }
}

function fallbackCopy(text, element) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    try {
        document.execCommand('copy');
        const original = element.textContent;
        element.textContent = '✓ Copied!';
        element.style.background = '#d1fae5';
        setTimeout(() => {
            element.textContent = original;
            element.style.background = '#fff';
        }, 2000);
    } catch (err) {
        showNotification('Failed to copy. Please copy manually: ' + text, 'warning');
    }
    document.body.removeChild(textarea);
}

// Make functions globally available and override toggle to save state
(function() {
    window.toggleAutoTrading = toggleAutoTrading;
    window.startAutoTrading = startAutoTrading;
    window.stopAutoTrading = stopAutoTrading;
    window.pauseAutoTrading = pauseAutoTrading;
    window.updateAutoTradingStatus = updateAutoTradingStatus;
    window.verifyRedirectURI = verifyRedirectURI;
    window.copyToClipboard = copyToClipboard;
    window.updateApiKeyPreview = updateApiKeyPreview;
    
    // Override toggle to save state
    const originalToggle = toggleAutoTrading;
    window.toggleAutoTrading = function() {
        originalToggle();
        localStorage.setItem('autoTradingCardVisible', autoTradingCardVisible.toString());
    };
})();
