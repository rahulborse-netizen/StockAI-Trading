"""
Rate Limiting
API rate limiting using Redis or in-memory store
"""
import os
import time
import logging
from functools import wraps
from flask import request, jsonify
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)

# Rate limiting configuration
RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', '60'))

# In-memory rate limiter (fallback if Redis not available)
_memory_store = defaultdict(list)
_memory_lock = Lock()

def get_client_id():
    """Get client identifier for rate limiting"""
    # Try to get user ID from JWT token first
    auth_header = request.headers.get('Authorization')
    if auth_header:
        try:
            from src.web.api.auth import verify_token
            token = auth_header.split(' ')[1] if ' ' in auth_header else auth_header
            payload = verify_token(token)
            return f"user:{payload.get('user_id')}"
        except:
            pass
    
    # Fall back to IP address
    return f"ip:{request.remote_addr}"

def check_rate_limit_redis(client_id: str, limit: int, window: int = 60) -> bool:
    """Check rate limit using Redis"""
    try:
        import redis
        redis_url = os.getenv('REDIS_URL', '')
        if not redis_url:
            return None
        
        r = redis.from_url(redis_url)
        key = f"rate_limit:{client_id}"
        current = r.get(key)
        
        if current is None:
            r.setex(key, window, 1)
            return True
        
        if int(current) >= limit:
            return False
        
        r.incr(key)
        return True
        
    except Exception as e:
        logger.debug(f"Redis rate limit check failed: {e}")
        return None

def check_rate_limit_memory(client_id: str, limit: int, window: int = 60) -> bool:
    """Check rate limit using in-memory store"""
    with _memory_lock:
        now = time.time()
        # Clean old entries
        _memory_store[client_id] = [
            timestamp for timestamp in _memory_store[client_id]
            if now - timestamp < window
        ]
        
        # Check limit
        if len(_memory_store[client_id]) >= limit:
            return False
        
        # Add current request
        _memory_store[client_id].append(now)
        return True

def rate_limit(limit: int = None, window: int = 60):
    """
    Rate limiting decorator
    
    Args:
        limit: Maximum requests per window (default: RATE_LIMIT_PER_MINUTE)
        window: Time window in seconds (default: 60)
    """
    if limit is None:
        limit = RATE_LIMIT_PER_MINUTE
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not RATE_LIMIT_ENABLED:
                return f(*args, **kwargs)
            
            client_id = get_client_id()
            
            # Try Redis first
            allowed = check_rate_limit_redis(client_id, limit, window)
            
            # Fall back to memory if Redis not available
            if allowed is None:
                allowed = check_rate_limit_memory(client_id, limit, window)
            
            if not allowed:
                return jsonify({
                    'status': 'error',
                    'message': 'Rate limit exceeded',
                    'code': 'RATE_LIMIT_EXCEEDED',
                    'retry_after': window
                }), 429
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator
