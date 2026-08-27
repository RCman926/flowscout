"""
Backtesting Engine
Validates strategy on historical data
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
import json
import yfinance as yf

logger = logging.getLogger(__name__)


class BacktestingEngine:
    """
    Backtesting engine for validating trading strategy
    """
    
    def __init__(self):
        self.results_cache = {}
    
    def backtest_strategy(self, 
                         symbol: str = "SPY",
                         start_date: str = None,
                         end_date: str = None,
                         initial_capital: float = 10000) -> Dict:
        """
        Backtest strategy on historical data
        
        Args:
            symbol: Symbol to backtest
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            initial_capital: Starting capital
        
        Returns:
            Dict with backtest results
        """
        try:
            # Default to last 30 days
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            # Get historical data
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date, interval="1d")
            
            if hist.empty:
                return {'error': 'No historical data available'}
            
            # Simulate trades
            trades = []
            capital = initial_capital
            positions = []
            
            for i in range(len(hist)):
                date = hist.index[i]
                price = float(hist['Close'].iloc[i])
                
                # Use REAL signal logic based on actual price data
                # This uses real historical price movements (not simulated)
                signal = self._get_real_signal_from_price_data(price, hist.iloc[:i+1])
                
                # Execute trades based on signal
                if signal['action'] != 'NO_TRADE' and signal['confidence'] >= 70:
                    # Open position
                    position_size = capital * 0.1  # 10% per trade
                    position = {
                        'entry_date': date,
                        'entry_price': price,
                        'action': signal['action'],
                        'size': position_size,
                        'confidence': signal['confidence']
                    }
                    positions.append(position)
                
                # Check for exits (simplified - would use actual exit logic)
                for pos in positions[:]:
                    if self._should_exit(pos, price, date):
                        # Close position
                        pnl = self._calculate_pnl(pos, price)
                        capital += pnl
                        
                        trades.append({
                            'entry_date': pos['entry_date'],
                            'exit_date': date,
                            'entry_price': pos['entry_price'],
                            'exit_price': price,
                            'action': pos['action'],
                            'pnl': pnl,
                            'pnl_pct': (pnl / pos['size']) * 100
                        })
                        positions.remove(pos)
            
            # Close remaining positions
            final_price = float(hist['Close'].iloc[-1])
            for pos in positions:
                pnl = self._calculate_pnl(pos, final_price)
                capital += pnl
                trades.append({
                    'entry_date': pos['entry_date'],
                    'exit_date': hist.index[-1],
                    'entry_price': pos['entry_price'],
                    'exit_price': final_price,
                    'action': pos['action'],
                    'pnl': pnl,
                    'pnl_pct': (pnl / pos['size']) * 100
                })
            
            # Calculate performance metrics
            metrics = self._calculate_metrics(trades, initial_capital, capital)
            
            return {
                'symbol': symbol,
                'start_date': start_date,
                'end_date': end_date,
                'initial_capital': initial_capital,
                'final_capital': round(capital, 2),
                'total_return': round((capital - initial_capital) / initial_capital * 100, 2),
                'total_trades': len(trades),
                'metrics': metrics,
                'trades': trades[-20:] if len(trades) > 20 else trades  # Last 20 trades
            }
            
        except Exception as e:
            logger.error(f"Backtest error: {e}", exc_info=True)
            return {'error': str(e)}
    
    def _get_real_signal_from_price_data(self, price: float, hist: pd.DataFrame) -> Dict:
        """
        Generate signal from REAL historical price data (not simulated)
        Uses actual price movements and momentum from real market data
        """
        if len(hist) < 5:
            return {'action': 'NO_TRADE', 'confidence': 50}
        
        # Calculate real momentum from actual price data
        recent_prices = hist['Close'].tail(5).values
        momentum = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
        
        # Use real volatility from actual price movements
        volatility = hist['Close'].tail(5).std() / hist['Close'].tail(5).mean()
        
        # Real signal based on actual price momentum and volatility
        if momentum > 0.01 and volatility < 0.02:  # Strong upward momentum, low volatility
            return {'action': 'BUY_CALLS', 'confidence': 75}
        elif momentum < -0.01 and volatility < 0.02:  # Strong downward momentum, low volatility
            return {'action': 'BUY_PUTS', 'confidence': 75}
        elif momentum > 0.005:  # Moderate upward
            return {'action': 'BUY_CALLS', 'confidence': 65}
        elif momentum < -0.005:  # Moderate downward
            return {'action': 'BUY_PUTS', 'confidence': 65}
        else:
            return {'action': 'NO_TRADE', 'confidence': 50}
    
    def _simulate_signal(self, price: float, hist: pd.DataFrame) -> Dict:
        """DEPRECATED: Use _get_real_signal_from_price_data instead"""
        return self._get_real_signal_from_price_data(price, hist)
    
    def _should_exit(self, position: Dict, current_price: float, current_date: datetime) -> bool:
        """Determine if position should be closed"""
        entry_price = position['entry_price']
        entry_date = position['entry_date']
        
        # Simple exit logic: 5% profit or 2% loss
        if position['action'] == 'BUY_CALLS':
            profit_pct = (current_price - entry_price) / entry_price
            return profit_pct >= 0.05 or profit_pct <= -0.02
        else:  # BUY_PUTS
            profit_pct = (entry_price - current_price) / entry_price
            return profit_pct >= 0.05 or profit_pct <= -0.02
    
    def _calculate_pnl(self, position: Dict, exit_price: float) -> float:
        """Calculate profit/loss for position"""
        entry_price = position['entry_price']
        size = position['size']
        
        if position['action'] == 'BUY_CALLS':
            return (exit_price - entry_price) / entry_price * size
        else:  # BUY_PUTS
            return (entry_price - exit_price) / entry_price * size
    
    def _calculate_metrics(self, trades: List[Dict], initial_capital: float, 
                          final_capital: float) -> Dict:
        """Calculate performance metrics"""
        if not trades:
            return {
                'win_rate': 0,
                'total_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0
            }
        
        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] < 0]
        
        win_rate = len(wins) / len(trades) if trades else 0
        avg_win = np.mean([t['pnl'] for t in wins]) if wins else 0
        avg_loss = np.mean([t['pnl'] for t in losses]) if losses else 0
        
        # Sharpe ratio (simplified)
        returns = [t['pnl_pct'] for t in trades]
        sharpe = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        
        # Max drawdown (simplified)
        cumulative = np.cumsum([t['pnl'] for t in trades])
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / initial_capital
        max_drawdown = abs(np.min(drawdown)) if len(drawdown) > 0 else 0
        
        return {
            'win_rate': round(win_rate * 100, 2),
            'total_trades': len(trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 0,
            'sharpe_ratio': round(sharpe, 2),
            'max_drawdown_pct': round(max_drawdown * 100, 2),
            'total_return_pct': round((final_capital - initial_capital) / initial_capital * 100, 2)
        }


# Global instance
backtesting_engine = BacktestingEngine()

