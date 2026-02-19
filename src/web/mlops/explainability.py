"""
Phase 2.3: Model explainability - feature importance, SHAP, signal reasoning.
"""
import logging
from typing import Dict, List, Optional, Any
import numpy as np

logger = logging.getLogger(__name__)

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False


class ExplainabilityManager:
    """Feature importance and model interpretation."""

    def get_feature_importance(
        self,
        model,
        X,
        feature_names: Optional[List[str]] = None,
        method: str = 'auto',
    ) -> Dict[str, Any]:
        """
        Get feature importance. Uses SHAP if available, else model-native or permutation.
        """
        if feature_names is None:
            feature_names = [f'feature_{i}' for i in range(X.shape[1])]

        if method == 'auto':
            method = 'shap' if SHAP_AVAILABLE else 'coefficient'

        if method == 'shap' and SHAP_AVAILABLE:
            return self._shap_importance(model, X, feature_names)
        if hasattr(model, 'feature_importances_'):
            return self._tree_importance(model, feature_names)
        if hasattr(model, 'coef_'):
            return self._coefficient_importance(model, feature_names)
        return self._fallback_importance(X, feature_names)

    def _shap_importance(self, model, X, feature_names: List[str]) -> Dict[str, Any]:
        try:
            if hasattr(model, 'predict_proba'):
                explainer = shap.TreeExplainer(model, X) if hasattr(model, 'feature_importances_') else shap.KernelExplainer(model.predict_proba, shap.sample(X, min(50, len(X))))
            else:
                explainer = shap.KernelExplainer(model.predict, shap.sample(X, min(50, len(X))))
            shap_values = explainer.shap_values(X)
            if isinstance(shap_values, list):
                shap_values = shap_values[1]  # positive class
            importance = np.abs(shap_values).mean(axis=0)
        except Exception as e:
            logger.debug(f"SHAP failed: {e}")
            return self._fallback_importance(X, feature_names)
        return self._format_importance(dict(zip(feature_names, importance.tolist())))

    def _tree_importance(self, model, feature_names: List[str]) -> Dict[str, Any]:
        imp = model.feature_importances_
        return self._format_importance(dict(zip(feature_names, imp.tolist())))

    def _coefficient_importance(self, model, feature_names: List[str]) -> Dict[str, Any]:
        coef = np.abs(np.ravel(model.coef_))
        if len(coef) != len(feature_names):
            coef = np.abs(model.coef_[0]) if model.coef_.ndim > 1 else coef
        return self._format_importance(dict(zip(feature_names, coef.tolist())))

    def _fallback_importance(self, X, feature_names: List[str]) -> Dict[str, Any]:
        # Variance as proxy for importance when no model attributes
        var = np.var(X, axis=0)
        total = var.sum() or 1
        return self._format_importance(dict(zip(feature_names, (var / total).tolist())))

    def _format_importance(self, raw: Dict[str, float]) -> Dict[str, Any]:
        total = sum(raw.values()) or 1
        return {
            'feature_importance': {k: round(v / total, 4) for k, v in raw.items()},
            'shap_available': SHAP_AVAILABLE,
        }

    def get_signal_reasoning(
        self,
        ticker: str,
        signal: str,
        feature_contributions: Optional[Dict[str, float]] = None,
        top_n: int = 5,
    ) -> Dict[str, Any]:
        """Produce human-readable signal reasoning from feature contributions."""
        reasons = []
        if feature_contributions:
            sorted_ = sorted(
                feature_contributions.items(),
                key=lambda x: abs(x[1]),
                reverse=True,
            )[:top_n]
            for name, contrib in sorted_:
                direction = 'supporting' if contrib > 0 else 'against'
                reasons.append(f"{name}: {direction} (weight {contrib:.3f})")
        return {
            'ticker': ticker,
            'signal': signal,
            'reasoning': reasons,
            'top_features': feature_contributions or {},
        }


_explain_manager: Optional[ExplainabilityManager] = None


def get_explainability_manager() -> ExplainabilityManager:
    global _explain_manager
    if _explain_manager is None:
        _explain_manager = ExplainabilityManager()
    return _explain_manager
