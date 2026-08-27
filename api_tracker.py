"""
API Usage Tracker and Rate Limit Monitor
Tracks all API calls, rate limits, and usage statistics
Enhanced with Circuit Breaker Pattern for reliability
"""

import time
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from collections import defaultdict
import logging
import asyncio

logger = logging.getLogger(__name__)


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit Breaker Pattern Implementation
    Prevents cascading failures by opening circuit after threshold failures
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60, half_open_max_calls: int = 3):
        """
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery (half-open state)
            half_open_max_calls: Max calls in half-open state before closing
        """
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.half_open_calls = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self.success_count = 0
        self.total_calls = 0
        self.lock = asyncio.Lock()
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Function to execute
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
        """
        # Check circuit state
        if self.state == 'OPEN':
            if self.last_failure_time and time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
                self.half_open_calls = 0
                logger.info(f"Circuit breaker entering HALF_OPEN state (recovery attempt)")
            else:
                remaining = int(self.recovery_timeout - (time.time() - self.last_failure_time))
                raise CircuitBreakerOpenError(f"Circuit breaker is OPEN. Retry in {remaining} seconds")
        
        # Execute function
        try:
            result = func(*args, **kwargs)
            self.total_calls += 1
            
            # Success - reset failure count
            if self.state == 'HALF_OPEN':
                self.half_open_calls += 1
                if self.half_open_calls >= self.half_open_max_calls:
                    # Multiple successes in half-open - close circuit
                    self.state = 'CLOSED'
                    self.failure_count = 0
                    self.half_open_calls = 0
                    logger.info(f"Circuit breaker CLOSED after successful recovery")
            
            if self.state == 'CLOSED':
                self.failure_count = 0
                self.success_count += 1
            
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            self.total_calls += 1
            
            # Check if threshold reached
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
                logger.warning(f"Circuit breaker OPENED after {self.failure_count} failures")
            
            # In half-open state, any failure opens circuit again
            elif self.state == 'HALF_OPEN':
                self.state = 'OPEN'
                logger.warning(f"Circuit breaker OPENED from HALF_OPEN after failure")
            
            raise
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Async version of call()"""
        # Check circuit state
        if self.state == 'OPEN':
            if self.last_failure_time and time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
                self.half_open_calls = 0
                logger.info(f"Circuit breaker entering HALF_OPEN state (recovery attempt)")
            else:
                remaining = int(self.recovery_timeout - (time.time() - self.last_failure_time))
                raise CircuitBreakerOpenError(f"Circuit breaker is OPEN. Retry in {remaining} seconds")
        
        # Execute function
        try:
            result = await func(*args, **kwargs)
            self.total_calls += 1
            
            # Success - reset failure count
            if self.state == 'HALF_OPEN':
                self.half_open_calls += 1
                if self.half_open_calls >= self.half_open_max_calls:
                    self.state = 'CLOSED'
                    self.failure_count = 0
                    self.half_open_calls = 0
                    logger.info(f"Circuit breaker CLOSED after successful recovery")
            
            if self.state == 'CLOSED':
                self.failure_count = 0
                self.success_count += 1
            
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            self.total_calls += 1
            
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
                logger.warning(f"Circuit breaker OPENED after {self.failure_count} failures")
            elif self.state == 'HALF_OPEN':
                self.state = 'OPEN'
                logger.warning(f"Circuit breaker OPENED from HALF_OPEN after failure")
            
            raise
    
    def get_state(self) -> Dict:
        """Get current circuit breaker state"""
        return {
            'state': self.state,
            'failure_count': self.failure_count,
            'failure_threshold': self.failure_threshold,
            'success_count': self.success_count,
            'total_calls': self.total_calls,
            'success_rate': (self.success_count / self.total_calls * 100) if self.total_calls > 0 else 0.0,
            'last_failure_time': self.last_failure_time,
            'recovery_timeout': self.recovery_timeout
        }
    
    def reset(self):
        """Manually reset circuit breaker to CLOSED state"""
        self.state = 'CLOSED'
        self.failure_count = 0
        self.half_open_calls = 0
        self.last_failure_time = None
        logger.info("Circuit breaker manually reset")


class APITracker:
    """
    Tracks API usage, rate limits, and prevents cutoff
    """
    
    # Known rate limits for different APIs
    RATE_LIMITS = {
        'yfinance': {
            # Stage A Yahoo-only: keep well under informal ~1 req/s comfort zone
            'requests_per_minute': 24,
            'requests_per_hour': 800,
            'requests_per_day': 10000,
            'cooldown_seconds': 3.0,
            'block_duration_seconds': 90,
            'notes': 'Yahoo/yfinance unofficial — IP bans if aggressive. Open-protect: 3s cooldown, 90s block (recover mid-session).'
        },
        'polygon': {
            'requests_per_minute': 5,  # Free tier
            'requests_per_hour': 200,  # Free tier
            'requests_per_day': 5000,  # Free tier
            'cooldown_seconds': 12,  # 5 requests per minute = 12 seconds between
            'block_duration_seconds': 3600,
            'notes': 'Free tier: 5 req/min, 200 req/hour'
        },
        'finnhub': {
            'requests_per_minute': 60,  # Free tier
            'requests_per_hour': 60,  # Free tier
            'requests_per_day': 60,  # Free tier
            'cooldown_seconds': 1,  # 1 request per second
            'block_duration_seconds': 3600,
            'notes': 'Free tier: 60 requests per minute'
        },
        'alphavantage': {
            'requests_per_minute': 5,  # Free tier
            'requests_per_hour': 500,  # Free tier
            'requests_per_day': 500,  # Free tier
            'cooldown_seconds': 12,
            'block_duration_seconds': 3600,
            'notes': 'Free tier: 5 requests per minute, 500 per day'
        },
        'ibkr': {
            'requests_per_minute': 100,  # IBKR Gateway limits
            'requests_per_hour': 6000,
            'requests_per_day': 100000,
            'cooldown_seconds': 0.3,  # OPTIMIZED: Reduced to 300ms for faster IBKR updates (was 600ms)
            'block_duration_seconds': 300,
            'notes': 'IBKR Gateway - depends on subscription'
        }
    }
    
    def __init__(self, stats_file: str = "api_usage_stats.json"):
        self.stats_file = stats_file
        self.usage_stats = self._load_stats()
        
        # Track requests in memory (last hour)
        self.request_history = defaultdict(list)  # api_name -> list of timestamps
        self.blocked_apis = {}  # api_name -> block_until_timestamp
        self.last_request_time = {}  # api_name -> last_request_timestamp
        
        # Track daily/hourly/minute counts
        self.daily_counts = defaultdict(int)  # api_name -> count
        self.hourly_counts = defaultdict(int)  # api_name -> count
        self.minute_counts = defaultdict(int)  # api_name -> count
        
        # Circuit breakers per API
        self.circuit_breakers = {}  # api_name -> CircuitBreaker
        
        # Initialize circuit breakers for each API
        for api_name in self.RATE_LIMITS.keys():
            # More sensitive breakers for critical APIs
            if api_name == 'ibkr':
                self.circuit_breakers[api_name] = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
            else:
                self.circuit_breakers[api_name] = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        
        # Reset counters if new day
        self._reset_daily_if_needed()
        
    def _load_stats(self) -> Dict:
        """Load usage statistics from file"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading API stats: {e}")
        return {
            'total_requests': {},
            'total_errors': {},
            'rate_limit_hits': {},
            'last_reset': datetime.now().isoformat()
        }
    
    def _save_stats(self):
        """Save usage statistics to file"""
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(self.usage_stats, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving API stats: {e}")
    
    def _reset_daily_if_needed(self):
        """Reset daily counters if it's a new day"""
        last_reset = self.usage_stats.get('last_reset')
        if last_reset:
            try:
                last_reset_dt = datetime.fromisoformat(last_reset)
                if datetime.now().date() > last_reset_dt.date():
                    # New day - reset daily counts
                    self.daily_counts.clear()
                    self.usage_stats['last_reset'] = datetime.now().isoformat()
                    logger.info("Daily API counters reset")
            except Exception:
                pass
    
    def _clean_old_requests(self, api_name: str):
        """Remove requests older than 1 hour from history"""
        current_time = time.time()
        one_hour_ago = current_time - 3600
        self.request_history[api_name] = [
            ts for ts in self.request_history[api_name] 
            if ts > one_hour_ago
        ]
    
    def _update_counts(self, api_name: str):
        """Update minute/hourly/daily counts"""
        current_time = time.time()
        current_minute = int(current_time / 60)
        current_hour = int(current_time / 3600)
        current_day = int(current_time / 86400)
        
        # Clean old requests
        self._clean_old_requests(api_name)
        
        # Count requests in last minute
        minute_ago = current_time - 60
        minute_count = sum(1 for ts in self.request_history[api_name] if ts > minute_ago)
        self.minute_counts[api_name] = minute_count
        
        # Count requests in last hour
        hour_ago = current_time - 3600
        hour_count = sum(1 for ts in self.request_history[api_name] if ts > hour_ago)
        self.hourly_counts[api_name] = hour_count
        
        # Daily count (persisted)
        day_key = f"{api_name}_{current_day}"
        if day_key not in self.usage_stats:
            self.usage_stats[day_key] = 0
        self.usage_stats[day_key] = self.usage_stats.get(day_key, 0) + 1
        self.daily_counts[api_name] = self.usage_stats[day_key]
    
    def can_make_request(self, api_name: str) -> tuple[bool, Optional[str]]:
        """
        Check if API request can be made
        
        Returns:
            (can_request: bool, reason: Optional[str])
        """
        # Check circuit breaker first
        if self.is_circuit_open(api_name):
            cb = self.circuit_breakers[api_name]
            if cb.last_failure_time:
                remaining = int(cb.recovery_timeout - (time.time() - cb.last_failure_time))
                if remaining > 0:
                    return False, f"Circuit breaker OPEN - retry in {remaining} seconds"
                else:
                    # Recovery timeout passed - allow attempt (will enter half-open)
                    pass
        
        # Check if API is blocked
        if api_name in self.blocked_apis:
            block_until = self.blocked_apis[api_name]
            if time.time() < block_until:
                remaining = int(block_until - time.time())
                return False, f"API blocked for {remaining} more seconds"
            else:
                # Block expired
                del self.blocked_apis[api_name]
        
        # Check rate limits
        limits = self.RATE_LIMITS.get(api_name, {})
        if not limits:
            return True, None  # Unknown API - allow
        
        # Check cooldown
        if api_name in self.last_request_time:
            time_since_last = time.time() - self.last_request_time[api_name]
            cooldown = limits.get('cooldown_seconds', 0)
            if time_since_last < cooldown:
                wait_time = cooldown - time_since_last
                return False, f"Cooldown: wait {wait_time:.1f} seconds"
        
        # Update counts
        self._update_counts(api_name)
        
        # Check per-minute limit
        per_minute = limits.get('requests_per_minute', float('inf'))
        if self.minute_counts[api_name] >= per_minute:
            return False, f"Rate limit: {per_minute} requests/minute exceeded"
        
        # Check per-hour limit
        per_hour = limits.get('requests_per_hour', float('inf'))
        if self.hourly_counts[api_name] >= per_hour:
            return False, f"Rate limit: {per_hour} requests/hour exceeded"
        
        # Check per-day limit
        per_day = limits.get('requests_per_day', float('inf'))
        if self.daily_counts[api_name] >= per_day:
            return False, f"Rate limit: {per_day} requests/day exceeded"
        
        return True, None
    
    def record_request(self, api_name: str, success: bool = True, error: Optional[str] = None):
        """
        Record an API request
        
        Args:
            api_name: Name of the API
            success: Whether request was successful
            error: Error message if failed
        """
        current_time = time.time()
        
        # Record in history
        self.request_history[api_name].append(current_time)
        self.last_request_time[api_name] = current_time
        
        # Update circuit breaker
        if api_name in self.circuit_breakers:
            if not success:
                # Record failure in circuit breaker
                try:
                    # Simulate a call that fails to update circuit breaker state
                    self.circuit_breakers[api_name].failure_count += 1
                    self.circuit_breakers[api_name].last_failure_time = current_time
                    if self.circuit_breakers[api_name].failure_count >= self.circuit_breakers[api_name].failure_threshold:
                        self.circuit_breakers[api_name].state = 'OPEN'
                        logger.warning(f"Circuit breaker for {api_name} OPENED after {self.circuit_breakers[api_name].failure_count} failures")
                except Exception:
                    pass
        
        # Update statistics
        if api_name not in self.usage_stats['total_requests']:
            self.usage_stats['total_requests'][api_name] = 0
            self.usage_stats['total_errors'][api_name] = 0
            self.usage_stats['rate_limit_hits'][api_name] = 0
        
        self.usage_stats['total_requests'][api_name] += 1
        
        if not success:
            self.usage_stats['total_errors'][api_name] += 1
            
            # Check if it's a rate limit error
            if error and ('rate limit' in error.lower() or '429' in error or 'too many' in error.lower()):
                self.usage_stats['rate_limit_hits'][api_name] += 1
                # Block API for configured duration
                limits = self.RATE_LIMITS.get(api_name, {})
                block_duration = limits.get('block_duration_seconds', 3600)
                self.blocked_apis[api_name] = current_time + block_duration
                logger.warning(f"API {api_name} rate limited - blocked for {block_duration} seconds")
        else:
            # Record success in circuit breaker
            if api_name in self.circuit_breakers:
                try:
                    self.circuit_breakers[api_name].success_count += 1
                    if self.circuit_breakers[api_name].state == 'HALF_OPEN':
                        self.circuit_breakers[api_name].half_open_calls += 1
                        if self.circuit_breakers[api_name].half_open_calls >= self.circuit_breakers[api_name].half_open_max_calls:
                            self.circuit_breakers[api_name].state = 'CLOSED'
                            self.circuit_breakers[api_name].failure_count = 0
                            logger.info(f"Circuit breaker for {api_name} CLOSED after successful recovery")
                    elif self.circuit_breakers[api_name].state == 'CLOSED':
                        self.circuit_breakers[api_name].failure_count = 0
                except Exception:
                    pass
        
        # Update counts
        self._update_counts(api_name)
        
        # Save stats periodically (every 10 requests)
        if self.usage_stats['total_requests'][api_name] % 10 == 0:
            self._save_stats()
    
    def get_circuit_breaker_state(self, api_name: str) -> Optional[Dict]:
        """Get circuit breaker state for an API"""
        if api_name in self.circuit_breakers:
            return self.circuit_breakers[api_name].get_state()
        return None
    
    def is_circuit_open(self, api_name: str) -> bool:
        """Check if circuit breaker is open for an API"""
        if api_name in self.circuit_breakers:
            return self.circuit_breakers[api_name].state == 'OPEN'
        return False

    def seconds_until_available(self, api_name: str) -> float:
        """Seconds until a request may be allowed (0 if available now)."""
        now = time.time()
        wait = 0.0

        cb = self.circuit_breakers.get(api_name)
        if cb is not None and getattr(cb, 'state', None) == 'OPEN' and cb.last_failure_time:
            rem = cb.recovery_timeout - (now - cb.last_failure_time)
            if rem > 0:
                wait = max(wait, float(rem))

        block_until = self.blocked_apis.get(api_name)
        if block_until is not None:
            rem = float(block_until) - now
            if rem > 0:
                wait = max(wait, rem)

        limits = self.RATE_LIMITS.get(api_name, {}) or {}
        cooldown = float(limits.get('cooldown_seconds', 0) or 0)
        last_ts = self.last_request_time.get(api_name)
        if last_ts is not None and cooldown > 0:
            rem = cooldown - (now - last_ts)
            if rem > 0:
                wait = max(wait, rem)

        return wait
    
    def get_usage_stats(self, api_name: Optional[str] = None) -> Dict:
        """
        Get usage statistics
        
        Args:
            api_name: Specific API name, or None for all
            
        Returns:
            Dictionary with usage statistics
        """
        if api_name:
            limits = self.RATE_LIMITS.get(api_name, {})
            return {
                'api_name': api_name,
                'total_requests': self.usage_stats['total_requests'].get(api_name, 0),
                'total_errors': self.usage_stats['total_errors'].get(api_name, 0),
                'rate_limit_hits': self.usage_stats['rate_limit_hits'].get(api_name, 0),
                'requests_last_minute': self.minute_counts.get(api_name, 0),
                'requests_last_hour': self.hourly_counts.get(api_name, 0),
                'requests_today': self.daily_counts.get(api_name, 0),
                'is_blocked': api_name in self.blocked_apis,
                'block_until': self.blocked_apis.get(api_name),
                'rate_limits': limits,
                'can_make_request': self.can_make_request(api_name)[0]
            }
        else:
            # All APIs
            result = {
                'apis': {},
                'summary': {
                    'total_requests_all': sum(self.usage_stats['total_requests'].values()),
                    'total_errors_all': sum(self.usage_stats['total_errors'].values()),
                    'total_rate_limits': sum(self.usage_stats['rate_limit_hits'].values())
                }
            }
            
            # Get stats for all known APIs
            for api_name in self.RATE_LIMITS.keys():
                result['apis'][api_name] = self.get_usage_stats(api_name)
            
            return result
    
    def wait_if_needed(self, api_name: str) -> float:
        """
        Wait if needed to respect rate limits
        OPTIMIZED: Only wait for critical cooldowns, skip minor ones to reduce throttling
        
        Returns:
            Time waited in seconds
        """
        can_request, reason = self.can_make_request(api_name)
        if can_request:
            return 0.0
        
        limits = self.RATE_LIMITS.get(api_name, {})
        cooldown = limits.get('cooldown_seconds', 0)
        
        # OPTIMIZATION: Only wait if cooldown is significant (> 0.5s)
        # Small cooldowns (< 0.5s) are handled by async delays, not blocking sleeps
        if cooldown < 0.5:
            return 0.0  # Skip tiny cooldowns to reduce throttling
        
        if api_name in self.last_request_time:
            time_since_last = time.time() - self.last_request_time[api_name]
            if time_since_last < cooldown:
                wait_time = cooldown - time_since_last
                # Only wait if significant (> 0.5s)
                if wait_time > 0.5:
                    time.sleep(wait_time)
                    return wait_time
        
        return 0.0


# Global instance
api_tracker = APITracker()

