"""
Phase 2.3: A/B testing framework for models.
"""
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import json

logger = logging.getLogger(__name__)


class ABTestManager:
    """A/B testing for model variants (e.g. control vs new model)."""

    def __init__(self, state_path: str = 'data/models/ab_tests.json'):
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._experiments: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        try:
            if self.state_path.exists():
                with open(self.state_path, 'r') as f:
                    self._experiments = json.load(f)
        except Exception as e:
            logger.debug(f"Could not load A/B test state: {e}")
            self._experiments = {}

    def _save(self) -> None:
        try:
            with open(self.state_path, 'w') as f:
                json.dump(self._experiments, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save A/B test state: {e}")

    def create_experiment(
        self,
        experiment_id: str,
        control_model_id: str,
        variant_model_id: str,
        traffic_split: float = 0.5,
    ) -> Dict[str, Any]:
        """Create an A/B experiment: control vs variant with traffic split."""
        self._experiments[experiment_id] = {
            'experiment_id': experiment_id,
            'control_model_id': control_model_id,
            'variant_model_id': variant_model_id,
            'traffic_split': max(0.0, min(1.0, traffic_split)),
            'control_assignments': 0,
            'variant_assignments': 0,
            'control_metrics': {'correct': 0, 'total': 0},
            'variant_metrics': {'correct': 0, 'total': 0},
            'created_at': datetime.now().isoformat(),
            'status': 'running',
        }
        self._save()
        return self._experiments[experiment_id]

    def assign_variant(self, experiment_id: str) -> str:
        """Assign user/request to control or variant. Returns 'control' or 'variant'."""
        exp = self._experiments.get(experiment_id)
        if not exp or exp.get('status') != 'running':
            return 'control'
        split = exp.get('traffic_split', 0.5)
        if random.random() < split:
            exp['variant_assignments'] = exp.get('variant_assignments', 0) + 1
            self._save()
            return 'variant'
        exp['control_assignments'] = exp.get('control_assignments', 0) + 1
        self._save()
        return 'control'

    def record_outcome(
        self,
        experiment_id: str,
        variant: str,
        correct: bool,
    ) -> None:
        """Record outcome (e.g. prediction was correct) for the assigned variant."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return
        key = 'control_metrics' if variant == 'control' else 'variant_metrics'
        m = exp.get(key, {'correct': 0, 'total': 0})
        m['total'] = m.get('total', 0) + 1
        if correct:
            m['correct'] = m.get('correct', 0) + 1
        exp[key] = m
        self._save()

    def get_experiment_results(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get experiment stats and whether variant is winning."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return None
        c = exp.get('control_metrics', {})
        v = exp.get('variant_metrics', {})
        c_acc = c['correct'] / c['total'] if c.get('total') else 0
        v_acc = v['correct'] / v['total'] if v.get('total') else 0
        return {
            **exp,
            'control_accuracy': c_acc,
            'variant_accuracy': v_acc,
            'variant_winning': v_acc > c_acc,
        }

    def list_experiments(self) -> List[Dict[str, Any]]:
        """List all experiments."""
        return list(self._experiments.values())

    def stop_experiment(self, experiment_id: str) -> None:
        """Stop an experiment."""
        if experiment_id in self._experiments:
            self._experiments[experiment_id]['status'] = 'stopped'
            self._save()


_ab_manager: Optional[ABTestManager] = None


def get_ab_test_manager() -> ABTestManager:
    global _ab_manager
    if _ab_manager is None:
        _ab_manager = ABTestManager()
    return _ab_manager
