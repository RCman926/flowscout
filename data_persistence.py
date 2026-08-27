"""
Data Persistence System
Saves user preferences, watchlists, and settings
"""

import json
import os
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DataPersistence:
    """
    Handles saving and loading user data:
    - Preferences (theme, notifications, etc.)
    - Watchlists (symbols to track)
    - Dashboard layout preferences
    - Alert settings
    """
    
    def __init__(self):
        self.data_file = "user_data.json"
        self.data = {}  # username -> {preferences, watchlist, layout, alerts}
        self._data_loaded = False  # Lazy loading flag
        # Don't load on init - load lazily on first use
        # self._load_data()
    
    def _load_data(self):
        """Load all user data (lazy loading)"""
        if self._data_loaded:
            return
        
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    self.data = json.load(f)
                logger.info(f"Loaded data for {len(self.data)} users")
        except Exception as e:
            logger.error(f"Error loading user data: {e}")
            self.data = {}
        
        self._data_loaded = True
    
    def _save_data(self):
        """Save all user data"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving user data: {e}")
    
    def get_user_data(self, username: str) -> Dict:
        """Get all data for a user"""
        # Lazy load data on first use
        self._load_data()
        
        if username not in self.data:
            self.data[username] = self._get_default_data()
        return self.data[username]
    
    def _get_default_data(self) -> Dict:
        """Get default user data structure"""
        return {
            'preferences': {
                'theme': 'dark',
                'notifications_enabled': True,
                'default_account_size': 10000,
                'risk_tolerance': 'MODERATE',
                'auto_trade': False
            },
            'watchlist': ['SPY'],
            'layout': {
                'show_bot_dashboard': False,
                'show_performance_dashboard': False,
                'show_trade_history': True,
                'metric_order': ['iv_percentile', 'gamma_exposure', 'most_active_strike']
            },
            'alerts': {
                'signal_alerts': True,
                'unusual_activity_alerts': True,
                'profit_target_alerts': True,
                'gamma_risk_alerts': True,
                'min_confidence': 70
            },
            'last_updated': datetime.now().isoformat()
        }
    
    def save_user_data(self, username: str, data: Dict):
        """Save user data"""
        # Lazy load data on first use
        self._load_data()
        
        self.data[username] = data
        self.data[username]['last_updated'] = datetime.now().isoformat()
        self._save_data()
    
    def update_preferences(self, username: str, preferences: Dict):
        """Update user preferences"""
        user_data = self.get_user_data(username)
        user_data['preferences'].update(preferences)
        self.save_user_data(username, user_data)
    
    def update_watchlist(self, username: str, watchlist: List[str]):
        """Update user watchlist"""
        user_data = self.get_user_data(username)
        user_data['watchlist'] = watchlist
        self.save_user_data(username, user_data)
    
    def update_layout(self, username: str, layout: Dict):
        """Update dashboard layout preferences"""
        user_data = self.get_user_data(username)
        user_data['layout'].update(layout)
        self.save_user_data(username, user_data)
    
    def update_alerts(self, username: str, alerts: Dict):
        """Update alert settings"""
        user_data = self.get_user_data(username)
        user_data['alerts'].update(alerts)
        self.save_user_data(username, user_data)


# Global instance
data_persistence = DataPersistence()

