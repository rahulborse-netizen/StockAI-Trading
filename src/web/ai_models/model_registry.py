"""
Model Registry
Manages ML models, their versions, and performance metrics
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import json
import joblib

logger = logging.getLogger(__name__)


class ModelMetadata:
    """Metadata for a trained model"""
    
    def __init__(
        self,
        model_id: str,
        model_type: str,
        version: str,
        feature_cols: List[str],
        performance_metrics: Dict,
        trained_date: datetime,
        model_path: Optional[str] = None
    ):
        self.model_id = model_id
        self.model_type = model_type  # 'logistic', 'lstm', 'xgboost', etc.
        self.version = version
        self.feature_cols = feature_cols
        self.performance_metrics = performance_metrics
        self.trained_date = trained_date
        self.model_path = model_path
        self.is_active = True
        self.prediction_count = 0
        self.last_used = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'model_id': self.model_id,
            'model_type': self.model_type,
            'version': self.version,
            'feature_cols': self.feature_cols,
            'performance_metrics': self.performance_metrics,
            'trained_date': self.trained_date.isoformat(),
            'model_path': self.model_path,
            'is_active': self.is_active,
            'prediction_count': self.prediction_count,
            'last_used': self.last_used.isoformat() if self.last_used else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ModelMetadata':
        """Create from dictionary"""
        metadata = cls(
            model_id=data['model_id'],
            model_type=data['model_type'],
            version=data['version'],
            feature_cols=data['feature_cols'],
            performance_metrics=data['performance_metrics'],
            trained_date=datetime.fromisoformat(data['trained_date']),
            model_path=data.get('model_path')
        )
        metadata.is_active = data.get('is_active', True)
        metadata.prediction_count = data.get('prediction_count', 0)
        if data.get('last_used'):
            metadata.last_used = datetime.fromisoformat(data['last_used'])
        return metadata


class ModelRegistry:
    """Registry for managing ML models"""
    
    def __init__(self, registry_path: str = 'data/models/registry.json'):
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.models: Dict[str, ModelMetadata] = {}
        self.load_registry()
    
    def load_registry(self) -> None:
        """Load model registry from disk"""
        try:
            if self.registry_path.exists():
                with open(self.registry_path, 'r') as f:
                    data = json.load(f)
                    self.models = {
                        model_id: ModelMetadata.from_dict(meta_data)
                        for model_id, meta_data in data.items()
                    }
                logger.info(f"Loaded {len(self.models)} models from registry")
        except Exception as e:
            logger.error(f"Error loading model registry: {e}")
            self.models = {}
    
    def save_registry(self) -> None:
        """Save model registry to disk"""
        try:
            data = {
                model_id: metadata.to_dict()
                for model_id, metadata in self.models.items()
            }
            with open(self.registry_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug("Model registry saved")
        except Exception as e:
            logger.error(f"Error saving model registry: {e}")
    
    def register_model(
        self,
        model_id: str,
        model_type: str,
        version: str,
        feature_cols: List[str],
        performance_metrics: Dict,
        model_path: Optional[str] = None
    ) -> ModelMetadata:
        """Register a new model"""
        metadata = ModelMetadata(
            model_id=model_id,
            model_type=model_type,
            version=version,
            feature_cols=feature_cols,
            performance_metrics=performance_metrics,
            trained_date=datetime.now(),
            model_path=model_path
        )
        
        self.models[model_id] = metadata
        self.save_registry()
        
        logger.info(f"Registered model: {model_id} ({model_type})")
        return metadata
    
    def get_model(self, model_id: str) -> Optional[ModelMetadata]:
        """Get model metadata"""
        return self.models.get(model_id)
    
    def get_active_models(self, model_type: Optional[str] = None) -> List[ModelMetadata]:
        """Get all active models, optionally filtered by type"""
        models = [
            metadata for metadata in self.models.values()
            if metadata.is_active
        ]
        
        if model_type:
            models = [m for m in models if m.model_type == model_type]
        
        # Sort by performance (if available)
        models.sort(
            key=lambda m: m.performance_metrics.get('accuracy', 0),
            reverse=True
        )
        
        return models
    
    def update_performance(
        self,
        model_id: str,
        metrics: Dict,
        increment_prediction_count: bool = True
    ) -> None:
        """Update model performance metrics"""
        if model_id in self.models:
            self.models[model_id].performance_metrics.update(metrics)
            if increment_prediction_count:
                self.models[model_id].prediction_count += 1
            self.models[model_id].last_used = datetime.now()
            self.save_registry()
    
    def deactivate_model(self, model_id: str) -> None:
        """Deactivate a model"""
        if model_id in self.models:
            self.models[model_id].is_active = False
            self.save_registry()
    
    def load_model_object(self, model_id: str):
        """Load actual model object from disk"""
        metadata = self.get_model(model_id)
        if not metadata or not metadata.model_path:
            return None
        
        try:
            model_path = Path(metadata.model_path)
            if model_path.exists():
                return joblib.load(model_path)
        except Exception as e:
            logger.error(f"Error loading model {model_id}: {e}")
        
        return None


# Global instance
_model_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    """Get global model registry instance"""
    global _model_registry
    if _model_registry is None:
        _model_registry = ModelRegistry()
    return _model_registry
