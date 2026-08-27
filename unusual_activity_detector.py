"""
Unusual Activity Detector - Catch Big Moves Early
Detects abnormal options flow that often precedes significant price movements
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import deque
import logging

logger = logging.getLogger(__name__)


class UnusualActivityDetector:
    """
    Detects unusual options activity patterns:
    - Volume spikes (>3x average)
    - Premium flow spikes (>$5M)
    - Single strike concentration (>30% of volume)
    - Unusual call/put ratios
    """
    
    def __init__(self, lookback_days: int = 20):
        self.lookback_days = lookback_days
        self.historical_volume = {}  # symbol -> deque of volumes
        self.historical_call_premium = {}  # symbol -> deque of call premium flows
        self.historical_put_premium = {}  # symbol -> deque of put premium flows
        self.alert_history = []  # Recent alerts
        
    def detect_unusual_activity(self, flow_data: Dict) -> Dict:
        """
        Detect unusual activity in current flow data
        
        Returns:
            Dict with unusual activity flags and alerts
        """
        symbol = flow_data.get('symbol', 'SPY')
        metrics = flow_data.get('flow_metrics', {})
        
        total_volume = metrics.get('total_call_volume', 0) + metrics.get('total_put_volume', 0)
        call_premium_flow = metrics.get('call_premium_flow', 0)
        put_premium_flow = metrics.get('put_premium_flow', 0)
        
        # Update historical data
        if symbol not in self.historical_volume:
            self.historical_volume[symbol] = deque(maxlen=self.lookback_days * 20)  # ~20 data points per day
        
        if symbol not in self.historical_call_premium:
            self.historical_call_premium[symbol] = deque(maxlen=self.lookback_days * 20)
        
        if symbol not in self.historical_put_premium:
            self.historical_put_premium[symbol] = deque(maxlen=self.lookback_days * 20)
        
        self.historical_volume[symbol].append(total_volume)
        self.historical_call_premium[symbol].append(call_premium_flow)
        self.historical_put_premium[symbol].append(put_premium_flow)
        
        alerts = []
        flags = {}
        
        # 1. Volume Spike Detection
        if len(self.historical_volume[symbol]) >= 10:
            avg_volume = sum(list(self.historical_volume[symbol])[-20:]) / min(20, len(self.historical_volume[symbol]))
            volume_ratio = total_volume / max(1, avg_volume)
            
            if volume_ratio >= 3.0:
                flags['volume_spike'] = True
                flags['volume_ratio'] = round(volume_ratio, 2)
                alerts.append({
                    'type': 'VOLUME_SPIKE',
                    'severity': 'HIGH' if volume_ratio >= 5.0 else 'MEDIUM',
                    'message': f"Volume spike detected: {volume_ratio:.1f}x average ({total_volume:,} vs {avg_volume:,.0f} avg)",
                    'timestamp': datetime.now().isoformat()
                })
            else:
                flags['volume_spike'] = False
                flags['volume_ratio'] = round(volume_ratio, 2)
        
        # 2. Premium Flow Spike Detection - Track CALL and PUT separately
        # Always calculate ratios if we have historical data, but only alert on spikes
        call_premium_ratio = 0
        put_premium_ratio = 0
        
        # Check CALL premium flow spike (need at least 3 data points to start detecting)
        if len(self.historical_call_premium[symbol]) >= 3:
            avg_call_premium = sum(list(self.historical_call_premium[symbol])[-20:]) / min(20, len(self.historical_call_premium[symbol]))
            call_premium_ratio = call_premium_flow / max(1, avg_call_premium)
            flags['call_premium_ratio'] = round(call_premium_ratio, 2)
            
            # Only trigger if actually a spike (>= 2.0x average) or very large absolute value
            if call_premium_flow > 5000000 and call_premium_ratio >= 2.0:  # >$5M AND 2x average (both conditions)
                flags['call_premium_spike'] = True
                alerts.append({
                    'type': 'CALL_PREMIUM_SPIKE',
                    'severity': 'HIGH' if call_premium_flow > 10000000 or call_premium_ratio >= 3.0 else 'MEDIUM',
                    'message': f"CALL premium flow spike: ${call_premium_flow/1000000:.2f}M ({call_premium_ratio:.1f}x average)",
                    'timestamp': datetime.now().isoformat()
                })
            else:
                flags['call_premium_spike'] = False
        else:
            flags['call_premium_spike'] = False
            flags['call_premium_ratio'] = 0
        
        # Check PUT premium flow spike (need at least 3 data points to start detecting)
        if len(self.historical_put_premium[symbol]) >= 3:
            avg_put_premium = sum(list(self.historical_put_premium[symbol])[-20:]) / min(20, len(self.historical_put_premium[symbol]))
            put_premium_ratio = put_premium_flow / max(1, avg_put_premium)
            flags['put_premium_ratio'] = round(put_premium_ratio, 2)
            
            # Only trigger if actually a spike (>= 2.0x average) or very large absolute value
            if put_premium_flow > 5000000 and put_premium_ratio >= 2.0:  # >$5M AND 2x average (both conditions)
                flags['put_premium_spike'] = True
                alerts.append({
                    'type': 'PUT_PREMIUM_SPIKE',
                    'severity': 'HIGH' if put_premium_flow > 10000000 or put_premium_ratio >= 3.0 else 'MEDIUM',
                    'message': f"PUT premium flow spike: ${put_premium_flow/1000000:.2f}M ({put_premium_ratio:.1f}x average)",
                    'timestamp': datetime.now().isoformat()
                })
            else:
                flags['put_premium_spike'] = False
        else:
            flags['put_premium_spike'] = False
            flags['put_premium_ratio'] = 0
        
        # Add flags for current premium flows (always available, even if not a spike)
        flags['call_premium_flow'] = call_premium_flow
        flags['put_premium_flow'] = put_premium_flow
        
        # 3. Single Strike Concentration
        strikes = flow_data.get('strikes', {})
        calls_by_strike = strikes.get('calls_by_strike', [])
        puts_by_strike = strikes.get('puts_by_strike', [])
        
        if calls_by_strike:
            call_volumes = [c.get('volume', 0) for c in calls_by_strike]
            total_call_vol = sum(call_volumes)
            if total_call_vol > 0:
                max_call_strike_vol = max(call_volumes)
                call_concentration = (max_call_strike_vol / total_call_vol) * 100
                
                if call_concentration > 30:
                    flags['call_strike_concentration'] = True
                    flags['call_concentration_pct'] = round(call_concentration, 1)
                    max_strike = calls_by_strike[call_volumes.index(max_call_strike_vol)].get('strike', 0)
                    alerts.append({
                        'type': 'STRIKE_CONCENTRATION',
                        'severity': 'MEDIUM',
                        'message': f"Call concentration: {call_concentration:.1f}% at strike ${max_strike:.2f}",
                        'timestamp': datetime.now().isoformat()
                    })
        
        if puts_by_strike:
            put_volumes = [p.get('volume', 0) for p in puts_by_strike]
            total_put_vol = sum(put_volumes)
            if total_put_vol > 0:
                max_put_strike_vol = max(put_volumes)
                put_concentration = (max_put_strike_vol / total_put_vol) * 100
                
                if put_concentration > 30:
                    flags['put_strike_concentration'] = True
                    flags['put_concentration_pct'] = round(put_concentration, 1)
                    max_strike = puts_by_strike[put_volumes.index(max_put_strike_vol)].get('strike', 0)
                    alerts.append({
                        'type': 'STRIKE_CONCENTRATION',
                        'severity': 'MEDIUM',
                        'message': f"Put concentration: {put_concentration:.1f}% at strike ${max_strike:.2f}",
                        'timestamp': datetime.now().isoformat()
                    })
        
        # 4. Unusual Call/Put Ratio
        cp_ratio = metrics.get('call_put_ratio', 1.0)
        if cp_ratio > 2.5:  # Very bullish
            flags['extreme_call_ratio'] = True
            alerts.append({
                'type': 'EXTREME_RATIO',
                'severity': 'MEDIUM',
                'message': f"Extreme call/put ratio: {cp_ratio:.2f} (very bullish)",
                'timestamp': datetime.now().isoformat()
            })
        elif cp_ratio < 0.4:  # Very bearish
            flags['extreme_put_ratio'] = True
            alerts.append({
                'type': 'EXTREME_RATIO',
                'severity': 'MEDIUM',
                'message': f"Extreme call/put ratio: {cp_ratio:.2f} (very bearish)",
                'timestamp': datetime.now().isoformat()
            })
        
        # Store alerts
        if alerts:
            self.alert_history.extend(alerts)
            # Keep last 50 alerts
            if len(self.alert_history) > 50:
                self.alert_history = self.alert_history[-50:]
        
        # Determine overall unusual activity level
        high_severity_count = sum(1 for a in alerts if a.get('severity') == 'HIGH')
        medium_severity_count = sum(1 for a in alerts if a.get('severity') == 'MEDIUM')
        
        if high_severity_count > 0:
            activity_level = 'HIGH'
        elif medium_severity_count >= 2:
            activity_level = 'MEDIUM'
        elif medium_severity_count > 0:
            activity_level = 'LOW'
        else:
            activity_level = 'NORMAL'
        
        return {
            'unusual_activity': activity_level != 'NORMAL',
            'activity_level': activity_level,
            'alerts': alerts,
            'flags': flags,
            'alert_count': len(alerts),
            'high_severity_count': high_severity_count,
            'medium_severity_count': medium_severity_count
        }


# Global instance
unusual_activity_detector = UnusualActivityDetector()

