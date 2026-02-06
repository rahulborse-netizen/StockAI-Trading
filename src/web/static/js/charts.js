// Chart.js integration for live trading charts
let stockCharts = {}; // Store chart instances

/**
 * Load and display chart for a stock
 */
// Phase 2.4: Portfolio performance charts

/**
 * Load portfolio value over time chart
 */
async function loadPortfolioValueChart() {
    try {
        const response = await fetch('/api/portfolio/history?days=30');
        const history = await response.json();
        
        if (!history || history.length === 0) {
            console.warn('No portfolio history data available');
            return;
        }
        
        const ctx = document.getElementById('portfolio-value-chart');
        if (!ctx) return;
        
        const dates = history.map(h => h.timestamp);
        const values = history.map(h => h.total_value);
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: dates,
                datasets: [{
                    label: 'Portfolio Value',
                    data: values,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    title: {
                        display: true,
                        text: 'Portfolio Value Over Time'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        ticks: {
                            callback: function(value) {
                                return '₹' + value.toLocaleString('en-IN');
                            }
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading portfolio value chart:', error);
    }
}

/**
 * Load daily P&L chart
 */
async function loadDailyPnLChart() {
    try {
        const response = await fetch('/api/portfolio/history?days=30');
        const history = await response.json();
        
        if (!history || history.length === 0) {
            console.warn('No portfolio history data available');
            return;
        }
        
        const ctx = document.getElementById('daily-pnl-chart');
        if (!ctx) return;
        
        const dates = history.map(h => h.timestamp);
        const dailyPnL = history.map(h => h.daily_pnl);
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: dates,
                datasets: [{
                    label: 'Daily P&L',
                    data: dailyPnL,
                    backgroundColor: dailyPnL.map(pnl => pnl >= 0 ? 'rgba(16, 185, 129, 0.6)' : 'rgba(239, 68, 68, 0.6)'),
                    borderColor: dailyPnL.map(pnl => pnl >= 0 ? '#10b981' : '#ef4444'),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    title: {
                        display: true,
                        text: 'Daily P&L'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        ticks: {
                            callback: function(value) {
                                return '₹' + value.toLocaleString('en-IN');
                            }
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading daily P&L chart:', error);
    }
}

/**
 * Load asset allocation pie chart
 */
async function loadAllocationChart() {
    try {
        const response = await fetch('/api/holdings');
        const holdings = await response.json();
        
        if (!holdings || holdings.length === 0) {
            console.warn('No holdings data available');
            return;
        }
        
        const ctx = document.getElementById('allocation-chart');
        if (!ctx) return;
        
        const labels = holdings.map(h => h.symbol || 'Unknown');
        const values = holdings.map(h => {
            const qty = parseFloat(h.qty || h.quantity || 0);
            const price = parseFloat(h.ltp || h.current_price || 0);
            return qty * price;
        });
        
        new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: [
                        '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
                        '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'right'
                    },
                    title: {
                        display: true,
                        text: 'Asset Allocation'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${label}: ₹${value.toLocaleString('en-IN')} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading allocation chart:', error);
    }
}

/**
 * Load returns comparison chart (Portfolio vs NIFTY50)
 */
async function loadReturnsComparisonChart() {
    try {
        const portfolioResponse = await fetch('/api/portfolio/history?days=30');
        const portfolioHistory = await portfolioResponse.json();
        
        if (!portfolioHistory || portfolioHistory.length === 0) {
            console.warn('No portfolio history data available');
            return;
        }
        
        const ctx = document.getElementById('returns-comparison-chart');
        if (!ctx) return;
        
        // Calculate portfolio returns
        const portfolioReturns = portfolioHistory.map((h, i) => {
            if (i === 0) return 0;
            const prevValue = portfolioHistory[i-1].total_value;
            const currentValue = h.total_value;
            return ((currentValue - prevValue) / prevValue) * 100;
        });
        
        // For NIFTY50, we'd need to fetch index data
        // For now, use placeholder data
        const dates = portfolioHistory.map(h => h.timestamp);
        const niftyReturns = portfolioReturns.map(() => Math.random() * 2 - 1); // Placeholder
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: dates,
                datasets: [{
                    label: 'Portfolio Returns',
                    data: portfolioReturns,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4
                }, {
                    label: 'NIFTY50 Returns',
                    data: niftyReturns,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    title: {
                        display: true,
                        text: 'Returns Comparison: Portfolio vs NIFTY50'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        ticks: {
                            callback: function(value) {
                                return value.toFixed(2) + '%';
                            }
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading returns comparison chart:', error);
    }
}

async function loadStockChart(symbol, ticker = null) {
    try {
        // Use ticker if provided, otherwise try to convert symbol to ticker
        let stockTicker = ticker || convertSymbolToTicker(symbol);
        if (!stockTicker) {
            console.error(`[Chart] Could not determine ticker for symbol: ${symbol}`);
            showNotification(`Could not determine ticker for ${symbol}. Please check the symbol.`, 'error');
            return;
        }

        console.log(`[Chart] Loading chart for ${symbol} (${stockTicker})`);
        
        // Show loading indicator
        showNotification(`Loading chart for ${symbol}...`, 'info');
        
        // Fetch historical data for chart
        let response = await fetch(`/api/chart-data/${encodeURIComponent(stockTicker)}`);
        
        // If first attempt fails, try alternative ticker formats
        if (!response.ok) {
            console.log(`[Chart] First attempt failed, trying alternative ticker formats...`);
            const alternative = await tryMultipleTickerFormats(symbol);
            if (alternative) {
                showChartModal(symbol, alternative.data);
                showNotification(`Chart loaded for ${symbol}`, 'success');
                return;
            }
        }
        
        if (!response.ok) {
            let errorMessage = `Failed to fetch chart data (${response.status})`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorMessage;
                if (errorData.suggestion) {
                    errorMessage += `\n\n${errorData.suggestion}`;
                }
            } catch (e) {
                // If JSON parsing fails, use status text
                errorMessage = `Server error: ${response.status} ${response.statusText}`;
            }
            throw new Error(errorMessage);
        }
        
        const chartData = await response.json();
        
        if (chartData.error) {
            throw new Error(chartData.error + (chartData.suggestion ? `\n\n${chartData.suggestion}` : ''));
        }
        
        if (!chartData.dates || !chartData.prices || chartData.prices.length === 0) {
            throw new Error('No chart data available. The ticker might not have historical data.');
        }
        
        // Show chart in modal
        showChartModal(symbol, chartData);
        showNotification(`Chart loaded for ${symbol}`, 'success');
        
    } catch (error) {
        console.error(`[Chart] Error loading chart for ${symbol}:`, error);
        const errorMsg = error.message || 'Unknown error occurred';
        showNotification(`Failed to load chart for ${symbol}:\n${errorMsg}`, 'error');
    }
}

/**
 * Show chart in modal
 */
function showChartModal(symbol, chartData) {
    const modal = new bootstrap.Modal(document.getElementById('chartModal'));
    document.getElementById('chart-modal-title').textContent = `${symbol} - Live Chart`;
    
    const canvas = document.getElementById('stockChart');
    const ctx = canvas.getContext('2d');
    
    // Destroy existing chart if any
    if (stockCharts[symbol]) {
        stockCharts[symbol].destroy();
    }
    
    // Prepare data for Chart.js
    const labels = chartData.dates || [];
    const prices = chartData.prices || [];
    
    stockCharts[symbol] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Price',
                data: prices,
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return `₹${context.parsed.y.toFixed(2)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#cbd5e1'
                    }
                },
                y: {
                    display: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#cbd5e1',
                        callback: function(value) {
                            return '₹' + value.toFixed(2);
                        }
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
    
    modal.show();
}

/**
 * Convert symbol to ticker format (e.g., "FSL" -> "FSL.NS")
 * Tries multiple formats if first attempt fails
 */
function convertSymbolToTicker(symbol) {
    if (!symbol || symbol === 'N/A') return null;
    
    // If already in ticker format, return as is
    if (symbol.includes('.NS') || symbol.includes('.BO')) {
        return symbol;
    }
    
    // Try NSE first (most common)
    return `${symbol.toUpperCase()}.NS`;
}

/**
 * Try multiple ticker formats for a symbol
 */
async function tryMultipleTickerFormats(symbol) {
    const formats = [
        `${symbol}.NS`,      // NSE
        `${symbol}.BO`,      // BSE
        symbol,              // As-is (might be index)
        `^${symbol}`,        // Index format
    ];
    
    for (const ticker of formats) {
        try {
            const response = await fetch(`/api/chart-data/${encodeURIComponent(ticker)}`);
            if (response.ok) {
                const data = await response.json();
                if (!data.error && data.prices && data.prices.length > 0) {
                    console.log(`[Chart] Found data with ticker format: ${ticker}`);
                    return { ticker, data };
                }
            }
        } catch (e) {
            // Try next format
            continue;
        }
    }
    
    return null;
}

/**
 * Get trading signal for a stock
 */
async function getStockSignal(symbol, ticker = null) {
    try {
        const stockTicker = ticker || convertSymbolToTicker(symbol);
        if (!stockTicker) {
            return { signal: 'N/A', color: 'muted' };
        }
        
        const response = await fetch(`/api/signals/${encodeURIComponent(stockTicker)}`);
        if (!response.ok) {
            return { signal: 'N/A', color: 'muted' };
        }
        
        const signalData = await response.json();
        
        if (signalData.signal === 'BUY') {
            return { signal: 'BUY', color: 'success', probability: signalData.probability };
        } else if (signalData.signal === 'SELL') {
            return { signal: 'SELL', color: 'danger', probability: signalData.probability };
        } else {
            return { signal: 'HOLD', color: 'warning', probability: signalData.probability };
        }
    } catch (error) {
        console.error(`[Signal] Error getting signal for ${symbol}:`, error);
        return { signal: 'N/A', color: 'muted' };
    }
}
