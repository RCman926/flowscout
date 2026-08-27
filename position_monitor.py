"""
Real-Time Position Monitor
Monitors open positions and suggests optimal exit points
Includes trailing stops, time-based exits, and gamma risk management
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class PositionMonitor:
    """
    Real-time position monitoring system that:
    1. Tracks open positions
    2. Suggests exits based on trailing stops
    3. Enforces time-based exits (critical for 0DTE)
    4. Monitors gamma risk
    5. Suggests profit-taking at optimal levels
    """
    
    def __init__(self):
        self.trailing_stops = {}  # trade_id -> {stop_price, highest_price, trail_pct}
        self.position_history = defaultdict(list)  # trade_id -> list of (timestamp, price)
        self.gamma_warnings = {}  # trade_id -> warning level
        
        # Configuration
        self.trailing_stop_pct = 0.03  # 3% trailing stop (locks in profits)
        self.initial_stop_pct = 0.05  # 5% initial stop loss
        self.time_exit_hour = 15  # Exit at 3 PM ET (15:00) to avoid gamma risk
        self.time_exit_minute = 0
        self.min_profit_for_trailing = 0.02  # Start trailing after 2% profit
        # CRITICAL: 0DTE options must be closed before market close to avoid theta decay
        self.force_close_0dte_hour = 15  # 3 PM ET - force close all 0DTE before market close
        self.force_close_0dte_minute = 30  # 3:30 PM ET - absolute deadline for 0DTE
        
    def update_position(self, trade_id: str, current_price: float, 
                       entry_price: float, action: str, entry_time: str,
                       conditions: Optional[Dict] = None) -> Dict:
        """
        Update position tracking and return exit recommendations
        
        Returns:
            Dict with exit_suggested, exit_reason, exit_urgency
        """
        # Track price history
        self.position_history[trade_id].append({
            'timestamp': datetime.now().isoformat(),
            'price': current_price
        })
        # Keep only last 100 updates
        if len(self.position_history[trade_id]) > 100:
            self.position_history[trade_id] = self.position_history[trade_id][-100:]
        
        # Calculate current P&L
        if action == 'BUY_CALLS':
            profit_pct = ((current_price - entry_price) / entry_price) * 100
        else:  # BUY_PUTS
            profit_pct = ((entry_price - current_price) / entry_price) * 100
        
        # Initialize trailing stop if not exists
        if trade_id not in self.trailing_stops:
            if action == 'BUY_CALLS':
                self.trailing_stops[trade_id] = {
                    'stop_price': entry_price * (1 - self.initial_stop_pct),
                    'highest_price': entry_price,
                    'lowest_price': entry_price,
                    'trail_pct': self.trailing_stop_pct
                }
            else:  # BUY_PUTS
                # For PUTS: stop_price is ABOVE entry (when SPY goes up, puts lose)
                # Initial stop: entry_price * 1.05 (5% above entry = 5% loss on puts)
                self.trailing_stops[trade_id] = {
                    'stop_price': entry_price * (1 + self.initial_stop_pct),  # 5% above entry
                    'highest_price': entry_price,  # Track when SPY goes UP (bad for puts)
                    'lowest_price': entry_price,   # Track when SPY goes DOWN (good for puts)
                    'trail_pct': self.trailing_stop_pct
                }
        
        trail = self.trailing_stops[trade_id]
        
        # Update trailing stop for CALLS
        if action == 'BUY_CALLS':
            if current_price > trail['highest_price']:
                trail['highest_price'] = current_price
                # Only start trailing after minimum profit
                if profit_pct >= self.min_profit_for_trailing * 100:
                    trail['stop_price'] = current_price * (1 - self.trailing_stop_pct)
            # Check if stop hit
            if current_price <= trail['stop_price']:
                return {
                    'exit_suggested': True,
                    'exit_reason': f"Trailing stop hit: {profit_pct:.1f}% profit locked in",
                    'exit_urgency': 'HIGH',
                    'exit_type': 'TRAILING_STOP',
                    'current_profit_pct': profit_pct
                }
        
        # Update trailing stop for PUTS
        else:  # BUY_PUTS
            # For PUTS: track when price goes UP (bad for puts) - this is when we need to exit
            if current_price > trail.get('highest_price', entry_price):
                trail['highest_price'] = current_price
                # Update stop loss when price goes up (SPY rising = puts losing)
                # Stop should be triggered when price goes above entry + stop_pct
                # For puts, stop_price should be entry_price * (1 + stop_pct) initially
                # Then trail it down as price goes up
                if profit_pct < 0:  # Already in loss - tighten stop
                    # Set stop at entry + initial_stop_pct (5% above entry)
                    trail['stop_price'] = entry_price * (1 + self.initial_stop_pct)
                elif profit_pct >= self.min_profit_for_trailing * 100:
                    # We had profit, now price is going up - trail the stop
                    # Stop should be at lowest_price + trailing_stop_pct
                    if 'lowest_price' in trail:
                        trail['stop_price'] = trail['lowest_price'] * (1 + self.trailing_stop_pct)
            
            # Track lowest price for trailing stop when in profit
            if current_price < trail.get('lowest_price', entry_price):
                trail['lowest_price'] = current_price
                # Only start trailing after minimum profit
                if profit_pct >= self.min_profit_for_trailing * 100:
                    trail['stop_price'] = current_price * (1 + self.trailing_stop_pct)
            
            # CRITICAL: Check if stop hit - when SPY goes UP, puts should exit
            # For PUTS: exit when current_price >= stop_price (SPY rising = puts losing)
            if current_price >= trail['stop_price']:
                return {
                    'exit_suggested': True,
                    'exit_reason': f"Stop loss hit: SPY rising to ${current_price:.2f} (stop: ${trail['stop_price']:.2f}) - {profit_pct:.1f}% P&L",
                    'exit_urgency': 'HIGH',
                    'exit_type': 'STOP_LOSS' if profit_pct < 0 else 'TRAILING_STOP',
                    'current_profit_pct': profit_pct
                }
        
        # Time-based exit (critical for 0DTE)
        # Get expiration from conditions if available
        expiration = conditions.get('expiration') if conditions else None
        exit_suggestion = self._check_time_based_exit(entry_time, profit_pct, expiration=expiration)
        if exit_suggestion:
            return exit_suggestion
        
        # Adaptive profit target exits (learns when to hold for bigger wins)
        try:
            from profit_target_learner import profit_target_learner
            
            # Calculate time since entry
            try:
                entry_dt = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
                now = datetime.now(entry_dt.tzinfo) if entry_dt.tzinfo else datetime.now()
                time_since_entry = (now - entry_dt).total_seconds() / 60  # minutes
                current_hour = now.hour
            except:
                time_since_entry = 0
                current_hour = datetime.now().hour
            
            # Get market conditions
            if conditions is None:
                conditions = {}
            momentum = conditions.get('momentum', 0)
            volume_change = conditions.get('volume_change', 0)
            conditions['time_of_day'] = current_hour
            
            # Get adaptive profit target
            target_profit, target_reasoning = profit_target_learner.get_adaptive_profit_target(
                profit_pct, conditions, current_hour, int(time_since_entry)
            )
            
            # Check if we should hold for more
            should_hold, hold_reasoning = profit_target_learner.should_hold_for_more(
                profit_pct, conditions, current_hour, int(time_since_entry),
                momentum, volume_change
            )
            
            # If we should hold, don't suggest exit yet (unless very late in day)
            if should_hold and current_hour < 15:
                return {
                    'exit_suggested': False,
                    'exit_reason': hold_reasoning,
                    'exit_urgency': 'NONE',
                    'current_profit_pct': profit_pct,
                    'target_profit_pct': target_profit,
                    'hold_reasoning': hold_reasoning
                }
            
            # Check against adaptive target
            if profit_pct >= target_profit:
                urgency = 'HIGH' if profit_pct >= target_profit * 1.5 else 'MEDIUM'
                return {
                    'exit_suggested': True,
                    'exit_reason': f"Adaptive target reached: {profit_pct:.1f}% (target: {target_profit:.1f}%) - {target_reasoning}",
                    'exit_urgency': urgency,
                    'exit_type': 'ADAPTIVE_PROFIT_TARGET',
                    'current_profit_pct': profit_pct,
                    'target_profit_pct': target_profit
                }
            elif profit_pct >= target_profit * 0.8:  # Within 80% of target
                return {
                    'exit_suggested': True,
                    'exit_reason': f"Near adaptive target: {profit_pct:.1f}% (target: {target_profit:.1f}%) - Consider taking",
                    'exit_urgency': 'LOW',
                    'exit_type': 'PROFIT_TAKING',
                    'current_profit_pct': profit_pct,
                    'target_profit_pct': target_profit
                }
        
        except ImportError:
            # FIXED: Increased profit targets significantly for BIG WINNERS
            # Only close at 25%+ for large winners, 20%+ for medium
            # Removed 5% and 10% exits - let trades run longer for bigger wins
            if profit_pct >= 50:
                return {
                    'exit_suggested': True,
                    'exit_reason': f"HUGE profit target reached: {profit_pct:.1f}% - Take profit!",
                    'exit_urgency': 'HIGH',
                    'exit_type': 'PROFIT_TARGET',
                    'current_profit_pct': profit_pct
                }
            elif profit_pct >= 30:
                return {
                    'exit_suggested': True,
                    'exit_reason': f"Large profit target reached: {profit_pct:.1f}% - Strong winner!",
                    'exit_urgency': 'HIGH',
                    'exit_type': 'PROFIT_TARGET',
                    'current_profit_pct': profit_pct
                }
            elif profit_pct >= 25:
                return {
                    'exit_suggested': True,
                    'exit_reason': f"Big profit target reached: {profit_pct:.1f}% - Good winner!",
                    'exit_urgency': 'MEDIUM',
                    'exit_type': 'PROFIT_TARGET',
                    'current_profit_pct': profit_pct
                }
            elif profit_pct >= 20:
                return {
                    'exit_suggested': True,
                    'exit_reason': f"Solid profit: {profit_pct:.1f}% - Consider taking",
                    'exit_urgency': 'MEDIUM',
                    'exit_type': 'PROFIT_TAKING',
                    'current_profit_pct': profit_pct
                }
            # REMOVED: 5% and 10% exits - let trades run for bigger wins
        except Exception as e:
            logger.debug(f"Error in adaptive profit target: {e}")
            # FIXED: Fallback with higher targets for big winners
            if profit_pct >= 50:
                return {
                    'exit_suggested': True,
                    'exit_reason': f"HUGE profit: {profit_pct:.1f}% - Take profit!",
                    'exit_urgency': 'HIGH',
                    'exit_type': 'PROFIT_TARGET',
                    'current_profit_pct': profit_pct
                }
            elif profit_pct >= 30:
                return {
                    'exit_suggested': True,
                    'exit_reason': f"Large profit: {profit_pct:.1f}% - Strong winner!",
                    'exit_urgency': 'HIGH',
                    'exit_type': 'PROFIT_TARGET',
                    'current_profit_pct': profit_pct
                }
            elif profit_pct >= 25:
                return {
                    'exit_suggested': True,
                    'exit_reason': f"Big profit: {profit_pct:.1f}% - Good winner!",
                    'exit_urgency': 'MEDIUM',
                    'exit_type': 'PROFIT_TARGET',
                    'current_profit_pct': profit_pct
                }
        
        # Volatility-based exit: Close if high volatility threatens profits
        # Calculate recent volatility from price movement
        try:
            if conditions and 'recent_prices' in conditions:
                recent_prices = conditions['recent_prices']
                if len(recent_prices) >= 5:
                    price_changes = [abs(recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1] * 100 
                                   for i in range(1, len(recent_prices))]
                    avg_volatility = sum(price_changes) / len(price_changes) if price_changes else 0
                    
                    # If high volatility (>2% per period) and we have profit, consider closing to protect gains
                    if avg_volatility > 2.0 and profit_pct > 5:
                        return {
                            'exit_suggested': True,
                            'exit_reason': f"High volatility ({avg_volatility:.1f}%) + profit ({profit_pct:.1f}%) - Protect gains",
                            'exit_urgency': 'MEDIUM',
                            'exit_type': 'VOLATILITY_EXIT',
                            'current_profit_pct': profit_pct,
                            'volatility_pct': avg_volatility
                        }
        except Exception as e:
            logger.debug(f"Error calculating volatility exit: {e}")
        
        # Stop loss check - CRITICAL for PUTS when SPY is flying up
        # For PUTS: negative profit_pct means SPY went up (puts losing)
        # For CALLS: negative profit_pct means SPY went down (calls losing)
        if profit_pct <= -5:  # 5% loss - hard stop (SPY moved against position)
            urgency = 'HIGH'
            if action == 'BUY_PUTS' and profit_pct <= -7:
                urgency = 'CRITICAL'  # SPY flying up = puts getting crushed
            return {
                'exit_suggested': True,
                'exit_reason': f"Stop loss hit: {profit_pct:.1f}% loss ({'SPY rising' if action == 'BUY_PUTS' else 'SPY falling'})",
                'exit_urgency': urgency,
                'exit_type': 'STOP_LOSS',
                'current_profit_pct': profit_pct
            }
        elif profit_pct <= -3:  # 3% loss - warning
            urgency = 'MEDIUM'
            if action == 'BUY_PUTS':
                urgency = 'HIGH'  # More urgent for puts when SPY rising
            return {
                'exit_suggested': True,
                'exit_reason': f"Approaching stop loss: {profit_pct:.1f}% loss ({'SPY rising' if action == 'BUY_PUTS' else 'SPY falling'})",
                'exit_urgency': urgency,
                'exit_type': 'STOP_LOSS_WARNING',
                'current_profit_pct': profit_pct
            }
        
        # No exit needed
        return {
            'exit_suggested': False,
            'exit_reason': '',
            'exit_urgency': 'NONE',
            'current_profit_pct': profit_pct,
            'trailing_stop_price': trail['stop_price']
        }
    
    def _check_time_based_exit(self, entry_time: str, profit_pct: float, expiration: str = None) -> Optional[Dict]:
        """
        Check if position should be exited based on time
        For 0DTE, FORCE EXIT before market close (3:30 PM ET) to avoid theta decay
        CRITICAL: All 0DTE options must be closed before 3:30 PM ET
        """
        try:
            entry_dt = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
            now = datetime.now(entry_dt.tzinfo) if entry_dt.tzinfo else datetime.now()
            
            # Get current hour (ET timezone)
            # Simple approximation: assume server is in ET or adjust accordingly
            current_hour = now.hour
            current_minute = now.minute
            
            # Check if this is a 0DTE option (expires today)
            is_0dte = False
            if expiration:
                try:
                    exp_date = datetime.strptime(expiration[:10], '%Y-%m-%d').date()
                    entry_date = entry_dt.date()
                    dte = (exp_date - entry_date).days
                    is_0dte = (dte == 0)
                except:
                    pass
            
            # CRITICAL: FORCE CLOSE all 0DTE options before market close (3:30 PM ET / 15:30)
            # Market closes at 4 PM ET, but we need to exit by 3:30 PM to avoid theta decay
            if is_0dte:
                # After 3:30 PM (15:30) - FORCE EXIT regardless of profit/loss
                if current_hour > self.force_close_0dte_hour or (current_hour == self.force_close_0dte_hour and current_minute >= self.force_close_0dte_minute):
                    return {
                        'exit_suggested': True,
                        'exit_reason': f"FORCE CLOSE: 0DTE option must close before market close (3:30 PM ET) - Current: {profit_pct:.1f}%",
                        'exit_urgency': 'HIGH',
                        'exit_type': 'FORCE_CLOSE_0DTE',
                        'current_profit_pct': profit_pct
                    }
                # Warning at 3:00 PM (15:00) - prepare to force close
                elif current_hour == self.force_close_0dte_hour and current_minute >= 0:
                    return {
                        'exit_suggested': True,
                        'exit_reason': f"WARNING: 0DTE option - Must close before 3:30 PM ET (Current: {profit_pct:.1f}%)",
                        'exit_urgency': 'HIGH',
                        'exit_type': 'TIME_WARNING_0DTE',
                        'current_profit_pct': profit_pct
                    }
                # Early warning at 2:30 PM (14:30) - start preparing
                elif current_hour == 14 and current_minute >= 30:
                    return {
                        'exit_suggested': True,
                        'exit_reason': f"0DTE Alert: Close before 3:30 PM ET to avoid theta decay (Current: {profit_pct:.1f}%)",
                        'exit_urgency': 'MEDIUM',
                        'exit_type': 'TIME_WARNING_0DTE',
                        'current_profit_pct': profit_pct
                    }
            
            # For non-0DTE options, use original logic
            # Exit at 3 PM (15:00) or later - CRITICAL for 0DTE
            if current_hour >= self.time_exit_hour:
                if current_hour > self.time_exit_hour or current_minute >= self.time_exit_minute:
                    # Force exit if in loss or small profit
                    if profit_pct <= 2:
                        return {
                            'exit_suggested': True,
                            'exit_reason': f"Time-based exit: After 3 PM ET (gamma risk) - {profit_pct:.1f}% P&L",
                            'exit_urgency': 'HIGH',
                            'exit_type': 'TIME_BASED',
                            'current_profit_pct': profit_pct
                        }
                    # Suggest exit if moderate profit (lock it in)
                    elif profit_pct < 10:
                        return {
                            'exit_suggested': True,
                            'exit_reason': f"Time-based exit recommended: After 3 PM ET (lock in {profit_pct:.1f}% profit)",
                            'exit_urgency': 'MEDIUM',
                            'exit_type': 'TIME_BASED',
                            'current_profit_pct': profit_pct
                        }
            
            # Warning at 2:30 PM (14:30) - prepare to exit
            elif current_hour == 14 and current_minute >= 30:
                return {
                    'exit_suggested': True,
                    'exit_reason': f"Time warning: Approaching 3 PM ET - Consider exit at {profit_pct:.1f}%",
                    'exit_urgency': 'LOW',
                    'exit_type': 'TIME_WARNING',
                    'current_profit_pct': profit_pct
                }
        
        except Exception as e:
            logger.debug(f"Error checking time-based exit: {e}")
        
        return None
    
    def get_trailing_stop_price(self, trade_id: str) -> Optional[float]:
        """Get current trailing stop price for a position"""
        if trade_id in self.trailing_stops:
            return self.trailing_stops[trade_id].get('stop_price')
        return None
    
    def cleanup_position(self, trade_id: str):
        """Remove position from tracking when closed"""
        if trade_id in self.trailing_stops:
            del self.trailing_stops[trade_id]
        if trade_id in self.position_history:
            del self.position_history[trade_id]
        if trade_id in self.gamma_warnings:
            del self.gamma_warnings[trade_id]


# Global instance
position_monitor = PositionMonitor()

