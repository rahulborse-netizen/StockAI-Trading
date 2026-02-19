"""
Phase 2.3: MLOps Pipeline
Automated training, model versioning, A/B testing, performance monitoring, explainability.
"""
from src.web.mlops.pipeline import get_training_pipeline
from src.web.mlops.ab_testing import get_ab_test_manager
from src.web.mlops.explainability import get_explainability_manager
from src.web.mlops.monitoring import get_ml_monitor

__all__ = [
    'get_training_pipeline',
    'get_ab_test_manager',
    'get_explainability_manager',
    'get_ml_monitor',
]
