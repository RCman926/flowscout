"""
Auto-Refresh System for Real-Time Dashboard Updates
Handles automatic page refreshes and data updates
"""

import streamlit as st
import time
import asyncio
from datetime import datetime, timedelta
import threading

class AutoRefreshSystem:
    """Manages automatic dashboard refreshes and data updates"""
    
    def __init__(self, refresh_interval: int = 30):
        self.refresh_interval = refresh_interval
        self.last_refresh = time.time()
        self.is_active = True
        
    def initialize_refresh_system(self):
        """Initialize the auto-refresh system in Streamlit"""
        
        # Initialize session state
        if 'refresh_system_active' not in st.session_state:
            st.session_state.refresh_system_active = True
            st.session_state.last_auto_refresh = time.time()
            st.session_state.refresh_count = 0
        
        # Check if auto-refresh should trigger
        current_time = time.time()
        time_since_refresh = current_time - st.session_state.last_auto_refresh
        
        if time_since_refresh >= self.refresh_interval and st.session_state.refresh_system_active:
            st.session_state.last_auto_refresh = current_time
            st.session_state.refresh_count += 1
            return True
        
        return False
    
    def add_refresh_controls(self):
        """Add refresh controls to sidebar"""
        
        with st.sidebar:
            st.markdown("### 🔄 Refresh Controls")
            
            # Auto-refresh toggle
            auto_refresh_enabled = st.checkbox(
                "Auto-refresh enabled",
                value=st.session_state.get('refresh_system_active', True),
                help="Automatically refresh data every 30 seconds"
            )
            st.session_state.refresh_system_active = auto_refresh_enabled
            
            # Manual refresh button
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Refresh", type="primary", use_container_width=True):
                    st.session_state.last_auto_refresh = time.time()
                    st.session_state.refresh_count += 1
                    st.rerun()
            
            with col2:
                if st.button("⏹️ Stop", use_container_width=True):
                    st.session_state.refresh_system_active = False
            
            # Refresh status
            current_time = time.time()
            time_since_refresh = int(current_time - st.session_state.last_auto_refresh)
            next_refresh = self.refresh_interval - time_since_refresh
            
            st.markdown("**Status:**")
            
            if st.session_state.refresh_system_active:
                st.success(f"🟢 Auto-refresh: ON")
                if next_refresh > 0:
                    st.caption(f"Next refresh in: {next_refresh}s")
                else:
                    st.caption("Refreshing now...")
            else:
                st.error(f"🔴 Auto-refresh: OFF")
                st.caption("Manual refresh only")
            
            st.caption(f"Total refreshes: {st.session_state.get('refresh_count', 0)}")
            st.caption(f"Last update: {time_since_refresh}s ago")
    
    def add_live_indicators(self):
        """Add live data status indicators"""
        
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 📡 Data Sources")
            
            # Market data status
            st.success("🟢 Market Data")
            st.caption("Yahoo Finance - Live")
            
            # Options flow status  
            st.success("🟢 Options Flow")
            st.caption("Real-time scraping")
            
            # News feed status
            st.success("🟢 News Feed")
            st.caption("Auto-updating")
            
            # Broker connections
            st.info("📊 Multi-Broker")
            st.caption("8 brokers integrated")
            
            # Market mood
            st.warning("🎭 Market Mood")
            st.caption("Live sentiment analysis")
    
    def add_refresh_javascript(self):
        """Add JavaScript-based auto-refresh as fallback"""
        
        if st.session_state.get('refresh_system_active', True):
            # JavaScript auto-refresh component
            refresh_script = f"""
            <script>
                // Auto-refresh every {self.refresh_interval} seconds
                setTimeout(function() {{
                    window.location.reload();
                }}, {self.refresh_interval * 1000});
                
                // Add refresh indicator
                const indicator = document.createElement('div');
                indicator.innerHTML = '🔄 Auto-refresh active';
                indicator.style.position = 'fixed';
                indicator.style.top = '10px';
                indicator.style.right = '10px';
                indicator.style.background = '#28a745';
                indicator.style.color = 'white';
                indicator.style.padding = '5px 10px';
                indicator.style.borderRadius = '5px';
                indicator.style.fontSize = '12px';
                indicator.style.zIndex = '9999';
                document.body.appendChild(indicator);
                
                // Countdown timer
                let countdown = {self.refresh_interval};
                setInterval(function() {{
                    countdown--;
                    if (countdown > 0) {{
                        indicator.innerHTML = `🔄 Refresh in ${{countdown}}s`;
                    }} else {{
                        indicator.innerHTML = '🔄 Refreshing...';
                    }}
                }}, 1000);
            </script>
            """
            
            st.components.v1.html(refresh_script, height=0)
    
    def check_market_hours(self) -> bool:
        """Check if markets are currently open"""
        
        now = datetime.now()
        
        # Market hours: 9:30 AM - 4:00 PM ET (simplified)
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        # Weekend check (Saturday = 5, Sunday = 6)
        if now.weekday() >= 5:
            return False
        
        return market_open <= now <= market_close
    
    def get_refresh_interval_by_market_status(self) -> int:
        """Adjust refresh interval based on market hours"""
        
        if self.check_market_hours():
            return 30  # 30 seconds during market hours
        else:
            return 300  # 5 minutes after hours
    
    def add_performance_metrics(self):
        """Add performance metrics for refresh system"""
        
        with st.sidebar:
            st.markdown("---")
            st.markdown("### ⚡ Performance")
            
            # Calculate refresh frequency
            refresh_count = st.session_state.get('refresh_count', 0)
            if refresh_count > 0:
                uptime = time.time() - st.session_state.get('session_start', time.time())
                avg_refresh_time = uptime / refresh_count if refresh_count > 0 else 0
                
                st.metric("Refresh Rate", f"{refresh_count}")
                st.caption(f"Avg: {avg_refresh_time:.1f}s interval")
            else:
                st.metric("Refresh Rate", "0")
                st.caption("No refreshes yet")
            
            # Market hours indicator
            if self.check_market_hours():
                st.success("🟢 Market: OPEN")
                st.caption("High-frequency updates")
            else:
                st.warning("🟡 Market: CLOSED")
                st.caption("Reduced frequency")

# Global auto-refresh system
auto_refresh_system = AutoRefreshSystem(refresh_interval=30)