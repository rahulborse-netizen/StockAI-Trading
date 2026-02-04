"""
Flask web application for AI Trading Algorithm
Provides UI/UX interface for monitoring, alerts, and order execution
"""
from flask import Flask, render_template, jsonify, request, session
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
import pandas as pd
import numpy as np
import os
import socket
from urllib.parse import urlencode

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
from src.web.trade_planner import get_trade_planner, get_plan_manager, TradePlanStatus
from src.web.position_sizing import calculate_risk_based_size
from src.web.risk_config import get_risk_config
from src.web.trade_journal import get_trade_journal
from src.web.risk_manager import get_risk_manager
from src.web.paper_trading import get_paper_trading_manager
from src.web.daily_positions import get_daily_tracker
from src.web.data_pipeline import get_data_pipeline
from src.web.data_collectors.financial_data import get_financial_collector
from src.web.data_collectors.news_sentiment import get_news_collector
from typing import Dict

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

@app.before_request
def make_session_permanent():
    """Make session permanent so it persists"""
    session.permanent = True

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

@app.route('/api/signals/<ticker>')
def get_signals(ticker):
    """Get trading signals for a ticker. Optionally generate trade plan with ?generate_plan=true&trading_type=swing"""
    try:
        # Check if trade plan generation is requested
        generate_plan = request.args.get('generate_plan', 'false').lower() == 'true'
        trading_type = request.args.get('trading_type', 'swing')
        # Get recent data - ensure dates are correct
        today = datetime.now()
        today_str = today.strftime('%Y-%m-%d')
        
        # Use today as end_date, but validate it's not in the future
        end_date = today_str
        
        # Start from 1 year ago
        start_date = (today - timedelta(days=365)).strftime('%Y-%m-%d')
        
        # Validate dates
        end_year = int(end_date.split('-')[0])
        if end_year > today.year + 1:
            logger.error(f"[Signals] End date {end_date} year {end_year} is in the future! Using today.")
            end_date = today_str
            start_date = (today - timedelta(days=365)).strftime('%Y-%m-%d')
        
        logger.info(f"[Signals] Date range for {ticker}: {start_date} to {end_date}")
        
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
            return jsonify({'error': 'No data available'}), 404
        
        # Generate features and predictions
        feat_df = make_features(ohlcv.df.copy())
        labeled_df = add_label_forward_return_up(feat_df, days=1, threshold=0.0)
        ml_df = clean_ml_frame(labeled_df, feature_cols=DEFAULT_FEATURE_COLS, label_col="label_up")
        
        if len(ml_df) < 50:
            return jsonify({'error': 'Insufficient data'}), 404
        
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
            'timestamp': datetime.now().isoformat()
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
        return jsonify({'error': str(e)}), 500

@app.route('/api/index-signals')
def get_all_index_signals():
    """Get trading signals for all major indices"""
    indices = [
        {'name': 'Nifty 50', 'ticker': '^NSEI', 'key': 'nifty50'},
        {'name': 'Bank Nifty', 'ticker': '^NSEBANK', 'key': 'banknifty'},
        {'name': 'Sensex', 'ticker': '^BSESN', 'key': 'sensex'}
    ]
    
    results = []
    for index in indices:
        try:
            # Get recent data - ensure dates are correct
            today = datetime.now()
            today_str = today.strftime('%Y-%m-%d')
            end_date = today_str
            start_date = (today - timedelta(days=365)).strftime('%Y-%m-%d')
            
            # Validate dates
            end_year = int(end_date.split('-')[0])
            if end_year > today.year + 1:
                logger.error(f"[Index Signals] End date {end_date} year {end_year} is in the future! Using today.")
                end_date = today_str
                start_date = (today - timedelta(days=365)).strftime('%Y-%m-%d')
            
            logger.info(f"[Index Signals] Date range for {index['name']}: {start_date} to {end_date}")
            
            Path("cache").mkdir(parents=True, exist_ok=True)
            cache_path = Path('cache') / f"{index['ticker'].replace('^', '').replace(':', '_').replace('/', '_')}.csv"
            ohlcv = download_yahoo_ohlcv(
                ticker=index['ticker'],
                start=start_date,
                end=end_date,
                interval='1d',
                cache_path=cache_path,
                refresh=False
            )
            
            if ohlcv is None or len(ohlcv.df) == 0:
                continue
            
            # Generate features and predictions
            feat_df = make_features(ohlcv.df.copy())
            labeled_df = add_label_forward_return_up(feat_df, days=1, threshold=0.0)
            ml_df = clean_ml_frame(labeled_df, feature_cols=DEFAULT_FEATURE_COLS, label_col="label_up")
            
            if len(ml_df) < 50:
                continue
            
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
            
            results.append({
                'index_name': index['name'],
                'index_key': index['key'],
                'ticker': index['ticker'],
                'current_price': current_price,
                'signal': signal,
                'probability': float(prob_up),
                'entry_level': entry_level,
                'stop_loss': stop_loss,
                'target_1': target_1,
                'target_2': target_2,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"[Index Signals] Error for {index['name']}: {e}")
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
            return jsonify({'error': 'Insufficient data'}), 404
        
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
    """Get current prices for watchlist - Phase 2.1: Real-time data integration"""
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
        # Not connected to Upstox, use cached data
        for ticker in watchlist:
            prices[ticker] = _get_cached_price(ticker)
    
    return jsonify(prices)

def _get_cached_price(ticker: str) -> Dict:
    """Fallback: Get price from cached Yahoo Finance data"""
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
        # If access token is provided directly, use it
        if access_token:
            logger.info("[Phase 1.2] Using direct access token")
            upstox_api = UpstoxAPI(api_key, api_secret, redirect_uri)
            upstox_api.set_access_token(access_token)
            connection_manager.save_connection(api_key, api_secret, redirect_uri, access_token)
            
            # Test connection with timeout handling
            logger.info("[Phase 1.2] Testing connection with access token...")
            try:
                profile = upstox_api.get_profile()
                if 'error' in profile:
                    error_msg = profile.get('error', 'Unknown error')
                    logger.error(f"[Phase 1.2] Connection test failed: {error_msg}")
                    connection_manager.clear_connection()
                    return jsonify({
                        'status': 'error', 
                        'message': f'Connection failed: {error_msg}',
                        'details': profile,
                        'hint': 'Check if access token is valid and not expired. You may need to generate a new token from Upstox.'
                    }), 400
                
                logger.info("[Phase 1.2] Connection test successful")
                return jsonify({
                    'status': 'success', 
                    'message': 'Upstox connected successfully',
                    'profile': profile
                })
            except Exception as e:
                logger.error(f"[Phase 1.2] Connection test exception: {e}")
                connection_manager.clear_connection()
                return jsonify({
                    'status': 'error',
                    'message': f'Connection test failed: {str(e)}',
                    'hint': 'This might be a network issue. Please check your internet connection and try again.'
                }), 400
        
        # Otherwise, generate authorization URL for OAuth flow
        # This should be instant - no network calls, just URL building
        logger.info("[Phase 1.2] Starting OAuth flow...")
        logger.info(f"[Phase 1.2] Creating UpstoxAPI instance...")
        upstox_api = UpstoxAPI(api_key, api_secret, redirect_uri)
        logger.info(f"[Phase 1.2] UpstoxAPI instance created")
        
        logger.info(f"[Phase 1.2] Saving connection to session...")
        connection_manager.save_connection(api_key, api_secret, redirect_uri)
        logger.info(f"[Phase 1.2] Connection saved to session")
        
        # Generate authorization URL (instant - no network call)
        logger.info(f"[Phase 1.2] Building authorization URL...")
        auth_url = upstox_api.build_authorize_url()
        logger.info(f"[Phase 1.2] Authorization URL generated: {auth_url[:100]}...")
        
        # Get suggested URIs (fast - no network detection)
        suggested_uris = ['http://localhost:5000/callback']  # Fast default
        
        logger.info(f"[Phase 1.2] Returning auth_required response...")
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
    
    logger.info(f"[Phase 1.2] Callback received - Code: {'Yes' if auth_code else 'No'}, Error: {error}")
    
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
        logger.info(f"[Phase 1.2] Attempting to authenticate with auth code: {auth_code[:10]}...")
        logger.info(f"[Phase 1.2] Using redirect_uri: {redirect_uri}")
        logger.info(f"[Phase 1.2] Using API Key: {api_key[:8]}...")
        
        auth_success = upstox_api.authenticate(auth_code)
        if not auth_success:
            logger.error(f"[Phase 1.2] Authentication failed - Invalid Credentials error")
            logger.error(f"[Phase 1.2] This usually means redirect URI mismatch")
            logger.error(f"[Phase 1.2] Expected redirect URI: {redirect_uri}")
            logger.error(f"[Phase 1.2] Please verify this EXACT URI is in Upstox Portal")
        
        if auth_success:
            connection_manager.save_connection(api_key, api_secret, redirect_uri, upstox_api.access_token)
            
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

@app.route('/api/upstox/status', methods=['GET'])
def upstox_status():
    """Phase 1.2: Get Upstox connection status"""
    try:
        info = connection_manager.get_connection_info()
        
        # Double-check connection status
        is_connected = connection_manager.is_connected()
        info['connected'] = is_connected
        
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
        
        if is_connected:
            client = connection_manager.get_client()
            if client:
                profile = client.get_profile()
                if 'error' not in profile:
                    info['profile'] = profile
                else:
                    info['connected'] = False
                    info['error'] = profile.get('error', 'Unknown error')
        
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

@app.route('/api/upstox/orders', methods=['GET'])
def get_orders():
    """Get order history"""
    client = _get_upstox_client()
    if not client:
        return jsonify({'error': 'Upstox not connected. Please connect first.'}), 400
    try:
        orders = client.get_orders()
        return jsonify(orders)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upstox/place_order', methods=['POST'])
def place_order():
    """Place order through Upstox (real trading) or Paper Trading (simulation)"""
    # Check if paper trading mode is enabled (from session or environment)
    paper_mode = session.get('paper_trading_mode', False) or PAPER_TRADING_MODE
    
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
    """Get positions data"""
    client = _get_upstox_client()
    if not client:
        return jsonify({'error': 'Upstox not connected. Please connect first.'}), 400
    try:
        return jsonify(client.get_positions())
    except Exception as e:
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
    app.run(debug=True, host=host, port=port)
