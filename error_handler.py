"""
Error Handling System
Graceful error handling for API failures and system errors
"""

import logging
from typing import Dict, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
import traceback

logger = logging.getLogger(__name__)


class ErrorHandler:
    """
    Centralized error handling system that:
    - Tracks API failures
    - Provides fallback mechanisms
    - Logs errors gracefully
    - Prevents cascading failures
    """
    
    def __init__(self):
        self.error_history = defaultdict(lambda: deque(maxlen=100))  # error_type -> list of errors
        self.api_failures = {}  # api_name -> {count, last_failure, is_degraded}
        self.degraded_apis = set()  # APIs that are currently degraded
        self.circuit_breakers = {}  # api_name -> {failures, last_failure, state}
        self.circuit_breaker_threshold = 5  # Fail 5 times, open circuit
        self.circuit_breaker_timeout = 300  # 5 minutes before retry
        
    def handle_api_error(self, api_name: str, error: Exception, fallback: Optional[Callable] = None) -> Dict:
        """
        Handle API errors gracefully
        
        Args:
            api_name: Name of the API that failed
            error: The exception that occurred
            fallback: Optional fallback function to call
        
        Returns:
            Dict with error info and fallback result if available
        """
        error_msg = str(error)
        error_type = type(error).__name__
        
        # Log error
        logger.warning(f"API Error [{api_name}]: {error_type} - {error_msg}")
        
        # Track error
        self.error_history[api_name].append({
            'timestamp': datetime.now().isoformat(),
            'error_type': error_type,
            'error_msg': error_msg,
            'traceback': traceback.format_exc()
        })
        
        # Update API failure tracking
        if api_name not in self.api_failures:
            self.api_failures[api_name] = {
                'count': 0,
                'last_failure': None,
                'is_degraded': False
            }
        
        self.api_failures[api_name]['count'] += 1
        self.api_failures[api_name]['last_failure'] = datetime.now().isoformat()
        
        # Check circuit breaker
        if self._check_circuit_breaker(api_name):
            self.degraded_apis.add(api_name)
            self.api_failures[api_name]['is_degraded'] = True
            logger.error(f"🚨 Circuit breaker OPEN for {api_name} - too many failures")
        
        # Try fallback if provided
        fallback_result = None
        if fallback:
            try:
                logger.info(f"Attempting fallback for {api_name}...")
                fallback_result = fallback()
                logger.info(f"✅ Fallback successful for {api_name}")
            except Exception as fallback_error:
                logger.error(f"❌ Fallback also failed for {api_name}: {fallback_error}")
        
        return {
            'success': False,
            'api': api_name,
            'error': error_msg,
            'error_type': error_type,
            'fallback_used': fallback is not None,
            'fallback_result': fallback_result,
            'is_degraded': api_name in self.degraded_apis
        }
    
    def _check_circuit_breaker(self, api_name: str) -> bool:
        """Check if circuit breaker should open"""
        if api_name not in self.circuit_breakers:
            self.circuit_breakers[api_name] = {
                'failures': 0,
                'last_failure': None,
                'state': 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
            }
        
        cb = self.circuit_breakers[api_name]
        
        if cb['state'] == 'OPEN':
            # Check if timeout has passed
            if cb['last_failure']:
                last_failure = datetime.fromisoformat(cb['last_failure'])
                if (datetime.now() - last_failure).total_seconds() > self.circuit_breaker_timeout:
                    cb['state'] = 'HALF_OPEN'
                    logger.info(f"Circuit breaker HALF_OPEN for {api_name} - testing...")
                    return False
            return True
        
        # Increment failure count
        cb['failures'] += 1
        cb['last_failure'] = datetime.now().isoformat()
        
        # Open circuit if threshold reached
        if cb['failures'] >= self.circuit_breaker_threshold:
            cb['state'] = 'OPEN'
            return True
        
        return False
    
    def record_success(self, api_name: str):
        """Record successful API call (reset circuit breaker)"""
        if api_name in self.circuit_breakers:
            cb = self.circuit_breakers[api_name]
            if cb['state'] == 'HALF_OPEN':
                # Success in half-open state - close circuit
                cb['state'] = 'CLOSED'
                cb['failures'] = 0
                logger.info(f"✅ Circuit breaker CLOSED for {api_name} - recovered")
            elif cb['state'] == 'CLOSED':
                # Reset failure count on success
                cb['failures'] = max(0, cb['failures'] - 1)
        
        if api_name in self.degraded_apis:
            self.degraded_apis.remove(api_name)
            if api_name in self.api_failures:
                self.api_failures[api_name]['is_degraded'] = False
    
    def is_api_degraded(self, api_name: str) -> bool:
        """Check if API is currently degraded"""
        return api_name in self.degraded_apis
    
    def get_error_summary(self) -> Dict:
        """Get summary of recent errors"""
        summary = {
            'degraded_apis': list(self.degraded_apis),
            'api_failures': {},
            'recent_errors': {}
        }
        
        for api_name, failures in self.api_failures.items():
            summary['api_failures'][api_name] = {
                'count': failures['count'],
                'last_failure': failures['last_failure'],
                'is_degraded': failures['is_degraded']
            }
        
        # Get recent errors (last 10 per API)
        for api_name, errors in self.error_history.items():
            summary['recent_errors'][api_name] = list(errors)[-10:]
        
        return summary
    
    def safe_execute(self, func: Callable, *args, fallback: Optional[Callable] = None, 
                     error_context: str = "operation", **kwargs) -> Dict:
        """
        Safely execute a function with error handling
        
        Returns:
            Dict with success, result, and error info
        """
        try:
            result = func(*args, **kwargs)
            return {
                'success': True,
                'result': result,
                'error': None
            }
        except Exception as e:
            logger.error(f"Error in {error_context}: {e}")
            error_info = {
                'success': False,
                'result': None,
                'error': str(e),
                'error_type': type(e).__name__,
                'traceback': traceback.format_exc()
            }
            
            # Try fallback
            if fallback:
                try:
                    error_info['fallback_result'] = fallback()
                    error_info['fallback_used'] = True
                except Exception as fallback_error:
                    error_info['fallback_error'] = str(fallback_error)
            
            return error_info


# Global instance
error_handler = ErrorHandler()

