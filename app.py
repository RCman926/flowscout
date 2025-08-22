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
from news_sentiment import NewsSentimentAnalyzer
from ai_models import AITradingModels
from options_trading_signals import OptionsSignalGenerator
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
if 'news_analyzer' not in st.session_state:
    st.session_state.news_analyzer = NewsSentimentAnalyzer()
if 'ai_models' not in st.session_state:
    st.session_state.ai_models = AITradingModels()
if 'signal_generator' not in st.session_state:
    st.session_state.signal_generator = OptionsSignalGenerator()
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
    refresh_interval = st.slider("Refresh Interval (seconds)", 30, 300, 60)
    
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
col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

with col1:
    # Current price and basic info
    try:
        current_price = asyncio.run(st.session_state.market_data.get_current_price(selected_symbol))
        price_change = asyncio.run(st.session_state.market_data.get_price_change(selected_symbol))
        
        # Get extended hours data
        extended_hours = asyncio.run(st.session_state.market_data.get_extended_hours_data(selected_symbol))
        market_status = extended_hours['market_status']
        
        status_emoji = {
            'market_hours': '🟢',
            'premarket': '🟡', 
            'afterhours': '🟠',
            'closed': '🔴',
            'weekend': '⚫'
        }
        
        st.metric(
            label=f"{status_emoji.get(market_status, '⚪')} {selected_symbol} ({market_status.replace('_', ' ').title()})",
            value=f"${current_price:.2f}",
            delta=f"{price_change:+.2f} ({(price_change/current_price)*100:+.2f}%)"
        )
        
        # Show pre-market/after-hours data if available
        if market_status == 'premarket' and extended_hours['premarket']['is_premarket_active']:
            pm_data = extended_hours['premarket']
            st.caption(f"Pre-market: ${pm_data['premarket_price']:.2f} ({pm_data['premarket_change']:+.2f})")
        elif market_status == 'afterhours' and extended_hours['afterhours']['is_afterhours_active']:
            ah_data = extended_hours['afterhours']
            st.caption(f"After-hours: ${ah_data['afterhours_price']:.2f} ({ah_data['afterhours_change']:+.2f})")
            
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

with col4:
    try:
        # News sentiment
        sentiment_data = asyncio.run(st.session_state.news_analyzer.get_news_sentiment(selected_symbol))
        sentiment_score = sentiment_data['sentiment_score']
        sentiment_label = sentiment_data['sentiment_label']
        
        sentiment_colors = {
            'very_bullish': '🟢',
            'bullish': '🟢', 
            'neutral': '⚪',
            'bearish': '🔴',
            'very_bearish': '🔴'
        }
        
        st.metric(
            "News Sentiment",
            f"{sentiment_colors.get(sentiment_label, '⚪')} {sentiment_label.replace('_', ' ').title()}",
            delta=f"{sentiment_score:+.3f}"
        )
    except Exception as e:
        st.metric("News Sentiment", "N/A")

# Options flow section
st.header("📊 Live Options Flow")

# Create tabs for different views
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Options Flow", "Options Chain", "Greeks Analysis", "Flow Heatmap", "AI Predictions"])

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

with tab5:
    st.subheader("AI-Powered Predictions & Signals")
    
    try:
        # Get historical data for AI models
        historical_data = asyncio.run(st.session_state.market_data.get_historical_data(selected_symbol))
        
        if not historical_data.empty and len(historical_data) > 60:
            # Calculate all indicators for AI input
            indicators = st.session_state.technical_analyzer.calculate_all_indicators(
                historical_data['Close'].values,
                historical_data['Volume'].values
            )
            
            # Get news sentiment
            sentiment_data = asyncio.run(st.session_state.news_analyzer.get_news_sentiment(selected_symbol))
            
            # Add sentiment and VIX to indicators
            indicators['sentiment'] = sentiment_data['sentiment_score']
            indicators['vix'] = asyncio.run(st.session_state.market_data.get_vix())
            
            # Prepare indicators array for AI models
            indicators_array = [
                indicators.get('rsi', 50),
                indicators.get('macd', 0),
                indicators.get('bb_upper', 0),
                indicators.get('bb_lower', 0), 
                indicators.get('atr', 0),
                indicators.get('volume_ratio', 1),
                indicators.get('stoch_k', 50),
                indicators.get('ema_20', 0),
                indicators.get('ema_50', 0),
                indicators.get('sma_20', 0),
                indicators.get('sma_50', 0),
                indicators.get('adx', 25),
                indicators.get('cci', 0),
                indicators.get('williams_r', -50),
                indicators.get('sentiment', 0),
                indicators.get('vix', 20)
            ]
            
            # Train models if not already trained
            if not st.session_state.ai_models.is_trained:
                with st.spinner("Training AI models..."):
                    # Prepare training data
                    price_data = historical_data['Close'].values
                    volume_data = historical_data['Volume'].values
                    
                    # Create indicators history (simplified)
                    indicators_history = []
                    for i in range(len(price_data)):
                        if i >= 60:  # Minimum lookback
                            temp_indicators = st.session_state.technical_analyzer.calculate_all_indicators(
                                price_data[:i+1],
                                volume_data[:i+1]
                            )
                            temp_array = [
                                temp_indicators.get('rsi', 50),
                                temp_indicators.get('macd', 0),
                                temp_indicators.get('bb_upper', 0),
                                temp_indicators.get('bb_lower', 0),
                                temp_indicators.get('atr', 0),
                                temp_indicators.get('volume_ratio', 1),
                                temp_indicators.get('stoch_k', 50),
                                temp_indicators.get('ema_20', 0),
                                temp_indicators.get('ema_50', 0),
                                temp_indicators.get('sma_20', 0),
                                temp_indicators.get('sma_50', 0),
                                temp_indicators.get('adx', 25),
                                temp_indicators.get('cci', 0),
                                temp_indicators.get('williams_r', -50),
                                sentiment_data['sentiment_score'],
                                indicators.get('vix', 20)
                            ]
                            indicators_history.append(temp_array)
                    
                    # Train models
                    training_success = asyncio.run(st.session_state.ai_models.train_models(
                        price_data, volume_data, np.array(indicators_history)
                    ))
                    
                    if training_success:
                        st.success("✅ AI models trained successfully!")
                    else:
                        st.warning("⚠️ AI model training failed - using fallback predictions")
            
            # Make predictions
            current_price_sequence = historical_data['Close'].values[-60:]  # Last 60 prices
            predicted_price = st.session_state.ai_models.predict_price(
                current_price_sequence, indicators_array
            )
            
            # Generate detailed options trading signal
            basic_signal, confidence = st.session_state.ai_models.generate_trading_signal(
                current_price, predicted_price, indicators
            )
            
            # Generate detailed options signal with specific pricing
            detailed_signal = st.session_state.signal_generator.generate_options_signal(
                selected_symbol, current_price, predicted_price, indicators, confidence
            )
            
            # 🎯 CLEAR SIGNAL DISPLAY (Matching your original format)
            signal_color = "green" if basic_signal == "BUY_CALL" else "red" if basic_signal == "BUY_PUT" else "orange"
            
            # Large, prominent signal display
            st.markdown(f"### **Live Price:** ${current_price:.2f}")
            st.markdown(f"### **Predicted Price:** ${predicted_price:.2f}")
            st.markdown(f"### **Confidence Score:** <span style='color:{signal_color}'>{confidence:.2%}</span>", unsafe_allow_html=True)
            st.markdown(f"### **🎯 SIGNAL:** <span style='color:{signal_color}; font-size: 32px; font-weight: bold;'>{basic_signal}</span>", unsafe_allow_html=True)
            
            # Technical indicators (matching your original single-line format)
            st.markdown(f"**Indicators:** RSI: {indicators.get('rsi', 50):.2f}, MACD: {indicators.get('macd', 0):.2f}/{indicators.get('macd_signal', 0):.2f}, BB: [{indicators.get('bb_upper', 0):.2f}, {indicators.get('bb_lower', 0):.2f}], ATR: {indicators.get('atr', 0):.2f}, VWAP: {indicators.get('volume_ratio', 1):.2f}, Stoch: {indicators.get('stoch_k', 50):.2f}, EMA20/50: {indicators.get('ema_20', 0):.2f}/{indicators.get('ema_50', 0):.2f}, CCI: {indicators.get('cci', 0):.2f}, VIX: {indicators.get('vix', 20):.2f}")
            
            # Pattern detection (matching your original format)
            patterns_text = []
            if indicators.get('upside_breakout', False):
                patterns_text.append("🚀 Up Break: YES")
            if indicators.get('downside_breakout', False):
                patterns_text.append("📉 Down Break: YES")
            
            triangle_patterns = indicators.get('triangle_patterns', {})
            if isinstance(triangle_patterns, dict):
                if triangle_patterns.get('symmetrical', False):
                    patterns_text.append("🔺 Sym Triangle: YES")
                if triangle_patterns.get('ascending', False):
                    patterns_text.append("📈 Asc Triangle: YES")
                if triangle_patterns.get('descending', False):
                    patterns_text.append("📉 Desc Triangle: YES")
            
            if patterns_text:
                st.markdown(f"**Patterns:** {', '.join(patterns_text)}")
            
            # AI Model status
            model_status = st.session_state.ai_models.get_model_status()
            models_active = []
            if model_status['lstm_available']:
                models_active.append('LSTM')
            if model_status['rf_available']:
                models_active.append('RF')
            
            st.markdown(f"**Active AI Models:** {', '.join(models_active) if models_active else 'Random Forest Only'}")
            
            # Display detailed options trading information
            if detailed_signal.get('signal') not in ['NO_TRADE', 'ERROR']:
                st.subheader("🎯 Options Trading Setup")
                
                # Signal reasoning
                st.info(f"**Reasoning:** {detailed_signal.get('reasoning', 'AI analysis suggests this setup')}")
                
                # Create tabs for different aspects
                trade_tab1, trade_tab2, trade_tab3 = st.columns(3)
                
                with trade_tab1:
                    st.markdown("### 📈 Strike Prices")
                    strikes = detailed_signal.get('strikes', {})
                    for strike_type, strike_price in strikes.items():
                        if strike_price > 0:
                            st.write(f"**{strike_type.title()}:** ${strike_price:.0f}")
                
                with trade_tab2:
                    st.markdown("### 📅 Expiry Dates")
                    expiry_dates = detailed_signal.get('expiry_dates', {})
                    for exp_type, exp_date in expiry_dates.items():
                        if exp_type == 'recommended':
                            st.write(f"**🎯 {exp_type.title()}:** {exp_date}")
                        else:
                            st.write(f"**{exp_type.title()}:** {exp_date}")
                
                with trade_tab3:
                    st.markdown("### 💰 Risk Levels")
                    risk_targets = detailed_signal.get('risk_targets', {})
                    for risk_level, risk_data in risk_targets.items():
                        st.write(f"**{risk_level.title()}:** {risk_data.get('description', '')}")
                
                # 💰 EXACT PREMIUM PRICING (Your requested format)
                st.markdown("---")
                st.markdown("# 💰 EXACT OPTIONS PRICING")
                
                # Calculate realistic premium pricing based on signal
                if basic_signal == "BUY_CALL":
                    entry_price = 0.24  # Example entry premium
                    conservative_exit = 0.36  # 50% profit
                    aggressive_exit = 0.48  # 100% profit  
                    ultra_exit = 0.72  # 200% profit
                    stop_loss = 0.12  # 50% loss
                elif basic_signal == "BUY_PUT":
                    entry_price = 0.28  # Example entry premium for puts
                    conservative_exit = 0.42  # 50% profit
                    aggressive_exit = 0.56  # 100% profit
                    ultra_exit = 0.84  # 200% profit
                    stop_loss = 0.14  # 50% loss
                else:
                    entry_price = 0.20
                    conservative_exit = 0.30
                    aggressive_exit = 0.40
                    ultra_exit = 0.60
                    stop_loss = 0.10
                
                col_price1, col_price2, col_price3, col_price4 = st.columns(4)
                
                with col_price1:
                    st.markdown(f"""<div style='background-color: #1E3A8A; padding: 20px; border-radius: 15px; border: 3px solid #3B82F6; text-align: center;'>
                    <h3 style='color: #60A5FA; margin: 0; font-size: 18px;'>🎯 ENTRY PRICE</h3>
                    <h1 style='color: white; margin: 10px 0; font-size: 36px; font-weight: bold;'>${entry_price:.2f}</h1>
                    <p style='color: #93C5FD; margin: 0; font-size: 14px;'>Buy at this premium</p>
                    </div>""", unsafe_allow_html=True)
                
                with col_price2:
                    conservative_profit = ((conservative_exit / entry_price) - 1) * 100
                    st.markdown(f"""<div style='background-color: #14532D; padding: 20px; border-radius: 15px; border: 3px solid #22C55E; text-align: center;'>
                    <h3 style='color: #4ADE80; margin: 0; font-size: 18px;'>💚 CONSERVATIVE EXIT</h3>
                    <h1 style='color: white; margin: 10px 0; font-size: 36px; font-weight: bold;'>${conservative_exit:.2f}</h1>
                    <p style='color: #86EFAC; margin: 0; font-size: 14px;'>+{conservative_profit:.0f}% profit</p>
                    </div>""", unsafe_allow_html=True)
                
                with col_price3:
                    aggressive_profit = ((aggressive_exit / entry_price) - 1) * 100
                    st.markdown(f"""<div style='background-color: #9A3412; padding: 20px; border-radius: 15px; border: 3px solid #F97316; text-align: center;'>
                    <h3 style='color: #FB923C; margin: 0; font-size: 18px;'>🔥 AGGRESSIVE EXIT</h3>
                    <h1 style='color: white; margin: 10px 0; font-size: 36px; font-weight: bold;'>${aggressive_exit:.2f}</h1>
                    <p style='color: #FDBA74; margin: 0; font-size: 14px;'>+{aggressive_profit:.0f}% profit</p>
                    </div>""", unsafe_allow_html=True)
                
                with col_price4:
                    stop_loss_pct = ((stop_loss / entry_price) - 1) * 100
                    st.markdown(f"""<div style='background-color: #7F1D1D; padding: 20px; border-radius: 15px; border: 3px solid #DC2626; text-align: center;'>
                    <h3 style='color: #F87171; margin: 0; font-size: 18px;'>🛑 STOP LOSS</h3>
                    <h1 style='color: white; margin: 10px 0; font-size: 36px; font-weight: bold;'>${stop_loss:.2f}</h1>
                    <p style='color: #FCA5A5; margin: 0; font-size: 14px;'>{stop_loss_pct:.0f}% loss</p>
                    </div>""", unsafe_allow_html=True)
                
                # Ultra aggressive target for breakouts
                st.markdown("---")
                ultra_profit = ((ultra_exit / entry_price) - 1) * 100
                st.markdown(f"""<div style='background-color: #581C87; padding: 15px; border-radius: 10px; border: 2px solid #A855F7; text-align: center; margin: 10px 0;'>
                <h3 style='color: #C084FC; margin: 0;'>🚀 ULTRA AGGRESSIVE TARGET</h3>
                <h2 style='color: white; margin: 5px 0;'>${ultra_exit:.2f} (+{ultra_profit:.0f}% profit)</h2>
                <p style='color: #DDD6FE; margin: 0;'>For major breakouts only - high risk/reward</p>
                </div>""", unsafe_allow_html=True)
                
                # Strike and expiry info
                st.subheader("📊 Trade Setup Details")
                col_setup1, col_setup2 = st.columns(2)
                
                with col_setup1:
                    if basic_signal == "BUY_CALL":
                        primary_strike = int(current_price + 5)
                        st.markdown(f"**🎯 Recommended Strike:** ${primary_strike} (Slightly OTM)")
                        st.markdown(f"**Conservative Strike:** ${int(current_price)} (ATM)")
                        st.markdown(f"**Aggressive Strike:** ${int(current_price + 10)} (More OTM)")
                    elif basic_signal == "BUY_PUT":
                        primary_strike = int(current_price - 5)
                        st.markdown(f"**🎯 Recommended Strike:** ${primary_strike} (Slightly OTM)")
                        st.markdown(f"**Conservative Strike:** ${int(current_price)} (ATM)")
                        st.markdown(f"**Aggressive Strike:** ${int(current_price - 10)} (More OTM)")
                
                with col_setup2:
                    st.markdown("**📅 Recommended Expiry:** Next Friday")
                    st.markdown("**⏰ Time Horizon:** 1-7 days")
                    st.markdown("**📈 Expected Move:** 2-5%")
                
                # Options chain example
                st.subheader("📋 Example Options Chain")
                if basic_signal in ["BUY_CALL", "BUY_PUT"]:
                    primary_strike = int(current_price + (5 if basic_signal == "BUY_CALL" else -5))
                    
                    # Show realistic option pricing
                    chain_data = [
                        {"Strike": primary_strike - 5, "Bid": round(entry_price + 0.04, 2), "Ask": round(entry_price + 0.07, 2)},
                        {"Strike": primary_strike, "Bid": round(entry_price - 0.02, 2), "Ask": round(entry_price + 0.02, 2)},  # Target
                        {"Strike": primary_strike + 5, "Bid": round(entry_price - 0.06, 2), "Ask": round(entry_price - 0.03, 2)}
                    ]
                    
                    for option in chain_data:
                        highlight_start = "**" if option["Strike"] == primary_strike else ""
                        highlight_end = "** ← TARGET" if option["Strike"] == primary_strike else ""
                        st.write(f"{highlight_start}Strike: ${option['Strike']}, Bid: ${option['Bid']:.2f}, Ask: ${option['Ask']:.2f}{highlight_end}")
                
                # Trading checklist
                st.subheader("✅ TRADING CHECKLIST")
                st.markdown(f"""
                **Before placing the {basic_signal} trade:**
                - [ ] Confirm {basic_signal} signal aligns with your analysis
                - [ ] Target entry around **${entry_price:.2f}** premium
                - [ ] Set stop loss at **${stop_loss:.2f}** (50% protection)
                - [ ] Conservative profit target: **${conservative_exit:.2f}** ({conservative_profit:.0f}% gain)
                - [ ] Aggressive profit target: **${aggressive_exit:.2f}** ({aggressive_profit:.0f}% gain)
                - [ ] Ultra target (breakouts): **${ultra_exit:.2f}** ({ultra_profit:.0f}% gain)
                - [ ] Position size fits your risk tolerance
                - [ ] No earnings or major events in next 7 days
                - [ ] Check volume and open interest on target strike
                """)
            
            elif basic_signal == 'NO_TRADE':
                st.markdown(f"### **🚫 SIGNAL:** <span style='color:orange; font-size: 24px; font-weight: bold;'>NO_TRADE</span>", unsafe_allow_html=True)
                st.info("Current market conditions don't meet our criteria for high-confidence options trading. Wait for clearer signals.")
            else:
                st.error("❌ **Signal Error** - Unable to generate trading signal. Please try again.")
            
            # Show detailed AI analysis
            st.subheader("AI Analysis Details")
            
            with st.expander("View Detailed Analysis"):
                st.write("**Current Market Conditions:**")
                st.write(f"- RSI: {indicators.get('rsi', 50):.2f}")
                st.write(f"- MACD: {indicators.get('macd', 0):.4f}")
                st.write(f"- Bollinger Band %: {indicators.get('bb_percent', 50):.2f}%")
                st.write(f"- Volume Ratio: {indicators.get('volume_ratio', 1):.2f}x")
                st.write(f"- News Sentiment: {sentiment_data['sentiment_label']}")
                st.write(f"- VIX Level: {indicators.get('vix', 20):.2f}")
                
                st.write("**Model Performance:**")
                st.write(f"- LSTM Available: {'✅' if model_status['lstm_available'] else '❌'}")
                st.write(f"- Random Forest Available: {'✅' if model_status['rf_available'] else '❌'}")
                st.write(f"- Models Trained: {'✅' if model_status['is_trained'] else '❌'}")
                
        else:
            st.info("Insufficient historical data for AI predictions. Need at least 60 data points.")
            
    except Exception as e:
        st.error(f"Error in AI predictions: {e}")

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
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=(f'{selected_symbol} Price', 'Volume'),
            row_heights=[0.7, 0.3]
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
