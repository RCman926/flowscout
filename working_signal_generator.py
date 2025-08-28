"""
Working Signal Generator - Generates actual trading signals that work
Simplified but functional approach to replace broken complex modules
"""

import yfinance as yf
import numpy as np
from datetime import datetime
import pandas as pd

class WorkingSignalGenerator:
    """Generates actual working trading signals"""
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 30  # 30 seconds
    
    def generate_live_signals(self, symbol: str) -> dict:
        """Generate live working trading signals"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d", interval="1h")
            
            if hist.empty:
                return self._get_fallback_signals(symbol)
            
            current_price = float(hist['Close'].iloc[-1])
            
            # Simple but effective technical analysis
            signals = self._calculate_working_signals(hist, current_price, symbol)
            
            return {
                'symbol': symbol,
                'current_price': current_price,
                'signals': signals,
                'timestamp': datetime.now(),
                'confidence': signals['overall_confidence'],
                'action': signals['action'],
                'strength': signals['strength']
            }
            
        except Exception as e:
            print(f"Signal generation error: {e}")
            return self._get_fallback_signals(symbol)
    
    def _calculate_working_signals(self, hist, current_price, symbol):
        """Calculate actual working signals"""
        closes = hist['Close'].values
        volumes = hist['Volume'].values
        
        # Moving averages
        sma_20 = np.mean(closes[-20:]) if len(closes) >= 20 else current_price
        sma_10 = np.mean(closes[-10:]) if len(closes) >= 10 else current_price
        sma_5 = np.mean(closes[-5:]) if len(closes) >= 5 else current_price
        
        # RSI calculation
        rsi = self._calculate_rsi(closes) if len(closes) >= 14 else 50
        
        # Volume analysis
        avg_volume = np.mean(volumes[-10:]) if len(volumes) >= 10 else volumes[-1]
        volume_ratio = volumes[-1] / avg_volume if avg_volume > 0 else 1
        
        # Price momentum
        price_change_pct = ((current_price - closes[-5]) / closes[-5] * 100) if len(closes) >= 5 else 0
        
        # Signal scoring
        signals = []
        confidence_score = 50  # Base confidence
        
        # Trend analysis
        if current_price > sma_5 > sma_10 > sma_20:
            signals.append("STRONG_BULLISH_TREND")
            confidence_score += 20
        elif current_price > sma_10 and sma_10 > sma_20:
            signals.append("BULLISH_TREND")
            confidence_score += 10
        elif current_price < sma_5 < sma_10 < sma_20:
            signals.append("STRONG_BEARISH_TREND")
            confidence_score -= 20
        elif current_price < sma_10 and sma_10 < sma_20:
            signals.append("BEARISH_TREND")
            confidence_score -= 10
        
        # RSI signals
        if rsi > 70:
            signals.append("OVERBOUGHT")
            confidence_score -= 15
        elif rsi < 30:
            signals.append("OVERSOLD")
            confidence_score += 15
        
        # Volume confirmation
        if volume_ratio > 1.5:
            signals.append("HIGH_VOLUME")
            confidence_score += 10
        elif volume_ratio > 2.0:
            signals.append("UNUSUAL_VOLUME")
            confidence_score += 15
        
        # Price momentum
        if price_change_pct > 3:
            signals.append("STRONG_MOMENTUM_UP")
            confidence_score += 15
        elif price_change_pct < -3:
            signals.append("STRONG_MOMENTUM_DOWN")
            confidence_score -= 15
        
        # Determine action
        if confidence_score >= 70:
            action = "STRONG_BUY_CALLS"
            strength = "STRONG"
        elif confidence_score >= 60:
            action = "BUY_CALLS"
            strength = "MODERATE"
        elif confidence_score <= 30:
            action = "STRONG_BUY_PUTS"
            strength = "STRONG"
        elif confidence_score <= 40:
            action = "BUY_PUTS"
            strength = "MODERATE"
        else:
            action = "HOLD"
            strength = "NEUTRAL"
        
        return {
            'signals': signals,
            'rsi': rsi,
            'sma_20': sma_20,
            'sma_10': sma_10,
            'sma_5': sma_5,
            'volume_ratio': volume_ratio,
            'price_change_pct': price_change_pct,
            'overall_confidence': min(95, max(5, confidence_score)),
            'action': action,
            'strength': strength,
            'reasoning': f"Based on {len(signals)} technical factors"
        }
    
    def _calculate_rsi(self, prices, period=14):
        """Calculate RSI"""
        if len(prices) < period + 1:
            return 50
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _get_fallback_signals(self, symbol):
        """Fallback when data unavailable"""
        return {
            'symbol': symbol,
            'current_price': 587.45 if symbol == 'SPY' else 150.0,
            'signals': {
                'signals': ['DATA_ERROR'],
                'rsi': 50,
                'sma_20': 587.45,
                'sma_10': 587.45,
                'sma_5': 587.45,
                'volume_ratio': 1.0,
                'price_change_pct': 0,
                'overall_confidence': 25,
                'action': 'HOLD',
                'strength': 'LOW_DATA',
                'reasoning': 'Insufficient data for analysis'
            },
            'timestamp': datetime.now(),
            'confidence': 25,
            'action': 'HOLD',
            'strength': 'LOW_DATA'
        }

# Global instance
working_signal_generator = WorkingSignalGenerator()