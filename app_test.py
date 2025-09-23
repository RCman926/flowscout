import streamlit as st

st.title("🔥 WORKING - Options Trading Platform")
st.write("✅ If you can see this, Streamlit is working!")

st.header("📊 Dashboard")
st.success("🎯 Platform is LIVE and running successfully!")

col1, col2 = st.columns(2)
with col1:
    st.metric("SPY", "$587.45", "-0.4%")
with col2:
    st.metric("Volume", "1.2M", "+5%")

st.info("📈 Real-time market data loading...")
st.warning("⚡ System operational")