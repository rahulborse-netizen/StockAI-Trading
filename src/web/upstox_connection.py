"""
Phase 1.2: Upstox Connection Manager
Handles OAuth2 flow, session management, and connection validation
"""

import logging
from typing import Optional, Dict, Tuple
from flask import session

from src.web.upstox_api import UpstoxAPI

logger = logging.getLogger(__name__)


class UpstoxConnectionManager:
    """Manages Upstox API connection lifecycle"""
    
    def __init__(self):
        self.client: Optional[UpstoxAPI] = None
    
    def get_client(self) -> Optional[UpstoxAPI]:
        """Get or rebuild Upstox client from session"""
        if self.client and self.client.access_token:
            return self.client
        
        # Rebuild from session
        api_key = session.get('upstox_api_key')
        api_secret = session.get('upstox_api_secret')
        redirect_uri = session.get('upstox_redirect_uri', 'http://localhost:5000/callback')
        access_token = session.get('upstox_access_token')
        
        if not api_key or not api_secret:
            return None
        
        self.client = UpstoxAPI(api_key, api_secret, redirect_uri)
        
        if access_token:
            self.client.set_access_token(access_token)
        
        return self.client
    
    def is_connected(self) -> bool:
        """Check if Upstox is connected"""
        # First check if we have a token in session
        access_token = session.get('upstox_access_token')
        if not access_token:
            logger.debug("[ConnectionManager] No access token in session")
            return False
        
        # Then check if client can be built and works
        client = self.get_client()
        if not client or not client.access_token:
            logger.debug("[ConnectionManager] Client is None or has no access token")
            return False
        
        # Test connection
        try:
            profile = client.get_profile()
            if 'error' in profile:
                logger.warning(f"[ConnectionManager] Profile check returned error: {profile.get('error')}")
                return False
            return True
        except Exception as e:
            logger.warning(f"[ConnectionManager] Exception checking connection: {e}")
            return False
    
    def validate_redirect_uri(self, redirect_uri: str) -> Tuple[bool, str]:
        """
        Validate redirect URI format
        Returns: (is_valid, error_message)
        """
        if not redirect_uri:
            return False, "Redirect URI is required"
        
        if not redirect_uri.startswith('http://') and not redirect_uri.startswith('https://'):
            return False, "Redirect URI must start with http:// or https://"
        
        if not redirect_uri.endswith('/callback'):
            return False, "Redirect URI must end with /callback"
        
        # Check for common mistakes
        if redirect_uri.count('//') > 1:
            return False, "Redirect URI has invalid format (double slashes)"
        
        return True, ""
    
    def get_suggested_redirect_uris(self, local_ip: str) -> list:
        """Get list of suggested redirect URIs for Upstox Portal"""
        return [
            'http://localhost:5000/callback',
            f'http://{local_ip}:5000/callback'
        ]
    
    def save_connection(self, api_key: str, api_secret: str, redirect_uri: str, access_token: Optional[str] = None):
        """Save connection details to session"""
        session['upstox_api_key'] = api_key
        session['upstox_api_secret'] = api_secret
        session['upstox_redirect_uri'] = redirect_uri
        session['upstox_connected'] = True
        
        if access_token:
            session['upstox_access_token'] = access_token
        
        # Rebuild client
        self.client = UpstoxAPI(api_key, api_secret, redirect_uri)
        if access_token:
            self.client.set_access_token(access_token)
    
    def clear_connection(self):
        """Clear connection from session"""
        session.pop('upstox_api_key', None)
        session.pop('upstox_api_secret', None)
        session.pop('upstox_redirect_uri', None)
        session.pop('upstox_access_token', None)
        session.pop('upstox_connected', None)
        self.client = None
    
    def get_connection_info(self) -> Dict:
        """Get current connection information"""
        api_key = session.get('upstox_api_key', '')
        redirect_uri = session.get('upstox_redirect_uri', '')
        is_connected = self.is_connected()
        
        return {
            'connected': is_connected,
            'api_key_preview': api_key[:8] + '...' if api_key else None,
            'redirect_uri': redirect_uri,
            'has_token': bool(session.get('upstox_access_token'))
        }


# Global instance
connection_manager = UpstoxConnectionManager()
