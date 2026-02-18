"""
Market Microstructure Analysis
Phase 2.2: Advanced Features - Order book depth, bid-ask spread, volume profile, market impact
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MarketMicrostructureAnalyzer:
    """
    Analyzes market microstructure features:
    - Order book depth
    - Bid-ask spread
    - Volume profile
    - Market impact
    """
    
    def __init__(self):
        self.order_book_cache: Dict[str, Dict] = {}
        self.volume_profile_cache: Dict[str, pd.DataFrame] = {}
    
    def calculate_bid_ask_spread(self, bid_price: float, ask_price: float, mid_price: float = None) -> Dict[str, float]:
        """
        Calculate bid-ask spread metrics.
        
        Args:
            bid_price: Best bid price
            ask_price: Best ask price
            mid_price: Mid price (optional, calculated if not provided)
        
        Returns:
            Dictionary with spread metrics
        """
        if not bid_price or not ask_price or bid_price <= 0 or ask_price <= 0:
            return {}
        
        if mid_price is None:
            mid_price = (bid_price + ask_price) / 2
        
        spread_absolute = ask_price - bid_price
        spread_percentage = (spread_absolute / mid_price * 100) if mid_price > 0 else 0
        
        return {
            'bid_price': bid_price,
            'ask_price': ask_price,
            'mid_price': mid_price,
            'spread_absolute': round(spread_absolute, 2),
            'spread_percentage': round(spread_percentage, 4),
            'spread_tight': spread_percentage < 0.1,  # Tight spread indicator
        }
    
    def estimate_spread_from_ohlcv(self, ohlcv_df: pd.DataFrame) -> Dict[str, float]:
        """
        Estimate bid-ask spread from OHLCV data using high-low spread approximation.
        
        Args:
            ohlcv_df: DataFrame with OHLCV data
        
        Returns:
            Estimated spread metrics
        """
        if ohlcv_df.empty or len(ohlcv_df) < 5:
            return {}
        
        # Use recent data for spread estimation
        recent = ohlcv_df.tail(20)
        
        # Estimate spread as average of (high - low) / close
        spreads = []
        for _, row in recent.iterrows():
            if row['close'] > 0:
                daily_spread = (row['high'] - row['low']) / row['close'] * 100
                spreads.append(daily_spread)
        
        if not spreads:
            return {}
        
        avg_spread = np.mean(spreads)
        median_spread = np.median(spreads)
        max_spread = np.max(spreads)
        min_spread = np.min(spreads)
        
        current_price = float(recent.iloc[-1]['close'])
        estimated_spread_absolute = current_price * (avg_spread / 100)
        
        return {
            'estimated_spread_percentage': round(avg_spread, 4),
            'estimated_spread_absolute': round(estimated_spread_absolute, 2),
            'spread_median': round(median_spread, 4),
            'spread_max': round(max_spread, 4),
            'spread_min': round(min_spread, 4),
            'spread_tight': avg_spread < 0.5,  # Tight spread if < 0.5%
            'current_price': current_price,
        }
    
    def calculate_volume_profile(self, ohlcv_df: pd.DataFrame, bins: int = 20) -> Dict[str, any]:
        """
        Calculate volume profile (price levels with highest volume).
        
        Args:
            ohlcv_df: DataFrame with OHLCV data
            bins: Number of price bins for volume distribution
        
        Returns:
            Volume profile analysis
        """
        if ohlcv_df.empty or 'volume' not in ohlcv_df.columns:
            return {}
        
        # Use recent data (last 60 days for better profile)
        recent = ohlcv_df.tail(60).copy()
        
        if recent.empty:
            return {}
        
        # Calculate price range
        price_min = float(recent['low'].min())
        price_max = float(recent['high'].max())
        price_range = price_max - price_min
        
        if price_range <= 0:
            return {}
        
        # Create price bins
        bin_edges = np.linspace(price_min, price_max, bins + 1)
        
        # Calculate volume at each price level
        volume_by_price = []
        for i in range(len(bin_edges) - 1):
            bin_low = bin_edges[i]
            bin_high = bin_edges[i + 1]
            bin_mid = (bin_low + bin_high) / 2
            
            # Find candles that overlap with this price bin
            mask = (
                (recent['low'] <= bin_high) & 
                (recent['high'] >= bin_low)
            )
            bin_volume = recent[mask]['volume'].sum()
            
            volume_by_price.append({
                'price_level': round(bin_mid, 2),
                'volume': int(bin_volume),
                'price_low': round(bin_low, 2),
                'price_high': round(bin_high, 2),
            })
        
        # Sort by volume
        volume_by_price.sort(key=lambda x: x['volume'], reverse=True)
        
        # Find POC (Point of Control) - price level with highest volume
        poc = volume_by_price[0] if volume_by_price else None
        
        # Find value area (price levels containing 70% of volume)
        total_volume = sum(v['volume'] for v in volume_by_price)
        value_area_volume = total_volume * 0.70
        
        cumulative_volume = 0
        value_area_levels = []
        for level in volume_by_price:
            cumulative_volume += level['volume']
            value_area_levels.append(level)
            if cumulative_volume >= value_area_volume:
                break
        
        value_area_high = max(level['price_level'] for level in value_area_levels)
        value_area_low = min(level['price_level'] for level in value_area_levels)
        
        current_price = float(recent.iloc[-1]['close'])
        
        return {
            'poc_price': poc['price_level'] if poc else None,
            'poc_volume': poc['volume'] if poc else 0,
            'value_area_high': round(value_area_high, 2),
            'value_area_low': round(value_area_low, 2),
            'value_area_range': round(value_area_high - value_area_low, 2),
            'current_price': current_price,
            'current_vs_poc': round(current_price - poc['price_level'], 2) if poc else None,
            'in_value_area': value_area_low <= current_price <= value_area_high,
            'volume_profile': volume_by_price[:10],  # Top 10 price levels
        }
    
    def calculate_market_impact(self, ohlcv_df: pd.DataFrame, trade_size: float = None) -> Dict[str, float]:
        """
        Estimate market impact of a trade.
        Uses price movement vs volume relationship.
        
        Args:
            ohlcv_df: DataFrame with OHLCV data
            trade_size: Size of trade (optional, uses average volume if not provided)
        
        Returns:
            Market impact estimates
        """
        if ohlcv_df.empty or len(ohlcv_df) < 20:
            return {}
        
        recent = ohlcv_df.tail(60).copy()
        
        # Calculate average daily volume
        avg_volume = float(recent['volume'].mean())
        median_volume = float(recent['volume'].median())
        
        if trade_size is None:
            trade_size = avg_volume * 0.01  # 1% of average volume
        
        # Calculate price impact based on volume
        # Impact = (trade_size / avg_volume) * volatility
        volume_ratio = trade_size / avg_volume if avg_volume > 0 else 0
        
        # Calculate volatility
        returns = recent['close'].pct_change().dropna()
        volatility = float(returns.std() * np.sqrt(252))  # Annualized
        
        # Estimate price impact (simplified model)
        # Impact increases with volume ratio and volatility
        estimated_impact_pct = volume_ratio * volatility * 0.5  # Scaling factor
        estimated_impact_absolute = float(recent.iloc[-1]['close']) * (estimated_impact_pct / 100)
        
        # Liquidity score (higher volume = more liquid = less impact)
        liquidity_score = min(100, (avg_volume / median_volume) * 50) if median_volume > 0 else 50
        
        return {
            'trade_size': round(trade_size, 2),
            'avg_volume': round(avg_volume, 2),
            'volume_ratio': round(volume_ratio, 4),
            'estimated_impact_percentage': round(estimated_impact_pct, 4),
            'estimated_impact_absolute': round(estimated_impact_absolute, 2),
            'volatility': round(volatility, 4),
            'liquidity_score': round(liquidity_score, 2),
            'high_liquidity': liquidity_score > 70,
        }
    
    def analyze_order_book_depth(self, order_book_data: Dict) -> Dict[str, any]:
        """
        Analyze order book depth.
        Requires order book data from Upstox API.
        
        Args:
            order_book_data: Order book data from Upstox
        
        Returns:
            Order book depth analysis
        """
        if not order_book_data:
            return {}
        
        # Extract bid and ask levels
        bids = order_book_data.get('bids', [])
        asks = order_book_data.get('asks', [])
        
        if not bids or not asks:
            return {}
        
        # Calculate depth at different levels
        bid_depth_5 = sum(bid.get('quantity', 0) for bid in bids[:5])
        ask_depth_5 = sum(ask.get('quantity', 0) for ask in asks[:5])
        bid_depth_10 = sum(bid.get('quantity', 0) for bid in bids[:10])
        ask_depth_10 = sum(ask.get('quantity', 0) for ask in asks[:10])
        
        # Imbalance ratio
        total_depth = bid_depth_5 + ask_depth_5
        imbalance_ratio = (bid_depth_5 - ask_depth_5) / total_depth if total_depth > 0 else 0
        
        # Best bid/ask
        best_bid = bids[0].get('price', 0) if bids else 0
        best_ask = asks[0].get('price', 0) if asks else 0
        
        return {
            'best_bid': best_bid,
            'best_ask': best_ask,
            'bid_depth_5': bid_depth_5,
            'ask_depth_5': ask_depth_5,
            'bid_depth_10': bid_depth_10,
            'ask_depth_10': ask_depth_10,
            'total_depth_5': total_depth,
            'imbalance_ratio': round(imbalance_ratio, 4),
            'buyer_dominance': imbalance_ratio > 0.2,
            'seller_dominance': imbalance_ratio < -0.2,
        }
    
    def get_microstructure_features(self, ticker: str, ohlcv_df: pd.DataFrame, 
                                   order_book_data: Optional[Dict] = None) -> Dict[str, any]:
        """
        Get all microstructure features for a ticker.
        
        Args:
            ticker: Stock/index ticker
            ohlcv_df: OHLCV DataFrame
            order_book_data: Optional order book data from Upstox
        
        Returns:
            Complete microstructure analysis
        """
        features = {
            'ticker': ticker,
            'timestamp': datetime.now().isoformat(),
        }
        
        # Spread analysis
        spread_features = self.estimate_spread_from_ohlcv(ohlcv_df)
        features.update({f'spread_{k}': v for k, v in spread_features.items()})
        
        # Volume profile
        volume_profile = self.calculate_volume_profile(ohlcv_df)
        features.update({f'vp_{k}': v for k, v in volume_profile.items()})
        
        # Market impact
        market_impact = self.calculate_market_impact(ohlcv_df)
        features.update({f'impact_{k}': v for k, v in market_impact.items()})
        
        # Order book depth (if available)
        if order_book_data:
            order_book = self.analyze_order_book_depth(order_book_data)
            features.update({f'ob_{k}': v for k, v in order_book.items()})
            
            # Calculate actual spread from order book
            if order_book.get('best_bid') and order_book.get('best_ask'):
                actual_spread = self.calculate_bid_ask_spread(
                    order_book['best_bid'],
                    order_book['best_ask']
                )
                features.update({f'actual_spread_{k}': v for k, v in actual_spread.items()})
        
        return features


# Global instance
_microstructure_analyzer: Optional[MarketMicrostructureAnalyzer] = None

def get_microstructure_analyzer() -> MarketMicrostructureAnalyzer:
    """Get global MarketMicrostructureAnalyzer instance"""
    global _microstructure_analyzer
    if _microstructure_analyzer is None:
        _microstructure_analyzer = MarketMicrostructureAnalyzer()
    return _microstructure_analyzer
