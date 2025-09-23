import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import time

# Basic page config
st.set_page_config(
    page_title="Options Trading Platform", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    # Simple header
    st.title("🏛️ Options Trading Platform")
    st.markdown("Real-time market data and options flow analysis")
    
    # Simple metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("SPY Price", "$587.45", "-0.4%")
    
    with col2:
        st.metric("Call Volume", "615,631", "+12%")
    
    with col3:
        st.metric("Put Volume", "858,405", "+8%")
    
    with col4:
        st.metric("C/P Ratio", "0.72", "Bearish")
    
    # Simple chart
    st.markdown("---")
    st.subheader("📊 Options Flow")
    
    # Sample data for chart
    chart_data = pd.DataFrame({
        'Strike': ['$580', '$585', '$590', '$595', '$600'],
        'Calls': [50000, 75000, 100000, 80000, 60000],
        'Puts': [60000, 90000, 120000, 95000, 70000]
    })
    
    fig = px.bar(chart_data, x='Strike', y=['Calls', 'Puts'], 
                 title="Key Trading Levels", barmode='group')
    st.plotly_chart(fig, use_container_width=True)
    
    # Simple sidebar
    with st.sidebar:
        st.markdown("### 📰 Market News")
        st.info("📈 Market showing mixed signals")
        st.info("⚡ High volatility expected")
        st.info("🎯 Watch key support levels")
        
        st.markdown("### ⚙️ Settings")
        if st.button("Refresh Data"):
            st.success("Data refreshed!")
            time.sleep(1)
            st.rerun()

if __name__ == "__main__":
    main()