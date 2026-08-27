"""
Enhanced Signal Analyzer - High-Powered Prediction Improvements
Adds momentum tracking, time decay, volatility context, and better strike analysis
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
import logging
from zerodte_signal_analyzer import ZeroDTESignalAnalyzer
try:
    from order_flow_history import order_flow_history
except ImportError:
    # Fallback if order_flow_history not available
    order_flow_history = None

logger = logging.getLogger(__name__)


class EnhancedSignalAnalyzer(ZeroDTESignalAnalyzer):
    """
    Enhanced signal analyzer with:
    - Momentum tracking (flow velocity)
    - Time decay weighting
    - Volatility context
    - Better strike concentration analysis
    """
    
    def __init__(self):
        super().__init__()
        self.momentum_window = 10  # Track last 10 data points for momentum
        
    def analyze_flow_signal(self, flow_data: Dict) -> Dict:
        """
        Enhanced flow signal analysis with momentum and time decay
        """
        # Get base signal from parent class
        base_signal = super().analyze_flow_signal(flow_data)
        
        if base_signal.get('signal') == 'NO_SIGNAL':
            return base_signal
        
        # Enhance with momentum
        momentum_analysis = self._analyze_momentum(flow_data)
        
        # Enhance with time decay
        time_decay_factor = self._calculate_time_decay_factor(flow_data)
        
        # Enhance with volatility context
        volatility_factor = self._get_volatility_factor(flow_data)
        
        # Enhance strike analysis
        enhanced_strike_analysis = self._enhanced_strike_analysis(flow_data)
        
        # Adjust confidence based on enhancements
        base_confidence = base_signal.get('confidence', 50)
        
        # Momentum boost/reduction
        momentum_boost = 0
        if momentum_analysis['trend'] == 'ACCELERATING' and momentum_analysis['direction'] == base_signal.get('action', ''):
            momentum_boost = 10  # Strong momentum in same direction
        elif momentum_analysis['trend'] == 'DECELERATING':
            momentum_boost = -5  # Losing momentum
        
        # Time decay adjustment
        time_adjusted_confidence = base_confidence * time_decay_factor
        
        # Volatility adjustment
        vol_adjusted_confidence = time_adjusted_confidence * volatility_factor
        
        # Final confidence with momentum
        final_confidence = min(95, max(30, vol_adjusted_confidence + momentum_boost))
        
        # Update recommendation
        recommendation = base_signal.get('recommendation', {})
        recommendation['confidence'] = int(final_confidence)
        recommendation['momentum'] = momentum_analysis
        recommendation['time_decay_factor'] = round(time_decay_factor, 2)
        recommendation['volatility_factor'] = round(volatility_factor, 2)
        
        # Enhanced reasoning
        reasoning_parts = [base_signal.get('reasoning', '')]
        
        if momentum_analysis['trend'] == 'ACCELERATING':
            reasoning_parts.append(f"Momentum: {momentum_analysis['direction']} flow accelerating (+{momentum_boost}% confidence)")
        elif momentum_analysis['trend'] == 'DECELERATING':
            reasoning_parts.append(f"Momentum: Flow decelerating (-5% confidence)")
        
        if time_decay_factor > 1.1:
            reasoning_parts.append(f"Time advantage: {time_decay_factor:.1f}x (morning signal)")
        elif time_decay_factor < 0.9:
            reasoning_parts.append(f"Time constraint: {time_decay_factor:.1f}x (late in day)")
        
        if volatility_factor < 0.8:
            reasoning_parts.append(f"High volatility: Reduced confidence due to market uncertainty")
        
        recommendation['reasoning'] = " | ".join(reasoning_parts)
        
        return {
            **base_signal,
            'confidence': int(final_confidence),
            'recommendation': recommendation,
            'enhancements': {
                'momentum': momentum_analysis,
                'time_decay_factor': round(time_decay_factor, 2),
                'volatility_factor': round(volatility_factor, 2),
                'momentum_boost': momentum_boost,
                'strike_analysis': enhanced_strike_analysis
            }
        }
    
    def _analyze_momentum(self, flow_data: Dict) -> Dict:
        """
        Analyze flow momentum (velocity and acceleration)
        """
        if not order_flow_history:
            return {
                'trend': 'INSUFFICIENT_DATA',
                'direction': 'NONE',
                'velocity': 0,
                'acceleration': 0
            }
        
        symbol = flow_data.get('symbol', 'SPY')
        recent_flow = order_flow_history.get_recent_flow(symbol, count=self.momentum_window)
        
        if len(recent_flow) < 3:
            return {
                'trend': 'INSUFFICIENT_DATA',
                'direction': 'NONE',
                'velocity': 0,
                'acceleration': 0
            }
        
        # Calculate net flow velocity (change over time)
        current_net = recent_flow[-1].get('net_flow', 0)
        previous_net = recent_flow[-2].get('net_flow', 0) if len(recent_flow) >= 2 else current_net
        earlier_net = recent_flow[-3].get('net_flow', 0) if len(recent_flow) >= 3 else previous_net
        
        velocity = current_net - previous_net
        previous_velocity = previous_net - earlier_net
        acceleration = velocity - previous_velocity
        
        # Determine trend
        if acceleration > 0 and velocity > 0:
            trend = 'ACCELERATING'
            direction = 'CALLS' if current_net > 0 else 'PUTS'
        elif acceleration < 0 and velocity < 0:
            trend = 'DECELERATING'
            direction = 'CALLS' if current_net > 0 else 'PUTS'
        elif abs(velocity) > abs(previous_velocity):
            trend = 'ACCELERATING'
            direction = 'CALLS' if current_net > 0 else 'PUTS'
        else:
            trend = 'STABLE'
            direction = 'CALLS' if current_net > 0 else 'PUTS' if current_net < 0 else 'NEUTRAL'
        
        return {
            'trend': trend,
            'direction': direction,
            'velocity': velocity,
            'acceleration': acceleration,
            'current_net_flow': current_net,
            'previous_net_flow': previous_net
        }
    
    def _calculate_time_decay_factor(self, flow_data: Dict) -> float:
        """
        Calculate time decay factor based on time until expiration
        Morning signals get higher weight (more time to play out)
        """
        try:
            from market_hours_detector import get_market_status
            market_status = get_market_status()
            
            if market_status['session'] != 'REGULAR':
                return 1.0  # No time decay outside regular hours
            
            # Get current time
            now = datetime.now()
            current_hour = now.hour
            current_minute = now.minute
            
            # Market hours: 9:30 AM - 4:00 PM ET
            market_open = 9.5  # 9:30 AM = 9.5
            market_close = 16.0  # 4:00 PM = 16.0
            
            current_time_decimal = current_hour + (current_minute / 60.0)
            
            # Calculate time remaining until close
            time_remaining = market_close - current_time_decimal
            total_market_hours = market_close - market_open
            
            # Weight factor: More time = Higher weight
            # Morning (9:30-11 AM): 1.2x weight
            # Midday (11 AM-2 PM): 1.0x weight
            # Afternoon (2-3 PM): 0.9x weight
            # Last hour (3-4 PM): 0.8x weight
            
            if current_time_decimal < 11.0:  # Before 11 AM
                return 1.2
            elif current_time_decimal < 14.0:  # Before 2 PM
                return 1.0
            elif current_time_decimal < 15.0:  # Before 3 PM
                return 0.9
            else:  # Last hour
                return 0.8
                
        except Exception as e:
            logger.error(f"Error calculating time decay: {e}")
            return 1.0
    
    def _get_volatility_factor(self, flow_data: Dict) -> float:
        """
        Adjust confidence based on market volatility
        High volatility = Lower confidence (unpredictable)
        Low volatility = Higher confidence (trends hold)
        """
        try:
            # Try to get VIX from flow data or calculate from price movement
            # For now, use a simple heuristic based on recent price movement
            
            symbol = flow_data.get('symbol', 'SPY')
            recent_flow = order_flow_history.get_recent_flow(symbol, count=10)
            
            if len(recent_flow) < 5:
                return 1.0  # Default if not enough data
            
            # Calculate price volatility from recent snapshots
            prices = [f.get('stock_price', 0) for f in recent_flow if f.get('stock_price', 0) > 0]
            
            if len(prices) < 5:
                return 1.0
            
            # Calculate price range
            price_range = max(prices) - min(prices)
            avg_price = sum(prices) / len(prices)
            
            if avg_price == 0:
                return 1.0
            
            volatility_pct = (price_range / avg_price) * 100
            
            # Adjust factor based on volatility
            # Low volatility (<1%): 1.1x (higher confidence)
            # Normal volatility (1-2%): 1.0x
            # High volatility (2-3%): 0.9x
            # Very high volatility (>3%): 0.8x (lower confidence)
            
            if volatility_pct < 1.0:
                return 1.1
            elif volatility_pct < 2.0:
                return 1.0
            elif volatility_pct < 3.0:
                return 0.9
            else:
                return 0.8
                
        except Exception as e:
            logger.error(f"Error calculating volatility factor: {e}")
            return 1.0
    
    def _enhanced_strike_analysis(self, flow_data: Dict) -> Dict:
        """
        Enhanced strike concentration analysis
        Identifies institutional activity patterns
        """
        try:
            stock_price = flow_data.get('stock_price', 0)
            if stock_price == 0:
                return {}
            
            calls_by_strike = flow_data.get('strikes', {}).get('calls_by_strike', [])
            puts_by_strike = flow_data.get('strikes', {}).get('puts_by_strike', [])
            
            # Analyze call strikes
            call_strikes = {}
            for call in calls_by_strike:
                strike = call.get('strike', 0)
                volume = call.get('volume', 0)
                if volume > 0:
                    if strike not in call_strikes:
                        call_strikes[strike] = 0
                    call_strikes[strike] += volume
            
            # Analyze put strikes
            put_strikes = {}
            for put in puts_by_strike:
                strike = put.get('strike', 0)
                volume = put.get('volume', 0)
                if volume > 0:
                    if strike not in put_strikes:
                        put_strikes[strike] = 0
                    put_strikes[strike] += volume
            
            # Find dominant strikes (highest volume)
            call_total = sum(call_strikes.values())
            put_total = sum(put_strikes.values())
            
            if call_total > 0:
                call_dominant_strike = max(call_strikes.items(), key=lambda x: x[1])
                call_dominant_pct = (call_dominant_strike[1] / call_total) * 100
            else:
                call_dominant_strike = (0, 0)
                call_dominant_pct = 0
            
            if put_total > 0:
                put_dominant_strike = max(put_strikes.items(), key=lambda x: x[1])
                put_dominant_pct = (put_dominant_strike[1] / put_total) * 100
            else:
                put_dominant_strike = (0, 0)
                put_dominant_pct = 0
            
            # Determine if institutional (high concentration on single strike)
            institutional_calls = call_dominant_pct > 30
            institutional_puts = put_dominant_pct > 30
            
            return {
                'call_dominant_strike': call_dominant_strike[0],
                'call_dominant_volume': call_dominant_strike[1],
                'call_dominant_pct': round(call_dominant_pct, 1),
                'put_dominant_strike': put_dominant_strike[0],
                'put_dominant_volume': put_dominant_strike[1],
                'put_dominant_pct': round(put_dominant_pct, 1),
                'institutional_calls': institutional_calls,
                'institutional_puts': institutional_puts,
                'institutional_activity': institutional_calls or institutional_puts
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced strike analysis: {e}")
            return {}

