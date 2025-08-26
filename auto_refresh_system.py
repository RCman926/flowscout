"""
Auto-Refresh System for Live Data Feeds
Ensures zero delays and continuous updates
"""

import streamlit as st
import time
import asyncio
from datetime import datetime

class AutoRefreshSystem:
    """Manages real-time updates for live trading data"""
    
    def __init__(self, refresh_interval=15):
        self.refresh_interval = refresh_interval
        self.last_update = time.time()
        
    def setup_auto_refresh(self):
        """Setup automatic refresh for live data"""
        # Initialize session state for refresh tracking
        if 'auto_refresh_enabled' not in st.session_state:
            st.session_state.auto_refresh_enabled = True
            
        if 'refresh_counter' not in st.session_state:
            st.session_state.refresh_counter = 0
            
        if 'last_refresh_time' not in st.session_state:
            st.session_state.last_refresh_time = time.time()
    
    def should_refresh(self):
        """Check if app should refresh for new data"""
        current_time = time.time()
        time_since_refresh = current_time - st.session_state.get('last_refresh_time', 0)
        
        return time_since_refresh >= self.refresh_interval
    
    def trigger_refresh(self):
        """Trigger app refresh for live data"""
        st.session_state.refresh_counter += 1
        st.session_state.last_refresh_time = time.time()
        
        # Use Streamlit's rerun for live updates
        st.rerun()
    
    def get_live_status(self):
        """Get current live status and timing"""
        current_time = time.time()
        last_refresh = st.session_state.get('last_refresh_time', current_time)
        seconds_ago = int(current_time - last_refresh)
        
        return {
            'status': 'LIVE',
            'seconds_since_update': seconds_ago,
            'next_update_in': max(0, self.refresh_interval - seconds_ago),
            'total_updates': st.session_state.get('refresh_counter', 0)
        }
    
    def add_refresh_widget(self):
        """Add refresh controls to sidebar"""
        with st.sidebar:
            st.markdown("### 🔄 Live Updates")
            
            status = self.get_live_status()
            
            # Live status indicator
            if status['seconds_since_update'] < 30:
                st.success(f"🟢 LIVE ({status['seconds_since_update']}s ago)")
            else:
                st.warning(f"🟡 DELAYED ({status['seconds_since_update']}s ago)")
            
            # Manual refresh button
            if st.button("🔄 Force Refresh Now"):
                self.trigger_refresh()
            
            # Auto-refresh toggle
            auto_enabled = st.checkbox("Auto-refresh enabled", value=True)
            st.session_state.auto_refresh_enabled = auto_enabled
            
            if auto_enabled:
                st.caption(f"Next update in {status['next_update_in']}s")
            else:
                st.caption("Manual refresh only")
            
            # Update counter
            st.caption(f"Total updates: {status['total_updates']}")
    
    def run_live_updates(self):
        """Main live update loop"""
        self.setup_auto_refresh()
        
        # Add refresh widget
        self.add_refresh_widget()
        
        # Check if refresh needed
        if (st.session_state.auto_refresh_enabled and 
            self.should_refresh()):
            self.trigger_refresh()

# Initialize auto-refresh system
auto_refresh = AutoRefreshSystem(refresh_interval=15)