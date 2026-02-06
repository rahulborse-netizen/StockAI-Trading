/**
 * Trading Mode Management
 * Phase 2.5: Trading mode toggle with safety confirmations
 */

class TradingModeManager {
    constructor() {
        this.currentMode = 'paper';
        this.init();
    }
    
    async init() {
        // Load current mode
        await this.loadMode();
        this.updateUI();
        
        // Setup confirmation input listener
        const confirmInput = document.getElementById('mode-confirm-input');
        const confirmBtn = document.getElementById('confirm-mode-switch-btn');
        
        if (confirmInput && confirmBtn) {
            confirmInput.addEventListener('input', (e) => {
                const value = e.target.value.trim().toUpperCase();
                confirmBtn.disabled = value !== 'CONFIRM';
            });
        }
    }
    
    async loadMode() {
        try {
            const response = await fetch('/api/trading-mode');
            const data = await response.json();
            this.currentMode = data.mode || 'paper';
        } catch (error) {
            console.error('Error loading trading mode:', error);
            this.currentMode = 'paper'; // Default to paper
        }
    }
    
    async switchMode(newMode) {
        if (newMode === this.currentMode) {
            return { status: 'success', message: `Already in ${newMode} mode` };
        }
        
        if (newMode === 'live') {
            // Show warning modal
            return this.showLiveModeWarning();
        } else {
            // Switch to paper mode (safer, no confirmation needed)
            return await this.actuallySwitch(newMode, true);
        }
    }
    
    showLiveModeWarning() {
        const modalElement = document.getElementById('modeSwitchModal');
        if (!modalElement) {
            console.error('Mode switch modal not found');
            return { status: 'error', error: 'Modal not found' };
        }
        
        // Reset confirmation input
        const confirmInput = document.getElementById('mode-confirm-input');
        const confirmBtn = document.getElementById('confirm-mode-switch-btn');
        if (confirmInput) confirmInput.value = '';
        if (confirmBtn) confirmBtn.disabled = true;
        
        // Show modal
        const modal = new bootstrap.Modal(modalElement, {
            backdrop: 'static',
            keyboard: false
        });
        modal.show();
        
        return { status: 'confirmation_required' };
    }
    
    async actuallySwitch(newMode, userConfirmation = false) {
        try {
            const response = await fetch('/api/trading-mode', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    mode: newMode,
                    user_confirmation: userConfirmation
                })
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                this.currentMode = newMode;
                this.updateUI();
                return result;
            } else {
                return result;
            }
        } catch (error) {
            console.error('Error switching mode:', error);
            return { status: 'error', error: error.message };
        }
    }
    
    updateUI() {
        const modeBadge = document.getElementById('mode-badge');
        const toggleBtn = document.getElementById('toggle-mode-btn');
        
        if (modeBadge) {
            modeBadge.textContent = this.currentMode.toUpperCase();
            modeBadge.className = `mode-badge ${this.currentMode}`;
        }
        
        if (toggleBtn) {
            if (this.currentMode === 'paper') {
                toggleBtn.textContent = 'Switch to Live Trading';
                toggleBtn.className = 'btn-toggle-mode';
            } else {
                toggleBtn.textContent = 'Switch to Paper Trading';
                toggleBtn.className = 'btn-toggle-mode live-mode';
            }
        }
    }
    
    getCurrentMode() {
        return this.currentMode;
    }
    
    isPaperMode() {
        return this.currentMode === 'paper';
    }
    
    isLiveMode() {
        return this.currentMode === 'live';
    }
}

// Global instance
let tradingModeManager = null;

function getTradingModeManager() {
    if (!tradingModeManager) {
        tradingModeManager = new TradingModeManager();
    }
    return tradingModeManager;
}

// Show mode switch modal
function showModeSwitchModal() {
    const manager = getTradingModeManager();
    const newMode = manager.isPaperMode() ? 'live' : 'paper';
    manager.switchMode(newMode);
}

// Confirm mode switch
async function confirmModeSwitch() {
    const manager = getTradingModeManager();
    const result = await manager.actuallySwitch('live', true);
    
    // Close modal
    const modalElement = document.getElementById('modeSwitchModal');
    const modal = bootstrap.Modal.getInstance(modalElement);
    if (modal) {
        modal.hide();
    }
    
    if (result.status === 'success') {
        if (typeof showNotification === 'function') {
            showNotification('✅ Switched to LIVE TRADING mode', 'success');
        } else {
            console.log('Switched to LIVE TRADING mode');
        }
    } else {
        if (typeof showNotification === 'function') {
            showNotification(result.error || 'Failed to switch mode', 'error');
        } else {
            console.error('Failed to switch mode:', result.error);
        }
    }
}

// Initialize on page load
if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', function() {
        getTradingModeManager();
    });
}
