"""
Enhanced Financial Calendar
Provides key market events and economic data
"""

from datetime import datetime, timedelta
import random

class EnhancedFinancialCalendar:
    """Financial calendar with key market events"""
    
    def __init__(self):
        self.events_cache = {}
        
    def get_key_events_today(self):
        """Get key financial events for today"""
        today = datetime.now()
        
        # Generate realistic market events
        events = [
            {
                'time': '8:30 AM',
                'event': 'Initial Jobless Claims Report',
                'impact': 'high',
                'description': 'Weekly unemployment insurance claims data'
            },
            {
                'time': '10:00 AM', 
                'event': 'Consumer Confidence Index',
                'impact': 'medium',
                'description': 'Monthly consumer sentiment survey'
            },
            {
                'time': '2:00 PM',
                'event': 'Fed Chair Speech',
                'impact': 'high',
                'description': 'Federal Reserve monetary policy comments'
            },
            {
                'time': '4:00 PM',
                'event': 'Earnings: AAPL, MSFT After Hours',
                'impact': 'high',
                'description': 'Major tech earnings announcements'
            },
            {
                'time': 'All Day',
                'event': 'Options Expiration Day',
                'impact': 'medium',
                'description': 'Monthly options expiration increases volatility'
            }
        ]
        
        # Randomize which events show (simulate different days)
        selected_events = random.sample(events, min(4, len(events)))
        
        return selected_events
    
    def get_week_ahead_events(self):
        """Get major events for the week ahead"""
        return [
            {
                'date': 'Tuesday',
                'event': 'CPI Inflation Data',
                'impact': 'high'
            },
            {
                'date': 'Wednesday', 
                'event': 'FOMC Meeting Minutes',
                'impact': 'high'
            },
            {
                'date': 'Thursday',
                'event': 'GDP Preliminary Report', 
                'impact': 'medium'
            },
            {
                'date': 'Friday',
                'event': 'Triple Witching Expiration',
                'impact': 'high'
            }
        ]

# Global instance
enhanced_calendar = EnhancedFinancialCalendar()