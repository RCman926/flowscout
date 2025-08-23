import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import talib as ta

class AdvancedTechnicalAnalyzer:
    """
    Advanced multi-timeframe technical analysis for institutional-grade decisions
    """
    
    def __init__(self):
        self.timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        self.indicator_weights = {
            'trend': 0.3,
            'momentum': 0.25,
            'volatility': 0.2,
            'volume': 0.15,
            'support_resistance': 0.1
        }
        
    async def analyze_multi_timeframe(self, price_data: np.ndarray, volume_data: np.ndarray) -> Dict:
        """
        Perform comprehensive multi-timeframe technical analysis
        """
        try:
            analysis_results = {}
            
            # 1. Trend Analysis
            trend_analysis = self._analyze_trend_structure(price_data)
            analysis_results['trend'] = trend_analysis
            
            # 2. Advanced Momentum Analysis
            momentum_analysis = self._analyze_advanced_momentum(price_data)
            analysis_results['momentum'] = momentum_analysis
            
            # 3. Volatility Analysis
            volatility_analysis = self._analyze_volatility_patterns(price_data)
            analysis_results['volatility'] = volatility_analysis
            
            # 4. Volume Profile Analysis
            volume_analysis = self._analyze_volume_profile(price_data, volume_data)
            analysis_results['volume'] = volume_analysis
            
            # 5. Support/Resistance Analysis
            support_resistance = self._identify_key_levels(price_data)
            analysis_results['support_resistance'] = support_resistance
            
            # 6. Pattern Recognition
            patterns = self._recognize_chart_patterns(price_data)
            analysis_results['patterns'] = patterns
            
            # 7. Generate Composite Score
            composite_score = self._calculate_composite_score(analysis_results)
            analysis_results['composite_score'] = composite_score
            
            return analysis_results
            
        except Exception as e:
            print(f"Advanced technical analysis error: {e}")
            return self._fallback_analysis()
    
    def _analyze_trend_structure(self, price_data: np.ndarray) -> Dict:
        """Analyze multi-timeframe trend structure"""
        try:
            results = {}
            
            # Moving averages for trend identification
            if len(price_data) >= 200:
                ma_20 = np.mean(price_data[-20:])
                ma_50 = np.mean(price_data[-50:])
                ma_200 = np.mean(price_data[-200:])
                current_price = price_data[-1]
                
                # Trend strength calculation
                if current_price > ma_20 > ma_50 > ma_200:
                    trend_strength = 'very_strong_bullish'
                    trend_score = 1.0
                elif current_price > ma_20 > ma_50:
                    trend_strength = 'strong_bullish'
                    trend_score = 0.75
                elif current_price > ma_20:
                    trend_strength = 'bullish'
                    trend_score = 0.5
                elif current_price < ma_20 < ma_50 < ma_200:
                    trend_strength = 'very_strong_bearish'
                    trend_score = -1.0
                elif current_price < ma_20 < ma_50:
                    trend_strength = 'strong_bearish'
                    trend_score = -0.75
                elif current_price < ma_20:
                    trend_strength = 'bearish'
                    trend_score = -0.5
                else:
                    trend_strength = 'sideways'
                    trend_score = 0.0
                
                # Trend consistency
                price_changes = np.diff(price_data[-20:])
                positive_changes = np.sum(price_changes > 0)
                trend_consistency = positive_changes / len(price_changes)
                
                results = {
                    'strength': trend_strength,
                    'score': trend_score,
                    'consistency': trend_consistency,
                    'ma_20': ma_20,
                    'ma_50': ma_50,
                    'ma_200': ma_200,
                    'current_vs_ma20': (current_price - ma_20) / ma_20,
                    'confidence': abs(trend_score) * trend_consistency
                }
            else:
                # Fallback for limited data
                if len(price_data) >= 5:
                    recent_trend = (price_data[-1] - price_data[-5]) / price_data[-5]
                    if recent_trend > 0.02:
                        results = {'strength': 'bullish', 'score': 0.6, 'confidence': 0.5}
                    elif recent_trend < -0.02:
                        results = {'strength': 'bearish', 'score': -0.6, 'confidence': 0.5}
                    else:
                        results = {'strength': 'sideways', 'score': 0.0, 'confidence': 0.3}
                else:
                    results = {'strength': 'unknown', 'score': 0.0, 'confidence': 0.1}
            
            return results
            
        except Exception as e:
            return {'strength': 'unknown', 'score': 0.0, 'confidence': 0.1, 'error': str(e)}
    
    def _analyze_advanced_momentum(self, price_data: np.ndarray) -> Dict:
        """Advanced momentum analysis with multiple indicators"""
        try:
            results = {}
            
            if len(price_data) >= 30:
                # RSI with multiple periods
                rsi_14 = self._calculate_rsi(price_data, 14)
                rsi_21 = self._calculate_rsi(price_data, 21)
                
                # Stochastic oscillator
                stoch_k, stoch_d = self._calculate_stochastic(price_data)
                
                # Williams %R
                williams_r = self._calculate_williams_r(price_data)
                
                # MACD
                macd_line, macd_signal, macd_histogram = self._calculate_macd(price_data)
                
                # Momentum score calculation
                momentum_signals = []
                
                # RSI signals
                if rsi_14 < 30 and rsi_21 < 35:
                    momentum_signals.append(0.8)  # Strong oversold
                elif rsi_14 < 40:
                    momentum_signals.append(0.4)  # Oversold
                elif rsi_14 > 70 and rsi_21 > 65:
                    momentum_signals.append(-0.8)  # Strong overbought
                elif rsi_14 > 60:
                    momentum_signals.append(-0.4)  # Overbought
                else:
                    momentum_signals.append(0.0)
                
                # Stochastic signals
                if stoch_k < 20 and stoch_d < 20:
                    momentum_signals.append(0.6)
                elif stoch_k > 80 and stoch_d > 80:
                    momentum_signals.append(-0.6)
                else:
                    momentum_signals.append(0.0)
                
                # MACD signals
                if macd_line > macd_signal and macd_histogram > 0:
                    momentum_signals.append(0.7)
                elif macd_line < macd_signal and macd_histogram < 0:
                    momentum_signals.append(-0.7)
                else:
                    momentum_signals.append(0.0)
                
                # Calculate composite momentum score
                momentum_score = np.mean(momentum_signals)
                momentum_strength = abs(momentum_score)
                
                results = {
                    'rsi_14': rsi_14,
                    'rsi_21': rsi_21,
                    'stoch_k': stoch_k,
                    'stoch_d': stoch_d,
                    'williams_r': williams_r,
                    'macd_line': macd_line,
                    'macd_signal': macd_signal,
                    'macd_histogram': macd_histogram,
                    'momentum_score': momentum_score,
                    'momentum_strength': momentum_strength,
                    'signal_direction': 'bullish' if momentum_score > 0.2 else 'bearish' if momentum_score < -0.2 else 'neutral',
                    'confidence': momentum_strength
                }
            else:
                # Fallback for limited data
                if len(price_data) >= 5:
                    price_momentum = (price_data[-1] - price_data[-5]) / price_data[-5]
                    results = {
                        'momentum_score': np.clip(price_momentum * 10, -1, 1),
                        'confidence': 0.3,
                        'signal_direction': 'bullish' if price_momentum > 0 else 'bearish'
                    }
                else:
                    results = {'momentum_score': 0.0, 'confidence': 0.1, 'signal_direction': 'neutral'}
            
            return results
            
        except Exception as e:
            return {'momentum_score': 0.0, 'confidence': 0.1, 'signal_direction': 'neutral', 'error': str(e)}
    
    def _analyze_volatility_patterns(self, price_data: np.ndarray) -> Dict:
        """Analyze volatility patterns and regimes"""
        try:
            results = {}
            
            if len(price_data) >= 20:
                # Calculate returns
                returns = np.diff(np.log(price_data))
                
                # Historical volatility (annualized)
                hist_vol = np.std(returns) * np.sqrt(252) * 100
                
                # Rolling volatility
                if len(returns) >= 10:
                    recent_vol = np.std(returns[-10:]) * np.sqrt(252) * 100
                    vol_ratio = recent_vol / hist_vol if hist_vol > 0 else 1.0
                else:
                    recent_vol = hist_vol
                    vol_ratio = 1.0
                
                # Volatility regime classification
                if vol_ratio > 1.5:
                    vol_regime = 'high_volatility'
                    vol_score = -0.3  # High vol generally negative for directional trades
                elif vol_ratio < 0.7:
                    vol_regime = 'low_volatility'
                    vol_score = 0.2  # Low vol good for trend following
                else:
                    vol_regime = 'normal_volatility'
                    vol_score = 0.0
                
                # Bollinger Bands for volatility context
                bb_upper, bb_lower, bb_middle = self._calculate_bollinger_bands(price_data)
                current_price = price_data[-1]
                bb_position = (current_price - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5
                
                results = {
                    'historical_volatility': hist_vol,
                    'recent_volatility': recent_vol,
                    'volatility_ratio': vol_ratio,
                    'volatility_regime': vol_regime,
                    'volatility_score': vol_score,
                    'bb_position': bb_position,
                    'bb_squeeze': (bb_upper - bb_lower) / bb_middle < 0.1,  # Low volatility squeeze
                    'confidence': min(1.0, len(returns) / 20)
                }
            else:
                results = {
                    'volatility_regime': 'unknown',
                    'volatility_score': 0.0,
                    'confidence': 0.1
                }
            
            return results
            
        except Exception as e:
            return {'volatility_regime': 'unknown', 'volatility_score': 0.0, 'confidence': 0.1, 'error': str(e)}
    
    def _analyze_volume_profile(self, price_data: np.ndarray, volume_data: np.ndarray) -> Dict:
        """Advanced volume profile analysis"""
        try:
            results = {}
            
            if len(volume_data) >= 20:
                # Volume moving averages
                volume_ma_10 = np.mean(volume_data[-10:])
                volume_ma_20 = np.mean(volume_data[-20:])
                current_volume = volume_data[-1]
                
                # Volume ratio analysis
                volume_ratio = current_volume / volume_ma_20 if volume_ma_20 > 0 else 1.0
                
                # Price-volume relationship
                price_changes = np.diff(price_data[-len(volume_data):])
                volume_changes = np.diff(volume_data)
                
                if len(price_changes) > 0 and len(volume_changes) > 0:
                    # Correlation between price and volume changes
                    correlation = np.corrcoef(price_changes[-min(len(price_changes), len(volume_changes)):], 
                                            volume_changes[-min(len(price_changes), len(volume_changes)):])[0, 1]
                    if np.isnan(correlation):
                        correlation = 0.0
                else:
                    correlation = 0.0
                
                # Volume trend
                if volume_ma_10 > volume_ma_20 * 1.1:
                    volume_trend = 'increasing'
                    volume_score = 0.3
                elif volume_ma_10 < volume_ma_20 * 0.9:
                    volume_trend = 'decreasing'
                    volume_score = -0.2
                else:
                    volume_trend = 'stable'
                    volume_score = 0.0
                
                # Exceptional volume detection
                if volume_ratio > 3.0:
                    volume_anomaly = 'exceptional_high'
                    volume_score += 0.5
                elif volume_ratio < 0.3:
                    volume_anomaly = 'exceptionally_low'
                    volume_score -= 0.3
                else:
                    volume_anomaly = 'normal'
                
                results = {
                    'current_volume': current_volume,
                    'volume_ma_10': volume_ma_10,
                    'volume_ma_20': volume_ma_20,
                    'volume_ratio': volume_ratio,
                    'volume_trend': volume_trend,
                    'volume_score': volume_score,
                    'volume_anomaly': volume_anomaly,
                    'price_volume_correlation': correlation,
                    'confidence': min(1.0, len(volume_data) / 20)
                }
            else:
                results = {
                    'volume_ratio': 1.0,
                    'volume_trend': 'unknown',
                    'volume_score': 0.0,
                    'confidence': 0.1
                }
            
            return results
            
        except Exception as e:
            return {'volume_ratio': 1.0, 'volume_trend': 'unknown', 'volume_score': 0.0, 'confidence': 0.1, 'error': str(e)}
    
    def _identify_key_levels(self, price_data: np.ndarray) -> Dict:
        """Identify key support and resistance levels"""
        try:
            results = {}
            
            if len(price_data) >= 20:
                current_price = price_data[-1]
                
                # Find local maxima and minima
                highs = []
                lows = []
                
                for i in range(2, len(price_data) - 2):
                    # Local high
                    if (price_data[i] > price_data[i-1] and price_data[i] > price_data[i-2] and
                        price_data[i] > price_data[i+1] and price_data[i] > price_data[i+2]):
                        highs.append(price_data[i])
                    
                    # Local low
                    if (price_data[i] < price_data[i-1] and price_data[i] < price_data[i-2] and
                        price_data[i] < price_data[i+1] and price_data[i] < price_data[i+2]):
                        lows.append(price_data[i])
                
                # Calculate support and resistance
                if lows:
                    support_level = max([low for low in lows if low < current_price] or [min(price_data)])
                    support_strength = sum(1 for low in lows if abs(low - support_level) / support_level < 0.02)
                else:
                    support_level = min(price_data)
                    support_strength = 1
                
                if highs:
                    resistance_level = min([high for high in highs if high > current_price] or [max(price_data)])
                    resistance_strength = sum(1 for high in highs if abs(high - resistance_level) / resistance_level < 0.02)
                else:
                    resistance_level = max(price_data)
                    resistance_strength = 1
                
                # Distance to key levels
                support_distance = (current_price - support_level) / current_price
                resistance_distance = (resistance_level - current_price) / current_price
                
                # Generate level score
                if support_distance < 0.02:  # Very close to support
                    level_score = 0.6  # Bullish if holding support
                elif resistance_distance < 0.02:  # Very close to resistance
                    level_score = -0.6  # Bearish if hitting resistance
                else:
                    level_score = 0.0
                
                results = {
                    'support_level': support_level,
                    'resistance_level': resistance_level,
                    'support_strength': support_strength,
                    'resistance_strength': resistance_strength,
                    'support_distance': support_distance,
                    'resistance_distance': resistance_distance,
                    'level_score': level_score,
                    'confidence': min(1.0, (len(highs) + len(lows)) / 10)
                }
            else:
                results = {
                    'support_level': min(price_data) if len(price_data) > 0 else 0,
                    'resistance_level': max(price_data) if len(price_data) > 0 else 0,
                    'level_score': 0.0,
                    'confidence': 0.1
                }
            
            return results
            
        except Exception as e:
            return {'level_score': 0.0, 'confidence': 0.1, 'error': str(e)}
    
    def _recognize_chart_patterns(self, price_data: np.ndarray) -> Dict:
        """Advanced chart pattern recognition"""
        try:
            patterns = []
            pattern_scores = []
            
            if len(price_data) >= 20:
                # Double bottom pattern
                if self._detect_double_bottom(price_data):
                    patterns.append('double_bottom')
                    pattern_scores.append(0.7)
                
                # Double top pattern
                if self._detect_double_top(price_data):
                    patterns.append('double_top')
                    pattern_scores.append(-0.7)
                
                # Head and shoulders
                if self._detect_head_shoulders(price_data):
                    patterns.append('head_and_shoulders')
                    pattern_scores.append(-0.8)
                
                # Ascending triangle
                if self._detect_ascending_triangle(price_data):
                    patterns.append('ascending_triangle')
                    pattern_scores.append(0.6)
                
                # Descending triangle
                if self._detect_descending_triangle(price_data):
                    patterns.append('descending_triangle')
                    pattern_scores.append(-0.6)
            
            # Calculate overall pattern score
            if pattern_scores:
                overall_score = np.mean(pattern_scores)
                confidence = len(patterns) / 5.0  # Max 5 patterns
            else:
                overall_score = 0.0
                confidence = 0.1
            
            return {
                'detected_patterns': patterns,
                'pattern_scores': pattern_scores,
                'overall_pattern_score': overall_score,
                'confidence': min(1.0, confidence)
            }
            
        except Exception as e:
            return {'detected_patterns': [], 'overall_pattern_score': 0.0, 'confidence': 0.1, 'error': str(e)}
    
    def _calculate_composite_score(self, analysis_results: Dict) -> Dict:
        """Calculate composite technical analysis score"""
        try:
            weighted_score = 0.0
            total_confidence = 0.0
            
            # Weight each component
            components = {
                'trend': analysis_results.get('trend', {}),
                'momentum': analysis_results.get('momentum', {}),
                'volatility': analysis_results.get('volatility', {}),
                'volume': analysis_results.get('volume', {}),
                'support_resistance': analysis_results.get('support_resistance', {}),
                'patterns': analysis_results.get('patterns', {})
            }
            
            for component_name, component_data in components.items():
                if component_name in self.indicator_weights:
                    weight = self.indicator_weights[component_name]
                    
                    # Extract score and confidence
                    if component_name == 'trend':
                        score = component_data.get('score', 0.0)
                        confidence = component_data.get('confidence', 0.1)
                    elif component_name == 'momentum':
                        score = component_data.get('momentum_score', 0.0)
                        confidence = component_data.get('confidence', 0.1)
                    elif component_name == 'volatility':
                        score = component_data.get('volatility_score', 0.0)
                        confidence = component_data.get('confidence', 0.1)
                    elif component_name == 'volume':
                        score = component_data.get('volume_score', 0.0)
                        confidence = component_data.get('confidence', 0.1)
                    elif component_name == 'support_resistance':
                        score = component_data.get('level_score', 0.0)
                        confidence = component_data.get('confidence', 0.1)
                    elif component_name == 'patterns':
                        score = component_data.get('overall_pattern_score', 0.0)
                        confidence = component_data.get('confidence', 0.1)
                    else:
                        score = 0.0
                        confidence = 0.1
                    
                    weighted_score += score * confidence * weight
                    total_confidence += confidence * weight
            
            # Normalize
            if total_confidence > 0:
                final_score = weighted_score / total_confidence
                system_confidence = total_confidence
            else:
                final_score = 0.0
                system_confidence = 0.1
            
            # Generate signal
            if final_score > 0.3:
                signal = 'STRONG_BUY'
            elif final_score > 0.1:
                signal = 'BUY'
            elif final_score < -0.3:
                signal = 'STRONG_SELL'
            elif final_score < -0.1:
                signal = 'SELL'
            else:
                signal = 'HOLD'
            
            return {
                'composite_score': final_score,
                'system_confidence': system_confidence,
                'signal': signal,
                'component_contributions': {
                    name: data.get(f'{name}_score' if name != 'trend' else 'score', 0.0) 
                    for name, data in components.items()
                },
                'technical_grade': 'INSTITUTIONAL' if system_confidence > 0.8 else 'PROFESSIONAL' if system_confidence > 0.6 else 'BASIC'
            }
            
        except Exception as e:
            return {
                'composite_score': 0.0,
                'system_confidence': 0.1,
                'signal': 'HOLD',
                'technical_grade': 'BASIC',
                'error': str(e)
            }
    
    # Helper methods for calculations
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate RSI"""
        try:
            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = np.mean(gains[-period:])
            avg_loss = np.mean(losses[-period:])
            
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except:
            return 50.0
    
    def _calculate_stochastic(self, prices: np.ndarray, period: int = 14) -> Tuple[float, float]:
        """Calculate Stochastic oscillator"""
        try:
            if len(prices) < period:
                return 50.0, 50.0
                
            recent_prices = prices[-period:]
            highest_high = np.max(recent_prices)
            lowest_low = np.min(recent_prices)
            current_price = prices[-1]
            
            if highest_high == lowest_low:
                k_percent = 50.0
            else:
                k_percent = ((current_price - lowest_low) / (highest_high - lowest_low)) * 100
            
            # Simple 3-period moving average for %D
            if len(prices) >= period + 2:
                k_values = []
                for i in range(3):
                    period_prices = prices[-(period + i):-(i) if i > 0 else None]
                    ph = np.max(period_prices)
                    pl = np.min(period_prices)
                    cp = prices[-(i + 1)]
                    if ph != pl:
                        k_values.append(((cp - pl) / (ph - pl)) * 100)
                    else:
                        k_values.append(50.0)
                d_percent = np.mean(k_values)
            else:
                d_percent = k_percent
                
            return k_percent, d_percent
        except:
            return 50.0, 50.0
    
    def _calculate_williams_r(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate Williams %R"""
        try:
            if len(prices) < period:
                return -50.0
                
            recent_prices = prices[-period:]
            highest_high = np.max(recent_prices)
            lowest_low = np.min(recent_prices)
            current_price = prices[-1]
            
            if highest_high == lowest_low:
                return -50.0
            
            williams_r = ((highest_high - current_price) / (highest_high - lowest_low)) * -100
            return williams_r
        except:
            return -50.0
    
    def _calculate_macd(self, prices: np.ndarray) -> Tuple[float, float, float]:
        """Calculate MACD"""
        try:
            if len(prices) < 26:
                return 0.0, 0.0, 0.0
            
            # EMA calculation
            def ema(data, span):
                return pd.Series(data).ewm(span=span).mean().iloc[-1]
            
            ema_12 = ema(prices, 12)
            ema_26 = ema(prices, 26)
            macd_line = ema_12 - ema_26
            
            # Signal line (9-period EMA of MACD)
            if len(prices) >= 35:  # Need enough data for signal line
                macd_values = []
                for i in range(9):
                    if len(prices) >= 26 + i:
                        period_prices = prices[:-(i) if i > 0 else None]
                        if len(period_prices) >= 26:
                            e12 = ema(period_prices, 12)
                            e26 = ema(period_prices, 26)
                            macd_values.append(e12 - e26)
                
                if macd_values:
                    macd_signal = ema(macd_values, 9)
                else:
                    macd_signal = macd_line
            else:
                macd_signal = macd_line
            
            macd_histogram = macd_line - macd_signal
            
            return macd_line, macd_signal, macd_histogram
        except:
            return 0.0, 0.0, 0.0
    
    def _calculate_bollinger_bands(self, prices: np.ndarray, period: int = 20, std_dev: float = 2.0) -> Tuple[float, float, float]:
        """Calculate Bollinger Bands"""
        try:
            if len(prices) < period:
                current_price = prices[-1] if len(prices) > 0 else 100
                return current_price * 1.02, current_price * 0.98, current_price
            
            recent_prices = prices[-period:]
            middle_band = np.mean(recent_prices)
            std = np.std(recent_prices)
            
            upper_band = middle_band + (std_dev * std)
            lower_band = middle_band - (std_dev * std)
            
            return upper_band, lower_band, middle_band
        except:
            current_price = prices[-1] if len(prices) > 0 else 100
            return current_price * 1.02, current_price * 0.98, current_price
    
    # Pattern detection methods (simplified versions)
    def _detect_double_bottom(self, prices: np.ndarray) -> bool:
        """Detect double bottom pattern"""
        try:
            if len(prices) < 20:
                return False
            
            # Find the two lowest points in recent data
            recent_prices = prices[-20:]
            min_indices = []
            
            for i in range(2, len(recent_prices) - 2):
                if (recent_prices[i] < recent_prices[i-1] and recent_prices[i] < recent_prices[i-2] and
                    recent_prices[i] < recent_prices[i+1] and recent_prices[i] < recent_prices[i+2]):
                    min_indices.append(i)
            
            if len(min_indices) >= 2:
                # Check if the two lows are approximately equal
                low1 = recent_prices[min_indices[-2]]
                low2 = recent_prices[min_indices[-1]]
                
                if abs(low1 - low2) / min(low1, low2) < 0.03:  # Within 3%
                    return True
            
            return False
        except:
            return False
    
    def _detect_double_top(self, prices: np.ndarray) -> bool:
        """Detect double top pattern"""
        try:
            if len(prices) < 20:
                return False
            
            recent_prices = prices[-20:]
            max_indices = []
            
            for i in range(2, len(recent_prices) - 2):
                if (recent_prices[i] > recent_prices[i-1] and recent_prices[i] > recent_prices[i-2] and
                    recent_prices[i] > recent_prices[i+1] and recent_prices[i] > recent_prices[i+2]):
                    max_indices.append(i)
            
            if len(max_indices) >= 2:
                high1 = recent_prices[max_indices[-2]]
                high2 = recent_prices[max_indices[-1]]
                
                if abs(high1 - high2) / max(high1, high2) < 0.03:
                    return True
            
            return False
        except:
            return False
    
    def _detect_head_shoulders(self, prices: np.ndarray) -> bool:
        """Detect head and shoulders pattern"""
        try:
            if len(prices) < 30:
                return False
            
            recent_prices = prices[-30:]
            peaks = []
            
            for i in range(5, len(recent_prices) - 5):
                if all(recent_prices[i] > recent_prices[i-j] for j in range(1, 6)) and \
                   all(recent_prices[i] > recent_prices[i+j] for j in range(1, 6)):
                    peaks.append((i, recent_prices[i]))
            
            if len(peaks) >= 3:
                # Check for head and shoulders pattern
                peaks = sorted(peaks, key=lambda x: x[1], reverse=True)[:3]
                peaks = sorted(peaks, key=lambda x: x[0])  # Sort by position
                
                # Head should be higher than shoulders
                if len(peaks) == 3:
                    left_shoulder = peaks[0][1]
                    head = peaks[1][1]
                    right_shoulder = peaks[2][1]
                    
                    if (head > left_shoulder * 1.02 and head > right_shoulder * 1.02 and
                        abs(left_shoulder - right_shoulder) / max(left_shoulder, right_shoulder) < 0.05):
                        return True
            
            return False
        except:
            return False
    
    def _detect_ascending_triangle(self, prices: np.ndarray) -> bool:
        """Detect ascending triangle pattern"""
        try:
            if len(prices) < 20:
                return False
            
            recent_prices = prices[-20:]
            
            # Find resistance level (horizontal top)
            highs = []
            for i in range(2, len(recent_prices) - 2):
                if all(recent_prices[i] >= recent_prices[i-j] for j in range(1, 3)) and \
                   all(recent_prices[i] >= recent_prices[i+j] for j in range(1, 3)):
                    highs.append(recent_prices[i])
            
            if len(highs) >= 2:
                # Check if highs are approximately equal (resistance)
                avg_high = np.mean(highs)
                if all(abs(h - avg_high) / avg_high < 0.02 for h in highs):
                    
                    # Check for ascending lows
                    lows = []
                    for i in range(2, len(recent_prices) - 2):
                        if all(recent_prices[i] <= recent_prices[i-j] for j in range(1, 3)) and \
                           all(recent_prices[i] <= recent_prices[i+j] for j in range(1, 3)):
                            lows.append((i, recent_prices[i]))
                    
                    if len(lows) >= 2:
                        lows = sorted(lows, key=lambda x: x[0])
                        if lows[-1][1] > lows[0][1]:  # Ascending lows
                            return True
            
            return False
        except:
            return False
    
    def _detect_descending_triangle(self, prices: np.ndarray) -> bool:
        """Detect descending triangle pattern"""
        try:
            if len(prices) < 20:
                return False
            
            recent_prices = prices[-20:]
            
            # Find support level (horizontal bottom)
            lows = []
            for i in range(2, len(recent_prices) - 2):
                if all(recent_prices[i] <= recent_prices[i-j] for j in range(1, 3)) and \
                   all(recent_prices[i] <= recent_prices[i+j] for j in range(1, 3)):
                    lows.append(recent_prices[i])
            
            if len(lows) >= 2:
                avg_low = np.mean(lows)
                if all(abs(l - avg_low) / avg_low < 0.02 for l in lows):
                    
                    # Check for descending highs
                    highs = []
                    for i in range(2, len(recent_prices) - 2):
                        if all(recent_prices[i] >= recent_prices[i-j] for j in range(1, 3)) and \
                           all(recent_prices[i] >= recent_prices[i+j] for j in range(1, 3)):
                            highs.append((i, recent_prices[i]))
                    
                    if len(highs) >= 2:
                        highs = sorted(highs, key=lambda x: x[0])
                        if highs[-1][1] < highs[0][1]:  # Descending highs
                            return True
            
            return False
        except:
            return False
    
    def _fallback_analysis(self) -> Dict:
        """Fallback analysis for error conditions"""
        return {
            'trend': {'strength': 'unknown', 'score': 0.0, 'confidence': 0.1},
            'momentum': {'momentum_score': 0.0, 'confidence': 0.1},
            'volatility': {'volatility_score': 0.0, 'confidence': 0.1},
            'volume': {'volume_score': 0.0, 'confidence': 0.1},
            'support_resistance': {'level_score': 0.0, 'confidence': 0.1},
            'patterns': {'overall_pattern_score': 0.0, 'confidence': 0.1},
            'composite_score': {
                'composite_score': 0.0,
                'system_confidence': 0.1,
                'signal': 'HOLD',
                'technical_grade': 'BASIC'
            }
        }