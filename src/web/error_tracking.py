"""
Error Tracking Integration (Sentry)
Provides production error tracking and monitoring
"""
import os
import logging

logger = logging.getLogger(__name__)

_sentry_initialized = False

def init_error_tracking():
    """Initialize Sentry error tracking if DSN is provided"""
    global _sentry_initialized
    
    sentry_dsn = os.getenv('SENTRY_DSN')
    if not sentry_dsn:
        logger.debug("Sentry DSN not provided, error tracking disabled")
        return False
    
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[
                FlaskIntegration(transaction_style='endpoint'),
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.ERROR
                ),
            ],
            traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
            environment=os.getenv('FLASK_ENV', 'development'),
            release=os.getenv('APP_VERSION', 'unknown'),
        )
        
        _sentry_initialized = True
        logger.info("Sentry error tracking initialized")
        return True
        
    except ImportError:
        logger.warning("sentry-sdk not installed. Install with: pip install sentry-sdk")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")
        return False

def capture_exception(error: Exception, **kwargs):
    """Capture an exception in Sentry"""
    if not _sentry_initialized:
        return
    
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            for key, value in kwargs.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_exception(error)
    except Exception:
        pass  # Fail silently if Sentry not available

def capture_message(message: str, level: str = 'info', **kwargs):
    """Capture a message in Sentry"""
    if not _sentry_initialized:
        return
    
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            for key, value in kwargs.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_message(message, level=level)
    except Exception:
        pass  # Fail silently if Sentry not available
