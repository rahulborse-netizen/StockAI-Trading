/**
 * Order Confirmation System
 * Phase 2.2: Enhanced order confirmation with risk warnings
 */

class OrderConfirmation {
    constructor() {
        this.confirmationCallbacks = new Map();
    }
    
    /**
     * Show order confirmation dialog
     * @param {Object} orderDetails - Order details
     * @param {Function} onConfirm - Callback when confirmed
     * @param {Function} onCancel - Callback when cancelled
     */
    showConfirmation(orderDetails, onConfirm, onCancel = null) {
        const {
            ticker,
            transaction_type,
            quantity,
            order_type,
            price,
            estimated_cost,
            estimated_charges,
            risk_warning
        } = orderDetails;
        
        // Calculate estimated cost if not provided
        const cost = estimated_cost || (price ? price * quantity : 0);
        const charges = estimated_charges || (cost * 0.001); // 0.1% brokerage estimate
        const total = cost + charges;
        
        // Determine risk level
        const riskLevel = this.calculateRiskLevel(orderDetails);
        
        // Create confirmation modal HTML
        const modalHtml = `
            <div class="modal fade" id="orderConfirmationModal" tabindex="-1">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content-modern">
                        <div class="modal-header-modern">
                            <div class="modal-title-section">
                                <i class="fas fa-check-circle modal-icon"></i>
                                <h5>Confirm Order</h5>
                            </div>
                            <button type="button" class="btn-close-modern" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body-modern">
                            <div class="order-summary">
                                <h6>Order Summary</h6>
                                <div class="summary-item">
                                    <span>Symbol:</span>
                                    <strong>${ticker}</strong>
                                </div>
                                <div class="summary-item">
                                    <span>Type:</span>
                                    <strong>${transaction_type}</strong>
                                </div>
                                <div class="summary-item">
                                    <span>Quantity:</span>
                                    <strong>${quantity}</strong>
                                </div>
                                <div class="summary-item">
                                    <span>Order Type:</span>
                                    <strong>${order_type}</strong>
                                </div>
                                ${price ? `<div class="summary-item">
                                    <span>Price:</span>
                                    <strong>₹${parseFloat(price).toFixed(2)}</strong>
                                </div>` : ''}
                                <div class="summary-item">
                                    <span>Estimated Cost:</span>
                                    <strong>₹${cost.toFixed(2)}</strong>
                                </div>
                                <div class="summary-item">
                                    <span>Estimated Charges:</span>
                                    <strong>₹${charges.toFixed(2)}</strong>
                                </div>
                                <div class="summary-item total">
                                    <span>Total:</span>
                                    <strong>₹${total.toFixed(2)}</strong>
                                </div>
                            </div>
                            
                            ${riskLevel === 'high' ? `
                                <div class="risk-warning high-risk">
                                    <i class="fas fa-exclamation-triangle"></i>
                                    <div>
                                        <strong>High Risk Warning</strong>
                                        <p>This order involves significant capital. Please review carefully.</p>
                                    </div>
                                </div>
                            ` : ''}
                            
                            ${risk_warning ? `
                                <div class="risk-warning">
                                    <i class="fas fa-info-circle"></i>
                                    <div>
                                        <strong>Risk Notice</strong>
                                        <p>${risk_warning}</p>
                                    </div>
                                </div>
                            ` : ''}
                            
                            ${order_type === 'MARKET' ? `
                                <div class="market-order-warning">
                                    <i class="fas fa-bolt"></i>
                                    <p><strong>Market Order:</strong> This order will execute immediately at the current market price.</p>
                                </div>
                            ` : ''}
                            
                            <div class="confirmation-checkbox">
                                <label>
                                    <input type="checkbox" id="confirm-order-checkbox">
                                    I understand the risks and confirm this order
                                </label>
                            </div>
                        </div>
                        <div class="modal-footer-modern">
                            <button type="button" class="btn-modern btn-secondary" data-bs-dismiss="modal" onclick="orderConfirmation.cancel()">Cancel</button>
                            <button type="button" class="btn-modern btn-success" id="confirm-order-btn" onclick="orderConfirmation.confirm()" disabled>
                                <i class="fas fa-check"></i> Confirm Order
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal if any
        const existingModal = document.getElementById('orderConfirmationModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Store callbacks
        this.confirmationCallbacks.set('confirm', onConfirm);
        if (onCancel) {
            this.confirmationCallbacks.set('cancel', onCancel);
        }
        
        // Enable confirm button when checkbox is checked
        const checkbox = document.getElementById('confirm-order-checkbox');
        const confirmBtn = document.getElementById('confirm-order-btn');
        
        checkbox.addEventListener('change', function() {
            confirmBtn.disabled = !this.checked;
        });
        
        // Show modal
        const modalElement = document.getElementById('orderConfirmationModal');
        const modal = new bootstrap.Modal(modalElement, {
            backdrop: 'static',
            keyboard: false
        });
        modal.show();
        
        // Clean up on close
        modalElement.addEventListener('hidden.bs.modal', function() {
            this.remove();
        });
    }
    
    /**
     * Calculate risk level for order
     * @param {Object} orderDetails - Order details
     * @returns {string} Risk level: 'low', 'medium', 'high'
     */
    calculateRiskLevel(orderDetails) {
        const { quantity, price, order_type, transaction_type } = orderDetails;
        const orderValue = (price || 0) * quantity;
        
        // High risk: Large order value or market orders
        if (orderValue > 100000 || order_type === 'MARKET') {
            return 'high';
        }
        
        // Medium risk: Moderate order value
        if (orderValue > 50000) {
            return 'medium';
        }
        
        return 'low';
    }
    
    /**
     * Confirm order
     */
    confirm() {
        const callback = this.confirmationCallbacks.get('confirm');
        if (callback) {
            callback();
        }
        
        // Close modal
        const modalElement = document.getElementById('orderConfirmationModal');
        const modal = bootstrap.Modal.getInstance(modalElement);
        if (modal) {
            modal.hide();
        }
        
        this.confirmationCallbacks.clear();
    }
    
    /**
     * Cancel order
     */
    cancel() {
        const callback = this.confirmationCallbacks.get('cancel');
        if (callback) {
            callback();
        }
        
        // Close modal
        const modalElement = document.getElementById('orderConfirmationModal');
        const modal = bootstrap.Modal.getInstance(modalElement);
        if (modal) {
            modal.hide();
        }
        
        this.confirmationCallbacks.clear();
    }
    
    /**
     * Show two-step confirmation for market orders
     * @param {Object} orderDetails - Order details
     * @param {Function} onConfirm - Callback when confirmed
     */
    showTwoStepConfirmation(orderDetails, onConfirm) {
        // First step: Show warning
        const firstStep = () => {
            if (confirm('⚠️ MARKET ORDER WARNING\n\nMarket orders execute immediately at current market price.\n\nDo you want to proceed?')) {
                // Second step: Show full confirmation
                this.showConfirmation(orderDetails, onConfirm);
            }
        };
        
        firstStep();
    }
}

// Global instance
const orderConfirmation = new OrderConfirmation();

// Add CSS for confirmation modal
const confirmationStyles = `
    <style>
        .order-summary {
            background: var(--card-bg);
            border-radius: 0.5rem;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        
        .order-summary h6 {
            margin-bottom: 0.75rem;
            color: var(--text-primary);
        }
        
        .summary-item {
            display: flex;
            justify-content: space-between;
            padding: 0.5rem 0;
            border-bottom: 1px solid var(--border-color);
        }
        
        .summary-item:last-child {
            border-bottom: none;
        }
        
        .summary-item.total {
            margin-top: 0.5rem;
            padding-top: 0.75rem;
            border-top: 2px solid var(--border-color);
            font-size: 1.1rem;
        }
        
        .risk-warning {
            display: flex;
            gap: 0.75rem;
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            background: rgba(234, 179, 8, 0.1);
            border-left: 4px solid #eab308;
        }
        
        .risk-warning.high-risk {
            background: rgba(239, 68, 68, 0.1);
            border-left-color: #ef4444;
        }
        
        .risk-warning i {
            color: #eab308;
            font-size: 1.5rem;
        }
        
        .risk-warning.high-risk i {
            color: #ef4444;
        }
        
        .market-order-warning {
            display: flex;
            gap: 0.75rem;
            padding: 0.75rem;
            background: rgba(59, 130, 246, 0.1);
            border-left: 4px solid #3b82f6;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
        }
        
        .market-order-warning i {
            color: #3b82f6;
        }
        
        .confirmation-checkbox {
            margin-top: 1rem;
            padding: 0.75rem;
            background: var(--card-bg);
            border-radius: 0.5rem;
        }
        
        .confirmation-checkbox label {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            cursor: pointer;
        }
        
        .confirmation-checkbox input[type="checkbox"] {
            width: 1.25rem;
            height: 1.25rem;
            cursor: pointer;
        }
    </style>
`;

// Inject styles
if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', function() {
        if (!document.getElementById('order-confirmation-styles')) {
            const styleElement = document.createElement('div');
            styleElement.id = 'order-confirmation-styles';
            styleElement.innerHTML = confirmationStyles;
            document.head.appendChild(styleElement);
        }
    });
}
