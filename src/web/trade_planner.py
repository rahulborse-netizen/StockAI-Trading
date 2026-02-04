"""
Trade Planning Engine
Generates comprehensive trade plans from ML signals with risk-based position sizing
"""
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional, Dict, List
from datetime import datetime
import json
import logging
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)


class TradePlanStatus(Enum):
    """Trade plan status"""
    DRAFT = "draft"
    APPROVED = "approved"
    EXECUTED = "executed"
    CANCELLED = "cancelled"


class TradingType(Enum):
    """Trading type"""
    INTRADAY = "intraday"
    SWING = "swing"
    POSITION = "position"


@dataclass
class TradePlan:
    """Complete trade plan data structure"""
    # Trade metadata
    plan_id: str
    symbol: str
    ticker: str
    signal: str  # BUY, SELL, HOLD
    confidence: float  # 0-1 probability
    trading_type: str  # intraday, swing, position
    timestamp: str
    
    # Entry/Exit levels
    entry_price: float
    stop_loss: float
    target_1: float
    target_2: float
    current_price: float
    
    # Position sizing
    quantity: int
    capital_required: float
    risk_amount: float
    
    # Risk metrics
    risk_per_trade_pct: float  # Risk as % of capital
    risk_reward_ratio: float
    max_loss: float
    
    # Order details
    order_type: str  # MARKET, LIMIT, SL, SL-M
    product: str  # 'I' for Intraday, 'D' for Delivery
    validity: str  # 'DAY', 'IOC'
    
    # Status
    status: str = TradePlanStatus.DRAFT.value
    
    # Additional data
    recent_high: Optional[float] = None
    recent_low: Optional[float] = None
    volatility: Optional[float] = None
    order_id: Optional[str] = None  # Set when executed
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TradePlan':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class ValidationResult:
    """Trade plan validation result"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    
    def to_dict(self) -> Dict:
        return {
            'is_valid': self.is_valid,
            'errors': self.errors,
            'warnings': self.warnings
        }


class TradePlanManager:
    """Manages trade plan storage and retrieval"""
    
    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path('data/trade_plans.json')
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.plans: Dict[str, TradePlan] = {}
        self.load_plans()
    
    def load_plans(self):
        """Load trade plans from storage"""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    self.plans = {
                        plan_id: TradePlan.from_dict(plan_data)
                        for plan_id, plan_data in data.items()
                    }
                logger.info(f"Loaded {len(self.plans)} trade plans from storage")
        except Exception as e:
            logger.error(f"Error loading trade plans: {e}")
            self.plans = {}
    
    def save_plans(self):
        """Save trade plans to storage"""
        try:
            data = {
                plan_id: plan.to_dict()
                for plan_id, plan in self.plans.items()
            }
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.plans)} trade plans to storage")
        except Exception as e:
            logger.error(f"Error saving trade plans: {e}")
    
    def add_plan(self, plan: TradePlan):
        """Add or update a trade plan"""
        self.plans[plan.plan_id] = plan
        self.save_plans()
    
    def get_plan(self, plan_id: str) -> Optional[TradePlan]:
        """Get a trade plan by ID"""
        return self.plans.get(plan_id)
    
    def get_all_plans(self, status: Optional[str] = None, 
                      trading_type: Optional[str] = None,
                      symbol: Optional[str] = None) -> List[TradePlan]:
        """Get all trade plans with optional filters"""
        plans = list(self.plans.values())
        
        if status:
            plans = [p for p in plans if p.status == status]
        if trading_type:
            plans = [p for p in plans if p.trading_type == trading_type]
        if symbol:
            plans = [p for p in plans if p.symbol == symbol]
        
        # Sort by timestamp (newest first)
        plans.sort(key=lambda p: p.timestamp, reverse=True)
        return plans
    
    def update_plan_status(self, plan_id: str, status: str):
        """Update trade plan status"""
        plan = self.plans.get(plan_id)
        if plan:
            plan.status = status
            self.save_plans()
    
    def delete_plan(self, plan_id: str):
        """Delete a trade plan"""
        if plan_id in self.plans:
            del self.plans[plan_id]
            self.save_plans()


class TradePlanner:
    """Core trade planning engine"""
    
    def __init__(self, plan_manager: TradePlanManager):
        self.plan_manager = plan_manager
    
    def generate_trade_plan(
        self,
        signal_data: Dict,
        market_data: Optional[Dict] = None,
        risk_params: Optional[Dict] = None,
        trading_type: str = TradingType.SWING.value,
        account_balance: float = 100000.0
    ) -> TradePlan:
        """
        Generate a complete trade plan from signal data
        
        Args:
            signal_data: ML signal output (from /api/signals endpoint)
            market_data: Current market data (optional, will fetch if not provided)
            risk_params: Risk management parameters
            trading_type: Trading type (intraday/swing/position)
            account_balance: Account balance for position sizing
        
        Returns:
            Complete TradePlan object
        """
        from src.web.position_sizing import calculate_risk_based_size
        from src.web.risk_config import get_risk_config
        
        # Get risk configuration
        risk_config = get_risk_config()
        if risk_params:
            risk_config.update(risk_params)
        
        # Extract signal data
        ticker = signal_data.get('ticker')
        # Extract symbol from ticker (remove exchange suffixes)
        symbol = str(ticker).replace('.NS', '').replace('.BO', '').replace('^', '').strip()
        if not symbol:
            symbol = ticker  # Fallback to ticker if symbol extraction fails
        signal = signal_data.get('signal', 'HOLD')
        confidence = signal_data.get('probability', 0.5)
        current_price = signal_data.get('current_price', 0)
        entry_level = signal_data.get('entry_level', current_price)
        stop_loss = signal_data.get('stop_loss', current_price * 0.97)
        target_1 = signal_data.get('target_1', current_price * 1.03)
        target_2 = signal_data.get('target_2', current_price * 1.05)
        
        # Adjust levels based on trading type
        entry_level, stop_loss, target_1, target_2 = self._adjust_levels_for_trading_type(
            current_price, entry_level, stop_loss, target_1, target_2, trading_type
        )
        
        # Calculate risk amount
        risk_per_trade_pct = risk_config.get('max_risk_per_trade', 0.02)  # 2% default
        risk_amount = account_balance * risk_per_trade_pct
        
        # Calculate position size
        quantity = calculate_risk_based_size(
            entry=entry_level,
            stop_loss=stop_loss,
            risk_amount=risk_amount,
            lot_size=1  # Default lot size, can be enhanced
        )
        
        # Calculate capital required
        capital_required = quantity * entry_level
        
        # Calculate risk metrics
        price_risk = abs(entry_level - stop_loss)
        price_reward = abs(target_1 - entry_level)
        risk_reward_ratio = price_reward / price_risk if price_risk > 0 else 0
        max_loss = quantity * price_risk
        
        # Determine order type and product
        order_type, product, validity = self._get_order_details(trading_type, signal)
        
        # Generate plan ID (sanitize symbol for filename)
        safe_symbol = symbol.replace(' ', '_').replace('/', '_').replace(':', '_').replace('|', '_')
        plan_id = f"{safe_symbol}_{trading_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create trade plan
        plan = TradePlan(
            plan_id=plan_id,
            symbol=symbol,
            ticker=ticker,
            signal=signal,
            confidence=confidence,
            trading_type=trading_type,
            timestamp=datetime.now().isoformat(),
            entry_price=entry_level,
            stop_loss=stop_loss,
            target_1=target_1,
            target_2=target_2,
            current_price=current_price,
            quantity=quantity,
            capital_required=capital_required,
            risk_amount=risk_amount,
            risk_per_trade_pct=risk_per_trade_pct * 100,
            risk_reward_ratio=risk_reward_ratio,
            max_loss=max_loss,
            order_type=order_type,
            product=product,
            validity=validity,
            recent_high=signal_data.get('recent_high'),
            recent_low=signal_data.get('recent_low'),
            volatility=signal_data.get('volatility')
        )
        
        # Save plan
        self.plan_manager.add_plan(plan)
        
        return plan
    
    def _adjust_levels_for_trading_type(
        self,
        current_price: float,
        entry: float,
        stop_loss: float,
        target_1: float,
        target_2: float,
        trading_type: str
    ) -> tuple:
        """Adjust entry/exit levels based on trading type"""
        if trading_type == TradingType.INTRADAY.value:
            # Tighter stops and targets for intraday
            stop_loss = current_price * 0.98  # 2% stop
            target_1 = current_price * 1.01  # 1% target
            target_2 = current_price * 1.015  # 1.5% target
        elif trading_type == TradingType.POSITION.value:
            # Wider stops and targets for position trading
            stop_loss = current_price * 0.95  # 5% stop
            target_1 = current_price * 1.05  # 5% target
            target_2 = current_price * 1.10  # 10% target
        # Swing trading uses original levels (2-3% stops, 2-5% targets)
        
        return entry, stop_loss, target_1, target_2
    
    def _get_order_details(self, trading_type: str, signal: str) -> tuple:
        """Get order type, product, and validity based on trading type"""
        if trading_type == TradingType.INTRADAY.value:
            return 'MARKET', 'I', 'DAY'
        else:
            return 'LIMIT', 'D', 'DAY'
    
    def backtest_trade_plan(
        self,
        plan: TradePlan,
        historical_data: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        Backtest a trade plan against historical data
        
        Args:
            plan: TradePlan to backtest
            historical_data: Historical OHLCV data (optional, will fetch if not provided)
        
        Returns:
            Dictionary with backtest results
        """
        try:
            from src.research.data import download_yahoo_ohlcv
            from datetime import timedelta
            
            # Get historical data if not provided
            if historical_data is None:
                today = datetime.now()
                start_date = (today - timedelta(days=365)).strftime('%Y-%m-%d')
                end_date = today.strftime('%Y-%m-%d')
                
                cache_path = Path('cache') / f"{plan.ticker.replace('^', '').replace(':', '_').replace('/', '_')}.csv"
                ohlcv = download_yahoo_ohlcv(
                    ticker=plan.ticker,
                    start=start_date,
                    end=end_date,
                    interval='1d',
                    cache_path=cache_path,
                    refresh=False
                )
                
                if ohlcv is None or len(ohlcv.df) == 0:
                    return {'error': 'No historical data available'}
                
                historical_data = ohlcv.df
            
            # Simulate trade
            entry_price = plan.entry_price
            stop_loss = plan.stop_loss
            target_1 = plan.target_1
            target_2 = plan.target_2
            quantity = plan.quantity
            
            # Find entry point in historical data
            # Use closest price to entry
            historical_data = historical_data.copy()
            historical_data['distance_to_entry'] = abs(historical_data['close'] - entry_price)
            entry_idx = historical_data['distance_to_entry'].idxmin()
            
            if entry_idx is None:
                return {'error': 'Could not find entry point in historical data'}
            
            # Simulate forward from entry
            entry_data = historical_data.loc[entry_idx:]
            
            # Check if stop loss or targets are hit
            hit_stop = False
            hit_target_1 = False
            hit_target_2 = False
            exit_price = None
            exit_idx = None
            
            for idx, row in entry_data.iterrows():
                high = row.get('high', row.get('close', entry_price))
                low = row.get('low', row.get('close', entry_price))
                close = row.get('close', entry_price)
                
                if plan.signal == 'BUY':
                    # Check for stop loss (price goes below stop)
                    if low <= stop_loss:
                        hit_stop = True
                        exit_price = stop_loss
                        exit_idx = idx
                        break
                    # Check for targets (price goes above target)
                    if high >= target_2:
                        hit_target_2 = True
                        exit_price = target_2
                        exit_idx = idx
                        break
                    elif high >= target_1 and not hit_target_1:
                        hit_target_1 = True
                        # Continue to check for target 2
                else:  # SELL
                    # Check for stop loss (price goes above stop)
                    if high >= stop_loss:
                        hit_stop = True
                        exit_price = stop_loss
                        exit_idx = idx
                        break
                    # Check for targets (price goes below target)
                    if low <= target_2:
                        hit_target_2 = True
                        exit_price = target_2
                        exit_idx = idx
                        break
                    elif low <= target_1 and not hit_target_1:
                        hit_target_1 = True
                        # Continue to check for target 2
            
            # Calculate P&L
            if exit_price:
                if plan.signal == 'BUY':
                    pnl = (exit_price - entry_price) * quantity
                else:  # SELL
                    pnl = (entry_price - exit_price) * quantity
                pnl_pct = (pnl / (entry_price * quantity)) * 100
            else:
                # No exit found, use last close
                last_close = entry_data.iloc[-1]['close']
                if plan.signal == 'BUY':
                    pnl = (last_close - entry_price) * quantity
                else:
                    pnl = (entry_price - last_close) * quantity
                pnl_pct = (pnl / (entry_price * quantity)) * 100
                exit_price = last_close
            
            # Calculate win rate estimate (simplified)
            # Count how many times similar setups would have worked
            win_count = 0
            total_count = 0
            
            # Simple heuristic: if target 1 or 2 was hit, it's a win
            if hit_target_1 or hit_target_2:
                win_count = 1
            elif hit_stop:
                win_count = 0
            total_count = 1
            
            return {
                'entry_price': entry_price,
                'exit_price': exit_price,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'hit_stop_loss': hit_stop,
                'hit_target_1': hit_target_1,
                'hit_target_2': hit_target_2,
                'win_estimate': win_count / total_count if total_count > 0 else 0.0,
                'days_held': (exit_idx - entry_idx) if exit_idx and entry_idx else None
            }
            
        except Exception as e:
            logger.error(f"Error backtesting trade plan: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {'error': str(e)}
    
    def validate_trade_plan(
        self,
        plan: TradePlan,
        portfolio_state: Optional[Dict] = None
    ) -> ValidationResult:
        """
        Validate a trade plan against risk limits
        
        Args:
            plan: TradePlan to validate
            portfolio_state: Current portfolio state (optional)
        
        Returns:
            ValidationResult with validation status
        """
        from src.web.risk_config import get_risk_config
        
        errors = []
        warnings = []
        risk_config = get_risk_config()
        
        # Check position size
        max_position_size = risk_config.get('max_position_size', 0.20)  # 20% default
        if plan.capital_required > (plan.capital_required / max_position_size * 100):
            # This check needs account balance, simplified for now
            pass
        
        # Check risk per trade
        max_risk_pct = risk_config.get('max_risk_per_trade', 0.02)
        if plan.risk_per_trade_pct / 100 > max_risk_pct:
            errors.append(f"Risk per trade ({plan.risk_per_trade_pct:.2f}%) exceeds maximum ({max_risk_pct*100:.2f}%)")
        
        # Check stop loss is reasonable
        stop_loss_pct = abs(plan.entry_price - plan.stop_loss) / plan.entry_price
        if stop_loss_pct > 0.10:  # More than 10% stop loss
            warnings.append(f"Stop loss is very wide ({stop_loss_pct*100:.2f}%)")
        elif stop_loss_pct < 0.01:  # Less than 1% stop loss
            warnings.append(f"Stop loss is very tight ({stop_loss_pct*100:.2f}%)")
        
        # Check risk-reward ratio
        if plan.risk_reward_ratio < 1.0:
            warnings.append(f"Risk-reward ratio is less than 1:1 ({plan.risk_reward_ratio:.2f})")
        
        # Check quantity
        if plan.quantity <= 0:
            errors.append("Position size is zero or negative")
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings
        )


# Global instance
_plan_manager = None
_trade_planner = None


def get_plan_manager() -> TradePlanManager:
    """Get global trade plan manager instance"""
    global _plan_manager
    if _plan_manager is None:
        _plan_manager = TradePlanManager()
    return _plan_manager


def get_trade_planner() -> TradePlanner:
    """Get global trade planner instance"""
    global _trade_planner
    if _trade_planner is None:
        _trade_planner = TradePlanner(get_plan_manager())
    return _trade_planner
