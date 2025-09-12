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
            price_data, volume_data, indicators, symbol
        )
        
        # 2. Prepare volume analysis data
        volume_analysis = {
            'volume_ratio': indicators.get('volume_ratio', 1.0),
            'trend': 'increasing' if len(volume_data) > 1 and volume_data[-1] > volume_data[-2] else 'neutral',
            'institutional_percentage': min(100, indicators.get('volume_ratio', 1) * 30)  # Estimate institutional flow
        }
        
        # 3. Enhanced market structure with multi-factor analysis
        rsi = indicators.get('rsi', 50)
        macd = indicators.get('macd', 0)
        bb_position = indicators.get('bb_percent', 50)
        
        # Advanced trend detection
        trend_score = 0
        if rsi < 30 and macd > 0: trend_score += 2  # Strong bullish divergence
        elif rsi > 70 and macd < 0: trend_score -= 2  # Strong bearish divergence
        elif 40 <= rsi <= 60 and abs(macd) < 0.1: trend_score = 0  # Neutral
        elif rsi < 45: trend_score += 1
        elif rsi > 55: trend_score -= 1
        
        # Volatility regime detection
        price_change = abs(indicators.get('change_pct', 0))
        vol_regime = 'high' if price_change > 2 else 'normal' if price_change > 0.5 else 'low'
        
        # Market breadth calculation
        breadth_score = (rsi - 50) / 50 * 0.6 + (bb_position - 50) / 50 * 0.4
        
        market_structure = {
            'market_trend': 'bullish' if trend_score >= 1 else 'bearish' if trend_score <= -1 else 'neutral',
            'trend_strength': abs(trend_score) / 2,  # 0 to 1 scale
            'vix_estimate': max(15, min(35, 20 + price_change * 3)),  # Dynamic VIX estimate
            'volatility_regime': vol_regime,
            'breadth': breadth_score,
            'sector_rotation': 'growth' if rsi < 50 and vol_regime == 'low' else 'defensive' if rsi > 50 and vol_regime == 'high' else 'balanced',
            'momentum_factor': (macd * 10) if abs(macd) > 0.05 else 0,
            'market_phase': _detect_market_phase(rsi, macd, price_change)
        }
        
        # 4. Get Enhanced News Sentiment for Market Intelligence
        try:
            from data_communication_enhancer import enhanced_data_communicator
            news_sentiment = enhanced_data_communicator.get_reliable_news_data(symbol)
            
            # Integrate news sentiment into market structure
            sentiment_score = news_sentiment.get('sentiment_score', 0.0)
            sentiment_confidence = news_sentiment.get('confidence', 0.5)
            news_impact = news_sentiment.get('news_impact', 'MEDIUM')
            
            # Adjust market structure with news intelligence
            market_structure['news_sentiment'] = sentiment_score
            market_structure['news_confidence'] = sentiment_confidence  
            market_structure['news_impact'] = news_impact
            market_structure['market_intelligence_active'] = news_sentiment.get('market_intelligence', False)
            
            # Boost or dampen signals based on news sentiment alignment
            if abs(sentiment_score) > 0.3 and sentiment_confidence > 0.7:
                market_structure['news_catalyst'] = True
                market_structure['enhanced_confidence'] = True
            else:
                market_structure['news_catalyst'] = False
                market_structure['enhanced_confidence'] = False
                
        except Exception as e:
            print(f"News sentiment integration warning: {e}")
            market_structure['news_sentiment'] = 0.0
            market_structure['news_catalyst'] = False

        # 5. Generate Coordinated Professional Signal with News Intelligence
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

def _detect_market_phase(rsi, macd, price_change):
    """Detect current market phase for enhanced prediction accuracy"""
    try:
        # Market phase detection algorithm
        if rsi < 30 and macd < 0 and price_change > 1:
            return 'oversold_bounce'  # High probability reversal
        elif rsi > 70 and macd > 0 and price_change > 1:  
            return 'overbought_pullback'  # High probability pullback
        elif 30 <= rsi <= 70 and abs(macd) < 0.05 and price_change < 0.5:
            return 'consolidation'  # Low volatility, range-bound
        elif rsi < 50 and macd > 0 and price_change < 1:
            return 'early_uptrend'  # Building momentum
        elif rsi > 50 and macd < 0 and price_change < 1:
            return 'early_downtrend'  # Weakening momentum  
        elif price_change > 2:
            return 'high_volatility'  # News-driven or breakout
        else:
            return 'neutral_trending'  # Standard market conditions
    except:
        return 'unknown'