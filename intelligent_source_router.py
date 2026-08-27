"""
Intelligent Source Routing with Failover
Routes requests to best available source based on health and performance
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class IntelligentSourceRouter:
    """
    Intelligent routing system that selects best data source based on:
    - Health score
    - Latency
    - Success rate
    - Recent failures
    """
    
    def __init__(self):
        self.source_health: Dict[str, Dict] = defaultdict(lambda: {
            'health_score': 100.0,
            'latency': 0.0,
            'success_rate': 100.0,
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'consecutive_failures': 0,
            'last_success': None,
            'last_failure': None,
            'avg_response_time': 0.0,
            'response_times': deque(maxlen=100)
        })
        self.source_priority: Dict[str, float] = {}
        self.failover_history: deque = deque(maxlen=100)
        self.routing_decisions: deque = deque(maxlen=1000)
    
    def update_health(self, source: str, success: bool, latency: float, error: Optional[str] = None):
        """
        Update health metrics for a source
        
        Args:
            source: Source name
            success: Whether request was successful
            latency: Response time in seconds
            error: Error message if failed
        """
        health = self.source_health[source]
        health['total_requests'] += 1
        health['response_times'].append(latency)
        
        if success:
            health['successful_requests'] += 1
            health['consecutive_failures'] = 0
            health['last_success'] = datetime.now().isoformat()
        else:
            health['failed_requests'] += 1
            health['consecutive_failures'] += 1
            health['last_failure'] = datetime.now().isoformat()
        
        # Update success rate
        if health['total_requests'] > 0:
            health['success_rate'] = (health['successful_requests'] / health['total_requests']) * 100
        
        # Update average latency
        if health['response_times']:
            health['avg_response_time'] = sum(health['response_times']) / len(health['response_times'])
        
        # Calculate health score (0-100)
        health['health_score'] = self._calculate_health_score(health)
        
        # Update priority
        self._update_priority(source)
    
    def _calculate_health_score(self, health: Dict) -> float:
        """Calculate health score (0-100)"""
        score = 100.0
        
        # Penalize for failures
        if health['total_requests'] > 0:
            failure_rate = (health['failed_requests'] / health['total_requests']) * 100
            score -= failure_rate * 0.5  # Each 1% failure = -0.5 points
        
        # Penalize for consecutive failures
        score -= health['consecutive_failures'] * 5  # Each consecutive failure = -5 points
        
        # Penalize for high latency
        if health['avg_response_time'] > 5:
            score -= (health['avg_response_time'] - 5) * 2  # -2 points per second over 5s
        
        # Penalize for old last success
        if health['last_success']:
            try:
                last_success = datetime.fromisoformat(health['last_success'])
                age_seconds = (datetime.now() - last_success).total_seconds()
                if age_seconds > 300:  # 5 minutes
                    score -= (age_seconds - 300) / 60  # -1 point per minute over 5 min
            except Exception:
                pass
        
        return max(0.0, min(100.0, score))
    
    def _update_priority(self, source: str):
        """Update priority score for source"""
        health = self.source_health[source]
        
        # Priority based on health score and latency
        priority = health['health_score']
        
        # Boost priority for low latency
        if health['avg_response_time'] < 1.0:
            priority += 10
        elif health['avg_response_time'] < 2.0:
            priority += 5
        
        # Reduce priority for high latency
        if health['avg_response_time'] > 5.0:
            priority -= 20
        elif health['avg_response_time'] > 3.0:
            priority -= 10
        
        self.source_priority[source] = priority
    
    def get_best_source(self, symbol: str, available_sources: List[str]) -> Optional[str]:
        """
        Get best available source for a symbol
        
        Args:
            symbol: Stock symbol
            available_sources: List of available sources
            
        Returns:
            Best source name or None
        """
        if not available_sources:
            return None
        
        # Filter to only available sources
        available_health = {
            source: self.source_health[source]
            for source in available_sources
            if source in self.source_health
        }
        
        if not available_health:
            # No health data - return first available
            return available_sources[0]
        
        # Rank by priority (health score + latency bonus)
        ranked = sorted(
            available_health.items(),
            key=lambda x: (
                -self.source_priority.get(x[0], x[1]['health_score']),  # Higher priority first
                x[1]['avg_response_time']  # Lower latency first
            )
        )
        
        best_source = ranked[0][0]
        
        # Record routing decision
        self.routing_decisions.append({
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'source': best_source,
            'health_score': available_health[best_source]['health_score'],
            'priority': self.source_priority.get(best_source, 0)
        })
        
        return best_source
    
    def should_failover(self, source: str) -> bool:
        """
        Determine if we should failover from a source
        
        Args:
            source: Source name
            
        Returns:
            True if should failover
        """
        if source not in self.source_health:
            return False
        
        health = self.source_health[source]
        
        # Failover conditions
        if health['consecutive_failures'] >= 3:
            return True
        
        if health['health_score'] < 20:
            return True
        
        if health['success_rate'] < 50 and health['total_requests'] >= 10:
            return True
        
        return False
    
    def record_failover(self, from_source: str, to_source: str, reason: str):
        """Record a failover event"""
        self.failover_history.append({
            'timestamp': datetime.now().isoformat(),
            'from_source': from_source,
            'to_source': to_source,
            'reason': reason
        })
        logger.info(f"Failover: {from_source} -> {to_source} (reason: {reason})")
    
    def get_routing_stats(self) -> Dict:
        """Get routing statistics"""
        return {
            'source_health': {
                source: {
                    'health_score': health['health_score'],
                    'success_rate': health['success_rate'],
                    'avg_latency': health['avg_response_time'],
                    'total_requests': health['total_requests'],
                    'consecutive_failures': health['consecutive_failures']
                }
                for source, health in self.source_health.items()
            },
            'source_priority': dict(self.source_priority),
            'total_failovers': len(self.failover_history),
            'recent_failovers': list(self.failover_history)[-10:],
            'recent_routing_decisions': list(self.routing_decisions)[-20:]
        }


# Global instance
intelligent_source_router = IntelligentSourceRouter()

