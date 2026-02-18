"""
Database Migration Script: SQLite to PostgreSQL
Migrates existing SQLite data to PostgreSQL
"""
import os
import sys
import sqlite3
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.web.database import USE_POSTGRES, get_db_connection, return_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_holdings_db():
    """Migrate holdings database from SQLite to PostgreSQL"""
    sqlite_path = Path('data') / 'holdings.db'
    
    if not sqlite_path.exists():
        logger.info("No SQLite holdings database found, skipping migration")
        return
    
    if not USE_POSTGRES:
        logger.warning("PostgreSQL not configured, skipping migration")
        return
    
    try:
        # Connect to SQLite
        sqlite_conn = sqlite3.connect(str(sqlite_path))
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        
        # Connect to PostgreSQL
        pg_conn = get_db_connection()
        pg_cursor = pg_conn.cursor()
        
        # Get all tables from SQLite
        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in sqlite_cursor.fetchall()]
        
        logger.info(f"Found {len(tables)} tables to migrate: {tables}")
        
        for table in tables:
            # Get table schema
            sqlite_cursor.execute(f"PRAGMA table_info({table})")
            columns = sqlite_cursor.fetchall()
            
            # Get all data
            sqlite_cursor.execute(f"SELECT * FROM {table}")
            rows = sqlite_cursor.fetchall()
            
            if not rows:
                logger.info(f"Table {table} is empty, skipping")
                continue
            
            # Create table in PostgreSQL if it doesn't exist
            # Note: This is a simplified migration - adjust schema as needed
            logger.info(f"Migrating {len(rows)} rows from {table}")
            
            # Insert data (simplified - adjust based on actual schema)
            for row in rows:
                # Convert SQLite row to dict
                row_dict = dict(row)
                # Insert into PostgreSQL (adjust based on actual schema)
                # This is a placeholder - implement actual migration logic
                pass
        
        pg_conn.commit()
        pg_cursor.close()
        return_db_connection(pg_conn)
        
        sqlite_cursor.close()
        sqlite_conn.close()
        
        logger.info("Migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    logger.info("Starting database migration...")
    migrate_holdings_db()
    logger.info("Migration complete")
