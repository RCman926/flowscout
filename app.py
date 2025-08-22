import streamlit as st
import pandas as pd
import numpy as np
import asyncio
import time
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf

from options_engine import OptionsEngine
from market_data import MarketDataManager
from technical_indicators import TechnicalAnalyzer
from alerts import AlertManager
from utils import format_currency, format_percentage, calculate_time_to_expiry

# Configure page
st.set_page_config(
    page_title="Professional Options Trading Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'options_engine' not in st.session_state:
    st.session_state.options_engine = OptionsEngine()
if 'market_data' not in st.session_state:
    st.session_state.market_data = MarketDataManager()
if 'technical_analyzer' not in st.session_state:
    st.session_state.technical_analyzer = TechnicalAnalyzer()
if 'alert_manager' not in st.session_state:
    st.session_state.alert_manager = AlertManager()
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now()
if 'selected_positions' not in st.session_state:
    st.session_state.selected_positions = []

# Main title and header
st.title("🏛️ Professional Options Trading Platform")
st.markdown("---")

# Sidebar for controls
with st.sidebar:
    st.header("Trading Controls")
    
    # Symbol selection
    symbols = ["SPY", "QQQ", "TSLA"]
    selected_symbol = st.selectbox("Select Symbol", symbols, index=0)
    
    # Refresh controls
    auto_refresh = st.checkbox("Auto Refresh", value=True)
    refresh_interval = st.slider("Refresh Interval (seconds)", 1, 30, 5)
    
    if st.button("🔄 Manual Refresh"):
        st.session_state.last_update = datetime.now()
        st.rerun()
    
    # Alert settings
    st.subheader("Alert Settings")
    telegram_enabled = st.checkbox("Telegram Alerts", value=False)
    if telegram_enabled:
        telegram_chat_id = st.text_input("Telegram Chat ID", placeholder="Enter your chat ID")
        if telegram_chat_id:
            st.session_state.telegram_chat_id = telegram_chat_id
    
    # Filter settings
    st.subheader("Flow Filters")
    min_volume = st.number_input("Min Volume", min_value=0, value=100)
    min_premium = st.number_input("Min Premium ($)", min_value=0.0, value=1000.0, step=100.0)
    
    unusual_activity_threshold = st.slider("Unusual Activity Threshold", 1.0, 10.0, 3.0)

# Auto-refresh logic
if auto_refresh:
    time_since_update = (datetime.now() - st.session_state.last_update).total_seconds()
    if time_since_update >= refresh_interval:
        st.session_state.last_update = datetime.now()
        st.rerun()

# Main dashboard layout
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    # Current price and basic info
    try:
        current_price = asyncio.run(st.session_state.market_data.get_current_price(selected_symbol))
        price_change = asyncio.run(st.session_state.market_data.get_price_change(selected_symbol))
        
        st.metric(
            label=f"{selected_symbol} Price",
            value=f"${current_price:.2f}",
            delta=f"{price_change:+.2f} ({(price_change/current_price)*100:+.2f}%)"
        )
    except Exception as e:
        st.error(f"Error fetching price data: {e}")
        current_price = 0

with col2:
    try:
        iv_rank = asyncio.run(st.session_state.options_engine.get_iv_rank(selected_symbol))
        st.metric("IV Rank", f"{iv_rank:.1f}%")
    except Exception as e:
        st.metric("IV Rank", "N/A")

with col3:
    try:
        vix = asyncio.run(st.session_state.market_data.get_vix())
        st.metric("VIX", f"{vix:.2f}")
    except Exception as e:
        st.metric("VIX", "N/A")

# Options flow section
st.header("📊 Live Options Flow")

# Create tabs for different views
tab1, tab2, tab3, tab4 = st.tabs(["Options Flow", "Options Chain", "Greeks Analysis", "Flow Heatmap"])

with tab1:
    st.subheader("Real-Time Options Flow")
    
    # Options flow data
    try:
        flow_data = asyncio.run(st.session_state.options_engine.get_options_flow(
            selected_symbol, 
            min_volume=min_volume,
            min_premium=min_premium
        ))
        
        if not flow_data.empty:
            # Apply unusual activity filter
            flow_data['unusual_factor'] = flow_data['volume'] / flow_data['avg_volume']
            unusual_flows = flow_data[flow_data['unusual_factor'] >= unusual_activity_threshold]
            
            # Display unusual activity alerts
            if not unusual_flows.empty:
                st.warning(f"🚨 {len(unusual_flows)} Unusual Options Activities Detected!")
                
                for _, row in unusual_flows.head(5).iterrows():
                    with st.container():
                        col_a, col_b, col_c, col_d = st.columns(4)
                        with col_a:
                            st.write(f"**{row['type']} {row['strike']}C/P**")
                        with col_b:
                            st.write(f"Vol: {row['volume']:,.0f}")
                        with col_c:
                            st.write(f"Premium: {format_currency(row['premium'])}")
                        with col_d:
                            st.write(f"Unusual: {row['unusual_factor']:.1f}x")
            
            # Display full flow table
            st.dataframe(
                flow_data[['timestamp', 'type', 'strike', 'expiry', 'volume', 'premium', 'iv', 'delta']],
                use_container_width=True
            )
            
            # Send alerts if enabled
            if telegram_enabled:
                telegram_chat_id = st.session_state.get('telegram_chat_id', '')
                if telegram_chat_id and not unusual_flows.empty:
                    for _, row in unusual_flows.head(3).iterrows():
                        alert_msg = f"🚨 Unusual {selected_symbol} {row['type']} activity:\n"
                        alert_msg += f"Strike: ${row['strike']}\n"
                        alert_msg += f"Volume: {row['volume']:,.0f} ({row['unusual_factor']:.1f}x avg)\n"
                        alert_msg += f"Premium: {format_currency(row['premium'])}"
                        
                        asyncio.run(st.session_state.alert_manager.send_telegram_alert(
                            telegram_chat_id, alert_msg
                        ))
        else:
            st.info("No significant options flow detected for the current filters.")
            
    except Exception as e:
        st.error(f"Error loading options flow data: {e}")

with tab2:
    st.subheader("Options Chain")
    
    try:
        # Get options chain
        options_chain = asyncio.run(st.session_state.options_engine.get_options_chain(selected_symbol))
        
        if not options_chain.empty:
            # Create expiry selector
            expiry_dates = sorted(options_chain['expiry'].unique())
            selected_expiry = st.selectbox("Select Expiry", expiry_dates)
            
            # Filter by selected expiry
            chain_data = options_chain[options_chain['expiry'] == selected_expiry]
            
            # Split into calls and puts
            calls = chain_data[chain_data['type'] == 'CALL']
            puts = chain_data[chain_data['type'] == 'PUT']
            
            if not calls.empty:
                calls = calls.sort_values('strike')
            if not puts.empty:
                puts = puts.sort_values('strike')
            
            # Display options chain
            col_calls, col_puts = st.columns(2)
            
            with col_calls:
                st.write("**CALLS**")
                if not calls.empty:
                    calls_display = calls[['strike', 'bid', 'ask', 'volume', 'open_interest', 'iv', 'delta', 'gamma', 'theta', 'vega']]
                    st.dataframe(calls_display, use_container_width=True)
            
            with col_puts:
                st.write("**PUTS**")
                if not puts.empty:
                    puts_display = puts[['strike', 'bid', 'ask', 'volume', 'open_interest', 'iv', 'delta', 'gamma', 'theta', 'vega']]
                    st.dataframe(puts_display, use_container_width=True)
                    
        else:
            st.info("No options chain data available.")
            
    except Exception as e:
        st.error(f"Error loading options chain: {e}")

with tab3:
    st.subheader("Greeks Analysis")
    
    try:
        # Get Greeks data
        greeks_data = asyncio.run(st.session_state.options_engine.get_portfolio_greeks(selected_symbol))
        
        # Display portfolio Greeks
        greek_col1, greek_col2, greek_col3, greek_col4 = st.columns(4)
        
        with greek_col1:
            st.metric("Portfolio Delta", f"{greeks_data.get('total_delta', 0):.2f}")
        with greek_col2:
            st.metric("Portfolio Gamma", f"{greeks_data.get('total_gamma', 0):.4f}")
        with greek_col3:
            st.metric("Portfolio Theta", f"{greeks_data.get('total_theta', 0):.2f}")
        with greek_col4:
            st.metric("Portfolio Vega", f"{greeks_data.get('total_vega', 0):.2f}")
        
        # Greeks visualization
        if 'positions' in greeks_data and greeks_data['positions']:
            positions_df = pd.DataFrame(greeks_data['positions'])
            
            # Create Greeks chart
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Delta by Strike', 'Gamma by Strike', 'Theta by Strike', 'Vega by Strike')
            )
            
            fig.add_trace(
                go.Bar(x=positions_df['strike'], y=positions_df['delta'], name='Delta'),
                row=1, col=1
            )
            fig.add_trace(
                go.Bar(x=positions_df['strike'], y=positions_df['gamma'], name='Gamma'),
                row=1, col=2
            )
            fig.add_trace(
                go.Bar(x=positions_df['strike'], y=positions_df['theta'], name='Theta'),
                row=2, col=1
            )
            fig.add_trace(
                go.Bar(x=positions_df['strike'], y=positions_df['vega'], name='Vega'),
                row=2, col=2
            )
            
            fig.update_layout(height=600, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            
    except Exception as e:
        st.error(f"Error loading Greeks analysis: {e}")

with tab4:
    st.subheader("Options Flow Heatmap")
    
    try:
        # Get heatmap data
        heatmap_data = asyncio.run(st.session_state.options_engine.get_flow_heatmap(selected_symbol))
        
        if not heatmap_data.empty:
            # Create pivot table for heatmap
            pivot_data = heatmap_data.pivot_table(
                index='strike', 
                columns='expiry', 
                values='volume', 
                fill_value=0
            )
            
            # Create heatmap
            fig = go.Figure(data=go.Heatmap(
                z=pivot_data.values,
                x=pivot_data.columns,
                y=pivot_data.index,
                colorscale='RdYlGn',
                showscale=True
            ))
            
            fig.update_layout(
                title="Options Volume Heatmap",
                xaxis_title="Expiry Date",
                yaxis_title="Strike Price",
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No heatmap data available.")
            
    except Exception as e:
        st.error(f"Error creating flow heatmap: {e}")

# Performance tracking section
st.header("📈 Performance Tracking")

# P&L tracking
try:
    pnl_data = asyncio.run(st.session_state.options_engine.calculate_portfolio_pnl(selected_symbol))
    
    pnl_col1, pnl_col2, pnl_col3 = st.columns(3)
    
    with pnl_col1:
        st.metric("Unrealized P&L", format_currency(pnl_data.get('unrealized_pnl', 0)))
    with pnl_col2:
        st.metric("Daily P&L", format_currency(pnl_data.get('daily_pnl', 0)))
    with pnl_col3:
        st.metric("Total P&L", format_currency(pnl_data.get('total_pnl', 0)))
        
except Exception as e:
    st.error(f"Error calculating P&L: {e}")

# Technical analysis section
st.header("🔍 Technical Analysis")

try:
    # Get historical data
    historical_data = asyncio.run(st.session_state.market_data.get_historical_data(selected_symbol))
    
    if not historical_data.empty:
        # Calculate technical indicators
        indicators = st.session_state.technical_analyzer.calculate_all_indicators(
            historical_data['Close'].values,
            historical_data['Volume'].values
        )
        
        # Display key indicators
        tech_col1, tech_col2, tech_col3, tech_col4 = st.columns(4)
        
        with tech_col1:
            st.metric("RSI", f"{indicators.get('rsi', 0):.2f}")
        with tech_col2:
            st.metric("MACD", f"{indicators.get('macd', 0):.4f}")
        with tech_col3:
            st.metric("Bollinger %", f"{indicators.get('bb_percent', 0):.2f}%")
        with tech_col4:
            st.metric("Volume Ratio", f"{indicators.get('volume_ratio', 0):.2f}")
        
        # Price chart with indicators
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxis=True,
            vertical_spacing=0.03,
            subplot_titles=(f'{selected_symbol} Price', 'Volume'),
            row_width=[0.7, 0.3]
        )
        
        # Price candlestick
        fig.add_trace(
            go.Candlestick(
                x=historical_data.index,
                open=historical_data['Open'],
                high=historical_data['High'],
                low=historical_data['Low'],
                close=historical_data['Close'],
                name='Price'
            ),
            row=1, col=1
        )
        
        # Volume bars
        fig.add_trace(
            go.Bar(
                x=historical_data.index,
                y=historical_data['Volume'],
                name='Volume',
                marker_color='lightblue'
            ),
            row=2, col=1
        )
        
        fig.update_layout(height=600, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        
except Exception as e:
    st.error(f"Error in technical analysis: {e}")

# Footer with last update time
st.markdown("---")
st.caption(f"Last updated: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}")
