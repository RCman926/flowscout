"""
0DTE Flow Tracker - Real-time call/put volume tracking for SPY
Tracks the battle between calls and puts for same-day expiration options
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import logging
from market_hours_detector import get_market_status, is_market_open

logger = logging.getLogger(__name__)

class ZeroDTEFlowTracker:
    """Real-time 0DTE options flow tracker"""
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 30  # 30 seconds cache (reduce rate limiting)
        self.flow_history = {}  # Track flow over time
        
    def get_0dte_options_chain(self, symbol: str = "SPY") -> Dict:
        """
        Get 0DTE (same-day expiration) options chain for symbol
        
        Returns:
            Dict with calls, puts, volumes, and flow metrics
        """
        cache_key = f"{symbol}_0dte"
        current_time = time.time()
        
        # Check cache
        if cache_key in self.cache:
            cached_data, cache_time = self.cache[cache_key]
            if current_time - cache_time < self.cache_duration:
                return cached_data
        
        try:
            ticker = yf.Ticker(symbol)
            
            # Add delay to avoid rate limiting (only if not cached)
            if cache_key not in self.cache:
                time.sleep(3.0)  # 3 second delay to avoid rate limiting
            
            # Get available expiration dates
            try:
                exp_dates = ticker.options
            except Exception as e:
                error_msg = str(e)
                if "rate" in error_msg.lower() or "too many" in error_msg.lower():
                    logger.warning(f"Rate limited by yfinance, waiting 10 seconds...")
                    time.sleep(10.0)
                    try:
                        exp_dates = ticker.options
                    except Exception as retry_error:
                        return self._get_empty_chain(symbol, "Rate limited by yfinance. Please wait 30-60 seconds or connect IB Gateway for real-time data.")
                else:
                    raise e
            
            if not exp_dates:
                return self._get_empty_chain(symbol)
            
            # Get market status
            market_status = get_market_status()
            session = market_status['session']
            
            # Find expiration based on session
            today = datetime.now().date()
            today_str = today.strftime('%Y-%m-%d')
            
            # During regular hours: use 0DTE (today)
            # During after-hours/pre-market/overnight: use 1DTE (tomorrow) for preview
            if session == 'REGULAR':
                target_dte = 0
                target_date = today
                expiration_label = "0DTE (Today)"
            else:
                # After-hours/pre-market/overnight: show tomorrow's expiration as preview
                target_dte = 1
                target_date = today + timedelta(days=1)
                if session == 'OVERNIGHT':
                    expiration_label = "1DTE (Tomorrow - Overnight Preview)"
                elif session == 'AFTER_HOURS':
                    expiration_label = "1DTE (Tomorrow - After-Hours Preview)"
                elif session == 'PRE_MARKET':
                    expiration_label = "1DTE (Tomorrow - Pre-Market Preview)"
                else:
                    expiration_label = "1DTE (Tomorrow - Preview)"
            
            target_exp = None
            
            # Try to find exact match first
            for exp in exp_dates:
                exp_date = datetime.strptime(exp, '%Y-%m-%d').date()
                if exp_date == target_date:
                    target_exp = exp
                    break
            
            # If no exact match, use nearest expiration
            if not target_exp and exp_dates:
                target_exp = exp_dates[0]
                exp_date = datetime.strptime(target_exp, '%Y-%m-%d').date()
                dte = (exp_date - today).days
                
                # Accept if it matches our target DTE, or if it's close (within 1 day)
                if dte == target_dte:
                    logger.info(f"Using {target_dte}DTE expiration ({expiration_label}) for {symbol}")
                elif dte == 1 and session != 'REGULAR':
                    # During extended hours, 1DTE is acceptable
                    logger.info(f"Using 1DTE expiration (Tomorrow - Preview) for {symbol}")
                elif dte == 2 and session != 'REGULAR' and target_dte == 1:
                    # HOLIDAY FIX: During extended hours, if 1DTE not available (holiday), accept 2DTE as fallback
                    expiration_label = f"2DTE (Holiday Fallback - {exp_date.strftime('%Y-%m-%d')})"
                    logger.info(f"Using 2DTE expiration (Holiday Fallback) for {symbol} - 1DTE not available, nearest is {dte}DTE")
                elif dte > 2:
                    # Only reject if more than 2 days away
                    return self._get_empty_chain(symbol, f"No {target_dte}DTE options available. Nearest expiration: {dte} days away.")
                elif dte == 1 and session == 'REGULAR':
                    # During regular hours, we prefer 0DTE but will accept 1DTE if needed
                    logger.warning(f"No 0DTE found, using 1DTE for {symbol}")
                elif dte == 2 and session == 'REGULAR' and target_dte == 0:
                    # HOLIDAY FIX: During regular hours, if 0DTE not available (holiday), accept 2DTE as fallback
                    expiration_label = f"2DTE (Holiday Fallback - {exp_date.strftime('%Y-%m-%d')})"
                    logger.warning(f"No 0DTE or 1DTE found (likely holiday), using 2DTE for {symbol}")
            else:
                target_exp = target_exp or (exp_dates[0] if exp_dates else None)
            
            if not target_exp:
                return self._get_empty_chain(symbol, "No options expirations found")
            
            today_exp = target_exp
            
            # Get options chain
            options_chain = ticker.option_chain(today_exp)
            calls_df = options_chain.calls
            puts_df = options_chain.puts
            
            # Official close outside RTH; avoid last-1m drift vs session close
            try:
                from multi_source_flow_tracker import resolve_yfinance_marks
                from market_hours_detector import get_market_status
                session = (get_market_status() or {}).get('session', 'REGULAR')
                marks = resolve_yfinance_marks(ticker, session=session)
                stock_price = marks["stock_price"]
            except Exception:
                current_price = ticker.history(period="1d", interval="1m")
                if not current_price.empty:
                    stock_price = float(current_price['Close'].iloc[-1])
                else:
                    hist = ticker.history(period="2d")
                    stock_price = float(hist['Close'].iloc[-1]) if not hist.empty else 0
            
            # Process calls
            calls_data = self._process_options(calls_df, 'CALL', stock_price)
            
            # Process puts
            puts_data = self._process_options(puts_df, 'PUT', stock_price)
            
            # Calculate flow metrics
            total_call_volume = calls_data['total_volume']
            total_put_volume = puts_data['total_volume']
            total_call_oi = calls_data['total_open_interest']
            total_put_oi = puts_data['total_open_interest']
            
            # Calculate premium flow (volume * last_price * 100)
            call_premium_flow = sum([
                row.get('volume', 0) * row.get('lastPrice', 0) * 100 
                for _, row in calls_df.iterrows() 
                if pd.notna(row.get('volume')) and pd.notna(row.get('lastPrice'))
            ])
            
            put_premium_flow = sum([
                row.get('volume', 0) * row.get('lastPrice', 0) * 100 
                for _, row in puts_df.iterrows() 
                if pd.notna(row.get('volume')) and pd.notna(row.get('lastPrice'))
            ])
            
            # Net flow
            net_volume_flow = total_call_volume - total_put_volume
            net_premium_flow = call_premium_flow - put_premium_flow
            
            # Call/Put ratio
            cp_ratio = total_call_volume / max(1, total_put_volume)
            
            # Determine flow direction
            if net_volume_flow > 10000:
                flow_direction = "STRONG_CALLS"
            elif net_volume_flow > 2000:
                flow_direction = "CALLS"
            elif net_volume_flow < -10000:
                flow_direction = "STRONG_PUTS"
            elif net_volume_flow < -2000:
                flow_direction = "PUTS"
            else:
                flow_direction = "NEUTRAL"
            
            # Add expiration label for display
            exp_date_obj = datetime.strptime(today_exp, '%Y-%m-%d').date()
            dte_actual = (exp_date_obj - today).days
            if session == 'REGULAR':
                if dte_actual == 0:
                    exp_label = f"0DTE ({today_exp})"
                elif dte_actual == 2:
                    # HOLIDAY FIX: 2DTE fallback when 0DTE/1DTE not available
                    exp_label = f"2DTE (Holiday Fallback - {today_exp})"
                else:
                    exp_label = f"{dte_actual}DTE ({today_exp})"
            else:
                if dte_actual == 1:
                    exp_label = f"1DTE Preview ({today_exp})"
                elif dte_actual == 2:
                    # HOLIDAY FIX: 2DTE fallback when 1DTE not available (holiday)
                    exp_label = f"2DTE (Holiday Fallback - {today_exp})"
                else:
                    exp_label = f"{dte_actual}DTE ({today_exp})"
            
            result = {
                'symbol': symbol,
                'stock_price': stock_price,
                'expiration': today_exp,
                'expiration_label': exp_label,
                'dte': dte_actual,
                'session': session,
                'timestamp': datetime.now(),
                'calls': calls_data,
                'puts': puts_data,
                'flow_metrics': {
                    'total_call_volume': int(total_call_volume),
                    'total_put_volume': int(total_put_volume),
                    'total_call_oi': int(total_call_oi),
                    'total_put_oi': int(total_put_oi),
                    'call_premium_flow': call_premium_flow,
                    'put_premium_flow': put_premium_flow,
                    'net_volume_flow': int(net_volume_flow),
                    'net_premium_flow': net_premium_flow,
                    'call_put_ratio': round(cp_ratio, 2),
                    'flow_direction': flow_direction
                },
                'strikes': {
                    'calls_by_strike': calls_data['by_strike'],
                    'puts_by_strike': puts_data['by_strike']
                },
                'market_status': market_status
            }
            
            # Cache result
            self.cache[cache_key] = (result, current_time)
            
            # Update flow history
            if symbol not in self.flow_history:
                self.flow_history[symbol] = []
            
            self.flow_history[symbol].append({
                'timestamp': datetime.now(),
                'call_volume': total_call_volume,
                'put_volume': total_put_volume,
                'net_flow': net_volume_flow,
                'flow_direction': flow_direction
            })
            
            # Keep only last 100 data points
            if len(self.flow_history[symbol]) > 100:
                self.flow_history[symbol] = self.flow_history[symbol][-100:]
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error getting 0DTE options chain for {symbol}: {error_msg}")
            
            # If it's a database corruption error, suggest clearing cache
            if "database" in error_msg.lower() or "malformed" in error_msg.lower():
                error_msg += " (Try clearing yfinance cache: POST /clear-cache)"
            
            return self._get_empty_chain(symbol, error_msg)
    
    def _process_options(self, df: pd.DataFrame, option_type: str, stock_price: float) -> Dict:
        """Process options DataFrame into structured data"""
        if df.empty:
            return {
                'total_volume': 0,
                'total_open_interest': 0,
                'by_strike': []
            }
        
        total_volume = 0
        total_oi = 0
        by_strike = []
        
        for _, row in df.iterrows():
            strike = float(row.get('strike', 0))
            volume = float(row.get('volume', 0)) if pd.notna(row.get('volume')) else 0
            oi = float(row.get('openInterest', 0)) if pd.notna(row.get('openInterest')) else 0
            last_price = float(row.get('lastPrice', 0)) if pd.notna(row.get('lastPrice')) else 0
            bid = float(row.get('bid', 0)) if pd.notna(row.get('bid')) else 0
            ask = float(row.get('ask', 0)) if pd.notna(row.get('ask')) else 0
            iv = float(row.get('impliedVolatility', 0)) if pd.notna(row.get('impliedVolatility')) else 0
            
            # Calculate moneyness
            if option_type == 'CALL':
                moneyness = "ITM" if strike < stock_price else "OTM" if strike > stock_price else "ATM"
            else:  # PUT
                moneyness = "ITM" if strike > stock_price else "OTM" if strike < stock_price else "ATM"
            
            # Premium flow for this strike
            premium_flow = volume * last_price * 100 if last_price > 0 else 0
            
            total_volume += volume
            total_oi += oi
            
            by_strike.append({
                'strike': strike,
                'volume': int(volume),
                'open_interest': int(oi),
                'last_price': last_price,
                'bid': bid,
                'ask': ask,
                'iv': iv,
                'moneyness': moneyness,
                'premium_flow': premium_flow,
                'distance_from_price': abs(strike - stock_price)
            })
        
        # Sort by volume descending
        by_strike.sort(key=lambda x: x['volume'], reverse=True)
        
        return {
            'total_volume': int(total_volume),
            'total_open_interest': int(total_oi),
            'by_strike': by_strike
        }
    
    def _get_empty_chain(self, symbol: str, reason: str = "No data available") -> Dict:
        """Return empty chain structure"""
        return {
            'symbol': symbol,
            'stock_price': 0,
            'expiration': None,
            'timestamp': datetime.now(),
            'calls': {
                'total_volume': 0,
                'total_open_interest': 0,
                'by_strike': []
            },
            'puts': {
                'total_volume': 0,
                'total_open_interest': 0,
                'by_strike': []
            },
            'flow_metrics': {
                'total_call_volume': 0,
                'total_put_volume': 0,
                'total_call_oi': 0,
                'total_put_oi': 0,
                'call_premium_flow': 0,
                'put_premium_flow': 0,
                'net_volume_flow': 0,
                'net_premium_flow': 0,
                'call_put_ratio': 1.0,
                'flow_direction': 'NEUTRAL'
            },
            'strikes': {
                'calls_by_strike': [],
                'puts_by_strike': []
            },
            'error': reason
        }
    
    def get_flow_momentum(self, symbol: str = "SPY") -> Dict:
        """Calculate flow momentum from history"""
        if symbol not in self.flow_history or len(self.flow_history[symbol]) < 3:
            return {
                'trend': 'NEUTRAL',
                'momentum': 0,
                'acceleration': 0
            }
        
        history = self.flow_history[symbol][-20:]  # Last 20 data points
        
        if len(history) < 3:
            return {
                'trend': 'NEUTRAL',
                'momentum': 0,
                'acceleration': 0
            }
        
        # Calculate trend from net flows
        net_flows = [h['net_flow'] for h in history]
        
        # Simple linear regression for trend
        x = np.arange(len(net_flows))
        if len(net_flows) > 1:
            slope = np.polyfit(x, net_flows, 1)[0]
        else:
            slope = 0
        
        # Determine trend
        if slope > 500:
            trend = 'STRONG_BULLISH'
        elif slope > 100:
            trend = 'BULLISH'
        elif slope < -500:
            trend = 'STRONG_BEARISH'
        elif slope < -100:
            trend = 'BEARISH'
        else:
            trend = 'NEUTRAL'
        
        # Calculate acceleration (change in slope)
        if len(net_flows) >= 6:
            recent_slope = np.polyfit(x[-6:], net_flows[-6:], 1)[0]
            earlier_slope = np.polyfit(x[-12:-6], net_flows[-12:-6], 1)[0] if len(net_flows) >= 12 else 0
            acceleration = recent_slope - earlier_slope
        else:
            acceleration = 0
        
        return {
            'trend': trend,
            'momentum': slope,
            'acceleration': acceleration,
            'recent_net_flow': net_flows[-1] if net_flows else 0
        }

# Global instance
flow_tracker = ZeroDTEFlowTracker()

