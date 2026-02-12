"""
Flask web application for AI Trading Algorithm
Provides UI/UX interface for monitoring, alerts, and order execution
"""
import sys
import os

# Add project root to Python path FIRST so imports work
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Fix SSL certificate before any HTTP calls (yfinance, requests)
try:
    from src.web import ssl_fix  # noqa: F401
except ImportError:
    try:
        import certifi
        os.environ.setdefault('SSL_CERT_FILE', certifi.where())
        os.environ.setdefault('REQUESTS_CA_BUNDLE', certifi.where())
    except ImportError:
        pass

from flask import Flask, render_template, jsonify, request, session
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
import pandas as pd
import numpy as np
from urllib.parse import urlencode
import requests

from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from src.research.data import download_yahoo_ohlcv, load_cached_csv
from src.research.features import make_features, add_label_forward_return_up, clean_ml_frame
from src.research.ml import train_baseline_classifier
from src.web.upstox_api import UpstoxAPI
from src.web.upstox_connection import connection_manager
from src.web.watchlist import WatchlistManager
from src.web.alerts import AlertManager
from src.web.instrument_master import InstrumentMaster
from src.web.market_data import MarketDataClient
from src.web.data_source_manager import get_data_source_manager
from src.web.trade_planner import get_trade_planner, get_plan_manager, TradePlanStatus
from src.web.position_sizing import calculate_risk_based_size
from src.web.risk_config import get_risk_config
from src.web.trade_journal import get_trade_journal
from src.web.risk_manager import get_risk_manager
from src.web.paper_trading import get_paper_trading_manager
# Optional modules - commented out if not present
# from src.web.daily_positions import get_daily_tracker
# from src.web.data_pipeline import get_data_pipeline
# from src.web.data_collectors.financial_data import get_financial_collector
# from src.web.data_collectors.news_sentiment import get_news_collector

# Stub functions for optional modules
def get_daily_tracker():
    return None
def get_data_pipeline():
    return None
def get_financial_collector():
    return None
def get_news_collector():
    return None
from typing import Dict, Optional, Tuple

# Phase 2.1: Flask-SocketIO for WebSocket support
from flask_socketio import SocketIO, emit
from src.web.websocket_server import init_websocket_handlers, get_ws_manager

# Phase 2.5: Trading mode manager
from src.web.trading_mode import get_trading_mode_manager
from src.web.holdings_db import get_holdings_db
from src.web.portfolio_recorder import get_portfolio_recorder
from src.web.stock_universe import get_stock_universe

# ELITE AI System
from src.web.ai_models.elite_signal_generator import get_elite_signal_generator
from src.web.ai_models.model_registry import get_model_registry
from src.web.ai_models.performance_tracker import get_performance_tracker
from src.web.ai_models.advanced_features import make_advanced_features, get_advanced_feature_columns

# Load environment variables (optional .env)
load_dotenv()

# Get the directory where this file is located
web_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(web_dir, 'templates')
static_dir = os.path.join(web_dir, 'static')

app = Flask(__name__, 
            template_folder=template_dir,
            static_folder=static_dir)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")  # Set FLASK_SECRET_KEY in production

# Configure session to persist
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Sessions last 7 days
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Phase 2.1: Initialize Flask-SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
init_websocket_handlers(socketio)

_upstox_wired_to_intraday = False


@app.before_request
def make_session_permanent():
    """Make session permanent so it persists"""
    session.permanent = True
    # Refresh Upstox token if expired (before any API calls)
    try:
        from src.web.upstox_connection import connection_manager
        if session.get('upstox_access_token'):
            connection_manager.refresh_token_if_needed()
    except Exception:
        pass
    # Wire Upstox to IntradayDataManager when connected (covers server restart)
    global _upstox_wired_to_intraday
    if not _upstox_wired_to_intraday and connection_manager.is_connected():
        try:
            client = connection_manager.get_client()
            if client and client.access_token:
                from src.web.intraday_data_manager import get_intraday_data_manager
                get_intraday_data_manager().set_upstox_client(client)
                _upstox_wired_to_intraday = True
                logger.debug("[Upstox] Wired to IntradayDataManager on request")
        except Exception as e:
            logger.debug(f"[Upstox] Wire to IntradayDataManager skipped: {e}")

# Initialize managers
watchlist_manager = WatchlistManager()
alert_manager = AlertManager()
upstox_api = None  # legacy global; use connection_manager instead

# Paper trading mode (can be toggled via environment variable or session)
PAPER_TRADING_MODE = os.getenv('PAPER_TRADING_MODE', 'false').lower() == 'true'

# Error handlers to ensure API routes always return JSON
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors - return JSON for API routes, HTML for others"""
    if request.path.startswith('/api/'):
        return jsonify({'status': 'error', 'message': 'API endpoint not found'}), 404
    return render_template('dashboard.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors - return JSON for API routes"""
    logger.error(f"Internal server error: {error}")
    if request.path.startswith('/api/'):
        return jsonify({
            'status': 'error', 
            'message': 'Internal server error. Check Flask server logs for details.',
            'error_type': 'InternalServerError'
        }), 500
    return f'<h1>Internal Server Error</h1><p>Check Flask server logs for details.</p>', 500

@app.errorhandler(Exception)
def handle_exception(error):
    """Handle all exceptions - return JSON for API routes"""
    logger.error(f"Unhandled exception: {error}", exc_info=True)
    if request.path.startswith('/api/'):
        return jsonify({
            'status': 'error',
            'message': f'Server error: {str(error)}',
            'error_type': type(error).__name__
        }), 500
    raise error  # Re-raise for non-API routes to use default Flask handler

DEFAULT_FEATURE_COLS = [
    "ret_1", "ret_5", "vol_10", "sma_10", "sma_50", "ema_20",
    "rsi_14", "macd", "macd_signal", "macd_hist",
    "vol_chg_1", "vol_sma_20",
]

def _get_local_ip():
    """Get local IP address for multi-device access (with timeout to prevent hanging)"""
    try:
        # Connect to a remote address to determine local IP with timeout
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)  # 2 second timeout to prevent hanging on company networks
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except (socket.timeout, socket.error, OSError) as e:
        logger.debug(f"Could not determine local IP (network may be restricted): {e}")
        return "127.0.0.1"
    except Exception as e:
        logger.warning(f"Unexpected error getting local IP: {e}")
        return "127.0.0.1"

def _get_base_url():
    """Get base URL for redirect URI (fast - defaults to localhost immediately)"""
    port = int(os.getenv("FLASK_PORT", "5000"))
    
    # FAST PATH: Always default to localhost immediately to avoid any delays
    # Network IP detection is slow and can cause timeouts on company networks
    # Users can manually enter network IP in redirect URI if needed
    return f"http://localhost:{port}"

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('dashboard.html')

@app.route('/trading-signals')
def trading_signals():
    """Trading signals UI page"""
    return render_template('trading_signals.html')

@app.route('/api/watchlist')
def get_watchlist():
    """Get current watchlist"""
    watchlist = watchlist_manager.get_watchlist()
    return jsonify(watchlist)

@app.route('/api/watchlist/add', methods=['POST'])
def add_to_watchlist():
    """Add ticker to watchlist"""
    data = request.json
    ticker = data.get('ticker')
    if ticker:
        watchlist_manager.add_ticker(ticker)
        return jsonify({'status': 'success', 'message': f'{ticker} added to watchlist'})
    return jsonify({'status': 'error', 'message': 'Ticker required'}), 400

@app.route('/api/watchlist/remove', methods=['POST'])
def remove_from_watchlist():
    """Remove ticker from watchlist"""
    data = request.json
    ticker = data.get('ticker')
    if ticker:
        watchlist_manager.remove_ticker(ticker)
        return jsonify({'status': 'success', 'message': f'{ticker} removed from watchlist'})
    return jsonify({'status': 'error', 'message': 'Ticker required'}), 400

@app.route('/api/chart-data/<ticker>')
def get_chart_data(ticker):
    """Get historical price data for charting"""
    try:
        logger.info(f"[Chart] Fetching chart data for ticker: {ticker}")
        
        # Get recent data (last 90 days for chart - more data for better visualization)
        # Ensure we're using correct dates (not future dates)
        today = datetime.now()
        today_str = today.strftime('%Y-%m-%d')
        
        # Use today as end_date (Yahoo Finance handles today's date fine)
        # But ensure it's not in the future by validating
        end_date = today_str
        
        # Start from 90 days ago
        start_date = (today - timedelta(days=90)).strftime('%Y-%m-%d')
        
        # Double-check: ensure end_date is not more than 1 day in the future
        # (accounting for timezone differences)
        max_future_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        if end_date > max_future_date:
            logger.error(f"[Chart] ERROR: End date {end_date} seems to be in the future! Using yesterday instead.")
            yesterday = today - timedelta(days=1)
            end_date = yesterday.strftime('%Y-%m-%d')
            start_date = (yesterday - timedelta(days=90)).strftime('%Y-%m-%d')
        
        logger.info(f"[Chart] System date check - Today: {today.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"[Chart] Calculated date range: {start_date} to {end_date}")
        
        # Final validation: ensure start < end and both are reasonable
        if start_date >= end_date:
            logger.error(f"[Chart] ERROR: Start date {start_date} >= End date {end_date}! Fixing...")
            start_date = (today - timedelta(days=90)).strftime('%Y-%m-%d')
            end_date = today_str
        
        # Ensure dates are not way in the future (sanity check)
        current_year = today.year
        start_year = int(start_date.split('-')[0])
        end_year = int(end_date.split('-')[0])
        
        if end_year > current_year + 1:
            logger.error(f"[Chart] ERROR: End date year {end_year} is way in the future (current year: {current_year})!")
            end_date = today_str
            start_date = (today - timedelta(days=90)).strftime('%Y-%m-%d')
        
        logger.info(f"[Chart] Final date range: {start_date} to {end_date}")
        
        # Try to get data from Upstox first if connected (more reliable)
        client = _get_upstox_client()
        if client and client.access_token:
            try:
                logger.info(f"[Chart] Attempting to get data from Upstox for {ticker}")
                # Try to get quote from Upstox
                from src.web.market_data import MarketDataClient
                from src.web.instrument_master import InstrumentMaster
                
                market_client = MarketDataClient(client.access_token)
                instrument_master = InstrumentMaster()
                
                # Convert ticker to instrument key
                inst_key = instrument_master.get_instrument_key(ticker)
                if inst_key:
                    quote = market_client.get_quote(inst_key)
                    if quote:
                        # For now, use Yahoo Finance for historical, but we have current price from Upstox
                        logger.info(f"[Chart] Got current price from Upstox: {quote.get('ltp', 'N/A')}")
            except Exception as upstox_err:
                logger.warning(f"[Chart] Upstox data fetch failed, using Yahoo Finance: {upstox_err}")
        
        Path("cache").mkdir(parents=True, exist_ok=True)
        cache_path = Path('cache') / f"{ticker.replace('^', '').replace(':', '_').replace('/', '_')}.csv"
        
        logger.info(f"[Chart] Downloading Yahoo Finance data from {start_date} to {end_date}")
        
        # Try with refresh=False first (use cache if available)
        ohlcv = None
        try:
            ohlcv = download_yahoo_ohlcv(
                ticker=ticker,
                start=start_date,
                end=end_date,
                interval='1d',
                cache_path=cache_path,
                refresh=False
            )
        except Exception as e:
            logger.warning(f"[Chart] First attempt failed: {e}, trying with refresh=True")
            # If cache fails, try refreshing
            try:
                ohlcv = download_yahoo_ohlcv(
                    ticker=ticker,
                    start=start_date,
                    end=end_date,
                    interval='1d',
                    cache_path=cache_path,
                    refresh=True
                )
            except Exception as e2:
                logger.error(f"[Chart] Both attempts failed: {e2}")
                # Try with a longer date range (1 year) as fallback
                logger.info(f"[Chart] Trying fallback: 1 year of data")
                try:
                    start_date_fallback = (today - timedelta(days=365)).strftime('%Y-%m-%d')
                    ohlcv = download_yahoo_ohlcv(
                        ticker=ticker,
                        start=start_date_fallback,
                        end=end_date,
                        interval='1d',
                        cache_path=cache_path,
                        refresh=True
                    )
                    if ohlcv and len(ohlcv.df) > 0:
                        # Take only last 90 days
                        ohlcv.df = ohlcv.df.tail(90)
                except Exception as e3:
                    logger.error(f"[Chart] Fallback also failed: {e3}")
                    raise e3
        
        if ohlcv is None:
            logger.warning(f"[Chart] No data returned for {ticker}")
            return jsonify({
                'error': f'No data available for {ticker}.',
                'suggestion': 'The ticker might be incorrect or Yahoo Finance might be temporarily unavailable. Try again later or verify the ticker symbol.'
            }), 404
        
        if len(ohlcv.df) == 0:
            logger.warning(f"[Chart] Empty dataframe for {ticker}")
            return jsonify({
                'error': f'No historical data found for {ticker}',
                'suggestion': 'This might be due to market holidays or the ticker not being available on Yahoo Finance.'
            }), 404
        
        logger.info(f"[Chart] Retrieved {len(ohlcv.df)} data points for {ticker}")
        
        # Format data for chart - handle different date column formats
        dates = []
        try:
            if 'date' in ohlcv.df.columns:
                if pd.api.types.is_datetime64_any_dtype(ohlcv.df['date']):
                    dates = ohlcv.df['date'].dt.strftime('%Y-%m-%d').tolist()
                else:
                    dates = pd.to_datetime(ohlcv.df['date']).dt.strftime('%Y-%m-%d').tolist()
            elif 'Date' in ohlcv.df.columns:
                if pd.api.types.is_datetime64_any_dtype(ohlcv.df['Date']):
                    dates = ohlcv.df['Date'].dt.strftime('%Y-%m-%d').tolist()
                else:
                    dates = pd.to_datetime(ohlcv.df['Date']).dt.strftime('%Y-%m-%d').tolist()
            elif isinstance(ohlcv.df.index, pd.DatetimeIndex):
                # Index is datetime
                dates = ohlcv.df.index.strftime('%Y-%m-%d').tolist()
            elif hasattr(ohlcv.df.index, 'strftime'):
                # Try to use index as date
                dates = [str(ohlcv.df.index[i])[:10] for i in range(len(ohlcv.df))]
            else:
                # Create sequential dates if no date column
                dates = [(datetime.now() - timedelta(days=len(ohlcv.df)-i)).strftime('%Y-%m-%d') 
                         for i in range(len(ohlcv.df))]
        except Exception as date_error:
            logger.warning(f"[Chart] Error parsing dates: {date_error}, using sequential dates")
            dates = [(datetime.now() - timedelta(days=len(ohlcv.df)-i)).strftime('%Y-%m-%d') 
                     for i in range(len(ohlcv.df))]
        
        # Get price data
        if 'close' in ohlcv.df.columns:
            prices = ohlcv.df['close'].tolist()
        elif 'Close' in ohlcv.df.columns:
            prices = ohlcv.df['Close'].tolist()
        else:
            logger.error(f"[Chart] No 'close' column found. Available columns: {list(ohlcv.df.columns)}")
            return jsonify({'error': 'Invalid data format - missing close price column'}), 500
        
        # Get high/low
        high = ohlcv.df['high'].tolist() if 'high' in ohlcv.df.columns else ohlcv.df.get('High', []).tolist() if 'High' in ohlcv.df.columns else prices
        low = ohlcv.df['low'].tolist() if 'low' in ohlcv.df.columns else ohlcv.df.get('Low', []).tolist() if 'Low' in ohlcv.df.columns else prices
        
        # Get volume
        volume = []
        if 'volume' in ohlcv.df.columns:
            volume = ohlcv.df['volume'].tolist()
        elif 'Volume' in ohlcv.df.columns:
            volume = ohlcv.df['Volume'].tolist()
        
        logger.info(f"[Chart] Successfully formatted {len(dates)} data points for chart")
        
        return jsonify({
            'ticker': ticker,
            'dates': dates,
            'prices': prices,
            'high': high,
            'low': low,
            'volume': volume
        })
    except Exception as e:
        logger.error(f"[Chart] Error fetching chart data for {ticker}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Failed to load chart data: {str(e)}'}), 500

@app.route('/api/signals/<path:ticker>')
def get_signals(ticker):
    """
    Get trading signals for a ticker using ELITE AI system
    Phase 3: Enhanced with ensemble models and advanced features
    Query params: ?elite=true (default), ?generate_plan=true, ?trading_type=swing
    """
    try:
        # Decode URL-encoded ticker (handles %5E for ^, etc.)
        from urllib.parse import unquote
        ticker = unquote(ticker)
        
        # Handle common ticker variations
        ticker = ticker.strip()
        
        # Map common index names to proper tickers
        index_map = {
            'nifty': '^NSEI',
            'nifty50': '^NSEI',
            'banknifty': '^NSEBANK',
            'sensex': '^BSESN',
            'vix': '^INDIAVIX',
            'indiavix': '^INDIAVIX'
        }
        
        ticker_lower = ticker.lower()
        if ticker_lower in index_map:
            ticker = index_map[ticker_lower]
            logger.info(f"[Signals] Mapped {ticker_lower} to {ticker}")
        
        logger.info(f"[Signals] Processing signal request for ticker: {ticker}")
        
        # Check if ELITE mode is enabled (default: true)
        use_elite = request.args.get('elite', 'true').lower() == 'true'
        generate_plan = request.args.get('generate_plan', 'false').lower() == 'true'
        trading_type = request.args.get('trading_type', 'swing')
        force_refresh = request.args.get('refresh', 'false').lower() == 'true'
        instrument_key = request.args.get('instrument_key', '').strip() or None  # From holdings - bypass instrument master
        
        # Serve from pre-computed cache first (unless refresh requested)
        if not force_refresh:
            try:
                from src.web.signal_cache import get_cached_signal
                cached = get_cached_signal(ticker)
                if cached:
                    logger.debug(f"[Signals] Serving {ticker} from cache")
                    return jsonify(cached)
            except Exception as cache_err:
                logger.debug(f"[Signals] Cache check failed: {cache_err}")
        
        # Use ELITE signal generator if enabled
        if use_elite:
            try:
                elite_generator = get_elite_signal_generator()
                signal_response = elite_generator.generate_signal(
                    ticker=ticker,
                    use_ensemble=True,
                    use_multi_timeframe=True,
                    instrument_key_override=instrument_key
                )
                
                # Check if signal_response is valid
                if signal_response and 'error' not in signal_response:
                    # Generate trade plan if requested
                    if generate_plan:
                        try:
                            account_balance = 100000.0  # Default
                            client = _get_upstox_client()
                            if client:
                                try:
                                    holdings = client.get_holdings()
                                    if holdings:
                                        total_value = sum(
                                            float(h.get('quantity', 0) or 0) * float(h.get('last_price', 0) or h.get('ltp', 0) or 0)
                                            for h in holdings
                                        )
                                        if total_value > 0:
                                            account_balance = total_value * 1.5
                                except:
                                    pass
                            
                            planner = get_trade_planner()
                            plan = planner.generate_trade_plan(
                                signal_data=signal_response,
                                trading_type=trading_type,
                                account_balance=account_balance
                            )
                            validation = planner.validate_trade_plan(plan)
                            
                            signal_response['trade_plan'] = plan.to_dict()
                            signal_response['validation'] = validation.to_dict()
                        except Exception as plan_err:
                            logger.warning(f"[Signals] Error generating trade plan: {plan_err}")
                            signal_response['trade_plan_error'] = str(plan_err)
                    
                    # Cache successful signal for next time
                    try:
                        from src.web.signal_cache import set_cached_signal
                        set_cached_signal(ticker, signal_response)
                    except Exception:
                        pass
                    return jsonify(signal_response)
                elif signal_response and 'error' in signal_response:
                    # ELITE returned an error - return 200 with structured response (graceful degradation)
                    hint = signal_response.get('hint') or 'Historical data unavailable. Connect Upstox or verify ticker symbol.'
                    logger.warning(f"[Signals] ELITE system returned error: {signal_response.get('error', 'Unknown error')} - {hint}")
                    return jsonify({
                        'signal': 'N/A',
                        'error': signal_response.get('error', 'Data unavailable'),
                        'hint': hint,
                        'ticker': ticker
                    }), 200
                else:
                    # ELITE returned None or invalid response
                    logger.warning(f"[Signals] ELITE system returned invalid response: {signal_response}")
            except Exception as elite_err:
                logger.error(f"[Signals] ELITE system exception: {elite_err}", exc_info=True)
                # If data-related failure, return structured 200 (graceful degradation)
                err_str = str(elite_err).lower()
                if 'download' in err_str or 'ssl' in err_str or 'certificate' in err_str or 'data' in err_str or 'yahoo' in err_str:
                    return jsonify({
                        'signal': 'N/A',
                        'error': 'Data unavailable',
                        'hint': 'Historical data failed. Connect Upstox for live data or check ticker symbol.',
                        'ticker': ticker
                    }), 200
                # Fall through to basic signal generation for other errors
        
        # Basic signal generation (fallback or if elite=false)
        # Get recent data - ensure dates are correct
        from datetime import date, timedelta
        today = date.today()
        
        # Use yesterday as end_date to ensure data availability
        end_date_obj = today - timedelta(days=1)
        
        # Validate end_date
        max_future_date = today + timedelta(days=1)
        if end_date_obj > max_future_date:
            logger.warning(f"[Signals] End date {end_date_obj} seems incorrect, using yesterday")
            end_date_obj = today - timedelta(days=1)
        
        end_date = end_date_obj.strftime('%Y-%m-%d')
        start_date = (end_date_obj - timedelta(days=365)).strftime('%Y-%m-%d')  # 1 year before
        
        logger.info(f"[Signals] Using dynamic date range for {ticker}: {start_date} to {end_date} (today: {today})")
        
        Path("cache").mkdir(parents=True, exist_ok=True)
        cache_path = Path('cache') / f"{ticker.replace('^', '').replace(':', '_').replace('/', '_')}.csv"
        
        # Fix Bug 1: Check if cache is stale and force refresh if needed
        # Cache is stale if it's older than 1 day or if date range doesn't match current range
        force_refresh = False
        if cache_path.exists():
            cache_age = (datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)).total_seconds()
            # Refresh if cache is older than 1 day (86400 seconds)
            if cache_age > 86400:
                force_refresh = True
                logger.info(f"[Signals] Cache for {ticker} is {cache_age/3600:.1f} hours old, forcing refresh")
        
        try:
            ohlcv = download_yahoo_ohlcv(
                ticker=ticker,
                start=start_date,
                end=end_date,
                interval='1d',
                cache_path=cache_path,
                refresh=force_refresh
            )
        except Exception as download_err:
            error_msg = f'Failed to download data for {ticker}: {str(download_err)}'
            logger.error(f"[Signals] {error_msg}")
            return jsonify({
                'signal': 'N/A',
                'error': 'Data unavailable',
                'hint': 'Connect Upstox for live data or check SSL/certifi setup',
                'ticker': ticker
            }), 200
        
        if ohlcv is None or len(ohlcv.df) == 0:
            error_msg = f'No data available for ticker {ticker}.'
            logger.error(f"[Signals] {error_msg}")
            return jsonify({
                'signal': 'N/A',
                'error': error_msg,
                'hint': 'Connect Upstox for live data or check ticker symbol.',
                'ticker': ticker
            }), 200
        
        # Generate features and predictions
        feat_df = make_features(ohlcv.df.copy())
        labeled_df = add_label_forward_return_up(feat_df, days=1, threshold=0.0)
        ml_df = clean_ml_frame(labeled_df, feature_cols=DEFAULT_FEATURE_COLS, label_col="label_up")
        
        if len(ml_df) < 50:
            return jsonify({
                'signal': 'N/A',
                'error': 'Insufficient data',
                'hint': 'Need at least 50 days of historical data. Connect Upstox for live data.',
                'ticker': ticker
            }), 200
        
        # Train model
        train_df = ml_df.iloc[:-1].copy()
        latest_row = ml_df.iloc[-1:].copy()
        
        trained, _ = train_baseline_classifier(
            df=train_df,
            feature_cols=DEFAULT_FEATURE_COLS,
            label_col="label_up",
            test_size=0.2,
            random_state=42
        )
        
        # Predict
        X_latest = latest_row[DEFAULT_FEATURE_COLS].fillna(0)
        prob_up = trained.model.predict_proba(X_latest)[0][1]
        
        # Calculate levels
        current_price = float(latest_row['close'].iloc[0])
        recent_high = float(ohlcv.df['high'].tail(20).max())
        recent_low = float(ohlcv.df['low'].tail(20).min())
        recent_volatility = float(ohlcv.df['close'].pct_change().tail(20).std() * np.sqrt(252))
        
        # Entry/Exit levels - Enhanced logic
        if prob_up >= 0.60:
            signal = 'BUY'
            entry_level = current_price * 0.998  # Slightly below current for better entry
            stop_loss = current_price * 0.97  # -3%
            target_1 = current_price * 1.03  # +3%
            target_2 = current_price * 1.05  # +5%
        elif prob_up <= 0.40:
            signal = 'SELL'
            entry_level = current_price * 1.002  # Slightly above current
            stop_loss = current_price * 1.03  # +3% (for short)
            target_1 = current_price * 0.97  # -3%
            target_2 = current_price * 0.95  # -5%
        else:
            signal = 'HOLD'
            entry_level = current_price * 1.002  # Wait for pullback
            stop_loss = current_price * 0.98
            target_1 = current_price * 1.02
            target_2 = current_price * 1.025
        
        signal_response = {
            'ticker': ticker,
            'current_price': current_price,
            'signal': signal,
            'probability': float(prob_up),
            'entry_level': entry_level,
            'stop_loss': stop_loss,
            'target_1': target_1,
            'target_2': target_2,
            'recent_high': recent_high,
            'recent_low': recent_low,
            'volatility': recent_volatility,
            'timestamp': datetime.now().isoformat(),
            'source': 'basic'  # Indicate this is from basic signal generator
        }
        
        # Generate trade plan if requested
        if generate_plan:
            try:
                signal_data = signal_response.copy()
                account_balance = 100000.0  # Default
                client = _get_upstox_client()
                if client:
                    try:
                        holdings = client.get_holdings()
                        if holdings:
                            total_value = sum(
                                float(h.get('quantity', 0) or 0) * float(h.get('last_price', 0) or h.get('ltp', 0) or 0)
                                for h in holdings
                            )
                            if total_value > 0:
                                account_balance = total_value * 1.5
                    except:
                        pass
                
                planner = get_trade_planner()
                plan = planner.generate_trade_plan(
                    signal_data=signal_data,
                    trading_type=trading_type,
                    account_balance=account_balance
                )
                validation = planner.validate_trade_plan(plan)
                
                signal_response['trade_plan'] = plan.to_dict()
                signal_response['validation'] = validation.to_dict()
            except Exception as plan_err:
                logger.warning(f"[Signals] Error generating trade plan: {plan_err}")
                signal_response['trade_plan_error'] = str(plan_err)
        
        return jsonify(signal_response)
        
    except Exception as e:
        error_msg = f'Error generating signals for {ticker}: {str(e)}'
        logger.error(f"[Signals] {error_msg}", exc_info=True)
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"[Signals] Full traceback:\n{error_trace}")
        if 'yfinance' in error_msg.lower() or 'download' in error_msg.lower():
            error_msg = f"Data fetch error: {error_msg}. Please check network connection or try again later."
        elif 'insufficient' in error_msg.lower() or 'data' in error_msg.lower():
            error_msg = f"Insufficient data for {ticker}. Please try a different stock."
        return jsonify({'error': error_msg, 'ticker': ticker}), 500

@app.route('/api/ai/models', methods=['GET'])
def get_ai_models():
    """Phase 3: Get list of registered AI models"""
    try:
        registry = get_model_registry()
        active_models = registry.get_active_models()
        
        models_list = [model.to_dict() for model in active_models]
        
        return jsonify({
            'models': models_list,
            'count': len(models_list)
        })
    except Exception as e:
        logger.error(f"Error getting AI models: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/models/<model_id>/performance', methods=['GET'])
def get_model_performance(model_id):
    """Phase 3: Get performance metrics for a model"""
    try:
        days = int(request.args.get('days', 30))
        tracker = get_performance_tracker()
        metrics = tracker.calculate_metrics(model_id, days)
        
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Error getting model performance: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/models/compare', methods=['GET'])
def compare_models():
    """Phase 3: Compare multiple models"""
    try:
        model_ids = request.args.get('models', '').split(',')
        days = int(request.args.get('days', 30))
        
        if not model_ids or model_ids == ['']:
            # Get all active models
            registry = get_model_registry()
            model_ids = [m.model_id for m in registry.get_active_models()]
        
        tracker = get_performance_tracker()
        comparison = tracker.compare_models(model_ids, days)
        
        return jsonify(comparison)
    except Exception as e:
        logger.error(f"Error comparing models: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/models/rankings', methods=['GET'])
def get_model_rankings():
    """Phase 3: Get ranked list of models by performance"""
    try:
        days = int(request.args.get('days', 30))
        tracker = get_performance_tracker()
        rankings = tracker.get_model_rankings(days)
        
        return jsonify({
            'rankings': rankings,
            'period_days': days
        })
    except Exception as e:
        logger.error(f"Error getting model rankings: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/index-signals')
def get_all_index_signals():
    """Get trading signals for all major indices using Adaptive Elite Strategy with multi-timeframe support"""
    from src.web.market_hours import get_market_hours_manager
    from src.web.ai_models.multi_timeframe_signal import get_multi_timeframe_aggregator
    
    indices = [
        {'name': 'Nifty 50', 'ticker': '^NSEI', 'key': 'nifty50'},
        {'name': 'Bank Nifty', 'ticker': '^NSEBANK', 'key': 'banknifty'},
        {'name': 'Sensex', 'ticker': '^BSESN', 'key': 'sensex'},
        {'name': 'Nifty 100', 'ticker': '^CNX100', 'key': 'nifty100'},
        {'name': 'Nifty 500', 'ticker': '^CNX500', 'key': 'nifty500'},
        {'name': 'India VIX', 'ticker': '^INDIAVIX', 'key': 'indiavix'}
    ]
    
    # Get timeframe parameter (default: all timeframes)
    timeframe = request.args.get('timeframe', 'all')  # '5m', '15m', '1h', '1d', 'all'
    timeframes = ['5m', '15m', '1h', '1d'] if timeframe == 'all' else [timeframe]
    
    # Check if intraday
    market_hours = get_market_hours_manager()
    is_intraday = market_hours.is_market_open()
    
    results = []
    elite_generator = get_elite_signal_generator()
    multi_tf_aggregator = get_multi_timeframe_aggregator()
    
    for index in indices:
        try:
            logger.info(f"[Index Signals] Processing {index['name']} ({index['ticker']}) - timeframes: {timeframes}")
            
            # Use multi-timeframe aggregator for intraday support
            if timeframe == 'all' or len(timeframes) > 1:
                # Multi-timeframe signal
                signal_response = multi_tf_aggregator.generate_multi_timeframe_signal(
                    ticker=index['ticker'],
                    timeframes=timeframes,
                    is_intraday=is_intraday,
                    use_ensemble=True,
                    min_confidence=0.6
                )
            else:
                # Single timeframe signal
                signal_response = elite_generator.generate_intraday_signal(
                    ticker=index['ticker'],
                    timeframe=timeframes[0],
                    use_ensemble=True
                )
            
            if 'error' in signal_response:
                logger.warning(f"[Index Signals] Error for {index['name']}: {signal_response.get('error')}")
                continue
            
            # Format response for index signals
            result = {
                'index_name': index['name'],
                'index_key': index['key'],
                'ticker': index['ticker'],
                'current_price': signal_response.get('current_price', 0),
                'signal': signal_response.get('signal') or signal_response.get('consensus_signal', 'HOLD'),
                'probability': signal_response.get('probability', signal_response.get('confidence', 0.5)),
                'confidence': signal_response.get('confidence', 0.5),
                'entry_level': signal_response.get('entry_level', signal_response.get('entry_price', 0)),
                'entry_price': signal_response.get('entry_level', signal_response.get('entry_price', 0)),
                'stop_loss': signal_response.get('stop_loss', 0),
                'target_1': signal_response.get('target_1', 0),
                'target_2': signal_response.get('target_2', 0),
                'timeframe': timeframe,
                'timeframes_analyzed': timeframes,
                'is_intraday': is_intraday,
                'timestamp': signal_response.get('timestamp', datetime.now().isoformat())
            }
            
            # Add multi-timeframe details if available
            if 'timeframe_signals' in signal_response:
                result['timeframe_signals'] = signal_response['timeframe_signals']
            
            # Add volatility and other metrics
            result['volatility'] = signal_response.get('volatility', 0)
            result['recent_high'] = signal_response.get('recent_high', 0)
            result['recent_low'] = signal_response.get('recent_low', 0)
            
            results.append(result)
        except Exception as e:
            logger.error(f"[Index Signals] Error for {index['name']}: {e}", exc_info=True)
            continue
    
    return jsonify(results)

# ============================================================================
# Trade Plan API Endpoints
# ============================================================================

@app.route('/api/trade-plan/generate', methods=['POST'])
def generate_trade_plan():
    """Generate a trade plan for a ticker"""
    try:
        data = request.json
        ticker = data.get('ticker')
        trading_type = data.get('trading_type', 'swing')  # intraday, swing, position
        
        if not ticker:
            return jsonify({'error': 'Ticker is required'}), 400
        
        # Get signal data first
        logger.info(f"[TradePlan] Generating trade plan for {ticker} ({trading_type})")
        
        # Get signal data
        today = datetime.now()
        today_str = today.strftime('%Y-%m-%d')
        end_date = today_str
        start_date = (today - timedelta(days=365)).strftime('%Y-%m-%d')
        
        Path("cache").mkdir(parents=True, exist_ok=True)
        cache_path = Path('cache') / f"{ticker.replace('^', '').replace(':', '_').replace('/', '_')}.csv"
        ohlcv = download_yahoo_ohlcv(
            ticker=ticker,
            start=start_date,
            end=end_date,
            interval='1d',
            cache_path=cache_path,
            refresh=False
        )
        
        if ohlcv is None or len(ohlcv.df) == 0:
            return jsonify({'error': 'No data available for ticker'}), 404
        
        # Generate features and predictions
        feat_df = make_features(ohlcv.df.copy())
        labeled_df = add_label_forward_return_up(feat_df, days=1, threshold=0.0)
        ml_df = clean_ml_frame(labeled_df, feature_cols=DEFAULT_FEATURE_COLS, label_col="label_up")
        
        if len(ml_df) < 50:
            return jsonify({
                'signal': 'N/A',
                'error': 'Insufficient data',
                'hint': 'Need at least 50 days of historical data. Connect Upstox for live data.',
                'ticker': ticker
            }), 200
        
        # Train model
        train_df = ml_df.iloc[:-1].copy()
        latest_row = ml_df.iloc[-1:].copy()
        
        trained, _ = train_baseline_classifier(
            df=train_df,
            feature_cols=DEFAULT_FEATURE_COLS,
            label_col="label_up",
            test_size=0.2,
            random_state=42
        )
        
        # Predict
        X_latest = latest_row[DEFAULT_FEATURE_COLS].fillna(0)
        prob_up = trained.model.predict_proba(X_latest)[0][1]
        
        # Calculate levels
        current_price = float(latest_row['close'].iloc[0])
        recent_high = float(ohlcv.df['high'].tail(20).max())
        recent_low = float(ohlcv.df['low'].tail(20).min())
        recent_volatility = float(ohlcv.df['close'].pct_change().tail(20).std() * np.sqrt(252))
        
        # Entry/Exit levels
        if prob_up >= 0.60:
            signal = 'BUY'
            entry_level = current_price * 0.998
            stop_loss = current_price * 0.97
            target_1 = current_price * 1.03
            target_2 = current_price * 1.05
        elif prob_up <= 0.40:
            signal = 'SELL'
            entry_level = current_price * 1.002
            stop_loss = current_price * 1.03
            target_1 = current_price * 0.97
            target_2 = current_price * 0.95
        else:
            signal = 'HOLD'
            entry_level = current_price * 1.002
            stop_loss = current_price * 0.98
            target_1 = current_price * 1.02
            target_2 = current_price * 1.025
        
        # Prepare signal data
        signal_data = {
            'ticker': ticker,
            'current_price': current_price,
            'signal': signal,
            'probability': float(prob_up),
            'entry_level': entry_level,
            'stop_loss': stop_loss,
            'target_1': target_1,
            'target_2': target_2,
            'recent_high': recent_high,
            'recent_low': recent_low,
            'volatility': recent_volatility,
            'timestamp': datetime.now().isoformat()
        }
        
        # Get account balance (estimate from holdings if available)
        account_balance = data.get('account_balance', 100000.0)  # Default 1L
        client = _get_upstox_client()
        if client:
            try:
                holdings = client.get_holdings()
                if holdings:
                    # Estimate account balance from holdings
                    total_value = sum(
                        float(h.get('quantity', 0) or 0) * float(h.get('last_price', 0) or h.get('ltp', 0) or 0)
                        for h in holdings
                    )
                    if total_value > 0:
                        account_balance = total_value * 1.5  # Assume 1.5x for available capital
            except:
                pass
        
        # Generate trade plan
        planner = get_trade_planner()
        plan = planner.generate_trade_plan(
            signal_data=signal_data,
            trading_type=trading_type,
            account_balance=account_balance
        )
        
        # Validate plan
        validation = planner.validate_trade_plan(plan)
        
        return jsonify({
            'plan': plan.to_dict(),
            'validation': validation.to_dict()
        })
        
    except Exception as e:
        logger.error(f"[TradePlan] Error generating trade plan: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/trade-plans', methods=['GET'])
def get_trade_plans():
    """Get all trade plans with optional filters"""
    try:
        status = request.args.get('status')
        trading_type = request.args.get('trading_type')
        symbol = request.args.get('symbol')
        
        manager = get_plan_manager()
        plans = manager.get_all_plans(
            status=status,
            trading_type=trading_type,
            symbol=symbol
        )
        
        return jsonify([plan.to_dict() for plan in plans])
        
    except Exception as e:
        logger.error(f"[TradePlan] Error getting trade plans: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trade-plan/<plan_id>', methods=['GET'])
def get_trade_plan(plan_id):
    """Get specific trade plan details"""
    try:
        manager = get_plan_manager()
        plan = manager.get_plan(plan_id)
        
        if not plan:
            return jsonify({'error': 'Trade plan not found'}), 404
        
        return jsonify(plan.to_dict())
        
    except Exception as e:
        logger.error(f"[TradePlan] Error getting trade plan {plan_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trade-plan/<plan_id>/approve', methods=['PUT'])
def approve_trade_plan(plan_id):
    """Approve a trade plan"""
    try:
        manager = get_plan_manager()
        plan = manager.get_plan(plan_id)
        
        if not plan:
            return jsonify({'error': 'Trade plan not found'}), 404
        
        manager.update_plan_status(plan_id, TradePlanStatus.APPROVED.value)
        
        return jsonify({'status': 'success', 'message': 'Trade plan approved'})
        
    except Exception as e:
        logger.error(f"[TradePlan] Error approving trade plan {plan_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trade-plan/<plan_id>/execute', methods=['POST'])
def execute_trade_plan(plan_id):
    """Execute a trade plan - returns order details for manual execution and logs to journal"""
    try:
        manager = get_plan_manager()
        plan = manager.get_plan(plan_id)
        
        if not plan:
            return jsonify({'error': 'Trade plan not found'}), 404
        
        # Get order ID from request if order was actually placed
        data = request.json or {}
        order_id = data.get('order_id')
        
        # Log to trade journal
        journal = get_trade_journal()
        trade = journal.log_trade(
            plan_id=plan_id,
            order_id=order_id,
            symbol=plan.symbol,
            ticker=plan.ticker,
            transaction_type=plan.signal,
            quantity=plan.quantity,
            entry_price=plan.entry_price,
            planned_entry=plan.entry_price,
            planned_stop_loss=plan.stop_loss,
            planned_target_1=plan.target_1,
            planned_target_2=plan.target_2
        )
        
        # Update plan status and link order
        if order_id:
            plan.order_id = order_id
            manager.update_plan_status(plan_id, TradePlanStatus.EXECUTED.value)
        
        # Return order details that can be used to pre-fill order form
        order_details = {
            'ticker': plan.ticker,
            'transaction_type': plan.signal,  # BUY or SELL
            'quantity': plan.quantity,
            'order_type': plan.order_type,
            'price': plan.entry_price if plan.order_type == 'LIMIT' else None,
            'product': plan.product,
            'stop_loss': plan.stop_loss,
            'target_1': plan.target_1,
            'target_2': plan.target_2
        }
        
        return jsonify({
            'status': 'success',
            'order_details': order_details,
            'plan': plan.to_dict(),
            'trade_id': trade.trade_id
        })
        
    except Exception as e:
        logger.error(f"[TradePlan] Error executing trade plan {plan_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trade-plan/<plan_id>', methods=['DELETE'])
def delete_trade_plan(plan_id):
    """Cancel/delete a trade plan"""
    try:
        manager = get_plan_manager()
        plan = manager.get_plan(plan_id)
        
        if not plan:
            return jsonify({'error': 'Trade plan not found'}), 404
        
        manager.delete_plan(plan_id)
        
        return jsonify({'status': 'success', 'message': 'Trade plan deleted'})
        
    except Exception as e:
        logger.error(f"[TradePlan] Error deleting trade plan {plan_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trade-plan/<plan_id>/backtest', methods=['POST'])
def backtest_trade_plan(plan_id):
    """Backtest a trade plan against historical data"""
    try:
        manager = get_plan_manager()
        plan = manager.get_plan(plan_id)
        
        if not plan:
            return jsonify({'error': 'Trade plan not found'}), 404
        
        planner = get_trade_planner()
        result = planner.backtest_trade_plan(plan)
        
        return jsonify({
            'status': 'success',
            'backtest_result': result
        })
        
    except Exception as e:
        logger.error(f"[TradePlan] Error backtesting trade plan {plan_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trade-journal', methods=['GET'])
def get_trade_journal_entries():
    """Get trade journal entries"""
    try:
        status = request.args.get('status')
        symbol = request.args.get('symbol')
        plan_id = request.args.get('plan_id')
        
        journal = get_trade_journal()
        
        if plan_id:
            trades = journal.get_trades_by_plan(plan_id)
        else:
            trades = journal.get_all_trades(status=status, symbol=symbol)
        
        return jsonify([trade.to_dict() for trade in trades])
        
    except Exception as e:
        logger.error(f"[TradeJournal] Error getting journal entries: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trade-journal/stats', methods=['GET'])
def get_trade_journal_stats():
    """Get trade journal performance statistics"""
    try:
        plan_id = request.args.get('plan_id')
        
        journal = get_trade_journal()
        stats = journal.get_performance_stats(plan_id=plan_id)
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"[TradeJournal] Error getting journal stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trade-plan/<plan_id>/risk-check', methods=['POST'])
def check_trade_plan_risk(plan_id):
    """Check portfolio risk for a trade plan"""
    try:
        manager = get_plan_manager()
        plan = manager.get_plan(plan_id)
        
        if not plan:
            return jsonify({'error': 'Trade plan not found'}), 404
        
        # Get portfolio state (simplified - would fetch from Upstox in production)
        portfolio_state = {
            'total_value': 100000.0,  # Default, would fetch from holdings
            'positions': []  # Would fetch from positions
        }
        
        # Try to get real portfolio data
        client = _get_upstox_client()
        if client:
            try:
                holdings = client.get_holdings()
                if holdings:
                    total_value = sum(
                        float(h.get('quantity', 0) or 0) * float(h.get('last_price', 0) or h.get('ltp', 0) or 0)
                        for h in holdings
                    )
                    portfolio_state['total_value'] = total_value * 1.5  # Estimate available capital
            except:
                pass
        
        risk_manager = get_risk_manager()
        risk_result = risk_manager.validate_trade_plan_risk(
            plan.to_dict(),
            portfolio_state
        )
        
        return jsonify({
            'status': 'success',
            'risk_check': {
                'passed': risk_result.passed,
                'message': risk_result.message,
                'details': risk_result.details
            }
        })
        
    except Exception as e:
        logger.error(f"[TradePlan] Error checking risk for plan {plan_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/prices')
def get_prices():
    """Get current prices for watchlist - Phase 2.1: Real-time data integration.
    Query: for_top_stocks=true | tickers=RELIANCE.NS,TCS.NS (comma-separated)"""
    tickers_param = request.args.get('tickers', '').strip()
    if tickers_param:
        watchlist = [t.strip() for t in tickers_param.split(',') if t.strip()]
    else:
        watchlist = watchlist_manager.get_watchlist()
    prices = {}
    
    # Try to get real-time data from Upstox if connected
    client = _get_upstox_client()
    if client and client.access_token:
        try:
            market_client = MarketDataClient(client.access_token)
            instrument_master = InstrumentMaster()
            
            # Get instrument keys for watchlist
            instrument_keys = []
            ticker_to_key = {}
            for ticker in watchlist:
                inst_key = instrument_master.get_instrument_key(ticker)
                if inst_key:
                    instrument_keys.append(inst_key)
                    ticker_to_key[ticker] = inst_key
            
            # Fetch real-time quotes
            if instrument_keys:
                quotes = market_client.get_quotes(instrument_keys)
                
                # Map quotes back to tickers
                for ticker, inst_key in ticker_to_key.items():
                    if inst_key in quotes:
                        parsed = market_client.parse_quote(quotes[inst_key])
                        prices[ticker] = parsed
                    else:
                        # Fallback to cached data
                        prices[ticker] = _get_cached_price(ticker)
            else:
                # No instrument keys found, use cached data
                for ticker in watchlist:
                    prices[ticker] = _get_cached_price(ticker)
                    
        except Exception as e:
            logger.error(f"Error fetching real-time prices: {e}")
            # Fallback to cached data
            for ticker in watchlist:
                prices[ticker] = _get_cached_price(ticker)
    else:
        # Not connected to Upstox - use DataSourceManager (correct tickers, SSL, null handling)
        for ticker in watchlist:
            try:
                quote, _ = get_data_source_manager().get_quote(ticker, use_cache=True)
                if quote and quote.get('current_price', 0) > 0:
                    prices[ticker] = {
                        'price': quote['current_price'],
                        'change': quote.get('change', 0),
                        'change_pct': quote.get('change_pct', 0),
                        'volume': int(quote.get('volume', 0)),
                        'timestamp': quote.get('timestamp', datetime.now().isoformat())
                    }
                else:
                    prices[ticker] = _get_cached_price(ticker)
            except Exception as e:
                logger.warning(f"Error fetching price for {ticker}: {e}")
                prices[ticker] = _get_cached_price(ticker)
    
    # Also handle top_stocks prices if requested (for sidebar)
    if request.args.get('for_top_stocks') == 'true':
        try:
            # Get top stocks list
            top_stocks_response = get_top_stocks()
            top_stocks = top_stocks_response.get_json() if hasattr(top_stocks_response, 'get_json') else top_stocks_response
            top_stocks_tickers = [s['ticker'] for s in top_stocks]
            
            for ticker in top_stocks_tickers:
                if ticker not in prices:
                    try:
                        quote, _ = get_data_source_manager().get_quote(ticker, use_cache=True)
                        if quote and quote.get('current_price', 0) > 0:
                            prices[ticker] = {
                                'price': quote['current_price'],
                                'change': quote.get('change', 0),
                                'change_pct': quote.get('change_pct', 0),
                                'volume': int(quote.get('volume', 0)),
                                'timestamp': quote.get('timestamp', datetime.now().isoformat())
                            }
                        else:
                            prices[ticker] = {
                                'price': 0,
                                'change': 0,
                                'change_pct': 0,
                                'volume': 0,
                                'error': 'No data'
                            }
                    except Exception as e:
                        logger.debug(f"Error fetching price for top stock {ticker}: {e}")
                        prices[ticker] = {
                            'price': 0,
                            'change': 0,
                            'change_pct': 0,
                            'volume': 0,
                            'error': str(e)
                        }
        except Exception as e:
            logger.warning(f"Error processing top stocks prices: {e}")
    
    return jsonify(prices)

@app.route('/api/market/start_stream', methods=['POST'])
def start_stream():
    """Phase 2.1: Start price streaming via WebSocket"""
    try:
        data = request.json or {}
        instrument_keys = data.get('instrument_keys', [])
        tickers = data.get('tickers', [])
        
        client = _get_upstox_client()
        if not client or not client.access_token:
            return jsonify({'error': 'Upstox not connected. Please connect first.'}), 400
        
        ws_manager = get_ws_manager()
        
        # Connect to WebSocket if not already connected
        if not ws_manager.is_connected():
            ws_manager.set_access_token(client.access_token)
            success = ws_manager.connect()
            if not success:
                return jsonify({'error': 'Failed to connect to Upstox WebSocket'}), 500
            
            # Register callback to broadcast price updates to Flask-SocketIO clients
            def broadcast_price_update(instrument_key, price_data):
                socketio.emit('price_update', {
                    'instrument_key': instrument_key,
                    'data': price_data
                }, broadcast=True)
            
            ws_manager.add_price_callback(broadcast_price_update)
        
        # Convert tickers to instrument keys if provided
        if tickers:
            instrument_master = InstrumentMaster()
            for ticker in tickers:
                inst_key = instrument_master.get_instrument_key(ticker)
                if inst_key:
                    instrument_keys.append(inst_key)
        
        # Subscribe to instruments
        if instrument_keys:
            success = ws_manager.subscribe_instruments(instrument_keys)
            if not success:
                return jsonify({'error': 'Failed to subscribe to instruments'}), 500
        
        subscribed = ws_manager.get_subscribed_instruments()
        
        return jsonify({
            'status': 'success',
            'message': f'Stream started with {len(subscribed)} instruments',
            'subscribed_instruments': list(subscribed)
        })
        
    except Exception as e:
        logger.error(f"Error starting stream: {e}", exc_info=True)
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Full traceback:\n{error_trace}")
        return jsonify({
            'error': str(e),
            'error_type': type(e).__name__,
            'message': 'Failed to start market data stream. Please check if Upstox is connected and try again.'
        }), 500

@app.route('/api/market/stop_stream', methods=['POST'])
def stop_stream():
    """Phase 2.1: Stop price streaming"""
    try:
        ws_manager = get_ws_manager()
        ws_manager.disconnect()
        
        return jsonify({
            'status': 'success',
            'message': 'Stream stopped'
        })
        
    except Exception as e:
        logger.error(f"Error stopping stream: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/market/ws_status', methods=['GET'])
def get_ws_status():
    """Phase 2.1: Get WebSocket connection status"""
    try:
        ws_manager = get_ws_manager()
        status = ws_manager.get_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting WebSocket status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/market-indices', methods=['GET'])
def get_market_indices():
    """Get live data for all major Indian stock market indices"""
    indices_config = [
        # Major Indices
        {'id': 'nifty', 'ticker': '^NSEI', 'label': 'NIFTY 50', 'upstox_key': 'NSE_INDEX|Nifty 50'},
        {'id': 'sensex', 'ticker': '^BSESN', 'label': 'SENSEX', 'upstox_key': 'BSE_INDEX|SENSEX'},
        {'id': 'banknifty', 'ticker': '^NSEBANK', 'label': 'BANKNIFTY', 'upstox_key': 'NSE_INDEX|Nifty Bank'},
        {'id': 'vix', 'ticker': '^INDIAVIX', 'label': 'INDIA VIX', 'upstox_key': 'NSE_INDEX|India VIX'},
        # Sectoral Indices
        {'id': 'niftyit', 'ticker': '^CNXIT', 'label': 'NIFTY IT', 'upstox_key': 'NSE_INDEX|Nifty IT'},
        {'id': 'niftyfmcg', 'ticker': '^CNXFMCG', 'label': 'NIFTY FMCG', 'upstox_key': 'NSE_INDEX|Nifty FMCG'},
        {'id': 'niftypharma', 'ticker': '^CNXPHARMA', 'label': 'NIFTY PHARMA', 'upstox_key': 'NSE_INDEX|Nifty Pharma'},
        {'id': 'niftyauto', 'ticker': '^CNXAUTO', 'label': 'NIFTY AUTO', 'upstox_key': 'NSE_INDEX|Nifty Auto'},
        {'id': 'niftymetal', 'ticker': '^CNXMETAL', 'label': 'NIFTY METAL', 'upstox_key': 'NSE_INDEX|Nifty Metal'},
        {'id': 'niftyenergy', 'ticker': '^CNXENERGY', 'label': 'NIFTY ENERGY', 'upstox_key': 'NSE_INDEX|Nifty Energy'},
        {'id': 'niftyrealty', 'ticker': '^CNXREALTY', 'label': 'NIFTY REALTY', 'upstox_key': 'NSE_INDEX|Nifty Realty'},
        {'id': 'niftypsu', 'ticker': '^CNXPSU', 'label': 'NIFTY PSU', 'upstox_key': 'NSE_INDEX|Nifty PSU Bank'},
        {'id': 'niftymidcap', 'ticker': '^CNXMID', 'label': 'NIFTY MIDCAP', 'upstox_key': 'NSE_INDEX|Nifty Midcap 100'},
        {'id': 'niftysmallcap', 'ticker': '^CNXSMALLCAP', 'label': 'NIFTY SMALLCAP', 'upstox_key': 'NSE_INDEX|Nifty Smallcap 100'},
    ]
    
    results = {}
    data_source_manager = get_data_source_manager()
    
    # Fetch from DataSourceManager (NSE → Upstox → Yahoo Finance)
    for index in indices_config:
        try:
            index_data, source = data_source_manager.get_index_data(index['id'])
            
            if index_data:
                results[index['id']] = {
                    'value': index_data.get('value', 0),
                    'change': index_data.get('change', 0),
                    'change_pct': index_data.get('change_pct', 0),
                    'source': source.name.lower() if source else 'unknown'
                }
                logger.debug(f"Got {index['label']} from {source.name if source else 'unknown'}")
            else:
                # Fallback to cached data
                try:
                    cached = _get_cached_price(index['ticker'])
                    if cached and 'price' in cached:
                        results[index['id']] = {
                            'value': cached['price'],
                            'change': cached.get('change', 0),
                            'change_pct': cached.get('change_pct', 0),
                            'source': 'cached'
                        }
                except:
                    pass
                    
        except Exception as e:
            logger.warning(f"Error fetching {index['label']}: {e}")
            continue
    
    return jsonify(results)

def _get_cached_price(ticker: str) -> Dict:
    """
    Get cached price - now uses DataSourceManager for better data quality
    Falls back to cache if DataSourceManager fails
    """
    # Try DataSourceManager first
    try:
        data_source_manager = get_data_source_manager()
        quote, source = data_source_manager.get_quote(ticker, use_cache=True)
        
        if quote and quote.get('current_price', 0) > 0:
            return {
                'price': quote.get('current_price', 0),
                'change': quote.get('change', 0),
                'change_pct': quote.get('change_pct', 0),
                'source': quote.get('source', 'unknown')
            }
    except Exception as e:
        logger.debug(f"DataSourceManager failed for {ticker}, using cache: {e}")
    
    # Fallback to original cache logic
    try:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        Path("cache").mkdir(parents=True, exist_ok=True)
        cache_path = Path('cache') / f"{ticker.replace('^', '').replace(':', '_').replace('/', '_')}.csv"
        
        # Try to use cached data first
        if cache_path.exists():
            try:
                ohlcv = load_cached_csv(cache_path)
                if ohlcv and len(ohlcv.df) > 0:
                    latest = ohlcv.df.iloc[-1]
                    if len(ohlcv.df) >= 2:
                        prev_close = ohlcv.df.iloc[-2]['close']
                        change = float(latest['close'] - prev_close)
                        change_pct = float((change / prev_close) * 100) if prev_close > 0 else 0.0
                    else:
                        change = 0.0
                        change_pct = 0.0
                    
                    return {
                        'price': float(latest['close']),
                        'change': change,
                        'change_pct': change_pct,
                        'volume': float(latest.get('volume', 0)),
                        'timestamp': latest.name.isoformat() if hasattr(latest.name, 'isoformat') else str(latest.name),
                        'source': 'cached'
                    }
            except Exception as cache_error:
                # Cache read failed, try downloading
                pass
        
        # Try to download fresh data
        try:
            ohlcv = download_yahoo_ohlcv(
                ticker=ticker,
                start=start_date,
                end=end_date,
                interval='1d',
                cache_path=cache_path,
                refresh=False
            )
            
            if ohlcv and len(ohlcv.df) > 0:
                latest = ohlcv.df.iloc[-1]
                if len(ohlcv.df) >= 2:
                    prev_close = ohlcv.df.iloc[-2]['close']
                    change = float(latest['close'] - prev_close)
                    change_pct = float((change / prev_close) * 100) if prev_close > 0 else 0.0
                else:
                    change = 0.0
                    change_pct = 0.0
                
                return {
                    'price': float(latest['close']),
                    'change': change,
                    'change_pct': change_pct,
                    'volume': float(latest.get('volume', 0)),
                    'timestamp': latest.name.isoformat() if hasattr(latest.name, 'isoformat') else str(latest.name),
                    'source': 'yahoo'
                }
        except Exception as download_error:
            logger.error(f"Error downloading data for {ticker}: {download_error}")
            return {'error': str(download_error), 'source': 'error'}
    
    except Exception as e:
        logger.error(f"Unexpected error in _get_cached_price for {ticker}: {e}")
        return {'error': str(e), 'source': 'error'}
    
    return {'error': 'No data available', 'source': 'error'}

def _get_upstox_client() -> UpstoxAPI | None:
    """
    Phase 1.2: Get Upstox client using connection manager.
    Falls back to session-based rebuild for compatibility.
    """
    # Try connection manager first
    client = connection_manager.get_client()
    if client:
        return client
    
    # Fallback to session-based rebuild
    api_key = session.get("upstox_api_key")
    redirect_uri = session.get("upstox_redirect_uri", "http://localhost:5000/callback")
    access_token = session.get("upstox_access_token")

    if not api_key or not access_token:
        return None

    # api_secret is not required once we already have an access token
    client = UpstoxAPI(api_key=api_key, api_secret=session.get("upstox_api_secret", ""), redirect_uri=redirect_uri)
    client.set_access_token(access_token)
    return client

@app.route('/api/alerts')
def get_alerts():
    """Get all alerts"""
    alerts = alert_manager.get_alerts()
    return jsonify(alerts)

@app.route('/api/alerts/add', methods=['POST'])
def add_alert():
    """Add new alert"""
    data = request.json
    ticker = data.get('ticker')
    condition = data.get('condition')  # 'above', 'below', 'change'
    value = data.get('value')
    
    if ticker and condition and value:
        alert_manager.add_alert(ticker, condition, value)
        return jsonify({'status': 'success', 'message': 'Alert added'})
    return jsonify({'status': 'error', 'message': 'Invalid alert parameters'}), 400

@app.route('/api/alerts/remove', methods=['POST'])
def remove_alert():
    """Remove alert"""
    data = request.json
    alert_id = data.get('alert_id')
    if alert_id:
        alert_manager.remove_alert(alert_id)
        return jsonify({'status': 'success', 'message': 'Alert removed'})
    return jsonify({'status': 'error', 'message': 'Alert ID required'}), 400

@app.route('/api/upstox/test', methods=['GET'])
def test_upstox_endpoint():
    """Quick test endpoint to verify server is responding"""
    return jsonify({
        'status': 'success',
        'message': 'Server is responding',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/upstox/connect', methods=['POST'])
def connect_upstox():
    """Phase 1.2: Connect to Upstox API with improved error handling"""
    global upstox_api
    
    logger.info(f"[Phase 1.2] ===== CONNECT REQUEST RECEIVED =====")
    logger.info(f"[Phase 1.2] Request method: {request.method}")
    logger.info(f"[Phase 1.2] Request content type: {request.content_type}")
    
    # Ensure we always return JSON, even on errors
    try:
        logger.info(f"[Phase 1.2] Parsing request JSON...")
        data = request.json
        if not data:
            logger.error(f"[Phase 1.2] No JSON data in request")
            return jsonify({'status': 'error', 'message': 'Invalid request: No JSON data provided'}), 400
        logger.info(f"[Phase 1.2] JSON parsed successfully")
    except Exception as e:
        logger.error(f"[Phase 1.2] Error parsing request JSON: {e}")
        return jsonify({'status': 'error', 'message': f'Invalid request format: {str(e)}'}), 400
    
    # Safely get and strip values, handling None
    api_key = (data.get('api_key') or '').strip()
    api_secret = (data.get('api_secret') or '').strip()
    
    # Auto-detect redirect URI if not provided (fast - defaults to localhost)
    redirect_uri = (data.get('redirect_uri') or '').strip()
    if not redirect_uri:
        # Fast path: use localhost immediately to avoid any delays
        port = int(os.getenv("FLASK_PORT", "5000"))
        redirect_uri = f'http://localhost:{port}/callback'
        logger.info(f"[Phase 1.2] Auto-detected redirect URI: {redirect_uri}")
    
    access_token = (data.get('access_token') or '').strip() or None
    
    # Validate inputs
    if not api_key:
        return jsonify({'status': 'error', 'message': 'API Key is required'}), 400
    if not api_secret:
        return jsonify({'status': 'error', 'message': 'API Secret is required'}), 400
    
    # Validate redirect URI format
    is_valid, error_msg = connection_manager.validate_redirect_uri(redirect_uri)
    if not is_valid:
        # Get suggested URIs without blocking on network detection
        try:
            local_ip = _get_local_ip()  # This now has timeout protection
            suggested_uris = connection_manager.get_suggested_redirect_uris(local_ip)
        except Exception as e:
            logger.warning(f"Could not get suggested URIs: {e}")
            suggested_uris = ['http://localhost:5000/callback']  # Fallback
        return jsonify({
            'status': 'error',
            'message': f'Invalid redirect URI: {error_msg}',
            'suggested_uris': suggested_uris
        }), 400
    
    logger.info(f"[Phase 1.2] Connect request - API Key: {api_key[:8]}..., Redirect URI: {redirect_uri}")
    
    try:
        # If access token is provided directly, test it first
        # Otherwise, skip straight to OAuth flow (faster, no timeout risk)
        if access_token and access_token.strip():
            logger.info("[Phase 1.2] Using direct access token")
            upstox_api = UpstoxAPI(api_key, api_secret, redirect_uri)
            upstox_api.set_access_token(access_token)
            connection_manager.save_connection(api_key, api_secret, redirect_uri, access_token)
            # Wire Upstox to IntradayDataManager for live data during market hours
            from src.web.intraday_data_manager import get_intraday_data_manager
            get_intraday_data_manager().set_upstox_client(upstox_api)
            
            # Test connection with timeout handling (short timeout to avoid hanging)
            logger.info("[Phase 1.2] Testing connection with access token (10s timeout)...")
            try:
                # Use shorter timeout for connection test to avoid hanging
                profile = upstox_api.get_profile(timeout=10)
                if 'error' in profile:
                    error_msg = profile.get('error', 'Unknown error')
                    status_code = profile.get('status_code', 0)
                    logger.error(f"[Phase 1.2] Connection test failed: {error_msg} (status: {status_code})")
                    connection_manager.clear_connection()
                    
                    # Provide specific hints based on error
                    hint = 'Check if access token is valid and not expired. You may need to generate a new token from Upstox.'
                    if status_code == 403 or 'Redirect URI' in error_msg or 'redirect' in error_msg.lower():
                        hint = f'Redirect URI mismatch! Verify in Upstox Portal that this EXACT URI is added: {redirect_uri}\nPortal: https://account.upstox.com/developer/apps'
                    elif status_code == 401:
                        hint = 'Access token is invalid or expired. Please reconnect using the OAuth flow (leave access token empty).'
                    
                    return jsonify({
                        'status': 'error', 
                        'message': f'Connection failed: {error_msg}',
                        'details': profile,
                        'hint': hint,
                        'redirect_uri': redirect_uri,
                        'upstox_portal_url': 'https://account.upstox.com/developer/apps'
                    }), 400
                
                logger.info("[Phase 1.2] Connection test successful")
                return jsonify({
                    'status': 'success', 
                    'message': 'Upstox connected successfully',
                    'profile': profile
                })
            except requests.exceptions.Timeout as e:
                logger.error(f"[Phase 1.2] Connection test timeout: {e}")
                connection_manager.clear_connection()
                return jsonify({
                    'status': 'error',
                    'message': f'Connection timeout - Upstox API took too long to respond',
                    'hint': f'This might indicate:\n1. Redirect URI mismatch (most common)\n2. Network issues\n3. Upstox API is slow\n\nVerify redirect URI in Upstox Portal: {redirect_uri}\nPortal: https://account.upstox.com/developer/apps',
                    'redirect_uri': redirect_uri,
                    'upstox_portal_url': 'https://account.upstox.com/developer/apps'
                }), 400
            except Exception as e:
                logger.error(f"[Phase 1.2] Connection test exception: {e}")
                import traceback
                logger.error(traceback.format_exc())
                connection_manager.clear_connection()
                error_msg = str(e)
                hint = 'This might be a network issue. Please check your internet connection and try again.'
                if 'redirect' in error_msg.lower() or 'uri' in error_msg.lower():
                    hint = f'Redirect URI issue detected. Verify in Upstox Portal: {redirect_uri}'
                return jsonify({
                    'status': 'error',
                    'message': f'Connection test failed: {error_msg}',
                    'hint': hint,
                    'redirect_uri': redirect_uri
                }), 400
        
        # Otherwise, generate authorization URL for OAuth flow
        # This should be instant - no network calls, just URL building
        # Skip connection test to avoid timeouts - OAuth flow is faster
        logger.info("[CONNECT] Starting OAuth flow (no connection test - instant)...")
        logger.info(f"[CONNECT] Creating UpstoxAPI instance...")
        upstox_api = UpstoxAPI(api_key, api_secret, redirect_uri)
        logger.info(f"[CONNECT] UpstoxAPI instance created")
        
        logger.info(f"[CONNECT] Saving connection to session...")
        connection_manager.save_connection(api_key, api_secret, redirect_uri)
        logger.info(f"[CONNECT] Connection saved to session")
        
        # Generate authorization URL (instant - no network call)
        logger.info(f"[CONNECT] Building authorization URL...")
        logger.info(f"[CONNECT] Using redirect_uri: {redirect_uri}")
        logger.info(f"[CONNECT] Using API Key: {api_key[:8]}...")
        auth_url = upstox_api.build_authorize_url()
        logger.info(f"[CONNECT] ✅ Authorization URL generated (instant, no network call)")
        logger.info(f"[CONNECT] Full auth URL: {auth_url[:150]}...")
        logger.info(f"[CONNECT] ⚠️ CRITICAL: Make sure this redirect_uri is in Upstox Portal: {redirect_uri}")
        
        # Get suggested URIs (fast - no network detection)
        suggested_uris = ['http://localhost:5000/callback']  # Fast default
        
        logger.info(f"[CONNECT] Returning auth_required response (instant)...")
        return jsonify({
            'status': 'auth_required',
            'message': 'Authorization required',
            'auth_url': auth_url,
            'redirect_uri': redirect_uri,
            'suggested_redirect_uris': suggested_uris,
            'api_key_preview': api_key[:8] + '...',
            'instructions': f'⚠️ CRITICAL: Add this EXACT redirect URI to Upstox Developer Portal:\n\n{redirect_uri}\n\nPortal: https://account.upstox.com/developer/apps',
            'upstox_portal_url': 'https://account.upstox.com/developer/apps'
        })
        
    except Exception as e:
        import traceback
        logger.error(f"[Phase 1.2] Connection error: {e}\n{traceback.format_exc()}")
        return jsonify({
            'status': 'error', 
            'message': f'Connection error: {str(e)}',
            'error_type': type(e).__name__
        }), 400

@app.route('/callback')
def upstox_callback():
    """Phase 1.2: Upstox OAuth callback handler with improved error handling"""
    global upstox_api
    auth_code = request.args.get('code')
    error = request.args.get('error')
    error_description = request.args.get('error_description', '')
    
    # Log full callback details for debugging
    logger.info(f"[CALLBACK] Full callback URL: {request.url}")
    logger.info(f"[CALLBACK] Query params: {dict(request.args)}")
    logger.info(f"[CALLBACK] Code: {'Yes' if auth_code else 'No'}, Error: {error}, Description: {error_description}")
    
    if error:
        error_html = f'''
        <html>
        <head>
            <title>Upstox Authorization Failed</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #0f172a; color: #f1f5f9; }}
                .error {{ background: #ef4444; padding: 20px; border-radius: 8px; margin: 20px auto; max-width: 500px; }}
                .info {{ background: #1e293b; padding: 15px; border-radius: 8px; margin: 20px auto; max-width: 500px; }}
            </style>
        </head>
        <body>
            <div class="error">
                <h1>✗ Authorization Failed</h1>
                <p><strong>Error:</strong> {error}</p>
                <p>{error_description or 'Please check your redirect URI in Upstox Developer Portal'}</p>
            </div>
            <div class="info">
                <p><strong>Common fixes:</strong></p>
                <ul style="text-align: left; display: inline-block;">
                    <li>Verify redirect URI matches exactly in Upstox Portal</li>
                    <li>Check API Key and Secret are correct</li>
                    <li>Ensure app is active in Upstox Developer Portal</li>
                </ul>
            </div>
        </body>
        </html>
        '''
        return error_html, 400
    
    if not auth_code:
        return '<h1>Authorization Failed</h1><p>No authorization code received. Please try connecting again.</p>', 400
    
    try:
        api_key = session.get('upstox_api_key')
        api_secret = session.get('upstox_api_secret')
        redirect_uri = session.get('upstox_redirect_uri', 'http://localhost:5000/callback')
        
        logger.info(f"[Phase 1.2] Session data - API Key: {'Yes' if api_key else 'No'}, Secret: {'Yes' if api_secret else 'No'}")
        logger.info(f"[Phase 1.2] Redirect URI from session: {redirect_uri}")
        
        if not api_key or not api_secret:
            logger.warning("[Phase 1.2] Session expired - missing credentials")
            return '''
            <h1>Session Expired</h1>
            <p>Your session expired. Please:</p>
            <ol>
                <li>Close this window</li>
                <li>Go back to the dashboard</li>
                <li>Click "Connect" again and enter your API credentials</li>
            </ol>
            ''', 400
        
        upstox_api = UpstoxAPI(api_key, api_secret, redirect_uri)
        
        # Exchange authorization code for access token
        logger.info(f"[CALLBACK] Attempting authentication with code: {auth_code[:20]}...")
        logger.info(f"[CALLBACK] Using redirect_uri: {redirect_uri}")
        logger.info(f"[CALLBACK] Using API Key: {api_key[:8]}...")
        
        try:
            auth_result = upstox_api.authenticate(auth_code)
            auth_success = False
            refresh_token = None
            
            if isinstance(auth_result, dict):
                # New format: returns dict with access_token and refresh_token
                access_token = auth_result.get('access_token')
                refresh_token = auth_result.get('refresh_token')
                if access_token:
                    upstox_api.set_access_token(access_token)
                    auth_success = True
                    logger.info(f"[CALLBACK] ✅ Authentication successful!")
            elif auth_result:
                # Old format: returns True
                auth_success = True
                logger.info(f"[CALLBACK] ✅ Authentication successful!")
            
            if not auth_success:
                # Get detailed error from upstox_api if available
                error_details = getattr(upstox_api, '_last_error', None) or {}
                error_code = error_details.get('error_code', 'Unknown')
                error_message = error_details.get('error_message', 'Authentication failed')
                
                logger.error(f"[CALLBACK] ❌ Authentication failed")
                logger.error(f"[CALLBACK] Error Code: {error_code}")
                logger.error(f"[CALLBACK] Error Message: {error_message}")
                logger.error(f"[CALLBACK] Expected redirect URI: {redirect_uri}")
                logger.error(f"[CALLBACK] Please verify this EXACT URI is in Upstox Portal")
                
                # Show detailed error page
                error_html = f'''
                <html>
                <head>
                    <title>Upstox Connection Failed</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #0f172a; color: #f1f5f9; }}
                        .error {{ background: #ef4444; padding: 20px; border-radius: 8px; margin: 20px auto; max-width: 600px; }}
                        .info {{ background: #1e293b; padding: 15px; border-radius: 8px; margin: 20px auto; max-width: 600px; text-align: left; }}
                        .code {{ background: #000; padding: 10px; border-radius: 4px; font-family: monospace; margin: 10px 0; word-break: break-all; }}
                        .success-btn {{ background: #6366f1; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin: 10px; }}
                        a {{ color: #60a5fa; }}
                    </style>
                </head>
                <body>
                    <div class="error">
                        <h1>✗ Connection Failed</h1>
                        <p><strong>Error Code:</strong> {error_code}</p>
                        <p><strong>Error:</strong> {error_message}</p>
                    </div>
                    <div class="info">
                        <h3>Most Common Cause: Redirect URI Mismatch</h3>
                        <p><strong>Expected Redirect URI:</strong></p>
                        <div class="code">{redirect_uri}</div>
                        <p><strong>Steps to fix:</strong></p>
                        <ol>
                            <li>Go to <a href="https://account.upstox.com/developer/apps" target="_blank">Upstox Developer Portal</a></li>
                            <li>Find your app (API Key: {api_key[:8]}...)</li>
                            <li>Click <strong>Edit/Settings</strong></li>
                            <li>In <strong>Redirect URI(s)</strong> field, add EXACTLY:</li>
                            <div class="code">{redirect_uri}</div>
                            <li><strong>Save</strong> and wait 1-2 minutes</li>
                            <li>Go back to dashboard and try connecting again</li>
                        </ol>
                        <p style="color: #fbbf24; margin-top: 20px;">
                            ⚠️ <strong>Important:</strong> The URI must match EXACTLY - no trailing spaces, correct port, must end with /callback
                        </p>
                    </div>
                    <button class="success-btn" onclick="window.close()">Close Window</button>
                    <button class="success-btn" onclick="window.location.href='/'">Go to Dashboard</button>
                </body>
                </html>
                '''
                return error_html, 400
        except Exception as auth_error:
            import traceback
            logger.error(f"[CALLBACK] ❌ Authentication exception: {auth_error}")
            logger.error(f"[CALLBACK] Traceback: {traceback.format_exc()}")
            # Show error page for exception too
            error_html = f'''
            <html>
            <head>
                <title>Upstox Connection Error</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #0f172a; color: #f1f5f9; }}
                    .error {{ background: #ef4444; padding: 20px; border-radius: 8px; margin: 20px auto; max-width: 600px; }}
                    .code {{ background: #000; padding: 10px; border-radius: 4px; font-family: monospace; margin: 10px 0; word-break: break-all; }}
                    .success-btn {{ background: #6366f1; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin: 10px; }}
                </style>
            </head>
            <body>
                <div class="error">
                    <h1>✗ Connection Error</h1>
                    <p><strong>Error:</strong> {str(auth_error)}</p>
                    <p>Please check server logs for details.</p>
                </div>
                <div class="code">Expected Redirect URI: {redirect_uri}</div>
                <button class="success-btn" onclick="window.close()">Close Window</button>
                <button class="success-btn" onclick="window.location.href='/'">Go to Dashboard</button>
            </body>
            </html>
            '''
            return error_html, 500
        
        if auth_success:
            connection_manager.save_connection(api_key, api_secret, redirect_uri, upstox_api.access_token, refresh_token)
            # Wire Upstox to IntradayDataManager for live data during market hours
            from src.web.intraday_data_manager import get_intraday_data_manager
            get_intraday_data_manager().set_upstox_client(upstox_api)
            
            # Test connection
            logger.info("[Phase 1.2] Testing profile fetch...")
            profile = upstox_api.get_profile()
            logger.info(f"[Phase 1.2] Profile: {profile}")
            
            user_name = 'Connected'
            if 'data' in profile and isinstance(profile['data'], dict):
                user_name = profile['data'].get('user_name', 'Connected')
            elif isinstance(profile, dict) and 'user_name' in profile:
                user_name = profile['user_name']
            
            return f'''
            <html>
            <head>
                <title>Upstox Connected</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #0f172a; color: #f1f5f9; }}
                    .success {{ background: #10b981; padding: 20px; border-radius: 8px; margin: 20px auto; max-width: 500px; }}
                    .info {{ background: #1e293b; padding: 15px; border-radius: 8px; margin: 20px auto; max-width: 500px; }}
                </style>
            </head>
            <body>
                <div class="success">
                    <h1>✓ Upstox Connected Successfully!</h1>
                    <p>You can now close this window and return to the dashboard.</p>
                </div>
                <div class="info">
                    <p><strong>Profile:</strong> {user_name}</p>
                </div>
                <script>
                    setTimeout(function() {{
                        window.close();
                        if (window.opener) {{
                            window.opener.location.reload();
                        }} else {{
                            window.location.href = '/';
                        }}
                    }}, 2000);
                </script>
            </body>
            </html>
            '''
        else:
            # Authentication failed - show detailed error with redirect URI
            error_html = f'''
            <html>
            <head>
                <title>Upstox Authorization Failed</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #0f172a; color: #f1f5f9; }}
                    .error {{ background: #ef4444; padding: 20px; border-radius: 8px; margin: 20px auto; max-width: 700px; }}
                    .info {{ background: #1e293b; padding: 20px; border-radius: 8px; margin: 20px auto; max-width: 700px; text-align: left; }}
                    .code {{ background: #0f172a; padding: 15px; border-radius: 4px; font-family: monospace; margin: 15px 0; border: 1px solid #334155; word-break: break-all; }}
                    .step {{ margin: 15px 0; padding: 10px; background: #1e293b; border-left: 4px solid #60a5fa; }}
                    a {{ color: #60a5fa; text-decoration: none; }}
                    a:hover {{ text-decoration: underline; }}
                    ul {{ margin: 10px 0; padding-left: 20px; }}
                    li {{ margin: 5px 0; }}
                </style>
            </head>
            <body>
                <div class="error">
                    <h1>✗ Authentication Failed</h1>
                    <p><strong>Error Code:</strong> UDAP1100016 - Invalid Credentials</p>
                    <p>This error means the <strong>Redirect URI doesn't match</strong> what's registered in Upstox Portal.</p>
                </div>
                <div class="info">
                    <h2>How to Fix:</h2>
                    
                    <div class="step">
                        <strong>Step 1:</strong> Go to <a href="https://account.upstox.com/developer/apps" target="_blank">Upstox Developer Portal</a>
                    </div>
                    
                    <div class="step">
                        <strong>Step 2:</strong> Click on your app ("upstok api")
                    </div>
                    
                    <div class="step">
                        <strong>Step 3:</strong> In "Redirect URL" field, enter EXACTLY:
                        <div class="code">{redirect_uri}</div>
                    </div>
                    
                    <div class="step">
                        <strong>Step 4:</strong> Verify:
                        <ul>
                            <li>✅ Must be <code>http://</code> (NOT https://)</li>
                            <li>✅ Must be <code>localhost</code> (NOT 127.0.0.1)</li>
                            <li>✅ Must be port <code>5000</code> (NOT 88)</li>
                            <li>✅ Must end with <code>/callback</code> (NOT /stocktrading)</li>
                            <li>✅ No trailing spaces</li>
                        </ul>
                    </div>
                    
                    <div class="step">
                        <strong>Step 5:</strong> Click "Save" in Upstox Portal, then try again
                    </div>
                    
                    <p style="text-align: center; margin-top: 30px;">
                        <a href="/" style="background: #3b82f6; padding: 10px 20px; border-radius: 5px; display: inline-block;">← Back to Dashboard</a>
                    </p>
                </div>
            </body>
            </html>
            '''
            return error_html, 400
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"[Phase 1.2] Callback error: {e}\n{error_trace}")
        return f'''
        <h1>Error</h1>
        <p>{str(e)}</p>
        <p><a href="/" style="color: #6366f1;">Return to Dashboard</a></p>
        ''', 500

@app.route('/api/upstox/health', methods=['GET'])
def check_upstox_health():
    """Phase 2.1: Check Upstox connection health"""
    try:
        client = _get_upstox_client()
        if not client:
            return jsonify({
                'healthy': False,
                'message': 'Not connected to Upstox',
                'connected': False
            }), 200
        
        health = client.check_connection_health()
        return jsonify({
            'healthy': health['healthy'],
            'message': health['message'],
            'connected': True,
            'profile': health.get('profile')
        })
    except Exception as e:
        logger.error(f"[Upstox Health] Error checking health: {e}")
        return jsonify({
            'healthy': False,
            'message': f'Health check error: {str(e)}',
            'connected': False
        }), 500

@app.route('/api/upstox/status', methods=['GET'])
def upstox_status():
    """Phase 1.2: Get Upstox connection status"""
    try:
        info = connection_manager.get_connection_info()
        
        # Get more detailed info
        has_api_key = bool(session.get('upstox_api_key'))
        has_api_secret = bool(session.get('upstox_api_secret'))
        has_token = bool(session.get('upstox_access_token'))
        
        info['debug'] = {
            'has_api_key': has_api_key,
            'has_api_secret': has_api_secret,
            'has_token': has_token,
            'session_keys': list(session.keys())
        }
        
        # Double-check connection status and get error details if failed
        is_connected = connection_manager.is_connected()
        info['connected'] = is_connected
        
        # If not connected but token exists, try to get the error reason
        if not is_connected and has_token:
            client = connection_manager.get_client()
            if client:
                try:
                    profile = client.get_profile()
                    if 'error' in profile:
                        info['connection_error'] = profile.get('error', 'Unknown error')
                        info['connection_error_details'] = profile
                except Exception as e:
                    info['connection_error'] = f'Exception checking connection: {str(e)}'
        elif is_connected:
            client = connection_manager.get_client()
            if client:
                profile = client.get_profile()
                if 'error' not in profile:
                    info['profile'] = profile
                else:
                    info['connected'] = False
                    info['connection_error'] = profile.get('error', 'Unknown error')
                    info['connection_error_details'] = profile
        
        return jsonify(info)
    except Exception as e:
        logger.error(f"[Phase 1.2] Status check error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'connected': False,
            'error': str(e)
        }), 500

@app.route('/api/upstox/test', methods=['GET'])
def test_upstox_connection():
    """Phase 1.2: Test Upstox connection"""
    client = connection_manager.get_client()
    if not client:
        return jsonify({'status': 'error', 'message': 'Not connected. Please connect first.'}), 400
    
    try:
        profile = client.get_profile()
        if 'error' in profile:
            logger.warning(f"[Phase 1.2] Connection test failed: {profile.get('error')}")
            return jsonify({'status': 'error', 'message': profile['error']}), 400
        
        logger.info("[Phase 1.2] Connection test successful")
        return jsonify({
            'status': 'success',
            'message': 'Connection is active',
            'profile': profile
        })
    except Exception as e:
        logger.error(f"[Phase 1.2] Connection test error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/upstox/verify-redirect-uri', methods=['POST'])
def verify_redirect_uri():
    """Verify redirect URI format and provide detailed instructions"""
    try:
        data = request.get_json() or {}
        redirect_uri = (data.get('redirect_uri') or '').strip()
        api_key = (data.get('api_key') or '').strip()
        
        if not redirect_uri:
            redirect_uri = 'http://localhost:5000/callback'
        
        # Validate format
        is_valid, error_msg = connection_manager.validate_redirect_uri(redirect_uri)
        
        if not is_valid:
            return jsonify({
                'status': 'error',
                'message': f'Invalid redirect URI format: {error_msg}',
                'redirect_uri': redirect_uri,
                'suggested': 'http://localhost:5000/callback'
            }), 400
        
        # Provide detailed instructions
        instructions = {
            'step1': 'https://account.upstox.com/developer/apps',
            'step2': f'Find your app (API Key: {api_key[:8] + "..." if api_key else "your API key"})',
            'step3': 'Click Edit/Settings on your app',
            'step4': 'In "Redirect URI(s)" field, add EXACTLY:',
            'redirect_uri': redirect_uri,
            'step5': 'Save the changes',
            'step6': 'Come back and click Connect again',
            'important_notes': [
                'URI must match EXACTLY (including http:// and /callback)',
                'No trailing spaces or extra characters',
                'Case-sensitive',
                'Must end with /callback'
            ]
        }
        
        return jsonify({
            'status': 'success',
            'message': 'Redirect URI format is valid',
            'redirect_uri': redirect_uri,
            'instructions': instructions
        })
    except Exception as e:
        logger.error(f"Error verifying redirect URI: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/upstox/debug-info', methods=['GET'])
def get_debug_info():
    """Get debug information about current connection state"""
    try:
        info = {
            'session_has_api_key': bool(session.get('upstox_api_key')),
            'session_has_api_secret': bool(session.get('upstox_api_secret')),
            'session_redirect_uri': session.get('upstox_redirect_uri'),
            'is_connected': connection_manager.is_connected(),
            'suggested_redirect_uri': 'http://localhost:5000/callback'
        }
        
        # Try to get current port
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            info['detected_local_ip'] = local_ip
            info['alternative_redirect_uri'] = f'http://{local_ip}:5000/callback'
        except:
            pass
        
        return jsonify(info)
    except Exception as e:
        logger.error(f"Error getting debug info: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/upstox/orders', methods=['GET'])
def get_orders():
    """Get order history from Upstox - formatted for dashboard"""
    client = _get_upstox_client()
    if not client:
        return jsonify({'error': 'Upstox not connected. Please connect first.'}), 400
    try:
        logger.info("[Orders] Fetching orders from Upstox...")
        orders = client.get_orders()
        logger.info(f"[Orders] Received {len(orders)} orders from Upstox")
        
        if not orders:
            return jsonify([])
        
        # Format orders for dashboard display
        formatted = []
        for order in orders:
            # Extract order data - handle different field names
            order_id = order.get('order_id') or order.get('orderId') or order.get('order_id') or 'N/A'
            symbol = (order.get('tradingsymbol') or 
                     order.get('trading_symbol') or
                     order.get('symbol') or 
                     order.get('instrument_key', '').split('|')[-1] if order.get('instrument_key') else 'N/A')
            
            transaction_type = order.get('transaction_type') or order.get('type') or 'N/A'
            quantity = float(order.get('quantity', 0) or order.get('qty', 0) or 0)
            price = float(order.get('price', 0) or order.get('limit_price', 0) or order.get('trigger_price', 0) or 0)
            status = order.get('status') or order.get('order_status') or 'PENDING'
            order_type = order.get('order_type') or order.get('product') or 'MARKET'
            timestamp = order.get('order_timestamp') or order.get('timestamp') or order.get('order_time') or ''
            
            # Clean symbol
            if symbol and symbol != 'N/A':
                if '|' in str(symbol):
                    symbol = str(symbol).split('|')[-1]
                symbol = str(symbol).replace('NSE_EQ|', '').replace('BSE_EQ|', '')
            
            formatted.append({
                'order_id': str(order_id),
                'symbol': symbol,
                'transaction_type': transaction_type.upper(),
                'quantity': quantity,
                'price': price,
                'status': status.upper(),
                'order_type': order_type,
                'timestamp': timestamp,
                'product': order.get('product', 'MIS')
            })
        
        logger.info(f"[Orders] Returning {len(formatted)} formatted orders")
        return jsonify(formatted)
    except Exception as e:
        logger.error(f"[Orders] Error fetching orders: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders/<order_id>', methods=['GET'])
def get_order_details(order_id):
    """Phase 2.2: Get detailed order information"""
    try:
        # Phase 2.5: Use trading mode manager
        mode_manager = get_trading_mode_manager()
        paper_mode = mode_manager.is_paper_mode()
        
        if paper_mode:
            paper_manager = get_paper_trading_manager()
            orders = paper_manager.get_orders()
            order = next((o for o in orders if o.get('order_id') == order_id), None)
            if order:
                return jsonify(order)
            return jsonify({'error': 'Order not found'}), 404
        else:
            # Live trading - fetch from Upstox
            client = _get_upstox_client()
            if not client:
                return jsonify({'error': 'Upstox not connected'}), 400
            
            orders = client.get_orders()
            order = next((o for o in orders if str(o.get('order_id')) == str(order_id) or str(o.get('orderId')) == str(order_id)), None)
            if order:
                return jsonify(order)
            return jsonify({'error': 'Order not found'}), 404
            
    except Exception as e:
        logger.error(f"Error getting order details: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders/<order_id>/modify', methods=['POST'])
def modify_order(order_id):
    """Phase 2.2: Modify an existing order"""
    try:
        data = request.json or {}
        quantity = data.get('quantity')
        price = data.get('price')
        order_type = data.get('order_type')
        
        # Phase 2.5: Use trading mode manager
        mode_manager = get_trading_mode_manager()
        paper_mode = mode_manager.is_paper_mode()
        
        if paper_mode:
            paper_manager = get_paper_trading_manager()
            result = paper_manager.modify_order(
                order_id=order_id,
                quantity=quantity,
                price=price,
                order_type=order_type
            )
            if result.get('status') == 'error':
                return jsonify(result), 400
            return jsonify(result)
        else:
            # Live trading - modify via Upstox API
            client = _get_upstox_client()
            if not client:
                return jsonify({'error': 'Upstox not connected'}), 400
            
            # Upstox modify order API call
            # Note: Upstox API may have different endpoint for modification
            result = client.modify_order(
                order_id=order_id,
                quantity=quantity,
                price=price,
                order_type=order_type
            )
            if result.get('error'):
                return jsonify(result), 400
            return jsonify({'status': 'success', 'message': 'Order modified successfully', 'order': result})
            
    except Exception as e:
        logger.error(f"Error modifying order: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders/<order_id>/cancel', methods=['POST'])
def cancel_order(order_id):
    """Phase 2.2: Cancel an existing order"""
    try:
        # Phase 2.5: Use trading mode manager
        mode_manager = get_trading_mode_manager()
        paper_mode = mode_manager.is_paper_mode()
        
        if paper_mode:
            paper_manager = get_paper_trading_manager()
            result = paper_manager.cancel_order(order_id)
            if result.get('status') == 'error':
                return jsonify(result), 400
            return jsonify(result)
        else:
            # Live trading - cancel via Upstox API
            client = _get_upstox_client()
            if not client:
                return jsonify({'error': 'Upstox not connected'}), 400
            
            result = client.cancel_order(order_id)
            if result.get('error'):
                return jsonify(result), 400
            return jsonify({'status': 'success', 'message': 'Order cancelled successfully'})
            
    except Exception as e:
        logger.error(f"Error cancelling order: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/upstox/place_order', methods=['POST'])
def place_order():
    """Phase 2.5: Place order through Upstox (real trading) or Paper Trading (simulation)"""
    # Phase 2.5: Use trading mode manager
    mode_manager = get_trading_mode_manager()
    paper_mode = mode_manager.is_paper_mode()
    
    data = request.json
    ticker = data.get('ticker')
    transaction_type = data.get('transaction_type')  # 'BUY' or 'SELL'
    quantity = int(data.get('quantity', 0))
    order_type = data.get('order_type', 'MARKET')  # 'MARKET', 'LIMIT', 'SL', 'SL-M'
    price = data.get('price')  # For LIMIT orders
    product = data.get('product', 'D')  # 'D' for Delivery, 'I' for Intraday
    
    if not ticker or not transaction_type or quantity <= 0:
        return jsonify({'error': 'Invalid order parameters: ticker, transaction_type, and quantity > 0 required'}), 400
    
    # Validate order type and price
    if order_type in ['LIMIT', 'SL'] and not price:
        return jsonify({'error': f'Price required for {order_type} orders'}), 400
    
    # Extract symbol from ticker
    symbol = ticker.replace('.NS', '').replace('.BO', '').replace('^', '').strip()
    
    # PAPER TRADING MODE
    if paper_mode:
        try:
            paper_manager = get_paper_trading_manager()
            
            # Get current market price for execution simulation
            current_price = price if price else None
            if not current_price:
                # Try to get from Upstox if connected, otherwise use price from request
                client = _get_upstox_client()
                if client:
                    try:
                        from src.web.instrument_master import InstrumentMaster
                        from src.web.market_data import MarketDataClient
                        inst_master = InstrumentMaster()
                        market_client = MarketDataClient(client.access_token)
                        inst_key = inst_master.get_instrument_key(ticker)
                        if inst_key:
                            quote = market_client.get_quote(inst_key)
                            if quote:
                                current_price = quote.get('ltp') or quote.get('last_price')
                    except:
                        pass
            
            if not current_price:
                current_price = price if price else 100.0  # Fallback
            
            result = paper_manager.place_order(
                symbol=symbol,
                ticker=ticker,
                transaction_type=transaction_type,
                quantity=quantity,
                order_type=order_type,
                price=price,
                trigger_price=data.get('trigger_price'),
                product=product,
                current_market_price=current_price
            )
            
            if result.get('status') == 'error':
                return jsonify(result), 400
            
            return jsonify({
                'status': 'success',
                'message': result.get('message', '✅ PAPER ORDER EXECUTED!'),
                'order': result.get('order'),
                'paper_trading': True,
                'portfolio': paper_manager.get_portfolio_summary()
            })
        except Exception as e:
            logger.error(f"[PaperTrading] Error placing paper order: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({'status': 'error', 'error': f'Paper order failed: {str(e)}'}), 500
    
    # LIVE TRADING MODE
    client = _get_upstox_client()
    if not client:
        return jsonify({'error': 'Upstox not connected. Please connect first.'}), 400
    
    try:
        result = client.place_order(
            ticker=ticker,
            transaction_type=transaction_type,
            quantity=quantity,
            order_type=order_type,
            price=price,
            product=product
        )
        
        # Check if order was successful
        if 'error' in result:
            error_msg = result.get('error', 'Order failed')
            hint = None
            if 'instrument' in error_msg.lower() or 'not found' in error_msg.lower():
                hint = f"Ticker '{ticker}' not found. Try: RELIANCE.NS, TCS.NS, HDFCBANK.NS, etc. (must end with .NS for NSE)"
            return jsonify({'status': 'error', 'message': error_msg, 'details': result, 'hint': hint}), 400
        
        return jsonify({
            'status': 'success',
            'message': '✅ LIVE ORDER PLACED SUCCESSFULLY!',
            'order': result,
            'paper_trading': False
        })
    except ValueError as e:
        # Instrument key not found
        error_msg = str(e)
        hint = f"Ticker '{ticker}' not found in instrument master. Supported format: RELIANCE.NS, TCS.NS, HDFCBANK.NS (must end with .NS for NSE stocks)"
        return jsonify({'status': 'error', 'error': error_msg, 'hint': hint}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'error': f'Order placement failed: {str(e)}'}), 500

@app.route('/api/stocks/refresh', methods=['POST'])
def refresh_stocks_universe():
    """Refresh instrument master and stock universe (NSE/BSE). Call after connecting Upstox."""
    try:
        from src.web.instrument_master import get_instrument_master
        from src.web.stock_universe import get_stock_universe
        im = get_instrument_master()
        im.refresh_cache()
        su = get_stock_universe()
        su._build_universe(force_refresh=True)
        info = su.get_universe_info()
        return jsonify({
            'status': 'success',
            'message': 'Instruments and stock universe refreshed',
            'total_stocks': info.get('total_stocks', 0),
            'nse_stocks': info.get('nse_stocks', 0),
            'bse_stocks': info.get('bse_stocks', 0),
        })
    except Exception as e:
        logger.exception("Refresh stocks universe failed")
        return jsonify({'status': 'error', 'error': str(e)}), 500


@app.route('/api/stocks/universe', methods=['GET'])
def get_stocks_universe():
    """Get paginated NSE/BSE stock list. Query: exchange (NSE|BSE), limit, offset, search."""
    exchange = request.args.get('exchange') or None
    try:
        limit = min(int(request.args.get('limit', 500)), 2000)
    except (TypeError, ValueError):
        limit = 500
    try:
        offset = max(0, int(request.args.get('offset', 0)))
    except (TypeError, ValueError):
        offset = 0
    search = request.args.get('search', '').strip() or None
    try:
        su = get_stock_universe()
        result = su.get_stocks_page(exchange=exchange, limit=limit, offset=offset, search=search)
        return jsonify(result)
    except Exception as e:
        logger.exception("Stocks universe API failed")
        return jsonify({"stocks": [], "total": 0, "error": str(e)}), 500


@app.route('/api/top_stocks')
def get_top_stocks():
    """Get top performing stocks from backtest"""
    # Based on our analysis - expanded list
    top_stocks = [
        {'ticker': 'LT.NS', 'name': 'Larsen & Toubro', 'return': 4.00, 'sharpe': 1.48},
        {'ticker': 'HDFCBANK.NS', 'name': 'HDFC Bank', 'return': 2.77, 'sharpe': 2.93},
        {'ticker': 'BAJFINANCE.NS', 'name': 'Bajaj Finance', 'return': 2.55, 'sharpe': 0.91},
        {'ticker': 'INFY.NS', 'name': 'Infosys', 'return': 1.91, 'sharpe': 1.23},
        {'ticker': 'KOTAKBANK.NS', 'name': 'Kotak Mahindra Bank', 'return': 1.56, 'sharpe': 0.91},
        {'ticker': 'TCS.NS', 'name': 'TCS', 'return': 1.50, 'sharpe': 0.85},
        {'ticker': 'RELIANCE.NS', 'name': 'Reliance Industries', 'return': 1.20, 'sharpe': 0.65},
        {'ticker': 'ICICIBANK.NS', 'name': 'ICICI Bank', 'return': 0.42, 'sharpe': 0.16},
        {'ticker': 'SBIN.NS', 'name': 'State Bank of India', 'return': 1.08, 'sharpe': 0.25},
        {'ticker': 'ITC.NS', 'name': 'ITC', 'return': 0.02, 'sharpe': 0.03},
        {'ticker': '^NSEI', 'name': 'NIFTY 50', 'return': 0.00, 'sharpe': 0.00},
        {'ticker': '^NSEBANK', 'name': 'Bank Nifty', 'return': 0.00, 'sharpe': 0.00},
    ]
    return jsonify(top_stocks)


def _holding_to_ticker_and_key(h: dict) -> Tuple[Optional[str], Optional[str]]:
    """Extract (ticker, instrument_key) from holding. instrument_key from Upstox is used for historical API."""
    instrument_key = h.get('instrument_key') or h.get('instrumentKey') or ''
    inst_key_upper = (instrument_key or '').upper()
    symbol = (h.get('tradingsymbol') or h.get('trading_symbol') or h.get('symbol') or
              h.get('name') or h.get('company_name') or '')
    if not symbol or symbol == 'N/A':
        if instrument_key:
            parts = str(instrument_key).split('|')
            symbol = parts[-1] if len(parts) > 1 else parts[0]
        else:
            return None, None
    symbol = str(symbol).strip()
    if '|' in symbol:
        symbol = symbol.split('|')[-1]
    symbol = symbol.replace('NSE_EQ|', '').replace('BSE_EQ|', '').replace('NSE_', '').replace('BSE_', '')
    if not symbol:
        return None, None
    if symbol.startswith('^'):
        return symbol, instrument_key if instrument_key else None
    if '.' in symbol:
        ticker = symbol
    elif 'BSE' in inst_key_upper or 'BSE_EQ' in inst_key_upper:
        ticker = f"{symbol}.BO"
    else:
        ticker = f"{symbol}.NS"
    return ticker, instrument_key if instrument_key else None


def _holding_to_ticker(h: dict) -> Optional[str]:
    """Extract normalized ticker from holding (e.g. RELIANCE.NS, BSE.BO)."""
    t, _ = _holding_to_ticker_and_key(h)
    return t


@app.route('/api/signals/tickers')
def get_signals_tickers():
    """
    Get ticker list for trading signals. Query: source=demat|watchlist|both.
    When Upstox connected and source includes demat: returns holdings tickers + instrument_keys for direct Upstox API.
    """
    source = request.args.get('source', 'demat').lower()
    if source not in ('demat', 'watchlist', 'both'):
        source = 'demat'
    tickers = []
    ticker_keys = {}  # ticker -> instrument_key for demat holdings (bypasses instrument master)
    seen = set()
    client = _get_upstox_client()
    if source in ('demat', 'both') and client and client.access_token:
        try:
            holdings = client.get_holdings()
            if holdings:
                for h in holdings:
                    t, inst_key = _holding_to_ticker_and_key(h)
                    if t and t not in seen:
                        tickers.append(t)
                        seen.add(t)
                        if inst_key:
                            ticker_keys[t] = inst_key
        except Exception as e:
            logger.warning(f"[Signals/Tickers] Holdings fetch failed: {e}")
    if source in ('watchlist', 'both'):
        wl = watchlist_manager.get_watchlist()
        for t in wl:
            t = str(t).strip()
            if t and t not in seen:
                tickers.append(t)
                seen.add(t)
    if not tickers and source == 'demat':
        wl = watchlist_manager.get_watchlist()
        tickers = wl[:20] if wl else []
    # Fallback: ensure we always return some tickers for signals to display
    _popular = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'ITC.NS', 'LT.NS', 'HINDUNILVR.NS']
    if not tickers:
        tickers = _popular
    return jsonify({'tickers': tickers, 'ticker_keys': ticker_keys, 'source': source})


@app.route('/api/signals/cache-status')
def get_signals_cache_status():
    """Get pre-computed signal cache status (count, last_updated)."""
    try:
        from src.web.signal_cache import get_cache_meta
        meta = get_cache_meta()
        return jsonify(meta)
    except Exception as e:
        return jsonify({'count': 0, 'error': str(e)})


@app.route('/api/holdings')
def get_holdings():
    """Get holdings data from Upstox (real account data)"""
    client = _get_upstox_client()
    if not client:
        logger.warning("[Holdings] Upstox not connected")
        return jsonify({'error': 'Upstox not connected. Please connect first.'}), 400
    
    try:
        logger.info("[Holdings] Fetching holdings from Upstox...")
        holdings = client.get_holdings()
        logger.info(f"[Holdings] Received {len(holdings)} holdings from Upstox")
        
        if not holdings:
            logger.info("[Holdings] No holdings found (empty list)")
            return jsonify([])
        
        # Transform Upstox format to UI format
        formatted = []
        for h in holdings:
            # Log first holding for debugging
            if len(formatted) == 0:
                logger.info(f"[Holdings] Sample raw holding data: {h}")
            
            # Try multiple field name variations (Upstox API may use different names)
            quantity = float(h.get('quantity', 0) or h.get('qty', 0) or h.get('net_quantity', 0) or 0)
            avg_price = float(h.get('average_price', 0.0) or h.get('avg_price', 0.0) or h.get('average_price', 0.0) or 0.0)
            last_price = float(h.get('last_price', 0.0) or h.get('ltp', 0.0) or h.get('close_price', 0.0) or 0.0)
            
            # If last_price is 0, try to get from other fields
            if last_price == 0:
                last_price = float(h.get('ltp', 0.0) or h.get('current_price', 0.0) or 0.0)
            
            current_value = quantity * last_price
            
            # Calculate P&L - Upstox may return P&L in different formats
            pnl_data = h.get('pnl', {})
            if isinstance(pnl_data, dict):
                # Try different P&L field names
                day_pnl = float(pnl_data.get('realized', 0.0) or pnl_data.get('unrealized', 0.0) or 
                               pnl_data.get('day_pnl', 0.0) or pnl_data.get('realised', 0.0) or 0.0)
            else:
                day_pnl = float(h.get('day_pnl', 0.0) or h.get('realized_pnl', 0.0) or 0.0)
            
            # Calculate overall P&L
            invested_value = quantity * avg_price
            overall_pnl = current_value - invested_value
            overall_pnl_pct = (overall_pnl / invested_value) * 100 if invested_value > 0 else 0.0
            day_pnl_pct = (day_pnl / current_value) * 100 if current_value > 0 else 0.0
            
            # Get symbol - try multiple field names and formats
            symbol = None
            
            # Try direct field names first
            symbol = (h.get('tradingsymbol') or 
                     h.get('trading_symbol') or
                     h.get('symbol') or 
                     h.get('name') or
                     h.get('company_name') or
                     h.get('isin'))
            
            # If still None, try extracting from instrument_key
            if not symbol or symbol == 'N/A':
                instrument_key = h.get('instrument_key') or h.get('instrumentKey') or ''
                if instrument_key:
                    # Format: "NSE_EQ|INE467B01029" or "NSE_EQ|FSL" or just "FSL"
                    parts = str(instrument_key).split('|')
                    if len(parts) > 1:
                        # Try to get symbol from second part or use first part
                        symbol = parts[-1] if parts[-1] else parts[0]
                    else:
                        symbol = parts[0] if parts[0] else None
            
            # If still None, try extracting from other fields
            if not symbol or symbol == 'N/A':
                # Try to extract from exchange_token or other identifiers
                exchange_token = h.get('exchange_token') or h.get('exchangeToken') or ''
                if exchange_token:
                    symbol = str(exchange_token).split('|')[-1] if '|' in str(exchange_token) else exchange_token
            
            # Final fallback
            if not symbol:
                symbol = 'N/A'
            
            # Clean up symbol - remove exchange prefix if present
            if symbol and symbol != 'N/A':
                # Remove common prefixes like "NSE_EQ|", "BSE_EQ|", etc.
                if '|' in str(symbol):
                    symbol = str(symbol).split('|')[-1]
                # Remove exchange codes at start
                symbol = str(symbol).replace('NSE_EQ|', '').replace('BSE_EQ|', '').replace('NSE_', '').replace('BSE_', '')
            
            logger.debug(f"[Holdings] Extracted symbol: {symbol} from holding: {list(h.keys())}")
            
            formatted.append({
                'symbol': symbol,
                'qty': quantity,
                'avg_price': avg_price,
                'ltp': last_price,
                'current_value': current_value,
                'day_pnl': day_pnl,
                'day_pnl_pct': day_pnl_pct,
                'overall_pnl': overall_pnl,
                'overall_pnl_pct': overall_pnl_pct
            })
        
        logger.info(f"[Holdings] Returning {len(formatted)} formatted holdings")
        return jsonify(formatted)
    except Exception as e:
        logger.error(f"[Holdings] Error fetching holdings: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/positions')
def get_positions():
    """Get positions data from Upstox - formatted for dashboard display"""
    client = _get_upstox_client()
    if not client:
        return jsonify({'error': 'Upstox not connected. Please connect first.'}), 400
    try:
        logger.info("[Positions] Fetching positions from Upstox...")
        positions = client.get_positions()
        logger.info(f"[Positions] Received {len(positions)} positions from Upstox")
        
        if not positions:
            return jsonify([])
        
        # Format positions for dashboard display
        formatted = []
        for pos in positions:
            # Extract position data - handle different field names
            quantity = float(pos.get('quantity', 0) or pos.get('qty', 0) or pos.get('net_quantity', 0) or 0)
            avg_price = float(pos.get('average_price', 0.0) or pos.get('avg_price', 0.0) or pos.get('price', 0.0) or 0.0)
            last_price = float(pos.get('last_price', 0.0) or pos.get('ltp', 0.0) or pos.get('current_price', 0.0) or 0.0)
            
            # Determine buy/sell from quantity (positive = buy/long, negative = sell/short)
            is_buy = quantity >= 0
            transaction_type = 'BUY' if is_buy else 'SELL'
            
            # Calculate P&L
            invested_value = abs(quantity) * avg_price
            current_value = abs(quantity) * last_price
            
            # P&L calculation depends on position type
            if is_buy:
                # Long position: profit when price goes up
                pnl = current_value - invested_value
            else:
                # Short position: profit when price goes down
                pnl = invested_value - current_value
            
            pnl_pct = (pnl / invested_value * 100) if invested_value > 0 else 0.0
            
            # Get symbol
            symbol = (pos.get('tradingsymbol') or 
                     pos.get('trading_symbol') or
                     pos.get('symbol') or 
                     pos.get('name') or 'N/A')
            
            # Clean symbol
            if symbol and symbol != 'N/A':
                if '|' in str(symbol):
                    symbol = str(symbol).split('|')[-1]
                symbol = str(symbol).replace('NSE_EQ|', '').replace('BSE_EQ|', '')
            
            # Get product type
            product = pos.get('product', 'MIS')  # MIS, CNC, NRML
            
            # Get exchange
            exchange = pos.get('exchange', 'NSE')
            
            formatted.append({
                'symbol': symbol,
                'ticker': f"{symbol}.NS" if exchange == 'NSE' else f"{symbol}.BO",
                'quantity': quantity,
                'net_quantity': abs(quantity),  # Absolute quantity for display
                'transaction_type': transaction_type,
                'product': product,
                'exchange': exchange,
                'entry_price': avg_price,
                'average_price': avg_price,
                'last_price': last_price,
                'ltp': last_price,
                'current_price': last_price,
                'invested_value': invested_value,
                'current_value': current_value,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'overall_pnl': pnl,
                'overall_pnl_pct': pnl_pct,
                'intraday_pnl': pnl,  # For intraday positions
                'status': 'OPEN'  # Positions are always open
            })
        
        logger.info(f"[Positions] Returning {len(formatted)} formatted positions")
        return jsonify(formatted)
    except Exception as e:
        logger.error(f"[Positions] Error fetching positions: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/daily-positions')
def get_daily_positions():
    """Get daily positions with filtering"""
    try:
        filter_type = request.args.get('filter', 'all')  # all, intraday, today, historical
        date_str = request.args.get('date')  # YYYY-MM-DD format
        symbol = request.args.get('symbol')
        
        filter_date = None
        if date_str:
            try:
                filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        tracker = get_daily_tracker()
        positions = tracker.get_positions(
            filter_type=filter_type,
            date_filter=filter_date,
            symbol=symbol
        )
        
        return jsonify({
            'status': 'success',
            'filter': filter_type,
            'count': len(positions),
            'positions': [pos.to_dict() for pos in positions]
        })
    except Exception as e:
        logger.error(f"[DailyPositions] Error getting daily positions: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/daily-positions/stats')
def get_daily_position_stats():
    """Get daily position statistics"""
    try:
        date_str = request.args.get('date')  # YYYY-MM-DD format
        
        filter_date = None
        if date_str:
            try:
                filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        tracker = get_daily_tracker()
        stats = tracker.get_daily_stats(target_date=filter_date)
        
        return jsonify({
            'status': 'success',
            'stats': stats
        })
    except Exception as e:
        logger.error(f"[DailyPositions] Error getting daily stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/daily-positions/sync', methods=['POST'])
def sync_daily_positions():
    """Sync daily positions from Upstox"""
    try:
        client = _get_upstox_client()
        if not client:
            return jsonify({'error': 'Upstox not connected. Please connect first.'}), 400
        
        # Get current positions from Upstox
        upstox_positions = client.get_positions()
        
        # Sync with daily tracker
        tracker = get_daily_tracker()
        tracker.sync_from_upstox(upstox_positions)
        
        return jsonify({
            'status': 'success',
            'message': f'Synced {len(upstox_positions)} positions from Upstox',
            'synced_count': len(upstox_positions)
        })
    except Exception as e:
        logger.error(f"[DailyPositions] Error syncing positions: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/financial-data/<ticker>')
def get_financial_data(ticker):
    """Get financial data for a ticker"""
    try:
        collector = get_financial_collector()
        data = collector.get_all_financial_data(ticker)
        return jsonify({
            'status': 'success',
            'data': data
        })
    except Exception as e:
        logger.error(f"[FinancialData] Error getting financial data for {ticker}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/news-sentiment/<ticker>')
def get_news_sentiment(ticker):
    """Get news and sentiment for a ticker"""
    try:
        collector = get_news_collector()
        data = collector.get_news_sentiment(ticker)
        return jsonify({
            'status': 'success',
            'data': data
        })
    except Exception as e:
        logger.error(f"[NewsSentiment] Error getting news sentiment for {ticker}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/data-pipeline/<ticker>')
def get_pipeline_data(ticker):
    """Get all data from pipeline for a ticker"""
    try:
        pipeline = get_data_pipeline()
        include_news = request.args.get('include_news', 'true').lower() == 'true'
        include_financials = request.args.get('include_financials', 'true').lower() == 'true'
        
        data = pipeline.collect_all_data(
            ticker,
            include_news=include_news,
            include_financials=include_financials
        )
        
        return jsonify({
            'status': 'success',
            'data': data
        })
    except Exception as e:
        logger.error(f"[DataPipeline] Error getting pipeline data for {ticker}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/upstox/disconnect', methods=['POST'])
def disconnect_upstox():
    """Disconnect Upstox (clears tokens from session)"""
    session.pop('upstox_connected', None)
    session.pop('upstox_access_token', None)
    session.pop('upstox_api_key', None)
    session.pop('upstox_api_secret', None)
    session.pop('upstox_redirect_uri', None)
    return jsonify({'status': 'success', 'message': 'Disconnected'})

@app.route('/api/network_info')
def get_network_info():
    """Get network info for multi-device access (fast - defaults to localhost)"""
    port = int(os.getenv("FLASK_PORT", "5000"))
    
    # Fast response: default to localhost immediately
    # Network IP detection is slow and can cause timeouts
    # Return localhost as default, user can manually enter network IP if needed
    return jsonify({
        'local_ip': '127.0.0.1',
        'port': port,
        'local_url': f'http://localhost:{port}',
        'network_url': f'http://localhost:{port}',  # Default to localhost
        'redirect_uri': f'http://localhost:{port}/callback'  # Fast default
    })

@app.route('/api/trading-mode', methods=['GET'])
def get_trading_mode():
    """Phase 2.5: Get current trading mode"""
    try:
        mode_manager = get_trading_mode_manager()
        mode_info = mode_manager.get_status()
        return jsonify(mode_info)
    except Exception as e:
        logger.error(f"Error getting trading mode: {e}", exc_info=True)
        # Return default mode info on error
        return jsonify({
            'current_mode': 'paper',
            'is_paper': True,
            'is_live': False,
            'error': str(e)
        }), 200  # Return 200 with error in response instead of 500

@app.route('/api/trading-mode', methods=['POST'])
def set_trading_mode():
    """Phase 2.5: Set trading mode"""
    try:
        data = request.json or {}
        mode = data.get('mode')
        user_confirmation = data.get('user_confirmation', False)
        
        if not mode:
            return jsonify({'error': 'Mode is required'}), 400
        
        mode_manager = get_trading_mode_manager()
        result = mode_manager.set_mode(mode, user_confirmation)
        
        if result.get('status') == 'error':
            return jsonify(result), 400
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error setting trading mode: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/portfolio/history', methods=['GET'])
def get_portfolio_history():
    """Phase 2.4: Get portfolio history"""
    try:
        days = int(request.args.get('days', 30))
        holdings_db = get_holdings_db()
        history = holdings_db.get_portfolio_history(days)
        return jsonify(history)
    except Exception as e:
        logger.error(f"Error getting portfolio history: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/portfolio/snapshot', methods=['POST'])
def record_portfolio_snapshot():
    """Phase 2.4: Manually record a portfolio snapshot"""
    try:
        # Get holdings
        holdings = []
        cash_balance = 0
        
        # Try Upstox first
        client = _get_upstox_client()
        if client:
            try:
                holdings = client.get_holdings()
            except:
                pass
        
        # Fallback to paper trading
        if not holdings:
            try:
                paper_manager = get_paper_trading_manager()
                holdings = paper_manager.get_positions()
                portfolio_summary = paper_manager.get_portfolio_summary()
                cash_balance = portfolio_summary.get('cash_balance', 0)
            except:
                pass
        
        # Record snapshot
        holdings_db = get_holdings_db()
        snapshot_id = holdings_db.record_portfolio_snapshot(
            holdings=holdings,
            cash_balance=cash_balance
        )
        
        if snapshot_id > 0:
            return jsonify({
                'status': 'success',
                'message': 'Portfolio snapshot recorded',
                'snapshot_id': snapshot_id
            })
        else:
            return jsonify({'error': 'Failed to record snapshot'}), 500
            
    except Exception as e:
        logger.error(f"Error recording portfolio snapshot: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/portfolio/summary', methods=['GET'])
def get_portfolio_summary():
    """
    Get portfolio summary with Day P&L
    Combines holdings, positions, and paper trading data
    """
    try:
        mode_manager = get_trading_mode_manager()
        paper_mode = mode_manager.is_paper_mode()
        
        # Get data based on trading mode
        if paper_mode:
            # Paper trading mode
            paper_manager = get_paper_trading_manager()
            summary = paper_manager.get_portfolio_summary()
            
            # Get today's P&L from holdings database
            holdings_db = get_holdings_db()
            latest_snapshot = holdings_db.get_latest_snapshot()
            
            day_pnl = latest_snapshot.get('daily_pnl', 0) if latest_snapshot else 0
            
            return jsonify({
                'status': 'success',
                'mode': 'paper',
                'total_value': summary.get('total_value', 0),
                'cash_balance': summary.get('cash_balance', 0),
                'position_value': summary.get('position_value', 0),
                'invested_value': summary.get('invested_value', 0),
                'total_pnl': summary.get('total_pnl', 0),
                'total_pnl_pct': summary.get('total_pnl_pct', 0),
                'day_pnl': day_pnl,
                'day_pnl_pct': (day_pnl / summary.get('total_value', 1) * 100) if summary.get('total_value', 0) > 0 else 0,
                'num_positions': summary.get('num_positions', 0)
            })
        else:
            # Live trading mode - get from Upstox
            client = _get_upstox_client()
            if not client:
                return jsonify({'error': 'Upstox not connected'}), 400
            
            # Get holdings
            holdings = client.get_holdings()
            positions = client.get_positions()
            
            # Calculate portfolio value
            total_invested = 0
            total_current_value = 0
            
            for holding in holdings:
                qty = float(holding.get('quantity', 0))
                avg_price = float(holding.get('average_price', 0) or holding.get('buy_price', 0))
                current_price = float(holding.get('last_price', 0) or holding.get('ltp', 0))
                
                total_invested += qty * avg_price
                total_current_value += qty * current_price
            
            # Add positions
            for pos in positions:
                qty = float(pos.get('quantity', 0) or pos.get('net_quantity', 0))
                avg_price = float(pos.get('average_price', 0) or pos.get('buy_price', 0))
                current_price = float(pos.get('last_price', 0) or pos.get('ltp', 0))
                
                total_current_value += qty * current_price
                total_invested += qty * avg_price
            
            total_pnl = total_current_value - total_invested
            total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
            
            # Get Day P&L from holdings database
            holdings_db = get_holdings_db()
            latest_snapshot = holdings_db.get_latest_snapshot()
            day_pnl = latest_snapshot.get('daily_pnl', 0) if latest_snapshot else 0
            day_pnl_pct = (day_pnl / total_current_value * 100) if total_current_value > 0 else 0
            
            return jsonify({
                'status': 'success',
                'mode': 'live',
                'total_value': total_current_value,
                'invested_value': total_invested,
                'total_pnl': total_pnl,
                'total_pnl_pct': total_pnl_pct,
                'day_pnl': day_pnl,
                'day_pnl_pct': day_pnl_pct,
                'num_positions': len(holdings) + len(positions)
            })
            
    except Exception as e:
        logger.error(f"Error getting portfolio summary: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# ========================================
# STRATEGY API ENDPOINTS
# Phase 3: Advanced Quant Strategies
# ========================================

from src.web.strategies.strategy_manager import get_strategy_manager

@app.route('/api/strategies/available', methods=['GET'])
def get_available_strategies():
    """Get list of available trading strategies"""
    try:
        manager = get_strategy_manager()
        strategies = manager.get_available_strategies()
        
        # Get info for each strategy
        strategy_info = {}
        for name in strategies:
            strategy_info[name] = manager.get_strategy_info(name)
        
        return jsonify({
            'strategies': strategies,
            'active_strategy': manager.active_strategy,
            'details': strategy_info
        })
    except Exception as e:
        logger.error(f"Error getting strategies: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/strategies/set_active', methods=['POST'])
def set_active_strategy():
    """Set the active trading strategy"""
    try:
        data = request.json or {}
        strategy_name = data.get('strategy')
        
        if not strategy_name:
            return jsonify({'error': 'Strategy name required'}), 400
        
        manager = get_strategy_manager()
        success = manager.set_active_strategy(strategy_name)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Active strategy set to: {strategy_name}',
                'active_strategy': manager.active_strategy
            })
        else:
            return jsonify({'error': f'Strategy not found: {strategy_name}'}), 404
            
    except Exception as e:
        logger.error(f"Error setting active strategy: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/strategies/execute', methods=['POST'])
def execute_strategy():
    """
    Execute a trading strategy and get signal
    
    Request body:
    {
        "ticker": "RELIANCE.NS",
        "strategy": "ml" (optional, uses active if not specified),
        "method": "single" or "ensemble" (optional)
    }
    """
    try:
        data = request.json or {}
        ticker = data.get('ticker')
        strategy_name = data.get('strategy')  # Optional
        method = data.get('method', 'single')  # 'single' or 'ensemble'
        
        if not ticker:
            return jsonify({'error': 'Ticker required'}), 400
        
        # Get current market data
        try:
            # Try to get live price from Upstox if connected
            client = _get_upstox_client()
            current_price = None
            market_data = {}
            
            if client:
                from src.web.instrument_master import InstrumentMaster
                from src.web.market_data import MarketDataClient
                inst_master = InstrumentMaster()
                market_client = MarketDataClient(client.access_token)
                inst_key = inst_master.get_instrument_key(ticker)
                
                if inst_key:
                    quote = market_client.get_quote(inst_key)
                    if quote:
                        current_price = quote.get('ltp') or quote.get('last_price', 0)
            
            # Fallback: Try to get from Yahoo Finance cache
            if not current_price:
                prices_response = _get_cached_price(ticker)
                current_price = prices_response.get('price', 0)
            
            if not current_price or current_price == 0:
                return jsonify({'error': f'Could not get price for {ticker}'}), 400
            
            # Get historical features (simplified - you should load from your research module)
            # For now, calculate basic features
            from src.research.data import load_cached_csv
            from src.research.features import make_features
            
            try:
                df = load_cached_csv(ticker)
                if df is not None and not df.empty:
                    df_features = make_features(df)
                    latest = df_features.iloc[-1]
                    
                    market_data = {
                        'current_price': current_price,
                        'sma_10': latest.get('sma_10', current_price),
                        'sma_20': (latest.get('sma_10', 0) + latest.get('sma_50', 0)) / 2,  # Approximate
                        'sma_50': latest.get('sma_50', current_price),
                        'ema_20': latest.get('ema_20', current_price),
                        'rsi_14': latest.get('rsi_14', 50),
                        'macd': latest.get('macd', 0),
                        'macd_signal': latest.get('macd_signal', 0),
                        'macd_hist': latest.get('macd_hist', 0),
                        'ret_1': latest.get('ret_1', 0),
                        'ret_5': latest.get('ret_5', 0),
                        'vol_10': latest.get('vol_10', 0.01),
                        'volume': latest.get('volume', 0),
                    }
                    
                    # Calculate additional metrics
                    prices = df['close'].tail(20).tolist()
                    price_std = df['close'].tail(20).std()
                    market_data['price_std'] = price_std
                    market_data['bollinger_upper'] = market_data['sma_20'] + (2 * price_std)
                    market_data['bollinger_lower'] = market_data['sma_20'] - (2 * price_std)
                    
                    # 20-day momentum
                    if len(df) > 20:
                        market_data['ret_20'] = (current_price - df['close'].iloc[-21]) / df['close'].iloc[-21] if df['close'].iloc[-21] > 0 else 0
                    
                    # Simplified ADX (trend strength) - use volatility as proxy
                    market_data['adx'] = min(100, market_data['vol_10'] * 1000)
                    
            except Exception as e:
                logger.warning(f"Could not load historical features: {e}")
                # Use simplified data
                market_data = {
                    'current_price': current_price,
                    'sma_10': current_price,
                    'sma_20': current_price,
                    'sma_50': current_price,
                    'ema_20': current_price,
                    'rsi_14': 50,
                    'macd': 0,
                    'macd_signal': 0,
                    'macd_hist': 0,
                    'ret_1': 0,
                    'ret_5': 0,
                    'ret_20': 0,
                    'vol_10': 0.01,
                    'price_std': current_price * 0.02,
                    'bollinger_upper': current_price * 1.04,
                    'bollinger_lower': current_price * 0.96,
                    'adx': 25,
                    'volume': 0
                }
        
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return jsonify({'error': f'Error getting market data: {str(e)}'}), 500
        
        # Execute strategy
        manager = get_strategy_manager()
        
        if method == 'ensemble':
            # Use ensemble of all strategies
            ensemble_method = data.get('ensemble_method', 'weighted_average')
            result = manager.combine_strategies(market_data, method=ensemble_method)
        elif strategy_name:
            # Use specific strategy
            result = manager.execute_strategy(strategy_name, market_data)
        else:
            # Use active strategy
            result = manager.execute_active_strategy(market_data)
        
        return jsonify({
            'status': 'success',
            'ticker': ticker,
            'strategy_used': strategy_name or manager.active_strategy,
            'signal': result.signal,
            'confidence': round(result.confidence, 3),
            'entry_price': round(result.entry_price, 2),
            'stop_loss': round(result.stop_loss, 2),
            'target_1': round(result.target_1, 2),
            'target_2': round(result.target_2, 2),
            'current_price': round(current_price, 2),
            'metadata': result.metadata,
            'market_data': {
                k: round(v, 4) if isinstance(v, (int, float)) else v
                for k, v in market_data.items()
            }
        })
        
    except Exception as e:
        logger.error(f"Error executing strategy: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/strategies/compare', methods=['POST'])
def compare_strategies():
    """
    Compare all strategies for a given ticker
    
    Request body:
    {
        "ticker": "RELIANCE.NS"
    }
    """
    try:
        data = request.json or {}
        ticker = data.get('ticker')
        
        if not ticker:
            return jsonify({'error': 'Ticker required'}), 400
        
        # Get market data (reuse logic from execute_strategy)
        # For brevity, calling execute_strategy internally
        manager = get_strategy_manager()
        
        # Execute all strategies
        results = {}
        for strategy_name in manager.get_available_strategies():
            try:
                # Call execute_strategy endpoint logic
                response = execute_strategy()
                response_data = response.get_json()
                
                if response_data.get('status') == 'success':
                    results[strategy_name] = {
                        'signal': response_data['signal'],
                        'confidence': response_data['confidence'],
                        'entry_price': response_data['entry_price']
                    }
            except Exception as e:
                logger.error(f"Error executing {strategy_name}: {e}")
        
        # Determine consensus
        signals = [r['signal'] for r in results.values()]
        signal_counts = {'BUY': signals.count('BUY'), 'SELL': signals.count('SELL'), 'HOLD': signals.count('HOLD')}
        consensus = max(signal_counts, key=signal_counts.get)
        
        return jsonify({
            'status': 'success',
            'ticker': ticker,
            'strategies': results,
            'consensus': consensus,
            'signal_counts': signal_counts
        })
        
    except Exception as e:
        logger.error(f"Error comparing strategies: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/trading/signals', methods=['POST'])
def get_trading_signal():
    """
    Get trading signal from Adaptive Elite Strategy
    
    Simple endpoint focused on signal accuracy
    
    Request body:
    {
        "ticker": "RELIANCE.NS"
    }
    
    Response:
    {
        "status": "success",
        "ticker": "RELIANCE.NS",
        "signal": "BUY|SELL|HOLD",
        "confidence": 0.85,
        "entry_price": 2450.50,
        "stop_loss": 2383.19,
        "target_1": 2579.75,
        "target_2": 2702.59,
        "current_price": 2450.50,
        "regime_type": "STRONG_TREND",
        "market_phase": "BULL",
        "timestamp": "2024-01-15T10:30:00"
    }
    """
    try:
        data = request.json or {}
        ticker = data.get('ticker')
        
        if not ticker:
            return jsonify({'error': 'Ticker required'}), 400
        
        # Get current price
        from src.web.data_source_manager import get_data_source_manager
        data_manager = get_data_source_manager()
        quote, source = data_manager.get_quote(ticker)
        
        if not quote:
            return jsonify({'error': f'Could not get price for {ticker}'}), 404
        
        current_price = float(quote.get('last_price', quote.get('close', 0)))
        
        if current_price <= 0:
            return jsonify({'error': 'Invalid price data'}), 404
        
        # Initialize Adaptive Elite Strategy
        from src.web.strategies.adaptive_elite_strategy import AdaptiveEliteStrategy
        strategy = AdaptiveEliteStrategy()
        
        # Execute strategy
        result = strategy.execute({
            'ticker': ticker,
            'current_price': current_price
        })
        
        # Extract regime info from metadata
        regime_info = result.metadata.get('regime_info', {}) if result.metadata else {}
        regime_type = result.metadata.get('regime_type', 'UNKNOWN') if result.metadata else 'UNKNOWN'
        market_phase = regime_info.get('market_phase', 'NEUTRAL')
        
        return jsonify({
            'status': 'success',
            'ticker': ticker,
            'signal': result.signal,
            'confidence': round(result.confidence, 3),
            'entry_price': round(result.entry_price, 2),
            'stop_loss': round(result.stop_loss, 2),
            'target_1': round(result.target_1, 2),
            'target_2': round(result.target_2, 2),
            'current_price': round(current_price, 2),
            'regime_type': regime_type,
            'market_phase': market_phase,
            'trend_strength': round(regime_info.get('trend_strength', 0), 2),
            'volatility_pct': round(regime_info.get('volatility_pct', 0), 2),
            'strategy_used': result.metadata.get('strategy_used', 'Adaptive Elite') if result.metadata else 'Adaptive Elite',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting trading signal: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/trading/signals/watchlist', methods=['GET', 'POST'])
def get_watchlist_signals():
    """
    Get trading signals for all watchlist stocks
    
    Returns signals for all stocks in watchlist, sorted by confidence
    
    Response:
    {
        "status": "success",
        "signals": [...],
        "summary": {
            "total": 5,
            "buy_signals": 2,
            "sell_signals": 1,
            "hold_signals": 2
        }
    }
    """
    try:
        # Get watchlist
        watchlist = watchlist_manager.get_watchlist()
        
        if not watchlist:
            return jsonify({
                'status': 'success',
                'signals': [],
                'summary': {
                    'total': 0,
                    'buy_signals': 0,
                    'sell_signals': 0,
                    'hold_signals': 0
                },
                'message': 'Watchlist is empty'
            })
        
        # Get signals for each ticker
        from src.web.strategies.adaptive_elite_strategy import AdaptiveEliteStrategy
        from src.web.data_source_manager import get_data_source_manager
        
        strategy = AdaptiveEliteStrategy()
        data_manager = get_data_source_manager()
        signals = []
        
        for ticker in watchlist:
            try:
                # Get current price
                quote, source = data_manager.get_quote(ticker)
                if not quote:
                    continue
                
                current_price = float(quote.get('last_price', quote.get('close', 0)))
                if current_price <= 0:
                    continue
                
                # Get signal
                result = strategy.execute({
                    'ticker': ticker,
                    'current_price': current_price
                })
                
                # Extract regime info
                regime_info = result.metadata.get('regime_info', {}) if result.metadata else {}
                regime_type = result.metadata.get('regime_type', 'UNKNOWN') if result.metadata else 'UNKNOWN'
                market_phase = regime_info.get('market_phase', 'NEUTRAL')
                
                signals.append({
                    'ticker': ticker,
                    'signal': result.signal,
                    'confidence': round(result.confidence, 3),
                    'current_price': round(current_price, 2),
                    'entry_price': round(result.entry_price, 2),
                    'stop_loss': round(result.stop_loss, 2),
                    'target_1': round(result.target_1, 2),
                    'target_2': round(result.target_2, 2),
                    'regime_type': regime_type,
                    'market_phase': market_phase,
                    'trend_strength': round(regime_info.get('trend_strength', 0), 2),
                    'volatility_pct': round(regime_info.get('volatility_pct', 0), 2),
                    'strategy_used': result.metadata.get('strategy_used', 'Adaptive Elite') if result.metadata else 'Adaptive Elite',
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.debug(f"Error getting signal for {ticker}: {e}")
                continue
        
        # Sort by confidence (highest first), then by signal (BUY > SELL > HOLD)
        signal_priority = {'BUY': 3, 'SELL': 2, 'HOLD': 1}
        signals.sort(key=lambda x: (x['confidence'], signal_priority.get(x['signal'], 0)), reverse=True)
        
        # Calculate summary
        buy_signals = sum(1 for s in signals if s['signal'] == 'BUY')
        sell_signals = sum(1 for s in signals if s['signal'] == 'SELL')
        hold_signals = sum(1 for s in signals if s['signal'] == 'HOLD')
        
        return jsonify({
            'status': 'success',
            'signals': signals,
            'summary': {
                'total': len(signals),
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'hold_signals': hold_signals
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting watchlist signals: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/trading/signals/all-stocks', methods=['GET'])
def get_all_stocks_signals():
    """
    Get trading signals for all BSE/NSE stocks using Adaptive Elite Strategy
    Supports pagination and filtering
    """
    try:
        from src.web.data.all_stocks_list import get_all_stocks, get_major_stocks
        
        # Get query parameters
        limit = int(request.args.get('limit', 50))  # Default 50 stocks per request
        offset = int(request.args.get('offset', 0))
        signal_filter = request.args.get('signal', None)  # 'BUY', 'SELL', 'HOLD', or None for all
        min_confidence = float(request.args.get('min_confidence', 0.0))
        use_major_only = request.args.get('major_only', 'false').lower() == 'true'
        
        # Get stock list
        if use_major_only:
            all_stocks = get_major_stocks(limit=200)  # NIFTY 50 + Next 50
        else:
            all_stocks = get_all_stocks()
        
        # Apply pagination
        total_stocks = len(all_stocks)
        stocks_to_process = all_stocks[offset:offset + limit]
        
        logger.info(f"[All Stocks Signals] Processing {len(stocks_to_process)} stocks (offset: {offset}, total: {total_stocks})")
        
        # Get ELITE signal generator
        elite_generator = get_elite_signal_generator()
        
        signals = []
        errors = []
        
        # Process stocks
        for ticker in stocks_to_process:
            try:
                # Generate signal using ELITE strategy
                signal_response = elite_generator.generate_signal(
                    ticker=ticker,
                    use_ensemble=True,
                    use_multi_timeframe=True
                )
                
                if 'error' in signal_response:
                    errors.append({'ticker': ticker, 'error': signal_response.get('error')})
                    continue
                
                # Apply filters
                signal_type = signal_response.get('signal', 'HOLD')
                confidence = signal_response.get('confidence', 0.0)
                
                if signal_filter and signal_type != signal_filter:
                    continue
                
                if confidence < min_confidence:
                    continue
                
                # Extract regime info
                regime_info = signal_response.get('regime_info', {})
                regime_type = signal_response.get('regime_type', 'UNKNOWN')
                market_phase = regime_info.get('market_phase', 'NEUTRAL') if isinstance(regime_info, dict) else 'NEUTRAL'
                
                signals.append({
                    'ticker': ticker,
                    'signal': signal_type,
                    'confidence': round(confidence, 3),
                    'current_price': round(signal_response.get('current_price', 0), 2),
                    'entry_price': round(signal_response.get('entry_price', 0), 2),
                    'stop_loss': round(signal_response.get('stop_loss', 0), 2),
                    'target_1': round(signal_response.get('target_1', 0), 2),
                    'target_2': round(signal_response.get('target_2', 0), 2),
                    'regime_type': regime_type,
                    'market_phase': market_phase,
                    'trend_strength': round(regime_info.get('trend_strength', 0), 2) if isinstance(regime_info, dict) else 0,
                    'volatility_pct': round(regime_info.get('volatility_pct', 0), 2) if isinstance(regime_info, dict) else 0,
                    'strategy_used': 'Adaptive Elite',
                    'timestamp': signal_response.get('timestamp', datetime.now().isoformat())
                })
                
            except Exception as e:
                logger.debug(f"Error getting signal for {ticker}: {e}")
                errors.append({'ticker': ticker, 'error': str(e)})
                continue
        
        # Sort by confidence (highest first), then by signal (BUY > SELL > HOLD)
        signal_priority = {'BUY': 3, 'SELL': 2, 'HOLD': 1}
        signals.sort(key=lambda x: (x['confidence'], signal_priority.get(x['signal'], 0)), reverse=True)
        
        # Calculate summary
        buy_signals = sum(1 for s in signals if s['signal'] == 'BUY')
        sell_signals = sum(1 for s in signals if s['signal'] == 'SELL')
        hold_signals = sum(1 for s in signals if s['signal'] == 'HOLD')
        
        return jsonify({
            'status': 'success',
            'signals': signals,
            'pagination': {
                'offset': offset,
                'limit': limit,
                'total': total_stocks,
                'returned': len(signals),
                'has_more': (offset + limit) < total_stocks
            },
            'summary': {
                'total': len(signals),
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'hold_signals': hold_signals
            },
            'errors': errors[:10] if errors else []  # Return first 10 errors for debugging
        })
        
    except Exception as e:
        logger.error(f"Error getting all stocks signals: {e}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# ============================================================================
# Auto Trading API Endpoints
# ============================================================================

@app.route('/auto-trading-test')
def auto_trading_test():
    """Simple test to verify this app is running (returns 200 OK)"""
    return "OK - Auto Trading app is running. Use /auto-trading for the dashboard."

@app.route('/auto-trading')
@app.route('/auto_trading')  # alternate URL in case of typo
def auto_trading_dashboard():
    """Auto trading dashboard page"""
    return render_template('auto_trading.html')

@app.route('/api/auto-trading/start', methods=['POST'])
def start_auto_trading():
    """Start auto trading and daily workflow (pre-market, scans, post-market)."""
    try:
        from src.web.auto_trader import AutoTrader
        from src.web.upstox_connection import get_upstox_connection
        from src.web.daily_workflow import get_daily_workflow_manager
        
        # Get Upstox client if available
        upstox_conn = get_upstox_connection()
        upstox_client = None
        if upstox_conn and upstox_conn.is_connected():
            upstox_client = upstox_conn.get_client()
        
        # Get or create auto trader
        if not hasattr(app, '_auto_trader') or app._auto_trader is None:
            app._auto_trader = AutoTrader(
                upstox_client=upstox_client,
                confidence_threshold=0.7,
                max_positions=10
            )
        else:
            # Update Upstox client if it changed
            if upstox_client:
                app._auto_trader.upstox_client = upstox_client
                if app._auto_trader.trade_executor:
                    app._auto_trader.trade_executor.upstox_client = upstox_client
        # Wire Upstox to intraday data manager for real 5m/15m/1h data during market hours
        if upstox_client:
            from src.web.intraday_data_manager import get_intraday_data_manager
            get_intraday_data_manager().set_upstox_client(upstox_client)
        
        if not app._auto_trader.start():
            return jsonify({
                'success': False,
                'message': 'Failed to start auto trading'
            }), 400
        
        # Wire to daily workflow so scans run on schedule (pre-market, market-hours, post-market)
        workflow = get_daily_workflow_manager(app._auto_trader)
        workflow.auto_trader = app._auto_trader
        if workflow.start_daily_workflow():
            return jsonify({
                'success': True,
                'message': 'Auto trading and daily workflow started (scans will run on schedule)'
            })
        # If scheduler already running or start failed, we still have auto_trader running
        return jsonify({
            'success': True,
            'message': 'Auto trading started successfully'
        })
    
    except Exception as e:
        logger.error(f"Error starting auto trading: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auto-trading/stop', methods=['POST'])
def stop_auto_trading():
    """Stop daily workflow (scheduler) and auto trading."""
    try:
        from src.web.daily_workflow import get_daily_workflow_manager
        
        # Stop daily workflow first (stops scheduler and auto_trader)
        workflow = get_daily_workflow_manager()
        if workflow.is_running:
            if workflow.stop_daily_workflow():
                return jsonify({
                    'success': True,
                    'message': 'Auto trading and daily workflow stopped successfully'
                })
        # If workflow was not running, stop auto_trader directly
        if hasattr(app, '_auto_trader') and app._auto_trader and app._auto_trader.is_running:
            if app._auto_trader.stop():
                return jsonify({
                    'success': True,
                    'message': 'Auto trading stopped successfully'
                })
            return jsonify({
                'success': False,
                'message': 'Failed to stop auto trading'
            }), 400
        return jsonify({
            'success': True,
            'message': 'Auto trading stopped (was not running)'
        })
    
    except Exception as e:
        logger.error(f"Error stopping auto trading: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auto-trading/pause', methods=['POST'])
def pause_auto_trading():
    """Pause auto trading (circuit breaker)"""
    try:
        if hasattr(app, '_auto_trader') and app._auto_trader:
            # Trigger circuit breaker
            app._auto_trader.circuit_breaker_triggered = True
            app._auto_trader.circuit_breaker_time = datetime.now()
            return jsonify({
                'success': True,
                'message': 'Auto trading paused (circuit breaker activated)'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Auto trader not initialized'
            }), 400
    
    except Exception as e:
        logger.error(f"Error pausing auto trading: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auto-trading/status')
def get_auto_trading_status():
    """Get auto trading status"""
    try:
        if hasattr(app, '_auto_trader') and app._auto_trader:
            status = app._auto_trader.get_status()
            
            # Add market status
            from src.web.market_hours import get_market_hours_manager
            market_hours = get_market_hours_manager()
            status['market_status'] = market_hours.get_market_status()
            
            # Add Upstox connection status
            from src.web.upstox_connection import get_upstox_connection
            upstox_conn = get_upstox_connection()
            status['upstox_connected'] = upstox_conn.is_connected() if upstox_conn else False
            
            # Add trading mode
            from src.web.trading_mode import get_trading_mode_manager
            trading_mode = get_trading_mode_manager()
            status['trading_mode'] = trading_mode.get_mode().value if trading_mode else 'paper'
            
            # Add open positions count
            positions = app._auto_trader._get_current_positions()
            status['open_positions'] = len(positions)
            
            # Add accuracy summary for active signal source (last 30 days)
            try:
                from src.web.ai_models.performance_tracker import get_performance_tracker
                tracker = get_performance_tracker()
                src = status.get('signal_source', 'elite')
                active = status.get('active_quant_strategy', '')
                model_id = 'quant_ensemble' if src == 'quant_ensemble' else ('quant_' + active if src == 'quant' else 'elite_multi_tf')
                metrics = tracker.calculate_metrics(model_id, days=30)
                if 'error' not in metrics:
                    status['accuracy_30d'] = round(metrics.get('accuracy', 0) * 100, 1)
                    status['win_rate_30d'] = round(metrics.get('win_rate', 0) * 100, 1)
                    status['evaluated_predictions_30d'] = metrics.get('evaluated_predictions', 0)
                else:
                    status['accuracy_30d'] = None
                    status['win_rate_30d'] = None
            except Exception:
                status['accuracy_30d'] = None
                status['win_rate_30d'] = None
            
            return jsonify(status)
        else:
            from src.web.risk_config import get_risk_config
            from src.web.strategies.strategy_manager import get_strategy_manager
            rc = get_risk_config()
            sm = get_strategy_manager()
            return jsonify({
                'is_running': False,
                'message': 'Auto trader not initialized',
                'market_status': {'status': 'UNKNOWN'},
                'upstox_connected': False,
                'trading_mode': 'paper',
                'open_positions': 0,
                'confidence_threshold': rc.get('confidence_threshold'),
                'max_positions': rc.get('max_open_positions'),
                'signal_source': rc.get('signal_source', 'elite'),
                'quant_ensemble_method': rc.get('quant_ensemble_method', 'weighted_average'),
                'active_quant_strategy': sm.active_strategy,
                'available_quant_strategies': sm.get_available_strategies(),
                'accuracy_30d': None,
                'win_rate_30d': None,
                'circuit_breaker': {
                    'daily_loss_limit_pct': rc.get('daily_loss_limit_pct'),
                    'daily_loss_limit_amount': rc.get('daily_loss_limit_amount'),
                    'max_consecutive_losses': rc.get('max_consecutive_losses'),
                    'cooldown_minutes': rc.get('cooldown_minutes'),
                }
            })
    
    except Exception as e:
        logger.error(f"Error getting auto trading status: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/auto-trading/settings', methods=['POST'])
def set_auto_trading_settings():
    """Set signal source (elite | quant | quant_ensemble) and/or active quant strategy."""
    try:
        data = request.get_json() or {}
        updates = {}
        if 'signal_source' in data:
            v = (data['signal_source'] or '').lower()
            if v in ('elite', 'quant', 'quant_ensemble'):
                updates['signal_source'] = v
        if 'quant_ensemble_method' in data:
            v = (data['quant_ensemble_method'] or '').lower()
            if v in ('weighted_average', 'voting', 'best_performer'):
                updates['quant_ensemble_method'] = v
        if updates:
            from src.web.risk_config import update_risk_config
            update_risk_config(updates)
            if hasattr(app, '_auto_trader') and app._auto_trader:
                for k, v in updates.items():
                    setattr(app._auto_trader, k, v)
        active_name = None
        if 'active_quant_strategy' in data:
            from src.web.strategies.strategy_manager import get_strategy_manager
            sm = get_strategy_manager()
            name = data['active_quant_strategy']
            if sm.set_active_strategy(name):
                active_name = name
        if not updates and active_name is None:
            return jsonify({'success': False, 'error': 'No valid settings to update'}), 400
        return jsonify({
            'success': True,
            'message': 'Settings updated',
            'signal_source': updates.get('signal_source') or (getattr(app._auto_trader, 'signal_source', None) if hasattr(app, '_auto_trader') and app._auto_trader else None),
            'quant_ensemble_method': updates.get('quant_ensemble_method'),
            'active_quant_strategy': active_name
        })
    except Exception as e:
        logger.exception("Error updating auto trading settings")
        return jsonify({'error': str(e)}), 500


@app.route('/api/auto-trading/scan', methods=['POST'])
def run_auto_trading_scan():
    """Run one scan-and-execute cycle now (manual trigger)."""
    try:
        if not hasattr(app, '_auto_trader') or app._auto_trader is None:
            return jsonify({
                'success': False,
                'error': 'Auto trader not initialized. Start auto trading first.'
            }), 400
        from src.web.market_hours import get_market_hours_manager
        market_hours = get_market_hours_manager()
        is_intraday = market_hours.is_market_open()
        result = app._auto_trader.scan_and_execute(
            timeframes=['5m', '15m', '1h', '1d'],
            is_intraday=is_intraday
        )
        if result.get('error'):
            return jsonify({
                'success': False,
                'error': result['error'],
                'result': result
            }), 400
        return jsonify({
            'success': True,
            'result': result,
            'timestamp': result.get('timestamp')
        })
    except Exception as e:
        logger.exception("Run scan failed")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auto-trading/backtest-run', methods=['POST'])
def run_backtest_tuning():
    """Run threshold sweep and strategy ranking; return results (does not apply)."""
    try:
        from datetime import date, timedelta
        from src.web.backtest_tuning import run_threshold_sweep, run_strategy_ranking
        data = request.get_json() or {}
        ticker = data.get('ticker') or None
        if not ticker:
            from src.web.data.all_stocks_list import get_all_stocks
            stocks = get_all_stocks()
            ticker = (stocks[0] if stocks else 'RELIANCE.NS')
        end_date = data.get('end_date') or date.today().strftime('%Y-%m-%d')
        start_date = data.get('start_date') or (date.today() - timedelta(days=365)).strftime('%Y-%m-%d')
        sweep = run_threshold_sweep(ticker, start_date, end_date)
        ranking = run_strategy_ranking(ticker, start_date, end_date)
        return jsonify({
            'success': 'error' not in sweep and 'error' not in ranking,
            'ticker': ticker,
            'start_date': start_date,
            'end_date': end_date,
            'sweep': sweep,
            'ranking': ranking,
        })
    except Exception as e:
        logger.exception("Backtest tuning run failed")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auto-trading/backtest-apply', methods=['POST'])
def apply_backtest_tuning():
    """Apply backtest results: set confidence_threshold (capped) and/or active strategy."""
    try:
        from src.web.backtest_tuning import apply_backtest_results, BEST_THRESHOLD_CAP
        data = request.get_json() or {}
        apply_threshold = data.get('apply_threshold', False)
        apply_strategy = data.get('apply_strategy', False)
        best_threshold = data.get('best_threshold')
        best_strategy = data.get('best_strategy')
        try:
            th_val = float(best_threshold) if best_threshold is not None else None
        except (TypeError, ValueError):
            th_val = None
        sweep_result = {'best_threshold': min(th_val, BEST_THRESHOLD_CAP)} if (apply_threshold and th_val is not None) else None
        ranking_result = {'best_strategy': best_strategy} if (apply_strategy and best_strategy) else None
        out = apply_backtest_results(
            sweep_result=sweep_result,
            ranking_result=ranking_result,
            apply_threshold=bool(sweep_result),
            apply_strategy=bool(ranking_result),
        )
        return jsonify({'success': True, **out})
    except Exception as e:
        logger.exception("Backtest apply failed")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auto-trading/retrain-elite', methods=['POST'])
def retrain_elite_baseline():
    """Run periodic retrain of ELITE baseline model. Uses time-based split and saves to data/models/."""
    try:
        from scripts.retrain_elite_baseline import run_retrain
        data = request.get_json() or {}
        ticker = data.get('ticker', 'RELIANCE.NS')
        days = int(data.get('days_back', 504))
        ok = run_retrain(ticker=ticker, days_back=days)
        return jsonify({'success': ok, 'message': 'Model retrained and saved' if ok else 'Retrain failed'})
    except ImportError:
        try:
            from src.research.data import download_yahoo_ohlcv
            from src.research.features import make_features, add_label_forward_return_up, clean_ml_frame
            from src.research.ml import train_baseline_classifier, save_model
            from datetime import datetime, timedelta
            data = request.get_json() or {}
            ticker = data.get('ticker', 'RELIANCE.NS')
            days = int(data.get('days_back', 504))
            end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            ohlcv = download_yahoo_ohlcv(ticker=ticker, start=start_date, end=end_date, interval='1d')
            if not ohlcv or len(ohlcv.df) < 300:
                return jsonify({'success': False, 'message': 'Insufficient data'}), 400
            df = make_features(ohlcv.df)
            df = add_label_forward_return_up(df, days=1, threshold=0.0)
            feature_cols = [c for c in ['ret_1', 'ret_5', 'vol_10', 'sma_10', 'sma_50', 'ema_20', 'rsi_14', 'macd', 'macd_signal', 'macd_hist', 'vol_chg_1', 'vol_sma_20'] if c in df.columns]
            if len(feature_cols) < 5:
                return jsonify({'success': False, 'message': 'Not enough features'}), 400
            ml_df = clean_ml_frame(df, feature_cols=feature_cols, label_col='label_up')
            if len(ml_df) < 252:
                return jsonify({'success': False, 'message': 'Insufficient rows'}), 400
            train_result, _ = train_baseline_classifier(df=ml_df, feature_cols=feature_cols, label_col='label_up', test_size=0.2, random_state=42)
            Path('data/models').mkdir(parents=True, exist_ok=True)
            save_model(train_result.model, 'data/models/elite_baseline.joblib')
            with open('data/models/elite_baseline_features.json', 'w') as f:
                json.dump(feature_cols, f, indent=2)
            return jsonify({'success': True, 'message': 'Model retrained and saved'})
        except Exception as e:
            logger.exception("ELITE retrain failed")
            return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        logger.exception("ELITE retrain failed")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auto-trading/history')
def get_auto_trading_history():
    """Get auto trading execution history"""
    try:
        if hasattr(app, '_auto_trader') and app._auto_trader and app._auto_trader.trade_executor:
            history = app._auto_trader.trade_executor.get_execution_history(limit=100)
            
            # Format history for display
            formatted_history = []
            for exec_record in history:
                signal = exec_record.get('signal', {})
                formatted_history.append({
                    'timestamp': exec_record.get('timestamp', ''),
                    'ticker': signal.get('ticker', '') or exec_record.get('ticker', ''),
                    'signal': signal.get('consensus_signal', '') or signal.get('signal', ''),
                    'probability': signal.get('probability', 0),
                    'success': exec_record.get('success', False),
                    'transaction_type': exec_record.get('transaction_type', ''),
                    'quantity': exec_record.get('quantity', 0),
                    'price': exec_record.get('price', signal.get('current_price', 0))
                })
            
            return jsonify(formatted_history)
        else:
            return jsonify([])
    
    except Exception as e:
        logger.error(f"Error getting auto trading history: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auto-trading/reset-circuit-breaker', methods=['POST'])
def reset_circuit_breaker():
    """Reset circuit breaker"""
    try:
        if hasattr(app, '_auto_trader') and app._auto_trader:
            app._auto_trader.reset_circuit_breaker()
            return jsonify({
                'success': True,
                'message': 'Circuit breaker reset successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Auto trader not initialized'
            }), 400
    
    except Exception as e:
        logger.error(f"Error resetting circuit breaker: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trading-signals', methods=['POST'])
def get_trading_signals():
    """Get trading signals for given stocks"""
    try:
        data = request.get_json()
        stocks = data.get('stocks', [])
        intraday = data.get('intraday', False)
        min_confidence = float(data.get('min_confidence', 0.55))
        
        if not stocks:
            return jsonify({'status': 'error', 'message': 'No stocks provided'}), 400
        
        # Import trading signals functions
        # project_root is already added to sys.path at the top of the file
        from trading_signals_nse_only import scan_stocks
        
        # Get signals
        signals = scan_stocks(stocks, min_confidence=min_confidence, intraday=intraday)
        
        return jsonify({
            'status': 'success',
            'signals': signals,
            'count': len(signals)
        })
    
    except Exception as e:
        logger.error(f"Error getting trading signals: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/auto-trading/positions')
def get_auto_trading_positions():
    """Get current open positions from auto trading"""
    try:
        if hasattr(app, '_auto_trader') and app._auto_trader:
            positions = app._auto_trader._get_current_positions()
            
            # Format positions for display
            formatted_positions = []
            for pos in positions:
                formatted_positions.append({
                    'ticker': pos.get('ticker') or pos.get('symbol', ''),
                    'quantity': pos.get('quantity', 0),
                    'entry_price': pos.get('entry_price', pos.get('average_price', 0)),
                    'current_price': pos.get('current_price', pos.get('ltp', 0)),
                    'pnl': pos.get('pnl', 0),
                    'product': pos.get('product', 'I')
                })
            
            return jsonify(formatted_positions)
        else:
            return jsonify([])
    
    except Exception as e:
        logger.error(f"Error getting auto trading positions: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "5000"))
    print(f"\n{'='*60}")
    print("AI Trading Dashboard - LIVE TRADING MODE")
    print(f"{'='*60}")
    print(f"Local access:  http://localhost:{port}")
    print(f"Network access: http://{_get_local_ip()}:{port}")
    print(f"{'='*60}")
    print("⚠️  LIVE TRADING ENABLED - Orders will execute with real money!")
    print(f"{'='*60}\n")
    # Phase 2.1: Use socketio.run instead of app.run for WebSocket support
    socketio.run(app, debug=True, host=host, port=port)
