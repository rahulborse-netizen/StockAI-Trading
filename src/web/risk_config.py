"""
Risk Management Configuration
Manages risk parameters and limits
"""
import logging
from pathlib import Path
from typing import Dict, Optional

try:
    import yaml
except ImportError:
    # Fallback: use simple YAML-like parsing or JSON
    yaml = None

logger = logging.getLogger(__name__)

# Default risk configuration
DEFAULT_RISK_CONFIG = {
    'max_risk_per_trade': 0.02,  # 2% of capital per trade
    'max_position_size': 0.20,  # 20% of capital per position
    'max_daily_risk': 0.05,  # 5% of capital per day
    'max_portfolio_risk': 0.30,  # 30% of capital total portfolio risk
    'min_lot_size': 1,  # Minimum lot size (can be instrument-specific)
    'min_risk_reward_ratio': 1.5,  # Minimum risk-reward ratio
    'max_open_positions': 10,  # Maximum number of open positions
}

_risk_config = None


def load_risk_config(config_path: Optional[Path] = None) -> Dict:
    """
    Load risk configuration from YAML file or use defaults
    
    Args:
        config_path: Path to config file (default: configs/trading_config.yaml)
    
    Returns:
        Risk configuration dictionary
    """
    if config_path is None:
        config_path = Path('configs/trading_config.yaml')
    
    config = DEFAULT_RISK_CONFIG.copy()
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                if yaml:
                    file_config = yaml.safe_load(f)
                else:
                    # Fallback: try JSON
                    import json
                    file_config = json.load(f)
                if file_config and 'risk_management' in file_config:
                    config.update(file_config['risk_management'])
                    logger.info(f"Loaded risk config from {config_path}")
        except Exception as e:
            logger.warning(f"Error loading risk config from {config_path}: {e}. Using defaults.")
    else:
        logger.info(f"Risk config file not found at {config_path}. Using defaults.")
    
    return config


def get_risk_config() -> Dict:
    """Get current risk configuration (cached)"""
    global _risk_config
    if _risk_config is None:
        _risk_config = load_risk_config()
    return _risk_config.copy()


def update_risk_config(updates: Dict, config_path: Optional[Path] = None):
    """
    Update risk configuration and save to file
    
    Args:
        updates: Dictionary of config updates
        config_path: Path to config file
    """
    global _risk_config
    
    if config_path is None:
        config_path = Path('configs/trading_config.yaml')
    
    # Load current config
    config = get_risk_config()
    config.update(updates)
    
    # Save to file
    config_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if yaml:
            yaml_data = {'risk_management': config}
            with open(config_path, 'w') as f:
                yaml.dump(yaml_data, f, default_flow_style=False)
        else:
            # Fallback: use JSON
            import json
            json_data = {'risk_management': config}
            with open(config_path, 'w') as f:
                json.dump(json_data, f, indent=2)
        logger.info(f"Updated risk config saved to {config_path}")
        
        # Update cached config
        _risk_config = config
    except Exception as e:
        logger.error(f"Error saving risk config to {config_path}: {e}")


def reset_risk_config():
    """Reset risk configuration to defaults"""
    global _risk_config
    _risk_config = DEFAULT_RISK_CONFIG.copy()
    logger.info("Risk config reset to defaults")
