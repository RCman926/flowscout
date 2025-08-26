"""
Dashboard Data Coordinator
Ensures all dashboard components receive consistent, real data from verified sources
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class DashboardDataCoordinator:
    """Coordinates all data flows to ensure real, consistent data across the platform"""
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 30  # 30 seconds for real-time trading
        
    def _is_cache_valid(self, key):
        if key not in self.cache:
            return False
        return (datetime.now() - self.cache[key]['timestamp']).seconds < self.cache_duration
    
    def get_market_data(self, symbol):
        """Get verified real market data"""
        cache_key = f"market_{symbol}"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
        
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='2d')
            info = ticker.info
            
            if hist.empty:
                return None
            
            current_price = float(hist['Close'].iloc[-1])
            prev_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
            volume = int(hist['Volume'].iloc[-1])
            avg_volume = int(info.get('averageVolume', volume))
            
            data = {
                'symbol': symbol,
                'price': current_price,
                'change': current_price - prev_close,
                'change_pct': ((current_price - prev_close) / prev_close) * 100,
                'volume': volume,
                'avg_volume': avg_volume,
                'market_cap': info.get('marketCap', 0),
                'timestamp': datetime.now()
            }
            
            self.cache[cache_key] = {'data': data, 'timestamp': datetime.now()}
            return data
            
        except Exception as e:
            print(f"Market data error for {symbol}: {e}")
            return None
    
    def get_options_flow(self, symbol):
        """Get verified real options flow data"""
        cache_key = f"flow_{symbol}"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
        
        try:
            ticker = yf.Ticker(symbol)
            
            if not ticker.options:
                return {'analysis': [], 'total_volume': 0, 'symbol': symbol}
            
            all_analysis = []
            total_volume = 0
            
            # Analyze top 3 expirations
            for exp_date in ticker.options[:3]:
                try:
                    chain = ticker.option_chain(exp_date)
                    calls_df = chain.calls
                    puts_df = chain.puts
                    
                    # Calculate days to expiry
                    exp_dt = datetime.strptime(exp_date, '%Y-%m-%d')
                    dte = (exp_dt.date() - datetime.now().date()).days
                    
                    # Filter for active options
                    active_calls = calls_df[(calls_df['volume'] > 0) & (calls_df['bid'] > 0)]
                    active_puts = puts_df[(puts_df['volume'] > 0) & (puts_df['bid'] > 0)]
                    
                    call_volume = int(active_calls['volume'].sum()) if not active_calls.empty else 0
                    put_volume = int(active_puts['volume'].sum()) if not active_puts.empty else 0
                    
                    call_premium = float((active_calls['volume'] * active_calls['lastPrice']).sum()) if not active_calls.empty else 0
                    put_premium = float((active_puts['volume'] * active_puts['lastPrice']).sum()) if not active_puts.empty else 0
                    
                    total_volume += call_volume + put_volume
                    
                    analysis = {
                        'expiry': exp_date,
                        'dte': dte,
                        'call_volume': call_volume,
                        'put_volume': put_volume,
                        'call_premium': call_premium,
                        'put_premium': put_premium,
                        'total_volume': call_volume + put_volume,
                        'pc_ratio': put_volume / call_volume if call_volume > 0 else 0
                    }
                    all_analysis.append(analysis)
                    
                except Exception as e:
                    print(f"Error analyzing {exp_date}: {e}")
                    continue
            
            data = {
                'analysis': all_analysis,
                'total_volume': total_volume,
                'symbol': symbol,
                'timestamp': datetime.now()
            }
            
            self.cache[cache_key] = {'data': data, 'timestamp': datetime.now()}
            return data
            
        except Exception as e:
            print(f"Flow analysis error for {symbol}: {e}")
            return {'analysis': [], 'total_volume': 0, 'symbol': symbol}
    
    def get_technical_indicators(self, symbol):
        """Get verified real technical indicators"""
        cache_key = f"tech_{symbol}"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
        
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='50d')  # Need enough data for indicators
            
            if len(hist) < 20:
                return {}
            
            # Calculate RSI
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            # Calculate MACD
            exp1 = hist['Close'].ewm(span=12).mean()
            exp2 = hist['Close'].ewm(span=26).mean()
            macd = exp1 - exp2
            signal_line = macd.ewm(span=9).mean()
            
            # Calculate Bollinger Bands
            rolling_mean = hist['Close'].rolling(window=20).mean()
            rolling_std = hist['Close'].rolling(window=20).std()
            bb_upper = rolling_mean + (rolling_std * 2)
            bb_lower = rolling_mean - (rolling_std * 2)
            
            # Calculate moving averages
            sma_20 = hist['Close'].rolling(window=20).mean()
            sma_50 = hist['Close'].rolling(window=50).mean() if len(hist) >= 50 else sma_20
            
            data = {
                'rsi': float(rsi.iloc[-1]),
                'macd': float(macd.iloc[-1]),
                'macd_signal': float(signal_line.iloc[-1]),
                'bb_upper': float(bb_upper.iloc[-1]),
                'bb_lower': float(bb_lower.iloc[-1]),
                'bb_middle': float(rolling_mean.iloc[-1]),
                'sma_20': float(sma_20.iloc[-1]),
                'sma_50': float(sma_50.iloc[-1]),
                'volume_sma': float(hist['Volume'].rolling(window=20).mean().iloc[-1]),
                'timestamp': datetime.now()
            }
            
            self.cache[cache_key] = {'data': data, 'timestamp': datetime.now()}
            return data
            
        except Exception as e:
            print(f"Technical indicators error for {symbol}: {e}")
            return {}
    
    def generate_trading_signal(self, symbol):
        """Generate trading signal based on real market data"""
        try:
            market_data = self.get_market_data(symbol)
            flow_data = self.get_options_flow(symbol)
            tech_data = self.get_technical_indicators(symbol)
            
            if not market_data or not tech_data:
                return {'signal': 'NO_DATA', 'confidence': 0}
            
            # Simple but real signal generation logic
            signals = []
            reasons = []
            
            # Price momentum signal
            if market_data['change_pct'] > 1:
                signals.append(1)
                reasons.append("Strong price momentum up")
            elif market_data['change_pct'] < -1:
                signals.append(-1)
                reasons.append("Strong price momentum down")
            
            # RSI signal
            rsi = tech_data.get('rsi', 50)
            if rsi < 30:
                signals.append(1)
                reasons.append("RSI oversold")
            elif rsi > 70:
                signals.append(-1)
                reasons.append("RSI overbought")
            
            # Volume signal
            volume_ratio = market_data['volume'] / market_data['avg_volume']
            if volume_ratio > 1.5:
                signals.append(1 if market_data['change_pct'] > 0 else -1)
                reasons.append(f"High volume ({volume_ratio:.1f}x average)")
            
            # Options flow signal
            total_flow = flow_data.get('total_volume', 0)
            if total_flow > 50000:  # Significant flow threshold
                call_vol = sum([exp.get('call_volume', 0) for exp in flow_data.get('analysis', [])])
                put_vol = sum([exp.get('put_volume', 0) for exp in flow_data.get('analysis', [])])
                
                if call_vol > put_vol * 1.5:
                    signals.append(1)
                    reasons.append("Bullish options flow")
                elif put_vol > call_vol * 1.5:
                    signals.append(-1)
                    reasons.append("Bearish options flow")
            
            # Calculate final signal
            if not signals:
                return {'signal': 'HOLD', 'confidence': 50, 'reasons': ['No clear signals']}
            
            avg_signal = sum(signals) / len(signals)
            confidence = min(95, 50 + (abs(avg_signal) * 20) + (len(signals) * 5))
            
            if avg_signal > 0.3:
                signal_text = "BUY CALLS"
            elif avg_signal < -0.3:
                signal_text = "BUY PUTS"
            else:
                signal_text = "HOLD"
            
            return {
                'signal': signal_text,
                'confidence': round(confidence),
                'reasons': reasons,
                'price_target': market_data['price'] * (1 + (avg_signal * 0.02)),
                'risk_level': 'LOW' if len(signals) >= 3 else 'MEDIUM',
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            print(f"Signal generation error for {symbol}: {e}")
            return {'signal': 'ERROR', 'confidence': 0}

# Global instance
data_coordinator = DashboardDataCoordinator()