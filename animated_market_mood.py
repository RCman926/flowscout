"""
Animated Market Mood Indicator
Real-time animated visualization of market sentiment and momentum
"""

import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import time
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

class MarketMoodIndicator:
    """Animated market mood visualization system"""
    
    def __init__(self):
        self.mood_history = []
        self.animation_frame = 0
        self.colors = {
            'extreme_fear': '#8B0000',
            'fear': '#FF4500', 
            'neutral': '#FFD700',
            'greed': '#32CD32',
            'extreme_greed': '#228B22'
        }
        
    def calculate_market_mood(self, market_data: dict, flow_data: dict, sentiment_data: dict) -> dict:
        """Calculate overall market mood from multiple indicators"""
        
        # Get key metrics
        rsi = market_data.get('rsi', 50)
        volume_ratio = flow_data.get('volume_ratio', 1.0)
        call_put_ratio = flow_data.get('call_put_ratio', 1.0)
        sentiment_score = sentiment_data.get('overall_score', 0)
        vix_level = market_data.get('vix', 20)
        
        # Calculate individual mood components
        components = {
            'technical_mood': self._calculate_technical_mood(rsi, market_data),
            'flow_mood': self._calculate_flow_mood(call_put_ratio, volume_ratio),
            'sentiment_mood': self._calculate_sentiment_mood(sentiment_score),
            'volatility_mood': self._calculate_volatility_mood(vix_level),
            'momentum_mood': self._calculate_momentum_mood(market_data)
        }
        
        # Weight the components
        weights = {
            'technical_mood': 0.25,
            'flow_mood': 0.30,
            'sentiment_mood': 0.20,
            'volatility_mood': 0.15,
            'momentum_mood': 0.10
        }
        
        # Calculate weighted average
        overall_mood = sum(components[key] * weights[key] for key in components)
        
        # Determine mood category
        if overall_mood >= 80:
            mood_category = 'extreme_greed'
            mood_label = 'EXTREME GREED'
            emoji = '🤑'
        elif overall_mood >= 60:
            mood_category = 'greed'
            mood_label = 'GREED'
            emoji = '😊'
        elif overall_mood >= 40:
            mood_category = 'neutral'
            mood_label = 'NEUTRAL'
            emoji = '😐'
        elif overall_mood >= 20:
            mood_category = 'fear'
            mood_label = 'FEAR'
            emoji = '😰'
        else:
            mood_category = 'extreme_fear'
            mood_label = 'EXTREME FEAR'
            emoji = '😱'
        
        mood_data = {
            'score': overall_mood,
            'category': mood_category,
            'label': mood_label,
            'emoji': emoji,
            'components': components,
            'timestamp': datetime.now(),
            'color': self.colors[mood_category]
        }
        
        # Add to history
        self.mood_history.append(mood_data)
        if len(self.mood_history) > 100:  # Keep last 100 readings
            self.mood_history.pop(0)
        
        return mood_data
    
    def _calculate_technical_mood(self, rsi: float, market_data: dict) -> float:
        """Calculate mood from technical indicators"""
        mood = 50  # Start neutral
        
        # RSI component
        if rsi > 70:
            mood += (rsi - 70) * 1.5  # Overbought = greed
        elif rsi < 30:
            mood -= (30 - rsi) * 1.5  # Oversold = fear
        
        # Price momentum
        price_change = market_data.get('price_change_pct', 0)
        mood += price_change * 2
        
        # Volume confirmation
        volume_ratio = market_data.get('volume_ratio', 1.0)
        if volume_ratio > 1.5:
            mood += 10  # High volume = conviction
        elif volume_ratio < 0.7:
            mood -= 5   # Low volume = uncertainty
        
        return max(0, min(100, mood))
    
    def _calculate_flow_mood(self, call_put_ratio: float, volume_ratio: float) -> float:
        """Calculate mood from options flow"""
        mood = 50  # Start neutral
        
        # Call/Put ratio analysis
        if call_put_ratio > 1.5:
            mood += (call_put_ratio - 1) * 15  # Heavy call buying = greed
        elif call_put_ratio < 0.7:
            mood -= (1 - call_put_ratio) * 20  # Heavy put buying = fear
        
        # Volume intensity
        if volume_ratio > 2.0:
            mood += 15  # Intense activity
        elif volume_ratio > 1.5:
            mood += 8
        
        return max(0, min(100, mood))
    
    def _calculate_sentiment_mood(self, sentiment_score: float) -> float:
        """Calculate mood from sentiment analysis"""
        # Convert sentiment score (-1 to 1) to mood (0 to 100)
        mood = 50 + (sentiment_score * 50)
        return max(0, min(100, mood))
    
    def _calculate_volatility_mood(self, vix: float) -> float:
        """Calculate mood from volatility"""
        # VIX interpretation (inverted - high VIX = fear)
        if vix > 30:
            return max(0, 50 - (vix - 30) * 2)  # High VIX = fear
        elif vix < 15:
            return min(100, 50 + (15 - vix) * 3)  # Low VIX = complacency
        else:
            return 50  # Normal VIX = neutral
    
    def _calculate_momentum_mood(self, market_data: dict) -> float:
        """Calculate mood from price momentum"""
        price_change = market_data.get('price_change_pct', 0)
        
        if abs(price_change) > 5:  # Strong momentum
            return 70 if price_change > 0 else 30
        elif abs(price_change) > 2:  # Moderate momentum
            return 60 if price_change > 0 else 40
        else:  # Weak momentum
            return 50
    
    def create_animated_gauge(self, mood_data: dict) -> go.Figure:
        """Create animated gauge chart for market mood"""
        
        # Create gauge figure
        fig = go.Figure()
        
        # Add gauge
        fig.add_trace(go.Indicator(
            mode="gauge+number+delta",
            value=mood_data['score'],
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': f"Market Mood {mood_data['emoji']}", 'font': {'size': 24}},
            delta={'reference': 50, 'increasing': {'color': "#32CD32"}, 'decreasing': {'color': "#FF4500"}},
            gauge={
                'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': mood_data['color']},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps': [
                    {'range': [0, 20], 'color': '#8B0000'},    # Extreme Fear
                    {'range': [20, 40], 'color': '#FF4500'},   # Fear
                    {'range': [40, 60], 'color': '#FFD700'},   # Neutral
                    {'range': [60, 80], 'color': '#32CD32'},   # Greed
                    {'range': [80, 100], 'color': '#228B22'}   # Extreme Greed
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': mood_data['score']
                }
            }
        ))
        
        # Update layout
        fig.update_layout(
            height=300,
            font={'color': "darkblue", 'family': "Arial"},
            paper_bgcolor="rgba(255,255,255,0.8)",
            plot_bgcolor="rgba(255,255,255,0.8)"
        )
        
        return fig
    
    def create_mood_history_chart(self) -> go.Figure:
        """Create animated line chart of mood history"""
        if not self.mood_history:
            return None
        
        # Prepare data
        times = [m['timestamp'] for m in self.mood_history]
        scores = [m['score'] for m in self.mood_history]
        categories = [m['label'] for m in self.mood_history]
        
        # Create figure
        fig = go.Figure()
        
        # Add line trace
        fig.add_trace(go.Scatter(
            x=times,
            y=scores,
            mode='lines+markers',
            name='Market Mood',
            line=dict(color='#1f77b4', width=3),
            marker=dict(size=8, color=scores, colorscale='RdYlGn', showscale=True,
                       colorbar=dict(title="Mood Score", titleside="right")),
            text=categories,
            hovertemplate='<b>%{text}</b><br>Score: %{y:.1f}<br>Time: %{x}<extra></extra>'
        ))
        
        # Add mood zones
        fig.add_hrect(y0=0, y1=20, fillcolor="red", opacity=0.1, 
                     annotation_text="EXTREME FEAR", annotation_position="left")
        fig.add_hrect(y0=20, y1=40, fillcolor="orange", opacity=0.1,
                     annotation_text="FEAR", annotation_position="left")
        fig.add_hrect(y0=40, y1=60, fillcolor="yellow", opacity=0.1,
                     annotation_text="NEUTRAL", annotation_position="left")
        fig.add_hrect(y0=60, y1=80, fillcolor="lightgreen", opacity=0.1,
                     annotation_text="GREED", annotation_position="left")
        fig.add_hrect(y0=80, y1=100, fillcolor="green", opacity=0.1,
                     annotation_text="EXTREME GREED", annotation_position="left")
        
        # Update layout
        fig.update_layout(
            title="Market Mood History",
            xaxis_title="Time",
            yaxis_title="Mood Score",
            height=300,
            showlegend=False,
            hovermode='x unified'
        )
        
        return fig
    
    def create_component_breakdown(self, mood_data: dict) -> go.Figure:
        """Create animated bar chart of mood components"""
        components = mood_data['components']
        
        # Prepare data
        categories = list(components.keys())
        values = list(components.values())
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
        
        # Create figure
        fig = go.Figure()
        
        # Add bars
        fig.add_trace(go.Bar(
            x=categories,
            y=values,
            marker_color=colors,
            text=[f'{v:.1f}' for v in values],
            textposition='auto',
            hovertemplate='<b>%{x}</b><br>Score: %{y:.1f}<extra></extra>'
        ))
        
        # Update layout
        fig.update_layout(
            title="Mood Component Breakdown",
            xaxis_title="Components",
            yaxis_title="Score",
            height=250,
            showlegend=False,
            yaxis=dict(range=[0, 100])
        )
        
        # Clean up category names for display
        fig.update_xaxes(ticktext=['Technical', 'Options Flow', 'Sentiment', 'Volatility', 'Momentum'],
                        tickvals=categories)
        
        return fig
    
    def get_mood_insights(self, mood_data: dict) -> list:
        """Generate insights based on current mood"""
        insights = []
        score = mood_data['score']
        components = mood_data['components']
        
        # Overall mood insights
        if score >= 80:
            insights.append("⚠️ Market showing EXTREME GREED - consider taking profits or protective positions")
        elif score >= 60:
            insights.append("📈 Market in GREED phase - good for momentum plays but watch for reversals")
        elif score <= 20:
            insights.append("💡 EXTREME FEAR presents buying opportunities for contrarian investors")
        elif score <= 40:
            insights.append("🛡️ Market FEAR suggests defensive positioning and careful entry timing")
        else:
            insights.append("⚖️ NEUTRAL market conditions - wait for clearer directional signals")
        
        # Component-specific insights
        if components['technical_mood'] > 75:
            insights.append("📊 Technical indicators extremely bullish - momentum likely to continue")
        elif components['technical_mood'] < 25:
            insights.append("📉 Technical indicators very bearish - downside risk elevated")
        
        if components['flow_mood'] > 70:
            insights.append("🔥 Heavy call buying detected - institutional bullish positioning")
        elif components['flow_mood'] < 30:
            insights.append("🐻 Put buying dominance - institutional hedging or bearish bets")
        
        if components['volatility_mood'] < 30:
            insights.append("⚡ High volatility environment - position sizes should be reduced")
        
        return insights

# Global market mood indicator
market_mood_indicator = MarketMoodIndicator()