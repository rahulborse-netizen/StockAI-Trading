"""
API v1 Tests
Tests for versioned API endpoints
"""
import pytest
import json
from src.web.app import app

@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'ok' in data
    assert 'status' in data
    assert 'services' in data

def test_health_v1_endpoint(client):
    """Test versioned health check endpoint"""
    response = client.get('/api/v1/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'ok' in data

def test_signals_endpoint(client):
    """Test signals endpoint"""
    response = client.get('/api/signals/^NSEI')
    assert response.status_code in [200, 404]  # May return 200 with error or 404
    
def test_signals_v1_endpoint(client):
    """Test versioned signals endpoint"""
    response = client.get('/api/v1/signals/^NSEI')
    assert response.status_code in [200, 404]

def test_openapi_docs(client):
    """Test OpenAPI documentation endpoint"""
    response = client.get('/api/docs')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'openapi' in data
    assert 'paths' in data
