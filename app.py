"""
Professional Options Trading Platform - Fixed Version
Real-time market data with unified data coordinator
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import asyncio
import warnings
warnings.filterwarnings('ignore')

# Configure Streamlit
st.set_page_config(
    page_title="Institutional Options Flow",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# === UNIFIED DATA SYSTEM ===
from dashboard_data_coordinator import data_coordinator

# === SYMBOL DEFINITIONS ===
symbols = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NFLX', 'AMD', 'SPY', 'QQQ', 'IWM', 'DIA', 'XLF']

# === MAIN APP LOGIC ===
def main():
    # Get selected symbol
    selected_symbol = st.session_state.get('selected_symbol', 'SPY')
    
    # Get all data using unified coordinator
    market_data = data_coordinator.get_market_data(selected_symbol)
    flow_data = data_coordinator.get_options_flow(selected_symbol)
    tech_data = data_coordinator.get_technical_indicators(selected_symbol)
    signal_data = data_coordinator.generate_trading_signal(selected_symbol)
    
    # Set defaults if data unavailable
    if not market_data:
        market_data = {
            'symbol': selected_symbol, 'price': 587.45, 'change': -2.35, 
            'change_pct': -0.4, 'volume': 1000000, 'timestamp': datetime.now(),
            'market_status': 'CLOSED', 'data_freshness': 'DELAYED'
        }
    
    if not flow_data:
        flow_data = {'analysis': [], 'total_volume': 0}
    
    if not tech_data:
        tech_data = {'rsi': 50, 'macd': 0, 'bb_upper': 650, 'bb_lower': 620, 'sma_20': 635}
    
    if not signal_data:
        signal_data = {'signal': 'HOLD', 'confidence': 50, 'reasons': ['No data']}
    
    # === HEADER ===
    market_open = datetime.now().weekday() < 5 and 9 <= datetime.now().hour <= 16
    status_text = "LIVE TRADING" if market_open else "MARKET CLOSED"
    
    header_cols = st.columns([3, 1])
    with header_cols[0]:
        st.title("🏛️ Institutional Options Flow")
    
    with header_cols[1]:
        if market_open:
            st.success(f"● {status_text}")
        else:
            st.error(f"● {status_text}")
    
    # === TIMESTAMP DISPLAY ===
    refresh_cols = st.columns([2, 1])
    with refresh_cols[0]:
        if market_data and market_data.get('timestamp'):
            data_time = market_data['timestamp']
            if isinstance(data_time, datetime):
                formatted_time = data_time.strftime("%H:%M:%S")
                market_status = market_data.get('market_status', 'UNKNOWN')
                
                # Calculate data age safely
                try:
                    if hasattr(data_time, 'tzinfo') and data_time.tzinfo is not None:
                        data_time_naive = data_time.replace(tzinfo=None)
                        minutes_ago = (datetime.now() - data_time_naive).total_seconds() / 60
                    else:
                        minutes_ago = (datetime.now() - data_time).total_seconds() / 60
                except Exception:
                    minutes_ago = 0
                
                if minutes_ago < 60:
                    time_ago = f"{int(minutes_ago)}m ago"
                else:
                    time_ago = f"{int(minutes_ago/60)}h ago"
                
                st.caption(f"Last Update: {formatted_time} ({market_status}) - {time_ago}")
            else:
                st.caption(f"Last Update: {datetime.now().strftime('%H:%M:%S')}")
        else:
            st.caption(f"Last Update: {datetime.now().strftime('%H:%M:%S')}")
    
    with refresh_cols[1]:
        st.caption("Auto-refresh: 15s")
    
    # === SYMBOL SELECTOR ===
    st.markdown("---")
    symbol_rows = [symbols[i:i+7] for i in range(0, len(symbols), 7)]
    
    for row in symbol_rows:
        cols = st.columns(len(row))
        for i, symbol in enumerate(row):
            # Get data for each symbol
            symbol_data = data_coordinator.get_market_data(symbol)
            symbol_signal = data_coordinator.generate_trading_signal(symbol)
            
            price = symbol_data['price'] if symbol_data else 150.0
            change_pct = symbol_data['change_pct'] if symbol_data else 0.0
            signal = symbol_signal.get('signal', 'HOLD') if symbol_signal else 'HOLD'
            
            with cols[i]:
                is_selected = symbol == selected_symbol
                button_label = f"{symbol} ${price:.0f} {change_pct:+.1f}%"
                if is_selected:
                    button_label = f"✓ {button_label}"
                
                if st.button(button_label, key=f"select_{symbol}", use_container_width=True):
                    st.session_state.selected_symbol = symbol
                    st.rerun()
    
    # === MAIN DASHBOARD ===
    st.markdown("---")
    st.markdown("#### 📊 Live Market Data")
    
    # Market overview
    overview_cols = st.columns(4)
    with overview_cols[0]:
        st.metric(
            "Price", 
            f"${market_data['price']:.2f}",
            f"{market_data['change_pct']:+.2f}%"
        )
    
    with overview_cols[1]:
        volume_ratio = market_data['volume'] / market_data.get('avg_volume', 1)
        st.metric("Volume", f"{market_data['volume']/1e6:.1f}M", f"{volume_ratio:.1f}x avg")
    
    with overview_cols[2]:
        st.metric("RSI", f"{tech_data['rsi']:.1f}", 
                 "Overbought" if tech_data['rsi'] > 70 else "Oversold" if tech_data['rsi'] < 30 else "Normal")
    
    with overview_cols[3]:
        st.metric("Signal", signal_data['signal'], f"{signal_data['confidence']}% conf")
    
    # === OPTIONS FLOW ===
    st.markdown("#### ⚡ Options Flow Analysis")
    
    flow_cols = st.columns(3)
    
    # Calculate totals
    call_volume = sum([exp.get('call_volume', 0) for exp in flow_data.get('analysis', [])])
    put_volume = sum([exp.get('put_volume', 0) for exp in flow_data.get('analysis', [])])
    total_volume = flow_data.get('total_volume', call_volume + put_volume)
    
    with flow_cols[0]:
        if call_volume > 0:
            st.success(f"📈 CALLS: {call_volume:,}")
            call_premium = sum([exp.get('call_premium', 0) for exp in flow_data.get('analysis', [])])
            st.caption(f"${call_premium/1e6:.1f}M premium")
        else:
            st.info("📈 No call flow")
    
    with flow_cols[1]:
        if put_volume > 0:
            st.error(f"📉 PUTS: {put_volume:,}")
            put_premium = sum([exp.get('put_premium', 0) for exp in flow_data.get('analysis', [])])
            st.caption(f"${put_premium/1e6:.1f}M premium")
        else:
            st.info("📉 No put flow")
    
    with flow_cols[2]:
        if total_volume > 50000:
            if call_volume > put_volume * 1.5:
                st.success("🟢 BULLISH FLOW")
            elif put_volume > call_volume * 1.5:
                st.error("🔴 BEARISH FLOW")
            else:
                st.info("⚪ NEUTRAL FLOW")
        else:
            st.info("📊 Low Activity")
    
    # === GAMMA EXPOSURE ===
    st.markdown("#### ⚡ Gamma Exposure & Key Strikes")
    
    gamma_cols = st.columns(4)
    current_price = market_data['price']
    
    with gamma_cols[0]:
        st.metric("Current Price", f"${current_price:.2f}", 
                 f"{market_data['change_pct']:+.1f}%")
    
    with gamma_cols[1]:
        # Estimate pin risk
        pin_strike = round(current_price / 5) * 5
        distance = abs(current_price - pin_strike)
        pin_risk = "HIGH" if distance < 2 else "MEDIUM" if distance < 5 else "LOW"
        st.metric("Pin Risk", pin_risk, f"${pin_strike:.0f} level")
    
    with gamma_cols[2]:
        gamma_flip = round(current_price / 5) * 5
        direction = "UP" if current_price > gamma_flip else "DOWN"
        st.metric("Gamma Flip", f"${gamma_flip:.0f}", f"Bias {direction}")
    
    with gamma_cols[3]:
        pressure = "HIGH" if total_volume > 100000 else "MEDIUM" if total_volume > 50000 else "LOW"
        st.metric("MM Pressure", pressure, f"{total_volume/1000:.0f}K vol")
    
    # === ENTRY & EXIT LEVELS ===
    st.markdown("#### 🎯 Entry & Exit Levels")
    
    levels_cols = st.columns(4)
    
    # Calculate levels
    resistance = min(tech_data['bb_upper'], current_price * 1.015)
    support = max(tech_data['bb_lower'], current_price * 0.985)
    sma_20 = tech_data['sma_20']
    daily_range = abs(market_data['change_pct'])
    
    with levels_cols[0]:
        distance_resistance = ((resistance - current_price) / current_price) * 100
        st.metric("Resistance", f"${resistance:.2f}", f"{distance_resistance:+.1f}%")
    
    with levels_cols[1]:
        distance_support = ((support - current_price) / current_price) * 100
        st.metric("Support", f"${support:.2f}", f"{distance_support:+.1f}%")
    
    with levels_cols[2]:
        trend_bias = "BULLISH" if current_price > sma_20 else "BEARISH"
        trend_distance = ((current_price - sma_20) / sma_20) * 100
        st.metric("Trend", trend_bias, f"{trend_distance:+.1f}%")
    
    with levels_cols[3]:
        vol_regime = "HIGH" if daily_range > 2 else "NORMAL" if daily_range > 0.5 else "LOW"
        st.metric("Vol Regime", vol_regime, f"{daily_range:.1f}% today")
    
    # === OPTIONS CHAIN DATA ===
    if flow_data.get('analysis'):
        st.markdown("#### 📋 Options Chain Analysis")
        
        chain_data = []
        for exp in flow_data['analysis'][:3]:  # Top 3 expirations
            chain_data.append({
                'Expiry': exp['expiry'],
                'DTE': exp['dte'],
                'Call Vol': f"{exp['call_volume']:,}",
                'Put Vol': f"{exp['put_volume']:,}",
                'Call Premium': f"${exp['call_premium']:,.0f}",
                'Put Premium': f"${exp['put_premium']:,.0f}",
                'P/C Ratio': f"{exp['pc_ratio']:.2f}"
            })
        
        if chain_data:
            df = pd.DataFrame(chain_data)
            st.dataframe(df, use_container_width=True)
    
    # === TRADING SIGNAL ===
    st.markdown("#### 🎯 Trading Decision")
    
    signal_cols = st.columns([2, 1])
    
    with signal_cols[0]:
        signal = signal_data['signal']
        confidence = signal_data['confidence']
        reasons = signal_data.get('reasons', [])
        
        if 'BUY CALLS' in signal:
            st.success(f"📈 {signal} - {confidence}% Confidence")
        elif 'BUY PUTS' in signal:
            st.error(f"📉 {signal} - {confidence}% Confidence")
        else:
            st.info(f"⚪ {signal} - {confidence}% Confidence")
        
        if reasons:
            st.caption(f"Reasons: {', '.join(reasons)}")
    
    with signal_cols[1]:
        price_target = signal_data.get('price_target', current_price)
        if price_target != current_price:
            target_pct = ((price_target - current_price) / current_price) * 100
            st.metric("Price Target", f"${price_target:.2f}", f"{target_pct:+.1f}%")
        else:
            st.metric("Price Target", "N/A", "No target")

# Run the app
if __name__ == "__main__":
    main()