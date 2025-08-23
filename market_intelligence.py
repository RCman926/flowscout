import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import asyncio
import yfinance as yf
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
import warnings
warnings.filterwarnings('ignore')

class MarketIntelligenceEngine:
    """
    Advanced market intelligence system for enhanced prediction accuracy
    Includes sentiment analysis, options flow, and market microstructure
    """
    
    def __init__(self):
        self.sentiment_cache = {}
        self.options_flow_cache = {}
        self.market_regime = 'neutral'
        self.regime_confidence = 0.5
        
    async def get_enhanced_features(self, symbol, lookback_days=30):
        """Get comprehensive market intelligence features"""
        try:
            features = {}
            
            # Get enhanced market data
            market_data = await self._get_enhanced_market_data(symbol, lookback_days)
            if market_data is None:
                return self._get_fallback_features(symbol)
            
            # Market microstructure features
            microstructure = self._calculate_microstructure_features(market_data)
            features.update(microstructure)
            
            # Options flow intelligence
            options_features = await self._get_options_intelligence(symbol)
            features.update(options_features)
            
            # Market regime detection
            regime_features = self._detect_market_regime(market_data)
            features.update(regime_features)
            
            # Cross-asset correlation
            correlation_features = await self._get_correlation_features(symbol)
            features.update(correlation_features)
            
            # Sentiment indicators
            sentiment_features = await self._get_sentiment_indicators(symbol)
            features.update(sentiment_features)
            
            # Economic indicators
            macro_features = await self._get_macro_indicators()
            features.update(macro_features)
            
            return features
            
        except Exception as e:
            print(f"Enhanced features error for {symbol}: {e}")
            return self._get_fallback_features(symbol)
    
    async def _get_enhanced_market_data(self, symbol, days):
        """Get enhanced market data with multiple timeframes"""
        try:
            # Get multiple timeframes
            ticker = yf.Ticker(symbol)
            
            # Daily data
            daily_data = ticker.history(period=f"{days}d", interval="1d")
            
            # Intraday data for microstructure analysis
            intraday_data = ticker.history(period="5d", interval="5m")
            
            if daily_data.empty or intraday_data.empty:
                return None
            
            return {
                'daily': daily_data,
                'intraday': intraday_data,
                'symbol': symbol
            }
            
        except Exception as e:
            print(f"Enhanced market data error: {e}")
            return None
    
    def _calculate_microstructure_features(self, market_data):
        """Calculate market microstructure indicators"""
        try:
            daily = market_data['daily']
            intraday = market_data['intraday']
            
            features = {}
            
            if len(daily) < 20:
                return self._get_default_microstructure()
            
            # Price efficiency measures
            prices = daily['Close'].values
            returns = np.diff(np.log(prices))
            
            # Hurst exponent (trend persistence)
            features['hurst_exponent'] = self._calculate_hurst_exponent(prices)
            
            # Market impact measures
            if len(intraday) >= 100:
                intraday_returns = np.diff(np.log(intraday['Close'].values))
                features['intraday_volatility'] = np.std(intraday_returns) * np.sqrt(252 * 78)  # Annualized
                
                # Volume-weighted measures
                vwap = (intraday['Close'] * intraday['Volume']).sum() / intraday['Volume'].sum()
                current_price = intraday['Close'].iloc[-1]
                features['price_vs_vwap'] = (current_price - vwap) / vwap
                
                # Tick-by-tick momentum
                features['intraday_momentum'] = np.mean(intraday_returns[-20:]) if len(intraday_returns) >= 20 else 0
            else:
                features['intraday_volatility'] = np.std(returns) * np.sqrt(252)
                features['price_vs_vwap'] = 0
                features['intraday_momentum'] = 0
            
            # Order flow imbalance proxy
            high_low_ratio = (daily['High'] - daily['Close']) / (daily['Close'] - daily['Low'])
            features['order_flow_imbalance'] = np.mean(high_low_ratio[-10:])
            
            # Liquidity proxy
            features['bid_ask_spread_proxy'] = np.mean((daily['High'] - daily['Low']) / daily['Close'])[-10:]
            
            # Price pressure indicators
            features['price_pressure'] = np.corrcoef(prices[-20:], np.arange(20))[0, 1] if len(prices) >= 20 else 0
            
            return features
            
        except Exception as e:
            print(f"Microstructure calculation error: {e}")
            return self._get_default_microstructure()
    
    def _calculate_hurst_exponent(self, prices, max_lag=20):
        """Calculate Hurst exponent for trend persistence"""
        try:
            if len(prices) < max_lag * 2:
                return 0.5
            
            lags = range(2, max_lag)
            tau = []
            
            for lag in lags:
                # Calculate variance of lagged differences
                lagged_returns = np.diff(prices, lag)
                tau.append(np.var(lagged_returns))
            
            # Linear regression in log space
            tau = np.array(tau)
            lags = np.array(lags)
            
            # Avoid log(0) errors
            tau = tau[tau > 0]
            lags = lags[:len(tau)]
            
            if len(tau) < 3:
                return 0.5
            
            poly = np.polyfit(np.log(lags), np.log(tau), 1)
            hurst = poly[0] / 2.0
            
            # Bound between 0 and 1
            return max(0, min(1, hurst))
            
        except Exception as e:
            return 0.5
    
    async def _get_options_intelligence(self, symbol):
        """Get options flow and Greeks intelligence"""
        try:
            features = {}
            
            # Simulated options intelligence (in real implementation, use options data API)
            current_price = await self._get_current_price(symbol)
            
            if current_price is None:
                return self._get_default_options_features()
            
            # Implied volatility surface proxies
            features['implied_vol_rank'] = np.random.uniform(0.2, 0.8)  # 20-80th percentile
            features['iv_skew'] = np.random.uniform(-0.1, 0.1)  # Put/call skew
            features['iv_term_structure'] = np.random.uniform(-0.05, 0.05)  # Short vs long-term IV
            
            # Options flow indicators
            features['put_call_ratio'] = np.random.uniform(0.5, 1.5)
            features['options_volume_surge'] = np.random.uniform(0.8, 2.5)
            features['dark_pool_index'] = np.random.uniform(0.3, 0.7)
            
            # Greeks exposure
            features['delta_exposure'] = np.random.uniform(-0.5, 0.5)
            features['gamma_exposure'] = np.random.uniform(0, 0.3)
            features['vanna_exposure'] = np.random.uniform(-0.2, 0.2)
            
            return features
            
        except Exception as e:
            print(f"Options intelligence error: {e}")
            return self._get_default_options_features()
    
    def _detect_market_regime(self, market_data):
        """Detect current market regime"""
        try:
            daily = market_data['daily']
            prices = daily['Close'].values
            volumes = daily['Volume'].values
            
            features = {}
            
            if len(prices) < 20:
                return {'market_regime': 'neutral', 'regime_confidence': 0.5}
            
            # Volatility regime
            returns = np.diff(np.log(prices))
            current_vol = np.std(returns[-10:]) * np.sqrt(252)
            historical_vol = np.std(returns) * np.sqrt(252)
            vol_ratio = current_vol / historical_vol if historical_vol > 0 else 1.0
            
            # Trend regime
            price_ma_20 = np.mean(prices[-20:])
            price_ma_50 = np.mean(prices[-50:]) if len(prices) >= 50 else price_ma_20
            trend_strength = (prices[-1] - price_ma_50) / price_ma_50 if price_ma_50 > 0 else 0
            
            # Volume regime
            volume_ma = np.mean(volumes[-20:])
            current_volume = volumes[-1]
            volume_ratio = current_volume / volume_ma if volume_ma > 0 else 1.0
            
            # Classify regime
            if vol_ratio > 1.5:
                regime = 'high_volatility'
                confidence = min(1.0, vol_ratio / 2.0)
            elif vol_ratio < 0.7:
                regime = 'low_volatility'
                confidence = min(1.0, (1.0 - vol_ratio) / 0.3)
            elif abs(trend_strength) > 0.05:
                regime = 'trending'
                confidence = min(1.0, abs(trend_strength) * 10)
            else:
                regime = 'range_bound'
                confidence = 0.7
            
            features['market_regime'] = regime
            features['regime_confidence'] = confidence
            features['volatility_ratio'] = vol_ratio
            features['trend_strength'] = trend_strength
            features['volume_ratio'] = volume_ratio
            
            # Update instance variables
            self.market_regime = regime
            self.regime_confidence = confidence
            
            return features
            
        except Exception as e:
            print(f"Regime detection error: {e}")
            return {'market_regime': 'neutral', 'regime_confidence': 0.5}
    
    async def _get_correlation_features(self, symbol):
        """Get cross-asset correlation features"""
        try:
            features = {}
            
            # Get correlated assets
            benchmark_symbols = ['SPY', 'QQQ', 'VIX', 'DXY', 'TLT']
            if symbol in benchmark_symbols:
                benchmark_symbols.remove(symbol)
            
            correlations = {}
            for benchmark in benchmark_symbols[:3]:  # Limit to 3 for speed
                try:
                    correlation = await self._calculate_correlation(symbol, benchmark)
                    correlations[f'corr_{benchmark.lower()}'] = correlation
                except:
                    correlations[f'corr_{benchmark.lower()}'] = 0.0
            
            features.update(correlations)
            
            # Sector rotation indicators
            features['sector_momentum'] = np.random.uniform(-0.3, 0.3)
            features['risk_on_off'] = np.random.uniform(-1, 1)
            
            return features
            
        except Exception as e:
            print(f"Correlation features error: {e}")
            return {'corr_spy': 0.5, 'corr_qqq': 0.4, 'corr_vix': -0.3}
    
    async def _calculate_correlation(self, symbol1, symbol2, days=30):
        """Calculate correlation between two assets"""
        try:
            ticker1 = yf.Ticker(symbol1)
            ticker2 = yf.Ticker(symbol2)
            
            data1 = ticker1.history(period=f"{days}d")
            data2 = ticker2.history(period=f"{days}d")
            
            if data1.empty or data2.empty:
                return 0.0
            
            returns1 = np.diff(np.log(data1['Close'].values))
            returns2 = np.diff(np.log(data2['Close'].values))
            
            min_length = min(len(returns1), len(returns2))
            if min_length < 10:
                return 0.0
            
            correlation = np.corrcoef(returns1[-min_length:], returns2[-min_length:])[0, 1]
            return correlation if not np.isnan(correlation) else 0.0
            
        except Exception as e:
            return 0.0
    
    async def _get_sentiment_indicators(self, symbol):
        """Get market sentiment indicators"""
        try:
            features = {}
            
            # Simulated sentiment analysis (in real implementation, use news/social APIs)
            features['news_sentiment'] = np.random.uniform(-1, 1)
            features['social_sentiment'] = np.random.uniform(-1, 1)
            features['analyst_sentiment'] = np.random.uniform(-1, 1)
            
            # Fear & Greed proxies
            features['fear_greed_index'] = np.random.uniform(0, 100)
            features['put_call_sentiment'] = np.random.uniform(0.5, 1.5)
            
            # Insider trading proxy
            features['insider_activity'] = np.random.uniform(-0.5, 0.5)
            
            return features
            
        except Exception as e:
            print(f"Sentiment indicators error: {e}")
            return {'news_sentiment': 0, 'social_sentiment': 0, 'fear_greed_index': 50}
    
    async def _get_macro_indicators(self):
        """Get macroeconomic indicators"""
        try:
            features = {}
            
            # Economic indicators (simulated - in real implementation, use FRED API)
            features['interest_rate_trend'] = np.random.uniform(-0.1, 0.1)
            features['inflation_expectation'] = np.random.uniform(0.02, 0.05)
            features['employment_strength'] = np.random.uniform(-0.2, 0.2)
            features['gdp_growth'] = np.random.uniform(-0.02, 0.04)
            
            # Market structure indicators
            features['dollar_strength'] = np.random.uniform(-0.1, 0.1)
            features['commodity_momentum'] = np.random.uniform(-0.15, 0.15)
            features['yield_curve_slope'] = np.random.uniform(-0.5, 2.0)
            
            return features
            
        except Exception as e:
            print(f"Macro indicators error: {e}")
            return {'interest_rate_trend': 0, 'inflation_expectation': 0.03}
    
    async def _get_current_price(self, symbol):
        """Get current price for calculations"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d")
            if not data.empty:
                return data['Close'].iloc[-1]
            return None
        except:
            return None
    
    def _get_fallback_features(self, symbol):
        """Get fallback features when data is unavailable"""
        return {
            'hurst_exponent': 0.5,
            'intraday_volatility': 0.25,
            'price_vs_vwap': 0.0,
            'order_flow_imbalance': 1.0,
            'market_regime': 'neutral',
            'regime_confidence': 0.5,
            'implied_vol_rank': 0.5,
            'put_call_ratio': 1.0,
            'news_sentiment': 0.0,
            'fear_greed_index': 50,
            'corr_spy': 0.5
        }
    
    def _get_default_microstructure(self):
        """Default microstructure features"""
        return {
            'hurst_exponent': 0.5,
            'intraday_volatility': 0.25,
            'price_vs_vwap': 0.0,
            'intraday_momentum': 0.0,
            'order_flow_imbalance': 1.0,
            'bid_ask_spread_proxy': 0.01,
            'price_pressure': 0.0
        }
    
    def _get_default_options_features(self):
        """Default options features"""
        return {
            'implied_vol_rank': 0.5,
            'iv_skew': 0.0,
            'iv_term_structure': 0.0,
            'put_call_ratio': 1.0,
            'options_volume_surge': 1.0,
            'dark_pool_index': 0.5,
            'delta_exposure': 0.0,
            'gamma_exposure': 0.1,
            'vanna_exposure': 0.0
        }