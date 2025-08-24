"""
MARKET STRUCTURE ANALYZER
Detects market maker activity, dark pools, and institutional flow patterns
"""

import numpy as np
import pandas as pd
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import yfinance as yf


class MarketStructureAnalyzer:
    """Advanced market microstructure analysis for institutional trading"""
    
    def __init__(self):
        self.cache_duration = 60  # 1 minute cache
        self.analysis_cache = {}
    
    async def analyze_market_structure(self, symbol: str) -> Dict:
        """Comprehensive market structure analysis"""
        try:
            # Check cache
            cache_key = f"structure_{symbol}"
            if self._is_cache_valid(cache_key):
                return self.analysis_cache[cache_key]
            
            # Get market data
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d", interval="1m")
            
            if hist.empty:
                return self._empty_analysis(symbol)
            
            analysis = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'market_maker_activity': await self._detect_market_maker_activity(hist),
                'dark_pool_estimate': await self._estimate_dark_pool_activity(hist),
                'institutional_flow': await self._detect_institutional_flow(hist),
                'liquidity_analysis': await self._analyze_liquidity_layers(hist),
                'volatility_regime': await self._classify_volatility_regime(hist),
                'trend_strength': await self._calculate_trend_strength(hist),
                'support_resistance': await self._identify_key_levels(hist),
                'market_regime': 'NORMAL'  # TRENDING, RANGING, VOLATILE, NORMAL
            }
            
            # Determine overall market regime
            analysis['market_regime'] = self._classify_market_regime(analysis)
            
            # Cache result
            self.analysis_cache[cache_key] = analysis
            return analysis
            
        except Exception as e:
            print(f"Error analyzing market structure for {symbol}: {e}")
            return self._empty_analysis(symbol)
    
    async def _detect_market_maker_activity(self, data: pd.DataFrame) -> Dict:
        """Detect market maker presence and activity patterns"""
        try:
            # Volume-weighted average price analysis
            vwap = (data['Close'] * data['Volume']).cumsum() / data['Volume'].cumsum()
            
            # Price clustering analysis (market maker support/resistance)
            closes = data['Close'].values
            price_levels = {}
            
            # Count price level frequency (simplified)
            for price in closes:
                rounded_price = round(price, 2)
                price_levels[rounded_price] = price_levels.get(rounded_price, 0) + 1
            
            # Find most frequent price levels (market maker levels)
            frequent_levels = sorted(price_levels.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Bid-ask spread analysis (proxy from price volatility)
            price_changes = np.abs(data['Close'].pct_change()).dropna()
            avg_spread_proxy = price_changes.mean()
            
            # Market maker strength score
            mm_strength = 0.0
            if len(frequent_levels) > 0:
                max_frequency = frequent_levels[0][1]
                total_bars = len(data)
                mm_strength = min(1.0, max_frequency / (total_bars * 0.1))  # Normalized
            
            return {
                'presence_detected': mm_strength > 0.3,
                'strength_score': round(mm_strength, 3),
                'key_levels': [level[0] for level in frequent_levels[:3]],
                'avg_spread_proxy': round(avg_spread_proxy, 4),
                'vwap_deviation': round(abs(data['Close'].iloc[-1] - vwap.iloc[-1]), 2),
                'activity_level': 'HIGH' if mm_strength > 0.7 else 'MEDIUM' if mm_strength > 0.3 else 'LOW'
            }
            
        except Exception as e:
            return {
                'presence_detected': False,
                'strength_score': 0.0,
                'key_levels': [],
                'avg_spread_proxy': 0.0,
                'vwap_deviation': 0.0,
                'activity_level': 'UNKNOWN'
            }
    
    async def _estimate_dark_pool_activity(self, data: pd.DataFrame) -> Dict:
        """Estimate dark pool trading activity"""
        try:
            # Volume analysis for dark pool detection
            volume_ma = data['Volume'].rolling(20).mean()
            recent_volume = data['Volume'].tail(10).mean()
            
            # Price impact analysis (low impact = potential dark pool)
            returns = data['Close'].pct_change().dropna()
            volume_normalized = data['Volume'] / data['Volume'].mean()
            
            # Calculate volume-price correlation
            correlation_data = pd.DataFrame({
                'returns': returns.tail(len(volume_normalized)),
                'volume': volume_normalized.tail(len(returns))
            }).dropna()
            
            price_impact = 0.0
            if len(correlation_data) > 10:
                price_impact = abs(correlation_data.corr().iloc[0, 1])
            
            # Dark pool estimate (inverse of price impact)
            dark_pool_estimate = max(0.0, 1.0 - price_impact) if price_impact > 0 else 0.5
            
            # Volume pattern analysis
            volume_consistency = 1.0 - (data['Volume'].std() / data['Volume'].mean())
            volume_consistency = max(0.0, min(1.0, volume_consistency))
            
            return {
                'estimated_percentage': round(dark_pool_estimate * 100, 1),
                'confidence': round((dark_pool_estimate + volume_consistency) / 2, 3),
                'volume_consistency': round(volume_consistency, 3),
                'price_impact_score': round(price_impact, 3),
                'interpretation': self._interpret_dark_pool_activity(dark_pool_estimate)
            }
            
        except Exception as e:
            return {
                'estimated_percentage': 0.0,
                'confidence': 0.0,
                'volume_consistency': 0.0,
                'price_impact_score': 0.0,
                'interpretation': 'ANALYSIS_ERROR'
            }
    
    async def _detect_institutional_flow(self, data: pd.DataFrame) -> Dict:
        """Detect institutional order flow patterns"""
        try:
            # Large volume spikes detection
            volume_threshold = data['Volume'].quantile(0.9)  # Top 10% volume
            large_volume_bars = data[data['Volume'] > volume_threshold]
            
            # Time-based analysis (institutional activity patterns)
            data['hour'] = pd.to_datetime(data.index).hour
            hourly_volume = data.groupby('hour')['Volume'].mean()
            
            # Institutional hours (9:30-11:30 AM, 2:00-4:00 PM ET)
            institutional_hours = [9, 10, 11, 14, 15]
            inst_volume = hourly_volume.loc[hourly_volume.index.isin(institutional_hours)].mean()
            retail_volume = hourly_volume.loc[~hourly_volume.index.isin(institutional_hours)].mean()
            
            institutional_ratio = inst_volume / retail_volume if retail_volume > 0 else 1.0
            
            # Block trade detection (simplified)
            avg_trade_size = data['Volume'].mean()
            large_trades = len(large_volume_bars)
            block_trade_frequency = large_trades / len(data) if len(data) > 0 else 0.0
            
            # Flow direction analysis
            price_volume_correlation = data['Close'].pct_change().corr(data['Volume'].pct_change())
            
            flow_direction = 'NEUTRAL'
            if price_volume_correlation > 0.3:
                flow_direction = 'BUYING'
            elif price_volume_correlation < -0.3:
                flow_direction = 'SELLING'
            
            return {
                'institutional_ratio': round(institutional_ratio, 2),
                'block_trade_frequency': round(block_trade_frequency, 3),
                'large_volume_count': large_trades,
                'flow_direction': flow_direction,
                'flow_strength': round(abs(price_volume_correlation), 3),
                'activity_score': round(min(1.0, (institutional_ratio - 1.0) * block_trade_frequency * 10), 3)
            }
            
        except Exception as e:
            return {
                'institutional_ratio': 1.0,
                'block_trade_frequency': 0.0,
                'large_volume_count': 0,
                'flow_direction': 'NEUTRAL',
                'flow_strength': 0.0,
                'activity_score': 0.0
            }
    
    async def _analyze_liquidity_layers(self, data: pd.DataFrame) -> Dict:
        """Analyze market liquidity and depth"""
        try:
            # Liquidity estimation based on volume and price stability
            returns = data['Close'].pct_change().dropna()
            volume_normalized = data['Volume'] / data['Volume'].mean()
            
            # Liquidity score (high volume + low volatility = high liquidity)
            volatility = returns.std()
            avg_volume = data['Volume'].mean()
            
            liquidity_score = (avg_volume / 1000000) / (volatility * 100)  # Normalized
            liquidity_score = min(1.0, liquidity_score)
            
            # Bid-ask spread proxy
            high_low_spread = ((data['High'] - data['Low']) / data['Close']).mean()
            
            # Market depth estimation
            volume_quartiles = data['Volume'].quantile([0.25, 0.5, 0.75])
            depth_consistency = 1.0 - (volume_quartiles.iloc[2] - volume_quartiles.iloc[0]) / volume_quartiles.iloc[1]
            depth_consistency = max(0.0, min(1.0, depth_consistency))
            
            return {
                'liquidity_score': round(liquidity_score, 3),
                'avg_spread_proxy': round(high_low_spread, 4),
                'depth_consistency': round(depth_consistency, 3),
                'volume_profile': {
                    'avg_volume': int(avg_volume),
                    'volume_std': int(data['Volume'].std()),
                    'peak_volume': int(data['Volume'].max())
                },
                'liquidity_rating': self._rate_liquidity(liquidity_score)
            }
            
        except Exception as e:
            return {
                'liquidity_score': 0.0,
                'avg_spread_proxy': 0.0,
                'depth_consistency': 0.0,
                'volume_profile': {'avg_volume': 0, 'volume_std': 0, 'peak_volume': 0},
                'liquidity_rating': 'UNKNOWN'
            }
    
    async def _classify_volatility_regime(self, data: pd.DataFrame) -> Dict:
        """Classify current volatility regime"""
        try:
            returns = data['Close'].pct_change().dropna()
            
            # Short-term volatility (1-hour)
            short_vol = returns.tail(60).std() * np.sqrt(252 * 24 * 60)  # Annualized
            
            # Medium-term volatility (4-hour)
            medium_vol = returns.tail(240).std() * np.sqrt(252 * 6)  # Annualized
            
            # Long-term volatility (daily)
            long_vol = returns.std() * np.sqrt(252)  # Annualized
            
            # Volatility clustering (GARCH-like effect)
            vol_persistence = returns.tail(100).rolling(10).std().autocorr(1)
            vol_persistence = max(0.0, vol_persistence) if not np.isnan(vol_persistence) else 0.0
            
            # Regime classification
            if short_vol > 0.5:
                regime = 'HIGH_VOLATILITY'
            elif short_vol > 0.3:
                regime = 'ELEVATED_VOLATILITY'
            elif short_vol > 0.15:
                regime = 'NORMAL_VOLATILITY'
            else:
                regime = 'LOW_VOLATILITY'
            
            return {
                'regime': regime,
                'short_term_vol': round(short_vol, 3),
                'medium_term_vol': round(medium_vol, 3),
                'long_term_vol': round(long_vol, 3),
                'volatility_persistence': round(vol_persistence, 3),
                'volatility_trend': 'INCREASING' if short_vol > medium_vol else 'DECREASING'
            }
            
        except Exception as e:
            return {
                'regime': 'UNKNOWN',
                'short_term_vol': 0.0,
                'medium_term_vol': 0.0,
                'long_term_vol': 0.0,
                'volatility_persistence': 0.0,
                'volatility_trend': 'STABLE'
            }
    
    async def _calculate_trend_strength(self, data: pd.DataFrame) -> Dict:
        """Calculate trend strength using multiple methods"""
        try:
            closes = data['Close'].values
            
            # ADX-like calculation (simplified)
            returns = np.diff(closes)
            up_moves = np.where(returns > 0, returns, 0)
            down_moves = np.where(returns < 0, np.abs(returns), 0)
            
            # Trend strength
            trend_strength = (np.sum(up_moves) - np.sum(down_moves)) / np.sum(np.abs(returns))
            trend_strength = max(-1.0, min(1.0, trend_strength))  # Normalize to [-1, 1]
            
            # Moving average slope
            ma_20 = pd.Series(closes).rolling(20).mean()
            ma_slope = (ma_20.iloc[-1] - ma_20.iloc[-5]) / ma_20.iloc[-5] if len(ma_20) > 5 else 0.0
            
            # Trend consistency
            price_above_ma = np.sum(closes[-20:] > ma_20.tail(20)) / 20 if len(closes) >= 20 else 0.5
            
            return {
                'trend_strength': round(trend_strength, 3),
                'trend_direction': 'BULLISH' if trend_strength > 0.1 else 'BEARISH' if trend_strength < -0.1 else 'NEUTRAL',
                'ma_slope': round(ma_slope, 4),
                'trend_consistency': round(abs(price_above_ma - 0.5) * 2, 3),  # 0 = inconsistent, 1 = very consistent
                'strength_rating': self._rate_trend_strength(abs(trend_strength))
            }
            
        except Exception as e:
            return {
                'trend_strength': 0.0,
                'trend_direction': 'NEUTRAL',
                'ma_slope': 0.0,
                'trend_consistency': 0.0,
                'strength_rating': 'WEAK'
            }
    
    async def _identify_key_levels(self, data: pd.DataFrame) -> Dict:
        """Identify key support and resistance levels"""
        try:
            closes = data['Close'].values
            highs = data['High'].values
            lows = data['Low'].values
            
            current_price = closes[-1]
            
            # Support levels (recent lows)
            recent_lows = []
            for i in range(len(lows) - 10, len(lows)):
                if i > 5 and i < len(lows) - 5:
                    if lows[i] == min(lows[i-5:i+5]):  # Local minimum
                        recent_lows.append(lows[i])
            
            # Resistance levels (recent highs)
            recent_highs = []
            for i in range(len(highs) - 10, len(highs)):
                if i > 5 and i < len(highs) - 5:
                    if highs[i] == max(highs[i-5:i+5]):  # Local maximum
                        recent_highs.append(highs[i])
            
            # Find closest levels
            support_levels = sorted([level for level in recent_lows if level < current_price], reverse=True)[:3]
            resistance_levels = sorted([level for level in recent_highs if level > current_price])[:3]
            
            return {
                'current_price': round(current_price, 2),
                'support_levels': [round(level, 2) for level in support_levels],
                'resistance_levels': [round(level, 2) for level in resistance_levels],
                'nearest_support': round(support_levels[0], 2) if support_levels else None,
                'nearest_resistance': round(resistance_levels[0], 2) if resistance_levels else None,
                'support_distance': round((current_price - support_levels[0]) / current_price * 100, 1) if support_levels else None,
                'resistance_distance': round((resistance_levels[0] - current_price) / current_price * 100, 1) if resistance_levels else None
            }
            
        except Exception as e:
            return {
                'current_price': 0.0,
                'support_levels': [],
                'resistance_levels': [],
                'nearest_support': None,
                'nearest_resistance': None,
                'support_distance': None,
                'resistance_distance': None
            }
    
    def _classify_market_regime(self, analysis: Dict) -> str:
        """Classify overall market regime"""
        try:
            vol_regime = analysis.get('volatility_regime', {}).get('regime', 'NORMAL_VOLATILITY')
            trend_direction = analysis.get('trend_strength', {}).get('trend_direction', 'NEUTRAL')
            trend_strength = abs(analysis.get('trend_strength', {}).get('trend_strength', 0.0))
            
            if vol_regime in ['HIGH_VOLATILITY', 'ELEVATED_VOLATILITY']:
                return 'VOLATILE'
            elif trend_direction != 'NEUTRAL' and trend_strength > 0.3:
                return 'TRENDING'
            elif trend_strength < 0.1:
                return 'RANGING'
            else:
                return 'NORMAL'
                
        except Exception as e:
            return 'NORMAL'
    
    def _interpret_dark_pool_activity(self, estimate: float) -> str:
        """Interpret dark pool activity level"""
        if estimate > 0.7:
            return 'HIGH_DARK_POOL_ACTIVITY'
        elif estimate > 0.4:
            return 'MODERATE_DARK_POOL_ACTIVITY'
        elif estimate > 0.2:
            return 'LOW_DARK_POOL_ACTIVITY'
        else:
            return 'MINIMAL_DARK_POOL_ACTIVITY'
    
    def _rate_liquidity(self, score: float) -> str:
        """Rate liquidity level"""
        if score > 0.8:
            return 'EXCELLENT'
        elif score > 0.6:
            return 'GOOD'
        elif score > 0.4:
            return 'MODERATE'
        elif score > 0.2:
            return 'POOR'
        else:
            return 'VERY_POOR'
    
    def _rate_trend_strength(self, strength: float) -> str:
        """Rate trend strength"""
        if strength > 0.6:
            return 'VERY_STRONG'
        elif strength > 0.4:
            return 'STRONG'
        elif strength > 0.2:
            return 'MODERATE'
        elif strength > 0.1:
            return 'WEAK'
        else:
            return 'VERY_WEAK'
    
    def _empty_analysis(self, symbol: str) -> Dict:
        """Return empty analysis structure"""
        return {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'market_maker_activity': {'presence_detected': False, 'strength_score': 0.0, 'activity_level': 'UNKNOWN'},
            'dark_pool_estimate': {'estimated_percentage': 0.0, 'interpretation': 'NO_DATA'},
            'institutional_flow': {'flow_direction': 'NEUTRAL', 'activity_score': 0.0},
            'liquidity_analysis': {'liquidity_rating': 'UNKNOWN'},
            'volatility_regime': {'regime': 'UNKNOWN'},
            'trend_strength': {'trend_direction': 'NEUTRAL', 'strength_rating': 'UNKNOWN'},
            'support_resistance': {'current_price': 0.0},
            'market_regime': 'UNKNOWN'
        }
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.analysis_cache:
            return False
        
        cached_time = datetime.fromisoformat(self.analysis_cache[cache_key]['timestamp'])
        return (datetime.now() - cached_time).seconds < self.cache_duration


# Global market structure analyzer instance
market_analyzer = MarketStructureAnalyzer()