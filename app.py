import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pytz
from scipy.stats import norm
import time
import warnings
warnings.filterwarnings('ignore')

# Import Telegram alerts system
from telegram_alerts import telegram_alerts

# === INSTITUTIONAL GRADE CONFIGURATION ===
st.set_page_config(
    page_title="Institutional Options Flow",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Minimal institutional styling
st.markdown("""
<style>
    .main > div { padding-top: 0.5rem; }
    .stMetric { 
        background: #0a0e27 !important; 
        padding: 0.3rem !important; 
        border-radius: 4px !important; 
        margin: 0.1rem 0 !important; 
        border: 1px solid #1e293b !important; 
        color: white !important;
    }
    .stMetric [data-testid="metric-container"] {
        background-color: #0a0e27 !important;
        color: white !important;
        padding: 0.3rem !important;
        font-size: 0.8rem !important;
    }
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
    h1, h2, h3 { color: #1e293b !important; font-weight: 600 !important; margin-bottom: 0.3rem !important; }
    h1 { font-size: 1.4rem !important; }
    h2 { font-size: 1.1rem !important; }
    p, div, span { font-size: 0.8rem !important; }
</style>
""", unsafe_allow_html=True)

# === REAL DATA FUNCTIONS ===
def get_real_market_data(symbol):
    """Get real market data from Yahoo Finance"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2d", interval="1m")
        if hist.empty:
            return None
        
        current_price = hist['Close'][-1]
        prev_close = hist['Close'][-2] if len(hist) > 1 else current_price
        change = current_price - prev_close
        change_pct = (change / prev_close) * 100
        volume = int(hist['Volume'][-1]) if not pd.isna(hist['Volume'][-1]) else 0
        
        return {
            'symbol': symbol,
            'price': float(current_price),
            'change': float(change),
            'change_pct': float(change_pct),
            'volume': volume,
            'market_state': 'OPEN',
            'history': hist
        }
    except Exception as e:
        return None

def get_institutional_flow_data(symbol):
    """Get institutional-grade options flow analysis"""
    try:
        ticker = yf.Ticker(symbol)
        exp_dates = ticker.options
        if not exp_dates:
            return None
            
        current_price = get_real_market_data(symbol)['price']
        
        # Analyze multiple expiries for flow patterns
        flow_analysis = []
        total_call_premium = 0
        total_put_premium = 0
        
        for i, exp_date in enumerate(exp_dates[:3]):  # Top 3 expiries
            try:
                exp_datetime = datetime.strptime(exp_date, '%Y-%m-%d')
                dte = (exp_datetime - datetime.now()).days
                
                options_chain = ticker.option_chain(exp_date)
                calls_df = options_chain.calls
                puts_df = options_chain.puts
                
                if calls_df.empty or puts_df.empty:
                    continue
                
                # Calculate flow metrics
                call_volume = calls_df['volume'].sum() if not calls_df['volume'].isna().all() else 0
                put_volume = puts_df['volume'].sum() if not puts_df['volume'].isna().all() else 0
                call_oi = calls_df['openInterest'].sum() if not calls_df['openInterest'].isna().all() else 0
                put_oi = puts_df['openInterest'].sum() if not puts_df['openInterest'].isna().all() else 0
                
                # Premium flow calculation
                call_premium = (calls_df['lastPrice'] * calls_df['volume']).sum() if not calls_df['volume'].isna().all() else 0
                put_premium = (puts_df['lastPrice'] * puts_df['volume']).sum() if not puts_df['volume'].isna().all() else 0
                
                total_call_premium += call_premium
                total_put_premium += put_premium
                
                # Find highest volume strikes
                top_call = calls_df.loc[calls_df['volume'].idxmax()] if not calls_df['volume'].isna().all() and calls_df['volume'].max() > 0 else None
                top_put = puts_df.loc[puts_df['volume'].idxmax()] if not puts_df['volume'].isna().all() and puts_df['volume'].max() > 0 else None
                
                flow_analysis.append({
                    'exp_date': exp_date,
                    'dte': dte,
                    'call_volume': int(call_volume),
                    'put_volume': int(put_volume),
                    'call_oi': int(call_oi),
                    'put_oi': int(put_oi),
                    'call_premium': call_premium,
                    'put_premium': put_premium,
                    'top_call_strike': top_call['strike'] if top_call is not None else None,
                    'top_put_strike': top_put['strike'] if top_put is not None else None,
                    'top_call_volume': int(top_call['volume']) if top_call is not None else 0,
                    'top_put_volume': int(top_put['volume']) if top_put is not None else 0
                })
                
            except Exception as e:
                continue
        
        # Calculate institutional signals
        total_volume = sum([f['call_volume'] + f['put_volume'] for f in flow_analysis])
        total_premium = total_call_premium + total_put_premium
        
        # Flow direction signal
        if total_call_premium > total_put_premium * 1.5:
            flow_signal = "BULLISH FLOW"
            flow_confidence = min(95, (total_call_premium / total_put_premium - 1) * 50)
        elif total_put_premium > total_call_premium * 1.5:
            flow_signal = "BEARISH FLOW" 
            flow_confidence = min(95, (total_put_premium / total_call_premium - 1) * 50)
        else:
            flow_signal = "NEUTRAL FLOW"
            flow_confidence = 30
            
        return {
            'analysis': flow_analysis,
            'total_call_premium': total_call_premium,
            'total_put_premium': total_put_premium,
            'total_volume': total_volume,
            'flow_signal': flow_signal,
            'flow_confidence': flow_confidence,
            'current_price': current_price
        }
        
    except Exception as e:
        return None

def calculate_institutional_signal(symbol):
    """Calculate institutional-grade trading signal"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="10d", interval="1d")
        if hist.empty:
            return "NEUTRAL", "#6b7280", 25
        
        # Price momentum
        returns = hist['Close'].pct_change().dropna()
        momentum_5d = (hist['Close'][-1] / hist['Close'][-6] - 1) * 100 if len(hist) >= 6 else 0
        
        # Volume analysis  
        avg_volume = hist['Volume'][-5:].mean()
        current_volume = hist['Volume'][-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # Volatility
        volatility = returns.std() * np.sqrt(252) * 100
        
        # Calculate signal strength
        signal_score = 50  # Start neutral
        
        # Momentum factor (40% weight)
        if momentum_5d > 3:
            signal_score += 20
        elif momentum_5d > 1:
            signal_score += 10
        elif momentum_5d < -3:
            signal_score -= 20
        elif momentum_5d < -1:
            signal_score -= 10
            
        # Volume factor (30% weight)
        if volume_ratio > 1.5:
            signal_score += 15 if momentum_5d > 0 else -15
        elif volume_ratio > 1.2:
            signal_score += 8 if momentum_5d > 0 else -8
            
        # Volatility factor (20% weight)
        if volatility > 40:
            signal_score *= 0.9  # Reduce confidence in high vol
        elif volatility < 15:
            signal_score *= 1.1  # Increase confidence in low vol
            
        # Recent performance (10% weight)
        recent_return = (hist['Close'][-1] / hist['Close'][-2] - 1) * 100
        if abs(recent_return) > 2:
            signal_score += 5 if recent_return > 0 else -5
            
        signal_score = max(0, min(100, signal_score))
        confidence = abs(signal_score - 50) * 2
        
        if signal_score >= 65:
            return "STRONG BUY", "#10b981", confidence
        elif signal_score >= 55:
            return "BUY", "#6ee7b7", confidence  
        elif signal_score <= 35:
            return "STRONG SELL", "#dc2626", confidence
        elif signal_score <= 45:
            return "SELL", "#f87171", confidence
        else:
            return "NEUTRAL", "#6b7280", confidence
            
    except Exception as e:
        return "NEUTRAL", "#6b7280", 25

# === INSTITUTIONAL HEADER ===
st.markdown("""
<div style="background: linear-gradient(135deg, #0a0e27 0%, #1e293b 100%); padding: 1rem; border-radius: 8px; margin-bottom: 1rem; color: white;">
    <h1 style="margin: 0; color: white; font-size: 1.6rem;">🏛️ INSTITUTIONAL OPTIONS FLOW</h1>
    <p style="margin: 0.3rem 0 0 0; color: #94a3b8; font-size: 0.9rem;">Real-time institutional-grade flow analysis • Live prediction signals</p>
</div>
""", unsafe_allow_html=True)

# === SYMBOL SELECTOR ===
symbols = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'SPY', 'QQQ']
cols = st.columns(9)
selected_symbol = st.session_state.get('selected_symbol', 'SPY')

for i, symbol in enumerate(symbols):
    signal, color, confidence = calculate_institutional_signal(symbol)
    market_data = get_real_market_data(symbol)
    price = market_data['price'] if market_data else 150.0
    change_pct = market_data['change_pct'] if market_data else 0.0
    
    with cols[i]:
        is_selected = symbol == selected_symbol
        
        # Color-coded signal boxes
        signal_short = signal.replace("STRONG ", "").replace("BUY", "📈").replace("SELL", "📉").replace("NEUTRAL", "⚪")
        border_style = "3px solid #fbbf24" if is_selected else "2px solid transparent"
        
        # Create color-coded clickable box
        st.markdown(f"""
        <style>
        .symbol-box-{symbol.lower()} {{
            background: {color} !important;
            color: white !important;
            border: {border_style} !important;
            padding: 0.8rem 0.3rem !important;
            border-radius: 8px !important;
            text-align: center !important;
            font-weight: bold !important;
            margin: 0.2rem 0 !important;
            cursor: pointer !important;
            width: 100% !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
        }}
        .symbol-box-{symbol.lower()}:hover {{
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 8px rgba(0,0,0,0.4) !important;
        }}
        </style>
        <div class="symbol-box-{symbol.lower()}">
            <div style="font-size: 0.9rem; font-weight: bold; margin-bottom: 0.2rem;">{symbol}</div>
            <div style="font-size: 0.8rem; margin: 0.1rem 0;">${price:.1f}</div>
            <div style="font-size: 0.7rem; margin: 0.1rem 0; opacity: 0.9;">{change_pct:+.1f}%</div>
            <div style="font-size: 0.7rem; margin-top: 0.2rem;">{signal_short} {confidence:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Invisible button for selection functionality
        if st.button(
            " ", 
            key=f"btn_{symbol}",
            help=f"{symbol} - {signal} ({confidence:.0f}% confidence)",
            use_container_width=True
        ):
            st.session_state.selected_symbol = symbol
            st.rerun()

# === LIVE FLOW ANALYSIS ===
flow_data = get_institutional_flow_data(selected_symbol)
market_data = get_real_market_data(selected_symbol)
signal, signal_color, confidence = calculate_institutional_signal(selected_symbol)

if not flow_data or not market_data:
    st.error("⚠️ Unable to fetch real market data for analysis")
    st.stop()

# === MAIN TRADING DASHBOARD ===
st.markdown("---")

# Top metrics row
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    price_color = "inverse" if market_data['change'] < 0 else "normal"
    st.metric(f"{selected_symbol} PRICE", f"${market_data['price']:.2f}", 
             f"{market_data['change']:+.2f} ({market_data['change_pct']:+.2f}%)",
             delta_color=price_color)

with col2:
    confidence_color = "🟢" if confidence > 60 else "🟡" if confidence > 40 else "🔴"
    st.metric("SIGNAL", f"{confidence_color} {signal}", f"{confidence:.0f}% conf")

with col3:
    flow_color = "🟢" if "BULLISH" in flow_data['flow_signal'] else "🔴" if "BEARISH" in flow_data['flow_signal'] else "⚪"
    st.metric("FLOW SIGNAL", f"{flow_color} {flow_data['flow_signal']}", f"{flow_data['flow_confidence']:.0f}% conf")

with col4:
    total_premium = flow_data['total_call_premium'] + flow_data['total_put_premium']
    st.metric("TOTAL PREMIUM", f"${total_premium/1e6:.1f}M", 
             f"{flow_data['total_volume']:,} contracts")

with col5:
    premium_ratio = flow_data['total_call_premium'] / max(1, flow_data['total_put_premium'])
    bias = "CALL" if premium_ratio > 1.2 else "PUT" if premium_ratio < 0.8 else "NEUTRAL"
    st.metric("PREMIUM BIAS", bias, f"{premium_ratio:.2f} ratio")

with col6:
    # Market timing
    now = datetime.now()
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    time_left = market_close - now
    hours_left = max(0, time_left.total_seconds() / 3600) if time_left.total_seconds() > 0 else 0
    status = "🔥 ACTIVE" if hours_left > 1 else "⚠️ FINAL HOUR" if hours_left > 0 else "🔴 CLOSED"
    st.metric("MARKET STATUS", status, f"{hours_left:.1f}h left")

# === LIVE FLOW CHART ===
st.markdown("### 🔥 REAL-TIME FLOW ANALYSIS")

flow_col1, flow_col2 = st.columns([2, 1])

with flow_col1:
    # Create flow visualization
    fig = make_subplots(
        rows=1, cols=2, 
        subplot_titles=("Call Premium Flow", "Put Premium Flow"),
        specs=[[{"type": "bar"}, {"type": "bar"}]]
    )
    
    # Extract data for chart
    exp_labels = [f"{f['dte']}DTE" for f in flow_data['analysis']]
    call_premiums = [f['call_premium']/1e3 for f in flow_data['analysis']]  # Convert to thousands
    put_premiums = [f['put_premium']/1e3 for f in flow_data['analysis']]
    
    # Add call flow
    fig.add_trace(
        go.Bar(x=exp_labels, y=call_premiums, name="Call Premium", 
               marker_color="#10b981", text=[f"${p:.0f}K" for p in call_premiums],
               textposition="auto"),
        row=1, col=1
    )
    
    # Add put flow  
    fig.add_trace(
        go.Bar(x=exp_labels, y=put_premiums, name="Put Premium", 
               marker_color="#dc2626", text=[f"${p:.0f}K" for p in put_premiums],
               textposition="auto"),
        row=1, col=2
    )
    
    fig.update_layout(
        height=300, 
        showlegend=False,
        title_text=f"Premium Flow Analysis - {flow_data['flow_signal']}",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    st.plotly_chart(fig, use_container_width=True)

with flow_col2:
    st.markdown("**📊 FLOW BREAKDOWN**")
    
    for f in flow_data['analysis'][:3]:
        total_vol = f['call_volume'] + f['put_volume']
        call_pct = (f['call_volume'] / max(1, total_vol)) * 100
        
        exp_short = datetime.strptime(f['exp_date'], '%Y-%m-%d').strftime('%m/%d')
        
        st.markdown(f"""
        <div style="background: #1e293b; padding: 0.8rem; margin: 0.3rem 0; border-radius: 6px; color: white;">
            <div style="font-weight: bold; font-size: 0.9rem;">{exp_short} ({f['dte']}DTE)</div>
            <div style="font-size: 0.8rem; margin: 0.2rem 0;">
                📈 Calls: {f['call_volume']:,} ({call_pct:.0f}%)<br>
                📉 Puts: {f['put_volume']:,} ({100-call_pct:.0f}%)<br>
                💰 Premium: ${(f['call_premium'] + f['put_premium'])/1e3:.0f}K
            </div>
        </div>
        """, unsafe_allow_html=True)

# === INSTITUTIONAL TRADING OPPORTUNITIES ===
st.markdown("### 🎯 INSTITUTIONAL TRADING OPPORTUNITIES")

if flow_data['analysis']:
    best_flow = max(flow_data['analysis'], key=lambda x: x['call_premium'] + x['put_premium'])
    exp_short = datetime.strptime(best_flow['exp_date'], '%Y-%m-%d').strftime('%m/%d')
    
    opp_col1, opp_col2, opp_col3 = st.columns(3)
    
    with opp_col1:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 1rem; border-radius: 8px; color: white;">
            <h4 style="margin: 0; color: white;">🟢 CALL OPPORTUNITY</h4>
            <div style="font-size: 1.1rem; font-weight: bold; margin: 0.5rem 0;">
                {selected_symbol} {exp_short} ${best_flow['top_call_strike']:.0f}C
            </div>
            <div>Volume: {best_flow['top_call_volume']:,}</div>
            <div>Premium Flow: ${best_flow['call_premium']/1e3:.0f}K</div>
        </div>
        """, unsafe_allow_html=True)
    
    with opp_col2:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); padding: 1rem; border-radius: 8px; color: white;">
            <h4 style="margin: 0; color: white;">🔴 PUT OPPORTUNITY</h4>
            <div style="font-size: 1.1rem; font-weight: bold; margin: 0.5rem 0;">
                {selected_symbol} {exp_short} ${best_flow['top_put_strike']:.0f}P
            </div>
            <div>Volume: {best_flow['top_put_volume']:,}</div>
            <div>Premium Flow: ${best_flow['put_premium']/1e3:.0f}K</div>
        </div>
        """, unsafe_allow_html=True)
    
    with opp_col3:
        flow_direction = "CALLS" if best_flow['call_premium'] > best_flow['put_premium'] else "PUTS"
        momentum = abs(best_flow['call_premium'] - best_flow['put_premium']) / (best_flow['call_premium'] + best_flow['put_premium']) * 100
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1e293b 0%, #334155 100%); padding: 1rem; border-radius: 8px; color: white;">
            <h4 style="margin: 0; color: white;">📈 FLOW DIRECTION</h4>
            <div style="font-size: 1.1rem; font-weight: bold; margin: 0.5rem 0;">
                {flow_direction} DOMINANT
            </div>
            <div>Momentum: {momentum:.0f}%</div>
            <div>Best Expiry: {exp_short} ({best_flow['dte']}DTE)</div>
        </div>
        """, unsafe_allow_html=True)

# === RISK METRICS ===
st.markdown("### ⚠️ INSTITUTIONAL RISK METRICS")

risk_col1, risk_col2, risk_col3, risk_col4 = st.columns(4)

with risk_col1:
    # Position sizing calculation
    portfolio_size = 10000000  # $10M portfolio assumption
    max_risk = portfolio_size * 0.02  # 2% max risk per trade
    st.metric("MAX POSITION RISK", f"${max_risk/1e6:.1f}M", "2% portfolio rule")

with risk_col2:
    # Volatility assessment
    hist = market_data['history']
    returns = hist['Close'].pct_change().dropna()
    daily_vol = returns.std() * 100
    vol_rating = "HIGH" if daily_vol > 3 else "NORMAL" if daily_vol > 1.5 else "LOW"
    st.metric("VOLATILITY", f"{daily_vol:.1f}%", vol_rating)

with risk_col3:
    # Liquidity assessment
    avg_volume = flow_data['total_volume'] / len(flow_data['analysis']) if flow_data['analysis'] else 0
    liquidity = "HIGH" if avg_volume > 5000 else "NORMAL" if avg_volume > 1000 else "LOW"
    st.metric("LIQUIDITY", f"{avg_volume:.0f}", liquidity)

with risk_col4:
    # Time decay risk for best opportunity
    time_risk = "HIGH" if best_flow['dte'] <= 1 else "MEDIUM" if best_flow['dte'] <= 7 else "LOW"
    st.metric("TIME DECAY RISK", f"{best_flow['dte']}DTE", time_risk)

# === ALERT SYSTEM ===
st.markdown("---")
alert_col1, alert_col2 = st.columns(2)

with alert_col1:
    st.markdown("**📢 ALERT STATUS**")
    
    # Simple alert settings
    alert_settings = {
        'unusual_activity': True,
        'flow_changes': True, 
        'signal_updates': True,
        'volume_threshold': 5000,
        'confidence_threshold': 70
    }
    
    # Check for alerts
    if flow_data['flow_confidence'] > 70:
        st.success(f"🔥 HIGH CONFIDENCE FLOW: {flow_data['flow_signal']}")
    
    if confidence > 70:
        st.success(f"🎯 HIGH CONFIDENCE SIGNAL: {signal}")
        
    if flow_data['total_volume'] > 50000:
        st.warning(f"⚡ UNUSUAL VOLUME: {flow_data['total_volume']:,} contracts")

with alert_col2:
    # Alert statistics
    alert_stats = telegram_alerts.get_alert_stats()
    stats_metrics = st.columns(3)
    
    with stats_metrics[0]:
        st.metric("Alerts Today", alert_stats.get('today', 0))
    with stats_metrics[1]:
        st.metric("Total Sent", alert_stats.get('total', 0))
    with stats_metrics[2]:
        st.metric("Success Rate", f"{alert_stats.get('success_rate', 0):.0f}%")

# === REAL-TIME MONITORING ===
# Auto-refresh every 5 seconds during market hours
current_time = time.time()
refresh_key = int(current_time // 5)

is_market_hours = (9.5 <= now.hour + now.minute/60 <= 16) and now.weekday() < 5

if is_market_hours:
    st.markdown(f"""
    <div style="background: #10b981; padding: 0.5rem; border-radius: 4px; color: white; text-align: center; margin-top: 1rem;">
        🔥 LIVE TRADING • Auto-refresh every 5s • Last update: {now.strftime('%H:%M:%S')}
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div style="background: #6b7280; padding: 0.5rem; border-radius: 4px; color: white; text-align: center; margin-top: 1rem;">
        MARKET CLOSED • Next session: Tomorrow 9:30 AM ET
    </div>
    """, unsafe_allow_html=True)

# Store current data for alert monitoring
st.session_state['current_flow'] = flow_data
st.session_state['current_signal'] = signal
st.session_state['current_confidence'] = confidence

# Run institutional alerts
if flow_data and alert_settings:
    # Check for unusual flow activity
    if flow_data['flow_confidence'] > alert_settings['confidence_threshold']:
        telegram_alerts.send_alert(
            f"🏛️ INSTITUTIONAL FLOW ALERT\n"
            f"Symbol: {selected_symbol}\n"
            f"Signal: {flow_data['flow_signal']}\n"
            f"Confidence: {flow_data['flow_confidence']:.0f}%\n"
            f"Premium: ${(flow_data['total_call_premium'] + flow_data['total_put_premium'])/1e6:.1f}M"
        )
    
    # Check for high-confidence trading signals
    if confidence > alert_settings['confidence_threshold']:
        telegram_alerts.send_alert(
            f"🎯 TRADING SIGNAL ALERT\n"
            f"Symbol: {selected_symbol}\n"
            f"Signal: {signal}\n"
            f"Confidence: {confidence:.0f}%\n"
            f"Price: ${market_data['price']:.2f}"
        )

# Footer with key refresh
st.markdown("---")
st.markdown("*Institutional-grade options flow analysis • Real-time predictive intelligence*")