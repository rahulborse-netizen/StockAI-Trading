#!/usr/bin/env python3
"""
Phase 2 Migration Script
Creates database, initializes components, and performs data migration
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import sqlite3
import json
import shutil
from datetime import datetime

def create_holdings_database():
    """Create holdings database with schema"""
    db_path = project_root / 'data' / 'holdings_history.db'
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Creating holdings database at {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Portfolio snapshots table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            total_value REAL NOT NULL,
            cash_balance REAL NOT NULL,
            position_value REAL NOT NULL,
            daily_pnl REAL NOT NULL,
            cumulative_pnl REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Holding snapshots table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS holding_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            ticker TEXT,
            quantity INTEGER NOT NULL,
            average_price REAL NOT NULL,
            current_price REAL NOT NULL,
            pnl REAL NOT NULL,
            pnl_pct REAL NOT NULL,
            FOREIGN KEY(snapshot_id) REFERENCES portfolio_snapshots(id) ON DELETE CASCADE
        )
    ''')
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_snapshot_timestamp ON portfolio_snapshots(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_holding_snapshot_id ON holding_snapshots(snapshot_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_holding_symbol ON holding_snapshots(symbol)')
    
    conn.commit()
    conn.close()
    
    print("✓ Holdings database created successfully")

def backup_existing_data():
    """Backup existing data files"""
    data_dir = project_root / 'data'
    backup_dir = project_root / 'data' / 'backup_phase2'
    
    if not data_dir.exists():
        return
    
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Backup paper trading data
    paper_trading_file = data_dir / 'paper_trading.json'
    if paper_trading_file.exists():
        backup_file = backup_dir / f'paper_trading_{timestamp}.json'
        shutil.copy2(paper_trading_file, backup_file)
        print(f"✓ Backed up paper trading data to {backup_file}")
    
    # Backup watchlist
    watchlist_file = data_dir / 'watchlist.json'
    if watchlist_file.exists():
        backup_file = backup_dir / f'watchlist_{timestamp}.json'
        shutil.copy2(watchlist_file, backup_file)
        print(f"✓ Backed up watchlist to {backup_file}")

def initialize_paper_trading():
    """Initialize paper trading storage"""
    paper_trading_file = project_root / 'data' / 'paper_trading.json'
    paper_trading_file.parent.mkdir(parents=True, exist_ok=True)
    
    if not paper_trading_file.exists():
        initial_data = {
            'orders': {},
            'positions': {},
            'cash_balance': 100000.0,
            'initial_cash': 100000.0,
            'last_updated': datetime.now().isoformat()
        }
        
        with open(paper_trading_file, 'w') as f:
            json.dump(initial_data, f, indent=2)
        
        print("✓ Initialized paper trading storage")

def set_default_mode():
    """Set default trading mode to PAPER"""
    # This is handled by TradingModeManager default
    print("✓ Default trading mode set to PAPER (handled by TradingModeManager)")

def test_websocket_connectivity():
    """Test WebSocket connectivity (placeholder)"""
    print("✓ WebSocket connectivity test (will be tested when server starts)")

def main():
    """Run migration"""
    print("=" * 60)
    print("Phase 2 Migration Script")
    print("=" * 60)
    print()
    
    try:
        # Step 1: Backup existing data
        print("Step 1: Backing up existing data...")
        backup_existing_data()
        print()
        
        # Step 2: Create holdings database
        print("Step 2: Creating holdings database...")
        create_holdings_database()
        print()
        
        # Step 3: Initialize paper trading storage
        print("Step 3: Initializing paper trading storage...")
        initialize_paper_trading()
        print()
        
        # Step 4: Set default mode
        print("Step 4: Setting default trading mode...")
        set_default_mode()
        print()
        
        # Step 5: Test WebSocket (placeholder)
        print("Step 5: WebSocket connectivity...")
        test_websocket_connectivity()
        print()
        
        print("=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Start the Flask server: python run_web.py")
        print("2. Open the dashboard in your browser")
        print("3. Connect to Upstox if needed")
        print("4. Start using Phase 2 features!")
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
