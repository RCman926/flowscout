"""
Enhanced Visualization Engine - Advanced charts and layouts
Free libraries: Plotly, streamlit
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class EnhancedVisualization:
    """Enhanced visualization engine for better UX"""
    
    def __init__(self):
        self.color_scheme = {
            'bullish': '#00c851',
            'bearish': '#ff4444', 
            'neutral': '#6c757d',
            'background': 'rgba(0,0,0,0)',
            'grid': 'rgba(128,128,128,0.2)',
            'text': '#ffffff'
        }
    
    def create_compact_dashboard(self, symbol, market_data, tech_data, flow_data, signal_data, prediction_data):
        """Create a compact, organized dashboard layout"""
        
        # Header with key metrics
        self._render_compact_header(symbol, market_data, signal_data, prediction_data)
        
        # Main content in tabs to reduce information overload
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Live Flow", "📈 Technical", "🎯 Signals", "🔮 Predictions"])
        
        with tab1:
            self._render_flow_dashboard(symbol, flow_data, market_data)
        
        with tab2:
            self._render_technical_dashboard(symbol, market_data, tech_data)
        
        with tab3:
            self._render_signals_dashboard(symbol, signal_data, market_data)
        
        with tab4:
            self._render_predictions_dashboard(symbol, prediction_data, market_data)
    
    def _render_compact_header(self, symbol, market_data, signal_data, prediction_data):
        """Compact header with essential metrics"""
        price = market_data.get('price', 100)
        change_pct = market_data.get('change_pct', 0)
        signal = signal_data.get('signal', 'HOLD')
        confidence = signal_data.get('confidence', 50)
        
        # Key metrics row
        col1, col2, col3, col4, col5 = st.columns([2, 1.5, 1.5, 1.5, 1.5])
        
        with col1:
            st.markdown(f"### {symbol}")
            color = "🟢" if change_pct > 0 else "🔴" if change_pct < 0 else "⚪"
            st.markdown(f"**${price:.2f}** {color} {change_pct:+.2f}%")
        
        with col2:
            signal_color = "success" if "CALL" in signal else "error" if "PUT" in signal else "info"
            if signal_color == "success":
                st.success(f"📈 {signal}")
            elif signal_color == "error":
                st.error(f"📉 {signal}")
            else:
                st.info(f"⚪ {signal}")
            st.caption(f"Confidence: {confidence}%")
        
        with col3:
            pred_score = prediction_data.get('prediction_score', 0)
            pred_signal = prediction_data.get('enhanced_signal', 'HOLD')
            if "STRONG" in pred_signal:
                st.success(f"🤖 {pred_signal.replace('_', ' ')}")
            elif "BUY" in pred_signal:
                st.warning(f"🤖 {pred_signal.replace('_', ' ')}")
            else:
                st.info(f"🤖 {pred_signal}")
            st.caption(f"ML Score: {pred_score:.2f}")
        
        with col4:
            pattern_strength = prediction_data.get('pattern_strength', 'MODERATE')
            risk_level = prediction_data.get('risk_level', 'MEDIUM')
            st.metric("Pattern", pattern_strength)
            st.caption(f"Risk: {risk_level}")
        
        with col5:
            time_horizon = prediction_data.get('time_horizon', '1-3 DTE')
            st.metric("Time Frame", time_horizon)
            st.caption(f"Updated: {datetime.now().strftime('%H:%M:%S')}")
    
    def _render_flow_dashboard(self, symbol, flow_data, market_data):
        """Enhanced options flow visualization with REAL LIVE DATA"""
        
        # Import real live scraper
        from real_live_options_scraper import real_live_scraper
        
        # Get actual live options data
        live_flow_metrics = real_live_scraper.get_live_flow_metrics(symbol)
        
        # Data source indicator
        data_source = live_flow_metrics.get('data_source', 'UNKNOWN')
        if data_source == 'LIVE_YAHOO_FINANCE':
            st.success(f"📡 LIVE DATA SOURCE: Yahoo Finance Options Chain - Updated: {live_flow_metrics['timestamp'].strftime('%H:%M:%S')}")
        else:
            st.warning("⚠️ Live data unavailable - using fallback")
        
        col1, col2 = st.columns(2)
        
        with col1:
            self._create_live_flow_gauge_chart(live_flow_metrics)
        
        with col2:
            self._create_live_volume_breakdown(live_flow_metrics)
        
        # Real-time strikes table
        st.markdown("#### 📊 LIVE Options Volume by Strike")
        self._create_live_strikes_table(live_flow_metrics)
        
        # Unusual activity alerts
        if live_flow_metrics.get('unusual_activity'):
            st.markdown("#### 🚨 Unusual Activity Detected")
            self._show_unusual_activity(live_flow_metrics['unusual_activity'])
    
    def _create_live_flow_gauge_chart(self, live_flow_metrics):
        """Create gauge chart for LIVE call/put ratio"""
        try:
            cp_ratio = live_flow_metrics.get('call_put_ratio', 1.0)
            call_volume = live_flow_metrics.get('call_volume', 0)
            put_volume = live_flow_metrics.get('put_volume', 0)
            
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=cp_ratio,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Call/Put Ratio", 'font': {'size': 16}},
                delta={'reference': 1.0, 'position': "top"},
                gauge={
                    'axis': {'range': [None, 3]},
                    'bar': {'color': self.color_scheme['bullish'] if cp_ratio > 1 else self.color_scheme['bearish']},
                    'steps': [
                        {'range': [0, 0.5], 'color': "rgba(255, 68, 68, 0.3)"},
                        {'range': [0.5, 1.5], 'color': "rgba(108, 117, 125, 0.3)"},
                        {'range': [1.5, 3], 'color': "rgba(0, 200, 81, 0.3)"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 1.0
                    }
                }
            ))
            
            fig.update_layout(
                height=250,
                margin=dict(l=20, r=20, t=40, b=20),
                paper_bgcolor=self.color_scheme['background'],
                plot_bgcolor=self.color_scheme['background']
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show actual volumes
            st.metric("Call Volume", f"{call_volume:,}")
            st.metric("Put Volume", f"{put_volume:,}")
            
        except Exception as e:
            st.error(f"Live flow gauge error: {e}")
    
    def _create_live_volume_breakdown(self, live_flow_metrics):
        """Create live volume breakdown display"""
        try:
            # Flow metrics
            total_volume = live_flow_metrics.get('total_volume', 0)
            net_flow = live_flow_metrics.get('net_flow', 0)
            flow_bias = live_flow_metrics.get('flow_bias', 'NEUTRAL')
            
            st.markdown("**Live Flow Metrics**")
            
            # Total volume
            st.metric("Total Options Volume", f"{total_volume:,}")
            
            # Net flow
            if net_flow > 0:
                st.success(f"Net Flow: +{net_flow:,} (Bullish)")
            elif net_flow < 0:
                st.error(f"Net Flow: {net_flow:,} (Bearish)")
            else:
                st.info(f"Net Flow: {net_flow:,} (Neutral)")
            
            # Flow bias
            if flow_bias == 'BULLISH':
                st.success(f"Flow Bias: {flow_bias}")
            elif flow_bias == 'BEARISH':
                st.error(f"Flow Bias: {flow_bias}")
            else:
                st.info(f"Flow Bias: {flow_bias}")
            
            # Data freshness
            timestamp = live_flow_metrics.get('timestamp', datetime.now())
            seconds_ago = (datetime.now() - timestamp).total_seconds()
            st.caption(f"Data age: {seconds_ago:.0f} seconds")
            
        except Exception as e:
            st.error(f"Volume breakdown error: {e}")
    
    def _create_live_strikes_table(self, live_flow_metrics):
        """Create table of live strikes by volume"""
        try:
            top_strikes = live_flow_metrics.get('top_strikes', [])
            
            if not top_strikes:
                st.info("No live strike data available")
                return
            
            # Convert to DataFrame
            df = pd.DataFrame(top_strikes)
            df = df.head(10)  # Top 10 strikes
            
            # Format for display
            display_df = df.copy()
            display_df['Strike'] = display_df['strike'].apply(lambda x: f"${x:.0f}")
            display_df['Volume'] = display_df['volume'].apply(lambda x: f"{x:,}")
            display_df['Type'] = display_df['type']
            display_df['DTE'] = display_df['dte']
            display_df['Price'] = display_df['last_price'].apply(lambda x: f"${x:.2f}")
            display_df['OI'] = display_df['open_interest'].apply(lambda x: f"{x:,}")
            
            # Select columns for display
            display_df = display_df[['Strike', 'Type', 'Volume', 'DTE', 'Price', 'OI']]
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
        except Exception as e:
            st.error(f"Strikes table error: {e}")
    
    def _show_unusual_activity(self, unusual_activity):
        """Show unusual options activity"""
        try:
            for activity in unusual_activity[:5]:  # Top 5
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**${activity['strike']:.0f} {activity['type']}** - {activity['reason']}")
                
                with col2:
                    st.metric("Volume", f"{activity['volume']:,}")
                
                with col3:
                    st.metric("DTE", f"{activity['dte']}")
                    
        except Exception as e:
            st.error(f"Unusual activity display error: {e}")
    
    def _create_flow_timeline_deprecated(self, flow_data):
        """Create timeline chart of flow changes"""
        try:
            # Generate sample timeline data (in real app, this would be historical)
            times = [datetime.now() - timedelta(minutes=i*5) for i in range(12, 0, -1)]
            call_flows = [np.random.randint(10000, 50000) for _ in times]
            put_flows = [np.random.randint(8000, 40000) for _ in times]
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=times,
                y=call_flows,
                mode='lines+markers',
                name='Call Flow',
                line=dict(color=self.color_scheme['bullish'], width=2),
                marker=dict(size=6)
            ))
            
            fig.add_trace(go.Scatter(
                x=times,
                y=put_flows,
                mode='lines+markers',
                name='Put Flow',
                line=dict(color=self.color_scheme['bearish'], width=2),
                marker=dict(size=6)
            ))
            
            fig.update_layout(
                title="Options Flow Timeline (Last Hour)",
                height=300,
                xaxis_title="Time",
                yaxis_title="Volume",
                legend=dict(x=0, y=1),
                margin=dict(l=20, r=20, t=40, b=20),
                paper_bgcolor=self.color_scheme['background'],
                plot_bgcolor=self.color_scheme['background'],
                xaxis=dict(showgrid=True, gridcolor=self.color_scheme['grid']),
                yaxis=dict(showgrid=True, gridcolor=self.color_scheme['grid'])
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Timeline error: {e}")
    
    def _render_technical_dashboard(self, symbol, market_data, tech_data):
        """Enhanced technical analysis dashboard"""
        # Combined technical chart
        self._create_combined_technical_chart(symbol, market_data, tech_data)
        
        # Technical indicators summary
        col1, col2 = st.columns(2)
        
        with col1:
            self._create_rsi_gauge(tech_data)
        
        with col2:
            self._create_technical_summary(tech_data)
    
    def _create_combined_technical_chart(self, symbol, market_data, tech_data):
        """Create combined price and technical indicators chart"""
        try:
            # Generate sample price data (in real app, fetch historical data)
            dates = [datetime.now() - timedelta(days=i) for i in range(20, 0, -1)]
            current_price = market_data.get('price', 100)
            prices = []
            
            for i, date in enumerate(dates):
                # Simulate price movement
                base_price = current_price * (0.98 + np.random.random() * 0.04)
                prices.append(base_price)
            
            # Add current price
            dates.append(datetime.now())
            prices.append(current_price)
            
            # Technical levels
            sma_20 = tech_data.get('sma_20', current_price)
            bb_upper = tech_data.get('bb_upper', current_price * 1.02)
            bb_lower = tech_data.get('bb_lower', current_price * 0.98)
            
            # Create subplots
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.1,
                subplot_titles=('Price & Indicators', 'RSI'),
                row_heights=[0.7, 0.3]
            )
            
            # Price line
            fig.add_trace(
                go.Scatter(x=dates, y=prices, mode='lines', name='Price',
                          line=dict(color='#FFD700', width=2)),
                row=1, col=1
            )
            
            # Bollinger Bands
            fig.add_trace(
                go.Scatter(x=dates, y=[bb_upper]*len(dates), mode='lines',
                          name='BB Upper', line=dict(color='gray', dash='dash')),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Scatter(x=dates, y=[bb_lower]*len(dates), mode='lines',
                          name='BB Lower', line=dict(color='gray', dash='dash')),
                row=1, col=1
            )
            
            # SMA 20
            fig.add_trace(
                go.Scatter(x=dates, y=[sma_20]*len(dates), mode='lines',
                          name='SMA 20', line=dict(color='orange')),
                row=1, col=1
            )
            
            # RSI
            rsi_values = [tech_data.get('rsi', 50)] * len(dates)
            fig.add_trace(
                go.Scatter(x=dates, y=rsi_values, mode='lines', name='RSI',
                          line=dict(color='purple')),
                row=2, col=1
            )
            
            # RSI levels
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
            
            fig.update_layout(
                title=f"{symbol} Technical Analysis",
                height=500,
                showlegend=True,
                paper_bgcolor=self.color_scheme['background'],
                plot_bgcolor=self.color_scheme['background']
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Technical chart error: {e}")
    
    def _create_rsi_gauge(self, tech_data):
        """Create RSI gauge indicator"""
        try:
            rsi = tech_data.get('rsi', 50)
            
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=rsi,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "RSI", 'font': {'size': 16}},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 30], 'color': "rgba(0, 200, 81, 0.3)"},  # Oversold
                        {'range': [30, 70], 'color': "rgba(108, 117, 125, 0.3)"},  # Neutral
                        {'range': [70, 100], 'color': "rgba(255, 68, 68, 0.3)"}  # Overbought
                    ]
                }
            ))
            
            fig.update_layout(
                height=200,
                margin=dict(l=20, r=20, t=40, b=20),
                paper_bgcolor=self.color_scheme['background']
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"RSI gauge error: {e}")
    
    def _create_technical_summary(self, tech_data):
        """Create technical indicators summary"""
        st.markdown("#### 📊 Technical Summary")
        
        rsi = tech_data.get('rsi', 50)
        macd = tech_data.get('macd', 0)
        macd_signal = tech_data.get('macd_signal', 0)
        
        # RSI status
        if rsi > 70:
            st.error("🔴 RSI: Overbought")
        elif rsi < 30:
            st.success("🟢 RSI: Oversold")
        else:
            st.info("⚪ RSI: Neutral")
        
        # MACD status
        if macd > macd_signal:
            st.success("🟢 MACD: Bullish")
        else:
            st.error("🔴 MACD: Bearish")
        
        # Key levels
        st.markdown("**Key Levels:**")
        st.text(f"BB Upper: ${tech_data.get('bb_upper', 0):.2f}")
        st.text(f"SMA 20:   ${tech_data.get('sma_20', 0):.2f}")
        st.text(f"BB Lower: ${tech_data.get('bb_lower', 0):.2f}")
    
    def _render_signals_dashboard(self, symbol, signal_data, market_data):
        """Enhanced signals dashboard"""
        col1, col2 = st.columns(2)
        
        with col1:
            self._create_signal_strength_chart(signal_data)
        
        with col2:
            self._create_confidence_meter(signal_data)
        
        # Signal breakdown
        self._create_signal_breakdown(signal_data)
    
    def _create_signal_strength_chart(self, signal_data):
        """Create signal strength visualization"""
        try:
            signal = signal_data.get('signal', 'HOLD')
            confidence = signal_data.get('confidence', 50)
            reasons = signal_data.get('reasons', [])
            
            # Signal strength based on reasons count and confidence
            strength = len(reasons) * (confidence / 100)
            
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=strength,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Signal Strength", 'font': {'size': 16}},
                gauge={
                    'axis': {'range': [None, 5]},
                    'bar': {'color': self.color_scheme['bullish'] if 'CALL' in signal 
                           else self.color_scheme['bearish'] if 'PUT' in signal 
                           else self.color_scheme['neutral']},
                    'steps': [
                        {'range': [0, 1], 'color': "rgba(128, 128, 128, 0.3)"},
                        {'range': [1, 3], 'color': "rgba(255, 193, 7, 0.3)"},
                        {'range': [3, 5], 'color': "rgba(40, 167, 69, 0.3)"}
                    ]
                }
            ))
            
            fig.update_layout(
                height=200,
                margin=dict(l=20, r=20, t=40, b=20),
                paper_bgcolor=self.color_scheme['background']
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Signal strength error: {e}")
    
    def _create_confidence_meter(self, signal_data):
        """Create confidence meter"""
        confidence = signal_data.get('confidence', 50)
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=confidence,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Confidence", 'font': {'size': 16}},
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': "blue"},
                'steps': [
                    {'range': [0, 50], 'color': "rgba(255, 68, 68, 0.3)"},
                    {'range': [50, 75], 'color': "rgba(255, 193, 7, 0.3)"},
                    {'range': [75, 100], 'color': "rgba(0, 200, 81, 0.3)"}
                ]
            }
        ))
        
        fig.update_layout(
            height=200,
            margin=dict(l=20, r=20, t=40, b=20),
            paper_bgcolor=self.color_scheme['background']
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _create_signal_breakdown(self, signal_data):
        """Create detailed signal breakdown"""
        st.markdown("#### 🔍 Signal Analysis")
        
        reasons = signal_data.get('reasons', [])
        if reasons:
            for i, reason in enumerate(reasons, 1):
                st.markdown(f"**{i}.** {reason}")
        else:
            st.info("No specific signals detected")
    
    def _render_predictions_dashboard(self, symbol, prediction_data, market_data):
        """Enhanced predictions dashboard"""
        col1, col2 = st.columns(2)
        
        with col1:
            self._create_prediction_radar(prediction_data)
        
        with col2:
            self._create_price_targets_chart(prediction_data, market_data)
        
        # ML insights
        self._create_ml_insights(prediction_data)
    
    def _create_prediction_radar(self, prediction_data):
        """Create radar chart for prediction factors"""
        try:
            categories = ['Pattern\nStrength', 'Volume\nConfirmation', 'Technical\nAlignment', 
                         'Flow\nMomentum', 'Risk\nLevel']
            
            # Convert prediction data to scores
            pattern_map = {'WEAK': 1, 'MODERATE': 2, 'STRONG': 3, 'VERY_STRONG': 4}
            risk_map = {'LOW': 4, 'MEDIUM': 2, 'HIGH': 1}
            
            values = [
                pattern_map.get(prediction_data.get('pattern_strength', 'MODERATE'), 2),
                min(4, prediction_data.get('confidence', 50) / 25),
                abs(prediction_data.get('prediction_score', 0)) * 4,
                min(4, abs(prediction_data.get('prediction_score', 0)) * 4),
                risk_map.get(prediction_data.get('risk_level', 'MEDIUM'), 2)
            ]
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                name='ML Prediction',
                line_color='rgb(0, 200, 81)'
            ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 4]
                    )),
                showlegend=True,
                title="ML Prediction Factors",
                height=300,
                margin=dict(l=20, r=20, t=40, b=20),
                paper_bgcolor=self.color_scheme['background']
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Radar chart error: {e}")
    
    def _create_price_targets_chart(self, prediction_data, market_data):
        """Create price targets visualization"""
        try:
            current_price = market_data.get('price', 100)
            targets = prediction_data.get('price_targets', {})
            
            target_1 = targets.get('target_1', current_price * 1.02)
            target_2 = targets.get('target_2', current_price * 1.05)
            target_3 = targets.get('target_3', current_price * 1.08)
            
            fig = go.Figure()
            
            # Current price line
            fig.add_hline(y=current_price, line_dash="solid", line_color="gold", 
                         annotation_text=f"Current: ${current_price:.2f}")
            
            # Target lines
            fig.add_hline(y=target_1, line_dash="dash", line_color="green", 
                         annotation_text=f"T1: ${target_1:.2f}")
            fig.add_hline(y=target_2, line_dash="dash", line_color="blue", 
                         annotation_text=f"T2: ${target_2:.2f}")
            fig.add_hline(y=target_3, line_dash="dash", line_color="purple", 
                         annotation_text=f"T3: ${target_3:.2f}")
            
            # Price range
            price_range = max(abs(target_3 - current_price), abs(current_price - target_1))
            y_min = current_price - price_range * 1.1
            y_max = current_price + price_range * 1.1
            
            fig.update_layout(
                title="Price Targets",
                yaxis_title="Price",
                height=300,
                yaxis=dict(range=[y_min, y_max]),
                xaxis=dict(visible=False),
                margin=dict(l=20, r=20, t=40, b=20),
                paper_bgcolor=self.color_scheme['background']
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Price targets error: {e}")
    
    def _create_ml_insights(self, prediction_data):
        """Create ML insights summary"""
        st.markdown("#### 🤖 ML Insights")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            enhanced_signal = prediction_data.get('enhanced_signal', 'HOLD')
            if 'STRONG' in enhanced_signal:
                st.success(f"🚀 {enhanced_signal.replace('_', ' ')}")
            elif 'BUY' in enhanced_signal:
                st.warning(f"📈 {enhanced_signal.replace('_', ' ')}")
            else:
                st.info(f"⚪ {enhanced_signal}")
        
        with col2:
            time_horizon = prediction_data.get('time_horizon', '1-3 DTE')
            st.metric("Optimal Timeframe", time_horizon)
        
        with col3:
            prediction_score = prediction_data.get('prediction_score', 0)
            st.metric("ML Score", f"{prediction_score:.3f}")

# Global instance
enhanced_viz = EnhancedVisualization()