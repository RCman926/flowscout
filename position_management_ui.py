"""
POSITION MANAGEMENT USER INTERFACE
Add new positions and view P&L in real-time
"""

import streamlit as st
import asyncio
from position_tracker import position_tracker
from live_news_engine import live_news_engine


def render_position_management_section():
    """Render the position management interface"""
    st.markdown("### 📊 POSITION MANAGEMENT")
    
    tab1, tab2, tab3 = st.tabs(["Add Position", "Current Positions", "Live News"])
    
    with tab1:
        render_add_position_form()
    
    with tab2:
        render_current_positions()
    
    with tab3:
        render_live_news_feed()


def render_add_position_form():
    """Form to add new positions"""
    st.markdown("**Add New Position**")
    
    position_type = st.selectbox("Position Type", ["Options", "Stock"])
    symbol = st.text_input("Symbol", value="AAPL", max_chars=10)
    
    if position_type == "Options":
        col1, col2 = st.columns(2)
        
        with col1:
            option_type = st.selectbox("Option Type", ["CALL", "PUT"])
            strike = st.number_input("Strike Price", min_value=1.0, value=150.0, step=1.0)
        
        with col2:
            expiry = st.date_input("Expiry Date")
            quantity = st.number_input("Quantity", min_value=1, value=1, step=1)
        
        entry_price = st.number_input("Entry Price", min_value=0.01, value=2.50, step=0.01)
        
        if st.button("Add Options Position", type="primary"):
            try:
                position_tracker.add_options_position(
                    symbol=symbol.upper(),
                    strike=strike,
                    expiry=expiry.isoformat(),
                    option_type=option_type,
                    quantity=quantity,
                    entry_price=entry_price
                )
                st.success(f"✅ Added {quantity} {symbol} {strike} {option_type} @ ${entry_price}")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error adding position: {e}")
    
    else:  # Stock position
        col1, col2 = st.columns(2)
        
        with col1:
            quantity = st.number_input("Quantity", value=100, step=1)
        
        with col2:
            entry_price = st.number_input("Entry Price", min_value=0.01, value=150.0, step=0.01)
        
        if st.button("Add Stock Position", type="primary"):
            try:
                position_tracker.add_stock_position(
                    symbol=symbol.upper(),
                    quantity=quantity,
                    entry_price=entry_price
                )
                st.success(f"✅ Added {quantity} shares of {symbol} @ ${entry_price}")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error adding position: {e}")


def render_current_positions():
    """Display current positions with real-time P&L"""
    st.markdown("**Current Positions**")
    
    try:
        # Update positions
        asyncio.run(position_tracker.update_all_positions())
        
        # Stock positions
        if position_tracker.positions["stocks"]:
            st.markdown("**📈 Stock Positions:**")
            
            for symbol, position in position_tracker.positions["stocks"].items():
                pnl = position.get("unrealized_pnl", 0)
                pnl_color = "🟢" if pnl >= 0 else "🔴"
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.write(f"**{symbol}**")
                with col2:
                    st.write(f"{position['quantity']} shares @ ${position['entry_price']:.2f}")
                with col3:
                    st.write(f"Current: ${position.get('current_price', position['entry_price']):.2f}")
                with col4:
                    st.write(f"{pnl_color} ${pnl:.2f}")
        
        # Options positions
        if position_tracker.positions["options"]:
            st.markdown("**⚡ Options Positions:**")
            
            for position_id, position in position_tracker.positions["options"].items():
                pnl = position.get("unrealized_pnl", 0)
                pnl_color = "🟢" if pnl >= 0 else "🔴"
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.write(f"**{position['symbol']}**")
                with col2:
                    st.write(f"{position['quantity']} {position['strike']} {position['type']}")
                with col3:
                    st.write(f"Current: ${position.get('current_price', position['entry_price']):.2f}")
                with col4:
                    st.write(f"{pnl_color} ${pnl:.2f}")
                
                # Display Greeks
                if position.get('delta'):
                    st.caption(f"Δ: {position['delta']:.3f} | Θ: {position['theta']:.4f} | Vega: {position['vega']:.3f}")
        
        if not position_tracker.positions["stocks"] and not position_tracker.positions["options"]:
            st.info("No positions found. Add your first position above!")
            
    except Exception as e:
        st.error(f"Error loading positions: {e}")


def render_live_news_feed():
    """Display live news sentiment for selected symbols"""
    st.markdown("**📰 Live News Intelligence**")
    
    # Symbol selector
    symbols = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "SPY", "QQQ"]
    selected_symbols = st.multiselect("Select Symbols for News Analysis", symbols, default=["AAPL"])
    
    if selected_symbols:
        for symbol in selected_symbols:
            with st.expander(f"📊 {symbol} News Sentiment", expanded=len(selected_symbols) == 1):
                try:
                    # Get news sentiment
                    news_data = asyncio.run(live_news_engine.get_comprehensive_news_sentiment(symbol))
                    
                    # Display sentiment metrics
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        sentiment_emoji = "🟢" if news_data['sentiment_score'] > 0.1 else "🔴" if news_data['sentiment_score'] < -0.1 else "🟡"
                        st.metric("Sentiment", f"{sentiment_emoji} {news_data['sentiment_label']}")
                    
                    with col2:
                        st.metric("Confidence", f"{news_data['confidence']:.1%}")
                    
                    with col3:
                        st.metric("Market Impact", news_data['market_impact'])
                    
                    # Display key headlines
                    if news_data.get('top_headlines'):
                        st.markdown("**📋 Key Headlines:**")
                        for i, headline in enumerate(news_data['top_headlines'][:3]):
                            st.markdown(f"• {headline.get('headline', 'No title')}")
                    
                    # Display key themes
                    if news_data.get('key_themes'):
                        st.markdown(f"**🔍 Key Themes:** {', '.join(news_data['key_themes'][:5])}")
                    
                    # Data sources
                    if news_data.get('sources_used'):
                        st.caption(f"Sources: {', '.join(news_data['sources_used'])}")
                    
                except Exception as e:
                    st.error(f"Error loading news for {symbol}: {e}")
    else:
        st.info("Select symbols to view live news sentiment analysis")


def render_portfolio_analytics():
    """Advanced portfolio analytics section"""
    st.markdown("### 📈 PORTFOLIO ANALYTICS")
    
    try:
        portfolio = position_tracker.get_portfolio_summary()
        
        if portfolio['total_positions'] > 0:
            # Risk metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total P&L", f"${portfolio['total_pnl']:,.2f}")
            
            with col2:
                st.metric("Net Delta", f"{portfolio['net_delta']:.3f}")
            
            with col3:
                st.metric("Daily Theta", f"${portfolio['net_theta']:.2f}")
            
            with col4:
                st.metric("Vega Exposure", f"{portfolio['net_vega']:.1f}")
            
            # Position breakdown
            st.markdown("**Position Breakdown:**")
            st.write(f"• **{portfolio['stock_positions']}** stock positions")
            st.write(f"• **{portfolio['options_positions']}** options positions")
            
        else:
            st.info("Add positions to see portfolio analytics")
            
    except Exception as e:
        st.error(f"Error loading portfolio analytics: {e}")