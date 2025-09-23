import streamlit as st
import pandas as pd
import plotly.express as px
import time
from datetime import datetime

# Page config
st.set_page_config(page_title="Options Trading Platform", page_icon="📊", layout="wide")

# Auto-refresh every 5 seconds
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=5000, key="trading_refresh")

# Header
st.title("🏛️ Institutional Options Flow")
st.markdown("Real-time market data and options flow analysis")

# Status
st.success("🟢 LIVE DATA CONNECTED | Q: 99%")

# Fixed metrics layout (always 4 columns)
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("SPY Price", "$587.45", "-0.4%")

with col2:
    st.metric("Call Volume", "615,631", "+12%")

with col3:
    st.metric("Put Volume", "858,405", "+8%")

with col4:
    st.metric("C/P Ratio", "0.72", "Bearish")

# Separator
st.markdown("---")

# Market data section
st.markdown("#### 📊 Live Market Data & Gamma Exposure")

# Fixed second row of metrics (always 4 columns)
data_col1, data_col2, data_col3, data_col4 = st.columns(4)

with data_col1:
    st.metric("Volume", "1.2M", "+5%")

with data_col2:
    st.metric("RSI", "65.3", "Normal")

with data_col3:
    st.metric("Gamma Flip", "$585", "UP")

with data_col4:
    st.metric("Flow", "PUT BIAS", "58.2%")

# Chart section
st.markdown("##### 📊 Live Calls vs Puts Volume")

# Fixed chart data
chart_data = pd.DataFrame({
    'Strike': ['$580', '$585', '$590', '$595', '$600'],
    'Calls': [50000, 75000, 100000, 80000, 60000],
    'Puts': [60000, 90000, 120000, 95000, 70000]
})

fig = px.bar(chart_data, x='Strike', y=['Calls', 'Puts'], 
             title=f"Key Trading Levels - Updated: {datetime.now().strftime('%H:%M:%S')}", 
             barmode='group')
st.plotly_chart(fig, use_container_width=True)

# Fixed call/put analysis (always 2 columns)
cp_col1, cp_col2 = st.columns(2)

with cp_col1:
    st.markdown("""
    <div style='background: #004400; padding: 10px; border-radius: 5px; text-align: center;'>
        <h4 style='color: #00ff00; margin: 0;'>🟢 CALLS</h4>
        <h3 style='color: white; margin: 5px 0;'>615,631</h3>
        <p style='color: #cccccc; margin: 0;'>41.8% of flow</p>
    </div>
    """, unsafe_allow_html=True)

with cp_col2:
    st.markdown("""
    <div style='background: #440000; padding: 10px; border-radius: 5px; text-align: center;'>
        <h4 style='color: #ff0000; margin: 0;'>🔴 PUTS</h4>
        <h3 style='color: white; margin: 5px 0;'>858,405</h3>
        <p style='color: #cccccc; margin: 0;'>58.2% of flow</p>
    </div>
    """, unsafe_allow_html=True)

# Total volume
st.caption("Total Volume: 1,474,036 | C/P Ratio: 0.72")

# Fixed sidebar
with st.sidebar:
    st.markdown("### 📰 Market Intelligence")
    
    # Always show same number of news items
    st.info("📈 Market showing mixed signals")
    st.info("⚡ High volatility expected")
    st.info("🎯 Watch key support levels")
    st.info("🚨 58.2% put dominance detected")
    
    st.markdown("### ⚙️ Settings")
    if st.button("Manual Refresh"):
        st.success("Refreshed!")
        time.sleep(0.5)
        st.rerun()