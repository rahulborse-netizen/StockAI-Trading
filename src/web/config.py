"""
Application Configuration
Environment-based configuration management
"""
import os
from pathlib import Path
from typing import Optional

class Config:
    """Base configuration"""
    # Flask
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-change-me-in-production')
    DEBUG = False
    TESTING = False
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', '')
    USE_POSTGRES = bool(DATABASE_URL and DATABASE_URL.startswith('postgresql'))
    
    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Upstox
    UPSTOX_API_KEY = os.getenv('UPSTOX_API_KEY', '')
    UPSTOX_API_SECRET = os.getenv('UPSTOX_API_SECRET', '')
    UPSTOX_REDIRECT_URI = os.getenv('UPSTOX_REDIRECT_URI', 'http://localhost:5000/callback')
    
    # Trading
    PAPER_TRADING_MODE = os.getenv('PAPER_TRADING_MODE', 'false').lower() == 'true'
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_DIR = Path(os.getenv('LOG_DIR', 'data/logs'))
    
    # Error Tracking
    SENTRY_DSN = os.getenv('SENTRY_DSN', '')
    SENTRY_TRACES_SAMPLE_RATE = float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1'))
    
    # API
    API_VERSION = os.getenv('API_VERSION', 'v1')
    RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
    RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', '60'))
    
    # Session (in seconds)
    PERMANENT_SESSION_LIFETIME = int(os.getenv('SESSION_LIFETIME_DAYS', '7')) * 24 * 60 * 60
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Data
    DATA_DIR = Path(os.getenv('DATA_DIR', 'data'))
    CACHE_DIR = Path(os.getenv('CACHE_DIR', 'cache'))
    
    # Application
    APP_VERSION = os.getenv('APP_VERSION', '1.0.0')
    APP_NAME = 'StockAI Trading Platform'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    
    # Production-specific settings
    if not Config.SECRET_KEY or Config.SECRET_KEY == 'dev-secret-change-me-in-production':
        raise ValueError("FLASK_SECRET_KEY must be set in production")

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    DATABASE_URL = 'sqlite:///:memory:'

def get_config() -> Config:
    """Get configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'development').lower()
    
    if env == 'production':
        return ProductionConfig()
    elif env == 'testing':
        return TestingConfig()
    else:
        return DevelopmentConfig()
