"""
Trading Mode Manager
Phase 2.5: Switch between Paper Trading and Live Trading modes
"""
import threading
import logging
from typing import Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class TradingMode(Enum):
    """Trading mode enum"""
    PAPER = "paper"
    LIVE = "live"


class TradingModeManager:
    """
    Manages switching between paper trading and live trading modes
    Includes safety checks and validation
    """
    
    def __init__(self):
        self.current_mode = TradingMode.PAPER  # Default to paper trading for safety
        self.mode_lock = threading.Lock()
        self.mode_change_callbacks = []
        self._initialized = True
        
        logger.info(f"✅ Trading Mode Manager initialized - Default mode: {self.current_mode.value.upper()}")
    
    def get_mode(self) -> TradingMode:
        """Get current trading mode"""
        with self.mode_lock:
            return self.current_mode
    
    def is_paper_mode(self) -> bool:
        """Check if currently in paper trading mode"""
        return self.get_mode() == TradingMode.PAPER
    
    def is_live_mode(self) -> bool:
        """Check if currently in live trading mode"""
        return self.get_mode() == TradingMode.LIVE
    
    def set_mode(self, mode: str, user_confirmation: bool = False) -> dict:
        """
        Set trading mode with safety checks
        
        Args:
            mode: 'paper' or 'live'
            user_confirmation: Whether user has confirmed the switch
        
        Returns:
            dict with status and message
        """
        try:
            # Normalize mode string
            mode = mode.lower()
            
            if mode not in ['paper', 'live']:
                return {
                    'status': 'error',
                    'message': f'Invalid mode: {mode}. Must be "paper" or "live"'
                }
            
            new_mode = TradingMode.PAPER if mode == 'paper' else TradingMode.LIVE
            
            # If already in requested mode, return success
            if new_mode == self.current_mode:
                return {
                    'status': 'success',
                    'message': f'Already in {new_mode.value.upper()} mode'
                }
            
            # Switching to LIVE requires confirmation
            if new_mode == TradingMode.LIVE and not user_confirmation:
                return {
                    'status': 'confirmation_required',
                    'message': 'Switching to LIVE mode requires user confirmation',
                    'warning': '⚠️ LIVE MODE WARNING: All orders will execute with REAL MONEY!'
                }
            
            # Validate mode switch
            validation = self.validate_mode_switch(new_mode)
            if not validation['valid']:
                return {
                    'status': 'error',
                    'message': validation['message'],
                    'warnings': validation.get('warnings', [])
                }
            
            # Switch mode
            with self.mode_lock:
                old_mode = self.current_mode
                self.current_mode = new_mode
            
            logger.warning(f"🔄 Trading mode switched: {old_mode.value.upper()} → {new_mode.value.upper()}")
            
            # Notify callbacks
            self._notify_mode_change(old_mode, new_mode)
            
            return {
                'status': 'success',
                'message': f'Successfully switched to {new_mode.value.upper()} mode',
                'previous_mode': old_mode.value,
                'current_mode': new_mode.value,
                'warnings': validation.get('warnings', [])
            }
            
        except Exception as e:
            logger.error(f"Error switching trading mode: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def validate_mode_switch(self, new_mode: TradingMode) -> dict:
        """
        Validate if mode switch is safe
        
        Returns:
            dict with 'valid' boolean, 'message', and optional 'warnings'
        """
        warnings = []
        
        # Check for open positions (placeholder - implement based on your position manager)
        try:
            # TODO: Check if there are open positions
            # from src.web.some_position_manager import get_positions
            # positions = get_positions()
            # if positions:
            #     warnings.append(f'You have {len(positions)} open positions')
            pass
        except Exception as e:
            logger.warning(f"Could not check positions: {e}")
        
        # Check for pending orders (placeholder)
        try:
            # TODO: Check if there are pending orders
            # from src.web.some_order_manager import get_pending_orders
            # pending = get_pending_orders()
            # if pending:
            #     warnings.append(f'You have {len(pending)} pending orders')
            pass
        except Exception as e:
            logger.warning(f"Could not check orders: {e}")
        
        # Switching to LIVE mode requires connection
        if new_mode == TradingMode.LIVE:
            try:
                # TODO: Check if broker is connected
                # from src.web.upstox_connection import connection_manager
                # if not connection_manager.is_connected():
                #     return {
                #         'valid': False,
                #         'message': 'Cannot switch to LIVE mode: Broker not connected'
                #     }
                pass
            except Exception as e:
                logger.warning(f"Could not check broker connection: {e}")
        
        return {
            'valid': True,
            'message': 'Mode switch validation passed',
            'warnings': warnings
        }
    
    def register_mode_change_callback(self, callback: Callable):
        """
        Register a callback to be called when mode changes
        
        Args:
            callback: Function with signature callback(old_mode: TradingMode, new_mode: TradingMode)
        """
        if callback not in self.mode_change_callbacks:
            self.mode_change_callbacks.append(callback)
            logger.info(f"Registered mode change callback: {callback.__name__}")
    
    def unregister_mode_change_callback(self, callback: Callable):
        """Unregister a mode change callback"""
        if callback in self.mode_change_callbacks:
            self.mode_change_callbacks.remove(callback)
            logger.info(f"Unregistered mode change callback: {callback.__name__}")
    
    def _notify_mode_change(self, old_mode: TradingMode, new_mode: TradingMode):
        """Notify all registered callbacks of mode change"""
        for callback in self.mode_change_callbacks:
            try:
                callback(old_mode, new_mode)
            except Exception as e:
                logger.error(f"Error in mode change callback {callback.__name__}: {e}")
    
    def get_status(self) -> dict:
        """Get current status"""
        return {
            'current_mode': self.current_mode.value,
            'is_paper': self.is_paper_mode(),
            'is_live': self.is_live_mode(),
            'callbacks_registered': len(self.mode_change_callbacks)
        }


# Global singleton instance
_trading_mode_manager = None
_manager_lock = threading.Lock()


def get_trading_mode_manager() -> TradingModeManager:
    """Get global trading mode manager instance (singleton)"""
    global _trading_mode_manager
    with _manager_lock:
        if _trading_mode_manager is None:
            _trading_mode_manager = TradingModeManager()
        return _trading_mode_manager


def reset_trading_mode_manager():
    """Reset trading mode manager (useful for testing)"""
    global _trading_mode_manager
    with _manager_lock:
        _trading_mode_manager = None


def get_trading_mode() -> TradingMode:
    """Get current trading mode (convenience function for backward compatibility)"""
    return get_trading_mode_manager().get_mode()
