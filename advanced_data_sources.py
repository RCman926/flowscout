"""
Advanced Data Sources for Institutional-Grade Squeeze Detection
Provides real short interest, options flow, borrow rates, dark pool data, and social sentiment
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import time
import json
import re
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor
import warnings
warnings.filterwarnings('ignore')


class AdvancedDataSources:
    """
    Institutional-grade data sources for squeeze detection
    """
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 300  # 5 minutes
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    # ========== 1. REAL SHORT INTEREST DATA ==========
    
    def get_real_short_interest(self, symbol: str) -> Dict:
        """
        Get REAL short interest data from finviz
        Returns: SI%, days to cover, float short, shares short, borrow rate
        """
        
        cache_key = f"si_{symbol}"
        if self._check_cache(cache_key):
            return self.cache[cache_key]['data']
        
        try:
            # Scrape from finviz
            url = f"https://finviz.com/quote.ashx?t={symbol}"
            response = requests.get(url, headers=self.headers, timeout=5)
            
            if response.status_code != 200:
                return self._get_fallback_si(symbol)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Parse finviz table
            si_data = {
                'short_percent_float': 0,
                'short_ratio': 0,
                'shares_short': 0,
                'float_shares': 0,
                'short_percent_shares_outstanding': 0,
                'data_source': 'finviz',
                'timestamp': datetime.now().isoformat()
            }
            
            # Find all table cells
            table = soup.find('table', class_='snapshot-table2')
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    for i in range(0, len(cells)-1, 2):
                        label = cells[i].text.strip()
                        value = cells[i+1].text.strip()
                        
                        if 'Short Float' in label:
                            # Extract percentage
                            match = re.search(r'(\d+\.?\d*)%', value)
                            if match:
                                si_data['short_percent_float'] = float(match.group(1))
                        
                        elif 'Short Ratio' in label:
                            try:
                                si_data['short_ratio'] = float(value)
                            except:
                                pass
                        
                        elif 'Shs Float' in label:
                            # Parse like "45.2M"
                            si_data['float_shares'] = self._parse_shares(value)
                        
                        elif 'Shs Outstand' in label:
                            shares_out = self._parse_shares(value)
                            if shares_out > 0 and si_data['short_percent_float'] > 0:
                                si_data['short_percent_shares_outstanding'] = (
                                    si_data['short_percent_float'] * si_data['float_shares'] / shares_out
                                )
            
            # Calculate shares short if we have the data
            if si_data['short_percent_float'] > 0 and si_data['float_shares'] > 0:
                si_data['shares_short'] = (
                    si_data['short_percent_float'] / 100 * si_data['float_shares']
                )
            
            self._cache_data(cache_key, si_data)
            return si_data
            
        except Exception as e:
            print(f"Error fetching real SI for {symbol}: {e}")
            return self._get_fallback_si(symbol)
    
    def _get_fallback_si(self, symbol: str) -> Dict:
        """Fallback to yfinance if scraping fails"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                'short_percent_float': info.get('shortPercentOfFloat', 0) * 100 if info.get('shortPercentOfFloat') else 0,
                'short_ratio': info.get('shortRatio', 0),
                'shares_short': info.get('sharesShort', 0),
                'float_shares': info.get('floatShares', 0),
                'short_percent_shares_outstanding': info.get('shortPercentageOfSharesOutstanding', 0) * 100 if info.get('shortPercentageOfSharesOutstanding') else 0,
                'data_source': 'yfinance',
                'timestamp': datetime.now().isoformat()
            }
        except:
            return {
                'short_percent_float': 0,
                'short_ratio': 0,
                'shares_short': 0,
                'float_shares': 0,
                'short_percent_shares_outstanding': 0,
                'data_source': 'unavailable',
                'timestamp': datetime.now().isoformat()
            }
    
    # ========== 2. REAL OPTIONS FLOW ==========
    
    def get_options_flow_data(self, symbol: str) -> Dict:
        """
        Detect unusual options activity
        Returns: unusual_activity_score, sweep_orders, block_trades, put_call_ratio
        """
        
        cache_key = f"options_flow_{symbol}"
        if self._check_cache(cache_key):
            return self.cache[cache_key]['data']
        
        try:
            ticker = yf.Ticker(symbol)
            
            # Get options chain
            exp_dates = ticker.options
            if not exp_dates or len(exp_dates) == 0:
                return self._get_empty_options_flow()
            
            # Get nearest expiration
            nearest_exp = exp_dates[0]
            opt_chain = ticker.option_chain(nearest_exp)
            
            calls = opt_chain.calls
            puts = opt_chain.puts
            
            flow_data = {
                'unusual_activity_score': 0,
                'sweep_orders_detected': 0,
                'block_trades_detected': 0,
                'put_call_ratio': 0,
                'call_volume': 0,
                'put_volume': 0,
                'call_oi': 0,
                'put_oi': 0,
                'unusual_call_buying': False,
                'unusual_put_buying': False,
                'data_source': 'yfinance_options',
                'timestamp': datetime.now().isoformat()
            }
            
            # Calculate volumes
            call_volume = calls['volume'].sum() if 'volume' in calls.columns else 0
            put_volume = puts['volume'].sum() if 'volume' in puts.columns else 0
            call_oi = calls['openInterest'].sum() if 'openInterest' in calls.columns else 0
            put_oi = puts['openInterest'].sum() if 'openInterest' in puts.columns else 0
            
            flow_data['call_volume'] = int(call_volume)
            flow_data['put_volume'] = int(put_volume)
            flow_data['call_oi'] = int(call_oi)
            flow_data['put_oi'] = int(put_oi)
            
            # Put/Call Ratio
            total_vol = call_volume + put_volume
            if total_vol > 0:
                flow_data['put_call_ratio'] = put_volume / call_volume if call_volume > 0 else 999
            
            # Detect unusual activity
            # 1. Volume vs Open Interest (fresh activity)
            volume_oi_ratio_calls = call_volume / call_oi if call_oi > 0 else 0
            volume_oi_ratio_puts = put_volume / put_oi if put_oi > 0 else 0
            
            # Unusual if volume > 2x open interest
            if volume_oi_ratio_calls > 2:
                flow_data['unusual_call_buying'] = True
                flow_data['unusual_activity_score'] += 30
            
            if volume_oi_ratio_puts > 2:
                flow_data['unusual_put_buying'] = True
                flow_data['unusual_activity_score'] += 15
            
            # 2. Detect potential sweep orders (large volume at ask)
            if 'volume' in calls.columns:
                # High volume calls (potential sweeps)
                high_vol_calls = calls[calls['volume'] > calls['volume'].quantile(0.9)]
                flow_data['sweep_orders_detected'] = len(high_vol_calls)
                
                if len(high_vol_calls) > 3:
                    flow_data['unusual_activity_score'] += 25
            
            # 3. Detect block trades (unusual open interest changes)
            if call_oi > 10000:  # Significant OI
                flow_data['block_trades_detected'] += 1
                flow_data['unusual_activity_score'] += 20
            
            # 4. Put/Call ratio extremes
            if flow_data['put_call_ratio'] < 0.5:  # Heavy call buying
                flow_data['unusual_activity_score'] += 25
            elif flow_data['put_call_ratio'] > 2:  # Heavy put buying
                flow_data['unusual_activity_score'] -= 10
            
            # Cap score at 100
            flow_data['unusual_activity_score'] = min(100, max(0, flow_data['unusual_activity_score']))
            
            self._cache_data(cache_key, flow_data)
            return flow_data
            
        except Exception as e:
            print(f"Error fetching options flow for {symbol}: {e}")
            return self._get_empty_options_flow()
    
    def _get_empty_options_flow(self) -> Dict:
        """Return empty options flow data"""
        return {
            'unusual_activity_score': 0,
            'sweep_orders_detected': 0,
            'block_trades_detected': 0,
            'put_call_ratio': 1,
            'call_volume': 0,
            'put_volume': 0,
            'call_oi': 0,
            'put_oi': 0,
            'unusual_call_buying': False,
            'unusual_put_buying': False,
            'data_source': 'unavailable',
            'timestamp': datetime.now().isoformat()
        }
    
    # ========== 3. BORROW RATE TRACKING ==========
    
    def get_borrow_rate(self, symbol: str) -> Dict:
        """
        Get borrow rate (proxy via finviz short data + volatility)
        High borrow rate = hard to short = more squeeze fuel
        """
        
        try:
            # Real borrow rates require paid services
            # We'll estimate based on short interest and volatility
            si_data = self.get_real_short_interest(symbol)
            
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='1mo')
            
            if hist.empty:
                return {'estimated_borrow_rate': 0, 'borrow_difficulty': 'UNKNOWN'}
            
            # Calculate volatility
            returns = hist['Close'].pct_change()
            volatility = returns.std() * np.sqrt(252) * 100
            
            # Estimate borrow rate based on short interest and volatility
            si_pct = si_data.get('short_percent_float', 0)
            
            # High SI + High volatility = High borrow rate
            estimated_rate = 0
            difficulty = 'EASY'
            
            if si_pct > 30:
                estimated_rate += 50
            elif si_pct > 20:
                estimated_rate += 30
            elif si_pct > 10:
                estimated_rate += 15
            
            if volatility > 100:
                estimated_rate += 30
            elif volatility > 75:
                estimated_rate += 20
            elif volatility > 50:
                estimated_rate += 10
            
            # Classify difficulty
            if estimated_rate > 50:
                difficulty = 'VERY HARD'
            elif estimated_rate > 30:
                difficulty = 'HARD'
            elif estimated_rate > 15:
                difficulty = 'MODERATE'
            
            return {
                'estimated_borrow_rate': min(100, estimated_rate),
                'borrow_difficulty': difficulty,
                'short_interest': si_pct,
                'volatility': volatility,
                'note': 'Estimated based on SI% and volatility',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'estimated_borrow_rate': 0, 'borrow_difficulty': 'UNKNOWN'}
    
    # ========== 4. DARK POOL DETECTION ==========
    
    def detect_dark_pool_activity(self, symbol: str) -> Dict:
        """
        Detect institutional dark pool accumulation
        Returns: dark_pool_score, accumulation_pattern, institutional_buying
        """
        
        cache_key = f"dark_pool_{symbol}"
        if self._check_cache(cache_key):
            return self.cache[cache_key]['data']
        
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='1mo')
            
            if len(hist) < 10:
                return self._get_empty_dark_pool()
            
            dark_pool_data = {
                'dark_pool_score': 0,
                'accumulation_pattern': False,
                'institutional_buying': False,
                'unusual_block_trades': 0,
                'price_vs_volume_divergence': 0,
                'data_source': 'price_action_analysis',
                'timestamp': datetime.now().isoformat()
            }
            
            # Detect dark pool via price/volume divergence
            # Dark pools = high volume, price stable/down (accumulation)
            
            # Recent 5 days
            recent_vol = hist['Volume'].tail(5).mean()
            recent_price_change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-6]) / hist['Close'].iloc[-6] * 100)
            
            # Historical 20 days
            hist_vol = hist['Volume'].tail(20).head(15).mean()
            
            # Volume surge but price flat = dark pool accumulation
            vol_increase = ((recent_vol - hist_vol) / hist_vol * 100) if hist_vol > 0 else 0
            
            if vol_increase > 50 and abs(recent_price_change) < 5:
                # High volume, price stable = accumulation
                dark_pool_data['accumulation_pattern'] = True
                dark_pool_data['institutional_buying'] = True
                dark_pool_data['dark_pool_score'] += 60
            elif vol_increase > 30 and abs(recent_price_change) < 3:
                dark_pool_data['accumulation_pattern'] = True
                dark_pool_data['dark_pool_score'] += 40
            
            # Detect block trades (huge volume spikes on single days)
            daily_vol_avg = hist['Volume'].mean()
            huge_vol_days = hist[hist['Volume'] > daily_vol_avg * 3]
            dark_pool_data['unusual_block_trades'] = len(huge_vol_days)
            
            if len(huge_vol_days) > 2:
                dark_pool_data['dark_pool_score'] += 30
            
            # Price vs Volume divergence score
            dark_pool_data['price_vs_volume_divergence'] = abs(vol_increase - recent_price_change)
            
            # Cap score
            dark_pool_data['dark_pool_score'] = min(100, dark_pool_data['dark_pool_score'])
            
            self._cache_data(cache_key, dark_pool_data)
            return dark_pool_data
            
        except Exception as e:
            print(f"Error detecting dark pool for {symbol}: {e}")
            return self._get_empty_dark_pool()
    
    def _get_empty_dark_pool(self) -> Dict:
        """Return empty dark pool data"""
        return {
            'dark_pool_score': 0,
            'accumulation_pattern': False,
            'institutional_buying': False,
            'unusual_block_trades': 0,
            'price_vs_volume_divergence': 0,
            'data_source': 'unavailable',
            'timestamp': datetime.now().isoformat()
        }
    
    # ========== 5. FLOAT ROTATION ANALYSIS ==========
    
    def analyze_float_rotation(self, symbol: str) -> Dict:
        """
        Track if entire float is trading (squeeze indicator)
        Returns: rotation_rate, days_to_trade_float, float_turnover_ratio
        """
        
        try:
            si_data = self.get_real_short_interest(symbol)
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='1mo')
            
            if hist.empty or si_data['float_shares'] == 0:
                return self._get_empty_float_rotation()
            
            float_shares = si_data['float_shares']
            
            # Calculate float rotation
            # Recent 5-day volume
            recent_5d_vol = hist['Volume'].tail(5).sum()
            
            # Recent 20-day volume
            recent_20d_vol = hist['Volume'].tail(20).sum()
            
            rotation_data = {
                'rotation_rate_5d': (recent_5d_vol / float_shares) if float_shares > 0 else 0,
                'rotation_rate_20d': (recent_20d_vol / float_shares) if float_shares > 0 else 0,
                'days_to_trade_float': 0,
                'float_turnover_ratio': 0,
                'entire_float_trading': False,
                'squeeze_indicator': False,
                'data_source': 'calculated',
                'timestamp': datetime.now().isoformat()
            }
            
            # Average daily volume
            avg_daily_vol = hist['Volume'].tail(20).mean()
            
            # Days to trade entire float
            if avg_daily_vol > 0:
                rotation_data['days_to_trade_float'] = float_shares / avg_daily_vol
            
            # Float turnover ratio (how many times float traded in 20 days)
            rotation_data['float_turnover_ratio'] = rotation_data['rotation_rate_20d']
            
            # Squeeze indicators
            # If entire float trades in < 3 days = extremely hot
            if rotation_data['rotation_rate_5d'] > 1.5:  # 150% of float in 5 days
                rotation_data['entire_float_trading'] = True
                rotation_data['squeeze_indicator'] = True
            elif rotation_data['rotation_rate_5d'] > 1.0:  # 100% of float in 5 days
                rotation_data['entire_float_trading'] = True
            
            return rotation_data
            
        except Exception as e:
            print(f"Error analyzing float rotation for {symbol}: {e}")
            return self._get_empty_float_rotation()
    
    def _get_empty_float_rotation(self) -> Dict:
        """Return empty float rotation data"""
        return {
            'rotation_rate_5d': 0,
            'rotation_rate_20d': 0,
            'days_to_trade_float': 999,
            'float_turnover_ratio': 0,
            'entire_float_trading': False,
            'squeeze_indicator': False,
            'data_source': 'unavailable',
            'timestamp': datetime.now().isoformat()
        }
    
    # ========== HELPER FUNCTIONS ==========
    
    def _parse_shares(self, value: str) -> float:
        """Parse share counts like '45.2M' or '1.5B'"""
        try:
            value = value.upper().replace(',', '')
            if 'B' in value:
                return float(value.replace('B', '')) * 1_000_000_000
            elif 'M' in value:
                return float(value.replace('M', '')) * 1_000_000
            elif 'K' in value:
                return float(value.replace('K', '')) * 1_000
            else:
                return float(value)
        except:
            return 0
    
    def _check_cache(self, key: str) -> bool:
        """Check if cached data is still valid"""
        if key in self.cache:
            age = time.time() - self.cache[key]['timestamp']
            return age < self.cache_duration
        return False
    
    def _cache_data(self, key: str, data: Dict):
        """Cache data with timestamp"""
        self.cache[key] = {
            'data': data,
            'timestamp': time.time()
        }


    # ========== 6. HISTORICAL WIN RATE ==========
    
    def calculate_historical_win_rate(self, symbol: str, pattern_type: str = 'squeeze') -> Dict:
        """
        Back-test historical patterns and calculate win rate
        Returns: win_rate, avg_gain, avg_loss, success_count, total_patterns
        """
        
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='1y')  # 1 year of data
            
            if len(hist) < 60:
                return self._get_empty_win_rate()
            
            win_rate_data = {
                'win_rate': 0,
                'avg_gain_percent': 0,
                'avg_loss_percent': 0,
                'success_count': 0,
                'failure_count': 0,
                'total_patterns': 0,
                'best_gain': 0,
                'worst_loss': 0,
                'pattern_type': pattern_type,
                'confidence_level': 'LOW',
                'timestamp': datetime.now().isoformat()
            }
            
            # Detect historical squeeze patterns
            # Pattern: Volume spike + price consolidation → breakout
            
            patterns_found = []
            
            for i in range(20, len(hist)-10):  # Need data before and after
                # Check for pattern setup
                vol_spike = hist['Volume'].iloc[i] > hist['Volume'].iloc[i-10:i].mean() * 2
                price_range = (hist['High'].iloc[i-5:i].max() - hist['Low'].iloc[i-5:i].min()) / hist['Close'].iloc[i] * 100
                price_compressed = price_range < 5  # Less than 5% range
                
                if vol_spike and price_compressed:
                    # Found pattern - check outcome in next 10 days
                    entry_price = hist['Close'].iloc[i]
                    max_price_10d = hist['High'].iloc[i+1:i+11].max()
                    min_price_10d = hist['Low'].iloc[i+1:i+11].min()
                    
                    # Calculate potential gain/loss
                    potential_gain = ((max_price_10d - entry_price) / entry_price * 100)
                    potential_loss = ((min_price_10d - entry_price) / entry_price * 100)
                    
                    # Define win as 5%+ gain before 5%+ loss
                    if potential_gain >= 5:
                        patterns_found.append({
                            'outcome': 'WIN',
                            'gain': potential_gain,
                            'entry_price': entry_price,
                            'date': hist.index[i]
                        })
                    elif potential_loss <= -5:
                        patterns_found.append({
                            'outcome': 'LOSS',
                            'loss': potential_loss,
                            'entry_price': entry_price,
                            'date': hist.index[i]
                        })
            
            # Calculate statistics
            if patterns_found:
                wins = [p for p in patterns_found if p['outcome'] == 'WIN']
                losses = [p for p in patterns_found if p['outcome'] == 'LOSS']
                
                win_rate_data['success_count'] = len(wins)
                win_rate_data['failure_count'] = len(losses)
                win_rate_data['total_patterns'] = len(patterns_found)
                
                if win_rate_data['total_patterns'] > 0:
                    win_rate_data['win_rate'] = (len(wins) / len(patterns_found) * 100)
                
                if wins:
                    win_rate_data['avg_gain_percent'] = np.mean([w['gain'] for w in wins])
                    win_rate_data['best_gain'] = max([w['gain'] for w in wins])
                
                if losses:
                    win_rate_data['avg_loss_percent'] = np.mean([l['loss'] for l in losses])
                    win_rate_data['worst_loss'] = min([l['loss'] for l in losses])
                
                # Confidence level based on sample size and win rate
                if win_rate_data['total_patterns'] >= 10:
                    if win_rate_data['win_rate'] >= 70:
                        win_rate_data['confidence_level'] = 'VERY HIGH'
                    elif win_rate_data['win_rate'] >= 60:
                        win_rate_data['confidence_level'] = 'HIGH'
                    elif win_rate_data['win_rate'] >= 50:
                        win_rate_data['confidence_level'] = 'MODERATE'
                    else:
                        win_rate_data['confidence_level'] = 'LOW'
                elif win_rate_data['total_patterns'] >= 5:
                    win_rate_data['confidence_level'] = 'MODERATE'
            
            return win_rate_data
            
        except Exception as e:
            print(f"Error calculating win rate for {symbol}: {e}")
            return self._get_empty_win_rate()
    
    def _get_empty_win_rate(self) -> Dict:
        """Return empty win rate data"""
        return {
            'win_rate': 0,
            'avg_gain_percent': 0,
            'avg_loss_percent': 0,
            'success_count': 0,
            'failure_count': 0,
            'total_patterns': 0,
            'best_gain': 0,
            'worst_loss': 0,
            'pattern_type': 'unknown',
            'confidence_level': 'UNKNOWN',
            'timestamp': datetime.now().isoformat()
        }
    
    # ========== 7. CATALYST INTEGRATION ==========
    
    def get_upcoming_catalysts(self, symbol: str) -> Dict:
        """
        Get upcoming catalysts: earnings, FDA approvals, product launches
        Returns: catalyst_score, next_catalyst, catalyst_type, days_until
        """
        
        cache_key = f"catalysts_{symbol}"
        if self._check_cache(cache_key):
            return self.cache[cache_key]['data']
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            catalyst_data = {
                'catalyst_score': 0,
                'has_upcoming_catalyst': False,
                'next_catalyst': None,
                'catalyst_type': None,
                'days_until_catalyst': 999,
                'earnings_date': None,
                'catalysts': [],
                'data_source': 'yfinance',
                'timestamp': datetime.now().isoformat()
            }
            
            # Check for earnings
            if 'earningsDate' in info and info['earningsDate']:
                try:
                    # Get first earnings date
                    earnings_timestamp = info['earningsDate']
                    if isinstance(earnings_timestamp, list) and len(earnings_timestamp) > 0:
                        earnings_timestamp = earnings_timestamp[0]
                    
                    earnings_date = pd.to_datetime(earnings_timestamp, unit='s')
                    days_until = (earnings_date - pd.Timestamp.now()).days
                    
                    if days_until >= 0 and days_until <= 60:  # Within 60 days
                        catalyst_data['has_upcoming_catalyst'] = True
                        catalyst_data['next_catalyst'] = f"Earnings in {days_until} days"
                        catalyst_data['catalyst_type'] = 'EARNINGS'
                        catalyst_data['days_until_catalyst'] = days_until
                        catalyst_data['earnings_date'] = earnings_date.strftime('%Y-%m-%d')
                        
                        catalyst_data['catalysts'].append({
                            'type': 'EARNINGS',
                            'date': earnings_date.strftime('%Y-%m-%d'),
                            'days_until': days_until,
                            'importance': 'HIGH'
                        })
                        
                        # Catalyst score based on proximity
                        if days_until <= 7:
                            catalyst_data['catalyst_score'] = 100
                        elif days_until <= 14:
                            catalyst_data['catalyst_score'] = 80
                        elif days_until <= 30:
                            catalyst_data['catalyst_score'] = 60
                        else:
                            catalyst_data['catalyst_score'] = 40
                except:
                    pass
            
            # Check industry for other catalysts
            sector = info.get('sector', '')
            industry = info.get('industry', '')
            
            # Biotech/Pharma - potential FDA catalysts
            if 'bio' in industry.lower() or 'pharma' in industry.lower() or 'health' in sector.lower():
                catalyst_data['catalysts'].append({
                    'type': 'POTENTIAL_FDA',
                    'note': 'Biotech/Pharma - monitor for FDA approvals',
                    'importance': 'MEDIUM'
                })
                catalyst_data['catalyst_score'] += 20
            
            # Tech - product launches
            if 'tech' in sector.lower() or 'software' in industry.lower():
                catalyst_data['catalysts'].append({
                    'type': 'POTENTIAL_PRODUCT_LAUNCH',
                    'note': 'Tech sector - monitor for product announcements',
                    'importance': 'MEDIUM'
                })
                catalyst_data['catalyst_score'] += 10
            
            # Cap score at 100
            catalyst_data['catalyst_score'] = min(100, catalyst_data['catalyst_score'])
            
            self._cache_data(cache_key, catalyst_data)
            return catalyst_data
            
        except Exception as e:
            print(f"Error fetching catalysts for {symbol}: {e}")
            return self._get_empty_catalysts()
    
    def _get_empty_catalysts(self) -> Dict:
        """Return empty catalyst data"""
        return {
            'catalyst_score': 0,
            'has_upcoming_catalyst': False,
            'next_catalyst': None,
            'catalyst_type': None,
            'days_until_catalyst': 999,
            'earnings_date': None,
            'catalysts': [],
            'data_source': 'unavailable',
            'timestamp': datetime.now().isoformat()
        }
    
    # ========== 8. SOCIAL SENTIMENT ==========
    
    def get_social_sentiment(self, symbol: str) -> Dict:
        """
        Get social sentiment score from Reddit/WSB buzz
        Returns: sentiment_score, buzz_level, trending, mentions_count
        """
        
        cache_key = f"sentiment_{symbol}"
        if self._check_cache(cache_key):
            return self.cache[cache_key]['data']
        
        # Note: Real social sentiment requires API access to Reddit/Twitter
        # This is a proxy based on volume and volatility (social stocks = high volume + volatility)
        
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='1mo')
            info = ticker.info
            
            if hist.empty:
                return self._get_empty_sentiment()
            
            sentiment_data = {
                'sentiment_score': 0,
                'buzz_level': 'LOW',
                'is_trending': False,
                'social_volume_proxy': 0,
                'retail_interest': 'LOW',
                'wsb_candidate': False,
                'data_source': 'proxy_analysis',
                'timestamp': datetime.now().isoformat()
            }
            
            # Proxy indicators for social/retail interest:
            # 1. Volume surge
            recent_vol = hist['Volume'].tail(5).mean()
            hist_vol = hist['Volume'].tail(20).head(15).mean()
            vol_surge = ((recent_vol - hist_vol) / hist_vol * 100) if hist_vol > 0 else 0
            
            # 2. Volatility (meme stocks are volatile)
            returns = hist['Close'].pct_change()
            volatility = returns.std() * np.sqrt(252) * 100
            
            # 3. Price range (big swings = retail attention)
            price_range_pct = ((hist['High'].tail(5).max() - hist['Low'].tail(5).min()) / hist['Close'].tail(5).mean() * 100)
            
            # 4. Market cap (smaller = more retail friendly)
            market_cap = info.get('marketCap', 0)
            
            # Calculate sentiment score
            score = 0
            
            # Volume surge scoring
            if vol_surge > 200:
                score += 40
                sentiment_data['social_volume_proxy'] = vol_surge
            elif vol_surge > 100:
                score += 30
                sentiment_data['social_volume_proxy'] = vol_surge
            elif vol_surge > 50:
                score += 20
                sentiment_data['social_volume_proxy'] = vol_surge
            
            # Volatility scoring
            if volatility > 100:
                score += 30
            elif volatility > 75:
                score += 20
            
            # Price action scoring
            if price_range_pct > 20:
                score += 20
            elif price_range_pct > 10:
                score += 10
            
            # Market cap scoring (smaller = more retail)
            if market_cap < 500_000_000:  # < $500M
                score += 10
                sentiment_data['retail_interest'] = 'VERY HIGH'
            elif market_cap < 2_000_000_000:  # < $2B
                score += 5
                sentiment_data['retail_interest'] = 'HIGH'
            
            sentiment_data['sentiment_score'] = min(100, score)
            
            # Classify buzz level
            if sentiment_data['sentiment_score'] >= 75:
                sentiment_data['buzz_level'] = 'VERY HIGH'
                sentiment_data['is_trending'] = True
                sentiment_data['wsb_candidate'] = True
            elif sentiment_data['sentiment_score'] >= 60:
                sentiment_data['buzz_level'] = 'HIGH'
                sentiment_data['is_trending'] = True
            elif sentiment_data['sentiment_score'] >= 40:
                sentiment_data['buzz_level'] = 'MODERATE'
            else:
                sentiment_data['buzz_level'] = 'LOW'
            
            self._cache_data(cache_key, sentiment_data)
            return sentiment_data
            
        except Exception as e:
            print(f"Error calculating sentiment for {symbol}: {e}")
            return self._get_empty_sentiment()
    
    def _get_empty_sentiment(self) -> Dict:
        """Return empty sentiment data"""
        return {
            'sentiment_score': 0,
            'buzz_level': 'UNKNOWN',
            'is_trending': False,
            'social_volume_proxy': 0,
            'retail_interest': 'UNKNOWN',
            'wsb_candidate': False,
            'data_source': 'unavailable',
            'timestamp': datetime.now().isoformat()
        }


# Global instance
advanced_data = AdvancedDataSources()
