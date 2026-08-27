"""
Market Hours Detector
Detects if market is open, pre-market, after-hours, or closed
"""

from datetime import datetime, time
from zoneinfo import ZoneInfo
from typing import Dict, Tuple

def get_market_status() -> Dict:
    """
    Get current market status
    
    Returns:
        Dict with status, session, and time info
    """
    # Get current time in Eastern Time (market timezone)
    et = ZoneInfo("America/New_York")
    now_et = datetime.now(et)
    current_time = now_et.time()
    current_date = now_et.date()
    weekday = now_et.weekday()  # 0 = Monday, 6 = Sunday
    
    # Market hours (Eastern Time)
    pre_market_start = time(4, 0)   # 4:00 AM ET
    market_open = time(9, 30)        # 9:30 AM ET
    market_close = time(16, 0)       # 4:00 PM ET
    after_hours_end = time(20, 0)    # 8:00 PM ET
    
    # Check if weekend
    if weekday >= 5:  # Saturday or Sunday
        return {
            'status': 'CLOSED',
            'session': 'WEEKEND',
            'next_open': _get_next_market_open(now_et),
            'message': 'Market is closed (Weekend)',
            'is_trading': False,
            'current_time_et': now_et.strftime('%Y-%m-%d %H:%M:%S %Z')
        }
    
    # Check time of day
    if current_time < pre_market_start:
        # Before pre-market (overnight)
        return {
            'status': 'CLOSED',
            'session': 'OVERNIGHT',
            'next_open': f"{current_date} {pre_market_start.strftime('%H:%M')} ET (Pre-Market)",
            'message': 'Market is closed (Overnight)',
            'is_trading': False,
            'current_time_et': now_et.strftime('%Y-%m-%d %H:%M:%S %Z')
        }
    elif pre_market_start <= current_time < market_open:
        # Pre-market
        return {
            'status': 'OPEN',
            'session': 'PRE_MARKET',
            'next_open': f"{current_date} {market_open.strftime('%H:%M')} ET (Regular Market)",
            'message': 'Pre-Market Trading (4:00 AM - 9:30 AM ET)',
            'is_trading': True,
            'current_time_et': now_et.strftime('%Y-%m-%d %H:%M:%S %Z')
        }
    elif market_open <= current_time < market_close:
        # Regular market hours
        return {
            'status': 'OPEN',
            'session': 'REGULAR',
            'next_open': f"{current_date} {market_close.strftime('%H:%M')} ET (Market Close)",
            'message': 'Regular Market Hours (9:30 AM - 4:00 PM ET)',
            'is_trading': True,
            'current_time_et': now_et.strftime('%Y-%m-%d %H:%M:%S %Z')
        }
    elif market_close <= current_time < after_hours_end:
        # After-hours
        return {
            'status': 'OPEN',
            'session': 'AFTER_HOURS',
            'next_open': f"{current_date} {after_hours_end.strftime('%H:%M')} ET (After-Hours End)",
            'message': 'After-Hours Trading (4:00 PM - 8:00 PM ET)',
            'is_trading': True,
            'current_time_et': now_et.strftime('%Y-%m-%d %H:%M:%S %Z')
        }
    else:
        # After after-hours (overnight)
        next_date = current_date
        if current_time >= after_hours_end:
            from datetime import timedelta
            next_date = current_date + timedelta(days=1)
        
        return {
            'status': 'CLOSED',
            'session': 'OVERNIGHT',
            'next_open': f"{next_date} {pre_market_start.strftime('%H:%M')} ET (Pre-Market)",
            'message': 'Market is closed (Overnight)',
            'is_trading': False,
            'current_time_et': now_et.strftime('%Y-%m-%d %H:%M:%S %Z')
        }

def _get_next_market_open(current_dt: datetime) -> str:
    """Calculate next market open time"""
    from datetime import timedelta
    
    # If it's Saturday, next open is Monday
    if current_dt.weekday() == 5:  # Saturday
        days_ahead = 2
    elif current_dt.weekday() == 6:  # Sunday
        days_ahead = 1
    else:
        days_ahead = 1
    
    next_date = current_dt.date() + timedelta(days=days_ahead)
    return f"{next_date} 04:00 ET (Pre-Market)"

def is_market_open() -> bool:
    """Quick check if market is open"""
    status = get_market_status()
    return status['is_trading']

def get_session_type() -> str:
    """Get current session type"""
    status = get_market_status()
    return status['session']


def session_clock() -> Dict:
    """Clock for health pills — closed is not the same as the site being down."""
    st = get_market_status()
    sess = str(st.get("session") or "UNKNOWN")
    labels = {
        "WEEKEND": "WEEKEND",
        "OVERNIGHT": "OVERNIGHT",
        "PRE_MARKET": "PREMARKET",
        "AFTER_HOURS": "AFTER HOURS",
        "REGULAR": "RTH",
    }
    return {
        "session": sess,
        "closed": sess in ("WEEKEND", "OVERNIGHT"),
        "rth": sess == "REGULAR",
        "extended": sess in ("PRE_MARKET", "AFTER_HOURS"),
        "label": labels.get(sess, sess),
        "message": st.get("message"),
        "next_open": st.get("next_open"),
        "is_trading": bool(st.get("is_trading")),
    }

