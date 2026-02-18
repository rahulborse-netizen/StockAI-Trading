"""
Rate Limiting Tests
Tests for API rate limiting functionality
"""
import pytest
import time
from src.web.api.rate_limit import check_rate_limit_memory, get_client_id
from flask import Flask, request

@pytest.fixture
def app_context():
    """Create Flask app context"""
    app = Flask(__name__)
    with app.app_context():
        with app.test_request_context():
            yield app

def test_rate_limit_memory(app_context):
    """Test in-memory rate limiting"""
    client_id = "test_client"
    limit = 5
    window = 60
    
    # Should allow first 5 requests
    for i in range(limit):
        assert check_rate_limit_memory(client_id, limit, window) == True
    
    # 6th request should be blocked
    assert check_rate_limit_memory(client_id, limit, window) == False

def test_rate_limit_window(app_context):
    """Test rate limit window expiration"""
    client_id = "test_client_window"
    limit = 2
    window = 1  # 1 second window
    
    # Make 2 requests
    assert check_rate_limit_memory(client_id, limit, window) == True
    assert check_rate_limit_memory(client_id, limit, window) == True
    
    # Should be blocked
    assert check_rate_limit_memory(client_id, limit, window) == False
    
    # Wait for window to expire
    time.sleep(1.1)
    
    # Should be allowed again
    assert check_rate_limit_memory(client_id, limit, window) == True
