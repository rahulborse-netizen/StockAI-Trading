"""
XGBoost Predictor
Gradient boosting model for enhanced predictions
"""
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logger.warning("XGBoost not available. Install with: pip install xgboost")


class XGBoostPredictor:
    """XGBoost model for stock prediction"""
    
    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 6,
        learning_rate: float = 0.1,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        random_state: int = 42
    ):
        if not XGBOOST_AVAILABLE:
            raise ImportError("XGBoost is not installed. Install with: pip install xgboost")
        
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.random_state = random_state
        self.model = None
        self.feature_cols: List[str] = []
        self.is_trained = False
    
    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        feature_cols: List[str],
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None
    ) -> Dict:
        """
        Train XGBoost model
        
        Args:
            X_train: Training features
            y_train: Training labels
            feature_cols: List of feature column names
            X_val: Validation features (optional)
            y_val: Validation labels (optional)
        
        Returns:
            Training metrics dictionary
        """
        self.feature_cols = feature_cols
        
        # Prepare data
        X_train_vals = X_train[feature_cols].fillna(0).values
        y_train_vals = y_train.values
        
        # Create XGBoost model
        self.model = xgb.XGBClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            random_state=self.random_state,
            eval_metric='logloss',
            use_label_encoder=False
        )
        
        # Train with validation set if provided
        if X_val is not None and y_val is not None:
            X_val_vals = X_val[feature_cols].fillna(0).values
            y_val_vals = y_val.values
            
            self.model.fit(
                X_train_vals,
                y_train_vals,
                eval_set=[(X_val_vals, y_val_vals)],
                verbose=False
            )
            
            # Get validation accuracy
            val_pred = self.model.predict(X_val_vals)
            val_accuracy = np.mean(val_pred == y_val_vals)
        else:
            self.model.fit(X_train_vals, y_train_vals, verbose=False)
            val_accuracy = None
        
        # Training accuracy
        train_pred = self.model.predict(X_train_vals)
        train_accuracy = np.mean(train_pred == y_train_vals)
        
        self.is_trained = True
        
        metrics = {
            'train_accuracy': float(train_accuracy),
            'val_accuracy': float(val_accuracy) if val_accuracy else None,
            'n_estimators': self.n_estimators,
            'feature_importance': self._get_feature_importance()
        }
        
        logger.info(f"XGBoost trained: train_acc={train_accuracy:.3f}, val_acc={val_accuracy:.3f if val_accuracy else 'N/A'}")
        
        return metrics
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict probabilities
        
        Args:
            X: Feature dataframe
        
        Returns:
            Array of probabilities for class 1
        """
        if not self.is_trained or self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        X_vals = X[self.feature_cols].fillna(0).values
        proba = self.model.predict_proba(X_vals)
        return proba[:, 1]  # Return probability of positive class
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict classes
        
        Args:
            X: Feature dataframe
        
        Returns:
            Array of predicted classes
        """
        if not self.is_trained or self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        X_vals = X[self.feature_cols].fillna(0).values
        return self.model.predict(X_vals)
    
    def _get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores"""
        if self.model is None:
            return {}
        
        try:
            importance = self.model.feature_importances_
            return {
                feature: float(importance[i])
                for i, feature in enumerate(self.feature_cols)
            }
        except:
            return {}
    
    def save_model(self, path: str) -> None:
        """Save model to disk"""
        import joblib
        if self.model is None:
            raise ValueError("No model to save")
        
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            'model': self.model,
            'feature_cols': self.feature_cols,
            'params': {
                'n_estimators': self.n_estimators,
                'max_depth': self.max_depth,
                'learning_rate': self.learning_rate
            }
        }, path)
        logger.info(f"XGBoost model saved to {path}")
    
    @classmethod
    def load_model(cls, path: str) -> 'XGBoostPredictor':
        """Load model from disk"""
        import joblib
        data = joblib.load(path)
        
        predictor = cls(**data['params'])
        predictor.model = data['model']
        predictor.feature_cols = data['feature_cols']
        predictor.is_trained = True
        
        return predictor
