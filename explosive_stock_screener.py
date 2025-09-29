"""
Explosive Stock Screener - Technical Analysis Engine
Identifies stocks with high profit potential through multiple technical signals
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


class ExplosiveStockScreener:
    """
    Advanced technical analysis system to identify stocks with explosive profit potential
    Uses multiple confirmation signals and momentum indicators
    """
    
    def __init__(self):
        self.watchlist_symbols = [
            # Large Cap Movers
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX',
            # Growth Tech
            'AMD', 'CRM', 'ADBE', 'NOW', 'SNOW', 'PLTR', 'RBLX', 'COIN',
            # Biotech/Healthcare 
            'MRNA', 'BNTX', 'GILD', 'BIIB', 'REGN', 'VRTX', 'ILMN',
            # Energy/Materials
            'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'FCX', 'NEM', 'AA',
            # Finance
            'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'V', 'MA',
            # Consumer/Retail
            'COST', 'WMT', 'HD', 'LOW', 'TGT', 'SBUX', 'NKE', 'LULU',
            # Industrial
            'CAT', 'DE', 'BA', 'GE', 'MMM', 'HON', 'UPS', 'FDX',
            # Emerging/Volatile
            'RIVN', 'LCID', 'SOFI', 'HOOD', 'UPST', 'AFRM', 'ZM', 'PTON'
        ]
        
        self.cache_duration = 300  # 5 minutes
        self.screener_cache = {}
        self.last_scan_time = {}
    
    def calculate_technical_signals(self, symbol: str, period: str = '3mo') -> Dict:
        """Calculate comprehensive technical analysis signals for explosive potential"""
        
        try:
            # Get stock data
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period)
            
            if df.empty or len(df) < 50:
                return None
            
            # Calculate technical indicators
            signals = {}
            
            # === MOMENTUM SIGNALS ===
            signals.update(self._calculate_momentum_signals(df))
            
            # === BREAKOUT SIGNALS ===
            signals.update(self._calculate_breakout_signals(df))
            
            # === VOLUME SIGNALS ===
            signals.update(self._calculate_volume_signals(df))
            
            # === VOLATILITY SIGNALS ===
            signals.update(self._calculate_volatility_signals(df))
            
            # === TREND SIGNALS ===
            signals.update(self._calculate_trend_signals(df))
            
            # === CALCULATE EXPLOSIVE SCORE ===
            explosive_score = self._calculate_explosive_score(signals)
            signals['explosive_score'] = explosive_score
            signals['recommendation'] = self._get_recommendation(explosive_score)
            
            # Add current price info
            current_price = df['Close'].iloc[-1]
            prev_close = df['Close'].iloc[-2] if len(df) > 1 else current_price
            signals['current_price'] = current_price
            signals['daily_change'] = ((current_price - prev_close) / prev_close * 100)
            
            return signals
            
        except Exception as e:
            st.error(f"Error analyzing {symbol}: {str(e)}")
            return None
    
    def _calculate_momentum_signals(self, df: pd.DataFrame) -> Dict:
        """Calculate momentum-based signals"""
        signals = {}
        
        # RSI (14-period)
        rsi = self._calculate_rsi(df['Close'], 14)
        signals['rsi'] = rsi.iloc[-1] if not rsi.empty else 50
        signals['rsi_signal'] = 'OVERSOLD_BOUNCE' if signals['rsi'] < 35 else 'MOMENTUM_BUILD' if signals['rsi'] > 55 else 'NEUTRAL'
        
        # MACD
        exp1 = df['Close'].ewm(span=12).mean()
        exp2 = df['Close'].ewm(span=26).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=9).mean()
        histogram = macd - signal_line
        
        signals['macd'] = macd.iloc[-1]
        signals['macd_signal'] = signal_line.iloc[-1]
        signals['macd_histogram'] = histogram.iloc[-1]
        signals['macd_crossover'] = 'BULLISH' if macd.iloc[-1] > signal_line.iloc[-1] and macd.iloc[-2] <= signal_line.iloc[-2] else 'BEARISH' if macd.iloc[-1] < signal_line.iloc[-1] and macd.iloc[-2] >= signal_line.iloc[-2] else 'NONE'
        
        # Williams %R
        high_14 = df['High'].rolling(window=14).max()
        low_14 = df['Low'].rolling(window=14).min()
        williams_r = ((high_14 - df['Close']) / (high_14 - low_14)) * -100
        signals['williams_r'] = williams_r.iloc[-1] if not williams_r.empty else -50
        
        return signals
    
    def _calculate_breakout_signals(self, df: pd.DataFrame) -> Dict:
        """Calculate breakout pattern signals"""
        signals = {}
        
        # Bollinger Bands breakout
        rolling_mean = df['Close'].rolling(window=20).mean()
        rolling_std = df['Close'].rolling(window=20).std()
        upper_band = rolling_mean + (rolling_std * 2)
        lower_band = rolling_mean - (rolling_std * 2)
        
        current_price = df['Close'].iloc[-1]
        signals['bb_upper'] = upper_band.iloc[-1]
        signals['bb_lower'] = lower_band.iloc[-1]
        signals['bb_position'] = (current_price - lower_band.iloc[-1]) / (upper_band.iloc[-1] - lower_band.iloc[-1])
        signals['bb_breakout'] = 'UPWARD' if current_price > upper_band.iloc[-1] else 'DOWNWARD' if current_price < lower_band.iloc[-1] else 'NONE'
        
        # Support/Resistance breakout
        # Find recent highs and lows
        high_20 = df['High'].rolling(window=20).max()
        low_20 = df['Low'].rolling(window=20).min()
        
        signals['resistance_level'] = high_20.iloc[-1]
        signals['support_level'] = low_20.iloc[-1]
        signals['near_resistance'] = abs(current_price - signals['resistance_level']) / current_price < 0.02
        signals['near_support'] = abs(current_price - signals['support_level']) / current_price < 0.02
        
        # Price consolidation (low volatility before breakout)
        price_range_10d = (df['High'].tail(10).max() - df['Low'].tail(10).min()) / df['Close'].tail(10).mean()
        signals['consolidation'] = price_range_10d < 0.05  # Within 5% range
        
        return signals
    
    def _calculate_volume_signals(self, df: pd.DataFrame) -> Dict:
        """Calculate volume-based signals"""
        signals = {}
        
        # Volume averages
        vol_avg_10 = df['Volume'].rolling(window=10).mean()
        vol_avg_30 = df['Volume'].rolling(window=30).mean()
        
        current_vol = df['Volume'].iloc[-1]
        signals['volume_10d_avg'] = vol_avg_10.iloc[-1]
        signals['volume_30d_avg'] = vol_avg_30.iloc[-1]
        signals['volume_surge'] = current_vol / vol_avg_10.iloc[-1] if vol_avg_10.iloc[-1] > 0 else 1
        signals['volume_trend'] = 'INCREASING' if vol_avg_10.iloc[-1] > vol_avg_30.iloc[-1] * 1.2 else 'DECREASING' if vol_avg_10.iloc[-1] < vol_avg_30.iloc[-1] * 0.8 else 'STABLE'
        
        # On-Balance Volume (OBV)
        obv = []
        obv_val = 0
        for i in range(len(df)):
            if i == 0:
                obv_val = df['Volume'].iloc[i]
            else:
                if df['Close'].iloc[i] > df['Close'].iloc[i-1]:
                    obv_val += df['Volume'].iloc[i]
                elif df['Close'].iloc[i] < df['Close'].iloc[i-1]:
                    obv_val -= df['Volume'].iloc[i]
                # If price unchanged, OBV unchanged
            obv.append(obv_val)
        
        signals['obv'] = obv[-1]
        signals['obv_trend'] = 'BULLISH' if len(obv) > 5 and obv[-1] > obv[-6] else 'BEARISH' if len(obv) > 5 and obv[-1] < obv[-6] else 'NEUTRAL'
        
        return signals
    
    def _calculate_volatility_signals(self, df: pd.DataFrame) -> Dict:
        """Calculate volatility-based signals"""
        signals = {}
        
        # Average True Range (ATR)
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = true_range.rolling(window=14).mean()
        
        signals['atr'] = atr.iloc[-1] if not atr.empty else 0
        signals['atr_percentage'] = (signals['atr'] / df['Close'].iloc[-1]) * 100
        
        # Volatility squeeze detection
        signals['low_volatility'] = signals['atr_percentage'] < 2.0  # Less than 2% daily range
        
        # Historical volatility
        returns = df['Close'].pct_change().dropna()
        hist_vol = returns.rolling(window=20).std() * np.sqrt(252) * 100
        signals['historical_volatility'] = hist_vol.iloc[-1] if not hist_vol.empty else 0
        
        return signals
    
    def _calculate_trend_signals(self, df: pd.DataFrame) -> Dict:
        """Calculate trend-based signals"""
        signals = {}
        
        # Moving averages
        sma_20 = df['Close'].rolling(window=20).mean()
        sma_50 = df['Close'].rolling(window=50).mean()
        ema_12 = df['Close'].ewm(span=12).mean()
        
        current_price = df['Close'].iloc[-1]
        signals['sma_20'] = sma_20.iloc[-1]
        signals['sma_50'] = sma_50.iloc[-1] if len(sma_50.dropna()) > 0 else current_price
        signals['ema_12'] = ema_12.iloc[-1]
        
        # Trend direction
        signals['above_sma_20'] = current_price > signals['sma_20']
        signals['above_sma_50'] = current_price > signals['sma_50']
        signals['ma_alignment'] = 'BULLISH' if signals['sma_20'] > signals['sma_50'] else 'BEARISH'
        
        # Trend strength
        price_change_20d = (current_price - df['Close'].iloc[-20]) / df['Close'].iloc[-20] * 100 if len(df) >= 20 else 0
        signals['trend_strength_20d'] = price_change_20d
        
        return signals
    
    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_explosive_score(self, signals: Dict) -> float:
        """Calculate overall explosive potential score (0-100)"""
        score = 0
        max_score = 100
        
        # Momentum Score (25 points)
        if signals.get('rsi_signal') == 'OVERSOLD_BOUNCE':
            score += 8
        elif signals.get('rsi_signal') == 'MOMENTUM_BUILD':
            score += 12
        
        if signals.get('macd_crossover') == 'BULLISH':
            score += 13
        
        # Breakout Score (25 points)
        if signals.get('bb_breakout') == 'UPWARD':
            score += 15
        elif signals.get('bb_position', 0) > 0.8:
            score += 8  # Near upper band
        
        if signals.get('near_resistance') and signals.get('volume_surge', 1) > 1.5:
            score += 10  # Breaking resistance with volume
        
        # Volume Score (20 points)
        volume_surge = signals.get('volume_surge', 1)
        if volume_surge > 3.0:
            score += 15
        elif volume_surge > 2.0:
            score += 10
        elif volume_surge > 1.5:
            score += 5
        
        if signals.get('obv_trend') == 'BULLISH':
            score += 5
        
        # Trend Score (20 points)
        if signals.get('above_sma_20') and signals.get('above_sma_50'):
            score += 8
        elif signals.get('above_sma_20'):
            score += 4
        
        if signals.get('ma_alignment') == 'BULLISH':
            score += 6
        
        trend_strength = signals.get('trend_strength_20d', 0)
        if trend_strength > 15:
            score += 6
        elif trend_strength > 5:
            score += 3
        
        # Volatility Score (10 points)
        if signals.get('low_volatility') and signals.get('consolidation'):
            score += 8  # Coiling for breakout
        elif signals.get('atr_percentage', 0) > 3:
            score += 5  # High volatility for explosive moves
        
        return min(score, max_score)
    
    def _get_recommendation(self, score: float) -> str:
        """Get recommendation based on explosive score"""
        if score >= 80:
            return "🚀 EXPLOSIVE - High Profit Potential"
        elif score >= 65:
            return "⚡ STRONG BUY - Good Opportunity"  
        elif score >= 50:
            return "📈 BUY - Moderate Potential"
        elif score >= 35:
            return "⚠️ WATCH - Wait for Setup"
        else:
            return "❌ AVOID - Low Potential"
    
    def screen_explosive_opportunities(self) -> List[Dict]:
        """Screen all watchlist stocks for explosive opportunities"""
        
        cache_key = "explosive_screen"
        current_time = time.time()
        
        # Check cache
        if (cache_key in self.screener_cache and 
            cache_key in self.last_scan_time and
            current_time - self.last_scan_time[cache_key] < self.cache_duration):
            return self.screener_cache[cache_key]
        
        opportunities = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, symbol in enumerate(self.watchlist_symbols):
            try:
                status_text.text(f"Analyzing {symbol}... ({i+1}/{len(self.watchlist_symbols)})")
                progress_bar.progress((i + 1) / len(self.watchlist_symbols))
                
                signals = self.calculate_technical_signals(symbol)
                if signals and signals['explosive_score'] > 30:  # Only show decent opportunities
                    opportunity = {
                        'symbol': symbol,
                        'score': signals['explosive_score'],
                        'recommendation': signals['recommendation'],
                        'current_price': signals['current_price'],
                        'daily_change': signals['daily_change'],
                        'key_signals': self._get_key_signals(signals),
                        'risk_level': self._get_risk_level(signals),
                        'target_upside': self._estimate_target_upside(signals),
                        'signals': signals  # Full signal data
                    }
                    opportunities.append(opportunity)
                    
            except Exception as e:
                st.error(f"Error screening {symbol}: {str(e)}")
                continue
        
        # Sort by explosive score
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        
        # Cache results
        self.screener_cache[cache_key] = opportunities
        self.last_scan_time[cache_key] = current_time
        
        progress_bar.empty()
        status_text.empty()
        
        return opportunities
    
    def _get_key_signals(self, signals: Dict) -> List[str]:
        """Extract key bullish signals for display"""
        key_signals = []
        
        if signals.get('macd_crossover') == 'BULLISH':
            key_signals.append("MACD Bullish Cross")
        
        if signals.get('volume_surge', 1) > 2.0:
            key_signals.append(f"Volume Surge {signals['volume_surge']:.1f}x")
        
        if signals.get('bb_breakout') == 'UPWARD':
            key_signals.append("Bollinger Breakout")
            
        if signals.get('rsi_signal') == 'OVERSOLD_BOUNCE':
            key_signals.append("RSI Oversold Bounce")
            
        if signals.get('near_resistance'):
            key_signals.append("Breaking Resistance")
            
        if signals.get('obv_trend') == 'BULLISH':
            key_signals.append("OBV Bullish")
            
        if signals.get('consolidation'):
            key_signals.append("Price Consolidation")
        
        return key_signals[:4]  # Top 4 signals
    
    def _get_risk_level(self, signals: Dict) -> str:
        """Determine risk level"""
        volatility = signals.get('atr_percentage', 0)
        trend_strength = signals.get('trend_strength_20d', 0)
        
        if volatility > 5 or abs(trend_strength) > 20:
            return "🔴 HIGH"
        elif volatility > 3 or abs(trend_strength) > 10:
            return "🟡 MEDIUM"
        else:
            return "🟢 LOW"
    
    def _estimate_target_upside(self, signals: Dict) -> str:
        """Estimate potential upside based on signals"""
        score = signals.get('explosive_score', 0)
        volatility = signals.get('atr_percentage', 0)
        
        if score >= 80:
            base_target = 15 + (volatility * 2)
        elif score >= 65:
            base_target = 10 + (volatility * 1.5)
        elif score >= 50:
            base_target = 7 + volatility
        else:
            base_target = 3 + (volatility * 0.5)
        
        return f"{base_target:.0f}%"


# Global screener instance
explosive_screener = ExplosiveStockScreener()