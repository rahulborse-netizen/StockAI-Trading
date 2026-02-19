"""
Phase 2.3: Automated model training pipeline and retraining triggers.
"""
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import json

logger = logging.getLogger(__name__)


class TrainingPipeline:
    """Automated model training pipeline with versioning and triggers."""

    def __init__(
        self,
        registry_path: str = 'data/models/registry.json',
        pipeline_state_path: str = 'data/models/pipeline_state.json',
    ):
        self.registry_path = Path(registry_path)
        self.state_path = Path(pipeline_state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state: Dict[str, Any] = {
            'last_training_run': None,
            'last_successful_run': None,
            'retrain_trigger_count': 0,
            'scheduled_next': None,
            'training_in_progress': False,
        }
        self._load_state()
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _load_state(self) -> None:
        try:
            if self.state_path.exists():
                with open(self.state_path, 'r') as f:
                    self._state = {**self._state, **json.load(f)}
        except Exception as e:
            logger.debug(f"Could not load pipeline state: {e}")

    def _save_state(self) -> None:
        try:
            with open(self.state_path, 'w') as f:
                json.dump(self._state, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save pipeline state: {e}")

    def trigger_retrain(self, reason: str = 'manual') -> Dict[str, Any]:
        """
        Trigger a retraining run. In production this would invoke actual model training.
        """
        with self._lock:
            if self._state.get('training_in_progress'):
                return {
                    'status': 'skipped',
                    'message': 'Training already in progress',
                    'triggered_at': datetime.now().isoformat(),
                }
            self._state['training_in_progress'] = True
            self._state['last_training_run'] = datetime.now().isoformat()
            self._state['retrain_trigger_count'] = self._state.get('retrain_trigger_count', 0) + 1
            self._save_state()

        try:
            # Placeholder: real implementation would call ensemble/retrain logic
            from src.web.ai_models.model_registry import get_model_registry
            registry = get_model_registry()
            active = registry.get_active_models()
            # Simulate training completion
            self._state['last_successful_run'] = datetime.now().isoformat()
            self._state['last_run_models_updated'] = len(active)
            logger.info(f"[MLOps] Retrain triggered ({reason}). Active models: {len(active)}")
        except Exception as e:
            logger.exception(f"[MLOps] Training run failed: {e}")
        finally:
            with self._lock:
                self._state['training_in_progress'] = False
                self._save_state()

        return {
            'status': 'completed',
            'reason': reason,
            'triggered_at': self._state['last_training_run'],
            'completed_at': self._state.get('last_successful_run'),
        }

    def schedule_retrain(self, interval_hours: float = 168) -> None:
        """Schedule next retrain (default 168h = 1 week)."""
        next_run = datetime.now() + timedelta(hours=interval_hours)
        self._state['scheduled_next'] = next_run.isoformat()
        self._save_state()
        logger.info(f"[MLOps] Next retrain scheduled for {next_run.isoformat()}")

    def check_retrain_trigger(
        self,
        accuracy_drop_threshold: float = 0.05,
        min_predictions_for_trigger: int = 100,
    ) -> bool:
        """
        Check if retraining should be triggered based on performance drift.
        Returns True if trigger conditions are met.
        """
        try:
            from src.web.ai_models.performance_tracker import get_performance_tracker
            tracker = get_performance_tracker()
            # Compare recent vs older accuracy per model
            for model_id, records in (tracker.performance_history or {}).items():
                if len(records) < min_predictions_for_trigger:
                    continue
                with_correct = [r for r in records if r.get('correct') is not None]
                if len(with_correct) < 20:
                    continue
                n = len(with_correct)
                baseline = sum(1 for r in with_correct[: n // 2] if r['correct']) / (n // 2 or 1)
                recent = sum(1 for r in with_correct[-n // 2:] if r['correct']) / (n // 2 or 1)
                if baseline - recent >= accuracy_drop_threshold:
                    logger.info(f"[MLOps] Accuracy drift detected for {model_id}: {baseline:.3f} -> {recent:.3f}")
                    return True
        except Exception as e:
            logger.debug(f"[MLOps] Retrain check failed: {e}")
        return False

    def get_status(self) -> Dict[str, Any]:
        """Return pipeline status for API."""
        with self._lock:
            return {
                'last_training_run': self._state.get('last_training_run'),
                'last_successful_run': self._state.get('last_successful_run'),
                'training_in_progress': self._state.get('training_in_progress', False),
                'retrain_trigger_count': self._state.get('retrain_trigger_count', 0),
                'scheduled_next': self._state.get('scheduled_next'),
            }


_pipeline: Optional[TrainingPipeline] = None


def get_training_pipeline() -> TrainingPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = TrainingPipeline()
    return _pipeline
