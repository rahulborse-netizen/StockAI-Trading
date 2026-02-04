/**
 * Trade Planner Frontend
 * Handles trade plan generation, display, and execution
 */

let tradePlans = [];
let currentFilters = {
    status: null,
    trading_type: null,
    symbol: null
};

/**
 * Load all trade plans
 */
async function loadTradePlans() {
    try {
        const params = new URLSearchParams();
        if (currentFilters.status) params.append('status', currentFilters.status);
        if (currentFilters.trading_type) params.append('trading_type', currentFilters.trading_type);
        if (currentFilters.symbol) params.append('symbol', currentFilters.symbol);
        
        const url = `/api/trade-plans${params.toString() ? '?' + params.toString() : ''}`;
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        tradePlans = await response.json();
        renderTradePlans();
        
    } catch (error) {
        console.error('[TradePlanner] Error loading trade plans:', error);
        showNotification('Error loading trade plans: ' + error.message, 'error');
    }
}

/**
 * Generate a new trade plan
 */
async function generateTradePlan(ticker, tradingType = 'swing') {
    try {
        if (!ticker) {
            showNotification('Please provide a ticker symbol', 'warning');
            return;
        }
        
        showNotification(`Generating trade plan for ${ticker}...`, 'info');
        
        const response = await fetch('/api/trade-plan/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                ticker: ticker,
                trading_type: tradingType
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.plan) {
            showNotification(`Trade plan generated for ${ticker}`, 'success');
            loadTradePlans(); // Refresh list
            showTradePlanModal(data.plan, data.validation);
        } else {
            throw new Error('No plan returned from server');
        }
        
    } catch (error) {
        console.error('[TradePlanner] Error generating trade plan:', error);
        showNotification('Error generating trade plan: ' + error.message, 'error');
    }
}

/**
 * Approve a trade plan
 */
async function approveTradePlan(planId) {
    try {
        const response = await fetch(`/api/trade-plan/${planId}/approve`, {
            method: 'PUT'
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        
        showNotification('Trade plan approved', 'success');
        loadTradePlans(); // Refresh list
        
    } catch (error) {
        console.error('[TradePlanner] Error approving trade plan:', error);
        showNotification('Error approving trade plan: ' + error.message, 'error');
    }
}

/**
 * Execute a trade plan (pre-fills order form)
 */
async function executeTradePlan(planId) {
    try {
        const response = await fetch(`/api/trade-plan/${planId}/execute`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.order_details) {
            // Pre-fill order form
            if (typeof showPlaceOrderModal === 'function') {
                showPlaceOrderModal();
                
                // Wait for modal to open, then fill fields
                setTimeout(() => {
                    const tickerInput = document.getElementById('order-ticker');
                    const quantityInput = document.getElementById('order-quantity');
                    const orderTypeSelect = document.getElementById('order-type');
                    const priceInput = document.getElementById('order-price');
                    const transactionTypeSelect = document.getElementById('order-transaction-type');
                    const productSelect = document.getElementById('order-product');
                    
                    if (tickerInput) tickerInput.value = data.order_details.ticker;
                    if (quantityInput) quantityInput.value = data.order_details.quantity;
                    if (orderTypeSelect) orderTypeSelect.value = data.order_details.order_type;
                    if (priceInput && data.order_details.price) priceInput.value = data.order_details.price;
                    if (transactionTypeSelect) transactionTypeSelect.value = data.order_details.transaction_type;
                    if (productSelect) productSelect.value = data.order_details.product;
                    
                    showNotification('Order form pre-filled from trade plan', 'info');
                }, 300);
            } else {
                // Fallback: show order details
                alert(`Order Details:\nTicker: ${data.order_details.ticker}\nQuantity: ${data.order_details.quantity}\nType: ${data.order_details.order_type}\nTransaction: ${data.order_details.transaction_type}`);
            }
        }
        
    } catch (error) {
        console.error('[TradePlanner] Error executing trade plan:', error);
        showNotification('Error executing trade plan: ' + error.message, 'error');
    }
}

/**
 * Delete a trade plan
 */
async function deleteTradePlan(planId) {
    if (!confirm('Are you sure you want to delete this trade plan?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/trade-plan/${planId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        
        showNotification('Trade plan deleted', 'success');
        loadTradePlans(); // Refresh list
        
    } catch (error) {
        console.error('[TradePlanner] Error deleting trade plan:', error);
        showNotification('Error deleting trade plan: ' + error.message, 'error');
    }
}

/**
 * Render trade plans list
 */
function renderTradePlans() {
    const container = document.getElementById('trade-plans-container');
    if (!container) return;
    
    if (tradePlans.length === 0) {
        container.innerHTML = '<div class="text-center text-muted p-4">No trade plans found. Generate one from a signal!</div>';
        return;
    }
    
    container.innerHTML = tradePlans.map(plan => renderTradePlanCard(plan)).join('');
}

/**
 * Render a single trade plan card
 */
function renderTradePlanCard(plan) {
    const statusClass = {
        'draft': 'bg-secondary',
        'approved': 'bg-success',
        'executed': 'bg-info',
        'cancelled': 'bg-danger'
    }[plan.status] || 'bg-secondary';
    
    const signalClass = {
        'BUY': 'text-success',
        'SELL': 'text-danger',
        'HOLD': 'text-warning'
    }[plan.signal] || '';
    
    const tradingTypeBadge = {
        'intraday': 'bg-primary',
        'swing': 'bg-info',
        'position': 'bg-warning'
    }[plan.trading_type] || 'bg-secondary';
    
    return `
        <div class="trade-plan-card card mb-3">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <div>
                        <h5 class="card-title mb-1">
                            <span class="${signalClass}"><strong>${plan.symbol}</strong></span>
                            <span class="badge ${statusClass} ms-2">${plan.status.toUpperCase()}</span>
                            <span class="badge ${tradingTypeBadge} ms-1">${plan.trading_type.toUpperCase()}</span>
                        </h5>
                        <p class="text-muted mb-0">
                            <small>Signal: <strong class="${signalClass}">${plan.signal}</strong> | Confidence: ${(plan.confidence * 100).toFixed(1)}%</small>
                        </p>
                    </div>
                    <div>
                        <button class="btn btn-sm btn-outline-primary" onclick="showTradePlanModal(${JSON.stringify(plan).replace(/"/g, '&quot;')})" title="View Details">
                            <i class="fas fa-eye"></i>
                        </button>
                        ${plan.status === 'draft' ? `
                            <button class="btn btn-sm btn-success" onclick="approveTradePlan('${plan.plan_id}')" title="Approve">
                                <i class="fas fa-check"></i>
                            </button>
                        ` : ''}
                        ${plan.status === 'approved' || plan.status === 'draft' ? `
                            <button class="btn btn-sm btn-primary" onclick="executeTradePlan('${plan.plan_id}')" title="Execute">
                                <i class="fas fa-play"></i>
                            </button>
                        ` : ''}
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteTradePlan('${plan.plan_id}')" title="Delete">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                
                <div class="row mt-3">
                    <div class="col-md-6">
                        <div class="trade-plan-details">
                            <div class="detail-item">
                                <span class="label">Entry:</span>
                                <span class="value">₹${plan.entry_price.toFixed(2)}</span>
                            </div>
                            <div class="detail-item">
                                <span class="label">Stop Loss:</span>
                                <span class="value text-danger">₹${plan.stop_loss.toFixed(2)}</span>
                            </div>
                            <div class="detail-item">
                                <span class="label">Target 1:</span>
                                <span class="value text-success">₹${plan.target_1.toFixed(2)}</span>
                            </div>
                            <div class="detail-item">
                                <span class="label">Target 2:</span>
                                <span class="value text-success">₹${plan.target_2.toFixed(2)}</span>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="trade-plan-details">
                            <div class="detail-item">
                                <span class="label">Quantity:</span>
                                <span class="value">${plan.quantity}</span>
                            </div>
                            <div class="detail-item">
                                <span class="label">Capital Required:</span>
                                <span class="value">₹${plan.capital_required.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                            </div>
                            <div class="detail-item">
                                <span class="label">Risk Amount:</span>
                                <span class="value text-danger">₹${plan.risk_amount.toFixed(2)} (${plan.risk_per_trade_pct.toFixed(2)}%)</span>
                            </div>
                            <div class="detail-item">
                                <span class="label">Risk:Reward:</span>
                                <span class="value">${plan.risk_reward_ratio.toFixed(2)}:1</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="mt-2">
                    <small class="text-muted">Created: ${new Date(plan.timestamp).toLocaleString()}</small>
                </div>
            </div>
        </div>
    `;
}

/**
 * Generate trade plan from input fields
 */
function generateTradePlanFromInput() {
    const tickerInput = document.getElementById('generate-plan-ticker');
    const typeSelect = document.getElementById('generate-plan-type');
    
    if (!tickerInput || !tickerInput.value.trim()) {
        showNotification('Please enter a ticker symbol', 'warning');
        return;
    }
    
    const ticker = tickerInput.value.trim();
    const tradingType = typeSelect ? typeSelect.value : 'swing';
    
    generateTradePlan(ticker, tradingType);
    
    // Clear input
    if (tickerInput) tickerInput.value = '';
}

/**
 * Show trade plan detail modal
 */
function showTradePlanModal(plan, validation = null) {
    // Create or update modal
    let modal = document.getElementById('tradePlanModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'tradePlanModal';
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg modal-dialog-centered">
                <div class="modal-content-modern">
                    <div class="modal-header-modern">
                        <div class="modal-title-section">
                            <i class="fas fa-chart-line modal-icon"></i>
                            <h5 class="modal-title">Trade Plan Details</h5>
                        </div>
                        <button type="button" class="btn-close-modern" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body-modern" id="tradePlanModalBody">
                        <!-- Content will be inserted here -->
                    </div>
                    <div class="modal-footer-modern">
                        <button type="button" class="btn-modern btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    const modalBody = document.getElementById('tradePlanModalBody');
    if (!modalBody) return;
    
    const signalClass = {
        'BUY': 'text-success',
        'SELL': 'text-danger',
        'HOLD': 'text-warning'
    }[plan.signal] || '';
    
    let validationHtml = '';
    if (validation) {
        const validationClass = validation.is_valid ? 'alert-success' : 'alert-danger';
        validationHtml = `
            <div class="alert ${validationClass}">
                <strong>Validation:</strong> ${validation.is_valid ? 'Valid' : 'Invalid'}
                ${validation.errors.length > 0 ? `<br><strong>Errors:</strong> ${validation.errors.join(', ')}` : ''}
                ${validation.warnings.length > 0 ? `<br><strong>Warnings:</strong> ${validation.warnings.join(', ')}` : ''}
            </div>
        `;
    }
    
    modalBody.innerHTML = `
        <div class="trade-plan-detail">
            <h4 class="${signalClass}">${plan.symbol} - ${plan.signal}</h4>
            <p class="text-muted">${plan.ticker} | ${plan.trading_type.toUpperCase()} | Confidence: ${(plan.confidence * 100).toFixed(1)}%</p>
            
            ${validationHtml}
            
            <div class="row mt-3">
                <div class="col-md-6">
                    <h6>Entry/Exit Levels</h6>
                    <table class="table table-sm">
                        <tr><td>Current Price:</td><td><strong>₹${plan.current_price.toFixed(2)}</strong></td></tr>
                        <tr><td>Entry Price:</td><td><strong>₹${plan.entry_price.toFixed(2)}</strong></td></tr>
                        <tr><td>Stop Loss:</td><td class="text-danger"><strong>₹${plan.stop_loss.toFixed(2)}</strong></td></tr>
                        <tr><td>Target 1:</td><td class="text-success"><strong>₹${plan.target_1.toFixed(2)}</strong></td></tr>
                        <tr><td>Target 2:</td><td class="text-success"><strong>₹${plan.target_2.toFixed(2)}</strong></td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6>Position & Risk</h6>
                    <table class="table table-sm">
                        <tr><td>Quantity:</td><td><strong>${plan.quantity}</strong></td></tr>
                        <tr><td>Capital Required:</td><td><strong>₹${plan.capital_required.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</strong></td></tr>
                        <tr><td>Risk Amount:</td><td class="text-danger"><strong>₹${plan.risk_amount.toFixed(2)}</strong></td></tr>
                        <tr><td>Risk %:</td><td><strong>${plan.risk_per_trade_pct.toFixed(2)}%</strong></td></tr>
                        <tr><td>Risk:Reward:</td><td><strong>${plan.risk_reward_ratio.toFixed(2)}:1</strong></td></tr>
                        <tr><td>Max Loss:</td><td class="text-danger"><strong>₹${plan.max_loss.toFixed(2)}</strong></td></tr>
                    </table>
                </div>
            </div>
            
            <div class="row mt-3">
                <div class="col-md-6">
                    <h6>Order Details</h6>
                    <table class="table table-sm">
                        <tr><td>Order Type:</td><td><strong>${plan.order_type}</strong></td></tr>
                        <tr><td>Product:</td><td><strong>${plan.product === 'I' ? 'Intraday' : 'Delivery'}</strong></td></tr>
                        <tr><td>Validity:</td><td><strong>${plan.validity}</strong></td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6>Additional Info</h6>
                    <table class="table table-sm">
                        ${plan.recent_high ? `<tr><td>Recent High:</td><td>₹${plan.recent_high.toFixed(2)}</td></tr>` : ''}
                        ${plan.recent_low ? `<tr><td>Recent Low:</td><td>₹${plan.recent_low.toFixed(2)}</td></tr>` : ''}
                        ${plan.volatility ? `<tr><td>Volatility:</td><td>${(plan.volatility * 100).toFixed(2)}%</td></tr>` : ''}
                        <tr><td>Created:</td><td>${new Date(plan.timestamp).toLocaleString()}</td></tr>
                    </table>
                </div>
            </div>
            
            <div class="mt-3">
                ${plan.status === 'draft' ? `
                    <button class="btn-modern btn-success me-2" onclick="approveTradePlan('${plan.plan_id}'); bootstrap.Modal.getInstance(document.getElementById('tradePlanModal')).hide();">
                        <i class="fas fa-check"></i> Approve
                    </button>
                ` : ''}
                ${plan.status === 'approved' || plan.status === 'draft' ? `
                    <button class="btn-modern btn-primary me-2" onclick="executeTradePlan('${plan.plan_id}'); bootstrap.Modal.getInstance(document.getElementById('tradePlanModal')).hide();">
                        <i class="fas fa-play"></i> Execute
                    </button>
                ` : ''}
            </div>
        </div>
    `;
    
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

/**
 * Apply filters to trade plans
 */
function filterTradePlans() {
    const statusFilter = document.getElementById('trade-plan-status-filter');
    const typeFilter = document.getElementById('trade-plan-type-filter');
    const symbolFilter = document.getElementById('trade-plan-symbol-filter');
    
    currentFilters.status = statusFilter?.value || null;
    currentFilters.trading_type = typeFilter?.value || null;
    currentFilters.symbol = symbolFilter?.value || null;
    
    loadTradePlans();
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Load trade plans if we're on the trade plans tab
    const tradePlansTab = document.getElementById('trade-plans-tab');
    if (tradePlansTab) {
        // Load when tab is shown
        tradePlansTab.addEventListener('shown.bs.tab', function() {
            loadTradePlans();
        });
    }
});
