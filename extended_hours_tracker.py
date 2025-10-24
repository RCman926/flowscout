"""
Extended Hours Tracker - Pre-Market and After-Hours Data
Critical for detecting overnight crashes and pumps
"""

import yfinance as yf
from typing import Dict
from datetime import datetime
import time


class ExtendedHoursTracker:
    """
    Tracks pre-market and after-hours price movements
    Essential for catching overnight selloffs and pumps
    """
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 60  # 60 seconds to avoid Yahoo rate limiting
        self.last_request_time = 0
        self.min_request_interval = 2  # Minimum 2 seconds between requests
    
    def get_extended_hours_data(self, symbol: str) -> Dict:
        """
        Get real-time extended hours data including pre-market and after-hours
        
        Returns:
            - current_price: Latest price (extended hours if available)
            - regular_close: Yesterday's regular market close
            - extended_hours_change: % change from regular close
            - is_extended_hours: Whether extended hours is active
            - extended_hours_type: 'PRE_MARKET' or 'POST_MARKET' or None
        """
        
        cache_key = f"extended_{symbol}"
        
        # Check cache (10 second cache for real-time)
        if self._check_cache(cache_key):
            return self.cache[cache_key]['data']
        
        try:
            # Throttle requests to avoid rate limiting
            current_time = time.time()
            time_since_last_request = current_time - self.last_request_time
            if time_since_last_request < self.min_request_interval:
                time.sleep(self.min_request_interval - time_since_last_request)
            
            self.last_request_time = time.time()
            
            ticker = yf.Ticker(symbol)
            
            # Get yesterday's close
            hist = ticker.history(period='2d')
            if hist.empty or len(hist) == 0:
                return self._get_empty_data(symbol)
            
            regular_close = hist['Close'].iloc[-1]
            
            # Initialize defaults
            current_price = regular_close
            extended_hours_active = False
            extended_hours_type = None
            extended_hours_change = 0
            extended_hours_volume = 0
            pre_market_price = None
            post_market_price = None
            
            # Try to get extended hours data with retry logic
            try:
                # First try fast_info (faster, less rate limiting)
                fast = ticker.fast_info
                current_price = getattr(fast, 'last_price', regular_close)
                
                # Then try full info for extended hours (with timeout)
                info = ticker.info
                
                # Check for pre-market price
                pre_market_price = info.get('preMarketPrice', None)
                pre_market_volume = info.get('preMarketVolume', 0)
                
                if pre_market_price and pre_market_price > 0:
                    current_price = pre_market_price
                    extended_hours_active = True
                    extended_hours_type = 'PRE_MARKET'
                    extended_hours_change = ((pre_market_price - regular_close) / regular_close * 100)
                    extended_hours_volume = pre_market_volume
                
                # Check for post-market price (overrides pre-market if both exist)
                post_market_price = info.get('postMarketPrice', None)
                post_market_volume = info.get('postMarketVolume', 0)
                
                if post_market_price and post_market_price > 0:
                    current_price = post_market_price
                    extended_hours_active = True
                    extended_hours_type = 'POST_MARKET'
                    extended_hours_change = ((post_market_price - regular_close) / regular_close * 100)
                    extended_hours_volume = post_market_volume
            
            except Exception as info_error:
                # If we can't get extended hours, use regular close
                print(f"Extended hours data unavailable for {symbol} (rate limited or unavailable): {info_error}")
                current_price = regular_close
            
            # Classify the move
            move_type = self._classify_extended_hours_move(extended_hours_change)
            
            data = {
                'symbol': symbol,
                'current_price': current_price,
                'regular_close': regular_close,
                'extended_hours_active': extended_hours_active,
                'extended_hours_type': extended_hours_type,
                'extended_hours_change': extended_hours_change,
                'extended_hours_volume': extended_hours_volume,
                'move_type': move_type,
                'pre_market_price': pre_market_price,
                'post_market_price': post_market_price,
                'timestamp': datetime.now().isoformat()
            }
            
            self._cache_data(cache_key, data)
            return data
            
        except Exception as e:
            print(f"Error fetching extended hours data for {symbol}: {e}")
            return self._get_empty_data(symbol)
    
    def detect_overnight_crash(self, symbol: str, threshold: float = -10.0) -> Dict:
        """
        Detect if stock crashed overnight (down >10% in extended hours)
        
        Returns:
            - is_crashing: Boolean
            - crash_severity: 'MINOR', 'MODERATE', 'SEVERE', 'CATASTROPHIC'
            - alert_message: Human-readable alert
        """
        
        data = self.get_extended_hours_data(symbol)
        
        if not data['extended_hours_active']:
            return {
                'is_crashing': False,
                'crash_severity': 'NONE',
                'alert_message': 'No extended hours trading',
                'extended_hours_change': 0
            }
        
        change = data['extended_hours_change']
        
        # Classify crash severity
        is_crashing = change <= threshold
        
        if change <= -30:
            severity = 'CATASTROPHIC'
            message = f"🔴 CATASTROPHIC CRASH: {symbol} down {change:.1f}% overnight - Major selloff"
        elif change <= -20:
            severity = 'SEVERE'
            message = f"🔴 SEVERE CRASH: {symbol} down {change:.1f}% overnight - Heavy selling"
        elif change <= -10:
            severity = 'MODERATE'
            message = f"⚠️ MODERATE CRASH: {symbol} down {change:.1f}% overnight - Significant drop"
        elif change <= -5:
            severity = 'MINOR'
            message = f"📉 MINOR PULLBACK: {symbol} down {change:.1f}% overnight"
        else:
            severity = 'NONE'
            message = f"✅ NO CRASH: {symbol} {change:+.1f}% overnight"
        
        return {
            'is_crashing': is_crashing,
            'crash_severity': severity,
            'alert_message': message,
            'extended_hours_change': change,
            'current_price': data['current_price'],
            'regular_close': data['regular_close']
        }
    
    def detect_overnight_pump(self, symbol: str, threshold: float = 10.0) -> Dict:
        """
        Detect if stock pumped overnight (up >10% in extended hours)
        """
        
        data = self.get_extended_hours_data(symbol)
        
        if not data['extended_hours_active']:
            return {
                'is_pumping': False,
                'pump_strength': 'NONE',
                'alert_message': 'No extended hours trading'
            }
        
        change = data['extended_hours_change']
        is_pumping = change >= threshold
        
        if change >= 50:
            strength = 'EXPLOSIVE'
            message = f"🚀 EXPLOSIVE PUMP: {symbol} up {change:.1f}% overnight - Possible squeeze"
        elif change >= 30:
            strength = 'VERY_STRONG'
            message = f"🔥 VERY STRONG PUMP: {symbol} up {change:.1f}% overnight"
        elif change >= 20:
            strength = 'STRONG'
            message = f"⚡ STRONG PUMP: {symbol} up {change:.1f}% overnight"
        elif change >= 10:
            strength = 'MODERATE'
            message = f"📈 MODERATE PUMP: {symbol} up {change:.1f}% overnight"
        else:
            strength = 'NONE'
            message = f"✅ NORMAL: {symbol} {change:+.1f}% overnight"
        
        return {
            'is_pumping': is_pumping,
            'pump_strength': strength,
            'alert_message': message,
            'extended_hours_change': change,
            'current_price': data['current_price'],
            'regular_close': data['regular_close']
        }
    
    def _classify_extended_hours_move(self, change: float) -> str:
        """Classify the extended hours move"""
        if change <= -20:
            return 'SEVERE_CRASH'
        elif change <= -10:
            return 'CRASH'
        elif change <= -5:
            return 'PULLBACK'
        elif change >= 20:
            return 'EXPLOSIVE_PUMP'
        elif change >= 10:
            return 'PUMP'
        elif change >= 5:
            return 'RALLY'
        else:
            return 'NORMAL'
    
    def _check_cache(self, key: str) -> bool:
        """Check if cached data is still valid"""
        if key in self.cache:
            age = time.time() - self.cache[key]['timestamp']
            return age < self.cache_duration
        return False
    
    def _cache_data(self, key: str, data: Dict):
        """Cache data with timestamp"""
        self.cache[key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    def _get_empty_data(self, symbol: str) -> Dict:
        """Return empty data structure"""
        return {
            'symbol': symbol,
            'current_price': 0,
            'regular_close': 0,
            'extended_hours_active': False,
            'extended_hours_type': None,
            'extended_hours_change': 0,
            'extended_hours_volume': 0,
            'move_type': 'UNKNOWN',
            'pre_market_price': None,
            'post_market_price': None,
            'timestamp': datetime.now().isoformat()
        }


# Global instance
extended_hours = ExtendedHoursTracker()
