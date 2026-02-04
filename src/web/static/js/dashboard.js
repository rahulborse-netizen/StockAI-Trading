// Modern Dashboard JavaScript with Enhanced Interactivity

let priceUpdateInterval = null;
let selectedTicker = null;
let currentTheme = 'dark';

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'dark';
    setTheme(savedTheme);
    
    // Initialize components
    loadWatchlist();
    loadTopStocks();
    loadAlerts();
    loadOrders();
    updateStats();
    
    // Auto-refresh prices every 30 seconds
    priceUpdateInterval = setInterval(() => {
        updatePrices();
        updateStats();
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

// Theme Toggle
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

// Update Stats
async function updateStats() {
    try {
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
        
        // Update portfolio value
        const portfolioEl = document.getElementById('portfolio-value');
        if (portfolioEl) {
            portfolioEl.textContent = `₹${totalValue.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        }
        
        // Update P&L
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

// Update prices with modern display
async function updatePrices() {
    try {
        const response = await fetch('/api/prices');
        const prices = await response.json();
        
        Object.keys(prices).forEach(ticker => {
            const priceInfo = document.getElementById(`price-${ticker}`);
            if (!priceInfo) return;
            
            if (prices[ticker].error) {
                const errorMsg = prices[ticker].error.length > 60 
                    ? prices[ticker].error.substring(0, 60) + '...' 
                    : prices[ticker].error;
                priceInfo.innerHTML = `
                    <div class="price-value" style="color: var(--text-muted); font-size: 1.25rem;">N/A</div>
                    <div class="price-change" style="color: var(--danger-color); font-size: 0.75rem; margin-top: 0.5rem;">
                        <i class="fas fa-exclamation-triangle"></i>
                        <span style="display: block; margin-top: 0.25rem;">${errorMsg}</span>
                    </div>
                `;
                return;
            }
            
            // Show warning if using cached data
            if (prices[ticker].warning) {
                console.warn(`${ticker}: ${prices[ticker].warning}`);
            }
            
            const price = prices[ticker];
            const changeClass = price.change >= 0 ? 'price-up' : 'price-down';
            const changeIcon = price.change >= 0 ? 'fa-arrow-up' : 'fa-arrow-down';
            
            priceInfo.innerHTML = `
                <div class="price-value">₹${price.price.toFixed(2)}</div>
                <div class="price-change ${changeClass}">
                    <i class="fas ${changeIcon}"></i>
                    <span>${price.change >= 0 ? '+' : ''}${price.change.toFixed(2)} (${price.change_pct >= 0 ? '+' : ''}${price.change_pct.toFixed(2)}%)</span>
                </div>
                <small class="text-muted">Vol: ${price.volume.toLocaleString()}</small>
            `;
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

        // Add timeout to fetch request (30 seconds for OAuth flow)
        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
            console.warn('[TIMEOUT] Connection request taking too long, aborting...');
            console.warn('[TIMEOUT] This might indicate:');
            console.warn('[TIMEOUT] 1. Flask server is not responding');
            console.warn('[TIMEOUT] 2. Network issue');
            console.warn('[TIMEOUT] 3. Server error (check Flask terminal)');
            controller.abort();
        }, 30000);  // Increased to 30 seconds
        
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
                    const redirectUri = result.redirect_uri || redirectUri || 'http://localhost:5000/callback';
                    showNotification(
                        `💡 Tip: Add this EXACT redirect URI in Upstox Portal:\n${redirectUri}\n\nPortal: https://account.upstox.com/developer/apps`,
                        'info'
                    );
                }, 2000);
            }
        }
    } catch (error) {
        console.error('[ERROR] Connect exception:', error);
        
        let errorMsg = 'Connection failed';
        if (error.name === 'AbortError') {
            errorMsg = 'Connection timeout - Request took too long. This might be due to:\n1. Upstox API is slow\n2. Network issues\n3. Redirect URI mismatch\n\nPlease check your redirect URI in Upstox Portal and try again.';
        } else if (error.message.includes('fetch')) {
            errorMsg = `Network error: ${error.message}. Make sure the server is running on port 5000.`;
        } else {
            errorMsg = `Error: ${error.message}`;
        }
        
        showNotification(`❌ ${errorMsg}`, 'error');
        
        // Show helpful hints with exact redirect URI
        if (error.name === 'AbortError') {
            setTimeout(() => {
                const redirectInput = document.getElementById('redirect-uri');
                const redirectUri = redirectInput?.value || 'http://localhost:5000/callback';
                showNotification(
                    `💡 Tip: Add this EXACT redirect URI in Upstox Portal:\n${redirectUri}\n\nPortal: https://account.upstox.com/developer/apps`,
                    'info'
                );
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
async function loadOrders() {
    try {
        const response = await fetch('/api/upstox/orders');
        const orders = await response.json();
        const container = document.getElementById('orders-container');
        
        if (orders.error) {
            container.innerHTML = `<div class="empty-state"><i class="fas fa-exclamation-triangle"></i><p>${orders.error}</p></div>`;
            return;
        }
        
        if (orders.length === 0) {
            container.innerHTML = '<div class="empty-state"><i class="fas fa-inbox"></i><p>No orders found</p></div>';
            return;
        }
        
        let html = '<div class="orders-list">';
        orders.forEach(order => {
            html += `
                <div class="order-item fade-in">
                    <div>
                        <strong>${order.instrument_token || 'N/A'}</strong>
                        <div class="text-muted" style="font-size: 0.875rem;">
                            ${order.transaction_type || 'N/A'} • Qty: ${order.quantity || 'N/A'}
                        </div>
                    </div>
                    <span class="badge bg-${order.status === 'COMPLETE' ? 'success' : 'warning'}">${order.status || 'N/A'}</span>
                </div>
            `;
        });
        html += '</div>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading orders:', error);
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
    
    try {
        // Check paper trading mode before placing order
        const statusResponse = await fetch('/api/paper-trading/status');
        const statusData = await statusResponse.json();
        const paperMode = statusData.paper_trading_mode;
        
        if (!paperMode) {
            // Double confirmation for live trading
            if (!confirm('⚠️ LIVE TRADING MODE\n\nThis will place a REAL order with REAL money.\n\nAre you sure you want to proceed?')) {
                return;
            }
        }
        
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
            const errorMsg = result.error || result.message || 'Error placing order';
            showNotification(`⚠️ ${errorMsg}`, 'error');
            if (result.hint) {
                setTimeout(() => showNotification(`💡 ${result.hint}`, 'info'), 2000);
            }
        }
    } catch (error) {
        console.error('Error placing order:', error);
        showNotification('Error placing order', 'error');
    }
}

// Refresh signals
function refreshSignals() {
    if (selectedTicker) {
        showLevels(selectedTicker);
    }
}

// Notification system
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
