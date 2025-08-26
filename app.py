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
    
    # === INSTITUTIONAL OPTIONS CHAIN ANALYSIS ===
    st.markdown("#### 📋 Live Options Chain - Institutional Grade")
    
    try:
        ticker = yf.Ticker(selected_symbol)
        current_price = market_data.get('price', 0)
        
        if current_price > 0 and ticker.options:
            exp_dates = ticker.options[:3]  # Top 3 expiries
            
            for exp_date in exp_dates:
                exp_dt = datetime.strptime(exp_date, '%Y-%m-%d').date()
                dte = (exp_dt - datetime.now().date()).days
                
                if dte >= 0:
                    st.markdown(f"**{selected_symbol} @ ${current_price:.2f} - {exp_date} ({dte}DTE)**")
                    
                    try:
                        options_chain = ticker.option_chain(exp_date)
                        calls_df = options_chain.calls
                        puts_df = options_chain.puts
                        
                        if not calls_df.empty and not puts_df.empty:
                            # Filter for liquid options around current price
                            calls_filtered = calls_df[
                                (calls_df['strike'] >= current_price - 20) & 
                                (calls_df['strike'] <= current_price + 30) &
                                (calls_df['volume'] > 5) &
                                (calls_df['bid'] > 0.01) &
                                (calls_df['ask'] > calls_df['bid'])
                            ].sort_values('volume', ascending=False).head(8)
                            
                            puts_filtered = puts_df[
                                (puts_df['strike'] >= current_price - 30) & 
                                (puts_df['strike'] <= current_price + 20) &
                                (puts_df['volume'] > 5) &
                                (puts_df['bid'] > 0.01) &
                                (puts_df['ask'] > puts_df['bid'])
                            ].sort_values('volume', ascending=False).head(8)
                            
                            # Display calls and puts side by side
                            chain_cols = st.columns(2)
                            
                            with chain_cols[0]:
                                st.markdown("**🟢 CALLS - TOP VOLUME**")
                                if not calls_filtered.empty:
                                    for _, call in calls_filtered.iterrows():
                                        strike = call['strike']
                                        volume = int(call['volume'])
                                        oi = int(call['openInterest'])
                                        bid = call['bid']
                                        ask = call['ask']
                                        mid = (bid + ask) / 2
                                        
                                        # Calculate moneyness
                                        moneyness = (strike - current_price) / current_price * 100
                                        
                                        # Color code by moneyness
                                        if abs(moneyness) < 2:  # ATM
                                            color = "🔥"
                                        elif moneyness > 0:  # OTM
                                            color = "📈"
                                        else:  # ITM
                                            color = "💰"
                                        
                                        premium_flow = volume * mid * 100
                                        
                                        st.markdown(f"""
                                        <div style='background: rgba(34, 197, 94, 0.1); padding: 0.3rem; border-radius: 3px; margin: 0.2rem 0;'>
                                        {color} **${strike:.0f}** | Vol: {volume:,} | OI: {oi:,}<br>
                                        Bid: ${bid:.2f} | Ask: ${ask:.2f} | Mid: **${mid:.2f}**<br>
                                        Premium Flow: **${premium_flow:,.0f}** | {moneyness:+.1f}%
                                        </div>
                                        """, unsafe_allow_html=True)
                                else:
                                    st.info("No liquid calls found")
                            
                            with chain_cols[1]:
                                st.markdown("**🔴 PUTS - TOP VOLUME**")
                                if not puts_filtered.empty:
                                    for _, put in puts_filtered.iterrows():
                                        strike = put['strike']
                                        volume = int(put['volume'])
                                        oi = int(put['openInterest'])
                                        bid = put['bid']
                                        ask = put['ask']
                                        mid = (bid + ask) / 2
                                        
                                        # Calculate moneyness
                                        moneyness = (current_price - strike) / current_price * 100
                                        
                                        # Color code by moneyness
                                        if abs(moneyness) < 2:  # ATM
                                            color = "🔥"
                                        elif moneyness > 0:  # ITM
                                            color = "💰"
                                        else:  # OTM
                                            color = "📉"
                                        
                                        premium_flow = volume * mid * 100
                                        
                                        st.markdown(f"""
                                        <div style='background: rgba(239, 68, 68, 0.1); padding: 0.3rem; border-radius: 3px; margin: 0.2rem 0;'>
                                        {color} **${strike:.0f}** | Vol: {volume:,} | OI: {oi:,}<br>
                                        Bid: ${bid:.2f} | Ask: ${ask:.2f} | Mid: **${mid:.2f}**<br>
                                        Premium Flow: **${premium_flow:,.0f}** | {moneyness:+.1f}%
                                        </div>
                                        """, unsafe_allow_html=True)
                                else:
                                    st.info("No liquid puts found")
                            
                            st.markdown("---")
                    except Exception as e:
                        st.warning(f"Chain data unavailable for {exp_date}")
        else:
            st.error("Options chain data unavailable")
    except Exception as e:
        st.error("Unable to load institutional options data")
    
    # === INSTITUTIONAL EXECUTION PLAN ===
    st.markdown("#### 🎯 Institutional Execution Plan")
    
    # Calculate sophisticated trading levels
    current_price = market_data['price']
    rsi = tech_data['rsi']
    bb_upper = tech_data['bb_upper']
    bb_lower = tech_data['bb_lower']
    volume_ratio = market_data['volume'] / market_data.get('avg_volume', 1)
    
    # Advanced signal analysis
    signal = signal_data['signal']
    confidence = signal_data['confidence']
    reasons = signal_data.get('reasons', [])
    
    exec_cols = st.columns([1, 1, 1])
    
    with exec_cols[0]:
        st.markdown("**📈 CALL EXECUTION PLAN**")
        
        if 'BUY CALLS' in signal or (rsi < 40 and current_price < bb_lower * 1.01):
            # Bullish setup
            entry_price = current_price * 1.005  # Slight premium for entry
            stop_loss = current_price * 0.985   # 1.5% stop
            target_1 = current_price * 1.02     # 2% target
            target_2 = current_price * 1.035    # 3.5% target
            target_3 = min(bb_upper, current_price * 1.05)  # 5% or BB upper
            
            st.markdown(f"""
            <div style='background: rgba(34, 197, 94, 0.1); padding: 0.5rem; border-radius: 5px;'>
            <strong>🟢 BULLISH SETUP</strong><br>
            Entry: ${entry_price:.2f}+<br>
            Stop: ${stop_loss:.2f}<br>
            T1: ${target_1:.2f} | T2: ${target_2:.2f}<br>
            T3: ${target_3:.2f} (Max Target)<br>
            Risk/Reward: 1:{((target_1 - entry_price) / (entry_price - stop_loss)):.1f}
            </div>
            """, unsafe_allow_html=True)
            
            # Suggest specific call strikes
            if ticker.options:
                try:
                    near_exp = ticker.options[0]
                    chain = ticker.option_chain(near_exp)
                    calls = chain.calls
                    
                    # Find ATM and slightly OTM calls
                    atm_calls = calls[
                        (calls['strike'] >= current_price - 5) & 
                        (calls['strike'] <= current_price + 15) &
                        (calls['volume'] > 0) &
                        (calls['bid'] > 0.01)
                    ].sort_values('volume', ascending=False).head(3)
                    
                    if not atm_calls.empty:
                        st.caption("**Recommended Strikes:**")
                        for _, call in atm_calls.iterrows():
                            strike = call['strike']
                            mid_price = (call['bid'] + call['ask']) / 2
                            delta = (strike - current_price) / current_price * 100
                            st.caption(f"${strike:.0f} Strike: ${mid_price:.2f} ({delta:+.1f}%)")
                except Exception:
                    pass
        else:
            st.info("No bullish setup identified")
    
    with exec_cols[1]:
        st.markdown("**📉 PUT EXECUTION PLAN**")
        
        if 'BUY PUTS' in signal or (rsi > 60 and current_price > bb_upper * 0.99):
            # Bearish setup
            entry_price = current_price * 0.995  # Slight discount for entry
            stop_loss = current_price * 1.015    # 1.5% stop
            target_1 = current_price * 0.98      # 2% target
            target_2 = current_price * 0.965     # 3.5% target
            target_3 = max(bb_lower, current_price * 0.95)  # 5% or BB lower
            
            st.markdown(f"""
            <div style='background: rgba(239, 68, 68, 0.1); padding: 0.5rem; border-radius: 5px;'>
            <strong>🔴 BEARISH SETUP</strong><br>
            Entry: ${entry_price:.2f}-<br>
            Stop: ${stop_loss:.2f}<br>
            T1: ${target_1:.2f} | T2: ${target_2:.2f}<br>
            T3: ${target_3:.2f} (Max Target)<br>
            Risk/Reward: 1:{((entry_price - target_1) / (stop_loss - entry_price)):.1f}
            </div>
            """, unsafe_allow_html=True)
            
            # Suggest specific put strikes
            if ticker.options:
                try:
                    near_exp = ticker.options[0]
                    chain = ticker.option_chain(near_exp)
                    puts = chain.puts
                    
                    # Find ATM and slightly OTM puts
                    atm_puts = puts[
                        (puts['strike'] >= current_price - 15) & 
                        (puts['strike'] <= current_price + 5) &
                        (puts['volume'] > 0) &
                        (puts['bid'] > 0.01)
                    ].sort_values('volume', ascending=False).head(3)
                    
                    if not atm_puts.empty:
                        st.caption("**Recommended Strikes:**")
                        for _, put in atm_puts.iterrows():
                            strike = put['strike']
                            mid_price = (put['bid'] + put['ask']) / 2
                            delta = (current_price - strike) / current_price * 100
                            st.caption(f"${strike:.0f} Strike: ${mid_price:.2f} ({delta:+.1f}%)")
                except Exception:
                    pass
        else:
            st.info("No bearish setup identified")
    
    with exec_cols[2]:
        st.markdown("**⚪ RISK MANAGEMENT**")
        
        # Calculate position sizing based on volatility
        daily_range = abs(market_data['change_pct'])
        vol_regime = "HIGH" if daily_range > 2 else "NORMAL" if daily_range > 0.5 else "LOW"
        
        if vol_regime == "HIGH":
            position_size = "SMALL (0.5-1%)"
            max_risk = "2% of portfolio"
        elif vol_regime == "NORMAL":
            position_size = "MEDIUM (1-2%)"
            max_risk = "3% of portfolio"
        else:
            position_size = "LARGE (2-3%)"
            max_risk = "5% of portfolio"
        
        st.markdown(f"""
        <div style='background: rgba(107, 114, 128, 0.1); padding: 0.5rem; border-radius: 5px;'>
        <strong>Vol Regime: {vol_regime}</strong><br>
        Position Size: {position_size}<br>
        Max Risk: {max_risk}<br>
        Volume Confirmation: {'✓' if volume_ratio > 1.2 else '✗'}<br>
        Trend Alignment: {'✓' if current_price > tech_data['sma_20'] else '✗'}
        </div>
        """, unsafe_allow_html=True)
        
        # Institutional confidence meter
        institutional_score = 0
        if volume_ratio > 1.5: institutional_score += 25
        if total_volume > 100000: institutional_score += 25
        if confidence > 70: institutional_score += 25
        if len(reasons) >= 3: institutional_score += 25
        
        if institutional_score >= 75:
            st.success(f"🏛️ Institutional Grade: {institutional_score}%")
        elif institutional_score >= 50:
            st.warning(f"🏛️ Institutional Grade: {institutional_score}%")
        else:
            st.error(f"🏛️ Institutional Grade: {institutional_score}%")
    
    # === FINAL TRADING RECOMMENDATION ===
    st.markdown("#### 🏆 Final Recommendation")
    
    recommendation_cols = st.columns([2, 1])
    
    with recommendation_cols[0]:
        if confidence > 70 and institutional_score >= 75:
            if 'BUY CALLS' in signal:
                st.success("🚀 STRONG BUY CALLS - Ken Griffin would approve this setup")
            elif 'BUY PUTS' in signal:
                st.error("🚀 STRONG BUY PUTS - Ken Griffin would approve this setup")
            else:
                st.info("⚪ HOLD - Wait for better setup")
        elif confidence > 60:
            if 'BUY CALLS' in signal:
                st.warning("📈 MODERATE BUY CALLS - Proceed with caution")
            elif 'BUY PUTS' in signal:
                st.warning("📉 MODERATE BUY PUTS - Proceed with caution")
            else:
                st.info("⚪ HOLD - Insufficient conviction")
        else:
            st.info("⚪ NO TRADE - Market conditions unclear")
        
        st.caption(f"Conviction: {confidence}% | Reasons: {', '.join(reasons)}")
    
    with recommendation_cols[1]:
        # Key metrics for decision
        st.metric("Conviction", f"{confidence}%", 
                 "High" if confidence > 70 else "Medium" if confidence > 50 else "Low")
        st.metric("Institutional Score", f"{institutional_score}%",
                 "Elite" if institutional_score >= 75 else "Good" if institutional_score >= 50 else "Poor")

# Run the app
if __name__ == "__main__":
    main()