"""
Database Tests
Tests for database connection and operations
"""
import pytest
import os
from src.web.database import get_db_connection, return_db_connection, init_database, USE_POSTGRES

def test_database_connection():
    """Test database connection"""
    assert init_database() == True

def test_get_connection():
    """Test getting database connection"""
    conn = get_db_connection()
    assert conn is not None
    return_db_connection(conn)

def test_connection_pool():
    """Test connection pool (PostgreSQL only)"""
    if not USE_POSTGRES:
        pytest.skip("PostgreSQL not configured")
    
    conn1 = get_db_connection()
    conn2 = get_db_connection()
    assert conn1 != conn2  # Should get different connections from pool
    return_db_connection(conn1)
    return_db_connection(conn2)
