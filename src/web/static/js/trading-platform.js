// Trading Platform JavaScript - Upstox-like functionality

let currentTab = 'holdings';
let holdingsData = [];
let selectedStock = null;
let signalsRefreshInterval = null;
let stocksUniverseOffset = 0;
let stocksUniverseLimit = 200;

// Make setTheme available globally (defined in dashboard.js)
// This ensures it's available when trading-platform.js loads
if (typeof setTheme === 'undefined') {
    // Fallback if dashboard.js hasn't loaded yet
    window.setTheme = function(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    };
}

// Initialize platform
document.addEventListener('DOMContentLoaded', function() {
    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'dark';
    if (typeof setTheme === 'function') {
        setTheme(savedTheme);
    } else {
        window.setTheme(savedTheme);
    }
    
    // Check Upstox connection status first
    checkUpstoxConnection();
    
    // Initialize components
    loadMarketIndices();
    loadWatchlist();
    loadTopStocks();
    loadAlerts();
    
    // Load Upstox data only if connected
    setTimeout(() => {
        loadHoldings();
        loadOrders();
    }, 500);
    
    // Auto-refresh - indices every 15s when tab visible for live feel
    setInterval(() => {
        if (document.visibilityState === 'visible') loadMarketIndices();
    }, 15000); // Refresh indices every 15 seconds
    
    setInterval(() => {
        if (document.visibilityState === 'visible') {
            loadHoldings();
            updatePrices();
        }
    }, 15000); // Refresh holdings and prices every 15 seconds
    
    // Stock search - live search from universe when 2+ chars, otherwise filter/restore top stocks
    let stockSearchDebounce;
    document.getElementById('stock-search')?.addEventListener('input', function(e) {
        const q = (e.target.value || '').trim();
        clearTimeout(stockSearchDebounce);
        if (q.length >= 2) {
            stockSearchDebounce = setTimeout(() => loadStockSearch(q), 300);
        } else if (q.length === 0) {
            loadTopStocks();
        } else {
            filterStockList(q);
        }
    });
    
    // Order type change
    document.getElementById('order-order-type')?.addEventListener('change', function() {
        const priceContainer = document.getElementById('price-input-container');
        if (this.value === 'LIMIT' || this.value === 'SL') {
            priceContainer.style.display = 'block';
        } else {
            priceContainer.style.display = 'none';
        }
    });
    
    // Close sidebar when clicking outside on mobile
    document.getElementById('mobile-overlay')?.addEventListener('click', function() {
        toggleMobileSidebar();
    });
    
    // Handle window resize
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768) {
            const sidebar = document.getElementById('mobile-sidebar');
            if (sidebar) {
                sidebar.classList.remove('mobile-open');
            }
            const overlay = document.getElementById('mobile-overlay');
            if (overlay) {
                overlay.classList.remove('active');
            }
        }
    });
});

// Load Market Indices - All major Indian indices
async function loadMarketIndices() {
    try {
        const response = await fetch('/api/market-indices');
        if (!response.ok) {
            throw new Error('Failed to fetch market indices');
        }
        
        const indices = await response.json();
        
        // Major indices (always visible in top bar)
        const majorIndices = ['nifty', 'sensex', 'banknifty', 'vix'];
        majorIndices.forEach(id => {
            if (indices[id]) {
                updateIndexDisplay(id, indices[id].value, indices[id].change, indices[id].change_pct);
            } else {
                const el = document.getElementById(`index-${id}`);
                if (el) {
                    const valueEl = el.querySelector('.index-value');
                    const changeEl = el.querySelector('.index-change');
                    if (valueEl) valueEl.textContent = '--';
                    if (changeEl) changeEl.textContent = '--';
                }
            }
        });
        
        // Sectoral indices (expandable section)
        const sectoralIndices = ['niftyit', 'niftyfmcg', 'niftypharma', 'niftyauto', 'niftymetal', 
                                 'niftyenergy', 'niftyrealty', 'niftypsu', 'niftymidcap', 'niftysmallcap'];
        const sectoralLabels = {
            'niftyit': 'NIFTY IT',
            'niftyfmcg': 'NIFTY FMCG',
            'niftypharma': 'NIFTY PHARMA',
            'niftyauto': 'NIFTY AUTO',
            'niftymetal': 'NIFTY METAL',
            'niftyenergy': 'NIFTY ENERGY',
            'niftyrealty': 'NIFTY REALTY',
            'niftypsu': 'NIFTY PSU',
            'niftymidcap': 'NIFTY MIDCAP',
            'niftysmallcap': 'NIFTY SMALLCAP'
        };
        
        // Render sectoral indices in expandable section
        const sectoralContainer = document.getElementById('sectoral-indices-container');
        if (sectoralContainer) {
            const sectoralHtml = sectoralIndices.map(id => {
                if (indices[id]) {
                    const index = indices[id];
                    const isPositive = index.change >= 0;
                    return `
                        <div class="index-item" style="min-width: 120px; font-size: 0.875rem;">
                            <div class="index-label">${sectoralLabels[id] || id.toUpperCase()}</div>
                            <div class="index-value">${index.value.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                            <div class="index-change ${isPositive ? 'positive' : 'negative'}">
                                ${isPositive ? '+' : ''}${index.change.toFixed(2)} (${isPositive ? '+' : ''}${index.change_pct.toFixed(2)}%)
                            </div>
                        </div>
                    `;
                }
                return '';
            }).filter(html => html).join('');
            
            sectoralContainer.innerHTML = sectoralHtml || '<div class="text-muted" style="font-size: 0.75rem; padding: 0.5rem;">Sectoral indices loading...</div>';
        }
        // Show "Connect Upstox" banner when indices empty and Upstox not connected
        const majorIds = ['nifty', 'sensex', 'banknifty', 'vix'];
        const allEmpty = majorIds.every(id => !indices[id] || !indices[id].value);
        if (allEmpty && !window.upstoxConnected) {
            let banner = document.getElementById('indices-connect-banner');
            if (!banner) {
                banner = document.createElement('div');
                banner.id = 'indices-connect-banner';
                banner.className = 'indices-connect-banner';
                banner.innerHTML = '<i class="fas fa-info-circle"></i> Connect Upstox for live index data';
                const container = document.getElementById('indices-container-main');
                if (container) container.prepend(banner);
            }
            banner.classList.remove('d-none');
        } else {
            document.getElementById('indices-connect-banner')?.classList.add('d-none');
        }
    } catch (error) {
        console.error('Error loading market indices:', error);
        // Show error on indices
        ['nifty', 'sensex', 'banknifty', 'vix'].forEach(id => {
            const el = document.getElementById(`index-${id}`);
            if (el) {
                const valueEl = el.querySelector('.index-value');
                const changeEl = el.querySelector('.index-change');
                if (valueEl) valueEl.textContent = '--';
                if (changeEl) changeEl.textContent = '--';
            }
        });
        if (!window.upstoxConnected) {
            let banner = document.getElementById('indices-connect-banner');
            if (!banner) {
                banner = document.createElement('div');
                banner.id = 'indices-connect-banner';
                banner.className = 'indices-connect-banner';
                banner.innerHTML = '<i class="fas fa-info-circle"></i> Connect Upstox for live index data';
                const container = document.getElementById('indices-container-main');
                if (container) container.prepend(banner);
            }
            banner.classList.remove('d-none');
        }
    }
}

// Toggle sectoral indices display
function toggleSectoralIndices() {
    const container = document.getElementById('sectoral-indices-container');
    const icon = document.getElementById('indices-toggle-icon');
    if (container && icon) {
        const isVisible = container.style.display !== 'none';
        container.style.display = isVisible ? 'none' : 'flex';
        icon.className = isVisible ? 'fas fa-chevron-down' : 'fas fa-chevron-up';
    }
}

// Check Upstox connection status
async function checkUpstoxConnection() {
    try {
        const response = await fetch('/api/upstox/status');
        const status = await response.json();
        
        window.upstoxConnected = !!status.connected;
        if (status.connected) {
            const statusEl = document.getElementById('connection-status');
            if (statusEl) {
                statusEl.innerHTML = '<i class="fas fa-circle"></i><span class="mobile-hide">Connected</span>';
                statusEl.classList.add('connected');
            }
            document.getElementById('indices-connect-banner')?.classList.add('d-none');
            console.log('[DEBUG] Upstox is connected, loading data...');
        } else {
            const statusEl = document.getElementById('connection-status');
            if (statusEl) {
                statusEl.innerHTML = '<i class="fas fa-circle"></i><span class="mobile-hide">Disconnected</span>';
                statusEl.classList.remove('connected');
            }
            console.log('[DEBUG] Upstox is not connected');
        }
    } catch (error) {
        console.error('Error checking connection status:', error);
    }
}

function updateIndexDisplay(id, value, change, changePct) {
    const element = document.getElementById(`index-${id}`);
    if (!element) return;
    
    const valueEl = element.querySelector('.index-value');
    const changeEl = element.querySelector('.index-change');
    
    if (valueEl && value && !isNaN(value)) {
        // Format value with Indian number formatting
        valueEl.textContent = value.toLocaleString('en-IN', { 
            minimumFractionDigits: 2, 
            maximumFractionDigits: 2 
        });
    }
    
    if (changeEl && change !== undefined && !isNaN(change) && changePct !== undefined && !isNaN(changePct)) {
        const isPositive = change >= 0;
        changeEl.className = `index-change ${isPositive ? 'positive' : 'negative'}`;
        changeEl.textContent = `${isPositive ? '+' : ''}${change.toFixed(2)} (${isPositive ? '+' : ''}${changePct.toFixed(2)}%)`;
    }
}

// Load Holdings from Upstox
async function loadHoldings() {
    try {
        console.log('[DEBUG] ===== Loading holdings from Upstox =====');
        
        // First check connection status
        const statusResponse = await fetch('/api/upstox/status');
        const status = await statusResponse.json();
        console.log('[DEBUG] Connection status:', status);
        
        if (!status.connected) {
            console.error('[ERROR] Upstox is not connected!');
            console.error('[ERROR] Status details:', status);
            
            // Determine error message
            let errorMessage = 'Please click "Connect" button to connect your Upstox account.';
            let errorHint = '';
            
            if (status.connection_error) {
                errorMessage = `Connection Error: ${status.connection_error}`;
                if (status.connection_error.includes('timeout')) {
                    errorHint = 'The connection timed out. Please check your internet connection and try again.';
                } else if (status.connection_error.includes('expired') || status.connection_error.includes('invalid')) {
                    errorHint = 'Your access token may have expired. Please reconnect your Upstox account.';
                } else if (status.connection_error.includes('Status 401') || status.connection_error.includes('Unauthorized')) {
                    errorHint = 'Authentication failed. Please reconnect your Upstox account with a fresh token.';
                }
            } else if (status.has_token && !status.connected) {
                errorMessage = 'Token exists but connection check failed.';
                errorHint = 'Please try reconnecting your Upstox account.';
            }
            
            // Show user-friendly message
            const tbody = document.getElementById('holdings-table-body');
            if (tbody) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="10" class="text-center text-muted">
                            <div style="padding: 2rem;">
                                <i class="fas fa-exclamation-triangle" style="font-size: 2rem; color: #f59e0b; margin-bottom: 1rem;"></i>
                                <p><strong>Upstox Not Connected</strong></p>
                                <p>${errorMessage}</p>
                                ${errorHint ? `<p style="font-size: 0.875rem; color: #94a3b8; margin-top: 0.5rem;">${errorHint}</p>` : ''}
                                ${status.connection_error ? `<p style="font-size: 0.75rem; color: #64748b; margin-top: 0.5rem; font-family: monospace;">Details: ${status.connection_error}</p>` : ''}
                            </div>
                        </td>
                    </tr>
                `;
            }
            return;
        }
        
        console.log('[DEBUG] Upstox is connected, fetching holdings...');
        
        // Fetch real holdings data from Upstox API
        const response = await fetch('/api/holdings');
        
        console.log('[DEBUG] Holdings API response status:', response.status);
        
        if (!response.ok) {
            if (response.status === 400 || response.status === 500) {
                const error = await response.json();
                console.error('[ERROR] Holdings API error:', error);
                
                // Show user-friendly error message
                const tbody = document.getElementById('holdings-table-body');
                if (tbody) {
                    tbody.innerHTML = `
                        <tr>
                            <td colspan="10" class="text-center text-muted">
                                <div style="padding: 2rem;">
                                    <i class="fas fa-exclamation-circle" style="font-size: 2rem; color: #ef4444; margin-bottom: 1rem;"></i>
                                    <p><strong>Error Loading Holdings</strong></p>
                                    <p>${error.error || 'Unknown error occurred'}</p>
                                    <p style="font-size: 0.875rem; color: #94a3b8; margin-top: 0.5rem;">
                                        Check browser console (F12) for details
                                    </p>
                                </div>
                            </td>
                        </tr>
                    `;
                }
                
                if (error.error && error.error.includes('not connected')) {
                    console.warn('[WARN] Upstox not connected, showing empty holdings');
                    holdingsData = [];
                    renderHoldingsTable();
                    return;
                }
            }
            throw new Error(`HTTP ${response.status}`);
        }
        
        const holdings = await response.json();
        console.log('[DEBUG] Received holdings:', holdings.length, 'items');
        
        if (holdings.length > 0) {
            console.log('[DEBUG] Sample holding:', holdings[0]);
        } else {
            console.warn('[WARN] No holdings returned from API');
            console.warn('[WARN] This could mean:');
            console.warn('[WARN]   1. You have no holdings in your Upstox account');
            console.warn('[WARN]   2. The API returned empty data');
            console.warn('[WARN]   3. There is a data format issue');
            
            // Show helpful message for empty holdings
            const tbody = document.getElementById('holdings-table-body');
            if (tbody && holdingsData.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="10" class="text-center text-muted">
                            <div style="padding: 2rem;">
                                <i class="fas fa-info-circle" style="font-size: 2rem; color: #3b82f6; margin-bottom: 1rem;"></i>
                                <p><strong>No Holdings Found</strong></p>
                                <p>You don't have any holdings in your Upstox account, or the API returned empty data.</p>
                                <p style="font-size: 0.875rem; color: #94a3b8; margin-top: 0.5rem;">
                                    Check your Upstox app/website to verify you have holdings.
                                </p>
                            </div>
                        </td>
                    </tr>
                `;
            }
        }
        
        // Transform API response to UI format
        holdingsData = [];
        let totalInvested = 0;
        let totalCurrent = 0;
        let totalDayPnl = 0;
        
        for (const h of holdings) {
            const qty = h.qty || 0;
            const avgPrice = h.avg_price || 0;
            const ltp = h.ltp || 0;
            const currentValue = h.current_value || (ltp * qty);
            const invested = avgPrice * qty;
            const overallPnl = h.overall_pnl || (currentValue - invested);
            const overallPnlPct = h.overall_pnl_pct || (invested > 0 ? (overallPnl / invested) * 100 : 0);
            const dayPnl = h.day_pnl || 0;
            const dayPnlPct = h.day_pnl_pct || 0;
            
            holdingsData.push({
                symbol: h.symbol || 'N/A',
                qty: qty,
                avgPrice: avgPrice,
                ltp: ltp,
                currentValue: currentValue,
                dayPnl: dayPnl,
                dayPnlPct: dayPnlPct,
                overallPnl: overallPnl,
                overallPnlPct: overallPnlPct
            });
            
            totalInvested += invested;
            totalCurrent += currentValue;
            totalDayPnl += dayPnl;
        }
        
        // Update summary
        const overallPnl = totalCurrent - totalInvested;
        const overallPnlPct = totalInvested > 0 ? (overallPnl / totalInvested) * 100 : 0;
        
        const totalInvestedEl = document.getElementById('total-invested');
        const totalCurrentEl = document.getElementById('total-current');
        const overallPnlEl = document.getElementById('overall-pnl');
        const dayPnlEl = document.getElementById('day-pnl');
        
        if (totalInvestedEl) {
            totalInvestedEl.textContent = `₹${totalInvested.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        }
        if (totalCurrentEl) {
            totalCurrentEl.textContent = `₹${totalCurrent.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        }
        if (overallPnlEl) {
            overallPnlEl.textContent = `₹${overallPnl.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})} (${overallPnlPct >= 0 ? '+' : ''}${overallPnlPct.toFixed(2)}%)`;
            overallPnlEl.parentElement.className = `summary-item ${overallPnl >= 0 ? 'profit' : 'loss'}`;
        }
        if (dayPnlEl) {
            const dayPnlPctCalc = totalInvested > 0 ? (totalDayPnl / totalInvested * 100) : 0;
            dayPnlEl.textContent = `₹${totalDayPnl.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})} (${totalDayPnl >= 0 ? '+' : ''}${dayPnlPctCalc.toFixed(2)}%)`;
            dayPnlEl.parentElement.className = `summary-item ${totalDayPnl >= 0 ? 'profit' : 'loss'}`;
        }
        
        // Update counts
        const countAllEl = document.getElementById('count-all');
        const countDematEl = document.getElementById('count-demat');
        if (countAllEl) countAllEl.textContent = holdingsData.length;
        if (countDematEl) countDematEl.textContent = holdingsData.length;
        
        // Render table
        renderHoldingsTable();
        
    } catch (error) {
        console.error('Error loading holdings:', error);
        holdingsData = [];
        renderHoldingsTable();
    }
}

async function renderHoldingsTable() {
    const tbody = document.getElementById('holdings-table-body');
    if (!tbody) return;
    
    if (holdingsData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="12" class="text-center text-muted">No holdings. Add stocks to watchlist to track.</td></tr>';
        return;
    }
    
    // Render table with loading signals
    tbody.innerHTML = holdingsData.map((holding, index) => {
        const dayPnlClass = holding.dayPnl >= 0 ? 'positive' : 'negative';
        const overallPnlClass = holding.overallPnl >= 0 ? 'positive' : 'negative';
        const signalId = `signal-${index}`;
        const chartId = `chart-${index}`;
        
        return `
            <tr onclick="selectStock('${holding.symbol}')" style="cursor: pointer;">
                <td class="symbol"><strong>${holding.symbol}</strong></td>
                <td>${holding.qty}</td>
                <td>₹${holding.avgPrice.toFixed(2)}</td>
                <td class="${holding.ltp >= holding.avgPrice ? 'positive' : 'negative'}">₹${holding.ltp.toFixed(2)}</td>
                <td>₹${holding.currentValue.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td class="${dayPnlClass}">₹${holding.dayPnl >= 0 ? '+' : ''}${holding.dayPnl.toFixed(2)}</td>
                <td class="${dayPnlClass}">${holding.dayPnlPct >= 0 ? '+' : ''}${holding.dayPnlPct.toFixed(2)}%</td>
                <td class="${overallPnlClass}">₹${holding.overallPnl >= 0 ? '+' : ''}${holding.overallPnl.toFixed(2)}</td>
                <td class="${overallPnlClass}">${holding.overallPnlPct >= 0 ? '+' : ''}${holding.overallPnlPct.toFixed(2)}%</td>
                <td>
                    <button class="btn-action btn-view" onclick="event.stopPropagation(); loadStockChart('${holding.symbol}')" title="View Chart">
                        <i class="fas fa-chart-line"></i>
                    </button>
                </td>
                <td id="${signalId}">
                    <span class="badge bg-secondary">Loading...</span>
                </td>
                <td>
                    <div class="action-buttons">
                        <button class="btn-action btn-buy" onclick="event.stopPropagation(); quickOrder('${holding.symbol}', 'BUY')">B</button>
                        <button class="btn-action btn-sell" onclick="event.stopPropagation(); quickOrder('${holding.symbol}', 'SELL')">S</button>
                        <button class="btn-action btn-view" onclick="event.stopPropagation(); showLevels('${holding.symbol}')">View</button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
    
    // Load signals for each holding asynchronously
    holdingsData.forEach(async (holding, index) => {
        if (holding.symbol && holding.symbol !== 'N/A') {
            try {
                const signal = await getStockSignal(holding.symbol);
                const signalEl = document.getElementById(`signal-${index}`);
                if (signalEl) {
                    const badgeClass = signal.color === 'success' ? 'bg-success' : 
                                     signal.color === 'danger' ? 'bg-danger' : 
                                     signal.color === 'warning' ? 'bg-warning' : 'bg-secondary';
                    const titleAttr = signal.hint ? ` title="${signal.hint.replace(/"/g, '&quot;')}"` : '';
                    const probText = signal.probability != null ? ` ${Math.round(signal.probability * 100)}%` : '';
                    signalEl.innerHTML = `<span class="badge ${badgeClass}"${titleAttr}>${signal.signal}${probText}</span>`;
                }
            } catch (error) {
                console.error(`Error loading signal for ${holding.symbol}:`, error);
            }
        }
    });
}

// Load Top Stocks for Sidebar
async function loadTopStocks() {
    try {
        const response = await fetch('/api/top_stocks');
        const stocks = await response.json();
        
        if (!stocks || stocks.length === 0) {
            console.warn('No stocks returned from /api/top_stocks');
            const container = document.getElementById('stock-list-container');
            if (container) {
                container.innerHTML = '<div class="empty-state"><p>No stocks available</p></div>';
            }
            return;
        }
        
        // Fetch prices for top stocks
        let prices = {};
        try {
            const pricesResponse = await fetch('/api/prices?for_top_stocks=true');
            if (pricesResponse.ok) {
                prices = await pricesResponse.json();
            }
        } catch (priceError) {
            console.warn('Error fetching prices, using defaults:', priceError);
        }
        
        const container = document.getElementById('stock-list-container');
        if (!container) {
            console.warn('stock-list-container element not found');
            return;
        }
        
        container.innerHTML = stocks.map(stock => {
            const price = prices[stock.ticker];
            const change = price && !price.error ? price.change_pct : 0;
            const changeClass = change >= 0 ? 'positive' : 'negative';
            
            return `
                <div class="stock-list-item" onclick="selectStock('${stock.ticker}')">
                    <div class="stock-list-item-info">
                        <div class="stock-list-item-symbol">${stock.name}</div>
                        <div class="stock-list-item-price">${stock.ticker}</div>
                    </div>
                    <div class="stock-list-item-change ${changeClass}">
                        ${change >= 0 ? '+' : ''}${change.toFixed(2)}%
                    </div>
                </div>
            `;
        }).join('');
        
        const countEl = document.getElementById('top-stocks-count');
        if (countEl) {
            countEl.textContent = stocks.length;
        }
        
        console.log(`Loaded ${stocks.length} stocks into sidebar`);
        
    } catch (error) {
        console.error('Error loading top stocks:', error);
        const container = document.getElementById('stock-list-container');
        if (container) {
            container.innerHTML = `<div class="empty-state"><p>Error loading stocks: ${error.message}</p></div>`;
        }
    }
}

function filterStockList(query) {
    const items = document.querySelectorAll('.stock-list-item');
    const lowerQuery = query.toLowerCase();
    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        item.style.display = text.includes(lowerQuery) ? 'flex' : 'none';
    });
}

// Live stock search from universe (when user types 2+ chars)
async function loadStockSearch(query) {
    const container = document.getElementById('stock-list-container');
    if (!container) return;
    try {
        container.innerHTML = '<div class="empty-state"><p>Searching...</p></div>';
        const res = await fetch('/api/stocks/universe?search=' + encodeURIComponent(query) + '&limit=25');
        const data = await res.json();
        const stocks = data.stocks || [];
        if (stocks.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>No stocks found for "' + query + '"</p></div>';
            return;
        }
        let prices = {};
        try {
            const tickers = stocks.map(s => s.ticker).join(',');
            const pricesRes = await fetch('/api/prices?tickers=' + encodeURIComponent(tickers));
            if (pricesRes.ok) prices = await pricesRes.json();
        } catch (_) {}
        container.innerHTML = stocks.map(stock => {
            const price = prices[stock.ticker];
            const change = price && !price.error ? (price.change_pct || 0) : 0;
            const changeClass = change >= 0 ? 'positive' : 'negative';
            return `<div class="stock-list-item" onclick="selectStock('${stock.ticker}')">
                <div class="stock-list-item-info">
                    <div class="stock-list-item-symbol">${stock.name || stock.ticker}</div>
                    <div class="stock-list-item-price">${stock.ticker}</div>
                </div>
                <div class="stock-list-item-change ${changeClass}">${change >= 0 ? '+' : ''}${Number(change).toFixed(2)}%</div>
            </div>`;
        }).join('');
        const countEl = document.getElementById('top-stocks-count');
        if (countEl) countEl.textContent = stocks.length;
    } catch (err) {
        console.error('Stock search failed:', err);
        container.innerHTML = '<div class="empty-state"><p>Search failed. Try again.</p></div>';
    }
}

function selectStock(ticker) {
    selectedStock = ticker;
    
    // Update active state
    document.querySelectorAll('.stock-list-item').forEach(item => {
        item.classList.remove('active');
        if (item.textContent.includes(ticker)) {
            item.classList.add('active');
        }
    });
    
    // Show levels
    showLevels(ticker);
    
    // Switch to signals tab
    switchTab('signals');
}

// Tab Switching
// Phase 2.4: Record portfolio snapshot
async function recordPortfolioSnapshot() {
    try {
        const response = await fetch('/api/portfolio/snapshot', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showNotification('Portfolio snapshot recorded successfully', 'success');
            // Reload charts
            loadPortfolioValueChart();
            loadDailyPnLChart();
        } else {
            showNotification(result.error || 'Failed to record snapshot', 'error');
        }
    } catch (error) {
        console.error('Error recording snapshot:', error);
        showNotification('Error recording snapshot: ' + error.message, 'error');
    }
}

// Make switchTab globally available
window.switchTab = function switchTab(tabName) {
    console.log('[TAB] Switching to tab:', tabName);
    currentTab = tabName;
    
    // Clear signals auto-refresh when leaving signals tab
    if (signalsRefreshInterval) {
        clearInterval(signalsRefreshInterval);
        signalsRefreshInterval = null;
    }
    
    // Update tab buttons - support both .tab-btn and .nav-tab classes
    const tabButtons = document.querySelectorAll('.tab-btn, .nav-tab');
    console.log('[TAB] Found', tabButtons.length, 'tab buttons');
    
    tabButtons.forEach(btn => {
        btn.classList.remove('active');
        const tabValue = btn.dataset.tab || btn.getAttribute('data-tab');
        if (tabValue === tabName) {
            btn.classList.add('active');
            console.log('[TAB] Activated button:', tabValue);
        }
    });
    
    // Update tab content
    const tabContents = document.querySelectorAll('.tab-content');
    console.log('[TAB] Found', tabContents.length, 'tab contents');
    
    tabContents.forEach(content => {
        content.classList.remove('active');
        if (content.id === `tab-${tabName}`) {
            content.classList.add('active');
            console.log('[TAB] Activated content:', content.id);
        }
    });
    
    // Scroll to top on mobile when switching tabs
    if (window.innerWidth <= 768) {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    
    // Load data for active tab
    if (tabName === 'holdings') {
        loadHoldings();
    } else if (tabName === 'watchlist') {
        loadWatchlist();
    } else if (tabName === 'positions') {
        loadPositions();
    } else if (tabName === 'orders') {
        loadOrders();
    } else if (tabName === 'signals') {
        // Auto-load signals when signals tab is opened
        loadSignals();
        // Auto-refresh signals every 90 seconds while on this tab
        signalsRefreshInterval = setInterval(function() {
            if (currentTab === 'signals' && (typeof loadSignals === 'function')) loadSignals();
        }, 90000);
    } else if (tabName === 'trade-plans') {
        if (typeof loadTradePlans === 'function') {
            loadTradePlans();
        }
    } else if (tabName === 'analytics') {
        // Phase 2.4: Load analytics charts
        setTimeout(() => {
            if (typeof loadPortfolioValueChart === 'function') {
                loadPortfolioValueChart();
            }
            if (typeof loadDailyPnLChart === 'function') {
                loadDailyPnLChart();
            }
            if (typeof loadAllocationChart === 'function') {
                loadAllocationChart();
            }
            if (typeof loadReturnsComparisonChart === 'function') {
                loadReturnsComparisonChart();
            }
        }, 500);
    }
}

function filterHoldings(filter) {
    // Filter logic for holdings
    renderHoldingsTable();
}

// Toggle sectoral indices display
function toggleSectoralIndices() {
    const container = document.getElementById('sectoral-indices-container');
    const icon = document.getElementById('indices-toggle-icon');
    if (container && icon) {
        const isVisible = container.style.display !== 'none';
        container.style.display = isVisible ? 'none' : 'flex';
        icon.className = isVisible ? 'fas fa-chevron-down' : 'fas fa-chevron-up';
    }
}

let currentPositionFilter = 'all';

async function loadPositions() {
    // Load positions from Upstox or Paper Trading
    const tbody = document.getElementById('positions-table-body');
    if (!tbody) return;
    
    try {
        // Check paper trading mode
        const statusResponse = await fetch('/api/paper-trading/status');
        const statusData = await statusResponse.json();
        const paperMode = statusData.paper_trading_mode;
        
        let positions = [];
        if (paperMode) {
            // Load paper trading positions
            const response = await fetch('/api/paper-trading/positions');
            const data = await response.json();
            if (data.status === 'success') {
                positions = data.positions || [];
            }
        } else {
            // Load daily positions with current filter
            const response = await fetch(`/api/daily-positions?filter=${currentPositionFilter}`);
            const data = await response.json();
            if (data.status === 'success') {
                positions = data.positions || [];
                
                // Load and display stats if filter is not 'all'
                if (currentPositionFilter !== 'all') {
                    await loadDailyPositionStats();
                }
            } else {
                // Fallback to regular positions API
                const fallbackResponse = await fetch('/api/positions');
                const positionsData = await fallbackResponse.json();
                if (Array.isArray(positionsData)) {
                    positions = positionsData;
                } else if (positionsData.error) {
                    tbody.innerHTML = `<tr><td colspan="10" class="text-center text-muted">${positionsData.error}</td></tr>`;
                    return;
                }
            }
        }
        
        if (positions.length === 0) {
            const modeText = paperMode ? 'paper trading' : 'real';
            tbody.innerHTML = `<tr><td colspan="10" class="text-center text-muted">No ${currentPositionFilter} ${modeText} positions found</td></tr>`;
            return;
        }
        
        tbody.innerHTML = positions.map(pos => {
            // Handle both paper and real position formats
            const pnlValue = paperMode ? (pos.pnl || 0) : (pos.overall_pnl || pos.pnl || pos.intraday_pnl || 0);
            const pnlPct = paperMode ? (pos.pnl_pct || 0) : (pos.pnl_pct || pos.overall_pnl_pct || 0);
            const pnlClass = pnlValue >= 0 ? 'positive' : 'negative';
            const symbol = pos.symbol || pos.tradingsymbol || 'N/A';
            const quantity = pos.quantity || pos.net_quantity || 0;
            const netQty = Math.abs(quantity);
            const transactionType = pos.transaction_type || (quantity >= 0 ? 'BUY' : 'SELL');
            const typeBadge = transactionType === 'BUY' 
                ? '<span class="badge bg-success">BUY</span>' 
                : '<span class="badge bg-danger">SELL</span>';
            const entryPrice = pos.entry_price || pos.average_price || 0;
            const currentPrice = pos.last_price || pos.current_price || pos.ltp || entryPrice;
            const product = pos.product || 'MIS';
            const productBadge = product === 'CNC' 
                ? '<span class="badge bg-info">CNC</span>' 
                : product === 'NRML' 
                ? '<span class="badge bg-warning">NRML</span>' 
                : '<span class="badge bg-secondary">MIS</span>';
            
            // Fix Bug 5: Add data attributes for real-time P&L updates
            // Get instrument key for Upstox positions, use symbol as fallback
            const instrumentKey = pos.instrument_key || pos.instrument_token || symbol;
            
            return `
                <tr onclick="selectStock('${symbol}')" 
                    style="cursor: pointer;"
                    data-instrument-key="${instrumentKey}"
                    data-avg-price="${entryPrice}"
                    data-quantity="${quantity}">
                    <td class="symbol">
                        <strong>${symbol}</strong>
                        ${paperMode ? ' <span class="badge bg-info">Paper</span>' : ''}
                    </td>
                    <td>
                        <div>${netQty}</div>
                        <div style="font-size: 0.75rem; color: var(--text-muted);">${typeBadge}</div>
                    </td>
                    <td>₹${entryPrice.toFixed(2)}</td>
                    <td class="${currentPrice >= entryPrice ? 'positive' : 'negative'}">₹${currentPrice.toFixed(2)}</td>
                    <td>₹${((netQty * currentPrice) || 0).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                    <td class="pnl-cell ${pnlClass}">₹${pnlValue >= 0 ? '+' : ''}${pnlValue.toFixed(2)}</td>
                    <td class="${pnlClass}">${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}%</td>
                    <td>${productBadge}</td>
                    <td>
                        <span class="badge bg-success">Open</span>
                    </td>
                    <td>
                        <button class="btn-action btn-view" onclick="event.stopPropagation(); selectStock('${symbol}')" title="View Details">
                            <i class="fas fa-eye"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading positions:', error);
        tbody.innerHTML = '<tr><td colspan="10" class="text-center text-muted">Error loading positions</td></tr>';
    }
}

function filterPositions(filter) {
    currentPositionFilter = filter;
    
    // Update filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.filter === filter) {
            btn.classList.add('active');
        }
    });
    
    // Reload positions
    loadPositions();
}

async function loadDailyPositionStats() {
    try {
        const response = await fetch('/api/daily-positions/stats');
        const data = await response.json();
        
        if (data.status === 'success' && data.stats) {
            const stats = data.stats;
            document.getElementById('stat-total-trades').textContent = stats.total_trades || 0;
            document.getElementById('stat-win-rate').textContent = (stats.win_rate || 0).toFixed(1) + '%';
            
            const intradayPnl = stats.intraday_pnl || 0;
            const intradayPnlClass = intradayPnl >= 0 ? 'positive' : 'negative';
            document.getElementById('stat-intraday-pnl').textContent = `₹${intradayPnl.toFixed(2)}`;
            document.getElementById('stat-intraday-pnl').className = `stat-value ${intradayPnlClass}`;
            
            const unrealizedPnl = stats.unrealized_pnl || 0;
            const unrealizedPnlClass = unrealizedPnl >= 0 ? 'positive' : 'negative';
            document.getElementById('stat-unrealized-pnl').textContent = `₹${unrealizedPnl.toFixed(2)}`;
            document.getElementById('stat-unrealized-pnl').className = `stat-value ${unrealizedPnlClass}`;
            
            // Show stats bar
            document.getElementById('daily-position-stats').style.display = 'flex';
        }
    } catch (error) {
        console.error('Error loading daily position stats:', error);
    }
}

async function syncDailyPositions() {
    try {
        const response = await fetch('/api/daily-positions/sync', { method: 'POST' });
        const data = await response.json();
        
        if (data.status === 'success') {
            showNotification(`Synced ${data.synced_count} positions from Upstox`, 'success');
            loadPositions();
        } else {
            showNotification('Error syncing positions: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error syncing positions:', error);
        showNotification('Error syncing positions', 'error');
    }
}

// Popular stocks to show signals for by default
const POPULAR_STOCKS = [
    'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'HINDUNILVR.NS',
    'ICICIBANK.NS', 'BHARTIARTL.NS', 'SBIN.NS', 'BAJFINANCE.NS', 'LICI.NS',
    'ITC.NS', 'LT.NS', 'HCLTECH.NS', 'AXISBANK.NS', 'MARUTI.NS'
];

let signalsSource = 'demat';  // demat | watchlist | both

function setSignalsSource(source) {
    signalsSource = source;
    document.querySelectorAll('.signals-source-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.source === source) btn.classList.add('active');
    });
    loadSignals();
}
window.setSignalsSource = setSignalsSource;

function loadSignalsWithPopularStocks() {
    loadSignals(POPULAR_STOCKS);
}
window.loadSignalsWithPopularStocks = loadSignalsWithPopularStocks;

function setSignalsLastUpdated() {
    const el = document.getElementById('signals-last-updated');
    if (el) el.textContent = 'Last updated: ' + new Date().toLocaleTimeString();
}

async function loadSignals(forceStocks) {
    const container = document.getElementById('signals-container');
    if (!container) return;
    
    // Show loading state
    container.innerHTML = '<div class="text-center p-4"><i class="fas fa-spinner fa-spin fa-2x"></i><p class="mt-3">Loading trading signals...</p></div>';
    
    try {
        let stocks = [];
        let tickerKeys = {};
        if (Array.isArray(forceStocks) && forceStocks.length > 0) {
            stocks = forceStocks.slice(0, 15);
        } else {
            // Fetch tickers from /api/signals/tickers (demat holdings, watchlist, or both)
            let stocksToLoad = [];
            try {
                const tickersRes = await fetch('/api/signals/tickers?source=' + encodeURIComponent(signalsSource));
                const tickersData = await tickersRes.json();
                stocksToLoad = tickersData.tickers || [];
                tickerKeys = tickersData.ticker_keys || {};
            } catch (tickersErr) {
                console.warn('[Signals] Tickers fetch failed, using popular stocks:', tickersErr);
            }
            
            // Fallback to watchlist or popular stocks if empty
            stocks = stocksToLoad.length > 0 ? stocksToLoad : [];
            if (stocks.length === 0) {
                try {
                    const wlRes = await fetch('/api/watchlist');
                    const wl = await wlRes.json();
                    stocks = Array.isArray(wl) && wl.length > 0 ? wl : POPULAR_STOCKS;
                } catch (wlErr) {
                    stocks = POPULAR_STOCKS;
                }
            }
            
            // Limit to first 15 stocks for performance
            stocks = stocks.slice(0, 15);
        }
        
        if (stocks.length === 0) {
            container.innerHTML = '<div class="empty-state"><i class="fas fa-mouse-pointer"></i><p>No stocks available. Add stocks to watchlist or select a stock to view signals.</p></div>';
            return;
        }
        
        // Load signals for all stocks in parallel with retry logic
        const signalPromises = stocks.map(async (ticker) => {
            const maxRetries = 2;
            let retryCount = 0;
            const instKey = tickerKeys[ticker];  // Use instrument_key from holdings when available
            
            while (retryCount <= maxRetries) {
                try {
                    // URL encode ticker to handle special characters like ^
                    const encodedTicker = encodeURIComponent(ticker);
                    let url = `/api/signals/${encodedTicker}`;
                    if (instKey) url += '?instrument_key=' + encodeURIComponent(instKey);
                    const response = await fetch(url, {
                        method: 'GET',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        signal: AbortSignal.timeout(30000) // 30 second timeout
                    });
                    
                    if (!response.ok) {
                        const errorData = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
                        
                        // Only log non-404 errors (404s are expected for invalid tickers)
                        if (response.status !== 404) {
                            console.warn(`Signal API returned ${response.status} for ${ticker}:`, errorData.error);
                        }
                        
                        // Retry on 500 errors (server errors)
                        if (response.status >= 500 && retryCount < maxRetries) {
                            retryCount++;
                            await new Promise(resolve => setTimeout(resolve, 1000 * retryCount)); // Exponential backoff
                            continue;
                        }
                        return null;
                    }
                    
                    const signal = await response.json();
                    if (signal.error && (signal.signal === 'N/A' || !signal.signal)) {
                        // Graceful degradation: show as Data unavailable instead of skipping
                        return { ticker, signal: { ...signal, signal: 'N/A', _dataUnavailable: true } };
                    }
                    if (signal.error) {
                        console.warn(`Signal error for ${ticker}: ${signal.error}`);
                        return null;
                    }
                    return { ticker, signal };
                } catch (error) {
                    console.error(`Error loading signal for ${ticker} (attempt ${retryCount + 1}/${maxRetries + 1}):`, error);
                    
                    // Retry on network errors
                    if (retryCount < maxRetries && (error.name === 'TypeError' || error.name === 'NetworkError')) {
                        retryCount++;
                        await new Promise(resolve => setTimeout(resolve, 1000 * retryCount)); // Exponential backoff
                        continue;
                    }
                    return null;
                }
            }
            return null;
        });
        
        const results = await Promise.all(signalPromises);
        const validSignals = results.filter(r => r !== null);
        const failedTickers = stocks.filter((ticker, index) => results[index] === null);
        
        // Log summary of failed tickers (only if there are failures)
        if (failedTickers.length > 0 && failedTickers.length < stocks.length) {
            console.log(`[Signals] Successfully loaded ${validSignals.length} signals. ${failedTickers.length} ticker(s) failed: ${failedTickers.join(', ')}`);
        }
        
        // Show results or error message
        if (validSignals.length === 0) {
            // Show more helpful error message with troubleshooting tips
            let errorDetails = '';
            if (failedTickers.length > 0) {
                errorDetails = `<p style="font-size: 0.75rem; color: #f59e0b; margin-top: 0.5rem;">
                    <strong>Signal generation failed for:</strong> ${failedTickers.join(', ')}<br>
                    Data may be unavailable (try connecting Upstox) or tickers may need verification.
                </p>`;
            }
            
            container.innerHTML = `
                <div class="empty-state" style="text-align: center; padding: 2rem;">
                    <i class="fas fa-exclamation-triangle" style="font-size: 3rem; color: #f59e0b; margin-bottom: 1rem;"></i>
                    <h4 style="margin-bottom: 0.5rem;">Unable to Load Trading Signals</h4>
                    <p style="font-size: 0.875rem; color: var(--text-muted); margin-top: 0.5rem; max-width: 500px; margin-left: auto; margin-right: auto;">
                        This might be due to:
                        <br>• Network connectivity issues
                        <br>• Market data temporarily unavailable
                        <br>• Server processing delay
                        <br>• Data source API rate limits
                        ${failedTickers.length > 0 ? '<br>• Invalid ticker symbols in watchlist' : ''}
                    </p>
                    ${errorDetails}
                    <div style="margin-top: 1.5rem;">
                        <button class="btn-modern btn-primary" onclick="loadSignals()" style="margin-right: 0.5rem;">
                            <i class="fas fa-sync-alt"></i> Retry Now
                        </button>
                        <button class="btn-modern btn-secondary" onclick="loadSignalsWithPopularStocks()" style="margin-right: 0.5rem;">
                            <i class="fas fa-star"></i> Try Popular Stocks
                        </button>
                        <button class="btn-modern btn-secondary" onclick="loadAllSignals()">
                            <i class="fas fa-redo"></i> Refresh All
                        </button>
                    </div>
                    <p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 1rem;">
                        <i class="fas fa-info-circle"></i> Check browser console (F12) for detailed error messages
                    </p>
                </div>
            `;
            console.error('No signals loaded. Check network and server logs.');
            return;
        }
        
        // Show warning if some signals failed but others succeeded
        let warningMessage = '';
        if (failedTickers.length > 0 && validSignals.length > 0) {
            warningMessage = `
                <div class="alert alert-warning" style="margin-bottom: 1rem; padding: 0.75rem; background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; color: #92400e;">
                    <i class="fas fa-exclamation-triangle"></i> 
                    <strong>Note:</strong> ${validSignals.length} signal(s) shown. 
                    ${failedTickers.length} ticker(s) failed: ${failedTickers.join(', ')}.
                </div>
            `;
        }
        
        // Render signals in a grid with enhanced display
        container.innerHTML = warningMessage + `
            <div class="signals-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1rem; margin-top: 1rem;">
                ${validSignals.map(({ ticker, signal }) => {
                    if (signal._dataUnavailable) {
                        const hint = signal.hint || 'Connect Upstox or verify ticker symbol.';
                        return `
                        <div class="signal-card" style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; padding: 1.25rem; opacity: 0.9;">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <h6 style="margin: 0; font-weight: 700; font-size: 1.1rem;">${ticker.replace('.NS', '')}</h6>
                                <span class="badge bg-secondary" style="font-size: 0.75rem;">Data unavailable</span>
                            </div>
                            <div style="font-size: 0.8rem; color: var(--text-muted);">${hint}</div>
                        </div>`;
                    }
                    const signalClass = signal.signal === 'BUY' ? 'success' : 
                                     signal.signal === 'SELL' ? 'danger' : 'warning';
                    const signalIcon = signal.signal === 'BUY' ? 'fa-arrow-up' : 
                                     signal.signal === 'SELL' ? 'fa-arrow-down' : 'fa-pause';
                    const probPercent = ((signal.probability || 0) * 100).toFixed(1);
                    const confidenceClass = probPercent >= 70 ? 'success' : probPercent >= 50 ? 'warning' : 'secondary';
                    
                    // Calculate potential profit/loss
                    const entryPrice = signal.entry_level || signal.current_price || 0;
                    const stopLoss = signal.stop_loss || 0;
                    const target1 = signal.target_1 || 0;
                    const target2 = signal.target_2 || 0;
                    
                    const riskAmount = Math.abs(entryPrice - stopLoss);
                    const reward1 = Math.abs(target1 - entryPrice);
                    const reward2 = Math.abs(target2 - entryPrice);
                    const riskReward1 = reward1 > 0 ? (reward1 / riskAmount).toFixed(2) : 'N/A';
                    const riskReward2 = reward2 > 0 ? (reward2 / riskAmount).toFixed(2) : 'N/A';
                    
                    return `
                        <div class="signal-card" style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; padding: 1.25rem; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s;" 
                             onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(0,0,0,0.15)'" 
                             onmouseout="this.style.transform=''; this.style.boxShadow=''" 
                             onclick="showLevels('${ticker}')">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <h6 style="margin: 0; font-weight: 700; font-size: 1.1rem;">${ticker.replace('.NS', '')}</h6>
                                <span class="badge bg-${signalClass}" style="font-size: 0.875rem; padding: 0.5rem 0.75rem;">
                                    <i class="fas ${signalIcon}"></i> ${signal.signal}
                                </span>
                            </div>
                            
                            <div class="mb-3" style="background: var(--bg-secondary); padding: 0.75rem; border-radius: 8px;">
                                <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.25rem;">Current Price</div>
                                <div style="font-size: 1.5rem; font-weight: 700; color: var(--text-primary);">₹${(signal.current_price || 0).toFixed(2)}</div>
                            </div>
                            
                            <div class="row mb-3" style="margin: 0;">
                                <div class="col-6" style="padding-right: 0.5rem;">
                                    <div style="font-size: 0.7rem; color: var(--text-muted); margin-bottom: 0.25rem;">Entry Level</div>
                                    <div style="font-size: 0.95rem; font-weight: 600;">₹${entryPrice.toFixed(2)}</div>
                                </div>
                                <div class="col-6" style="padding-left: 0.5rem;">
                                    <div style="font-size: 0.7rem; color: var(--text-muted); margin-bottom: 0.25rem;">Stop Loss</div>
                                    <div style="font-size: 0.95rem; font-weight: 600; color: #ef4444;">₹${stopLoss.toFixed(2)}</div>
                                </div>
                            </div>
                            
                            <div class="row mb-3" style="margin: 0;">
                                <div class="col-6" style="padding-right: 0.5rem;">
                                    <div style="font-size: 0.7rem; color: var(--text-muted); margin-bottom: 0.25rem;">Target 1</div>
                                    <div style="font-size: 0.95rem; font-weight: 600; color: #10b981;">₹${target1.toFixed(2)}</div>
                                </div>
                                <div class="col-6" style="padding-left: 0.5rem;">
                                    <div style="font-size: 0.7rem; color: var(--text-muted); margin-bottom: 0.25rem;">Target 2</div>
                                    <div style="font-size: 0.95rem; font-weight: 600; color: #10b981;">₹${target2.toFixed(2)}</div>
                                </div>
                            </div>
                            
                            <div style="border-top: 1px solid var(--border-color); padding-top: 0.75rem; margin-top: 0.75rem;">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <div style="font-size: 0.7rem; color: var(--text-muted);">Confidence</div>
                                        <div style="font-size: 0.95rem; font-weight: 600;">
                                            <span class="badge bg-${confidenceClass}">${probPercent}%</span>
                                        </div>
                                    </div>
                                    <div style="text-align: right;">
                                        <div style="font-size: 0.7rem; color: var(--text-muted);">Risk:Reward</div>
                                        <div style="font-size: 0.85rem; font-weight: 500;">1:${riskReward1}</div>
                                    </div>
                                </div>
                            </div>
                            
                            ${signal.source ? `<div style="font-size: 0.65rem; color: var(--text-muted); margin-top: 0.5rem; text-align: right;">Source: ${signal.source}</div>` : ''}
                        </div>
                    `;
                }).join('')}
            </div>
        `;
        setSignalsLastUpdated();
    } catch (error) {
        console.error('Error loading signals:', error);
        container.innerHTML = `
            <div class="empty-state" style="text-align: center; padding: 2rem;">
                <i class="fas fa-exclamation-circle" style="font-size: 3rem; color: #ef4444; margin-bottom: 1rem;"></i>
                <h4 style="margin-bottom: 0.5rem;">Error Loading Signals</h4>
                <p style="font-size: 0.875rem; color: var(--text-muted); margin-top: 0.5rem;">
                    ${error.message || 'An unexpected error occurred while loading trading signals.'}
                </p>
                <button class="btn-modern btn-primary mt-3" onclick="loadSignals()">
                    <i class="fas fa-sync-alt"></i> Try Again
                </button>
                <p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 1rem;">
                    Error details: ${error.name || 'Unknown error'}
                </p>
            </div>
        `;
    }
}

function refreshHoldings() {
    loadHoldings();
    showNotification('Holdings refreshed', 'success');
}

// Load all index signals
async function showIndexSignals() {
    const section = document.getElementById('index-signals-section');
    const grid = document.getElementById('index-signals-grid');
    const container = document.getElementById('signals-container');
    
    // Hide other sections
    if (container) container.style.display = 'none';
    
    if (!section || !grid) return;
    
    section.style.display = 'block';
    grid.innerHTML = '<div class="text-center p-4"><i class="fas fa-spinner fa-spin fa-2x"></i><p class="mt-3">Loading index signals...</p></div>';
    
    try {
        const response = await fetch('/api/index-signals', {
            signal: AbortSignal.timeout(60000) // 60 second timeout
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const signals = await response.json();
        
        if (!signals || signals.length === 0) {
            grid.innerHTML = '<div class="text-center text-muted p-4">No index signals available. Please try again later.</div>';
            return;
        }
        
        // Render signals in grid format
        grid.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1rem; margin-top: 1rem;">
                ${signals.map(signal => {
                    const signalClass = signal.signal === 'BUY' ? 'success' : 
                                       signal.signal === 'SELL' ? 'danger' : 'warning';
                    const probPercent = ((signal.probability || signal.confidence || 0) * 100).toFixed(1);
                    const entryPrice = signal.entry_level || signal.entry_price || 0;
                    
                    return `
                        <div class="signal-card" style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 1.25rem;">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <h5 style="margin: 0; font-weight: 700;">${signal.index_name || signal.ticker.replace('^', '').replace('.NS', '').replace('.BO', '')}</h5>
                                <span class="badge bg-${signalClass}" style="font-size: 0.875rem; padding: 0.5rem 0.75rem;">
                                    <i class="fas ${signal.signal === 'BUY' ? 'fa-arrow-up' : signal.signal === 'SELL' ? 'fa-arrow-down' : 'fa-pause'}"></i> ${signal.signal}
                                </span>
                            </div>
                            <div style="background: var(--bg-secondary); padding: 0.75rem; border-radius: 8px; margin-bottom: 1rem;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                    <span style="color: var(--text-muted); font-size: 0.875rem;">Current:</span>
                                    <span style="color: var(--text-primary); font-weight: 600;">₹${(signal.current_price || 0).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                    <span style="color: var(--text-muted); font-size: 0.875rem;">Confidence:</span>
                                    <span style="color: var(--text-primary); font-weight: 600;">${probPercent}%</span>
                                </div>
                                ${signal.signal !== 'HOLD' ? `
                                <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                    <span style="color: var(--text-muted); font-size: 0.875rem;">Entry:</span>
                                    <span style="color: var(--text-primary);">₹${entryPrice.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                    <span style="color: var(--text-muted); font-size: 0.875rem;">Stop Loss:</span>
                                    <span style="color: #ef4444;">₹${(signal.stop_loss || 0).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                                </div>
                                <div style="display: flex; justify-content: space-between;">
                                    <span style="color: var(--text-muted); font-size: 0.875rem;">Target:</span>
                                    <span style="color: #10b981;">₹${(signal.target_1 || 0).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                                </div>
                                ` : '<p style="margin: 0; color: var(--text-muted); font-size: 0.875rem;">No actionable signal</p>'}
                            </div>
                            ${signal.regime_type ? `
                            <div style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid var(--border-color); font-size: 0.75rem; color: var(--text-muted);">
                                <span>${signal.regime_type}</span>
                            </div>
                            ` : ''}
                        </div>
                    `;
                }).join('')}
            </div>
        `;
        setSignalsLastUpdated();
        
    } catch (error) {
        console.error('Error loading index signals:', error);
        grid.innerHTML = `
            <div class="text-center text-danger p-4">
                <i class="fas fa-exclamation-triangle fa-2x mb-3"></i>
                <p><strong>Error loading index signals</strong></p>
                <p style="font-size: 0.875rem; color: var(--text-muted);">${error.message}</p>
                <button class="btn-modern btn-primary mt-3" onclick="showIndexSignals()">
                    <i class="fas fa-sync-alt"></i> Retry
                </button>
            </div>
        `;
    }
}

// Load all BSE/NSE stocks signals
async function loadAllStocksSignals() {
    const container = document.getElementById('signals-container');
    if (!container) return;
    
    // Hide index signals section
    const indexSection = document.getElementById('index-signals-section');
    if (indexSection) indexSection.style.display = 'none';
    
    container.style.display = 'block';
    container.innerHTML = '<div class="text-center p-4"><i class="fas fa-spinner fa-spin fa-2x"></i><p class="mt-3">Loading signals for all BSE/NSE stocks...<br><small>This may take a few moments</small></p></div>';
    
    try {
        // Load first batch (50 stocks)
        const response = await fetch('/api/trading/signals/all-stocks?limit=50&offset=0&min_confidence=0.60', {
            signal: AbortSignal.timeout(120000) // 2 minute timeout
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.status !== 'success' || !data.signals || data.signals.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-info-circle"></i>
                    <p>No signals available. Try adjusting filters or check back later.</p>
                    <button class="btn-modern btn-primary mt-3" onclick="loadAllStocksSignals()">
                        <i class="fas fa-sync-alt"></i> Retry
                    </button>
                </div>
            `;
            return;
        }
        
        // Render signals similar to Adaptive Elite Signals
        let html = `
            <div style="margin-bottom: 1rem; padding: 1rem; background: var(--card-bg); border-radius: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                    <div>
                        <h4 style="margin: 0; color: var(--text-primary);">
                            <i class="fas fa-chart-line"></i> All BSE/NSE Stocks Signals
                        </h4>
                        <p style="margin: 0.5rem 0 0 0; color: var(--text-muted); font-size: 0.875rem;">
                            ${data.summary.buy_signals} BUY | ${data.summary.sell_signals} SELL | ${data.summary.hold_signals} HOLD
                            <br><small>Showing ${data.signals.length} of ${data.pagination.total} stocks</small>
                        </p>
                    </div>
                    <div>
                        <button class="btn-modern btn-secondary" onclick="loadAllStocksSignals()" style="margin-right: 0.5rem;">
                            <i class="fas fa-sync-alt"></i> Refresh
                        </button>
                        ${data.pagination.has_more ? `
                        <button class="btn-modern btn-primary" onclick="loadMoreStocksSignals(${data.pagination.offset + data.pagination.limit})">
                            <i class="fas fa-arrow-down"></i> Load More
                        </button>
                        ` : ''}
                    </div>
                </div>
            </div>
            <div class="signals-grid" id="all-stocks-signals-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1rem;">
        `;
        
        data.signals.forEach(signal => {
            const signalClass = signal.signal === 'BUY' ? 'success' : 
                             signal.signal === 'SELL' ? 'danger' : 'warning';
            const signalIcon = signal.signal === 'BUY' ? 'fa-arrow-up' : 
                             signal.signal === 'SELL' ? 'fa-arrow-down' : 'fa-pause';
            const confidencePercent = (signal.confidence * 100).toFixed(0);
            const confidenceClass = signal.confidence >= 0.75 ? 'success' : 
                                  signal.confidence >= 0.65 ? 'warning' : 'secondary';
            
            html += `
                <div class="signal-card" data-signal-type="${signal.signal}" data-confidence="${signal.confidence}" 
                     style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.75rem;">
                        <div>
                            <h5 style="margin: 0; color: var(--text-primary); font-size: 1rem;">${signal.ticker.replace('.NS', '').replace('.BO', '')}</h5>
                            <span class="badge badge-${signalClass}" style="margin-top: 0.25rem; display: inline-block;">
                                <i class="fas ${signalIcon}"></i> ${signal.signal}
                            </span>
                        </div>
                        <div style="text-align: right;">
                            <div class="badge badge-${confidenceClass}" style="font-size: 0.875rem;">
                                ${confidencePercent}% confidence
                            </div>
                        </div>
                    </div>
                    
                    <div style="margin: 0.75rem 0; padding: 0.75rem; background: var(--bg-secondary); border-radius: 4px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                            <span style="color: var(--text-muted); font-size: 0.875rem;">Current:</span>
                            <span style="color: var(--text-primary); font-weight: 600;">₹${signal.current_price.toLocaleString('en-IN')}</span>
                        </div>
                        ${signal.signal !== 'HOLD' ? `
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                            <span style="color: var(--text-muted); font-size: 0.875rem;">Entry:</span>
                            <span style="color: var(--text-primary);">₹${signal.entry_price.toLocaleString('en-IN')}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                            <span style="color: var(--text-muted); font-size: 0.875rem;">Stop Loss:</span>
                            <span style="color: #ef4444;">₹${signal.stop_loss.toLocaleString('en-IN')}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: var(--text-muted); font-size: 0.875rem;">Target:</span>
                            <span style="color: #10b981;">₹${signal.target_1.toLocaleString('en-IN')}</span>
                        </div>
                        ` : '<p style="margin: 0; color: var(--text-muted); font-size: 0.875rem;">No actionable signal</p>'}
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        container.innerHTML = html;
        
        // Store pagination info
        window.allStocksPagination = data.pagination;
        
    } catch (error) {
        console.error('Error loading all stocks signals:', error);
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-exclamation-triangle"></i>
                <p>Error loading signals: ${error.message}</p>
                <button class="btn-modern btn-primary mt-3" onclick="loadAllStocksSignals()">
                    <i class="fas fa-sync-alt"></i> Retry
                </button>
            </div>
        `;
    }
}

async function loadMoreStocksSignals(offset) {
    const grid = document.getElementById('all-stocks-signals-grid');
    if (!grid) return;
    
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'text-center p-4';
    loadingDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading more...';
    grid.appendChild(loadingDiv);
    
    try {
        const response = await fetch(`/api/trading/signals/all-stocks?limit=50&offset=${offset}&min_confidence=0.60`, {
            signal: AbortSignal.timeout(120000)
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        loadingDiv.remove();
        
        if (data.status === 'success' && data.signals && data.signals.length > 0) {
            // Append new signals
            data.signals.forEach(signal => {
                const signalClass = signal.signal === 'BUY' ? 'success' : 
                                 signal.signal === 'SELL' ? 'danger' : 'warning';
                const signalIcon = signal.signal === 'BUY' ? 'fa-arrow-up' : 
                                 signal.signal === 'SELL' ? 'fa-arrow-down' : 'fa-pause';
                const confidencePercent = (signal.confidence * 100).toFixed(0);
                const confidenceClass = signal.confidence >= 0.75 ? 'success' : 
                                      signal.confidence >= 0.65 ? 'warning' : 'secondary';
                
                const card = document.createElement('div');
                card.className = 'signal-card';
                card.setAttribute('data-signal-type', signal.signal);
                card.setAttribute('data-confidence', signal.confidence);
                card.style.cssText = 'background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 1rem;';
                card.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.75rem;">
                        <div>
                            <h5 style="margin: 0; color: var(--text-primary); font-size: 1rem;">${signal.ticker.replace('.NS', '').replace('.BO', '')}</h5>
                            <span class="badge badge-${signalClass}" style="margin-top: 0.25rem; display: inline-block;">
                                <i class="fas ${signalIcon}"></i> ${signal.signal}
                            </span>
                        </div>
                        <div style="text-align: right;">
                            <div class="badge badge-${confidenceClass}" style="font-size: 0.875rem;">
                                ${confidencePercent}% confidence
                            </div>
                        </div>
                    </div>
                    <div style="margin: 0.75rem 0; padding: 0.75rem; background: var(--bg-secondary); border-radius: 4px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                            <span style="color: var(--text-muted); font-size: 0.875rem;">Current:</span>
                            <span style="color: var(--text-primary); font-weight: 600;">₹${signal.current_price.toLocaleString('en-IN')}</span>
                        </div>
                        ${signal.signal !== 'HOLD' ? `
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                            <span style="color: var(--text-muted); font-size: 0.875rem;">Entry:</span>
                            <span style="color: var(--text-primary);">₹${signal.entry_price.toLocaleString('en-IN')}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                            <span style="color: var(--text-muted); font-size: 0.875rem;">Stop Loss:</span>
                            <span style="color: #ef4444;">₹${signal.stop_loss.toLocaleString('en-IN')}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: var(--text-muted); font-size: 0.875rem;">Target:</span>
                            <span style="color: #10b981;">₹${signal.target_1.toLocaleString('en-IN')}</span>
                        </div>
                        ` : '<p style="margin: 0; color: var(--text-muted); font-size: 0.875rem;">No actionable signal</p>'}
                    </div>
                `;
                grid.appendChild(card);
            });
            
            // Update pagination
            window.allStocksPagination = data.pagination;
            
            // Update load more button if needed
            if (!data.pagination.has_more) {
                const loadMoreBtn = document.querySelector('button[onclick*="loadMoreStocksSignals"]');
                if (loadMoreBtn) loadMoreBtn.style.display = 'none';
            }
        }
    } catch (error) {
        loadingDiv.innerHTML = `<div class="text-danger">Error: ${error.message}</div>`;
    }
}

// Load all signals for holdings
// Load Adaptive Elite signals for watchlist
async function loadAdaptiveEliteSignals() {
    const container = document.getElementById('signals-container');
    if (!container) return;
    
    container.innerHTML = '<div class="text-center p-4"><i class="fas fa-spinner fa-spin fa-2x"></i><p class="mt-3">Loading Adaptive Elite signals...</p></div>';
    
    try {
        const response = await fetch('/api/trading/signals/watchlist');
        const data = await response.json();
        
        if (data.status !== 'success' || !data.signals || data.signals.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-info-circle"></i>
                    <p>No signals available. Add stocks to watchlist or check back later.</p>
                </div>
            `;
            return;
        }
        
        // Filter to show only BUY/SELL signals (high confidence)
        const actionableSignals = data.signals.filter(s => s.signal !== 'HOLD' && s.confidence >= 0.70);
        const allSignals = data.signals;
        
        // Render signals
        let html = `
            <div style="margin-bottom: 1rem; padding: 1rem; background: var(--card-bg); border-radius: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                    <div>
                        <h4 style="margin: 0; color: var(--text-primary);">
                            <i class="fas fa-chart-line"></i> Adaptive Elite Strategy Signals
                        </h4>
                        <p style="margin: 0.5rem 0 0 0; color: var(--text-muted); font-size: 0.875rem;">
                            ${data.summary.buy_signals} BUY | ${data.summary.sell_signals} SELL | ${data.summary.hold_signals} HOLD
                        </p>
                    </div>
                    <div>
                        <button class="btn-modern btn-secondary" onclick="loadAdaptiveEliteSignals()" style="margin-right: 0.5rem;">
                            <i class="fas fa-sync-alt"></i> Refresh
                        </button>
                        <label style="display: inline-flex; align-items: center; cursor: pointer;">
                            <input type="checkbox" id="show-only-actionable" onchange="filterActionableSignals()" style="margin-right: 0.5rem;">
                            <span style="font-size: 0.875rem;">Show only BUY/SELL</span>
                        </label>
                    </div>
                </div>
            </div>
            <div class="signals-grid" id="adaptive-signals-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1rem;">
        `;
        
        // Store all signals for filtering
        window.adaptiveEliteSignals = allSignals;
        
        allSignals.forEach(signal => {
            const signalClass = signal.signal === 'BUY' ? 'success' : 
                             signal.signal === 'SELL' ? 'danger' : 'warning';
            const signalIcon = signal.signal === 'BUY' ? 'fa-arrow-up' : 
                             signal.signal === 'SELL' ? 'fa-arrow-down' : 'fa-pause';
            const confidencePercent = (signal.confidence * 100).toFixed(0);
            const confidenceClass = signal.confidence >= 0.75 ? 'success' : 
                                  signal.confidence >= 0.65 ? 'warning' : 'secondary';
            
            const regimeEmoji = signal.regime_type === 'STRONG_TREND' ? '📈' :
                               signal.regime_type === 'RANGING' ? '📊' :
                               signal.regime_type === 'HIGH_VOLATILITY' ? '⚡' : '📉';
            
            html += `
                <div class="signal-card" data-signal-type="${signal.signal}" data-confidence="${signal.confidence}" 
                     style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 1rem; 
                            ${signal.signal === 'HOLD' || signal.confidence < 0.70 ? 'opacity: 0.7;' : ''}">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.75rem;">
                        <div>
                            <h5 style="margin: 0; color: var(--text-primary); font-size: 1rem;">${signal.ticker}</h5>
                            <span class="badge badge-${signalClass}" style="margin-top: 0.25rem; display: inline-block;">
                                <i class="fas ${signalIcon}"></i> ${signal.signal}
                            </span>
                        </div>
                        <div style="text-align: right;">
                            <div class="badge badge-${confidenceClass}" style="font-size: 0.875rem;">
                                ${confidencePercent}% confidence
                            </div>
                        </div>
                    </div>
                    
                    <div style="margin: 0.75rem 0; padding: 0.75rem; background: var(--bg-secondary); border-radius: 4px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                            <span style="color: var(--text-muted); font-size: 0.875rem;">Current:</span>
                            <span style="color: var(--text-primary); font-weight: 600;">₹${signal.current_price.toLocaleString('en-IN')}</span>
                        </div>
                        ${signal.signal !== 'HOLD' ? `
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                            <span style="color: var(--text-muted); font-size: 0.875rem;">Entry:</span>
                            <span style="color: var(--text-primary);">₹${signal.entry_price.toLocaleString('en-IN')}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                            <span style="color: var(--text-muted); font-size: 0.875rem;">Stop Loss:</span>
                            <span style="color: #ef4444;">₹${signal.stop_loss.toLocaleString('en-IN')}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: var(--text-muted); font-size: 0.875rem;">Target:</span>
                            <span style="color: #10b981;">₹${signal.target_1.toLocaleString('en-IN')}</span>
                        </div>
                        ` : '<p style="margin: 0; color: var(--text-muted); font-size: 0.875rem;">No actionable signal</p>'}
                    </div>
                    
                    <div style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid var(--border-color);">
                        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem; color: var(--text-muted);">
                            <span>${regimeEmoji} ${signal.regime_type}</span>
                            <span>${signal.market_phase}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-top: 0.25rem; font-size: 0.75rem; color: var(--text-muted);">
                            <span>Trend: ${signal.trend_strength}</span>
                            <span>Vol: ${signal.volatility_pct}%</span>
                        </div>
                    </div>
                    
                    ${signal.signal !== 'HOLD' ? `
                    <div style="margin-top: 0.75rem;">
                        <button class="btn-modern btn-primary" onclick="quickOrderFromSignal('${signal.ticker}', '${signal.signal}', ${signal.entry_price})" 
                                style="width: 100%; font-size: 0.875rem;">
                            <i class="fas fa-shopping-cart"></i> Place Order
                        </button>
                    </div>
                    ` : ''}
                </div>
            `;
        });
        
        html += '</div>';
        container.innerHTML = html;
        setSignalsLastUpdated();
        
    } catch (error) {
        console.error('Error loading adaptive elite signals:', error);
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-exclamation-triangle"></i>
                <p>Error loading signals. Please try again.</p>
                <button class="btn-modern btn-primary" onclick="loadAdaptiveEliteSignals()">
                    <i class="fas fa-sync-alt"></i> Retry
                </button>
            </div>
        `;
    }
}

function filterActionableSignals() {
    const checkbox = document.getElementById('show-only-actionable');
    const grid = document.getElementById('adaptive-signals-grid');
    if (!grid || !checkbox) return;
    
    const cards = grid.querySelectorAll('.signal-card');
    cards.forEach(card => {
        const signalType = card.getAttribute('data-signal-type');
        const confidence = parseFloat(card.getAttribute('data-confidence'));
        
        if (checkbox.checked) {
            // Show only BUY/SELL with high confidence
            if (signalType === 'HOLD' || confidence < 0.70) {
                card.style.display = 'none';
            } else {
                card.style.display = 'block';
            }
        } else {
            // Show all
            card.style.display = 'block';
        }
    });
}

function quickOrderFromSignal(ticker, signal, entryPrice) {
    // Open order placement modal with pre-filled data
    if (typeof quickOrder === 'function') {
        quickOrder(ticker, signal === 'BUY' ? 'BUY' : 'SELL');
    } else {
        alert(`Place ${signal} order for ${ticker} at ₹${entryPrice.toLocaleString('en-IN')}`);
    }
}

async function loadAllSignals() {
    showNotification('Loading signals for all stocks...', 'info');
    
    // Load signals in the signals tab
    await loadSignals();
    
    // Also reload holdings to refresh signals in holdings table
    if (typeof loadHoldings === 'function') {
        await loadHoldings();
    }
    
    showNotification('Signals refreshed!', 'success');
}

function refreshAllSignals() {
    loadAllSignals();
    loadWatchlist().then(() => {
        const watchlist = document.querySelectorAll('.watchlist-item');
        watchlist.forEach(item => {
            const ticker = item.dataset.ticker;
            if (ticker) {
                showLevels(ticker);
            }
        });
    });
    showNotification('All signals refreshed', 'success');
}

function showAddStockModal() {
    const modal = new bootstrap.Modal(document.getElementById('addStockModal'));
    modal.show();
}

function addStockToHoldings() {
    const ticker = document.getElementById('stock-ticker').value.trim();
    const qty = parseInt(document.getElementById('stock-quantity').value);
    const avgPrice = parseFloat(document.getElementById('stock-avg-price').value);
    
    if (!ticker || !qty || !avgPrice) {
        showNotification('Please fill all fields', 'warning');
        return;
    }
    
    // Add to watchlist first
    addToWatchlistFromInput(ticker).then(() => {
        bootstrap.Modal.getInstance(document.getElementById('addStockModal')).hide();
        document.getElementById('add-stock-form').reset();
        loadHoldings();
        showNotification('Stock added to holdings', 'success');
    });
}

async function addToWatchlistFromInput(ticker) {
    try {
        const response = await fetch('/api/watchlist/add', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ticker: ticker})
        });
        return await response.json();
    } catch (error) {
        console.error('Error adding to watchlist:', error);
    }
}

function quickOrder(ticker, type) {
    document.getElementById('order-ticker').value = ticker;
    document.getElementById('order-type').value = type;
    const modal = new bootstrap.Modal(document.getElementById('orderModal'));
    modal.show();
}

// Mobile Sidebar Toggle
function toggleMobileSidebar() {
    const sidebar = document.getElementById('mobile-sidebar');
    const overlay = document.getElementById('mobile-overlay');
    
    if (sidebar && overlay) {
        sidebar.classList.toggle('mobile-open');
        overlay.classList.toggle('active');
        
        // Prevent body scroll when sidebar is open
        if (sidebar.classList.contains('mobile-open')) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
    }
}

// --- All NSE/BSE Stocks modal ---
function openStocksUniverseModal() {
    stocksUniverseOffset = 0;
    const modal = new (window.bootstrap && window.bootstrap.Modal)(document.getElementById('stocksUniverseModal'));
    modal.show();
    loadStocksUniversePage(0);
}

async function loadStocksUniversePage(offset) {
    const tbody = document.getElementById('stocks-universe-tbody');
    const totalEl = document.getElementById('stocks-universe-total');
    const rangeEl = document.getElementById('stocks-universe-range');
    const prevBtn = document.getElementById('stocks-universe-prev');
    const nextBtn = document.getElementById('stocks-universe-next');
    if (!tbody) return;

    const exchange = document.getElementById('stocks-universe-exchange') && document.getElementById('stocks-universe-exchange').value;
    const search = document.getElementById('stocks-universe-search') && document.getElementById('stocks-universe-search').value;

    tbody.innerHTML = '<tr><td colspan="4" class="text-center"><i class="fas fa-spinner fa-spin"></i> Loading...</td></tr>';
    try {
        const params = new URLSearchParams({ limit: stocksUniverseLimit, offset: String(offset >= 0 ? offset : 0) });
        if (exchange) params.set('exchange', exchange);
        if (search) params.set('search', search);
        const res = await fetch('/api/stocks/universe?' + params.toString());
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to load stocks');

        stocksUniverseOffset = offset >= 0 ? offset : 0;
        const total = data.total || 0;
        const stocks = data.stocks || [];

        totalEl.textContent = total + ' stock(s)';
        rangeEl.textContent = total === 0 ? '—' : (stocksUniverseOffset + 1) + '–' + Math.min(stocksUniverseOffset + stocksUniverseLimit, total) + ' of ' + total;
        prevBtn.disabled = stocksUniverseOffset <= 0;
        nextBtn.disabled = stocksUniverseOffset + stocksUniverseLimit >= total;

        if (stocks.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No stocks found.</td></tr>';
            return;
        }
        tbody.innerHTML = stocks.map(s => {
            const ticker = s.ticker || (s.tradingsymbol + (s.exchange === 'BSE' ? '.BO' : '.NS'));
            return '<tr><td><code>' + (s.ticker || ticker) + '</code></td><td>' + (s.exchange || '') + '</td><td>' + (s.name || s.tradingsymbol || '') + '</td><td><button class="btn-modern btn-primary btn-sm" onclick="addToWatchlistFromUniverse(\'' + ticker.replace(/'/g, "\\'") + '\'); document.getElementById(\'stocksUniverseModal\').querySelector(\'[data-bs-dismiss=modal]\').click();">Add to watchlist</button></td></tr>';
        }).join('');
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger">' + (e.message || 'Error loading stocks') + '</td></tr>';
        if (totalEl) totalEl.textContent = '—';
        if (rangeEl) rangeEl.textContent = '—';
    }
}

function addToWatchlistFromUniverse(ticker) {
    if (typeof addToWatchlist === 'function') {
        addToWatchlist(ticker);
    } else {
        fetch('/api/watchlist/add', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ticker: ticker }) })
            .then(r => r.json()).then(d => { if (d.error) showNotification(d.error, 'error'); else showNotification('Added ' + ticker, 'success'); });
    }
}

// Include all functions from dashboard.js
// (Keeping existing functions for compatibility)
