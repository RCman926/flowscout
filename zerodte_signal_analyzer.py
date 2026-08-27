"""
0DTE Options Flow Signal Analyzer
Analyzes 0DTE options flow to determine CALL vs PUT recommendations
Uses institutional-grade signal analysis with ML learning from wins/losses
"""

from typing import Dict, Optional, List
from datetime import datetime, timedelta
import logging
import json
import os

logger = logging.getLogger(__name__)


class ZeroDTESignalAnalyzer:
    """
    Analyzes 0DTE options flow to generate CALL/PUT trading signals
    Uses multiple factors: flow ratio, volume intensity, premium flow, momentum
    Includes ML learning from wins/losses to improve over time
    """
    
    def __init__(self, load_history_immediately: bool = False):
        # Signal performance tracking
        self.signal_history_file = "zerodte_signal_history.json"
        self.signal_history = []
        self.performance_stats = {
            'total_signals': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0,
            'call_win_rate': 0.0,
            'put_win_rate': 0.0,
            'avg_confidence_wins': 0.0,
            'avg_confidence_losses': 0.0
        }
        
        # OPTIMIZED: Load history lazily to avoid blocking startup
        # History will be loaded on first use or in background
        self._history_loaded = False
        if load_history_immediately:
            self.load_signal_history()
        else:
            # Load in background thread to avoid blocking
            import threading
            def load_async():
                try:
                    self.load_signal_history()
                    self._history_loaded = True
                except Exception as e:
                    logger.debug(f"Background signal history load: {e}")
            threading.Thread(target=load_async, daemon=True).start()
        # Signal thresholds (institutional-grade)
        # FIXED: Lowered thresholds to catch bullish days better
        self.flow_thresholds = {
            'strong_calls': {
                'cp_ratio_min': 1.3,           # Call/Put ratio > 1.3 (was 1.5)
                'net_flow_min': 30000,          # Net flow > 30K (was 50K)
                'premium_flow_min': 500000,    # Premium flow > $500K (was $1M)
                'confidence': 85
            },
            'calls': {
                'cp_ratio_min': 1.1,           # Call/Put ratio > 1.1 (was 1.2)
                'net_flow_min': 10000,          # Net flow > 10K (was 20K)
                'premium_flow_min': 200000,     # Premium flow > $200K (was $500K)
                'confidence': 70
            },
            'neutral': {
                'cp_ratio_min': 0.9,           # Between 0.9 and 1.1
                'cp_ratio_max': 1.1,
                'confidence': 50
            },
            'puts': {
                'cp_ratio_max': 0.8,           # Call/Put ratio < 0.8
                'net_flow_max': -20000,        # Net flow < -20K
                'premium_flow_max': -500000,    # Premium flow < -$500K
                'confidence': 70
            },
            'strong_puts': {
                'cp_ratio_max': 0.5,           # Call/Put ratio < 0.5
                'net_flow_max': -50000,        # Net flow < -50K
                'premium_flow_max': -1000000,  # Premium flow < -$1M
                'confidence': 85
            }
        }
    
    def analyze_flow_signal(self, flow_data: Dict, historical_flow: List[Dict] = None) -> Dict:
        """
        Analyze 0DTE options flow and generate trading signal
        
        Args:
            flow_data: Dictionary from zerodte_flow_tracker with flow metrics
            
        Returns:
            Dict with signal, confidence, reasoning, and recommendations
        """
        try:
            metrics = flow_data.get('flow_metrics', {})
            stock_price = flow_data.get('stock_price', 0)
            
            if stock_price == 0:
                return self._no_signal("No stock price data available")
            
            # Extract key metrics
            call_volume = metrics.get('total_call_volume', 0)
            put_volume = metrics.get('total_put_volume', 0)
            net_volume_flow = metrics.get('net_volume_flow', 0)
            cp_ratio = metrics.get('call_put_ratio', 1.0)
            call_premium = metrics.get('call_premium_flow', 0)
            put_premium = metrics.get('put_premium_flow', 0)
            net_premium_flow = metrics.get('net_premium_flow', 0)
            total_volume = call_volume + put_volume
            
            # Check if we have enough data
            if total_volume < 10000:
                return self._no_signal(f"Insufficient volume ({total_volume:,}). Need at least 10K total volume.")
            
            # CRITICAL FIX: Check price momentum first - if market is flying, boost CALL signals
            price_momentum = self._check_price_momentum(flow_data, historical_flow)
            
            # Analyze signal strength
            signal_analysis = self._determine_signal_strength(
                cp_ratio, net_volume_flow, net_premium_flow, total_volume, price_momentum
            )
            
            # Get strike analysis
            strike_analysis = self._analyze_strike_distribution(flow_data)
            
            # Calculate final confidence
            confidence = self._calculate_confidence(
                signal_analysis, strike_analysis, total_volume, price_momentum
            )
            
            # Generate recommendation
            recommendation = self._generate_recommendation(
                signal_analysis, confidence, stock_price, flow_data
            )
            
            # ML Learning: Adjust confidence based on historical win rates
            action = recommendation['action']
            if action != 'NO_TRADE':
                ml_adjusted_confidence = self.adjust_confidence_based_on_history(confidence, action)
                if ml_adjusted_confidence != confidence:
                    confidence = ml_adjusted_confidence
                    recommendation['confidence'] = confidence
                    recommendation['ml_adjusted'] = True
                    recommendation['historical_win_rate'] = (
                        self.performance_stats.get('call_win_rate', 0) if 'CALL' in action
                        else self.performance_stats.get('put_win_rate', 0) if 'PUT' in action
                        else 0
                    )
            
            return {
                'signal': signal_analysis['signal'],
                'confidence': confidence,
                'recommendation': recommendation,
                'action': recommendation['action'],
                'reasoning': recommendation['reasoning'],
                'metrics': {
                    'call_volume': call_volume,
                    'put_volume': put_volume,
                    'net_flow': net_volume_flow,
                    'cp_ratio': round(cp_ratio, 2),
                    'net_premium_flow': net_premium_flow,
                    'total_volume': total_volume
                },
                'strike_analysis': strike_analysis,
                'timestamp': datetime.now().isoformat(),
                'expiration': flow_data.get('expiration'),
                'expiration_label': flow_data.get('expiration_label', 'N/A'),
                'ml_learning': {
                    'enabled': True,
                    'total_signals': self.performance_stats['total_signals'],
                    'win_rate': round(self.performance_stats['win_rate'], 1),
                    'call_win_rate': round(self.performance_stats.get('call_win_rate', 0), 1),
                    'put_win_rate': round(self.performance_stats.get('put_win_rate', 0), 1)
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing flow signal: {e}")
            return self._no_signal(f"Analysis error: {str(e)}")
    
    def _check_price_momentum(self, flow_data: Dict, historical_flow: List[Dict] = None) -> Dict:
        """Check if stock price is rising/falling significantly (market direction)"""
        try:
            stock_price = flow_data.get('stock_price', 0)
            if stock_price == 0:
                return {'momentum': 0, 'direction': 'NEUTRAL', 'strength': 0}
            
            # Try to get price change from flow_data first
            price_change_pct = flow_data.get('price_change_pct', 0)
            price_change = flow_data.get('price_change', 0)
            
            # If no explicit change, calculate from historical flow data
            if price_change_pct == 0 and price_change == 0:
                # Use historical flow to calculate momentum
                if historical_flow and len(historical_flow) >= 2:
                    # Get last 5 prices to calculate momentum
                    recent_prices = []
                    for hf in historical_flow[-5:]:
                        price = hf.get('stock_price', 0)
                        if price > 0:
                            recent_prices.append(price)
                    
                    if len(recent_prices) >= 2:
                        # Calculate % change from oldest to newest
                        oldest_price = recent_prices[0]
                        newest_price = recent_prices[-1]
                        price_change_pct = ((newest_price - oldest_price) / oldest_price) * 100
                    elif len(recent_prices) == 1:
                        # Only one historical price
                        prev_price = recent_prices[0]
                        price_change_pct = ((stock_price - prev_price) / prev_price) * 100
                else:
                    # Check if there's a previous price in the current flow_data
                    prev_price = flow_data.get('previous_price', 0)
                    if prev_price > 0:
                        price_change_pct = ((stock_price - prev_price) / prev_price) * 100
                    else:
                        # No momentum data available
                        return {'momentum': 0, 'direction': 'NEUTRAL', 'strength': 0}
            
            # Determine momentum strength
            if price_change_pct > 1.0:  # Up more than 1%
                return {
                    'momentum': price_change_pct,
                    'direction': 'BULLISH',
                    'strength': 'STRONG' if price_change_pct > 2.0 else 'MODERATE'
                }
            elif price_change_pct < -1.0:  # Down more than 1%
                return {
                    'momentum': price_change_pct,
                    'direction': 'BEARISH',
                    'strength': 'STRONG' if price_change_pct < -2.0 else 'MODERATE'
                }
            else:
                return {'momentum': price_change_pct, 'direction': 'NEUTRAL', 'strength': 0}
        except Exception as e:
            logger.debug(f"Error checking price momentum: {e}")
            return {'momentum': 0, 'direction': 'NEUTRAL', 'strength': 0}
    
    def _determine_signal_strength(self, cp_ratio: float, net_flow: int, 
                                   net_premium: float, total_volume: int, 
                                   price_momentum: Dict = None) -> Dict:
        """Determine signal strength based on flow metrics"""
        # CRITICAL FIX: Price momentum can override flow thresholds
        # If market is flying up (>1% gain), generate CALL signals even with weaker flow
        if price_momentum and price_momentum.get('direction') == 'BULLISH':
            momentum_strength = price_momentum.get('strength', '')
            momentum_pct = price_momentum.get('momentum', 0)
            
            # Strong bullish momentum (>2% gain) = strong CALL signal regardless of flow
            if momentum_strength == 'STRONG' and momentum_pct > 2.0:
                return {
                    'signal': 'STRONG_CALLS',
                    'direction': 'BULLISH',
                    'strength': 'HIGH',
                    'score': 85,
                    'momentum_boost': True
                }
            # Moderate bullish momentum (>1% gain) = CALL signal with lower flow requirements
            elif momentum_pct > 1.0:
                # Lower thresholds when price is rising
                if cp_ratio >= 1.05 or net_flow >= 5000 or net_premium >= 100000:
                    return {
                        'signal': 'CALLS',
                        'direction': 'BULLISH',
                        'strength': 'MEDIUM',
                        'score': 70,
                        'momentum_boost': True
                    }
        
        # FIXED: Lowered thresholds and made them more flexible (OR instead of AND)
        
        # Strong Calls - any 2 of 3 conditions
        strong_call_conditions = [
            cp_ratio >= 1.3,
            net_flow >= 30000,
            net_premium >= 500000
        ]
        if sum(strong_call_conditions) >= 2:  # At least 2 conditions met
            return {
                'signal': 'STRONG_CALLS',
                'direction': 'BULLISH',
                'strength': 'HIGH',
                'score': 90
            }
        
        # Calls - any 2 of 3 conditions (lower thresholds)
        call_conditions = [
            cp_ratio >= 1.1,
            net_flow >= 10000,
            net_premium >= 200000
        ]
        if sum(call_conditions) >= 2:  # At least 2 conditions met
            return {
                'signal': 'CALLS',
                'direction': 'BULLISH',
                'strength': 'MEDIUM',
                'score': 75
            }
        
        # Weak Calls - any 1 of 3 conditions (catches bullish days with mixed flow)
        weak_call_conditions = [
            cp_ratio >= 1.05,  # Even slight call bias
            net_flow >= 5000,   # Small net call flow
            net_premium >= 100000  # Some call premium
        ]
        if sum(weak_call_conditions) >= 1 and cp_ratio > 1.0:  # At least 1 condition + call bias
            return {
                'signal': 'WEAK_CALLS',
                'direction': 'SLIGHTLY_BULLISH',
                'strength': 'LOW',
                'score': 65  # Increased from 60 to 65 for better confidence
            }
        
        # Strong Puts — mirror Strong Calls (any 2 of 3)
        strong_put_conditions = [
            cp_ratio <= 0.77,
            net_flow <= -30000,
            net_premium <= -500000
        ]
        if sum(strong_put_conditions) >= 2:
            return {
                'signal': 'STRONG_PUTS',
                'direction': 'BEARISH',
                'strength': 'HIGH',
                'score': 90
            }

        put_conditions = [
            cp_ratio <= 0.91,
            net_flow <= -10000,
            net_premium <= -200000
        ]
        if sum(put_conditions) >= 2:
            return {
                'signal': 'PUTS',
                'direction': 'BEARISH',
                'strength': 'MEDIUM',
                'score': 75
            }

        weak_put_conditions = [
            cp_ratio <= 0.95,
            net_flow <= -5000,
            net_premium <= -100000
        ]
        if sum(weak_put_conditions) >= 1 and cp_ratio < 1.0:
            return {
                'signal': 'WEAK_PUTS',
                'direction': 'SLIGHTLY_BEARISH',
                'strength': 'LOW',
                'score': 65
            }

        # Neutral band — do not default to calls
        return {
            'signal': 'NEUTRAL',
            'direction': 'UNCERTAIN',
            'strength': 'LOW',
            'score': 50
        }
    
    def _analyze_strike_distribution(self, flow_data: Dict) -> Dict:
        """Analyze where the volume is concentrated (ITM, ATM, OTM)"""
        try:
            stock_price = flow_data.get('stock_price', 0)
            if stock_price == 0:
                return {'analysis': 'No price data'}
            
            strikes = flow_data.get('strikes', {})
            calls = strikes.get('calls_by_strike', [])
            puts = strikes.get('puts_by_strike', [])
            
            # Analyze call strikes
            call_itm_volume = 0
            call_atm_volume = 0
            call_otm_volume = 0
            
            for call in calls:
                strike = call.get('strike', 0)
                volume = call.get('volume', 0)
                
                if strike < stock_price * 0.98:  # ITM
                    call_itm_volume += volume
                elif strike <= stock_price * 1.02:  # ATM
                    call_atm_volume += volume
                else:  # OTM
                    call_otm_volume += volume
            
            # Analyze put strikes
            put_itm_volume = 0
            put_atm_volume = 0
            put_otm_volume = 0
            
            for put in puts:
                strike = put.get('strike', 0)
                volume = put.get('volume', 0)
                
                if strike > stock_price * 1.02:  # ITM
                    put_itm_volume += volume
                elif strike >= stock_price * 0.98:  # ATM
                    put_atm_volume += volume
                else:  # OTM
                    put_otm_volume += volume
            
            # Determine concentration
            total_call_vol = call_itm_volume + call_atm_volume + call_otm_volume
            total_put_vol = put_itm_volume + put_atm_volume + put_otm_volume
            
            call_concentration = 'ATM' if call_atm_volume > max(call_itm_volume, call_otm_volume) else \
                               'ITM' if call_itm_volume > call_otm_volume else 'OTM'
            
            put_concentration = 'ATM' if put_atm_volume > max(put_itm_volume, put_otm_volume) else \
                               'ITM' if put_itm_volume > put_otm_volume else 'OTM'
            
            return {
                'call_concentration': call_concentration,
                'put_concentration': put_concentration,
                'call_atm_pct': (call_atm_volume / max(1, total_call_vol)) * 100,
                'put_atm_pct': (put_atm_volume / max(1, total_put_vol)) * 100,
                'analysis': f"Calls: {call_concentration}, Puts: {put_concentration}"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing strike distribution: {e}")
            return {'analysis': 'Error in strike analysis'}
    
    def _calculate_confidence(self, signal_analysis: Dict, strike_analysis: Dict, 
                             total_volume: int, price_momentum: Dict = None) -> int:
        """Calculate overall confidence score"""
        base_score = signal_analysis.get('score', 50)
        
        # Volume boost (more volume = more confidence)
        if total_volume > 500000:
            volume_boost = 15  # Increased from 10
        elif total_volume > 200000:
            volume_boost = 10  # Increased from 5
        elif total_volume > 100000:
            volume_boost = 5   # Added mid-tier boost
        else:
            volume_boost = 0
        
        # Strike concentration boost (ATM concentration = higher confidence)
        call_atm_pct = strike_analysis.get('call_atm_pct', 0)
        put_atm_pct = strike_analysis.get('put_atm_pct', 0)
        
        if signal_analysis['direction'] == 'BULLISH' and call_atm_pct > 40:
            concentration_boost = 5
        elif signal_analysis['direction'] == 'BEARISH' and put_atm_pct > 40:
            concentration_boost = 5
        else:
            concentration_boost = 0
        
        # CRITICAL FIX: Price momentum boost - if market is flying, boost confidence
        momentum_boost = 0
        if price_momentum and price_momentum.get('direction') == 'BULLISH':
            if signal_analysis['direction'] == 'BULLISH':
                momentum_pct = price_momentum.get('momentum', 0)
                if momentum_pct > 2.0:
                    momentum_boost = 15  # Strong momentum = big boost
                elif momentum_pct > 1.0:
                    momentum_boost = 10  # Moderate momentum = good boost
        elif price_momentum and price_momentum.get('direction') == 'BEARISH':
            if signal_analysis['direction'] == 'BEARISH':
                momentum_pct = abs(price_momentum.get('momentum', 0))
                if momentum_pct > 2.0:
                    momentum_boost = 15
                elif momentum_pct > 1.0:
                    momentum_boost = 10
        
        confidence = min(95, base_score + volume_boost + concentration_boost + momentum_boost)
        return confidence
    
    def _generate_recommendation(self, signal_analysis: Dict, confidence: int,
                                stock_price: float, flow_data: Dict) -> Dict:
        """Generate final trading recommendation"""
        
        signal = signal_analysis['signal']
        direction = signal_analysis['direction']
        strength = signal_analysis['strength']
        
        # Determine action
        # Weak flow is context only — Boss needs MEDIUM+ from this worker
        if signal in ['STRONG_CALLS', 'CALLS']:
            action = 'BUY_CALLS'
            reasoning = self._generate_call_reasoning(signal_analysis, confidence, flow_data)
        elif signal in ['STRONG_PUTS', 'PUTS']:
            action = 'BUY_PUTS'
            reasoning = self._generate_put_reasoning(signal_analysis, confidence, flow_data)
        else:
            action = 'NO_TRADE'
            reasoning = f"Neutral/weak flow ({signal}). Confidence: {confidence}%. Wait for clearer direction."
        
        return {
            'action': action,
            'reasoning': reasoning,
            'risk_level': 'HIGH' if strength == 'HIGH' else 'MEDIUM' if strength == 'MEDIUM' else 'LOW'
        }
    
    def _generate_call_reasoning(self, signal_analysis: Dict, confidence: int, 
                                flow_data: Dict) -> str:
        """Generate reasoning for call recommendation"""
        metrics = flow_data.get('flow_metrics', {})
        cp_ratio = metrics.get('call_put_ratio', 1.0)
        net_flow = metrics.get('net_volume_flow', 0)
        net_premium = metrics.get('net_premium_flow', 0)
        
        strength = signal_analysis['strength']
        
        reasons = []
        reasons.append(f"Strong call flow detected (C/P Ratio: {cp_ratio:.2f})")
        reasons.append(f"Net volume flow: +{net_flow:,} calls")
        
        if net_premium > 0:
            reasons.append(f"Premium flow: +${net_premium/1000000:.2f}M bullish")
        
        if strength == 'HIGH':
            reasons.append("HIGH CONVICTION - Institutional buying detected")
        else:
            reasons.append("MEDIUM CONVICTION - Good flow signal")
        
        reasons.append(f"Confidence: {confidence}%")
        
        return " | ".join(reasons)
    
    def _generate_put_reasoning(self, signal_analysis: Dict, confidence: int,
                               flow_data: Dict) -> str:
        """Generate reasoning for put recommendation"""
        metrics = flow_data.get('flow_metrics', {})
        cp_ratio = metrics.get('call_put_ratio', 1.0)
        net_flow = metrics.get('net_volume_flow', 0)
        net_premium = metrics.get('net_premium_flow', 0)
        
        strength = signal_analysis['strength']
        
        reasons = []
        reasons.append(f"Strong put flow detected (C/P Ratio: {cp_ratio:.2f})")
        reasons.append(f"Net volume flow: {net_flow:,} puts")
        
        if net_premium < 0:
            reasons.append(f"Premium flow: ${net_premium/1000000:.2f}M bearish")
        
        if strength == 'HIGH':
            reasons.append("HIGH CONVICTION - Institutional selling detected")
        else:
            reasons.append("MEDIUM CONVICTION - Good flow signal")
        
        reasons.append(f"Confidence: {confidence}%")
        
        return " | ".join(reasons)
    
    def _no_signal(self, reason: str) -> Dict:
        """Return no signal response"""
        return {
            'signal': 'NO_SIGNAL',
            'confidence': 0,
            'recommendation': {
                'action': 'NO_TRADE',
                'reasoning': reason,
                'risk_level': 'N/A'
            },
            'metrics': {},
            'timestamp': datetime.now().isoformat()
        }
    
    def record_signal(self, signal_data: Dict, symbol: str, expiration: str) -> str:
        """
        Record a signal for later win/loss tracking
        
        Args:
            signal_data: The signal analysis result
            symbol: Stock symbol
            expiration: Options expiration date
            
        Returns:
            signal_id: Unique ID for this signal
        """
        try:
            signal_id = f"{symbol}_{expiration}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            signal_record = {
                'signal_id': signal_id,
                'symbol': symbol,
                'expiration': expiration,
                'timestamp': datetime.now().isoformat(),
                'action': signal_data.get('action', 'NO_TRADE'),
                'confidence': signal_data.get('confidence', 0),
                'signal_type': signal_data.get('signal', 'N/A'),
                'metrics': signal_data.get('metrics', {}),
                'status': 'ACTIVE',  # ACTIVE, WIN, LOSS, EXPIRED
                'result': None,
                'actual_price_at_expiry': None,
                'profit_loss_pct': None
            }
            
            self.signal_history.append(signal_record)
            self.performance_stats['total_signals'] += 1
            self.save_signal_history()
            
            return signal_id
            
        except Exception as e:
            logger.error(f"Error recording signal: {e}")
            return ""
    
    def update_signal_result(self, signal_id: str, actual_price: float, starting_price: float, 
                            action: str) -> bool:
        """
        Update signal with actual result (win/loss)
        
        Args:
            signal_id: Signal ID to update
            actual_price: Price at expiration
            starting_price: Price when signal was given
            action: BUY_CALLS, BUY_PUTS, or NO_TRADE
            
        Returns:
            True if updated successfully
        """
        try:
            # Find signal
            signal = None
            for s in self.signal_history:
                if s['signal_id'] == signal_id:
                    signal = s
                    break
            
            if not signal:
                return False
            
            # Calculate win/loss
            price_change_pct = ((actual_price - starting_price) / starting_price) * 100
            
            if action == 'BUY_CALLS':
                # Call wins if price went up
                is_win = actual_price > starting_price
            elif action == 'BUY_PUTS':
                # Put wins if price went down
                is_win = actual_price < starting_price
            else:
                # NO_TRADE - neutral
                is_win = None
            
            # Update signal
            signal['status'] = 'EXPIRED'
            signal['result'] = 'WIN' if is_win else 'LOSS' if is_win is not None else 'NEUTRAL'
            signal['actual_price_at_expiry'] = actual_price
            signal['profit_loss_pct'] = price_change_pct
            
            # Update performance stats
            if is_win is True:
                self.performance_stats['wins'] += 1
                if action == 'BUY_CALLS':
                    self.performance_stats['call_win_rate'] = (
                        (self.performance_stats.get('call_wins', 0) + 1) / 
                        max(1, self.performance_stats.get('call_total', 0) + 1)
                    ) * 100
                elif action == 'BUY_PUTS':
                    self.performance_stats['put_win_rate'] = (
                        (self.performance_stats.get('put_wins', 0) + 1) / 
                        max(1, self.performance_stats.get('put_total', 0) + 1)
                    ) * 100
            elif is_win is False:
                self.performance_stats['losses'] += 1
            
            # Calculate overall win rate
            total_completed = self.performance_stats['wins'] + self.performance_stats['losses']
            if total_completed > 0:
                self.performance_stats['win_rate'] = (
                    self.performance_stats['wins'] / total_completed
                ) * 100
            
            # Update confidence averages
            if is_win is True:
                current_avg = self.performance_stats.get('avg_confidence_wins', 0)
                count = self.performance_stats.get('win_count', 0) + 1
                self.performance_stats['avg_confidence_wins'] = (
                    (current_avg * (count - 1) + signal['confidence']) / count
                )
            elif is_win is False:
                current_avg = self.performance_stats.get('avg_confidence_losses', 0)
                count = self.performance_stats.get('loss_count', 0) + 1
                self.performance_stats['avg_confidence_losses'] = (
                    (current_avg * (count - 1) + signal['confidence']) / count
                )
            
            self.save_signal_history()
            return True
            
        except Exception as e:
            logger.error(f"Error updating signal result: {e}")
            return False
    
    def get_performance_summary(self) -> Dict:
        """Get ML performance summary"""
        return {
            'total_signals': self.performance_stats['total_signals'],
            'completed_signals': self.performance_stats['wins'] + self.performance_stats['losses'],
            'wins': self.performance_stats['wins'],
            'losses': self.performance_stats['losses'],
            'win_rate': round(self.performance_stats['win_rate'], 1),
            'call_win_rate': round(self.performance_stats.get('call_win_rate', 0), 1),
            'put_win_rate': round(self.performance_stats.get('put_win_rate', 0), 1),
            'avg_confidence_wins': round(self.performance_stats.get('avg_confidence_wins', 0), 1),
            'avg_confidence_losses': round(self.performance_stats.get('avg_confidence_losses', 0), 1),
            'learning_enabled': True,
            'model_version': '1.0_ml'
        }
    
    def adjust_confidence_based_on_history(self, base_confidence: int, action: str) -> int:
        """
        Adjust confidence based on historical win rates
        
        Args:
            base_confidence: Base confidence from flow analysis
            action: BUY_CALLS, BUY_PUTS, or NO_TRADE
            
        Returns:
            Adjusted confidence (0-95)
        """
        try:
            # Get historical win rate for this action type
            if action == 'BUY_CALLS':
                historical_win_rate = self.performance_stats.get('call_win_rate', 50) / 100
            elif action == 'BUY_PUTS':
                historical_win_rate = self.performance_stats.get('put_win_rate', 50) / 100
            else:
                return base_confidence
            
            # Adjust confidence based on historical performance
            # If historical win rate is high, boost confidence
            # If historical win rate is low, reduce confidence
            adjustment_factor = historical_win_rate  # 0.0 to 1.0
            
            # Boost if win rate > 60%, reduce if < 40%
            if historical_win_rate > 0.6:
                adjusted = min(95, base_confidence + (historical_win_rate - 0.5) * 20)
            elif historical_win_rate < 0.4:
                adjusted = max(30, base_confidence - (0.5 - historical_win_rate) * 20)
            else:
                adjusted = base_confidence
            
            return int(adjusted)
            
        except Exception as e:
            logger.error(f"Error adjusting confidence: {e}")
            return base_confidence
    
    def load_signal_history(self):
        """Load signal history from file"""
        # OPTIMIZED: Skip if already loaded
        if self._history_loaded:
            return
        try:
            if os.path.exists(self.signal_history_file):
                with open(self.signal_history_file, 'r') as f:
                    data = json.load(f)
                    self.signal_history = data.get('history', [])
                    self.performance_stats = data.get('stats', self.performance_stats)
                    logger.debug(f"Loaded {len(self.signal_history)} signal records")  # Changed to debug
                    self._history_loaded = True
        except Exception as e:
            logger.debug(f"Error loading signal history: {e}")  # Changed to debug
            self.signal_history = []
            self._history_loaded = True  # Mark as loaded even on error to prevent retries
    
    def save_signal_history(self):
        """Save signal history to file"""
        try:
            data = {
                'history': self.signal_history[-1000:],  # Keep last 1000 signals
                'stats': self.performance_stats,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.signal_history_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving signal history: {e}")

