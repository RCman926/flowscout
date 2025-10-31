"""
Real-Time Data Quality Monitor
Advanced data quality monitoring with real-time scoring and validation
SYNCHRONOUS implementation for maximum compatibility
"""

import time
import logging
from datetime import datetime, timedelta, time as time_obj
from typing import Dict, List, Any, Optional, Tuple
from zoneinfo import ZoneInfo
import yfinance as yf
import numpy as np
import pandas as pd
from dataclasses import dataclass
import statistics

@dataclass
class QualityMetrics:
    """Comprehensive data quality metrics"""
    symbol: str
    overall_score: int  # 0-100 overall quality score
    freshness_score: int  # Data age penalty
    volume_score: int  # Volume consistency score
    price_score: int  # Price movement validation score
    historical_score: int  # Historical context validation
    anomaly_flags: List[str]  # List of detected anomalies
    quality_trend: str  # IMPROVING, STABLE, DEGRADING
    last_update: datetime
    data_latency_ms: float
    confidence_level: int

@dataclass
class QualityAlert:
    """Quality degradation alert"""
    severity: str  # CRITICAL, WARNING, INFO
    message: str
    symbol: str
    metric_affected: str
    current_score: int
    threshold: int
    timestamp: datetime
    recommended_action: str

class RealTimeQualityMonitor:
    """
    Advanced real-time data quality monitoring system
    Continuously monitors data accuracy, freshness, and consistency
    """
    
    def __init__(self):
        self.quality_history = {}  # Symbol -> List[QualityMetrics] 
        self.alert_history = []
        self.baseline_metrics = {}  # Historical baselines for comparison
        self.monitoring_config = {
            'freshness_penalty_per_second': 1,  # Points lost per second of staleness
            'volume_spike_threshold': 3.0,      # 3x average = spike
            'volume_drop_threshold': 0.3,       # 30% of average = drop  
            'price_jump_threshold': 0.05,       # 5% price jump threshold
            'historical_deviation_threshold': 0.15,  # 15% from historical range
            'quality_degradation_threshold': 70,     # Alert below 70% quality
            'max_history_length': 100
        }
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Performance tracking
        self.monitoring_stats = {
            'total_evaluations': 0,
            'alerts_generated': 0,
            'avg_evaluation_time_ms': 0.0,
            'quality_trend_distribution': {'IMPROVING': 0, 'STABLE': 0, 'DEGRADING': 0}
        }
    
    def evaluate_data_quality(self, symbol: str, data: Dict, fetch_start_time: float = None) -> QualityMetrics:
        """
        Primary quality evaluation method - comprehensive real-time analysis
        Returns detailed quality metrics with scoring and anomaly detection
        """
        evaluation_start = time.time()
        self.monitoring_stats['total_evaluations'] += 1
        
        try:
            # Calculate data latency
            data_latency_ms = 0.0
            if fetch_start_time:
                data_latency_ms = (evaluation_start - fetch_start_time) * 1000
            
            # 1. Evaluate data freshness
            freshness_score, freshness_flags = self._evaluate_freshness(data)
            
            # 2. Evaluate volume consistency
            volume_score, volume_flags = self._evaluate_volume_quality(symbol, data)
            
            # 3. Evaluate price movement validation
            price_score, price_flags = self._evaluate_price_quality(symbol, data)
            
            # 4. Evaluate historical context
            historical_score, historical_flags = self._evaluate_historical_context(symbol, data)
            
            # 5. Calculate overall quality score
            overall_score = self._calculate_overall_score(
                freshness_score, volume_score, price_score, historical_score
            )
            
            # 6. Aggregate anomaly flags
            all_flags = freshness_flags + volume_flags + price_flags + historical_flags
            
            # 7. Determine quality trend
            quality_trend = self._analyze_quality_trend(symbol, overall_score)
            
            # 8. Calculate confidence level
            confidence_level = self._calculate_confidence_level(
                overall_score, len(all_flags), data_latency_ms
            )
            
            # Create quality metrics object
            quality_metrics = QualityMetrics(
                symbol=symbol,
                overall_score=overall_score,
                freshness_score=freshness_score,
                volume_score=volume_score,
                price_score=price_score,
                historical_score=historical_score,
                anomaly_flags=all_flags,
                quality_trend=quality_trend,
                last_update=datetime.now(),
                data_latency_ms=data_latency_ms,
                confidence_level=confidence_level
            )
            
            # 9. Store quality history
            self._store_quality_metrics(symbol, quality_metrics)
            
            # 10. Check for quality alerts
            self._check_quality_alerts(quality_metrics)
            
            # 11. Update performance stats
            evaluation_time = (time.time() - evaluation_start) * 1000
            self._update_performance_stats(evaluation_time, quality_trend)
            
            self.logger.info(
                f"📊 QUALITY EVAL {symbol}: Overall {overall_score}%, "
                f"Confidence {confidence_level}%, {len(all_flags)} flags, "
                f"Trend: {quality_trend}, Latency: {data_latency_ms:.1f}ms"
            )
            
            return quality_metrics
            
        except Exception as e:
            self.logger.error(f"Quality evaluation failed for {symbol}: {e}")
            return QualityMetrics(
                symbol=symbol,
                overall_score=50,  # Neutral score on error
                freshness_score=50,
                volume_score=50,
                price_score=50,
                historical_score=50,
                anomaly_flags=[f"Evaluation error: {str(e)}"],
                quality_trend='UNKNOWN',
                last_update=datetime.now(),
                data_latency_ms=0.0,
                confidence_level=25
            )
    
    def _evaluate_freshness(self, data: Dict) -> Tuple[int, List[str]]:
        """Evaluate data freshness and penalize stale timestamps"""
        flags = []
        base_score = 100
        
        # Check for timestamp
        timestamp = data.get('timestamp')
        if not timestamp:
            flags.append("Missing timestamp - cannot verify freshness")
            return 60, flags
        
        try:
            # Handle different timestamp formats
            if isinstance(timestamp, str):
                data_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif isinstance(timestamp, datetime):
                data_time = timestamp
            else:
                flags.append("Invalid timestamp format")
                return 50, flags
            
            # Calculate age in seconds
            current_time = datetime.now()
            if data_time.tzinfo and not current_time.tzinfo:
                current_time = current_time.replace(tzinfo=data_time.tzinfo)
            elif not data_time.tzinfo and current_time.tzinfo:
                data_time = data_time.replace(tzinfo=current_time.tzinfo)
            
            age_seconds = (current_time - data_time).total_seconds()
            
            # Apply freshness penalties
            penalty_per_second = self.monitoring_config['freshness_penalty_per_second']
            freshness_penalty = min(50, age_seconds * penalty_per_second)  # Max 50 point penalty
            
            final_score = max(50, base_score - freshness_penalty)
            
            # Generate freshness flags
            if age_seconds > 300:  # 5 minutes
                flags.append(f"Stale data: {age_seconds:.0f}s old (>5min)")
            elif age_seconds > 60:  # 1 minute
                flags.append(f"Aging data: {age_seconds:.0f}s old (>1min)")
            elif age_seconds > 30:  # 30 seconds
                flags.append(f"Moderate age: {age_seconds:.0f}s old")
            
            return int(final_score), flags
            
        except Exception as e:
            flags.append(f"Freshness evaluation error: {str(e)}")
            return 50, flags
    
    def _evaluate_volume_quality(self, symbol: str, data: Dict) -> Tuple[int, List[str]]:
        """Evaluate volume consistency and detect anomalies"""
        flags = []
        base_score = 100
        
        current_volume = data.get('volume', 0)
        
        if current_volume <= 0:
            flags.append("Missing or invalid volume data")
            return 70, flags  # Not critical for all data types
        
        try:
            # Get historical volume baseline
            baseline_volume = self._get_volume_baseline(symbol)
            
            if baseline_volume <= 0:
                # No baseline yet, return neutral score
                return 85, flags
            
            # Check for volume spikes
            spike_threshold = self.monitoring_config['volume_spike_threshold']
            drop_threshold = self.monitoring_config['volume_drop_threshold']
            
            volume_ratio = current_volume / baseline_volume
            
            if volume_ratio > spike_threshold:
                flags.append(f"Volume spike: {volume_ratio:.1f}x normal ({current_volume:,} vs {baseline_volume:,})")
                base_score -= 15  # Moderate penalty for spikes
            elif volume_ratio < drop_threshold:
                flags.append(f"Volume drop: {volume_ratio:.1%} of normal ({current_volume:,} vs {baseline_volume:,})")
                base_score -= 20  # Higher penalty for drops (more suspicious)
            
            # Check for unrealistic volumes
            if current_volume > 1000000000:  # 1B+ volume is very high
                flags.append(f"Extremely high volume: {current_volume:,}")
                base_score -= 25
            elif current_volume < 100:  # Very low volume
                flags.append(f"Extremely low volume: {current_volume:,}")
                base_score -= 10
            
            return max(50, base_score), flags
            
        except Exception as e:
            flags.append(f"Volume evaluation error: {str(e)}")
            return 70, flags
    
    def _evaluate_price_quality(self, symbol: str, data: Dict) -> Tuple[int, List[str]]:
        """Evaluate price movement and detect unrealistic jumps"""
        flags = []
        base_score = 100
        
        current_price = data.get('price', 0)
        
        if current_price <= 0:
            flags.append("Missing or invalid price data")
            return 40, flags  # Critical issue for price data
        
        try:
            # Get previous price for comparison
            previous_price = self._get_previous_price(symbol)
            
            if previous_price <= 0:
                # No previous price, return neutral score
                return 85, flags
            
            # Calculate price change percentage
            price_change_pct = abs(current_price - previous_price) / previous_price
            jump_threshold = self.monitoring_config['price_jump_threshold']
            
            if price_change_pct > jump_threshold:
                flags.append(
                    f"Large price movement: {price_change_pct:.1%} "
                    f"({previous_price:.2f} -> {current_price:.2f})"
                )
                # Scale penalty based on magnitude of jump
                if price_change_pct > 0.20:  # >20% jump
                    base_score -= 30
                elif price_change_pct > 0.10:  # >10% jump
                    base_score -= 20
                else:  # 5-10% jump
                    base_score -= 10
            
            # Check for obviously unrealistic prices
            if current_price > 10000:  # Very high price
                flags.append(f"Very high price: ${current_price:.2f}")
                base_score -= 15
            elif current_price < 0.01:  # Very low price
                flags.append(f"Very low price: ${current_price:.2f}")
                base_score -= 15
            
            # Check for price precision anomalies (too many decimal places)
            price_str = str(current_price)
            if '.' in price_str and len(price_str.split('.')[1]) > 4:
                flags.append("Unusual price precision (>4 decimal places)")
                base_score -= 5
            
            return max(50, base_score), flags
            
        except Exception as e:
            flags.append(f"Price evaluation error: {str(e)}")
            return 70, flags
    
    def _evaluate_historical_context(self, symbol: str, data: Dict) -> Tuple[int, List[str]]:
        """Evaluate data against historical context and patterns"""
        flags = []
        base_score = 100
        
        current_price = data.get('price', 0)
        current_volume = data.get('volume', 0)
        
        if current_price <= 0:
            return 85, flags  # Cannot validate without price
        
        try:
            # Get historical context
            historical_context = self._get_historical_context(symbol)
            
            if not historical_context:
                return 85, flags  # No historical data available
            
            # Check price against historical range
            price_range = historical_context.get('price_range', [0, 999999])
            if not (price_range[0] <= current_price <= price_range[1]):
                flags.append(
                    f"Price outside historical range: ${current_price:.2f} "
                    f"not in [${price_range[0]:.2f}, ${price_range[1]:.2f}]"
                )
                base_score -= 20
            
            # Check against historical average with deviation threshold
            price_avg = historical_context.get('price_avg', current_price)
            deviation_threshold = self.monitoring_config['historical_deviation_threshold']
            
            if price_avg > 0:
                price_deviation = abs(current_price - price_avg) / price_avg
                if price_deviation > deviation_threshold:
                    flags.append(
                        f"High deviation from historical avg: {price_deviation:.1%} "
                        f"(${current_price:.2f} vs ${price_avg:.2f})"
                    )
                    base_score -= 10
            
            # Check volume against historical patterns
            if current_volume > 0:
                volume_avg = historical_context.get('volume_avg', current_volume)
                if volume_avg > 0:
                    volume_deviation = abs(current_volume - volume_avg) / volume_avg
                    if volume_deviation > 2.0:  # >200% deviation
                        flags.append(
                            f"High volume deviation: {volume_deviation:.1%} "
                            f"({current_volume:,} vs {volume_avg:,})"
                        )
                        base_score -= 5
            
            # Check for weekend/holiday trading (if timestamp available)
            timestamp = data.get('timestamp')
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        dt = timestamp
                    
                    if dt.weekday() >= 5:  # Saturday or Sunday
                        flags.append("Weekend trading detected")
                        base_score -= 5
                        
                except Exception:
                    pass  # Ignore timestamp parsing errors here
            
            return max(50, base_score), flags
            
        except Exception as e:
            flags.append(f"Historical evaluation error: {str(e)}")
            return 75, flags
    
    def _calculate_overall_score(self, freshness_score: int, volume_score: int, 
                               price_score: int, historical_score: int) -> int:
        """Calculate weighted overall quality score"""
        
        # Weights based on importance for trading data
        weights = {
            'freshness': 0.25,    # Data age is important
            'volume': 0.20,       # Volume consistency is important
            'price': 0.35,        # Price accuracy is most critical
            'historical': 0.20    # Historical context provides validation
        }
        
        weighted_score = (
            freshness_score * weights['freshness'] +
            volume_score * weights['volume'] +
            price_score * weights['price'] +
            historical_score * weights['historical']
        )
        
        return int(min(100, max(0, weighted_score)))
    
    def _analyze_quality_trend(self, symbol: str, current_score: int) -> str:
        """Analyze quality trend over recent measurements"""
        
        if symbol not in self.quality_history:
            return 'UNKNOWN'
        
        history = self.quality_history[symbol]
        if len(history) < 3:
            return 'INSUFFICIENT_DATA'
        
        # Look at last 3 scores for trend analysis
        recent_scores = [q.overall_score for q in history[-3:]]
        recent_scores.append(current_score)
        
        # Calculate trend using linear regression slope
        x = list(range(len(recent_scores)))
        y = recent_scores
        
        # Simple slope calculation
        n = len(x)
        slope = (n * sum(x[i] * y[i] for i in range(n)) - sum(x) * sum(y)) / (n * sum(x[i]**2 for i in range(n)) - sum(x)**2)
        
        if slope > 2:
            return 'IMPROVING'
        elif slope < -2:
            return 'DEGRADING'
        else:
            return 'STABLE'
    
    def _calculate_confidence_level(self, overall_score: int, num_flags: int, latency_ms: float) -> int:
        """Calculate confidence level based on multiple factors"""
        base_confidence = overall_score
        
        # Penalize for anomaly flags
        flag_penalty = min(25, num_flags * 5)
        base_confidence -= flag_penalty
        
        # Penalize for high latency
        if latency_ms > 5000:  # >5 seconds
            base_confidence -= 20
        elif latency_ms > 2000:  # >2 seconds
            base_confidence -= 10
        elif latency_ms > 1000:  # >1 second
            base_confidence -= 5
        
        return max(0, min(100, base_confidence))
    
    def _get_volume_baseline(self, symbol: str) -> float:
        """Get volume baseline for comparison"""
        if symbol not in self.baseline_metrics:
            return 0.0
        
        baseline = self.baseline_metrics[symbol]
        return baseline.get('avg_volume', 0.0)
    
    def _get_previous_price(self, symbol: str) -> float:
        """Get previous price for comparison"""
        if symbol not in self.quality_history:
            return 0.0
        
        history = self.quality_history[symbol]
        if not history:
            return 0.0
        
        # Find most recent measurement with valid price data
        for quality_metric in reversed(history):
            if hasattr(quality_metric, 'symbol'):  # Ensure it's a proper object
                # Try to get price from last known good data
                return self.baseline_metrics.get(symbol, {}).get('last_price', 0.0)
        
        return 0.0
    
    def _get_historical_context(self, symbol: str) -> Dict:
        """Get historical context for validation"""
        if symbol not in self.baseline_metrics:
            return {}
        
        return self.baseline_metrics[symbol]
    
    def _store_quality_metrics(self, symbol: str, metrics: QualityMetrics):
        """Store quality metrics in history"""
        if symbol not in self.quality_history:
            self.quality_history[symbol] = []
        
        history = self.quality_history[symbol]
        history.append(metrics)
        
        # Limit history length
        max_length = self.monitoring_config['max_history_length']
        if len(history) > max_length:
            history.pop(0)
        
        # Update baseline metrics
        self._update_baseline_metrics(symbol, metrics)
    
    def _update_baseline_metrics(self, symbol: str, metrics: QualityMetrics):
        """Update baseline metrics for future comparisons"""
        if symbol not in self.baseline_metrics:
            self.baseline_metrics[symbol] = {
                'price_range': [999999, 0],
                'price_avg': 0.0,
                'volume_avg': 0.0,
                'last_price': 0.0,
                'sample_count': 0
            }
        
        baseline = self.baseline_metrics[symbol]
        
        # Update based on recent quality history
        if symbol in self.quality_history and self.quality_history[symbol]:
            recent_metrics = self.quality_history[symbol][-10:]  # Last 10 measurements
            
            # Calculate price statistics (from data cache - simplified)
            # This would ideally pull from the actual data, but for now we'll use a simple approach
            baseline['sample_count'] = len(recent_metrics)
            
            # Simple baseline update - in a full implementation, this would be more sophisticated
            if hasattr(metrics, 'overall_score'):
                baseline['last_update'] = metrics.last_update
    
    def _check_quality_alerts(self, metrics: QualityMetrics):
        """Check for quality alerts and generate notifications"""
        threshold = self.monitoring_config['quality_degradation_threshold']
        
        alerts = []
        
        # Overall quality degradation
        if metrics.overall_score < threshold:
            alerts.append(QualityAlert(
                severity='WARNING' if metrics.overall_score > 50 else 'CRITICAL',
                message=f"Quality degradation: {metrics.overall_score}% (threshold: {threshold}%)",
                symbol=metrics.symbol,
                metric_affected='overall_quality',
                current_score=metrics.overall_score,
                threshold=threshold,
                timestamp=datetime.now(),
                recommended_action='Investigate data sources and refresh data feeds'
            ))
        
        # Specific metric alerts - BUT suppress freshness warnings when market is closed
        # Check if market is open (9:30 AM - 4:00 PM ET)
        et_now = datetime.now(ZoneInfo('America/New_York'))
        market_open_time = time_obj(9, 30)
        market_close_time = time_obj(16, 0)
        is_market_open = (et_now.weekday() < 5 and 
                         market_open_time <= et_now.time() <= market_close_time)
        
        # Only alert about stale data if market is OPEN
        if metrics.freshness_score < 60 and is_market_open:
            alerts.append(QualityAlert(
                severity='WARNING',
                message=f"Stale data detected: {metrics.freshness_score}% freshness",
                symbol=metrics.symbol,
                metric_affected='freshness',
                current_score=metrics.freshness_score,
                threshold=60,
                timestamp=datetime.now(),
                recommended_action='Check data feed connectivity and refresh rates'
            ))
        
        if metrics.confidence_level < 50:
            alerts.append(QualityAlert(
                severity='CRITICAL',
                message=f"Low confidence in data: {metrics.confidence_level}%",
                symbol=metrics.symbol,
                metric_affected='confidence',
                current_score=metrics.confidence_level,
                threshold=50,
                timestamp=datetime.now(),
                recommended_action='Multiple quality issues detected - investigate thoroughly'
            ))
        
        # Store alerts and log
        for alert in alerts:
            self.alert_history.append(alert)
            self.monitoring_stats['alerts_generated'] += 1
            
            self.logger.warning(
                f"🚨 QUALITY ALERT [{alert.severity}] {alert.symbol}: {alert.message}"
            )
        
        # Limit alert history
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-500:]  # Keep last 500 alerts
    
    def _update_performance_stats(self, evaluation_time_ms: float, quality_trend: str):
        """Update monitoring performance statistics"""
        stats = self.monitoring_stats
        
        # Update average evaluation time
        current_avg = stats['avg_evaluation_time_ms']
        total_evals = stats['total_evaluations']
        
        stats['avg_evaluation_time_ms'] = (
            (current_avg * (total_evals - 1) + evaluation_time_ms) / total_evals
        )
        
        # Update trend distribution
        if quality_trend in stats['quality_trend_distribution']:
            stats['quality_trend_distribution'][quality_trend] += 1
    
    def get_quality_summary(self, symbol: str = None) -> Dict:
        """Get comprehensive quality summary"""
        if symbol:
            # Symbol-specific summary
            if symbol not in self.quality_history:
                return {'error': f'No quality data for {symbol}'}
            
            history = self.quality_history[symbol]
            if not history:
                return {'error': f'Empty quality history for {symbol}'}
            
            latest = history[-1]
            avg_score = sum(q.overall_score for q in history[-10:]) / min(10, len(history))
            
            return {
                'symbol': symbol,
                'latest_quality': latest.overall_score,
                'average_quality_10': round(avg_score, 1),
                'confidence_level': latest.confidence_level,
                'quality_trend': latest.quality_trend,
                'anomaly_count': len(latest.anomaly_flags),
                'last_update': latest.last_update.isoformat(),
                'data_latency_ms': latest.data_latency_ms
            }
        else:
            # Global summary
            total_symbols = len(self.quality_history)
            if total_symbols == 0:
                return {'total_symbols': 0}
            
            # Calculate aggregate statistics
            all_latest_scores = []
            for symbol_history in self.quality_history.values():
                if symbol_history:
                    all_latest_scores.append(symbol_history[-1].overall_score)
            
            avg_quality = sum(all_latest_scores) / len(all_latest_scores) if all_latest_scores else 0
            
            recent_alerts = [a for a in self.alert_history if (datetime.now() - a.timestamp).seconds < 3600]
            
            return {
                'total_symbols_monitored': total_symbols,
                'average_quality_score': round(avg_quality, 1),
                'total_evaluations': self.monitoring_stats['total_evaluations'],
                'alerts_last_hour': len(recent_alerts),
                'avg_evaluation_time_ms': round(self.monitoring_stats['avg_evaluation_time_ms'], 2),
                'quality_trend_distribution': self.monitoring_stats['quality_trend_distribution'].copy()
            }
    
    def get_recent_alerts(self, severity: str = None, limit: int = 10) -> List[QualityAlert]:
        """Get recent quality alerts"""
        alerts = self.alert_history
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        # Sort by timestamp (newest first) and limit
        alerts.sort(key=lambda x: x.timestamp, reverse=True)
        return alerts[:limit]

# Global instance for easy access
real_time_quality_monitor = RealTimeQualityMonitor()