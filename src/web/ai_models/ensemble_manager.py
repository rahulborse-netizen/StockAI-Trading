"""
Ensemble Manager
Combines multiple ML models for superior predictions
"""
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from src.web.ai_models.model_registry import get_model_registry

logger = logging.getLogger(__name__)


class EnsembleManager:
    """Manages ensemble of ML models"""
    
    def __init__(self):
        self.registry = get_model_registry()
        self.model_weights: Dict[str, float] = {}
        self.ensemble_method = 'weighted_average'  # 'weighted_average', 'voting', 'stacking'
        self._initialize_weights()
    
    def _initialize_weights(self) -> None:
        """Initialize model weights based on performance"""
        active_models = self.registry.get_active_models()
        
        if not active_models:
            logger.warning("No active models found in registry")
            return
        
        # Calculate weights based on performance metrics
        total_score = 0
        scores = {}
        
        for model in active_models:
            # Composite score: accuracy * (1 - drawdown) * win_rate
            accuracy = model.performance_metrics.get('accuracy', 0.5)
            sharpe = model.performance_metrics.get('sharpe_ratio', 0.0)
            win_rate = model.performance_metrics.get('win_rate', 0.5)
            
            # Normalize sharpe (assuming range -2 to 5)
            normalized_sharpe = max(0, (sharpe + 2) / 7)
            
            score = accuracy * 0.4 + normalized_sharpe * 0.4 + win_rate * 0.2
            scores[model.model_id] = score
            total_score += score
        
        # Normalize weights
        if total_score > 0:
            self.model_weights = {
                model_id: score / total_score
                for model_id, score in scores.items()
            }
        else:
            # Equal weights if no performance data
            weight = 1.0 / len(active_models)
            self.model_weights = {
                model.model_id: weight
                for model in active_models
            }
        
        logger.info(f"Initialized ensemble weights: {self.model_weights}")
    
    def predict_ensemble(
        self,
        predictions: Dict[str, float],
        confidence_scores: Optional[Dict[str, float]] = None
    ) -> Dict:
        """
        Combine predictions from multiple models
        
        Args:
            predictions: Dictionary of model_id -> probability
            confidence_scores: Optional confidence scores for each model
        
        Returns:
            Ensemble prediction with confidence
        """
        if not predictions:
            return {
                'probability': 0.5,
                'confidence': 0.0,
                'method': self.ensemble_method,
                'model_count': 0
            }
        
        # Filter to active models only
        active_predictions = {
            model_id: prob
            for model_id, prob in predictions.items()
            if self.registry.get_model(model_id) and self.registry.get_model(model_id).is_active
        }
        
        if not active_predictions:
            return {
                'probability': 0.5,
                'confidence': 0.0,
                'method': self.ensemble_method,
                'model_count': 0
            }
        
        if self.ensemble_method == 'weighted_average':
            return self._weighted_average(active_predictions, confidence_scores)
        elif self.ensemble_method == 'voting':
            return self._voting(active_predictions)
        elif self.ensemble_method == 'stacking':
            return self._stacking(active_predictions)
        else:
            return self._weighted_average(active_predictions, confidence_scores)
    
    def _weighted_average(
        self,
        predictions: Dict[str, float],
        confidence_scores: Optional[Dict[str, float]] = None
    ) -> Dict:
        """Weighted average ensemble"""
        total_weight = 0
        weighted_sum = 0
        
        for model_id, prob in predictions.items():
            # Use confidence-adjusted weight if available
            if confidence_scores and model_id in confidence_scores:
                weight = self.model_weights.get(model_id, 1.0) * confidence_scores[model_id]
            else:
                weight = self.model_weights.get(model_id, 1.0)
            
            weighted_sum += prob * weight
            total_weight += weight
        
        ensemble_prob = weighted_sum / total_weight if total_weight > 0 else 0.5
        
        # Calculate confidence as agreement between models
        probs = list(predictions.values())
        std_dev = np.std(probs)
        confidence = max(0, 1 - (std_dev * 2))  # Higher agreement = higher confidence
        
        return {
            'probability': float(ensemble_prob),
            'confidence': float(confidence),
            'method': 'weighted_average',
            'model_count': len(predictions),
            'individual_predictions': predictions,
            'weights_used': {
                model_id: self.model_weights.get(model_id, 0)
                for model_id in predictions.keys()
            }
        }
    
    def _voting(self, predictions: Dict[str, float]) -> Dict:
        """Majority voting ensemble"""
        # Convert probabilities to votes
        votes = []
        for prob in predictions.values():
            if prob >= 0.6:
                votes.append(1)  # Strong buy
            elif prob >= 0.5:
                votes.append(0.5)  # Weak buy
            elif prob >= 0.4:
                votes.append(-0.5)  # Weak sell
            else:
                votes.append(-1)  # Strong sell
        
        avg_vote = np.mean(votes)
        # Convert vote back to probability
        ensemble_prob = (avg_vote + 1) / 2
        
        # Confidence based on vote agreement
        vote_std = np.std(votes)
        confidence = max(0, 1 - vote_std)
        
        return {
            'probability': float(ensemble_prob),
            'confidence': float(confidence),
            'method': 'voting',
            'model_count': len(predictions),
            'individual_predictions': predictions
        }
    
    def _stacking(self, predictions: Dict[str, float]) -> Dict:
        """Stacking ensemble (simplified - would need meta-learner in production)"""
        # For now, use weighted average as stacking approximation
        return self._weighted_average(predictions)
    
    def update_weights(self, performance_data: Dict[str, Dict]) -> None:
        """
        Update model weights based on recent performance
        
        Args:
            performance_data: Dictionary of model_id -> performance metrics
        """
        total_score = 0
        new_weights = {}
        
        for model_id, metrics in performance_data.items():
            accuracy = metrics.get('accuracy', 0.5)
            sharpe = metrics.get('sharpe_ratio', 0.0)
            win_rate = metrics.get('win_rate', 0.5)
            
            normalized_sharpe = max(0, (sharpe + 2) / 7)
            score = accuracy * 0.4 + normalized_sharpe * 0.4 + win_rate * 0.2
            
            new_weights[model_id] = score
            total_score += score
        
        if total_score > 0:
            self.model_weights = {
                model_id: score / total_score
                for model_id, score in new_weights.items()
            }
            logger.info(f"Updated ensemble weights: {self.model_weights}")
    
    def get_best_models(self, n: int = 3) -> List[str]:
        """Get top N best performing models"""
        active_models = self.registry.get_active_models()
        
        # Sort by performance
        sorted_models = sorted(
            active_models,
            key=lambda m: m.performance_metrics.get('accuracy', 0),
            reverse=True
        )
        
        return [model.model_id for model in sorted_models[:n]]


# Global instance
_ensemble_manager: Optional[EnsembleManager] = None


def get_ensemble_manager() -> EnsembleManager:
    """Get global ensemble manager instance"""
    global _ensemble_manager
    if _ensemble_manager is None:
        _ensemble_manager = EnsembleManager()
    return _ensemble_manager
