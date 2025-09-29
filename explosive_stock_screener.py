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
            # Large Cap Movers (potential explosive moves)
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
            'RIVN', 'LCID', 'SOFI', 'HOOD', 'UPST', 'AFRM', 'ZM', 'PTON',
            
            # === EXPLOSIVE PENNY STOCKS & HIGH VOLATILITY ===
            # Penny Stocks Under $10 (High Explosion Potential)
            'SNDL', 'HITI', 'BBIG', 'MULN', 'GNUS', 'PROG', 'ATER', 'BBBY',
            'NKLA', 'RIDE', 'GOEV', 'WKHS', 'HYMC', 'RMED', 'PHUN', 'DWAC',
            'SPRT', 'GREE', 'IRNT', 'OPAD', 'ANY', 'BGFV', 'ROOT', 'CLOV',
            'WISH', 'SKLZ', 'DKNG', 'PENN', 'TLRY', 'ACB', 'CGC', 'CRON',
            'RIOT', 'MARA', 'BTBT', 'EBON', 'CAN', 'HVBT', 'BITF', 'HIVE',
            
            # Small Cap Explosive Potential ($10-50)
            'PLBY', 'BODY', 'BARK', 'MVST', 'QS', 'CHPT', 'BLNK', 'EVGO',
            'SPCE', 'ASTR', 'RKT', 'OPEN', 'BROS', 'DNUT', 'BYND', 'OATLY',
            'RKLB', 'PL', 'DDOG', 'CRWD', 'ZS', 'OKTA', 'ESTC', 'MDB',
            
            # Meme Stock Potential
            'GME', 'AMC', 'KOSS', 'EXPR', 'NAKD', 'SIRI', 'NOK', 'BB'
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
            
            # === EXPLOSIVE PATTERN RECOGNITION ===
            signals.update(self._detect_explosive_patterns(df))
            
            # === PENNTY STOCK EXPLOSIVE SIGNALS ===
            if signals['current_price'] < 10:  # Penny stock special analysis
                signals.update(self._calculate_penny_stock_signals(df))
            
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
    
    def _detect_explosive_patterns(self, df: pd.DataFrame) -> Dict:
        """Detect explosive chart patterns like triple tops/bottoms, cup and handle, etc."""
        signals = {}
        
        # === TRIPLE TOP/BOTTOM DETECTION ===
        triple_signals = self._detect_triple_patterns(df)
        signals.update(triple_signals)
        
        # === DOUBLE TOP/BOTTOM DETECTION ===
        double_signals = self._detect_double_patterns(df)
        signals.update(double_signals)
        
        # === BOLLINGER BAND SQUEEZE ("BOILER BANGER") ===
        squeeze_signals = self._detect_bollinger_squeeze(df)
        signals.update(squeeze_signals)
        
        # === CUP AND HANDLE PATTERN ===
        cup_handle_signals = self._detect_cup_and_handle(df)
        signals.update(cup_handle_signals)
        
        # === ASCENDING/DESCENDING TRIANGLE ===
        triangle_signals = self._detect_triangle_patterns(df)
        signals.update(triangle_signals)
        
        # === FLAG AND PENNANT PATTERNS ===
        flag_signals = self._detect_flag_patterns(df)
        signals.update(flag_signals)
        
        return signals
    
    def _detect_triple_patterns(self, df: pd.DataFrame) -> Dict:
        """Detect triple top/bottom patterns (very explosive when broken)"""
        signals = {}
        
        if len(df) < 60:  # Need enough data for pattern recognition
            return {'triple_pattern': 'INSUFFICIENT_DATA'}
        
        highs = df['High'].rolling(window=5).max()
        lows = df['Low'].rolling(window=5).min()
        
        # Find peaks (highs) and troughs (lows)
        recent_highs = highs.tail(30)
        recent_lows = lows.tail(30)
        
        # Triple top detection (bearish until broken)
        high_peaks = []
        for i in range(2, len(recent_highs)-2):
            if (recent_highs.iloc[i] > recent_highs.iloc[i-1] and 
                recent_highs.iloc[i] > recent_highs.iloc[i-2] and
                recent_highs.iloc[i] > recent_highs.iloc[i+1] and
                recent_highs.iloc[i] > recent_highs.iloc[i+2]):
                high_peaks.append(recent_highs.iloc[i])
        
        # Triple bottom detection (bullish pattern)
        low_troughs = []
        for i in range(2, len(recent_lows)-2):
            if (recent_lows.iloc[i] < recent_lows.iloc[i-1] and 
                recent_lows.iloc[i] < recent_lows.iloc[i-2] and
                recent_lows.iloc[i] < recent_lows.iloc[i+1] and
                recent_lows.iloc[i] < recent_lows.iloc[i+2]):
                low_troughs.append(recent_lows.iloc[i])
        
        current_price = df['Close'].iloc[-1]
        
        if len(high_peaks) >= 3:
            # Check if similar levels (within 3%)
            peak_range = (max(high_peaks[-3:]) - min(high_peaks[-3:])) / min(high_peaks[-3:])
            if peak_range < 0.03:
                resistance_level = max(high_peaks[-3:])
                if current_price > resistance_level * 1.01:  # Breakout above
                    signals['triple_pattern'] = 'TRIPLE_TOP_BREAKOUT'
                    signals['triple_pattern_strength'] = 95  # Very strong
                else:
                    signals['triple_pattern'] = 'TRIPLE_TOP_FORMING'
                    signals['triple_pattern_strength'] = 75
        
        if len(low_troughs) >= 3:
            trough_range = (max(low_troughs[-3:]) - min(low_troughs[-3:])) / min(low_troughs[-3:])
            if trough_range < 0.03:
                support_level = min(low_troughs[-3:])
                if current_price > support_level * 1.05:  # Bouncing off support
                    signals['triple_pattern'] = 'TRIPLE_BOTTOM_BOUNCE'
                    signals['triple_pattern_strength'] = 90
                else:
                    signals['triple_pattern'] = 'TRIPLE_BOTTOM_FORMING'
                    signals['triple_pattern_strength'] = 70
        
        if 'triple_pattern' not in signals:
            signals['triple_pattern'] = 'NONE'
            signals['triple_pattern_strength'] = 0
        
        return signals
    
    def _detect_double_patterns(self, df: pd.DataFrame) -> Dict:
        """Detect double top/bottom patterns"""
        signals = {}
        
        if len(df) < 40:
            return {'double_pattern': 'INSUFFICIENT_DATA'}
        
        # Look for two distinct peaks/troughs
        rolling_max = df['High'].rolling(window=10, center=True).max()
        rolling_min = df['Low'].rolling(window=10, center=True).min()
        
        # Find recent peaks and troughs
        recent_data = df.tail(40)
        peaks = []
        troughs = []
        
        for i in range(10, len(recent_data)-10):
            if recent_data['High'].iloc[i] == rolling_max.iloc[-40+i]:
                peaks.append((i, recent_data['High'].iloc[i]))
            if recent_data['Low'].iloc[i] == rolling_min.iloc[-40+i]:
                troughs.append((i, recent_data['Low'].iloc[i]))
        
        current_price = df['Close'].iloc[-1]
        
        # Double top detection
        if len(peaks) >= 2:
            last_two_peaks = peaks[-2:]
            peak1_price = last_two_peaks[0][1]
            peak2_price = last_two_peaks[1][1]
            
            # Check if peaks are similar (within 2%)
            if abs(peak1_price - peak2_price) / max(peak1_price, peak2_price) < 0.02:
                resistance = max(peak1_price, peak2_price)
                if current_price > resistance * 1.015:  # Breakout
                    signals['double_pattern'] = 'DOUBLE_TOP_BREAKOUT'
                    signals['double_pattern_strength'] = 85
                else:
                    signals['double_pattern'] = 'DOUBLE_TOP_FORMING'
                    signals['double_pattern_strength'] = 65
        
        # Double bottom detection
        if len(troughs) >= 2:
            last_two_troughs = troughs[-2:]
            trough1_price = last_two_troughs[0][1]
            trough2_price = last_two_troughs[1][1]
            
            if abs(trough1_price - trough2_price) / max(trough1_price, trough2_price) < 0.02:
                support = min(trough1_price, trough2_price)
                if current_price > support * 1.03:  # Bouncing up
                    signals['double_pattern'] = 'DOUBLE_BOTTOM_BOUNCE'
                    signals['double_pattern_strength'] = 80
                else:
                    signals['double_pattern'] = 'DOUBLE_BOTTOM_FORMING'
                    signals['double_pattern_strength'] = 60
        
        if 'double_pattern' not in signals:
            signals['double_pattern'] = 'NONE'
            signals['double_pattern_strength'] = 0
        
        return signals
    
    def _detect_bollinger_squeeze(self, df: pd.DataFrame) -> Dict:
        """Detect Bollinger Band squeeze - the 'boiler banger' setup"""
        signals = {}
        
        # Calculate Bollinger Bands
        rolling_mean = df['Close'].rolling(window=20).mean()
        rolling_std = df['Close'].rolling(window=20).std()
        
        upper_band = rolling_mean + (rolling_std * 2)
        lower_band = rolling_mean - (rolling_std * 2)
        
        # Band width (squeeze indicator)
        band_width = (upper_band - lower_band) / rolling_mean
        
        # Current vs historical band width
        current_width = band_width.iloc[-1]
        avg_width_50 = band_width.tail(50).mean()
        
        # Squeeze detection
        squeeze_ratio = current_width / avg_width_50
        
        if squeeze_ratio < 0.7:  # Bands are very tight
            signals['bollinger_squeeze'] = 'EXTREME_SQUEEZE'
            signals['squeeze_strength'] = 95
        elif squeeze_ratio < 0.8:
            signals['bollinger_squeeze'] = 'STRONG_SQUEEZE' 
            signals['squeeze_strength'] = 80
        elif squeeze_ratio < 0.9:
            signals['bollinger_squeeze'] = 'MODERATE_SQUEEZE'
            signals['squeeze_strength'] = 65
        else:
            signals['bollinger_squeeze'] = 'NONE'
            signals['squeeze_strength'] = 0
        
        # Check for breakout from squeeze
        current_price = df['Close'].iloc[-1]
        if current_price > upper_band.iloc[-1]:
            signals['squeeze_breakout'] = 'UPWARD_BREAKOUT'
            signals['breakout_strength'] = 90
        elif current_price < lower_band.iloc[-1]:
            signals['squeeze_breakout'] = 'DOWNWARD_BREAKOUT' 
            signals['breakout_strength'] = 75
        else:
            signals['squeeze_breakout'] = 'NONE'
            signals['breakout_strength'] = 0
        
        return signals
    
    def _detect_cup_and_handle(self, df: pd.DataFrame) -> Dict:
        """Detect cup and handle pattern - very bullish"""
        signals = {}
        
        if len(df) < 50:
            return {'cup_handle': 'INSUFFICIENT_DATA'}
        
        prices = df['Close'].tail(50)
        
        # Find the cup (U-shape)
        # Cup should have: high -> low -> high pattern
        first_third = prices.iloc[:17].max()
        middle_third = prices.iloc[17:34].min()
        last_third = prices.iloc[34:].max()
        
        # Cup criteria
        cup_depth = (first_third - middle_third) / first_third
        cup_recovery = (last_third - middle_third) / (first_third - middle_third)
        
        if (0.12 < cup_depth < 0.35 and  # 12-35% correction
            cup_recovery > 0.75 and      # Recovered 75%+ 
            abs(first_third - last_third) / first_third < 0.05):  # Similar highs
            
            # Look for handle (small pullback)
            recent_prices = prices.tail(10)
            handle_high = recent_prices.max()
            handle_low = recent_prices.min()
            handle_depth = (handle_high - handle_low) / handle_high
            
            current_price = df['Close'].iloc[-1]
            
            if handle_depth < 0.15:  # Handle pullback < 15%
                if current_price >= handle_high * 0.98:  # Near breakout
                    signals['cup_handle'] = 'CUP_HANDLE_BREAKOUT'
                    signals['cup_handle_strength'] = 90
                else:
                    signals['cup_handle'] = 'CUP_HANDLE_FORMING'
                    signals['cup_handle_strength'] = 75
            else:
                signals['cup_handle'] = 'CUP_FORMED'
                signals['cup_handle_strength'] = 60
        else:
            signals['cup_handle'] = 'NONE'
            signals['cup_handle_strength'] = 0
        
        return signals
    
    def _detect_triangle_patterns(self, df: pd.DataFrame) -> Dict:
        """Detect ascending/descending triangles"""
        signals = {}
        
        if len(df) < 30:
            return {'triangle_pattern': 'INSUFFICIENT_DATA'}
        
        recent_data = df.tail(30)
        highs = recent_data['High']
        lows = recent_data['Low']
        
        # Find trend in highs and lows
        high_trend = np.polyfit(range(len(highs)), highs, 1)[0]  # Slope
        low_trend = np.polyfit(range(len(lows)), lows, 1)[0]
        
        current_price = df['Close'].iloc[-1]
        recent_high = highs.tail(5).max()
        recent_low = lows.tail(5).min()
        
        # Ascending triangle (flat resistance, rising support)
        if abs(high_trend) < 0.01 and low_trend > 0.02:
            if current_price > recent_high * 1.01:  # Breakout
                signals['triangle_pattern'] = 'ASCENDING_BREAKOUT'
                signals['triangle_strength'] = 85
            else:
                signals['triangle_pattern'] = 'ASCENDING_FORMING'
                signals['triangle_strength'] = 70
        
        # Descending triangle (declining resistance, flat support)  
        elif high_trend < -0.02 and abs(low_trend) < 0.01:
            if current_price > recent_high * 1.02:  # Breakout above declining resistance
                signals['triangle_pattern'] = 'DESCENDING_BREAKOUT'
                signals['triangle_strength'] = 80
            else:
                signals['triangle_pattern'] = 'DESCENDING_FORMING'
                signals['triangle_strength'] = 50
        
        # Symmetrical triangle (converging lines)
        elif high_trend < -0.01 and low_trend > 0.01:
            range_compression = (recent_high - recent_low) / current_price
            if range_compression < 0.05:  # Very tight range
                signals['triangle_pattern'] = 'SYMMETRICAL_SQUEEZE'
                signals['triangle_strength'] = 75
            else:
                signals['triangle_pattern'] = 'SYMMETRICAL_FORMING'
                signals['triangle_strength'] = 55
        else:
            signals['triangle_pattern'] = 'NONE'
            signals['triangle_strength'] = 0
        
        return signals
    
    def _detect_flag_patterns(self, df: pd.DataFrame) -> Dict:
        """Detect flag and pennant patterns (continuation patterns)"""
        signals = {}
        
        if len(df) < 25:
            return {'flag_pattern': 'INSUFFICIENT_DATA'}
        
        # Look for strong move followed by consolidation
        prices = df['Close']
        
        # Check for strong initial move (flagpole)
        flagpole_start = prices.iloc[-20]
        flagpole_end = prices.iloc[-10]
        flagpole_move = (flagpole_end - flagpole_start) / flagpole_start
        
        if abs(flagpole_move) > 0.08:  # Strong 8%+ move
            # Check consolidation period (flag)
            consolidation = prices.tail(10)
            flag_range = (consolidation.max() - consolidation.min()) / consolidation.mean()
            
            current_price = prices.iloc[-1]
            
            if flag_range < 0.05:  # Tight consolidation
                if flagpole_move > 0:  # Bullish flag
                    if current_price > consolidation.max() * 1.005:  # Breakout
                        signals['flag_pattern'] = 'BULL_FLAG_BREAKOUT'
                        signals['flag_strength'] = 85
                    else:
                        signals['flag_pattern'] = 'BULL_FLAG_FORMING'
                        signals['flag_strength'] = 70
                else:  # Bear flag (less relevant for explosive screening)
                    signals['flag_pattern'] = 'BEAR_FLAG_FORMING'
                    signals['flag_strength'] = 40
            else:
                signals['flag_pattern'] = 'LOOSE_CONSOLIDATION'
                signals['flag_strength'] = 30
        else:
            signals['flag_pattern'] = 'NONE'
            signals['flag_strength'] = 0
        
        return signals
    
    def _calculate_penny_stock_signals(self, df: pd.DataFrame) -> Dict:
        """Special analysis for penny stocks with explosive potential"""
        signals = {}
        
        current_price = df['Close'].iloc[-1]
        
        # Penny stock classification
        if current_price < 1:
            signals['penny_tier'] = 'ULTRA_PENNY'  # Highest volatility
            volatility_multiplier = 2.0
        elif current_price < 5:
            signals['penny_tier'] = 'PENNY_STOCK'
            volatility_multiplier = 1.5
        else:
            signals['penny_tier'] = 'LOW_PRICE'
            volatility_multiplier = 1.2
        
        # Volume explosion detection (critical for penny stocks)
        volume_recent = df['Volume'].tail(5).mean()
        volume_baseline = df['Volume'].tail(50).mean()
        volume_explosion = volume_recent / max(volume_baseline, 1)
        
        if volume_explosion > 5:
            signals['penny_volume_signal'] = 'EXPLOSIVE_VOLUME'
            signals['penny_volume_strength'] = 95
        elif volume_explosion > 3:
            signals['penny_volume_signal'] = 'HIGH_VOLUME'
            signals['penny_volume_strength'] = 80
        elif volume_explosion > 1.5:
            signals['penny_volume_signal'] = 'ELEVATED_VOLUME'
            signals['penny_volume_strength'] = 60
        else:
            signals['penny_volume_signal'] = 'NORMAL_VOLUME'
            signals['penny_volume_strength'] = 20
        
        # Price explosion potential
        price_change_5d = (current_price - df['Close'].iloc[-5]) / df['Close'].iloc[-5] * 100
        
        if price_change_5d > 50:  # 50%+ move in 5 days
            signals['penny_momentum'] = 'EXPLOSIVE'
        elif price_change_5d > 25:
            signals['penny_momentum'] = 'STRONG'
        elif price_change_5d > 10:
            signals['penny_momentum'] = 'BUILDING'
        else:
            signals['penny_momentum'] = 'WEAK'
        
        # Apply volatility multiplier to scoring
        signals['penny_multiplier'] = volatility_multiplier
        
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