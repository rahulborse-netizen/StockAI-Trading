"""
Backtesting Module for Adaptive Elite Strategy
Tests algorithm accuracy and performance
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import logging

from .adaptive_elite_strategy import AdaptiveEliteStrategy
from .base_strategy import StrategyResult

logger = logging.getLogger(__name__)


class AdaptiveBacktester:
    """
    Backtest the Adaptive Elite Strategy
    
    Calculates:
    - Win rate
    - Sharpe ratio
    - Maximum drawdown
    - Total return
    - Average return per trade
    """
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.strategy = AdaptiveEliteStrategy()
    
    def backtest(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        commission: float = 0.001  # 0.1% commission
    ) -> Dict:
        """
        Backtest strategy on historical data
        
        Args:
            ticker: Stock ticker
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            commission: Commission rate per trade
        
        Returns:
            Dict with performance metrics
        """
        try:
            # Load historical data
            from src.research.data import download_yahoo_ohlcv
            
            ohlcv = download_yahoo_ohlcv(
                ticker=ticker,
                start=start_date,
                end=end_date,
                interval='1d'
            )
            
            if ohlcv is None or len(ohlcv.df) < 50:
                return {'error': 'Insufficient data for backtesting'}
            
            df = ohlcv.df.copy()
            
            # Simulate trading
            equity = self.initial_capital
            cash = self.initial_capital
            position = 0  # Number of shares
            position_entry_price = 0
            
            trades = []
            equity_curve = [equity]
            
            # Process each day
            for i in range(50, len(df)):  # Start after 50 days for indicators
                current_date = df.index[i]
                current_price = df['close'].iloc[i]
                current_row = df.iloc[i]
                
                # Get signal for this day
                # Use data up to this point
                historical_df = df.iloc[:i+1]
                
                try:
                    result = self.strategy.execute({
                        'ticker': ticker,
                        'current_price': current_price,
                        'ohlcv_df': historical_df
                    })
                    
                    signal = result.signal
                    confidence = result.confidence
                    
                    # Execute trades based on signal
                    if signal == 'BUY' and position == 0 and confidence >= 0.70:
                        # Buy signal
                        shares_to_buy = int((cash * 0.95) / current_price)  # Use 95% of cash
                        if shares_to_buy > 0:
                            cost = shares_to_buy * current_price * (1 + commission)
                            if cost <= cash:
                                position = shares_to_buy
                                position_entry_price = current_price
                                cash -= cost
                                
                                trades.append({
                                    'date': current_date,
                                    'action': 'BUY',
                                    'price': current_price,
                                    'shares': shares_to_buy,
                                    'confidence': confidence,
                                    'equity': equity
                                })
                    
                    elif signal == 'SELL' and position > 0 and confidence >= 0.70:
                        # Sell signal
                        proceeds = position * current_price * (1 - commission)
                        cash += proceeds
                        
                        pnl = (current_price - position_entry_price) * position
                        pnl_pct = ((current_price - position_entry_price) / position_entry_price * 100) if position_entry_price > 0 else 0
                        
                        trades.append({
                            'date': current_date,
                            'action': 'SELL',
                            'price': current_price,
                            'shares': position,
                            'pnl': pnl,
                            'pnl_pct': pnl_pct,
                            'confidence': confidence,
                            'equity': equity
                        })
                        
                        position = 0
                        position_entry_price = 0
                    
                    # Update equity (cash + position value)
                    equity = cash + (position * current_price)
                    equity_curve.append(equity)
                    
                except Exception as e:
                    logger.debug(f"Error processing day {current_date}: {e}")
                    equity_curve.append(equity)
                    continue
            
            # Close any open position at end
            if position > 0:
                final_price = df['close'].iloc[-1]
                proceeds = position * final_price * (1 - commission)
                cash += proceeds
                equity = cash
                
                pnl = (final_price - position_entry_price) * position
                pnl_pct = ((final_price - position_entry_price) / position_entry_price * 100) if position_entry_price > 0 else 0
                
                trades.append({
                    'date': df.index[-1],
                    'action': 'SELL',
                    'price': final_price,
                    'shares': position,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'confidence': 0.5,
                    'equity': equity
                })
            
            # Calculate metrics
            metrics = self._calculate_metrics(
                equity_curve,
                trades,
                df,
                start_date,
                end_date
            )
            
            return {
                'status': 'success',
                'ticker': ticker,
                'start_date': start_date,
                'end_date': end_date,
                'initial_capital': self.initial_capital,
                'final_equity': equity,
                'total_return': ((equity / self.initial_capital) - 1) * 100,
                'metrics': metrics,
                'trades': trades[-20:] if len(trades) > 20 else trades,  # Last 20 trades
                'num_trades': len([t for t in trades if t['action'] == 'SELL']),
                'equity_curve': equity_curve[-100:] if len(equity_curve) > 100 else equity_curve  # Last 100 points
            }
            
        except Exception as e:
            logger.error(f"Error in backtest: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {'error': str(e)}
    
    def _calculate_metrics(
        self,
        equity_curve: List[float],
        trades: List[Dict],
        df: pd.DataFrame,
        start_date: str,
        end_date: str
    ) -> Dict:
        """Calculate performance metrics"""
        if len(equity_curve) < 2:
            return {}
        
        equity_series = pd.Series(equity_curve)
        
        # Calculate returns
        returns = equity_series.pct_change().dropna()
        
        # Win rate
        sell_trades = [t for t in trades if t['action'] == 'SELL' and 'pnl' in t]
        if sell_trades:
            winning_trades = [t for t in sell_trades if t['pnl'] > 0]
            win_rate = len(winning_trades) / len(sell_trades) * 100
            avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
            avg_loss = np.mean([t['pnl'] for t in sell_trades if t['pnl'] <= 0]) if len(sell_trades) > len(winning_trades) else 0
        else:
            win_rate = 0
            avg_win = 0
            avg_loss = 0
        
        # Sharpe ratio (annualized)
        if len(returns) > 1 and returns.std() > 0:
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)  # Annualized
        else:
            sharpe_ratio = 0
        
        # Maximum drawdown
        running_max = equity_series.expanding().max()
        drawdown = (equity_series - running_max) / running_max
        max_drawdown = drawdown.min() * 100
        
        # Total return
        total_return = ((equity_curve[-1] / equity_curve[0]) - 1) * 100
        
        # Average return per trade
        if sell_trades:
            avg_return_per_trade = np.mean([t['pnl_pct'] for t in sell_trades])
        else:
            avg_return_per_trade = 0
        
        # Buy and hold return (for comparison)
        buy_hold_return = ((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100
        
        return {
            'win_rate': round(win_rate, 2),
            'sharpe_ratio': round(sharpe_ratio, 3),
            'max_drawdown': round(max_drawdown, 2),
            'total_return': round(total_return, 2),
            'avg_return_per_trade': round(avg_return_per_trade, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'buy_hold_return': round(buy_hold_return, 2),
            'num_trades': len(sell_trades)
        }


def backtest_adaptive_strategy(
    ticker: str,
    start_date: str,
    end_date: str,
    initial_capital: float = 100000.0
) -> Dict:
    """
    Convenience function to backtest adaptive strategy
    
    Example:
        results = backtest_adaptive_strategy(
            'RELIANCE.NS',
            '2023-01-01',
            '2024-01-01'
        )
    """
    backtester = AdaptiveBacktester(initial_capital=initial_capital)
    return backtester.backtest(ticker, start_date, end_date)
