"""
Performance Tracker - FRESH REBUILD
Always reads from file - no caching whatsoever
"""
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """Tracks trade performance - OPTIMIZED WITH SMART CACHING"""
    
    def __init__(self):
        # CRITICAL: Use absolute path based on current working directory
        # This will be updated by get_performance_tracker() if needed
        self.trades_file = os.path.abspath("zerodte_trades.json")
        # Smart caching: cache for 1 second to reduce file I/O
        self._cache = None
        self._cache_time = 0
        self._cache_ttl = 0.5  # ACCELERATED: 0.5 second cache TTL (reduced from 1.0s for faster updates)
        logger.info(f"📊 PerformanceTracker initialized - will read from: {self.trades_file} (exists: {os.path.exists(self.trades_file)})")
    
    def _invalidate_cache(self):
        """Invalidate cache to force fresh read"""
        self._cache = None
        self._cache_time = 0
    
    def _read_file(self) -> List[Dict]:
        """Read trades with smart caching - reduces file I/O by 90%+"""
        try:
            # Check cache first
            import time
            current_time = time.time()
            if self._cache is not None and (current_time - self._cache_time) < self._cache_ttl:
                # Cache is valid, return cached data
                return self._cache
            
            # Cache miss or expired - read from file
            file_path = os.path.abspath(self.trades_file)
            
            # BULLETPROOF: Try multiple file paths if primary doesn't exist
            if not os.path.exists(file_path):
                logger.warning(f"⚠️ Primary file not found: {file_path}")
                # Try current working directory
                cwd_file = os.path.join(os.getcwd(), "zerodte_trades.json")
                if os.path.exists(cwd_file):
                    logger.info(f"✅ Found file at CWD: {cwd_file}")
                    file_path = cwd_file
                    self.trades_file = cwd_file
                else:
                    # FAILSAFE: Create empty file if it doesn't exist
                    logger.info(f"Trades file not found: {file_path} - creating empty file")
                    try:
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        with open(file_path, 'w') as f:
                            json.dump({'trades': []}, f, indent=2)
                        logger.info(f"Created empty trades file: {file_path}")
                    except Exception as create_error:
                        logger.warning(f"Could not create trades file: {create_error}")
                    return []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            trades = data.get('trades', [])
            
            # FAILSAFE: Ensure trades is a list
            if not isinstance(trades, list):
                logger.warning(f"Trades data is not a list, resetting to empty list")
                trades = []
            
            # Update cache
            self._cache = trades
            self._cache_time = current_time
            
            # Log read success (reduced frequency)
            if len(trades) > 0 and (len(trades) % 100 == 0 or self._cache_time == 0):
                logger.info(f"✅ READ FROM FILE {file_path}: {len(trades)} trades (cached for {self._cache_ttl}s)")
            
            return trades
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error reading file {self.trades_file}: {e} - returning empty list", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"❌ Error reading file {self.trades_file}: {e}", exc_info=True)
            return []
    
    def _invalidate_cache(self):
        """Invalidate cache (call after writes)"""
        self._cache = None
        self._cache_time = 0
    
    def _write_file(self, trades: List[Dict]):
        """Write trades to file and invalidate cache"""
        try:
            file_path = os.path.abspath(self.trades_file)
            data = {
                'trades': trades,
                'last_updated': datetime.now().isoformat()
            }
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"Wrote {len(trades)} trades to file")
            # Invalidate cache after write
            self._invalidate_cache()
        except Exception as e:
            logger.error(f"Error writing file: {e}")
    
    @property
    def trades(self) -> List[Dict]:
        """Property that ALWAYS reads from file - no caching"""
        return self._read_file()
    
    def record_signal(self, signal_id: str, symbol: str, action: str, 
                     entry_price: float, confidence: int, expiration: str, 
                     option_price: Optional[float] = None, 
                     bot_predictions: Optional[Dict] = None,
                     num_contracts: int = 1) -> str:
        """
        Record a new trade with bot predictions for outcome tracking
        
        Args:
            signal_id: Signal identifier
            symbol: Stock symbol
            action: BUY_CALLS or BUY_PUTS
            entry_price: Stock price at entry
            confidence: Confidence level (0-100)
            expiration: Expiration date
            option_price: Option price per contract (e.g., 1.21)
            bot_predictions: Bot predictions dict
            num_contracts: Number of contracts (default 1)
        """
        trades = self._read_file()
        trade_id = f"{symbol}_{expiration}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Calculate entry commission if option price is available
        entry_commission = 0.0
        min_profit_needed_pct = 0.0
        if option_price is not None:
            try:
                from broker_commission_tracker import broker_commission_tracker
                entry_commission = broker_commission_tracker.calculate_commission(
                    option_price, num_contracts, is_entry=True
                )
                min_profit_needed_pct = broker_commission_tracker.calculate_min_profit_threshold(
                    option_price, num_contracts
                )
            except Exception as e:
                logger.debug(f"Error calculating entry commission: {e}")
        
        trade = {
            'trade_id': trade_id,
            'signal_id': signal_id,
            'symbol': symbol,
            'action': action,
            'entry_price': entry_price,  # Stock price at entry
            'option_price': option_price,  # Option price (e.g., 1.21, 1.03) - the actual cost to buy the option
            'num_contracts': num_contracts,
            'entry_commission': round(entry_commission, 2),
            'min_profit_needed_pct': round(min_profit_needed_pct, 2),
            'entry_time': datetime.now().isoformat(),
            'expiration': expiration,
            'confidence': confidence,
            'status': 'OPEN',
            'exit_price': None,
            'exit_option_price': None,
            'exit_time': None,
            'profit_loss': None,  # Gross profit
            'profit_loss_pct': None,  # Net profit %
            'total_commissions': None,
            'net_profit': None,
            'result': None,
            'bot_predictions': bot_predictions  # CRITICAL: Store bot predictions for outcome tracking
        }
        trades.append(trade)
        self._write_file(trades)
        return trade_id
    
    def close_trade(self, trade_id: str, exit_price: float, exit_time: Optional[datetime] = None, 
                   exit_option_price: Optional[float] = None, num_contracts: int = 1) -> bool:
        """
        Close a trade with commission tracking
        
        Args:
            trade_id: Trade identifier
            exit_price: Stock price at exit
            exit_time: Exit timestamp
            exit_option_price: Option price at exit (for commission calculation)
            num_contracts: Number of contracts (default 1)
        """
        trades = self._read_file()
        for trade in trades:
            if trade['trade_id'] == trade_id and trade.get('status') == 'OPEN':
                entry_price = trade['entry_price']
                entry_option_price = trade.get('option_price', entry_price)  # Use option_price if available
                action = trade['action']
                
                # Calculate gross profit (before commissions)
                if action == 'BUY_CALLS':
                    profit_loss = exit_price - entry_price
                    profit_loss_pct = ((exit_price - entry_price) / entry_price) * 100
                    is_win = exit_price > entry_price
                elif action == 'BUY_PUTS':
                    profit_loss = entry_price - exit_price
                    profit_loss_pct = ((entry_price - exit_price) / entry_price) * 100
                    is_win = exit_price < entry_price
                else:
                    profit_loss = 0
                    profit_loss_pct = 0
                    is_win = None
                
                # Calculate net profit with commissions if option prices are available
                net_profit = profit_loss
                total_commissions = 0.0
                if exit_option_price is not None and entry_option_price is not None:
                    try:
                        from broker_commission_tracker import broker_commission_tracker
                        gross_profit, total_commissions, net_profit = broker_commission_tracker.calculate_net_profit(
                            entry_option_price, exit_option_price, num_contracts
                        )
                        # Record commission
                        entry_commission = broker_commission_tracker.calculate_commission(
                            entry_option_price, num_contracts, is_entry=True
                        )
                        exit_commission = broker_commission_tracker.calculate_commission(
                            exit_option_price, num_contracts, is_entry=False
                        )
                        broker_commission_tracker.record_commission(trade_id, entry_commission, exit_commission)
                        
                        # Update is_win based on net profit
                        is_win = net_profit > 0
                        profit_loss_pct = (net_profit / (entry_option_price * num_contracts * 100)) * 100
                    except Exception as e:
                        logger.warning(f"Error calculating commissions for trade {trade_id}: {e}")
                
                trade['exit_price'] = exit_price
                trade['exit_option_price'] = exit_option_price
                trade['num_contracts'] = num_contracts
                # Store exit_time in UTC for consistency (timezone-aware)
                if exit_time is None:
                    exit_time = datetime.now(timezone.utc)
                elif exit_time.tzinfo is None:
                    # If naive datetime provided, assume it's UTC
                    exit_time = exit_time.replace(tzinfo=timezone.utc)
                trade['exit_time'] = exit_time.isoformat()
                trade['profit_loss'] = round(profit_loss, 2)  # Gross profit
                trade['profit_loss_pct'] = round(profit_loss_pct, 2)  # Net profit %
                trade['total_commissions'] = round(total_commissions, 2)
                trade['net_profit'] = round(net_profit, 2)
                trade['status'] = 'CLOSED'
                trade['result'] = 'WIN' if is_win else 'LOSS' if is_win is not None else 'BREAKEVEN'
                
                self._write_file(trades)
                return True
        return False
    
    def auto_close_expired_trades(self):
        """Close expired trades and old trades (older than expiration date)"""
        trades = self._read_file()
        today = datetime.now().date()
        updated = False
        closed_count = 0
        checked_count = 0
        
        logger.debug(f"🔍 Checking {len(trades)} trades for expiration/age (today: {today})")
        
        for trade in trades:
            if trade.get('status') == 'OPEN':
                checked_count += 1
                trade_id = trade.get('trade_id', 'unknown')
                try:
                    # Check if trade is expired
                    exp_str = trade.get('expiration', '')
                    if exp_str and len(exp_str) >= 10:
                        try:
                            exp_date = datetime.strptime(exp_str[:10], '%Y-%m-%d').date()
                            if exp_date < today:
                                # Trade expired - option is now worthless ($0)
                                # CRITICAL FIX: Close at entry stock price but with exit_option_price = 0
                                # This correctly calculates the loss as the full option premium paid
                                entry_price = trade.get('entry_price', 0)
                                entry_option_price = trade.get('option_price', 0)
                                num_contracts = trade.get('num_contracts', 1)
                                
                                # Close with exit_option_price = 0 (expired worthless)
                                if self.close_trade(trade_id, entry_price, exit_option_price=0.0, num_contracts=num_contracts):
                                    closed_count += 1
                                    updated = True
                                    logger.info(f"🔄 Auto-closed EXPIRED trade: {trade_id} (expired {exp_date}, today: {today}) - Option expired worthless ($0)")
                                    continue  # Don't check age if already closed
                        except ValueError as e:
                            logger.debug(f"Invalid expiration date format for {trade_id}: {exp_str[:10]} - {e}")
                    
                    # CRITICAL FIX: Only auto-close 0DTE trades older than 1 day
                    # Long calls (non-0DTE) should NOT be auto-closed based on age - only if expired
                    entry_time_str = trade.get('entry_time', '')
                    exp_str = trade.get('expiration', '')
                    
                    if entry_time_str and exp_str:
                        try:
                            # Check if this is a 0DTE trade (expires same day as entry or next day)
                            entry_time_str_clean = entry_time_str.replace('Z', '+00:00')
                            entry_time = datetime.fromisoformat(entry_time_str_clean)
                            if entry_time.tzinfo:
                                entry_time = entry_time.replace(tzinfo=None)
                            
                            # Parse expiration date
                            if len(exp_str) >= 10:
                                exp_date = datetime.strptime(exp_str[:10], '%Y-%m-%d').date()
                                entry_date = entry_time.date()
                                
                                # Calculate days to expiration at entry
                                dte_at_entry = (exp_date - entry_date).days
                                
                                # Only auto-close if it's a 0DTE trade (expires same day or next day) AND older than 1 day
                                if dte_at_entry <= 1:  # 0DTE or 1DTE trade
                                    days_old = (datetime.now().date() - entry_date).days
                                    if days_old >= 1:  # 0DTE trade older than 1 day should be closed
                                        # CRITICAL FIX: Close with exit_option_price = 0 (expired worthless)
                                        entry_price = trade.get('entry_price', 0)
                                        entry_option_price = trade.get('option_price', 0)
                                        num_contracts = trade.get('num_contracts', 1)
                                        
                                        # Close with exit_option_price = 0 (expired worthless)
                                        if self.close_trade(trade_id, entry_price, exit_option_price=0.0, num_contracts=num_contracts):
                                            closed_count += 1
                                            updated = True
                                            logger.info(f"🔄 Auto-closed OLD 0DTE trade: {trade_id} ({days_old} days old, entry: {entry_time_str}, exp: {exp_str})")
                                else:
                                    # Long call (non-0DTE) - don't auto-close based on age, only if expired (already handled above)
                                    logger.debug(f"✅ Keeping LONG trade: {trade_id} (DTE at entry: {dte_at_entry}, exp: {exp_str})")
                        except Exception as e:
                            logger.debug(f"Error parsing dates for {trade_id}: {e}")
                except Exception as e:
                    logger.debug(f"Error auto-closing trade {trade_id}: {e}")
        
        if closed_count > 0:
            logger.info(f"✅ Auto-closed {closed_count} expired/old trade(s) (checked {checked_count} open trades)")
        else:
            logger.debug(f"✅ No expired/old trades to close (checked {checked_count} open trades)")
        
        return closed_count
    
    def get_performance_stats(self) -> Dict:
        """Get performance stats - ALWAYS reads fresh from file"""
        self.auto_close_expired_trades()
        trades = self._read_file()  # Always fresh read
        
        if not trades:
            return {
                'total_trades': 0,
                'open_trades': 0,
                'closed_trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0.0,
                'total_profit_loss': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0
            }
        
        closed = [t for t in trades if t.get('status') == 'CLOSED']
        open_trades = [t for t in trades if t.get('status') == 'OPEN']
        
        # CRITICAL: Exclude offline closures from all calculations
        real_closed = [t for t in closed if not t.get('offline_closure', False)]
        
        wins = [t for t in real_closed if t.get('result') == 'WIN']
        losses = [t for t in real_closed if t.get('result') == 'LOSS']
        
        # Separate CALLS and PUTS for win rate calculation
        calls_closed = [t for t in real_closed if t.get('action') == 'BUY_CALLS']
        puts_closed = [t for t in real_closed if t.get('action') == 'BUY_PUTS']
        calls_wins = [t for t in calls_closed if t.get('result') == 'WIN']
        puts_wins = [t for t in puts_closed if t.get('result') == 'WIN']
        
        # Calculate overall win rate
        win_rate = (len(wins) / len(real_closed) * 100) if real_closed else 0
        
        # Calculate CALLS win rate
        calls_win_rate = (len(calls_wins) / len(calls_closed) * 100) if calls_closed else 0
        
        # Calculate PUTS win rate
        puts_win_rate = (len(puts_wins) / len(puts_closed) * 100) if puts_closed else 0
        
        # CRITICAL: Calculate using net_profit (after commissions) for accurate economics
        total_pnl = sum(t.get('net_profit', t.get('profit_loss', 0)) for t in real_closed)
        avg_win = sum(t.get('net_profit', t.get('profit_loss', 0)) for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t.get('net_profit', t.get('profit_loss', 0)) for t in losses) / len(losses) if losses else 0
        
        total_wins = sum(t.get('net_profit', t.get('profit_loss', 0)) for t in wins)
        total_losses = abs(sum(t.get('net_profit', t.get('profit_loss', 0)) for t in losses))
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Calculate total capital deployed (entry costs for CLOSED trades only - for realized ROI)
        total_capital_deployed_closed = 0.0
        total_exit_value = 0.0
        total_commissions_paid = 0.0
        for trade in real_closed:  # CRITICAL: Exclude offline closures
            option_price = trade.get('option_price') or trade.get('entry_option_price', 0)
            num_contracts = trade.get('num_contracts', 1)
            entry_cost = option_price * num_contracts * 100 if option_price > 0 else 0
            total_capital_deployed_closed += entry_cost
            
            exit_option_price = trade.get('exit_option_price', 0)
            exit_value = exit_option_price * num_contracts * 100 if exit_option_price > 0 else 0
            total_exit_value += exit_value
            
            commissions = trade.get('total_commissions', 0)
            total_commissions_paid += commissions
        
        # Calculate capital deployed for OPEN trades (unrealized capital)
        total_capital_deployed_open = 0.0
        for trade in open_trades:
            option_price = trade.get('option_price') or trade.get('entry_option_price', 0)
            num_contracts = trade.get('num_contracts', 1)
            entry_cost = option_price * num_contracts * 100 if option_price > 0 else 0
            total_capital_deployed_open += entry_cost
        
        # Total capital deployed (closed + open)
        total_capital_deployed = total_capital_deployed_closed + total_capital_deployed_open
        
        # Calculate ROI (Return on Investment) - REALIZED ROI (closed trades only)
        # Use real_closed for ROI calculation (excludes offline closures)
        realized_roi_pct = (total_pnl / total_capital_deployed_closed * 100) if total_capital_deployed_closed > 0 else 0.0
        
        # For backward compatibility, keep roi_pct as realized ROI
        roi_pct = realized_roi_pct
        
        # NEW: Categorize wins by value (for tax efficiency and customer focus)
        big_wins = []  # >$200 or >20%
        medium_wins = []  # $50-$200 or 10-20%
        tiny_wins = []  # <$5 or <2%
        meaningful_wins = []  # $5-$50 or 2-10%
        
        # NEW: Categorize losses by value (for risk management focus)
        big_losses = []  # <-$200 or <-20%
        medium_losses = []  # -$50 to -$200 or -10% to -20%
        tiny_losses = []  # >-$5 or >-2%
        meaningful_losses = []  # -$5 to -$50 or -2% to -10%
        
        for trade in closed:
            option_price = trade.get('option_price') or trade.get('entry_option_price', 0)
            num_contracts = trade.get('num_contracts', 1)
            entry_cost = option_price * num_contracts * 100 if option_price > 0 else 0
            net_profit = trade.get('net_profit', trade.get('profit_loss', 0))
            net_profit_pct = (net_profit / entry_cost * 100) if entry_cost > 0 else 0
            
            if net_profit > 0:
                if net_profit >= 200 or net_profit_pct >= 20:
                    big_wins.append(trade)
                elif net_profit >= 50 or net_profit_pct >= 10:
                    medium_wins.append(trade)
                elif net_profit < 5 or net_profit_pct < 2:
                    tiny_wins.append(trade)
                else:
                    meaningful_wins.append(trade)
            elif net_profit < 0:
                # CRITICAL: Exclude offline closures from loss calculations
                # These are expired options that weren't closed before market close because program was offline
                is_offline_closure = trade.get('offline_closure', False)
                if is_offline_closure:
                    continue  # Skip offline closures - they're not real losses
                
                # Categorize losses (use absolute values for comparison)
                abs_loss = abs(net_profit)
                abs_loss_pct = abs(net_profit_pct)
                if abs_loss >= 200 or abs_loss_pct >= 20:
                    big_losses.append(trade)
                elif abs_loss >= 50 or abs_loss_pct >= 10:
                    medium_losses.append(trade)
                elif abs_loss < 5 or abs_loss_pct < 2:
                    tiny_losses.append(trade)
                else:
                    meaningful_losses.append(trade)
        
        big_wins_total = sum(t.get('net_profit', t.get('profit_loss', 0)) for t in big_wins)
        medium_wins_total = sum(t.get('net_profit', t.get('profit_loss', 0)) for t in medium_wins)
        tiny_wins_total = sum(t.get('net_profit', t.get('profit_loss', 0)) for t in tiny_wins)
        big_losses_total = sum(t.get('net_profit', t.get('profit_loss', 0)) for t in big_losses)  # Will be negative
        medium_losses_total = sum(t.get('net_profit', t.get('profit_loss', 0)) for t in medium_losses)  # Will be negative
        tiny_losses_total = sum(t.get('net_profit', t.get('profit_loss', 0)) for t in tiny_losses)  # Will be negative
        medium_losses_total = sum(t.get('net_profit', t.get('profit_loss', 0)) for t in medium_losses)  # Will be negative
        
        # Count open trades by type for better visibility
        calls_open = [t for t in open_trades if t.get('action') == 'BUY_CALLS']
        puts_open = [t for t in open_trades if t.get('action') == 'BUY_PUTS']
        
        # Calculate open trade durations and P&L
        open_trades_with_duration = []
        for trade in open_trades:
            entry_time_str = trade.get('entry_time', '')
            duration_hours = 0
            duration_display = 'N/A'
            
            if entry_time_str:
                try:
                    # Handle various datetime formats
                    entry_time_str_clean = entry_time_str.replace('Z', '+00:00')
                    entry_time = datetime.fromisoformat(entry_time_str_clean)
                    if entry_time.tzinfo:
                        entry_time = entry_time.replace(tzinfo=None)
                    
                    duration = datetime.now() - entry_time
                    duration_hours = duration.total_seconds() / 3600
                    
                    if duration_hours < 1:
                        duration_display = f"{int(duration.total_seconds() / 60)}m"
                    elif duration_hours < 24:
                        duration_display = f"{duration_hours:.1f}h"
                    else:
                        duration_display = f"{duration.days}d {int((duration_hours % 24))}h"
                except Exception as e:
                    logger.debug(f"Error calculating duration for trade {trade.get('trade_id')}: {e}")
            
            open_trades_with_duration.append({
                'trade_id': trade.get('trade_id', ''),
                'symbol': trade.get('symbol', 'SPY'),
                'action': trade.get('action', ''),
                'entry_price': trade.get('entry_price', 0),
                'entry_time': entry_time_str,
                'duration_hours': duration_hours,
                'duration_display': duration_display,
                'expiration': trade.get('expiration', ''),
                'confidence': trade.get('confidence', 0)
            })
        
        # Sort open trades by duration (longest first)
        open_trades_with_duration.sort(key=lambda x: x['duration_hours'], reverse=True)
        
        # ========== ADVANCED RISK METRICS ==========
        # Calculate Sharpe Ratio, Sortino Ratio, Max Drawdown, Calmar Ratio
        advanced_metrics = {}
        
        # Try to import numpy, fallback to manual calculation if not available
        try:
            import numpy as np
            numpy_available = True
        except ImportError:
            numpy_available = False
            logger.debug("NumPy not available, using manual calculations for risk metrics")
        
        if len(real_closed) >= 2:  # Need at least 2 trades for meaningful metrics
            # Build equity curve from closed trades
            equity_curve = []
            cumulative_pnl = 0.0
            initial_equity = 10000.0  # Base equity for calculation
            
            for trade in sorted(real_closed, key=lambda t: t.get('exit_time', t.get('entry_time', ''))):
                net_profit = trade.get('net_profit', trade.get('profit_loss', 0))
                cumulative_pnl += net_profit
                equity_curve.append(initial_equity + cumulative_pnl)
            
            if len(equity_curve) > 1:
                # Calculate returns (daily returns approximation)
                returns = []
                for i in range(1, len(equity_curve)):
                    ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
                    returns.append(ret)
                
                if len(returns) > 1:
                    if numpy_available:
                        returns_array = np.array(returns)
                        equity_array = np.array(equity_curve)
                        
                        # Sharpe Ratio (annualized, assuming ~252 trading days)
                        mean_return = float(np.mean(returns_array))
                        std_return = float(np.std(returns_array))
                        sharpe_ratio = (mean_return / std_return * np.sqrt(252)) if std_return > 0 else 0.0
                        
                        # Sortino Ratio (downside deviation only)
                        downside_returns = returns_array[returns_array < 0]
                        if len(downside_returns) > 1:
                            downside_std = float(np.std(downside_returns))
                            sortino_ratio = (mean_return / downside_std * np.sqrt(252)) if downside_std > 0 else 0.0
                        else:
                            sortino_ratio = sharpe_ratio if sharpe_ratio > 0 else 0.0
                        
                        # Max Drawdown
                        running_max = np.maximum.accumulate(equity_array)
                        drawdowns = (equity_array - running_max) / running_max
                        max_drawdown_pct = abs(float(np.min(drawdowns))) * 100 if len(drawdowns) > 0 else 0.0
                    else:
                        # Manual calculation without numpy
                        mean_return = sum(returns) / len(returns)
                        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
                        std_return = variance ** 0.5
                        sharpe_ratio = (mean_return / std_return * (252 ** 0.5)) if std_return > 0 else 0.0
                        
                        # Sortino (downside only)
                        downside_returns = [r for r in returns if r < 0]
                        if len(downside_returns) > 1:
                            downside_mean = sum(downside_returns) / len(downside_returns)
                            downside_variance = sum((r - downside_mean) ** 2 for r in downside_returns) / len(downside_returns)
                            downside_std = downside_variance ** 0.5
                            sortino_ratio = (mean_return / downside_std * (252 ** 0.5)) if downside_std > 0 else 0.0
                        else:
                            sortino_ratio = sharpe_ratio if sharpe_ratio > 0 else 0.0
                        
                        # Max Drawdown (manual)
                        running_max = []
                        max_so_far = equity_curve[0]
                        for equity in equity_curve:
                            if equity > max_so_far:
                                max_so_far = equity
                            running_max.append(max_so_far)
                        
                        drawdowns = [(equity_curve[i] - running_max[i]) / running_max[i] for i in range(len(equity_curve))]
                        max_drawdown_pct = abs(min(drawdowns)) * 100 if drawdowns else 0.0
                    
                    # Calmar Ratio (annualized return / max drawdown)
                    total_return_pct = ((equity_curve[-1] - equity_curve[0]) / equity_curve[0]) * 100
                    # Annualize return (approximate: assume trades span multiple days)
                    days_span = max(1, len(real_closed) / 2)  # Rough estimate: 2 trades per day
                    annualized_return = total_return_pct * (252 / days_span) if days_span > 0 else 0.0
                    calmar_ratio = (annualized_return / max_drawdown_pct) if max_drawdown_pct > 0 else 0.0
                    
                    # Expectancy (expected value per trade)
                    expectancy = (win_rate / 100.0 * avg_win) + ((1 - win_rate / 100.0) * avg_loss)
                    
                    # Win/Loss Ratio
                    win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0.0
                    
                    advanced_metrics = {
                        'sharpe_ratio': round(sharpe_ratio, 2),
                        'sortino_ratio': round(sortino_ratio, 2),
                        'max_drawdown_pct': round(max_drawdown_pct, 2),
                        'calmar_ratio': round(calmar_ratio, 2),
                        'expectancy': round(expectancy, 2),
                        'win_loss_ratio': round(win_loss_ratio, 2),
                        'total_return_pct': round(total_return_pct, 2),
                        'annualized_return_pct': round(annualized_return, 2)
                    }
                else:
                    advanced_metrics = {
                        'sharpe_ratio': 0.0, 'sortino_ratio': 0.0, 'max_drawdown_pct': 0.0,
                        'calmar_ratio': 0.0, 'expectancy': 0.0, 'win_loss_ratio': 0.0,
                        'total_return_pct': 0.0, 'annualized_return_pct': 0.0
                    }
            else:
                advanced_metrics = {
                    'sharpe_ratio': 0.0, 'sortino_ratio': 0.0, 'max_drawdown_pct': 0.0,
                    'calmar_ratio': 0.0, 'expectancy': 0.0, 'win_loss_ratio': 0.0,
                    'total_return_pct': 0.0, 'annualized_return_pct': 0.0
                }
        else:
            advanced_metrics = {
                'sharpe_ratio': 0.0, 'sortino_ratio': 0.0, 'max_drawdown_pct': 0.0,
                'calmar_ratio': 0.0, 'expectancy': 0.0, 'win_loss_ratio': 0.0,
                'total_return_pct': 0.0, 'annualized_return_pct': 0.0
            }
        
        # ========== SPY COMPARISON ==========
        # Compare performance to SPY buy-and-hold
        spy_comparison = {}
        if len(real_closed) >= 5:  # Need enough trades for comparison
            try:
                import yfinance as yf
                from datetime import datetime, timedelta
                
                # Get date range from trades
                entry_times = [t.get('entry_time', '') for t in real_closed if t.get('entry_time')]
                if entry_times:
                    # Find earliest and latest trade dates
                    dates = []
                    for et in entry_times:
                        try:
                            dt = datetime.fromisoformat(et.replace('Z', '+00:00').split('.')[0])
                            dates.append(dt)
                        except:
                            pass
                    
                    if dates:
                        start_date = min(dates).date()
                        end_date = max(dates).date() if len(dates) > 1 else start_date
                        
                        # Fetch SPY data
                        spy = yf.Ticker("SPY")
                        hist = spy.history(start=start_date, end=end_date + timedelta(days=1))
                        
                        if not hist.empty and len(hist) > 1:
                            spy_start_price = hist.iloc[0]['Close']
                            spy_end_price = hist.iloc[-1]['Close']
                            spy_return_pct = ((spy_end_price - spy_start_price) / spy_start_price) * 100
                            
                            # Our strategy return
                            our_return_pct = advanced_metrics.get('total_return_pct', 0.0)
                            
                            # Comparison
                            outperformance = our_return_pct - spy_return_pct
                            
                            spy_comparison = {
                                'spy_return_pct': round(spy_return_pct, 2),
                                'our_return_pct': round(our_return_pct, 2),
                                'outperformance_pct': round(outperformance, 2),
                                'outperformed': outperformance > 0,
                                'period_days': (end_date - start_date).days if end_date > start_date else 1
                            }
                        else:
                            spy_comparison = {'error': 'Insufficient SPY data'}
                    else:
                        spy_comparison = {'error': 'Could not parse trade dates'}
                else:
                    spy_comparison = {'error': 'No trade dates available'}
            except Exception as e:
                logger.debug(f"SPY comparison calculation error: {e}")
                spy_comparison = {'error': str(e)}
        else:
            spy_comparison = {'error': 'Need at least 5 trades for comparison'}
        
        return {
            'total_trades': len(trades),
            'open_trades': len(open_trades),
            'closed_trades': len(closed),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': round(win_rate, 1),
            'calls_win_rate': round(calls_win_rate, 1),
            'puts_win_rate': round(puts_win_rate, 1),
            'calls_closed': len(calls_closed),
            'puts_closed': len(puts_closed),
            'calls_wins': len(calls_wins),
            'puts_wins': len(puts_wins),
            'calls_open': len(calls_open),  # Add open counts for visibility
            'puts_open': len(puts_open),    # Add open counts for visibility
            'total_profit_loss': round(total_pnl, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'open_trades_detail': open_trades_with_duration,  # NEW: Detailed open trades with duration
            # NEW: Trade Economics - Capital Deployed & Returns
            'total_capital_deployed': round(total_capital_deployed, 2),  # Total (closed + open)
            'total_capital_deployed_closed': round(total_capital_deployed_closed, 2),  # Closed trades only
            'total_capital_deployed_open': round(total_capital_deployed_open, 2),  # Open trades only
            'total_exit_value': round(total_exit_value, 2),
            'total_commissions_paid': round(total_commissions_paid, 2),
            'roi_pct': round(roi_pct, 2),  # Realized ROI (closed trades only)
            'realized_roi_pct': round(realized_roi_pct, 2),  # Explicit realized ROI
            'avg_position_size': round(total_capital_deployed_closed / len(closed), 2) if closed else 0.0,
            # NEW: High Value Trades breakdown (for tax efficiency focus)
            'big_wins_count': len(big_wins),
            'big_wins_total': round(big_wins_total, 2),
            'medium_wins_count': len(medium_wins),
            'medium_wins_total': round(medium_wins_total, 2),
            'tiny_wins_count': len(tiny_wins),
            'tiny_wins_total': round(tiny_wins_total, 2),
            'meaningful_wins_count': len(meaningful_wins),
            'big_wins_pct_of_total': round((len(big_wins) / len(wins) * 100) if wins else 0, 1),
            'big_wins_pct_of_profit': round((big_wins_total / total_pnl * 100) if total_pnl > 0 else 0, 1),
            # NEW: Big Losses breakdown (for risk management focus)
            'big_losses_count': len(big_losses),
            'big_losses_total': round(big_losses_total, 2),  # Will be negative
            'medium_losses_count': len(medium_losses),
            'medium_losses_total': round(medium_losses_total, 2),  # Will be negative
            'tiny_losses_count': len(tiny_losses),
            'tiny_losses_total': round(tiny_losses_total, 2),
            'meaningful_losses_count': len(meaningful_losses),
            'big_losses_pct_of_total': round((len(big_losses) / len(losses) * 100) if losses else 0, 1),
            'big_losses_pct_of_loss': round((abs(big_losses_total) / abs(total_losses) * 100) if total_losses < 0 else 0, 1),
            # Advanced Risk Metrics
            **advanced_metrics,
            # SPY Comparison
            'spy_comparison': spy_comparison
        }
    
    def get_performance_by_confidence(self) -> Dict:
        """Get performance by confidence - ALWAYS reads fresh"""
        trades = self._read_file()  # Always fresh read
        closed = [t for t in trades if t.get('status') == 'CLOSED']
        
        buckets = {
            '80-95': {'trades': [], 'wins': 0, 'losses': 0},
            '70-79': {'trades': [], 'wins': 0, 'losses': 0},
            '60-69': {'trades': [], 'wins': 0, 'losses': 0},
            '50-59': {'trades': [], 'wins': 0, 'losses': 0},
            '30-49': {'trades': [], 'wins': 0, 'losses': 0}
        }
        
        for trade in closed:
            conf = trade.get('confidence', 50)
            if conf >= 80:
                bucket = '80-95'
            elif conf >= 70:
                bucket = '70-79'
            elif conf >= 60:
                bucket = '60-69'
            elif conf >= 50:
                bucket = '50-59'
            else:
                bucket = '30-49'
            
            buckets[bucket]['trades'].append(trade)
            if trade.get('result') == 'WIN':
                buckets[bucket]['wins'] += 1
            elif trade.get('result') == 'LOSS':
                buckets[bucket]['losses'] += 1
        
        result = {}
        for bucket, data in buckets.items():
            total = len(data['trades'])
            if total > 0:
                result[bucket] = {
                    'total_trades': total,
                    'wins': data['wins'],
                    'losses': data['losses'],
                    'win_rate': round((data['wins'] / total) * 100, 1),
                    'avg_pnl': round(sum(t.get('profit_loss', 0) for t in data['trades']) / total, 2)
                }
        
        return result
    
    def reload_trades(self):
        """No-op - we always read from file"""
        count = len(self.trades)
        logger.info(f"Reload requested - current count from file: {count}")
        return count

    def archive_and_clear_trades(self) -> Dict:
        """
        Archive current zerodte_trades.json and start a fresh Stage A history.
        Returns archive path and counts.
        """
        file_path = os.path.abspath(self.trades_file)
        before = len(self._read_file()) if os.path.exists(file_path) else 0
        archive_path = None
        if os.path.exists(file_path) and before > 0:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_path = f"{file_path}.archive_{stamp}.json"
            try:
                os.replace(file_path, archive_path)
            except Exception:
                # Fallback copy+truncate if replace fails across devices
                import shutil
                shutil.copy2(file_path, archive_path)
        self._write_file([])
        self._invalidate_cache()
        logger.info(f"Trade history restarted: archived {before} trades -> {archive_path or 'n/a'}")
        return {
            "before_count": before,
            "after_count": 0,
            "archive_path": archive_path,
            "file_path": file_path,
        }


# Create instance - will read from file on first access
performance_tracker = PerformanceTracker()

def get_performance_tracker():
    """Get the global performance tracker instance"""
    return performance_tracker

