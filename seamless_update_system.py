"""
Seamless Update System for Professional Trading Platform
Eliminates page flashing by using st.empty() containers for smooth in-place updates
"""

import streamlit as st
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional
import asyncio


class SeamlessUpdateSystem:
    """
    Professional seamless update system that eliminates page flashing
    Uses st.empty() containers for smooth in-place content updates
    """
    
    def __init__(self):
        self.containers = {}
        self.last_update_times = {}
        self.update_intervals = {
            'price_data': 3,      # Price updates every 3 seconds (LIVE)
            'options_flow': 5,    # Options flow every 5 seconds (LIVE)
            'technical_data': 10, # Technical indicators every 10 seconds
            'charts': 20,         # Charts every 20 seconds
            'news': 60,           # News every 60 seconds
            'alerts': 3           # Alerts every 3 seconds (LIVE)
        }
        
        # Initialize session state for seamless data persistence
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize session state for seamless data persistence"""
        
        # Core data persistence
        if 'seamless_data' not in st.session_state:
            st.session_state.seamless_data = {}
        
        if 'seamless_containers' not in st.session_state:
            st.session_state.seamless_containers = {}
        
        if 'seamless_timestamps' not in st.session_state:
            st.session_state.seamless_timestamps = {}
        
        if 'seamless_active' not in st.session_state:
            st.session_state.seamless_active = True
        
        # Background update control
        if 'seamless_background_running' not in st.session_state:
            st.session_state.seamless_background_running = False
    
    def create_container(self, container_id: str, initial_content=None):
        """Create a seamless update container for specific content section"""
        
        if container_id not in st.session_state.seamless_containers:
            # Create empty container for seamless updates
            container = st.empty()
            st.session_state.seamless_containers[container_id] = container
            
            # Initialize with content if provided
            if initial_content is not None:
                container.markdown(initial_content)
                st.session_state.seamless_data[container_id] = initial_content
        
        return st.session_state.seamless_containers[container_id]
    
    def update_container(self, container_id: str, content, force_update: bool = False):
        """
        Update container content seamlessly without page flashing
        Only updates if content has changed or force_update is True
        """
        
        current_time = time.time()
        
        # Check if update is needed
        if not force_update:
            # Check update interval
            last_update = st.session_state.seamless_timestamps.get(container_id, 0)
            interval = self.update_intervals.get(container_id, 10)
            
            if current_time - last_update < interval:
                return False  # Too soon to update
            
            # Check if content has actually changed
            if st.session_state.seamless_data.get(container_id) == content:
                return False  # No change needed
        
        # Get or create container
        if container_id not in st.session_state.seamless_containers:
            self.create_container(container_id)
        
        container = st.session_state.seamless_containers[container_id]
        
        try:
            # Seamless update - no page flash
            if hasattr(content, '__call__'):
                # Content is a function that renders
                with container:
                    content()
            else:
                # Content is data/markup
                container.markdown(content)
            
            # Update tracking
            st.session_state.seamless_data[container_id] = content
            st.session_state.seamless_timestamps[container_id] = current_time
            
            return True  # Successfully updated
            
        except Exception as e:
            st.error(f"Seamless update error for {container_id}: {e}")
            return False
    
    def update_price_display(self, container_id: str, market_data: Dict[str, Any]):
        """Update price display seamlessly"""
        
        def render_price():
            symbol = market_data.get('symbol', 'N/A')
            price = market_data.get('price', 0.0)
            change_pct = market_data.get('change_pct', 0.0)
            
            # Professional price display
            color = "green" if change_pct >= 0 else "red"
            arrow = "▲" if change_pct >= 0 else "▼"
            
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 8px; margin: 0.5rem 0;">
                <h3 style="margin: 0; font-size: 1.5rem;">{symbol}</h3>
                <div style="font-size: 2rem; font-weight: bold; color: {color};">
                    ${price:.2f} <span style="font-size: 1.2rem;">{arrow} {change_pct:.2f}%</span>
                </div>
                <div style="font-size: 0.9rem; color: #888;">
                    App Check: {datetime.now().strftime('%H:%M:%S')}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        return self.update_container(container_id, render_price)
    
    def update_options_flow(self, container_id: str, flow_data: Dict[str, Any]):
        """Update options flow display seamlessly"""
        
        def render_flow():
            call_vol = flow_data.get('call_volume', 0)
            put_vol = flow_data.get('put_volume', 0)
            total_vol = call_vol + put_vol
            
            if total_vol > 0:
                call_pct = (call_vol / total_vol) * 100
                put_pct = (put_vol / total_vol) * 100
                
                # Professional flow display
                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 8px; margin: 0.5rem 0;">
                    <h4 style="margin: 0 0 0.5rem 0;">Options Flow</h4>
                    <div style="display: flex; justify-content: space-between;">
                        <div style="color: #00ff00;">
                            <strong>Calls: {call_pct:.1f}%</strong><br>
                            <span style="font-size: 0.9rem;">{call_vol:,} contracts</span>
                        </div>
                        <div style="color: #ff4444;">
                            <strong>Puts: {put_pct:.1f}%</strong><br>
                            <span style="font-size: 0.9rem;">{put_vol:,} contracts</span>
                        </div>
                    </div>
                    <div style="font-size: 0.8rem; color: #888; margin-top: 0.5rem;">
                        Total Volume: {total_vol:,} contracts
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("📊 Loading options flow data...")
        
        return self.update_container(container_id, render_flow)
    
    def update_technical_indicators(self, container_id: str, tech_data: Dict[str, Any]):
        """Update technical indicators seamlessly"""
        
        def render_tech():
            rsi = tech_data.get('rsi', 50)
            macd = tech_data.get('macd', 0)
            
            # Professional technical display
            rsi_color = "green" if 30 <= rsi <= 70 else "orange"
            macd_color = "green" if macd > 0 else "red"
            
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 8px; margin: 0.5rem 0;">
                <h4 style="margin: 0 0 0.5rem 0;">Technical Indicators</h4>
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <span style="color: {rsi_color}; font-weight: bold;">RSI: {rsi:.1f}</span>
                    </div>
                    <div>
                        <span style="color: {macd_color}; font-weight: bold;">MACD: {macd:.3f}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        return self.update_container(container_id, render_tech)
    
    def update_alert_feed(self, container_id: str, alerts: list):
        """Update alert feed seamlessly"""
        
        def render_alerts():
            if alerts:
                st.markdown("### 🚨 Live Alerts")
                for alert in alerts[-5:]:  # Show last 5 alerts
                    alert_time = alert.get('timestamp', datetime.now())
                    alert_msg = alert.get('message', 'Alert')
                    
                    st.markdown(f"""
                    <div style="background: rgba(255,200,0,0.1); padding: 0.5rem; border-left: 3px solid #ffc107; margin: 0.25rem 0;">
                        <strong>{alert_time.strftime('%H:%M:%S')}</strong> - {alert_msg}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("🔔 No alerts")
        
        return self.update_container(container_id, render_alerts)
    
    def start_seamless_mode(self):
        """Initialize seamless update mode"""
        st.session_state.seamless_active = True
        
        # Hide refresh indicators
        st.markdown("""
        <style>
        .stApp > header {visibility: hidden;}
        .stStatus {display: none;}
        .stSpinner {display: none;}
        [data-testid="stStatusMessage"] {display: none;}
        </style>
        """, unsafe_allow_html=True)
    
    def create_invisible_refresh_trigger(self):
        """
        Create an invisible refresh trigger that updates containers without page flashing
        Replaces streamlit-autorefresh with seamless updates
        """
        
        # Use JavaScript for background timing without page refresh
        refresh_script = """
        <script>
        // Seamless update trigger - NO page reload
        if (!window.seamlessUpdateActive) {
            window.seamlessUpdateActive = true;
            
            // Background update cycle - updates data without visible changes
            setInterval(function() {
                // Trigger Streamlit component value update for data refresh
                if (window.parent && window.parent.postMessage) {
                    window.parent.postMessage({
                        type: 'seamless_update_trigger',
                        timestamp: Date.now()
                    }, '*');
                }
            }, 3000); // 3 second intervals for live trading
            
            // Add subtle indicator (optional)
            const indicator = document.createElement('div');
            indicator.innerHTML = '🟢';
            indicator.style.position = 'fixed';
            indicator.style.top = '10px';
            indicator.style.right = '10px';
            indicator.style.fontSize = '12px';
            indicator.style.zIndex = '9999';
            indicator.style.opacity = '0.3';
            document.body.appendChild(indicator);
        }
        </script>
        """
        
        # Note: st.components.v1.html requires additional setup 
        # Using session state approach for seamless updates instead
        pass
    
    def get_should_update(self, container_id: str) -> bool:
        """Check if container should be updated based on timing"""
        current_time = time.time()
        last_update = st.session_state.seamless_timestamps.get(container_id, 0)
        interval = self.update_intervals.get(container_id, 10)
        
        return (current_time - last_update) >= interval
    
    def batch_update(self, updates: Dict[str, Any]):
        """Perform multiple seamless updates efficiently"""
        
        updated_count = 0
        
        for container_id, content in updates.items():
            if self.update_container(container_id, content):
                updated_count += 1
        
        return updated_count


# Global seamless update system
seamless_updater = SeamlessUpdateSystem()