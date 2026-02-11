"""
Model Performance Tracker
Track and compare model performance over time
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pathlib import Path
import json

from src.web.ai_models.model_registry import get_model_registry

logger = logging.getLogger(__name__)


def _normalize_ticker(ticker: str) -> str:
    """Normalize ticker for matching (e.g. RELIANCE.NS, RELIANCE-EQ -> RELIANCE)."""
    if not ticker:
        return ''
    t = str(ticker).strip().upper()
    for suffix in ('.NS', '.BO', '.NSE', '.BSE', '-EQ', '-NSE', '-BSE'):
        if t.endswith(suffix):
            t = t[:-len(suffix)]
    return t


class PerformanceTracker:
    """Track model performance metrics and pending predictions for accuracy feedback."""
    
    def __init__(self, storage_path: str = 'data/models/performance.json', pending_path: Optional[str] = None):
        self.storage_path = Path(storage_path)
        self.pending_path = Path(pending_path or 'data/models/pending_predictions.json')
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.pending_path.parent.mkdir(parents=True, exist_ok=True)
        self.performance_history: Dict[str, List[Dict]] = {}
        self.pending_predictions: List[Dict] = []
        self.load_history()
        self._load_pending()
    
    def _load_pending(self) -> None:
        try:
            if self.pending_path.exists():
                with open(self.pending_path, 'r') as f:
                    self.pending_predictions = json.load(f)
        except Exception as e:
            logger.debug(f"Could not load pending predictions: {e}")
            self.pending_predictions = []
    
    def _save_pending(self) -> None:
        try:
            with open(self.pending_path, 'w') as f:
                json.dump(self.pending_predictions, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save pending predictions: {e}")
    
    def add_pending(
        self,
        model_id: str,
        ticker: str,
        prediction: float,
        entry_price: float,
        timestamp: Optional[datetime] = None
    ) -> None:
        """Store a pending prediction (call when a BUY is executed)."""
        if timestamp is None:
            timestamp = datetime.now()
        self.pending_predictions.append({
            'model_id': model_id,
            'ticker': _normalize_ticker(ticker),
            'prediction': float(prediction),
            'entry_price': float(entry_price),
            'timestamp': timestamp.isoformat(),
        })
        self._save_pending()
    
    def resolve_pending(self, ticker: str, exit_price: float) -> bool:
        """
        Resolve the oldest pending prediction for this ticker (call when position is closed).
        Computes actual_return, records via record_prediction, removes pending.
        Returns True if a pending was resolved.
        """
        normalized = _normalize_ticker(ticker)
        for i, p in enumerate(self.pending_predictions):
            if p.get('ticker') != normalized:
                continue
            entry_price = float(p.get('entry_price', 0))
            if entry_price <= 0:
                self.pending_predictions.pop(i)
                self._save_pending()
                return False
            actual_return = (exit_price - entry_price) / entry_price
            self.record_prediction(
                model_id=p['model_id'],
                ticker=ticker,
                prediction=p['prediction'],
                actual_return=actual_return,
                timestamp=datetime.fromisoformat(p['timestamp']) if isinstance(p.get('timestamp'), str) else None
            )
            self.pending_predictions.pop(i)
            self._save_pending()
            return True
        return False
    
    def load_history(self) -> None:
        """Load performance history from disk"""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r') as f:
                    self.performance_history = json.load(f)
                logger.info(f"Loaded performance history for {len(self.performance_history)} models")
        except Exception as e:
            logger.error(f"Error loading performance history: {e}")
            self.performance_history = {}
    
    def save_history(self) -> None:
        """Save performance history to disk"""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.performance_history, f, indent=2)
            logger.debug("Performance history saved")
        except Exception as e:
            logger.error(f"Error saving performance history: {e}")
    
    def record_prediction(
        self,
        model_id: str,
        ticker: str,
        prediction: float,
        actual_return: Optional[float] = None,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Record a prediction for later evaluation
        
        Args:
            model_id: Model identifier
            ticker: Stock ticker
            prediction: Predicted probability
            actual_return: Actual return (if available)
            timestamp: Prediction timestamp
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        if model_id not in self.performance_history:
            self.performance_history[model_id] = []
        
        record = {
            'timestamp': timestamp.isoformat(),
            'ticker': ticker,
            'prediction': float(prediction),
            'actual_return': float(actual_return) if actual_return is not None else None,
            'predicted_signal': 'BUY' if prediction >= 0.6 else ('SELL' if prediction <= 0.4 else 'HOLD'),
            'correct': None
        }
        
        # Calculate correctness if actual return available
        if actual_return is not None:
            if record['predicted_signal'] == 'BUY' and actual_return > 0:
                record['correct'] = True
            elif record['predicted_signal'] == 'SELL' and actual_return < 0:
                record['correct'] = True
            elif record['predicted_signal'] == 'HOLD':
                record['correct'] = None  # Can't evaluate HOLD
            else:
                record['correct'] = False
        
        self.performance_history[model_id].append(record)
        
        # Keep only last 10000 records per model
        if len(self.performance_history[model_id]) > 10000:
            self.performance_history[model_id] = self.performance_history[model_id][-10000:]
        
        self.save_history()
    
    def calculate_metrics(
        self,
        model_id: str,
        days: int = 30
    ) -> Dict:
        """
        Calculate performance metrics for a model
        
        Args:
            model_id: Model identifier
            days: Number of days to analyze
        
        Returns:
            Dictionary of performance metrics
        """
        if model_id not in self.performance_history:
            return {
                'error': 'No performance data found',
                'model_id': model_id
            }
        
        records = self.performance_history[model_id]
        
        # Filter by date
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_records = [
            r for r in records
            if datetime.fromisoformat(r['timestamp']) >= cutoff_date
        ]
        
        if not recent_records:
            return {
                'error': 'No recent performance data',
                'model_id': model_id,
                'days': days
            }
        
        # Calculate metrics
        total_predictions = len(recent_records)
        evaluated_predictions = [r for r in recent_records if r['correct'] is not None]
        
        if not evaluated_predictions:
            return {
                'model_id': model_id,
                'total_predictions': total_predictions,
                'evaluated_predictions': 0,
                'error': 'No evaluated predictions available'
            }
        
        correct_predictions = sum(1 for r in evaluated_predictions if r['correct'])
        accuracy = correct_predictions / len(evaluated_predictions) if evaluated_predictions else 0
        
        # Calculate returns for BUY signals
        buy_signals = [r for r in evaluated_predictions if r['predicted_signal'] == 'BUY' and r['actual_return'] is not None]
        sell_signals = [r for r in evaluated_predictions if r['predicted_signal'] == 'SELL' and r['actual_return'] is not None]
        
        avg_return_buy = np.mean([r['actual_return'] for r in buy_signals]) if buy_signals else 0
        avg_return_sell = np.mean([r['actual_return'] for r in sell_signals]) if sell_signals else 0
        
        # Calculate win rate
        winning_trades = [r for r in buy_signals if r['actual_return'] > 0] + [r for r in sell_signals if r['actual_return'] < 0]
        win_rate = len(winning_trades) / len(evaluated_predictions) if evaluated_predictions else 0
        
        # Calculate Sharpe ratio (simplified)
        returns = [r['actual_return'] for r in evaluated_predictions if r['actual_return'] is not None]
        if len(returns) > 1:
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        else:
            sharpe_ratio = 0
        
        metrics = {
            'model_id': model_id,
            'period_days': days,
            'total_predictions': total_predictions,
            'evaluated_predictions': len(evaluated_predictions),
            'accuracy': float(accuracy),
            'win_rate': float(win_rate),
            'correct_predictions': correct_predictions,
            'avg_return_buy': float(avg_return_buy),
            'avg_return_sell': float(avg_return_sell),
            'sharpe_ratio': float(sharpe_ratio),
            'buy_signals': len(buy_signals),
            'sell_signals': len(sell_signals),
            'timestamp': datetime.now().isoformat()
        }
        
        return metrics
    
    def compare_models(self, model_ids: List[str], days: int = 30) -> Dict:
        """
        Compare performance of multiple models
        
        Args:
            model_ids: List of model identifiers
            days: Number of days to analyze
        
        Returns:
            Comparison results
        """
        comparison = {
            'models': {},
            'best_model': None,
            'comparison_date': datetime.now().isoformat(),
            'period_days': days
        }
        
        best_accuracy = 0
        best_model_id = None
        
        for model_id in model_ids:
            metrics = self.calculate_metrics(model_id, days)
            comparison['models'][model_id] = metrics
            
            if 'accuracy' in metrics and metrics['accuracy'] > best_accuracy:
                best_accuracy = metrics['accuracy']
                best_model_id = model_id
        
        comparison['best_model'] = best_model_id
        
        return comparison
    
    def get_model_rankings(self, days: int = 30) -> List[Dict]:
        """
        Get ranked list of models by performance
        
        Args:
            days: Number of days to analyze
        
        Returns:
            List of models ranked by performance
        """
        registry = get_model_registry()
        active_models = registry.get_active_models()
        
        rankings = []
        
        for model in active_models:
            metrics = self.calculate_metrics(model.model_id, days)
            if 'error' not in metrics:
                rankings.append({
                    'model_id': model.model_id,
                    'model_type': model.model_type,
                    **metrics
                })
        
        # Sort by accuracy
        rankings.sort(key=lambda x: x.get('accuracy', 0), reverse=True)
        
        return rankings


# Global instance
_performance_tracker: Optional[PerformanceTracker] = None


def get_performance_tracker() -> PerformanceTracker:
    """Get global performance tracker instance"""
    global _performance_tracker
    if _performance_tracker is None:
        _performance_tracker = PerformanceTracker()
    return _performance_tracker
