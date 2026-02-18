"""
Alternative Data Integration
Phase 2.2: Advanced Features - News sentiment, social media sentiment, options flow, economic indicators
"""
import logging
import requests
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)


class NewsSentimentAnalyzer:
    """
    Analyzes news sentiment for stocks/indices.
    Uses simple keyword-based sentiment analysis (can be enhanced with NLP models).
    """
    
    def __init__(self):
        self.sentiment_cache: Dict[str, Dict] = {}
        self.cache_ttl = 3600  # 1 hour
    
    def analyze_text_sentiment(self, text: str) -> Dict[str, float]:
        """
        Simple sentiment analysis using keyword matching.
        Returns sentiment score between -1 (very negative) and 1 (very positive).
        
        Args:
            text: News headline or article text
        
        Returns:
            Sentiment analysis results
        """
        if not text:
            return {'sentiment_score': 0.0, 'sentiment_label': 'NEUTRAL'}
        
        text_lower = text.lower()
        
        # Positive keywords (weighted)
        positive_keywords = {
            'surge': 0.3, 'rally': 0.3, 'gain': 0.2, 'rise': 0.2, 'up': 0.1,
            'bullish': 0.4, 'buy': 0.3, 'outperform': 0.3, 'upgrade': 0.3,
            'profit': 0.2, 'growth': 0.2, 'strong': 0.2, 'beat': 0.3,
            'positive': 0.2, 'optimistic': 0.2, 'breakthrough': 0.3,
        }
        
        # Negative keywords (weighted)
        negative_keywords = {
            'fall': 0.2, 'drop': 0.2, 'decline': 0.2, 'down': 0.1, 'plunge': 0.3,
            'bearish': 0.4, 'sell': 0.3, 'underperform': 0.3, 'downgrade': 0.3,
            'loss': 0.2, 'weak': 0.2, 'miss': 0.3, 'negative': 0.2,
            'concern': 0.2, 'risk': 0.2, 'crisis': 0.4, 'crash': 0.4,
        }
        
        # Calculate sentiment score
        positive_score = sum(weight for keyword, weight in positive_keywords.items() 
                           if keyword in text_lower)
        negative_score = sum(weight for keyword, weight in negative_keywords.items() 
                           if keyword in text_lower)
        
        # Normalize score
        total_score = positive_score - negative_score
        sentiment_score = max(-1.0, min(1.0, total_score / 2.0))  # Normalize to [-1, 1]
        
        # Determine label
        if sentiment_score > 0.3:
            sentiment_label = 'POSITIVE'
        elif sentiment_score < -0.3:
            sentiment_label = 'NEGATIVE'
        else:
            sentiment_label = 'NEUTRAL'
        
        return {
            'sentiment_score': round(sentiment_score, 3),
            'sentiment_label': sentiment_label,
            'positive_keywords_found': positive_score,
            'negative_keywords_found': negative_score,
        }
    
    def fetch_news_sentiment(self, ticker: str, use_cache: bool = True) -> Dict[str, any]:
        """
        Fetch and analyze news sentiment for a ticker.
        Currently uses mock data - can be integrated with news APIs.
        
        Args:
            ticker: Stock/index ticker
            use_cache: Whether to use cached results
        
        Returns:
            News sentiment analysis
        """
        # Check cache
        if use_cache and ticker in self.sentiment_cache:
            cached = self.sentiment_cache[ticker]
            age = (datetime.now() - cached['timestamp']).total_seconds()
            if age < self.cache_ttl:
                return cached['data']
        
        # TODO: Integrate with actual news API (NewsAPI, Alpha Vantage, etc.)
        # For now, return neutral sentiment
        result = {
            'ticker': ticker,
            'sentiment_score': 0.0,
            'sentiment_label': 'NEUTRAL',
            'news_count': 0,
            'last_updated': datetime.now().isoformat(),
            'source': 'mock',
        }
        
        # Cache result
        self.sentiment_cache[ticker] = {
            'data': result,
            'timestamp': datetime.now(),
        }
        
        return result


class OptionsFlowAnalyzer:
    """
    Analyzes options flow data to identify unusual activity.
    Can be integrated with Upstox options chain API.
    """
    
    def analyze_options_flow(self, options_chain_data: Dict) -> Dict[str, any]:
        """
        Analyze options flow for unusual activity.
        
        Args:
            options_chain_data: Options chain data from Upstox
        
        Returns:
            Options flow analysis
        """
        if not options_chain_data:
            return {}
        
        # Extract call and put data
        calls = options_chain_data.get('call_options', [])
        puts = options_chain_data.get('put_options', [])
        
        if not calls and not puts:
            return {}
        
        # Calculate total call/put volume and OI
        total_call_volume = sum(c.get('volume', 0) for c in calls)
        total_put_volume = sum(p.get('volume', 0) for p in puts)
        total_call_oi = sum(c.get('open_interest', 0) for c in calls)
        total_put_oi = sum(p.get('open_interest', 0) for p in puts)
        
        # Put-Call Ratio
        pcr_volume = total_put_volume / total_call_volume if total_call_volume > 0 else 0
        pcr_oi = total_put_oi / total_call_oi if total_call_oi > 0 else 0
        
        # Find unusual activity (high volume relative to OI)
        unusual_calls = [c for c in calls if c.get('volume', 0) > c.get('open_interest', 0) * 0.5]
        unusual_puts = [p for p in puts if p.get('volume', 0) > p.get('open_interest', 0) * 0.5]
        
        # Bullish/Bearish signal
        # High call volume = bullish, High put volume = bearish
        call_put_ratio = total_call_volume / total_put_volume if total_put_volume > 0 else 0
        
        return {
            'total_call_volume': total_call_volume,
            'total_put_volume': total_put_volume,
            'total_call_oi': total_call_oi,
            'total_put_oi': total_put_oi,
            'pcr_volume': round(pcr_volume, 4),
            'pcr_oi': round(pcr_oi, 4),
            'call_put_ratio': round(call_put_ratio, 4),
            'unusual_call_count': len(unusual_calls),
            'unusual_put_count': len(unusual_puts),
            'bullish_signal': call_put_ratio > 1.2,
            'bearish_signal': call_put_ratio < 0.8,
            'neutral_signal': 0.8 <= call_put_ratio <= 1.2,
        }


class EconomicIndicators:
    """
    Economic indicators integration.
    Can fetch data from APIs like FRED, Trading Economics, etc.
    """
    
    def get_india_economic_indicators(self) -> Dict[str, any]:
        """
        Get key Indian economic indicators.
        Currently returns mock data - can be integrated with economic data APIs.
        
        Returns:
            Economic indicators data
        """
        # TODO: Integrate with economic data APIs
        # For now, return structure
        return {
            'gdp_growth': None,
            'inflation_rate': None,
            'repo_rate': None,
            'usd_inr': None,
            'crude_oil_price': None,
            'gold_price': None,
            'last_updated': datetime.now().isoformat(),
            'source': 'mock',
        }


class AlternativeDataManager:
    """
    Manages all alternative data sources.
    """
    
    def __init__(self):
        self.news_analyzer = NewsSentimentAnalyzer()
        self.options_flow_analyzer = OptionsFlowAnalyzer()
        self.economic_indicators = EconomicIndicators()
    
    def get_alternative_data_features(self, ticker: str, 
                                     options_chain_data: Optional[Dict] = None) -> Dict[str, any]:
        """
        Get all alternative data features for a ticker.
        
        Args:
            ticker: Stock/index ticker
            options_chain_data: Optional options chain data
        
        Returns:
            Combined alternative data features
        """
        features = {
            'ticker': ticker,
            'timestamp': datetime.now().isoformat(),
        }
        
        # News sentiment
        news_sentiment = self.news_analyzer.fetch_news_sentiment(ticker)
        features.update({f'news_{k}': v for k, v in news_sentiment.items()})
        
        # Options flow (if available)
        if options_chain_data:
            options_flow = self.options_flow_analyzer.analyze_options_flow(options_chain_data)
            features.update({f'options_{k}': v for k, v in options_flow.items()})
        
        # Economic indicators (for indices)
        if ticker.startswith('^'):
            economic_data = self.economic_indicators.get_india_economic_indicators()
            features.update({f'econ_{k}': v for k, v in economic_data.items()})
        
        return features


# Global instance
_alternative_data_manager: Optional[AlternativeDataManager] = None

def get_alternative_data_manager() -> AlternativeDataManager:
    """Get global AlternativeDataManager instance"""
    global _alternative_data_manager
    if _alternative_data_manager is None:
        _alternative_data_manager = AlternativeDataManager()
    return _alternative_data_manager
