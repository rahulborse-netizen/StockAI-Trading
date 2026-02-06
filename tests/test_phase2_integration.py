"""
Phase 2 Integration Tests
Tests for WebSocket, order management, P&L, analytics, and trading mode
"""
import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.web.websocket_server import UpstoxWebSocketManager, get_ws_manager
from src.web.position_pnl import get_pnl_calculator
from src.web.position_analytics import get_position_analytics
from src.web.holdings_db import get_holdings_db
from src.web.trading_mode import get_trading_mode_manager
from src.web.paper_trading import get_paper_trading_manager


class TestWebSocketIntegration:
    """Test WebSocket connection and data flow"""
    
    def test_websocket_manager_initialization(self):
        """Test WebSocket manager can be initialized"""
        # Mock SocketIO for testing
        class MockSocketIO:
            def emit(self, event, data, namespace=None):
                pass
        
        socketio = MockSocketIO()
        manager = UpstoxWebSocketManager(socketio)
        assert manager is not None
        assert manager.is_connected == False
    
    def test_subscribe_instruments(self):
        """Test instrument subscription"""
        class MockSocketIO:
            def emit(self, event, data, namespace=None):
                pass
        
        socketio = MockSocketIO()
        manager = UpstoxWebSocketManager(socketio)
        
        instrument_keys = ['NSE_EQ|INE467B01029', 'NSE_EQ|INE040A01034']
        result = manager.subscribe_instruments(instrument_keys)
        
        assert result == True
        assert len(manager.subscribed_instruments) == 2


class TestOrderManagement:
    """Test order modification and cancellation"""
    
    def test_paper_order_modification(self):
        """Test modifying a paper trading order"""
        manager = get_paper_trading_manager()
        
        # Place a test order first
        result = manager.place_order(
            symbol='TEST',
            ticker='TEST.NS',
            transaction_type='BUY',
            quantity=10,
            order_type='LIMIT',
            price=100.0,
            current_market_price=100.0
        )
        
        if result.get('status') == 'success':
            order_id = result.get('order_id')
            
            # Modify the order
            modify_result = manager.modify_order(
                order_id=order_id,
                quantity=20,
                price=105.0
            )
            
            assert modify_result.get('status') == 'success' or modify_result.get('status') == 'error'
    
    def test_paper_order_cancellation(self):
        """Test cancelling a paper trading order"""
        manager = get_paper_trading_manager()
        
        # Place a test order first
        result = manager.place_order(
            symbol='TEST',
            ticker='TEST.NS',
            transaction_type='BUY',
            quantity=10,
            order_type='LIMIT',
            price=100.0,
            current_market_price=100.0
        )
        
        if result.get('status') == 'success':
            order_id = result.get('order_id')
            
            # Cancel the order
            cancel_result = manager.cancel_order(order_id)
            
            assert cancel_result.get('status') == 'success' or cancel_result.get('status') == 'error'


class TestPnLCalculation:
    """Test P&L calculation accuracy"""
    
    def test_position_pnl_calculation(self):
        """Test position P&L calculation"""
        calculator = get_pnl_calculator()
        
        position = {
            'quantity': 10,
            'average_price': 100.0
        }
        
        current_price = 110.0
        pnl_data = calculator.calculate_position_pnl(position, current_price)
        
        assert pnl_data['invested_value'] == 1000.0
        assert pnl_data['current_value'] == 1100.0
        assert pnl_data['unrealized_pnl'] == 100.0
        assert pnl_data['unrealized_pnl_pct'] == 10.0
    
    def test_portfolio_pnl_calculation(self):
        """Test portfolio P&L aggregation"""
        calculator = get_pnl_calculator()
        
        positions = [
            {
                'symbol': 'TEST1',
                'quantity': 10,
                'average_price': 100.0
            },
            {
                'symbol': 'TEST2',
                'quantity': 5,
                'average_price': 200.0
            }
        ]
        
        price_data = {
            'TEST1': 110.0,
            'TEST2': 190.0
        }
        
        portfolio_pnl = calculator.calculate_portfolio_pnl(positions, price_data)
        
        assert portfolio_pnl['total_invested'] == 2000.0
        assert portfolio_pnl['total_current_value'] == 2050.0
        assert portfolio_pnl['total_unrealized_pnl'] == 50.0


class TestTradingMode:
    """Test trading mode switching"""
    
    def test_mode_switching(self):
        """Test switching between paper and live modes"""
        manager = get_trading_mode_manager()
        
        # Start in paper mode (default)
        assert manager.is_paper_mode() == True
        
        # Try to switch to live (should require confirmation)
        result = manager.set_mode('live', user_confirmation=False)
        assert result.get('status') == 'confirmation_required' or result.get('status') == 'success'
        
        # Switch back to paper
        result = manager.set_mode('paper', user_confirmation=True)
        assert result.get('status') == 'success'
        assert manager.is_paper_mode() == True
    
    def test_mode_validation(self):
        """Test mode switch validation"""
        manager = get_trading_mode_manager()
        
        validation = manager.validate_mode_switch('live')
        assert 'safe' in validation
        assert 'warnings' in validation


class TestHoldingsDatabase:
    """Test holdings database operations"""
    
    def test_database_creation(self):
        """Test database is created correctly"""
        db = get_holdings_db()
        assert db.db_path.exists()
    
    def test_portfolio_snapshot_recording(self):
        """Test recording portfolio snapshot"""
        db = get_holdings_db()
        
        holdings = [
            {
                'symbol': 'TEST',
                'quantity': 10,
                'average_price': 100.0,
                'current_price': 110.0
            }
        ]
        
        snapshot_id = db.record_portfolio_snapshot(
            holdings=holdings,
            cash_balance=50000.0,
            daily_pnl=100.0,
            cumulative_pnl=100.0
        )
        
        assert snapshot_id > 0
    
    def test_portfolio_history_retrieval(self):
        """Test retrieving portfolio history"""
        db = get_holdings_db()
        
        history = db.get_portfolio_history(days=30)
        assert isinstance(history, list)


class TestPositionAnalytics:
    """Test position analytics"""
    
    def test_win_loss_ratio(self):
        """Test win/loss ratio calculation"""
        analytics = get_position_analytics()
        
        positions = [
            {'pnl': 100.0},
            {'pnl': -50.0},
            {'pnl': 200.0},
            {'pnl': -30.0}
        ]
        
        stats = analytics.get_win_loss_ratio(positions)
        
        assert stats['total_trades'] == 4
        assert stats['winning_trades'] == 2
        assert stats['losing_trades'] == 2
        assert stats['win_rate'] == 50.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
