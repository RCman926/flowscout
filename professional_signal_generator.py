import numpy as np
import pandas as pd
import asyncio

async def generate_professional_ai_signal(symbol, indicators, price_data, volume_data):
    """Generate professional institutional-grade AI signal with 90% accuracy targeting"""
    try:
        current_price = price_data[-1] if len(price_data) > 0 else 100
        
        # Import here to avoid circular imports
        import streamlit as st
        
        # 1. Get Professional AI Prediction
        ai_prediction = await st.session_state.professional_ai.generate_professional_prediction(
            price_data, indicators
        )
        
        # 2. Prepare volume analysis data
        volume_analysis = {
            'volume_ratio': indicators.get('volume_ratio', 1.0),
            'trend': 'increasing' if len(volume_data) > 1 and volume_data[-1] > volume_data[-2] else 'neutral',
            'institutional_percentage': min(100, indicators.get('volume_ratio', 1) * 30)  # Estimate institutional flow
        }
        
        # 3. Prepare market structure data
        market_structure = {
            'market_trend': 'bullish' if indicators.get('rsi', 50) < 60 and indicators.get('macd', 0) > 0 else 'bearish' if indicators.get('rsi', 50) > 60 and indicators.get('macd', 0) < 0 else 'neutral',
            'vix': 20 + abs(indicators.get('rsi', 50) - 50) * 0.5,  # Simulate VIX based on RSI
            'breadth': (indicators.get('rsi', 50) - 50) / 50,  # Market breadth simulation
            'sector_rotation': 'stable'
        }
        
        # 4. Generate Coordinated Professional Signal
        coordinated_signal = await st.session_state.signal_coordinator.generate_coordinated_signal(
            symbol=symbol,
            ai_prediction=ai_prediction,
            technical_indicators=indicators,
            volume_data=volume_analysis,
            current_price=current_price,
            market_data=market_structure
        )
        
        return coordinated_signal
        
    except Exception as e:
        print(f"Professional AI signal error: {e}")
        fallback_price = price_data[-1] if len(price_data) > 0 else 100
        return {
            'signal': 'NO_TRADE',
            'confidence': 0.5,
            'probability': 50.0,
            'current_price': fallback_price,
            'predicted_price': fallback_price,
            'reasoning': f"Professional AI system error: {e}",
            'professional_grade': False,
            'institutional_approved': False
        }