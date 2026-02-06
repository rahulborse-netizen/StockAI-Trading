"""
Upstox API integration for order execution
Phase 1.2: Improved error handling and timeouts
"""
import requests
from typing import Optional, Dict, List
import json
from urllib.parse import urlencode
import logging

logger = logging.getLogger(__name__)

class UpstoxAPI:
    """Upstox API client for order execution"""
    
    BASE_URL = "https://api.upstox.com/v2"
    
    def __init__(self, api_key: str, api_secret: str, redirect_uri: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.redirect_uri = redirect_uri
        self.access_token = None
        self.session = requests.Session()

    def build_authorize_url(self) -> str:
        """
        Build the Upstox OAuth authorize URL (no SDK required).

        Upstox v2 flow:
        - User visits authorize URL -> Upstox redirects back with ?code=
        - We exchange code at /login/authorization/token
        """
        qs = urlencode(
            {
                "response_type": "code",
                "client_id": self.api_key,
                "redirect_uri": self.redirect_uri,
            }
        )
        return f"{self.BASE_URL}/login/authorization/dialog?{qs}"
    
    def authenticate(self, auth_code: str) -> bool:
        """Authenticate using authorization code"""
        try:
            url = f"{self.BASE_URL}/login/authorization/token"
            data = {
                'code': auth_code,
                'client_id': self.api_key,
                'client_secret': self.api_secret,
                'redirect_uri': self.redirect_uri,
                'grant_type': 'authorization_code'
            }
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }
            print(f"[DEBUG] Exchanging auth code for token...")
            print(f"[DEBUG] URL: {url}")
            print(f"[DEBUG] Redirect URI: {self.redirect_uri}")
            
            response = self.session.post(url, data=data, headers=headers, timeout=30)
            
            print(f"[DEBUG] Token exchange response status: {response.status_code}")
            print(f"[DEBUG] Response text: {response.text[:500]}")
            
            if response.status_code == 200:
                result = response.json()
                self.access_token = result.get('access_token')
                if self.access_token:
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.access_token}',
                        'Accept': 'application/json'
                    })
                    print(f"[DEBUG] Access token obtained successfully")
                    # Return refresh token if available for token refresh functionality
                    refresh_token = result.get('refresh_token')
                    if refresh_token:
                        return {'access_token': self.access_token, 'refresh_token': refresh_token}
                    return True
                else:
                    print(f"[ERROR] No access_token in response: {result}")
            else:
                error_text = response.text
                logger.error(f"[ERROR] Authentication failed: {response.status_code}")
                logger.error(f"[ERROR] Response: {error_text}")
                # Try to parse error details
                try:
                    error_json = response.json()
                    logger.error(f"[ERROR] Error details: {error_json}")
                    # Check for specific Upstox error codes
                    if 'errors' in error_json:
                        for err in error_json.get('errors', []):
                            error_code = err.get('errorCode', '')
                            error_msg = err.get('message', '')
                            logger.error(f"[ERROR] Upstox Error: {error_code} - {error_msg}")
                            if error_code == 'UDAP1100016':
                                logger.error(f"[ERROR] Invalid Credentials - This usually means:")
                                logger.error(f"[ERROR] 1. Redirect URI mismatch (most common)")
                                logger.error(f"[ERROR] 2. API Key/Secret mismatch")
                                logger.error(f"[ERROR] 3. Redirect URI in Portal: Check Upstox Developer Portal")
                                logger.error(f"[ERROR] 4. Redirect URI we're using: {self.redirect_uri}")
                except:
                    pass
            return False
        except Exception as e:
            print(f"[ERROR] Authentication exception: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def set_access_token(self, access_token: str):
        """Set access token directly"""
        self.access_token = access_token
        self.session.headers.update({
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        })
    
    def refresh_access_token(self, refresh_token: str) -> bool:
        """
        Refresh access token using refresh token
        Upstox v2 API uses refresh_token grant type
        """
        try:
            url = f"{self.BASE_URL}/login/authorization/token"
            data = {
                'grant_type': 'refresh_token',
                'client_id': self.api_key,
                'client_secret': self.api_secret,
                'refresh_token': refresh_token
            }
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }
            
            logger.info("[UpstoxAPI] Refreshing access token...")
            response = self.session.post(url, data=data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                new_access_token = result.get('access_token')
                new_refresh_token = result.get('refresh_token')
                
                if new_access_token:
                    self.set_access_token(new_access_token)
                    logger.info("[UpstoxAPI] Access token refreshed successfully")
                    
                    # Return refresh token if provided (for storage)
                    if new_refresh_token:
                        return {'access_token': new_access_token, 'refresh_token': new_refresh_token}
                    return {'access_token': new_access_token}
                else:
                    logger.error(f"[UpstoxAPI] No access_token in refresh response: {result}")
                    return None
            else:
                error_text = response.text
                logger.error(f"[UpstoxAPI] Token refresh failed: {response.status_code} - {error_text[:200]}")
                return None
        except Exception as e:
            logger.error(f"[UpstoxAPI] Exception refreshing token: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def check_connection_health(self) -> Dict:
        """
        Check connection health by making a lightweight API call
        Returns: {'healthy': bool, 'message': str, 'profile': dict}
        """
        try:
            profile = self.get_profile()
            if 'error' in profile:
                return {
                    'healthy': False,
                    'message': profile.get('error', 'Connection check failed'),
                    'profile': None
                }
            return {
                'healthy': True,
                'message': 'Connection is healthy',
                'profile': profile
            }
        except Exception as e:
            return {
                'healthy': False,
                'message': f'Health check exception: {str(e)}',
                'profile': None
            }
    
    def get_profile(self) -> Dict:
        """Get user profile with timeout"""
        try:
            url = f"{self.BASE_URL}/user/profile"
            response = self.session.get(url, timeout=10)  # 10 second timeout
            if response.status_code == 200:
                return response.json()
            return {'error': f'Status {response.status_code}', 'response': response.text[:200]}
        except requests.exceptions.Timeout:
            return {'error': 'Connection timeout - Upstox API took too long to respond. Please check your internet connection.'}
        except requests.exceptions.ConnectionError:
            return {'error': 'Connection error - Cannot reach Upstox API. Please check your internet connection.'}
        except Exception as e:
            return {'error': str(e)}
    
    def get_holdings(self) -> List[Dict]:
        """Get current holdings with timeout - tries multiple endpoints"""
        # Try multiple possible endpoints
        endpoints = [
            "/portfolio/short-term-holdings",
            "/portfolio/long-term-holdings", 
            "/portfolio/holdings",
            "/portfolio/positions"  # Sometimes holdings are in positions
        ]
        
        for endpoint in endpoints:
            try:
                url = f"{self.BASE_URL}{endpoint}"
                logger.info(f"[UpstoxAPI] Trying endpoint: {url}")
                logger.info(f"[UpstoxAPI] Access token present: {bool(self.access_token)}")
                
                response = self.session.get(url, timeout=10)
                logger.info(f"[UpstoxAPI] Response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"[UpstoxAPI] Raw API response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    logger.info(f"[UpstoxAPI] Raw API response (first 2000 chars): {str(data)[:2000]}")
                    
                    # Try different response formats
                    holdings = []
                    if isinstance(data, dict):
                        # Try common response formats
                        holdings = data.get('data', [])
                        if not holdings:
                            # Maybe data is directly in response
                            if 'data' in data and isinstance(data['data'], list):
                                holdings = data['data']
                            elif isinstance(data.get('result'), list):
                                holdings = data['result']
                            elif isinstance(data.get('holdings'), list):
                                holdings = data['holdings']
                            # Sometimes it's nested
                            elif isinstance(data.get('data'), dict) and 'holdings' in data.get('data', {}):
                                holdings = data['data']['holdings']
                    
                    logger.info(f"[UpstoxAPI] Extracted {len(holdings)} holdings from {endpoint}")
                    
                    if len(holdings) > 0:
                        logger.info(f"[UpstoxAPI] ✅ SUCCESS! Found holdings using endpoint: {endpoint}")
                        logger.info(f"[UpstoxAPI] Sample holding structure: {holdings[0]}")
                        return holdings
                    else:
                        logger.warning(f"[UpstoxAPI] No holdings in {endpoint}, trying next endpoint...")
                        continue
                elif response.status_code == 404:
                    logger.info(f"[UpstoxAPI] Endpoint {endpoint} not found (404), trying next...")
                    continue
                else:
                    error_text = response.text[:1000]
                    logger.warning(f"[UpstoxAPI] Endpoint {endpoint} returned {response.status_code}: {error_text[:200]}")
                    continue
                    
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"[UpstoxAPI] Timeout/connection error on {endpoint}: {e}")
                continue
            except Exception as e:
                logger.warning(f"[UpstoxAPI] Error on {endpoint}: {e}")
                continue
        
        # If we get here, no endpoint worked
        logger.error(f"[UpstoxAPI] ❌ All endpoints failed. No holdings found.")
        return []
    
    def get_positions(self) -> List[Dict]:
        """Get current positions with timeout"""
        try:
            url = f"{self.BASE_URL}/portfolio/positions"
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                return response.json().get('data', [])
            return []
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            logger.warning(f"Timeout/connection error getting positions: {e}")
            return []
        except Exception as e:
            logger.warning(f"Error getting positions: {e}")
            return []
    
    def get_orders(self) -> List[Dict]:
        """Get order history with timeout"""
        try:
            url = f"{self.BASE_URL}/order/retrieve-all"
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                return response.json().get('data', [])
            return []
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            logger.warning(f"Timeout/connection error getting orders: {e}")
            return []
        except Exception as e:
            logger.warning(f"Error getting orders: {e}")
            return []
    
    def get_instrument_key(self, ticker: str) -> Optional[str]:
        """Convert ticker to Upstox instrument key using instrument master"""
        try:
            from src.web.instrument_master import get_instrument_master
            master = get_instrument_master()
            key = master.get_instrument_key(ticker)
            if key:
                return key
        except Exception as e:
            pass
        
        # If instrument master fails, try Upstox API search (requires auth)
        if self.access_token:
            try:
                return self._search_instrument_via_api(ticker)
            except:
                pass
        
        # Final fallback: return None (will show helpful error)
        return None
    
    def _search_instrument_via_api(self, ticker: str) -> Optional[str]:
        """Search for instrument using Upstox API (requires authentication)"""
        try:
            # Remove .NS/.BO suffix for search
            search_symbol = ticker.replace('.NS', '').replace('.BO', '').replace('^', '')
            
            # Use Upstox market quote search API
            url = f"{self.BASE_URL}/market-quote/quotes"
            # Note: This endpoint may require instrument_key, so we'll use a different approach
            # For now, return None and let the error message guide the user
            return None
        except:
            return None
    
    def place_order(
        self,
        ticker: str,
        transaction_type: str,  # 'BUY' or 'SELL'
        quantity: int,
        order_type: str = 'MARKET',  # 'MARKET', 'LIMIT', 'SL', 'SL-M'
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        product: str = 'D',  # 'D' for Delivery, 'I' for Intraday
    ) -> Dict:
        """Place order"""
        if not self.access_token:
            raise ValueError("Not authenticated. Please authenticate first.")
        
        instrument_key = self.get_instrument_key(ticker)
        if not instrument_key:
            raise ValueError(f"Could not find instrument key for {ticker}")
        
        order_data = {
            'quantity': quantity,
            'product': product,
            'validity': 'DAY',
            'price': price if order_type in ['LIMIT', 'SL'] else 0,
            'tag': 'AI_TRADING',
            'instrument_token': instrument_key,
            'order_type': order_type,
            'transaction_type': transaction_type.upper(),
        }
        
        if trigger_price and order_type in ['SL', 'SL-M']:
            order_data['trigger_price'] = trigger_price
        
        try:
            url = f"{self.BASE_URL}/order/place"
            response = self.session.post(url, json=order_data)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {'error': f'Status {response.status_code}', 'message': response.text}
        except Exception as e:
            return {'error': str(e)}
    
    def cancel_order(self, order_id: str) -> Dict:
        """Cancel order"""
        try:
            url = f"{self.BASE_URL}/order/cancel"
            data = {'order_id': order_id}
            response = self.session.post(url, json=data)
            if response.status_code == 200:
                return response.json()
            return {'error': f'Status {response.status_code}'}
        except Exception as e:
            return {'error': str(e)}
    
    def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        order_type: Optional[str] = None
    ) -> Dict:
        """Modify existing order"""
        try:
            url = f"{self.BASE_URL}/order/modify"
            data = {'order_id': order_id}
            if quantity:
                data['quantity'] = quantity
            if price:
                data['price'] = price
            if order_type:
                data['order_type'] = order_type
            
            response = self.session.post(url, json=data)
            if response.status_code == 200:
                return response.json()
            return {'error': f'Status {response.status_code}'}
        except Exception as e:
            return {'error': str(e)}
