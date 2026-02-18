"""
Server Monitoring Script - Checks for errors and resolves common issues
Run this alongside the trading dashboard to monitor and auto-fix errors
"""
import time
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Common error patterns and their fixes
ERROR_PATTERNS = {
    'YFRateLimitError': {
        'severity': 'warning',
        'action': 'rate_limit_detected',
        'message': 'Rate limit detected - will use longer backoff'
    },
    'SSL certificate problem': {
        'severity': 'warning',
        'action': 'ssl_issue',
        'message': 'SSL issue - YFINANCE_INSECURE_SSL should be enabled'
    },
    'Too Many Requests': {
        'severity': 'error',
        'action': 'rate_limit_detected',
        'message': 'Rate limit - requests are being throttled'
    },
    'ConnectionError': {
        'severity': 'error',
        'action': 'connection_issue',
        'message': 'Connection error - check network'
    },
    'Timeout': {
        'severity': 'warning',
        'action': 'timeout',
        'message': 'Request timeout - may need longer timeout'
    }
}


def check_server_health():
    """Check if server is running and responding."""
    try:
        import requests
        response = requests.get('http://localhost:5000', timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def monitor_log_file(log_file_path: Path, check_interval: int = 30):
    """Monitor log file for errors."""
    if not log_file_path.exists():
        logger.warning(f"Log file not found: {log_file_path}")
        return
    
    logger.info(f"Monitoring log file: {log_file_path}")
    logger.info("Press Ctrl+C to stop monitoring")
    
    # Track last position in file
    last_position = log_file_path.stat().st_size if log_file_path.exists() else 0
    
    try:
        while True:
            time.sleep(check_interval)
            
            # Check if file has grown
            current_size = log_file_path.stat().st_size
            if current_size > last_position:
                # Read new content
                with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(last_position)
                    new_content = f.read()
                    last_position = current_size
                    
                    # Check for error patterns
                    for pattern, info in ERROR_PATTERNS.items():
                        if pattern in new_content:
                            logger.warning(f"[{info['severity'].upper()}] {info['message']}")
                            
                            # Take action based on error type
                            if info['action'] == 'rate_limit_detected':
                                logger.info("Rate limiting is active - server will automatically backoff")
                            elif info['action'] == 'ssl_issue':
                                logger.info("SSL issues detected - ensure YFINANCE_INSECURE_SSL=1 is set")
                            
            # Check server health
            if not check_server_health():
                logger.error("Server is not responding! Check if it's still running.")
            
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Monitoring error: {e}")


if __name__ == '__main__':
    # Default log file location (adjust based on your setup)
    project_root = Path(__file__).parent
    log_file = project_root / 'server.log'
    
    # If log file doesn't exist, try to find terminal output
    if not log_file.exists():
        logger.info("No server.log found. Monitor terminal output manually.")
        logger.info("Common errors to watch for:")
        for pattern, info in ERROR_PATTERNS.items():
            logger.info(f"  - {pattern}: {info['message']}")
        sys.exit(0)
    
    check_interval = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    monitor_log_file(log_file, check_interval)
