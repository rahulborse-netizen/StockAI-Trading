"""
Authentication and Authorization
JWT-based authentication for API endpoints
"""
import os
import jwt
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app

logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', os.getenv('FLASK_SECRET_KEY', 'dev-secret'))
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

def generate_token(user_id: str, email: str = None, role: str = 'user') -> str:
    """
    Generate JWT token for user
    
    Args:
        user_id: User identifier
        email: User email (optional)
        role: User role (default: 'user')
    
    Returns:
        JWT token string
    """
    payload = {
        'user_id': user_id,
        'email': email,
        'role': role,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> dict:
    """
    Verify JWT token
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload
    
    Raises:
        jwt.ExpiredSignatureError: Token has expired
        jwt.InvalidTokenError: Token is invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")

def get_current_user():
    """Get current user from JWT token in request"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None
    
    try:
        # Extract token from "Bearer <token>"
        token = auth_header.split(' ')[1] if ' ' in auth_header else auth_header
        payload = verify_token(token)
        return payload
    except Exception as e:
        logger.debug(f"Token verification failed: {e}")
        return None

def require_auth(f):
    """Decorator to require authentication for API endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({
                'status': 'error',
                'message': 'Authentication required',
                'code': 'UNAUTHORIZED'
            }), 401
        
        # Add user to kwargs for use in route
        kwargs['current_user'] = user
        return f(*args, **kwargs)
    
    return decorated_function

def require_role(*allowed_roles):
    """Decorator to require specific role(s) for API endpoints"""
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            user = kwargs.get('current_user', {})
            user_role = user.get('role', 'user')
            
            if user_role not in allowed_roles:
                return jsonify({
                    'status': 'error',
                    'message': 'Insufficient permissions',
                    'code': 'FORBIDDEN'
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator
