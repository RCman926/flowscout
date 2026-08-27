"""
Order Flow History Tracker
Tracks options buy/sell activity over time for order flow visualization
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import deque
import time
import logging

logger = logging.getLogger(__name__)


class OrderFlowHistory:
    """
    Tracks order flow history for visualization
    Stores flow data points with timestamps for charting
    """
    
    def __init__(self, max_history: int = 100):
        """
        Initialize order flow history tracker
        
        Args:
            max_history: Maximum number of data points to keep (default: 100)
        """
        self.max_history = max_history
        self.flow_history: Dict[str, deque] = {}  # symbol -> deque of flow snapshots
    
    def add_flow_snapshot(self, symbol: str, flow_data: Dict) -> None:
        """
        Add a flow snapshot to history
        
        Args:
            symbol: Stock symbol
            flow_data: Flow data dictionary from zerodte_flow_tracker
        """
        try:
            if symbol not in self.flow_history:
                self.flow_history[symbol] = deque(maxlen=self.max_history)
            
            metrics = flow_data.get('flow_metrics', {})
            stock_price = flow_data.get('stock_price', 0)
            
            snapshot = {
                'timestamp': datetime.now().isoformat(),
                'timestamp_ms': int(time.time() * 1000),
                'stock_price': stock_price,
                'call_volume': metrics.get('total_call_volume', 0),
                'put_volume': metrics.get('total_put_volume', 0),
                'net_flow': metrics.get('net_volume_flow', 0),
                'cp_ratio': metrics.get('call_put_ratio', 1.0),
                'call_premium_flow': metrics.get('call_premium_flow', 0),
                'put_premium_flow': metrics.get('put_premium_flow', 0),
                'net_premium_flow': metrics.get('net_premium_flow', 0),
                'expiration': flow_data.get('expiration'),
                'dte': flow_data.get('dte', 0),
                'session': flow_data.get('session', 'UNKNOWN')
            }
            
            self.flow_history[symbol].append(snapshot)
            
        except Exception as e:
            logger.error(f"Error adding flow snapshot for {symbol}: {e}")
    
    def get_flow_history(self, symbol: str, minutes: int = 60) -> List[Dict]:
        """
        Get flow history for a symbol within specified time window
        
        Args:
            symbol: Stock symbol
            minutes: Number of minutes of history to return (default: 60)
            
        Returns:
            List of flow snapshots within time window
        """
        if symbol not in self.flow_history:
            return []
        
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        cutoff_iso = cutoff_time.isoformat()
        
        # Filter snapshots within time window
        history = list(self.flow_history[symbol])
        filtered = [s for s in history if s['timestamp'] >= cutoff_iso]
        
        return filtered
    
    def get_recent_flow(self, symbol: str, count: int = 20) -> List[Dict]:
        """
        Get most recent N flow snapshots
        
        Args:
            symbol: Stock symbol
            count: Number of recent snapshots to return
            
        Returns:
            List of most recent flow snapshots
        """
        if symbol not in self.flow_history:
            return []
        
        return list(self.flow_history[symbol])[-count:]
    
    def get_flow_summary(self, symbol: str) -> Dict:
        """
        Get summary statistics for flow history
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with summary statistics
        """
        if symbol not in self.flow_history or len(self.flow_history[symbol]) == 0:
            return {
                'total_snapshots': 0,
                'time_span_minutes': 0,
                'avg_call_volume': 0,
                'avg_put_volume': 0,
                'avg_net_flow': 0,
                'trend': 'N/A'
            }
        
        history = list(self.flow_history[symbol])
        
        if len(history) < 2:
            return {
                'total_snapshots': len(history),
                'time_span_minutes': 0,
                'avg_call_volume': history[0]['call_volume'] if history else 0,
                'avg_put_volume': history[0]['put_volume'] if history else 0,
                'avg_net_flow': history[0]['net_flow'] if history else 0,
                'trend': 'N/A'
            }
        
        # Calculate time span
        first_time = datetime.fromisoformat(history[0]['timestamp'])
        last_time = datetime.fromisoformat(history[-1]['timestamp'])
        time_span = (last_time - first_time).total_seconds() / 60
        
        # Calculate averages
        avg_call_volume = sum(s['call_volume'] for s in history) / len(history)
        avg_put_volume = sum(s['put_volume'] for s in history) / len(history)
        avg_net_flow = sum(s['net_flow'] for s in history) / len(history)
        
        # Determine trend (comparing first half to second half)
        mid_point = len(history) // 2
        first_half_avg = sum(s['net_flow'] for s in history[:mid_point]) / mid_point
        second_half_avg = sum(s['net_flow'] for s in history[mid_point:]) / (len(history) - mid_point)
        
        if second_half_avg > first_half_avg * 1.1:
            trend = 'INCREASING_CALLS'
        elif second_half_avg < first_half_avg * 0.9:
            trend = 'INCREASING_PUTS'
        else:
            trend = 'STABLE'
        
        return {
            'total_snapshots': len(history),
            'time_span_minutes': round(time_span, 1),
            'avg_call_volume': round(avg_call_volume, 0),
            'avg_put_volume': round(avg_put_volume, 0),
            'avg_net_flow': round(avg_net_flow, 0),
            'trend': trend
        }


# Global instance
order_flow_history = OrderFlowHistory(max_history=200)

