// Trading Platform JavaScript - Upstox-like functionality

let currentTab = 'holdings';
let holdingsData = [];
let selectedStock = null;

// Initialize platform
document.addEventListener('DOMContentLoaded', function() {
    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'dark';
    setTheme(savedTheme);
    
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
    
    // Auto-refresh
    setInterval(() => {
        loadMarketIndices();
        loadHoldings();
        updatePrices();
    }, 30000);
    
    // Stock search
    document.getElementById('stock-search')?.addEventListener('input', function(e) {
        filterStockList(e.target.value);
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

// Load Market Indices
async function loadMarketIndices() {
    const indices = [
        { id: 'nifty', ticker: '^NSEI', label: 'NIFTY' },
        { id: 'sensex', ticker: '^BSESN', label: 'SENSEX' },
        { id: 'banknifty', ticker: '^NSEBANK', label: 'BANKNIFTY' },
        { id: 'vix', ticker: '^INDIAVIX', label: 'INDIA VIX' }
    ];
    
    for (const index of indices) {
        try {
            const response = await fetch(`/api/prices`);
            const prices = await response.json();
            
            if (prices[index.ticker] && !prices[index.ticker].error) {
                const price = prices[index.ticker];
                updateIndexDisplay(index.id, price.price, price.change, price.change_pct);
            }
        } catch (error) {
            console.error(`Error loading ${index.label}:`, error);
        }
    }
}

// Check Upstox connection status
async function checkUpstoxConnection() {
    try {
        const response = await fetch('/api/upstox/status');
        const status = await response.json();
        
        if (status.connected) {
            const statusEl = document.getElementById('connection-status');
            if (statusEl) {
                statusEl.innerHTML = '<i class="fas fa-circle"></i><span class="mobile-hide">Connected</span>';
                statusEl.classList.add('connected');
            }
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
    
    if (valueEl) {
        valueEl.textContent = value.toFixed(2);
    }
    
    if (changeEl) {
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
            
            // Show user-friendly message
            const tbody = document.getElementById('holdings-table-body');
            if (tbody) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="10" class="text-center text-muted">
                            <div style="padding: 2rem;">
                                <i class="fas fa-exclamation-triangle" style="font-size: 2rem; color: #f59e0b; margin-bottom: 1rem;"></i>
                                <p><strong>Upstox Not Connected</strong></p>
                                <p>Please click "Connect" button to connect your Upstox account.</p>
                                <p style="font-size: 0.875rem; color: #94a3b8; margin-top: 0.5rem;">
                                    Debug: ${status.error || 'No error message'}
                                </p>
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
                    signalEl.innerHTML = `<span class="badge ${badgeClass}">${signal.signal}</span>`;
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
        
        const pricesResponse = await fetch('/api/prices');
        const prices = await pricesResponse.json();
        
        const container = document.getElementById('stock-list-container');
        if (!container) return;
        
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
        
        document.getElementById('top-stocks-count').textContent = stocks.length;
        
    } catch (error) {
        console.error('Error loading top stocks:', error);
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
function switchTab(tabName) {
    currentTab = tabName;
    
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.tab === tabName) {
            btn.classList.add('active');
        }
    });
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
        if (content.id === `tab-${tabName}`) {
            content.classList.add('active');
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
        loadSignals();
    } else if (tabName === 'trade-plans') {
        if (typeof loadTradePlans === 'function') {
            loadTradePlans();
        }
    }
}

function filterHoldings(filter) {
    // Filter logic for holdings
    renderHoldingsTable();
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
            const pnl = pos.pnl || (paperMode ? pos.pnl : {});
            const pnlValue = paperMode ? (pos.pnl || 0) : (pos.overall_pnl || pos.intraday_pnl || 0);
            const pnlPct = paperMode ? (pos.pnl_pct || 0) : (pos.pnl_pct || 0);
            const pnlClass = pnlValue >= 0 ? 'positive' : 'negative';
            const symbol = pos.symbol || pos.tradingsymbol || 'N/A';
            const quantity = pos.quantity || 0;
            const entryPrice = pos.entry_price || pos.average_price || 0;
            const exitPrice = pos.exit_price || pos.last_price || entryPrice;
            const entryTime = pos.entry_time ? new Date(pos.entry_time).toLocaleString() : 'N/A';
            const exitTime = pos.exit_time ? new Date(pos.exit_time).toLocaleString() : '-';
            const status = pos.status || 'OPEN';
            const statusBadge = status === 'OPEN' ? '<span class="badge bg-success">Open</span>' : '<span class="badge bg-secondary">Closed</span>';
            
            return `
                <tr>
                    <td class="symbol">${symbol}${paperMode ? ' <span class="badge bg-info">Paper</span>' : ''}</td>
                    <td>${quantity}</td>
                    <td>₹${entryPrice.toFixed(2)}</td>
                    <td>${exitPrice ? '₹' + exitPrice.toFixed(2) : '-'}</td>
                    <td>${entryTime}</td>
                    <td>${exitTime}</td>
                    <td class="${pnlClass}">₹${pnlValue >= 0 ? '+' : ''}${pnlValue.toFixed(2)}</td>
                    <td class="${pnlClass}">${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}%</td>
                    <td>${statusBadge}</td>
                    <td>
                        <button class="btn-action btn-view" onclick="selectStock('${symbol}')">View</button>
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

function loadSignals() {
    // Load signals for all watchlist stocks
    const container = document.getElementById('signals-container');
    if (!container) return;
    
    container.innerHTML = '<div class="empty-state"><i class="fas fa-mouse-pointer"></i><p>Select a stock to view trading signals</p></div>';
}

function refreshHoldings() {
    loadHoldings();
    showNotification('Holdings refreshed', 'success');
}

// Load all index signals
async function showIndexSignals() {
    const section = document.getElementById('index-signals-section');
    const grid = document.getElementById('index-signals-grid');
    
    if (!section || !grid) return;
    
    section.style.display = 'block';
    grid.innerHTML = '<div class="text-center"><i class="fas fa-spinner fa-spin"></i> Loading index signals...</div>';
    
    try {
        const response = await fetch('/api/index-signals');
        const signals = await response.json();
        
        if (signals.length === 0) {
            grid.innerHTML = '<div class="text-center text-muted">No index signals available</div>';
            return;
        }
        
        grid.innerHTML = signals.map(signal => {
            const signalClass = signal.signal === 'BUY' ? 'success' : 
                               signal.signal === 'SELL' ? 'danger' : 'warning';
            const probPercent = (signal.probability * 100).toFixed(1);
            
            return `
                <div class="signal-card">
                    <div class="signal-header">
                        <h4>${signal.index_name || signal.ticker}</h4>
                        <span class="badge bg-${signalClass}">${signal.signal}</span>
                    </div>
                    <div class="signal-body">
                        <div class="signal-item">
                            <span class="label">Current Price:</span>
                            <span class="value">₹${signal.current_price.toFixed(2)}</span>
                        </div>
                        <div class="signal-item">
                            <span class="label">Probability:</span>
                            <span class="value">${probPercent}%</span>
                        </div>
                        <div class="signal-item">
                            <span class="label">Entry Level:</span>
                            <span class="value">₹${signal.entry_level.toFixed(2)}</span>
                        </div>
                        <div class="signal-item">
                            <span class="label">Stop Loss:</span>
                            <span class="value">₹${signal.stop_loss.toFixed(2)}</span>
                        </div>
                        <div class="signal-item">
                            <span class="label">Target 1:</span>
                            <span class="value">₹${signal.target_1.toFixed(2)}</span>
                        </div>
                        <div class="signal-item">
                            <span class="label">Target 2:</span>
                            <span class="value">₹${signal.target_2.toFixed(2)}</span>
                        </div>
                    </div>
                    <div class="signal-footer mt-2">
                        <button class="btn-modern btn-primary btn-sm me-1" onclick="generateTradePlan('${signal.ticker || signal.index_name}', 'intraday')" title="Generate Intraday Plan">
                            <i class="fas fa-clock"></i> Intraday
                        </button>
                        <button class="btn-modern btn-info btn-sm me-1" onclick="generateTradePlan('${signal.ticker || signal.index_name}', 'swing')" title="Generate Swing Plan">
                            <i class="fas fa-chart-line"></i> Swing
                        </button>
                        <button class="btn-modern btn-warning btn-sm" onclick="generateTradePlan('${signal.ticker || signal.index_name}', 'position')" title="Generate Position Plan">
                            <i class="fas fa-chart-area"></i> Position
                        </button>
                    </div>
                </div>
            `;
        }).join('');
        
    } catch (error) {
        console.error('Error loading index signals:', error);
        grid.innerHTML = '<div class="text-center text-danger">Error loading index signals</div>';
    }
}

// Load all signals for holdings
async function loadAllSignals() {
    showNotification('Loading signals for all holdings...', 'info');
    
    // Reload holdings to refresh signals
    await loadHoldings();
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

// Include all functions from dashboard.js
// (Keeping existing functions for compatibility)
