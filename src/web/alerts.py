"""
Alert management system
"""
import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime

class AlertManager:
    """Manage price alerts"""
    
    def __init__(self, alerts_file: Path = None):
        if alerts_file is None:
            alerts_file = Path('data/alerts.json')
        self.alerts_file = alerts_file
        self.alerts_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_alerts()
    
    def _load_alerts(self):
        """Load alerts from file"""
        if self.alerts_file.exists():
            try:
                with open(self.alerts_file, 'r') as f:
                    self.alerts = json.load(f)
            except:
                self.alerts = []
        else:
            self.alerts = []
    
    def _save_alerts(self):
        """Save alerts to file"""
        with open(self.alerts_file, 'w') as f:
            json.dump(self.alerts, f, indent=2)
    
    def get_alerts(self) -> List[Dict]:
        """Get all alerts"""
        return self.alerts
    
    def add_alert(self, ticker: str, condition: str, value: float, alert_type: str = 'price'):
        """Add new alert
        condition: 'above', 'below', 'change_up', 'change_down'
        """
        alert = {
            'id': len(self.alerts) + 1,
            'ticker': ticker,
            'condition': condition,
            'value': value,
            'type': alert_type,
            'active': True,
            'created_at': datetime.now().isoformat(),
            'triggered': False
        }
        self.alerts.append(alert)
        self._save_alerts()
        return alert
    
    def remove_alert(self, alert_id: int):
        """Remove alert"""
        self.alerts = [a for a in self.alerts if a['id'] != alert_id]
        self._save_alerts()
    
    def check_alerts(self, ticker: str, current_price: float, previous_price: float = None):
        """Check if any alerts should trigger"""
        triggered = []
        for alert in self.alerts:
            if not alert['active'] or alert['triggered']:
                continue
            if alert['ticker'] != ticker:
                continue
            
            condition = alert['condition']
            value = alert['value']
            
            if condition == 'above' and current_price >= value:
                alert['triggered'] = True
                alert['triggered_at'] = datetime.now().isoformat()
                triggered.append(alert)
            elif condition == 'below' and current_price <= value:
                alert['triggered'] = True
                alert['triggered_at'] = datetime.now().isoformat()
                triggered.append(alert)
            elif condition == 'change_up' and previous_price:
                change_pct = ((current_price - previous_price) / previous_price) * 100
                if change_pct >= value:
                    alert['triggered'] = True
                    alert['triggered_at'] = datetime.now().isoformat()
                    triggered.append(alert)
            elif condition == 'change_down' and previous_price:
                change_pct = ((current_price - previous_price) / previous_price) * 100
                if change_pct <= -value:
                    alert['triggered'] = True
                    alert['triggered_at'] = datetime.now().isoformat()
                    triggered.append(alert)
        
        if triggered:
            self._save_alerts()
        
        return triggered
