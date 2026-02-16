"""
Subscription Tiers and Feature Gating
Free: 5 signals/day | Pro: unlimited signals | Premium: auto-trade + unlimited
Stripe/Razorpay integration can be added to upgrade users.
"""
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, date

logger = logging.getLogger(__name__)

# Tier limits
TIER_LIMITS = {
    'free': {
        'signals_per_day': 5,
        'auto_trade': False,
        'accuracy_dashboard': True,
        'export_csv': False,
    },
    'pro': {
        'signals_per_day': None,  # unlimited
        'auto_trade': False,
        'accuracy_dashboard': True,
        'export_csv': True,
    },
    'premium': {
        'signals_per_day': None,
        'auto_trade': True,
        'accuracy_dashboard': True,
        'export_csv': True,
    },
}

# In-memory daily signal count per "user" (keyed by session or IP for now)
_daily_signal_count: Dict[str, Dict[str, int]] = {}


def get_user_tier(user_id: Optional[str] = None) -> str:
    """
    Return current user's subscription tier.
    When auth/payment is integrated, resolve from database or session.
    """
    if user_id and user_id != 'anonymous':
        # TODO: resolve from session/db when Stripe/Razorpay is integrated
        pass
    return 'free'


def can_use_feature(tier: str, feature: str) -> bool:
    """Check if tier allows the feature."""
    limits = TIER_LIMITS.get(tier, TIER_LIMITS['free'])
    return limits.get(feature, False) if isinstance(limits.get(feature), bool) else True


def get_signals_per_day_limit(tier: str) -> Optional[int]:
    """None means unlimited."""
    return TIER_LIMITS.get(tier, TIER_LIMITS['free']).get('signals_per_day')


def record_signal_usage(user_key: str) -> None:
    """Increment daily signal count for user_key (e.g. IP or session id)."""
    today = date.today().isoformat()
    if user_key not in _daily_signal_count:
        _daily_signal_count[user_key] = {}
    _daily_signal_count[user_key][today] = _daily_signal_count[user_key].get(today, 0) + 1


def get_daily_signal_count(user_key: str) -> int:
    """Return number of signals used today by user_key."""
    today = date.today().isoformat()
    return _daily_signal_count.get(user_key, {}).get(today, 0)


def can_request_signal(user_key: str, tier: Optional[str] = None) -> Tuple[bool, str]:
    """
    Returns (allowed: bool, message: str).
    For free tier, enforces signals_per_day limit.
    """
    tier = tier or get_user_tier()
    limit = get_signals_per_day_limit(tier)
    if limit is None:
        return True, ''
    count = get_daily_signal_count(user_key)
    if count >= limit:
        return False, f'Daily signal limit ({limit}) reached. Upgrade to Pro for unlimited signals.'
    return True, ''
