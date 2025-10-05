import pandas as pd
import numpy as np
from scipy import stats
import talib

class TechnicalAnalyzer:
    def __init__(self):
        self.indicators = {}
        
    def calculate_all_indicators(self, price_data, volume_data):
        """Calculate all technical indicators"""
        if len(price_data) < 50:  # Need minimum data points
            return self._default_indicators()
            
        try:
            indicators = {}
            
            # Price-based indicators
            indicators['rsi'] = self.calculate_rsi(price_data)
            indicators['macd'], indicators['macd_signal'] = self.calculate_macd(price_data)
            indicators['bb_upper'], indicators['bb_lower'], indicators['bb_middle'] = self.calculate_bollinger_bands(price_data)
            indicators['bb_percent'] = self.calculate_bb_percent(price_data, indicators['bb_upper'], indicators['bb_lower'])
            indicators['stoch_k'], indicators['stoch_d'] = self.calculate_stochastic(price_data)
            indicators['ema_20'] = self.calculate_ema(price_data, 20)
            indicators['ema_50'] = self.calculate_ema(price_data, 50)
            indicators['sma_20'] = self.calculate_sma(price_data, 20)
            indicators['sma_50'] = self.calculate_sma(price_data, 50)
            indicators['atr'] = self.calculate_atr(price_data)
            indicators['adx'] = self.calculate_adx(price_data)
            indicators['cci'] = self.calculate_cci(price_data)
            indicators['williams_r'] = self.calculate_williams_r(price_data)
            
            # Volume-based indicators
            if len(volume_data) == len(price_data):
                indicators['volume_sma'] = self.calculate_sma(volume_data, 20)
                indicators['volume_ratio'] = volume_data[-1] / indicators['volume_sma'] if indicators['volume_sma'] > 0 else 1
                indicators['obv'] = self.calculate_obv(price_data, volume_data)
                indicators['cmf'] = self.calculate_cmf(price_data, volume_data)
            else:
                indicators['volume_sma'] = 0
                indicators['volume_ratio'] = 1
                indicators['obv'] = 0
                indicators['cmf'] = 0
            
            # Pattern recognition
            indicators['support'] = self.find_support_level(price_data)
            indicators['resistance'] = self.find_resistance_level(price_data)
            indicators['trend'] = self.identify_trend(price_data)
            
            # Fibonacci retracement levels
            fib_levels = self.calculate_fibonacci_retracements(price_data)
            indicators.update(fib_levels)
            
            # VWAP (Volume Weighted Average Price)
            if len(volume_data) == len(price_data):
                indicators['vwap'] = self.calculate_vwap(price_data, volume_data)
            else:
                indicators['vwap'] = None
            
            return indicators
            
        except Exception as e:
            print(f"Technical analysis error: {e}")
            return self._default_indicators()
    
    def _default_indicators(self):
        """Return error indicators when calculation fails - NO FAKE NEUTRAL VALUES"""
        return {
            'rsi': None, 'macd': None, 'macd_signal': None,
            'bb_upper': None, 'bb_lower': None, 'bb_middle': None, 'bb_percent': None,
            'stoch_k': None, 'stoch_d': None,
            'ema_20': None, 'ema_50': None, 'sma_20': None, 'sma_50': None,
            'atr': None, 'adx': None, 'cci': None, 'williams_r': None,
            'volume_sma': None, 'volume_ratio': None, 'obv': None, 'cmf': None,
            'support': None, 'resistance': None, 'trend': 'DATA_ERROR',
            'status': 'CALCULATION_FAILED'
        }
    
    def calculate_rsi(self, data, period=14):
        """Calculate Relative Strength Index"""
        try:
            if hasattr(talib, 'RSI'):
                return talib.RSI(np.array(data, dtype=float), timeperiod=period)[-1]
            else:
                # Manual calculation
                delta = np.diff(data)
                gain = np.where(delta > 0, delta, 0)
                loss = np.where(delta < 0, -delta, 0)
                
                avg_gain = np.mean(gain[-period:]) if len(gain) >= period else 0
                avg_loss = np.mean(loss[-period:]) if len(loss) >= period else 0
                
                if avg_loss == 0:
                    return 100
                
                rs = avg_gain / avg_loss
                return 100 - (100 / (1 + rs))
                
        except Exception as e:
            print(f"CRITICAL: RSI calculation failed: {e}")
            return None  # No fake neutral values for institutional trading
    
    def calculate_macd(self, data, fast=12, slow=26, signal=9):
        """Calculate MACD indicator"""
        try:
            if hasattr(talib, 'MACD'):
                macd, signal_line, hist = talib.MACD(np.array(data, dtype=float), 
                                                   fastperiod=fast, slowperiod=slow, signalperiod=signal)
                return macd[-1], signal_line[-1]
            else:
                # Manual calculation
                exp1 = pd.Series(data).ewm(span=fast, adjust=False).mean()
                exp2 = pd.Series(data).ewm(span=slow, adjust=False).mean()
                macd = exp1 - exp2
                signal_line = macd.ewm(span=signal, adjust=False).mean()
                return macd.iloc[-1], signal_line.iloc[-1]
                
        except Exception as e:
            print(f"MACD calculation error: {e}")
            return 0, 0
    
    def calculate_bollinger_bands(self, data, period=20, std_dev=2):
        """Calculate Bollinger Bands"""
        try:
            if hasattr(talib, 'BBANDS'):
                upper, middle, lower = talib.BBANDS(np.array(data, dtype=float), 
                                                   timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev)
                return upper[-1], lower[-1], middle[-1]
            else:
                # Manual calculation
                sma = pd.Series(data).rolling(window=period).mean()
                std = pd.Series(data).rolling(window=period).std()
                upper = sma + (std * std_dev)
                lower = sma - (std * std_dev)
                return upper.iloc[-1], lower.iloc[-1], sma.iloc[-1]
                
        except Exception as e:
            print(f"Bollinger Bands calculation error: {e}")
            return 0, 0, 0
    
    def calculate_bb_percent(self, data, bb_upper, bb_lower):
        """Calculate %B (Bollinger Band percentage)"""
        try:
            if bb_upper == bb_lower:
                return 50
            return ((data[-1] - bb_lower) / (bb_upper - bb_lower)) * 100
        except:
            return 50
    
    def calculate_stochastic(self, data, k_period=14, d_period=3):
        """Calculate Stochastic Oscillator"""
        try:
            if hasattr(talib, 'STOCH'):
                # Need high, low, close for proper stochastic
                high = np.array(data, dtype=float)
                low = np.array(data, dtype=float) 
                close = np.array(data, dtype=float)
                slowk, slowd = talib.STOCH(high, low, close, 
                                         fastk_period=k_period, slowk_period=d_period, slowd_period=d_period)
                return slowk[-1], slowd[-1]
            else:
                # Manual calculation
                low_min = pd.Series(data).rolling(window=k_period).min()
                high_max = pd.Series(data).rolling(window=k_period).max()
                k_percent = 100 * ((pd.Series(data) - low_min) / (high_max - low_min))
                d_percent = k_percent.rolling(window=d_period).mean()
                return k_percent.iloc[-1], d_percent.iloc[-1]
                
        except Exception as e:
            print(f"CRITICAL: Stochastic calculation failed: {e}")
            return None, None  # No fake neutral values for institutional trading
    
    def calculate_ema(self, data, period):
        """Calculate Exponential Moving Average"""
        try:
            if hasattr(talib, 'EMA'):
                return talib.EMA(np.array(data, dtype=float), timeperiod=period)[-1]
            else:
                return pd.Series(data).ewm(span=period, adjust=False).mean().iloc[-1]
        except:
            return np.mean(data[-period:]) if len(data) >= period else np.mean(data)
    
    def calculate_sma(self, data, period):
        """Calculate Simple Moving Average"""
        try:
            if hasattr(talib, 'SMA'):
                return talib.SMA(np.array(data, dtype=float), timeperiod=period)[-1]
            else:
                return pd.Series(data).rolling(window=period).mean().iloc[-1]
        except:
            return np.mean(data[-period:]) if len(data) >= period else np.mean(data)
    
    def calculate_atr(self, data, period=14):
        """Calculate Average True Range"""
        try:
            # Simplified ATR using only close prices
            high_low = np.diff(data)
            true_range = np.abs(high_low)
            return pd.Series(true_range).rolling(window=period).mean().iloc[-1]
        except:
            return np.std(data[-period:]) if len(data) >= period else np.std(data)
    
    def calculate_adx(self, data, period=14):
        """Calculate Average Directional Index"""
        try:
            if hasattr(talib, 'ADX'):
                # Simplified using close prices as high/low/close
                close_array = np.array(data, dtype=float)
                return talib.ADX(close_array, close_array, close_array, timeperiod=period)[-1]
            else:
                # PROFESSIONAL ADX CALCULATION (Average Directional Index)
                if len(data) < 30:
                    return None  # Need minimum 30 periods for ADX
                
                # Calculate price movements
                price_changes = np.diff(data)
                up_moves = np.where(price_changes > 0, price_changes, 0)
                down_moves = np.where(price_changes < 0, np.abs(price_changes), 0)
                
                # Calculate True Range (simplified for close prices only)
                true_ranges = np.abs(price_changes)
                
                # Apply Wilder's smoothing (exponential moving average with alpha = 1/period)
                alpha = 1.0 / period
                
                # Smoothed True Range
                atr_values = []
                atr_values.append(true_ranges[0])
                for i in range(1, len(true_ranges)):
                    atr_values.append(alpha * true_ranges[i] + (1 - alpha) * atr_values[-1])
                
                # Smoothed Directional Movements
                plus_dm = []
                minus_dm = []
                plus_dm.append(up_moves[0])
                minus_dm.append(down_moves[0])
                
                for i in range(1, len(up_moves)):
                    plus_dm.append(alpha * up_moves[i] + (1 - alpha) * plus_dm[-1])
                    minus_dm.append(alpha * down_moves[i] + (1 - alpha) * minus_dm[-1])
                
                # Calculate +DI and -DI
                plus_di = [(dm / atr) * 100 for dm, atr in zip(plus_dm, atr_values)]
                minus_di = [(dm / atr) * 100 for dm, atr in zip(minus_dm, atr_values)]
                
                # Calculate DX (Directional Index)
                dx_values = []
                for pdi, mdi in zip(plus_di, minus_di):
                    if (pdi + mdi) != 0:
                        dx_values.append(abs(pdi - mdi) / (pdi + mdi) * 100)
                    else:
                        dx_values.append(0)
                
                # Calculate ADX (smoothed DX)
                if len(dx_values) < period:
                    return None
                    
                adx_values = []
                adx_values.append(np.mean(dx_values[:period]))  # Initial ADX
                
                for i in range(len(dx_values) - period):
                    idx = i + period
                    adx_values.append(alpha * dx_values[idx] + (1 - alpha) * adx_values[-1])
                
                return round(float(adx_values[-1]), 2) if adx_values else None
        except:
            return None
    
    def calculate_cci(self, data, period=20):
        """Calculate Commodity Channel Index"""
        try:
            if hasattr(talib, 'CCI'):
                close_array = np.array(data, dtype=float)
                return talib.CCI(close_array, close_array, close_array, timeperiod=period)[-1]
            else:
                # Manual calculation
                tp = pd.Series(data)  # Using close as typical price
                sma_tp = tp.rolling(window=period).mean()
                mad = tp.rolling(window=period).apply(lambda x: np.mean(np.abs(x - x.mean())))
                return ((tp.iloc[-1] - sma_tp.iloc[-1]) / (0.015 * mad.iloc[-1])) if mad.iloc[-1] != 0 else 0
        except:
            return 0
    
    def calculate_williams_r(self, data, period=14):
        """Calculate Williams %R"""
        try:
            if hasattr(talib, 'WILLR'):
                close_array = np.array(data, dtype=float)
                return talib.WILLR(close_array, close_array, close_array, timeperiod=period)[-1]
            else:
                # Manual calculation
                high_max = pd.Series(data).rolling(window=period).max()
                low_min = pd.Series(data).rolling(window=period).min()
                current = data[-1]
                return -100 * ((high_max.iloc[-1] - current) / (high_max.iloc[-1] - low_min.iloc[-1])) if (high_max.iloc[-1] - low_min.iloc[-1]) != 0 else -50
        except:
            return -50
    
    def calculate_obv(self, price_data, volume_data):
        """Calculate On-Balance Volume"""
        try:
            if hasattr(talib, 'OBV'):
                return talib.OBV(np.array(price_data, dtype=float), np.array(volume_data, dtype=float))[-1]
            else:
                # Manual calculation
                obv = [0]
                for i in range(1, len(price_data)):
                    if price_data[i] > price_data[i-1]:
                        obv.append(obv[-1] + volume_data[i])
                    elif price_data[i] < price_data[i-1]:
                        obv.append(obv[-1] - volume_data[i])
                    else:
                        obv.append(obv[-1])
                return obv[-1]
        except:
            return 0
    
    def calculate_cmf(self, price_data, volume_data, period=20):
        """Calculate Chaikin Money Flow"""
        try:
            if len(price_data) != len(volume_data) or len(price_data) < period:
                return 0
                
            # Simplified CMF calculation
            mfv = []
            for i in range(1, len(price_data)):
                if price_data[i] != price_data[i-1]:
                    mf_multiplier = (price_data[i] - price_data[i-1]) / abs(price_data[i] - price_data[i-1])
                    mfv.append(mf_multiplier * volume_data[i])
                else:
                    mfv.append(0)
            
            mfv_sum = sum(mfv[-period:])
            volume_sum = sum(volume_data[-period:])
            
            return mfv_sum / volume_sum if volume_sum > 0 else 0
            
        except:
            return 0
    
    def find_support_level(self, data, lookback=20):
        """Find support level"""
        try:
            recent_data = data[-lookback:]
            return np.percentile(recent_data, 20)  # 20th percentile as support
        except:
            return min(data) if data else 0
    
    def find_resistance_level(self, data, lookback=20):
        """Find resistance level"""
        try:
            recent_data = data[-lookback:]
            return np.percentile(recent_data, 80)  # 80th percentile as resistance
        except:
            return max(data) if data else 0
    
    def identify_trend(self, data, period=20):
        """Identify price trend"""
        try:
            if len(data) < period:
                return "insufficient_data"
                
            recent_data = data[-period:]
            slope, _, r_value, _, _ = stats.linregress(range(len(recent_data)), recent_data)
            
            if abs(r_value) < 0.5:  # Weak correlation
                return "sideways"
            elif slope > 0:
                return "uptrend"
            else:
                return "downtrend"
                
        except:
            return "unknown"
    
    def calculate_momentum_indicators(self, data):
        """Calculate momentum-based indicators"""
        try:
            indicators = {}
            
            # Rate of Change
            if len(data) >= 12:
                indicators['roc'] = ((data[-1] - data[-12]) / data[-12]) * 100
            else:
                indicators['roc'] = 0
            
            # Momentum
            if len(data) >= 10:
                indicators['momentum'] = data[-1] - data[-10]
            else:
                indicators['momentum'] = 0
            
            return indicators
            
        except Exception as e:
            print(f"Momentum indicators error: {e}")
            return {'roc': 0, 'momentum': 0}
    
    def calculate_keltner_channels(self, data, period=20, multiplier=2):
        """Calculate Keltner Channels"""
        try:
            # Use close price as typical price for simplification
            typical_price = pd.Series(data)
            sma = typical_price.rolling(window=period).mean()
            atr = self.calculate_atr(data, period)
            
            upper = sma + (multiplier * atr)
            lower = sma - (multiplier * atr)
            
            return upper.iloc[-1], lower.iloc[-1], sma.iloc[-1]
            
        except Exception as e:
            print(f"Keltner Channels calculation error: {e}")
            return 0, 0, 0
    
    def calculate_ad_oscillator(self, price_data, volume_data):
        """Calculate Accumulation/Distribution Oscillator"""
        try:
            if len(price_data) != len(volume_data):
                return 0
                
            adl = [0]
            for i in range(1, len(price_data)):
                # Money Flow Multiplier calculation
                high = max(price_data[i-5:i+1]) if i >= 5 else price_data[i]
                low = min(price_data[i-5:i+1]) if i >= 5 else price_data[i]
                close = price_data[i]
                
                if high != low:
                    mf_multiplier = ((close - low) - (high - close)) / (high - low)
                else:
                    mf_multiplier = 0
                
                # Money Flow Volume
                mf_volume = mf_multiplier * volume_data[i]
                
                # Accumulation/Distribution Line
                adl.append(adl[-1] + mf_volume)
            
            # Return the oscillator (difference from 14 periods ago)
            return adl[-1] - adl[-14] if len(adl) > 14 else adl[-1]
            
        except Exception as e:
            print(f"A/D Oscillator calculation error: {e}")
            return 0
    
    def detect_upside_breakout(self, price_data, volume_data, period=20):
        """Detect upside breakout pattern"""
        try:
            if len(price_data) < period or len(volume_data) < period:
                return False
                
            recent_high = max(price_data[-period:-1])
            current_price = price_data[-1]
            avg_volume = sum(volume_data[-period:]) / period
            current_volume = volume_data[-1]
            
            return current_price > recent_high and current_volume > avg_volume * 1.5
            
        except Exception as e:
            print(f"Upside breakout detection error: {e}")
            return False
    
    def detect_downside_breakout(self, price_data, volume_data, period=20):
        """Detect downside breakout pattern"""
        try:
            if len(price_data) < period or len(volume_data) < period:
                return False
                
            recent_low = min(price_data[-period:-1])
            current_price = price_data[-1]
            avg_volume = sum(volume_data[-period:]) / period
            current_volume = volume_data[-1]
            
            return current_price < recent_low and current_volume > avg_volume * 1.5
            
        except Exception as e:
            print(f"Downside breakout detection error: {e}")
            return False
    
    def detect_triangle_pattern(self, price_data, period=30):
        """Detect triangle patterns"""
        try:
            if len(price_data) < period:
                return {'symmetrical': False, 'ascending': False, 'descending': False}
            
            recent_data = price_data[-period:]
            highs = pd.Series(recent_data).rolling(window=5).max()
            lows = pd.Series(recent_data).rolling(window=5).min()
            
            # Calculate trend lines
            high_trend = np.polyfit(range(len(highs)), highs, 1)[0]
            low_trend = np.polyfit(range(len(lows)), lows, 1)[0]
            
            # Pattern detection
            symmetrical = abs(high_trend) < 0.01 and abs(low_trend) < 0.01
            ascending = abs(high_trend) < 0.01 and low_trend > 0.01
            descending = high_trend < -0.01 and abs(low_trend) < 0.01
            
            return {
                'symmetrical': symmetrical,
                'ascending': ascending, 
                'descending': descending
            }
            
        except Exception as e:
            print(f"Triangle pattern detection error: {e}")
            return {'symmetrical': False, 'ascending': False, 'descending': False}
    
    def calculate_vwap(self, price_data, volume_data):
        """Calculate Volume Weighted Average Price"""
        try:
            if len(price_data) != len(volume_data):
                return np.mean(price_data) if price_data else 0
                
            price_volume = [p * v for p, v in zip(price_data, volume_data)]
            total_price_volume = sum(price_volume)
            total_volume = sum(volume_data)
            
            return total_price_volume / total_volume if total_volume > 0 else 0
            
        except Exception as e:
            print(f"VWAP calculation error: {e}")
            return 0
    
    def calculate_parabolic_sar(self, price_data, step=0.02, max_step=0.2):
        """Calculate Parabolic SAR"""
        try:
            if len(price_data) < 10:
                return price_data[-1] if price_data else 0
                
            # Simplified PSAR calculation
            high = max(price_data[-10:])
            low = min(price_data[-10:])
            current = price_data[-1]
            
            # Determine if we're in uptrend or downtrend
            if current > (high + low) / 2:
                # Uptrend - SAR below price
                return low + (high - low) * step
            else:
                # Downtrend - SAR above price  
                return high - (high - low) * step
                
        except Exception as e:
            print(f"Parabolic SAR calculation error: {e}")
            return 0
    
    def get_trading_signals(self, indicators):
        """Generate trading signals based on indicators"""
        try:
            signals = []
            
            # RSI signals
            if indicators.get('rsi', 50) > 70:
                signals.append({"type": "sell", "strength": "strong", "reason": "RSI overbought"})
            elif indicators.get('rsi', 50) < 30:
                signals.append({"type": "buy", "strength": "strong", "reason": "RSI oversold"})
            
            # MACD signals
            macd = indicators.get('macd', 0)
            macd_signal = indicators.get('macd_signal', 0)
            if macd > macd_signal and macd > 0:
                signals.append({"type": "buy", "strength": "medium", "reason": "MACD bullish crossover"})
            elif macd < macd_signal and macd < 0:
                signals.append({"type": "sell", "strength": "medium", "reason": "MACD bearish crossover"})
            
            # Bollinger Band signals
            bb_percent = indicators.get('bb_percent', 50)
            if bb_percent > 100:
                signals.append({"type": "sell", "strength": "medium", "reason": "Price above upper Bollinger Band"})
            elif bb_percent < 0:
                signals.append({"type": "buy", "strength": "medium", "reason": "Price below lower Bollinger Band"})
            
            # Pattern-based signals
            if indicators.get('upside_breakout', False):
                signals.append({"type": "buy", "strength": "strong", "reason": "Upside breakout detected"})
            if indicators.get('downside_breakout', False):
                signals.append({"type": "sell", "strength": "strong", "reason": "Downside breakout detected"})
            
            return signals
            
        except Exception as e:
            print(f"Trading signals error: {e}")
            return []
    
    def calculate_fibonacci_retracements(self, data, lookback=50):
        """Calculate Fibonacci retracement levels based on recent swing high/low"""
        try:
            if len(data) < lookback:
                lookback = len(data)
            
            # Find swing high and low in the lookback period
            recent_data = data[-lookback:]
            swing_high = np.max(recent_data)
            swing_low = np.min(recent_data)
            
            # Calculate the range
            price_range = swing_high - swing_low
            
            # Standard Fibonacci retracement levels
            fib_levels = {
                'fib_0': swing_low,  # 0% (swing low)
                'fib_236': swing_low + (price_range * 0.236),  # 23.6%
                'fib_382': swing_low + (price_range * 0.382),  # 38.2%
                'fib_50': swing_low + (price_range * 0.50),   # 50%
                'fib_618': swing_low + (price_range * 0.618),  # 61.8%
                'fib_786': swing_low + (price_range * 0.786),  # 78.6%
                'fib_100': swing_high,  # 100% (swing high)
                'fib_swing_high': swing_high,
                'fib_swing_low': swing_low
            }
            
            return fib_levels
            
        except Exception as e:
            print(f"Fibonacci calculation error: {e}")
            return {
                'fib_0': None, 'fib_236': None, 'fib_382': None, 'fib_50': None,
                'fib_618': None, 'fib_786': None, 'fib_100': None,
                'fib_swing_high': None, 'fib_swing_low': None
            }
    
    def calculate_vwap(self, price_data, volume_data):
        """Calculate Volume Weighted Average Price"""
        try:
            if len(price_data) != len(volume_data) or len(price_data) == 0:
                return None
            
            # VWAP = Sum(Price * Volume) / Sum(Volume)
            prices = np.array(price_data)
            volumes = np.array(volume_data)
            
            # Calculate cumulative (price * volume)
            pv = prices * volumes
            cum_pv = np.cumsum(pv)
            cum_vol = np.cumsum(volumes)
            
            # VWAP is cumulative PV / cumulative volume
            vwap = cum_pv[-1] / cum_vol[-1] if cum_vol[-1] > 0 else None
            
            return vwap
            
        except Exception as e:
            print(f"VWAP calculation error: {e}")
            return None
