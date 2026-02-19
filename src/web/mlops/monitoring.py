"""
Phase 2.3: Model performance monitoring and alerts.
"""
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import json

logger = logging.getLogger(__name__)


class MLMonitor:
    """Monitor model performance and trigger alerts."""

    def __init__(self, state_path: str = 'data/models/monitoring_alerts.json'):
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._alerts: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        try:
            if self.state_path.exists():
                with open(self.state_path, 'r') as f:
                    data = json.load(f)
                    self._alerts = data.get('alerts', [])
        except Exception as e:
            logger.debug(f"Could not load monitoring state: {e}")

    def _save(self) -> None:
        try:
            with open(self.state_path, 'w') as f:
                json.dump({'alerts': self._alerts[-500:]}, f, indent=2)  # keep last 500
        except Exception as e:
            logger.warning(f"Could not save monitoring state: {e}")

    def record_metric(
        self,
        model_id: str,
        metric_name: str,
        value: float,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Record a performance metric for monitoring."""
        self._alerts.append({
            'type': 'metric',
            'model_id': model_id,
            'metric_name': metric_name,
            'value': value,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat(),
        })
        self._save()

    def check_threshold(
        self,
        model_id: str,
        metric_name: str,
        value: float,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Check if value is outside thresholds and return alert if so."""
        alert = None
        if min_value is not None and value < min_value:
            alert = {
                'type': 'threshold_below',
                'model_id': model_id,
                'metric_name': metric_name,
                'value': value,
                'threshold': min_value,
                'timestamp': datetime.now().isoformat(),
            }
        if max_value is not None and value > max_value:
            alert = {
                'type': 'threshold_above',
                'model_id': model_id,
                'metric_name': metric_name,
                'value': value,
                'threshold': max_value,
                'timestamp': datetime.now().isoformat(),
            }
        if alert:
            self._alerts.append(alert)
            self._save()
        return alert

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Aggregate metrics for dashboard (last 24h)."""
        try:
            from src.web.ai_models.model_registry import get_model_registry
            from src.web.ai_models.performance_tracker import get_performance_tracker
        except ImportError:
            return {'error': 'Dependencies not available'}

        registry = get_model_registry()
        tracker = get_performance_tracker()
        cutoff = (datetime.now() - timedelta(hours=24)).isoformat()

        models = registry.get_active_models()
        recent = []
        for recs in (tracker.performance_history or {}).values():
            recent.extend(r for r in recs if r.get('timestamp', '') >= cutoff)

        return {
            'active_models': len(models),
            'predictions_last_24h': len(recent),
            'alerts_last_24h': len([a for a in self._alerts if a.get('timestamp', '') >= cutoff]),
            'model_summary': [
                {
                    'model_id': m.model_id,
                    'model_type': m.model_type,
                    'accuracy': m.performance_metrics.get('accuracy'),
                    'prediction_count': m.prediction_count,
                }
                for m in models
            ],
        }

    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return most recent alerts."""
        return list(reversed(self._alerts[-limit:]))


_ml_monitor: Optional[MLMonitor] = None


def get_ml_monitor() -> MLMonitor:
    global _ml_monitor
    if _ml_monitor is None:
        _ml_monitor = MLMonitor()
    return _ml_monitor
