"""
Create test database schema
Sets up database tables for testing
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.web.database import get_db_connection, return_db_connection, USE_POSTGRES

def create_schema():
    """Create database schema"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            # PostgreSQL schema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id SERIAL PRIMARY KEY,
                    ticker VARCHAR(50) NOT NULL,
                    entry_price DECIMAL(10, 2) NOT NULL,
                    exit_price DECIMAL(10, 2),
                    quantity INTEGER NOT NULL,
                    transaction_type VARCHAR(10) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    pnl DECIMAL(10, 2),
                    status VARCHAR(20) DEFAULT 'open'
                );
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id SERIAL PRIMARY KEY,
                    ticker VARCHAR(50) NOT NULL,
                    signal VARCHAR(20) NOT NULL,
                    probability DECIMAL(5, 4),
                    confidence DECIMAL(5, 4),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        else:
            # SQLite schema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    quantity INTEGER NOT NULL,
                    transaction_type TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    pnl REAL,
                    status TEXT DEFAULT 'open'
                );
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    probability REAL,
                    confidence REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        
        conn.commit()
        print("Database schema created successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"Error creating schema: {e}")
        raise
    finally:
        cursor.close()
        return_db_connection(conn)

if __name__ == '__main__':
    create_schema()
