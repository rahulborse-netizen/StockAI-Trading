/**
 * Auto Trading Dashboard JavaScript
 * Real-time monitoring and control for automated trading system
 */

class AutoTradingDashboard {
    constructor() {
        this.updateInterval = null;
        this.statusUpdateInterval = null;
        this.performanceChart = null;
        this.performanceData = {
            labels: [],
            pnl: [],
            trades: []
        };
        this.init();
    }
    
    init() {
        // Load initial data
        this.loadStatus();
        this.loadHistory();
        this.loadSignals();
        this.loadPositions();
        
        // Set up auto-refresh
        this.statusUpdateInterval = setInterval(() => {
            this.loadStatus();
        }, 3000); // Update status every 3 seconds
        
        this.updateInterval = setInterval(() => {
            this.loadHistory();
            this.loadSignals();
            this.loadPositions();
        }, 10000); // Update data every 10 seconds
        
        // Initialize performance chart
        this.initPerformanceChart();
        
        // Handle page visibility
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pauseUpdates();
            } else {
                this.resumeUpdates();
            }
        });
    }
    
    async loadStatus() {
        try {
            const response = await fetch('/api/auto-trading/status');
            const data = await response.json();
            this.updateStatusDisplay(data);
        } catch (error) {
            console.error('Error loading status:', error);
            this.showAlert('Error loading status: ' + error.message, 'danger');
        }
    }
    
    updateStatusDisplay(data) {
        // Update status indicator
        const indicator = document.getElementById('status-indicator');
        const statusText = document.getElementById('status-text');
        
        if (data.is_running) {
            indicator.className = 'status-indicator status-running';
            statusText.textContent = 'Running';
            document.getElementById('btn-start').disabled = true;
            document.getElementById('btn-stop').disabled = false;
            document.getElementById('btn-pause').disabled = false;
        } else {
            indicator.className = 'status-indicator status-stopped';
            statusText.textContent = 'Stopped';
            document.getElementById('btn-start').disabled = false;
            document.getElementById('btn-stop').disabled = true;
            document.getElementById('btn-pause').disabled = true;
        }
        
        // Update market status
        if (data.market_status) {
            const marketStatus = data.market_status.status || 'Unknown';
            const marketEl = document.getElementById('market-status');
            marketEl.textContent = marketStatus;
            marketEl.className = 'metric-value ' + (
                marketStatus === 'OPEN' ? 'positive' : 
                marketStatus === 'CLOSED' ? 'negative' : ''
            );
        }
        
        // Update Upstox connection
        const upstoxStatus = data.upstox_connected ? 'Connected' : 'Disconnected';
        const upstoxEl = document.getElementById('upstox-status');
        upstoxEl.textContent = upstoxStatus;
        upstoxEl.className = 'metric-value ' + (data.upstox_connected ? 'positive' : 'negative');
        
        // Update trading mode
        if (data.trading_mode) {
            document.getElementById('trading-mode').textContent = 
                data.trading_mode.charAt(0).toUpperCase() + data.trading_mode.slice(1);
        }
        
        // Update statistics
        const totalSignals = (data.executed_signals_count || 0) + (data.rejected_signals_count || 0);
        document.getElementById('signals-generated').textContent = totalSignals;
        document.getElementById('trades-executed').textContent = data.executed_signals_count || 0;
        document.getElementById('trades-rejected').textContent = data.rejected_signals_count || 0;
        
        // Calculate success rate
        const successRate = totalSignals > 0 
            ? ((data.executed_signals_count || 0) / totalSignals * 100).toFixed(1)
            : 0;
        const successRateEl = document.getElementById('success-rate');
        successRateEl.textContent = successRate + '%';
        successRateEl.className = 'metric-value ' + (successRate >= 50 ? 'positive' : 'negative');
        
        // Update risk management
        if (data.circuit_breaker) {
            const cb = data.circuit_breaker;
            const dailyPnl = cb.daily_pnl || 0;
            const dailyPnlEl = document.getElementById('daily-pnl');
            dailyPnlEl.textContent = `Rs ${dailyPnl.toFixed(2)}`;
            dailyPnlEl.className = 'metric-value ' + (dailyPnl >= 0 ? 'positive' : 'negative');
            
            document.getElementById('consecutive-losses').textContent = cb.consecutive_losses || 0;
            
            const cbStatus = cb.triggered ? 'Active' : 'Inactive';
            const cbStatusEl = document.getElementById('circuit-breaker-status');
            cbStatusEl.textContent = cbStatus;
            cbStatusEl.className = 'metric-value ' + (cb.triggered ? 'negative' : 'positive');
            
            // Show alert if circuit breaker is active
            if (cb.triggered) {
                this.showAlert(
                    `Circuit breaker is ACTIVE. Trading paused due to ${cb.consecutive_losses} consecutive losses or daily loss limit.`,
                    'warning'
                );
            }
        }
        
        // Update open positions count
        if (data.open_positions !== undefined) {
            document.getElementById('open-positions').textContent = data.open_positions || 0;
        }
        const accEl = document.getElementById('accuracy-30d');
        const wrEl = document.getElementById('win-rate-30d');
        if (accEl) accEl.textContent = data.accuracy_30d != null ? data.accuracy_30d + '%' : '—';
        if (wrEl) wrEl.textContent = data.win_rate_30d != null ? data.win_rate_30d + '%' : '—';
        // Update algo settings display
        const setEl = (id, text) => { const el = document.getElementById(id); if (el) el.textContent = text; };
        setEl('algo-confidence', (data.confidence_threshold != null) ? String(data.confidence_threshold) : '—');
        setEl('algo-max-positions', (data.max_positions != null) ? String(data.max_positions) : '—');
        if (data.circuit_breaker) {
            const cb = data.circuit_breaker;
            setEl('algo-daily-loss-pct', (cb.daily_loss_limit_pct != null) ? (cb.daily_loss_limit_pct * 100) + '%' : '—');
            setEl('algo-max-consec-losses', (cb.max_consecutive_losses != null) ? String(cb.max_consecutive_losses) : '—');
            setEl('algo-cooldown-min', (cb.cooldown_minutes != null) ? String(cb.cooldown_minutes) : '—');
        }
        const signalSourceEl = document.getElementById('signal-source-select');
        if (signalSourceEl && data.signal_source) {
            signalSourceEl.value = data.signal_source;
        }
        const quantStrategyEl = document.getElementById('active-quant-strategy-select');
        if (quantStrategyEl) {
            if (data.available_quant_strategies && data.available_quant_strategies.length) {
                quantStrategyEl.innerHTML = data.available_quant_strategies.map(s =>
                    '<option value="' + s + '">' + s.replace(/_/g, ' ') + '</option>'
                ).join('');
            }
            if (data.active_quant_strategy) {
                quantStrategyEl.value = data.active_quant_strategy;
            }
        }
    }
    
    async loadHistory() {
        try {
            const response = await fetch('/api/auto-trading/history');
            const data = await response.json();
            this.updateHistoryDisplay(data);
        } catch (error) {
            console.error('Error loading history:', error);
        }
    }
    
    updateHistoryDisplay(data) {
        const tbody = document.getElementById('execution-history');
        
        if (!data || data.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center" style="padding: 40px; color: var(--text-secondary);">
                        No executions yet
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = data.slice(0, 50).map(exec => {
            const timestamp = new Date(exec.timestamp);
            const timeStr = timestamp.toLocaleTimeString();
            const dateStr = timestamp.toLocaleDateString();
            
            return `
                <tr>
                    <td>${dateStr} ${timeStr}</td>
                    <td><strong>${exec.ticker || 'N/A'}</strong></td>
                    <td>
                        <span class="badge badge-${this.getSignalBadgeClass(exec.signal)}">
                            ${exec.signal || 'N/A'}
                        </span>
                    </td>
                    <td>${((exec.probability || 0) * 100).toFixed(1)}%</td>
                    <td>${exec.quantity || 0}</td>
                    <td>Rs ${(exec.price || 0).toFixed(2)}</td>
                    <td>
                        <span class="badge ${exec.success ? 'badge-success' : 'badge-danger'}">
                            ${exec.success ? 'Success' : 'Failed'}
                        </span>
                    </td>
                </tr>
            `;
        }).join('');
    }
    
    async loadSignals() {
        try {
            // For now, we'll show recent signals from history
            // In the future, this could be a dedicated endpoint
            const response = await fetch('/api/auto-trading/history');
            const data = await response.json();
            this.updateSignalsDisplay(data);
        } catch (error) {
            console.error('Error loading signals:', error);
        }
    }
    
    updateSignalsDisplay(data) {
        const container = document.getElementById('recent-signals');
        
        if (!data || data.length === 0) {
            container.innerHTML = `
                <div class="text-center" style="padding: 40px; color: var(--text-secondary);">
                    <i class="fas fa-info-circle" style="font-size: 2rem; margin-bottom: 10px;"></i>
                    <p>No signals generated yet</p>
                </div>
            `;
            return;
        }
        
        // Get unique signals (latest per ticker)
        const signalMap = new Map();
        data.forEach(exec => {
            const ticker = exec.ticker;
            if (!signalMap.has(ticker) || new Date(exec.timestamp) > new Date(signalMap.get(ticker).timestamp)) {
                signalMap.set(ticker, exec);
            }
        });
        
        const recentSignals = Array.from(signalMap.values())
            .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
            .slice(0, 10);
        
        container.innerHTML = recentSignals.map(exec => {
            const signal = exec.signal || 'HOLD';
            const signalClass = this.getSignalClass(signal);
            
            return `
                <div class="signal-item ${signalClass}">
                    <div class="signal-header">
                        <span class="signal-ticker">${exec.ticker || 'N/A'}</span>
                        <span class="signal-type">${signal}</span>
                    </div>
                    <div class="signal-details">
                        <div>
                            <strong>Probability:</strong> ${((exec.probability || 0) * 100).toFixed(1)}%
                        </div>
                        <div>
                            <strong>Price:</strong> Rs ${(exec.price || 0).toFixed(2)}
                        </div>
                        <div>
                            <strong>Time:</strong> ${new Date(exec.timestamp).toLocaleTimeString()}
                        </div>
                        <div>
                            <strong>Status:</strong> 
                            <span class="badge ${exec.success ? 'badge-success' : 'badge-danger'}">
                                ${exec.success ? 'Executed' : 'Rejected'}
                            </span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }
    
    async loadPositions() {
        try {
            // This would need a positions endpoint
            // For now, we'll show a placeholder
            const container = document.getElementById('open-positions-list');
            container.innerHTML = `
                <div class="text-center" style="padding: 40px; color: var(--text-secondary);">
                    <i class="fas fa-info-circle" style="font-size: 2rem; margin-bottom: 10px;"></i>
                    <p>Position tracking coming soon</p>
                </div>
            `;
        } catch (error) {
            console.error('Error loading positions:', error);
        }
    }
    
    initPerformanceChart() {
        const ctx = document.getElementById('performance-chart');
        if (!ctx) return;
        
        this.performanceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: this.performanceData.labels,
                datasets: [{
                    label: 'Daily P&L',
                    data: this.performanceData.pnl,
                    borderColor: 'rgb(40, 167, 69)',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
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
                        labels: {
                            color: '#e0e0e0'
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: '#888' },
                        grid: { color: '#2a2f4a' }
                    },
                    y: {
                        ticks: { color: '#888' },
                        grid: { color: '#2a2f4a' }
                    }
                }
            }
        });
    }
    
    getSignalClass(signal) {
        if (signal.includes('BUY')) return 'signal-buy';
        if (signal.includes('SELL')) return 'signal-sell';
        return 'signal-hold';
    }
    
    getSignalBadgeClass(signal) {
        if (signal.includes('BUY')) return 'success';
        if (signal.includes('SELL')) return 'danger';
        return 'warning';
    }
    
    showAlert(message, type = 'info') {
        const alertContainer = document.getElementById('system-alert');
        const alertClass = `alert alert-${type}`;
        
        alertContainer.innerHTML = `
            <div class="${alertClass}">
                <i class="fas fa-${type === 'danger' ? 'exclamation-circle' : type === 'warning' ? 'exclamation-triangle' : 'info-circle'}"></i>
                ${message}
            </div>
        `;
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            alertContainer.innerHTML = '';
        }, 5000);
    }
    
    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab').forEach(tab => {
            tab.classList.remove('active');
        });
        event.target.classList.add('active');
        
        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`tab-${tabName}`).classList.add('active');
        
        // Load data for active tab
        if (tabName === 'performance') {
            this.updatePerformanceChart();
        }
    }
    
    updatePerformanceChart() {
        // This would fetch historical performance data
        // For now, we'll use mock data
        if (this.performanceChart) {
            // Update chart with real data when available
        }
    }
    
    pauseUpdates() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        if (this.statusUpdateInterval) {
            clearInterval(this.statusUpdateInterval);
        }
    }
    
    resumeUpdates() {
        this.init();
    }
}

// Global functions for button clicks
let dashboard;

document.addEventListener('DOMContentLoaded', function() {
    dashboard = new AutoTradingDashboard();
    const endInput = document.getElementById('backtest-end');
    const startInput = document.getElementById('backtest-start');
    if (endInput && !endInput.value) { const d = new Date(); endInput.value = d.toISOString().slice(0, 10); }
    if (startInput && !startInput.value) { const d = new Date(); d.setFullYear(d.getFullYear() - 1); startInput.value = d.toISOString().slice(0, 10); }
    const btnRun = document.getElementById('btn-run-backtest');
    if (btnRun) btnRun.addEventListener('click', runBacktest);
    const btnApplyTh = document.getElementById('btn-apply-threshold');
    if (btnApplyTh) btnApplyTh.addEventListener('click', applyBacktestThreshold);
    const btnApplySt = document.getElementById('btn-apply-strategy');
    if (btnApplySt) btnApplySt.addEventListener('click', applyBacktestStrategy);
    const btnRetrain = document.getElementById('btn-retrain-elite');
    if (btnRetrain) btnRetrain.addEventListener('click', retrainEliteBaseline);
});

async function startAutoTrading() {
    try {
        const response = await fetch('/api/auto-trading/start', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            dashboard.showAlert(data.message || 'Auto trading started successfully', 'info');
            dashboard.loadStatus();
        } else {
            dashboard.showAlert(data.message || 'Failed to start auto trading', 'danger');
        }
    } catch (error) {
        dashboard.showAlert('Error starting auto trading: ' + error.message, 'danger');
    }
}

async function stopAutoTrading() {
    if (!confirm('Are you sure you want to stop auto trading? This will halt all automated trading activities.')) {
        return;
    }
    
    try {
        const response = await fetch('/api/auto-trading/stop', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            dashboard.showAlert(data.message || 'Auto trading stopped successfully', 'info');
            dashboard.loadStatus();
        } else {
            dashboard.showAlert(data.message || 'Failed to stop auto trading', 'danger');
        }
    } catch (error) {
        dashboard.showAlert('Error stopping auto trading: ' + error.message, 'danger');
    }
}

async function pauseAutoTrading() {
    try {
        const response = await fetch('/api/auto-trading/pause', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            dashboard.showAlert(data.message || 'Auto trading paused (circuit breaker activated)', 'warning');
            dashboard.loadStatus();
        } else {
            dashboard.showAlert(data.message || 'Failed to pause auto trading', 'danger');
        }
    } catch (error) {
        dashboard.showAlert('Error pausing auto trading: ' + error.message, 'danger');
    }
}

async function resetCircuitBreaker() {
    if (!confirm('Reset circuit breaker? This will resume trading even if loss limits were hit.')) {
        return;
    }
    
    try {
        const response = await fetch('/api/auto-trading/reset-circuit-breaker', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            dashboard.showAlert(data.message || 'Circuit breaker reset successfully', 'info');
            dashboard.loadStatus();
        } else {
            dashboard.showAlert(data.message || 'Failed to reset circuit breaker', 'danger');
        }
    } catch (error) {
        dashboard.showAlert('Error resetting circuit breaker: ' + error.message, 'danger');
    }
}

async function applySignalSource() {
    const el = document.getElementById('signal-source-select');
    if (!el) return;
    try {
        const response = await fetch('/api/auto-trading/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ signal_source: el.value })
        });
        const data = await response.json();
        if (data.success) {
            dashboard.showAlert(data.message || 'Signal source updated', 'info');
            dashboard.loadStatus();
        } else {
            dashboard.showAlert(data.error || 'Failed to update', 'danger');
        }
    } catch (e) {
        dashboard.showAlert('Error: ' + e.message, 'danger');
    }
}

async function applyActiveQuantStrategy() {
    const el = document.getElementById('active-quant-strategy-select');
    if (!el) return;
    try {
        const response = await fetch('/api/auto-trading/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ active_quant_strategy: el.value })
        });
        const data = await response.json();
        if (data.success) {
            dashboard.showAlert(data.message || 'Active quant strategy updated', 'info');
            dashboard.loadStatus();
        } else {
            dashboard.showAlert(data.error || 'Failed to update', 'danger');
        }
    } catch (e) {
        dashboard.showAlert('Error: ' + e.message, 'danger');
    }
}

async function runScanNow() {
    const btn = document.getElementById('btn-scan-now');
    if (btn) btn.disabled = true;
    try {
        const response = await fetch('/api/auto-trading/scan', { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            const r = data.result || {};
            const msg = `Scan complete: ${r.stocks_scanned || 0} scanned, ${r.signals_generated || 0} signals, ${r.signals_executed || 0} executed, ${r.signals_rejected || 0} rejected`;
            dashboard.showAlert(msg, 'info');
            dashboard.loadStatus();
            dashboard.loadHistory();
        } else {
            dashboard.showAlert(data.error || 'Scan failed', 'danger');
        }
    } catch (error) {
        dashboard.showAlert('Error running scan: ' + error.message, 'danger');
    } finally {
        if (btn) btn.disabled = false;
    }
}

function switchTab(tabName) {
    if (dashboard) {
        dashboard.switchTab(tabName);
    }
}

let lastBacktestResult = null;

async function runBacktest() {
    const btn = document.getElementById('btn-run-backtest');
    const resultsDiv = document.getElementById('backtest-results');
    const loadingDiv = document.getElementById('backtest-loading');
    const errorDiv = document.getElementById('backtest-error');
    if (btn) btn.disabled = true;
    if (loadingDiv) loadingDiv.classList.remove('d-none');
    if (resultsDiv) resultsDiv.classList.add('d-none');
    if (errorDiv) { errorDiv.classList.add('d-none'); errorDiv.textContent = ''; }
    try {
        const ticker = (document.getElementById('backtest-ticker') && document.getElementById('backtest-ticker').value.trim()) || null;
        let start = document.getElementById('backtest-start') && document.getElementById('backtest-start').value;
        let end = document.getElementById('backtest-end') && document.getElementById('backtest-end').value;
        if (!end) { const d = new Date(); end = d.toISOString().slice(0, 10); }
        if (!start) { const d = new Date(); d.setFullYear(d.getFullYear() - 1); start = d.toISOString().slice(0, 10); }
        const response = await fetch('/api/auto-trading/backtest-run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker: ticker || undefined, start_date: start, end_date: end })
        });
        const data = await response.json();
        lastBacktestResult = data;
        if (data.sweep && data.ranking) {
            const sweep = data.sweep;
            const rank = data.ranking;
            if (document.getElementById('backtest-best-threshold')) {
                document.getElementById('backtest-best-threshold').textContent = sweep.error ? '—' : (sweep.best_threshold != null ? sweep.best_threshold : '—');
            }
            if (document.getElementById('backtest-best-sharpe')) {
                document.getElementById('backtest-best-sharpe').textContent = sweep.error ? '—' : (sweep.best_sharpe != null ? sweep.best_sharpe : '—');
            }
            if (document.getElementById('backtest-best-strategy')) {
                document.getElementById('backtest-best-strategy').textContent = rank.error ? '—' : (rank.best_strategy || '—');
            }
            let detail = '';
            if (sweep.results && sweep.results.length) {
                detail += 'Thresholds: ' + sweep.results.map(r => r.threshold + '→Sharpe ' + r.sharpe).join(', ') + '. ';
            }
            if (rank.rankings && rank.rankings.length) {
                detail += 'Strategies: ' + rank.rankings.map(r => r.strategy + ' (Sharpe ' + r.sharpe_ratio + ')').join(', ');
            }
            const detailEl = document.getElementById('backtest-detail');
            if (detailEl) detailEl.textContent = detail;
            if (resultsDiv) resultsDiv.classList.remove('d-none');
        }
        if ((data.sweep && data.sweep.error) || (data.ranking && data.ranking.error)) {
            const err = (data.sweep && data.sweep.error) || (data.ranking && data.ranking.error) || 'Backtest failed';
            if (errorDiv) { errorDiv.textContent = err; errorDiv.classList.remove('d-none'); }
        }
    } catch (e) {
        if (errorDiv) { errorDiv.textContent = e.message; errorDiv.classList.remove('d-none'); }
    } finally {
        if (btn) btn.disabled = false;
        if (loadingDiv) loadingDiv.classList.add('d-none');
    }
}

async function applyBacktestThreshold() {
    if (!lastBacktestResult || !lastBacktestResult.sweep || lastBacktestResult.sweep.error || lastBacktestResult.sweep.best_threshold == null) {
        dashboard.showAlert('Run backtest first and ensure threshold sweep succeeded.', 'warning');
        return;
    }
    try {
        const response = await fetch('/api/auto-trading/backtest-apply', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ apply_threshold: true, best_threshold: lastBacktestResult.sweep.best_threshold })
        });
        const data = await response.json();
        if (data.success) {
            dashboard.showAlert(data.message || 'Threshold applied', 'info');
            dashboard.loadStatus();
        } else {
            dashboard.showAlert(data.error || 'Apply failed', 'danger');
        }
    } catch (e) {
        dashboard.showAlert('Error: ' + e.message, 'danger');
    }
}

async function applyBacktestStrategy() {
    if (!lastBacktestResult || !lastBacktestResult.ranking || lastBacktestResult.ranking.error || !lastBacktestResult.ranking.best_strategy) {
        dashboard.showAlert('Run backtest first and ensure strategy ranking succeeded.', 'warning');
        return;
    }
    try {
        const response = await fetch('/api/auto-trading/backtest-apply', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ apply_strategy: true, best_strategy: lastBacktestResult.ranking.best_strategy })
        });
        const data = await response.json();
        if (data.success) {
            dashboard.showAlert(data.message || 'Strategy applied', 'info');
            dashboard.loadStatus();
        } else {
            dashboard.showAlert(data.error || 'Apply failed', 'danger');
        }
    } catch (e) {
        dashboard.showAlert('Error: ' + e.message, 'danger');
    }
}

async function retrainEliteBaseline() {
    const btn = document.getElementById('btn-retrain-elite');
    const statusEl = document.getElementById('retrain-status');
    if (btn) btn.disabled = true;
    if (statusEl) { statusEl.textContent = 'Retraining...'; statusEl.className = 'ms-2 small text-info'; }
    try {
        const ticker = (document.getElementById('backtest-ticker') && document.getElementById('backtest-ticker').value.trim()) || 'RELIANCE.NS';
        const response = await fetch('/api/auto-trading/retrain-elite', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker: ticker, days_back: 504 })
        });
        const data = await response.json();
        if (data.success) {
            if (statusEl) { statusEl.textContent = 'Done'; statusEl.className = 'ms-2 small text-success'; }
            dashboard.showAlert(data.message || 'ELITE baseline retrained', 'info');
        } else {
            if (statusEl) { statusEl.textContent = data.error || 'Failed'; statusEl.className = 'ms-2 small text-danger'; }
            dashboard.showAlert(data.error || data.message || 'Retrain failed', 'danger');
        }
    } catch (e) {
        if (statusEl) { statusEl.textContent = 'Error'; statusEl.className = 'ms-2 small text-danger'; }
        dashboard.showAlert('Error: ' + e.message, 'danger');
    } finally {
        if (btn) btn.disabled = false;
    }
}
