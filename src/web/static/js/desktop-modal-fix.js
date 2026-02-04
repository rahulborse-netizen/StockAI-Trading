/**
 * Phase 1.1: Modal Input Fixes
 * Ensures all inputs and buttons are clickable
 * Clean, reliable approach
 */

(function() {
    'use strict';
    
    // Fix modal when it's shown
    function fixModalInputs() {
        console.log('[Phase 1.1] Fixing modal inputs...');
        
        // Remove mobile overlay completely
        const mobileOverlay = document.getElementById('mobile-overlay');
        if (mobileOverlay) {
            mobileOverlay.style.display = 'none';
            mobileOverlay.style.pointerEvents = 'none';
            mobileOverlay.style.zIndex = '-1';
            mobileOverlay.classList.remove('active');
        }
        
        // Ensure backdrop doesn't block
        document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
            backdrop.style.pointerEvents = 'none';
            backdrop.style.zIndex = '1040';
        });
        
        // Fix all inputs in modal
        const inputIds = ['api-key', 'api-secret', 'redirect-uri', 'access-token', 'upstox-auth-url'];
        inputIds.forEach(id => {
            const input = document.getElementById(id);
            if (input) {
                input.style.setProperty('pointer-events', 'auto', 'important');
                input.style.setProperty('z-index', '10000', 'important');
                input.style.setProperty('position', 'relative', 'important');
                input.style.setProperty('cursor', 'text', 'important');
                input.disabled = false;
                input.readOnly = false;
            }
        });
        
        // Fix all buttons
        const modal = document.getElementById('upstoxModal');
        if (modal) {
            modal.querySelectorAll('button').forEach(btn => {
                btn.style.setProperty('pointer-events', 'auto', 'important');
                btn.style.setProperty('cursor', 'pointer', 'important');
                btn.disabled = false;
            });
        }
        
        // Focus first input
        const firstInput = document.getElementById('api-key');
        if (firstInput) {
            setTimeout(() => {
                firstInput.focus();
            }, 150);
        }
        
        console.log('[Phase 1.1] Modal inputs fixed');
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            const upstoxModal = document.getElementById('upstoxModal');
            if (upstoxModal) {
                upstoxModal.addEventListener('shown.bs.modal', fixModalInputs);
            }
        });
    } else {
        const upstoxModal = document.getElementById('upstoxModal');
        if (upstoxModal) {
            upstoxModal.addEventListener('shown.bs.modal', fixModalInputs);
        }
    }
    
    // Also fix when showUpstoxModal is called
    if (typeof showUpstoxModal === 'function') {
        const originalShowUpstoxModal = showUpstoxModal;
        window.showUpstoxModal = function() {
            originalShowUpstoxModal();
            setTimeout(fixModalInputs, 100);
            setTimeout(fixModalInputs, 300);
        };
    }
    
    // Export for manual calls
    window.fixModalInputs = fixModalInputs;
})();
