"""
Database Configuration and Connection Management
Supports both SQLite (development) and PostgreSQL (production)
"""
import os
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL', '')
USE_POSTGRES = bool(DATABASE_URL and DATABASE_URL.startswith('postgresql'))

if USE_POSTGRES:
    try:
        import psycopg2
        from psycopg2 import pool
        from psycopg2.extras import RealDictCursor
        
        # Parse database URL
        # Format: postgresql://user:password@host:port/database
        import urllib.parse as urlparse
        parsed = urlparse.urlparse(DATABASE_URL)
        
        DB_CONFIG = {
            'user': parsed.username,
            'password': parsed.password,
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path[1:] if parsed.path else 'stockai'
        }
        
        # Connection pool
        _connection_pool: Optional[pool.ThreadedConnectionPool] = None
        
        def get_connection_pool():
            """Get or create PostgreSQL connection pool"""
            global _connection_pool
            if _connection_pool is None:
                _connection_pool = pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=20,
                    **DB_CONFIG
                )
                logger.info("PostgreSQL connection pool created")
            return _connection_pool
        
        def get_db_connection():
            """Get a database connection from the pool"""
            pool = get_connection_pool()
            return pool.getconn()
        
        def return_db_connection(conn):
            """Return a connection to the pool"""
            pool = get_connection_pool()
            pool.putconn(conn)
        
        def init_database():
            """Initialize PostgreSQL database"""
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT version();")
                version = cursor.fetchone()
                logger.info(f"PostgreSQL connected: {version[0]}")
                cursor.close()
                return_db_connection(conn)
                return True
            except Exception as e:
                logger.error(f"PostgreSQL initialization failed: {e}")
                return False
        
    except ImportError:
        logger.warning("psycopg2 not installed, falling back to SQLite")
        USE_POSTGRES = False

if not USE_POSTGRES:
    # SQLite configuration (development)
    import sqlite3
    from contextlib import contextmanager
    
    DB_PATH = Path('data') / 'stockai.db'
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    def get_db_connection():
        """Get SQLite database connection"""
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def return_db_connection(conn):
        """Close SQLite connection"""
        conn.close()
    
    def init_database():
        """Initialize SQLite database"""
        try:
            conn = get_db_connection()
            conn.execute("SELECT 1")
            logger.info(f"SQLite database initialized: {DB_PATH}")
            conn.close()
            return True
        except Exception as e:
            logger.error(f"SQLite initialization failed: {e}")
            return False

from contextlib import contextmanager

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = get_db_connection()
    try:
        yield conn
        if USE_POSTGRES:
            conn.commit()
        else:
            conn.commit()
    except Exception as e:
        if USE_POSTGRES:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        return_db_connection(conn)
