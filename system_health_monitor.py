"""
System Health Monitoring
Comprehensive health checks with metrics for proactive issue detection
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import deque
import time

logger = logging.getLogger(__name__)


class SystemHealthMonitor:
    """
    Monitors system health metrics and provides health status
    """
    
    def __init__(self):
        self.metrics = {
            'websocket_connections': 0,
            'data_fetch_success_rate': 0.0,
            'avg_response_time': 0.0,
            'error_rate': 0.0,
            'last_successful_fetch': None,
            'consecutive_failures': 0,
            'total_fetches': 0,
            'successful_fetches': 0,
            'failed_fetches': 0
        }
        self.health_history = deque(maxlen=1000)
        self.response_times = deque(maxlen=100)
        self.error_history = deque(maxlen=100)
        self.last_update = datetime.now()
    
    def record_fetch(self, success: bool, response_time: float, error: Optional[str] = None):
        """
        Record a data fetch attempt
        
        Args:
            success: Whether fetch was successful
            response_time: Response time in seconds
            error: Error message if failed
        """
        self.metrics['total_fetches'] += 1
        self.response_times.append(response_time)
        
        if success:
            self.metrics['successful_fetches'] += 1
            self.metrics['consecutive_failures'] = 0
            self.metrics['last_successful_fetch'] = datetime.now().isoformat()
        else:
            self.metrics['failed_fetches'] += 1
            self.metrics['consecutive_failures'] += 1
            if error:
                self.error_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'error': error
                })
        
        # Update rolling averages
        self._update_metrics()
    
    def _update_metrics(self):
        """Update rolling average metrics"""
        # Success rate
        if self.metrics['total_fetches'] > 0:
            self.metrics['data_fetch_success_rate'] = (
                self.metrics['successful_fetches'] / self.metrics['total_fetches'] * 100
            )
        
        # Average response time
        if self.response_times:
            self.metrics['avg_response_time'] = sum(self.response_times) / len(self.response_times)
        
        # Error rate
        if self.metrics['total_fetches'] > 0:
            self.metrics['error_rate'] = (
                self.metrics['failed_fetches'] / self.metrics['total_fetches'] * 100
            )
        
        # Record health snapshot
        self.health_history.append({
            'timestamp': datetime.now().isoformat(),
            'metrics': self.metrics.copy()
        })
    
    def update_websocket_connections(self, count: int):
        """Update WebSocket connection count"""
        self.metrics['websocket_connections'] = count
    
    def get_health_status(self) -> Dict:
        """
        Get current health status
        
        Returns:
            Dictionary with health status, metrics, and recommendations
        """
        try:
            from market_hours_detector import session_clock

            clock = session_clock()
            if clock.get("closed"):
                return {
                    "status": "CLOSED",
                    "timestamp": datetime.now().isoformat(),
                    "metrics": self.metrics.copy(),
                    "issues": [],
                    "recommendations": [
                        f"{clock.get('label')} — fetch gaps and cooling APIs are expected. Site is not down."
                    ],
                    "clock": clock,
                }
        except Exception:
            pass

        # Determine overall health status
        status = 'HEALTHY'
        issues = []
        
        # Check consecutive failures
        if self.metrics['consecutive_failures'] >= 5:
            status = 'DEGRADED'
            issues.append(f"High consecutive failures: {self.metrics['consecutive_failures']}")
        elif self.metrics['consecutive_failures'] >= 10:
            status = 'UNHEALTHY'
            issues.append(f"Critical consecutive failures: {self.metrics['consecutive_failures']}")
        
        # Check success rate
        if self.metrics['data_fetch_success_rate'] < 50:
            status = 'UNHEALTHY'
            issues.append(f"Low success rate: {self.metrics['data_fetch_success_rate']:.1f}%")
        elif self.metrics['data_fetch_success_rate'] < 80:
            status = 'DEGRADED'
            issues.append(f"Moderate success rate: {self.metrics['data_fetch_success_rate']:.1f}%")
        
        # Check response time
        if self.metrics['avg_response_time'] > 10:
            status = 'DEGRADED' if status == 'HEALTHY' else status
            issues.append(f"High response time: {self.metrics['avg_response_time']:.2f}s")
        
        # Check error rate
        if self.metrics['error_rate'] > 50:
            status = 'UNHEALTHY'
            issues.append(f"High error rate: {self.metrics['error_rate']:.1f}%")
        elif self.metrics['error_rate'] > 20:
            status = 'DEGRADED' if status == 'HEALTHY' else status
            issues.append(f"Moderate error rate: {self.metrics['error_rate']:.1f}%")
        
        # Check last successful fetch
        if self.metrics['last_successful_fetch']:
            try:
                last_success = datetime.fromisoformat(self.metrics['last_successful_fetch'])
                time_since_success = (datetime.now() - last_success).total_seconds()
                if time_since_success > 300:  # 5 minutes
                    status = 'DEGRADED' if status == 'HEALTHY' else status
                    issues.append(f"No successful fetch in {int(time_since_success)}s")
            except Exception:
                pass
        
        return {
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'metrics': self.metrics.copy(),
            'issues': issues,
            'recommendations': self._generate_recommendations(status, issues)
        }
    
    def _generate_recommendations(self, status: str, issues: List[str]) -> List[str]:
        """Generate recommendations based on health status"""
        recommendations = []
        
        if status == 'UNHEALTHY':
            recommendations.append("⚠️ CRITICAL: System is unhealthy - immediate attention required")
            recommendations.append("Check data source connections and API keys")
            recommendations.append("Review error logs for root cause")
        
        if self.metrics['consecutive_failures'] >= 5:
            recommendations.append("Consider switching to backup data sources")
            recommendations.append("Check network connectivity")
        
        if self.metrics['data_fetch_success_rate'] < 80:
            recommendations.append("Review API rate limits and quotas")
            recommendations.append("Check data source availability")
        
        if self.metrics['avg_response_time'] > 5:
            recommendations.append("Optimize data fetching logic")
            recommendations.append("Consider caching to reduce API calls")
        
        if not recommendations:
            recommendations.append("✅ System is operating normally")
        
        return recommendations
    
    def get_health_history(self, limit: int = 100) -> List[Dict]:
        """Get recent health history"""
        return list(self.health_history)[-limit:]
    
    def get_error_summary(self) -> Dict:
        """Get summary of recent errors"""
        recent_errors = list(self.error_history)[-20:]
        error_counts = {}
        
        for error_entry in recent_errors:
            error_msg = error_entry.get('error', 'Unknown')
            # Extract error type (first part of error message)
            error_type = error_msg.split(':')[0] if ':' in error_msg else error_msg[:50]
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        return {
            'total_recent_errors': len(recent_errors),
            'error_types': error_counts,
            'recent_errors': recent_errors
        }


# Global instance
system_health_monitor = SystemHealthMonitor()

