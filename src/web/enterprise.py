"""
Phase 6: Enterprise Features
Multi-user support, RBAC, audit logging, compliance hooks.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class AuditLog:
    """Simple audit log for sensitive actions."""

    def __init__(self, log_path: str = 'data/audit/audit.jsonl'):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        action: str,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict] = None,
        ip: Optional[str] = None,
    ) -> None:
        entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'action': action,
            'user_id': user_id,
            'resource': resource,
            'details': details or {},
            'ip': ip,
        }
        try:
            with open(self.log_path, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            logger.warning(f"Audit log write failed: {e}")

    def query(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Read recent audit entries (simple filter)."""
        if not self.log_path.exists():
            return []
        entries = []
        try:
            with open(self.log_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        e = json.loads(line)
                        if user_id and e.get('user_id') != user_id:
                            continue
                        if action and e.get('action') != action:
                            continue
                        entries.append(e)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.debug(f"Audit log read failed: {e}")
            return []
        return entries[-(limit):]


class RBAC:
    """Role-based access control (in-memory, extend with DB)."""

    ROLES = {'admin', 'trader', 'viewer', 'support'}

    def __init__(self):
        self._role_permissions: Dict[str, set] = {
            'admin': {'*'},
            'trader': {'read', 'write', 'place_order', 'view_holdings', 'view_signals'},
            'viewer': {'read', 'view_holdings', 'view_signals'},
            'support': {'read', 'view_holdings', 'view_signals', 'view_orders'},
        }
        self._user_roles: Dict[str, str] = {}

    def assign_role(self, user_id: str, role: str) -> bool:
        if role not in self.ROLES:
            return False
        self._user_roles[user_id] = role
        return True

    def has_permission(self, user_id: str, permission: str) -> bool:
        role = self._user_roles.get(user_id, 'viewer')
        perms = self._role_permissions.get(role, set())
        return '*' in perms or permission in perms

    def get_role(self, user_id: str) -> str:
        return self._user_roles.get(user_id, 'viewer')


_audit_log: Optional[AuditLog] = None
_rbac: Optional[RBAC] = None


def get_audit_log() -> AuditLog:
    global _audit_log
    if _audit_log is None:
        _audit_log = AuditLog()
    return _audit_log


def get_rbac() -> RBAC:
    global _rbac
    if _rbac is None:
        _rbac = RBAC()
    return _rbac
