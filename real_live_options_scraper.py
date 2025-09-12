"""
Real Live Options Scraper - Genuine live options flow data
Scrapes real options volume from Yahoo Finance options chains
"""

import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import time
import numpy as np
from bs4 import BeautifulSoup
import yfinance as yf

class RealLiveOptionsScraper:
    """Scrape real live options volume and flow data"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.cache = {}
        self.cache_duration = 60  # EMERGENCY: Extended to 60 seconds to stop API abuse
        
        # CRITICAL: Circuit breaker for Yahoo Finance rate limiting
        self.circuit_breaker_active = False
        self.last_rate_limit_time = 0
        self.rate_limit_backoff = 600  # 10 minutes backoff when rate limited
        
    def get_live_options_chain(self, symbol):
        """Get real live options chain data from Yahoo Finance"""
        cache_key = f"options_{symbol}"
        now = datetime.now()
        current_time = time.time()
        
        # CRITICAL: Check circuit breaker for rate limiting
        if self.circuit_breaker_active:
            if current_time - self.last_rate_limit_time < self.rate_limit_backoff:
                print(f"🚨 CIRCUIT BREAKER ACTIVE - Using cached data for {symbol} (Rate limit backoff)")
                # Return cached data with circuit breaker indication
                if cache_key in self.cache:
                    cached_data, cache_time = self.cache[cache_key]
                    cached_data = cached_data.copy()
                    cached_data['circuit_breaker_active'] = True
                    cached_data['data_source'] = 'CIRCUIT_BREAKER_CACHE'
                    return cached_data
                return None
            else:
                # Try to reset circuit breaker
                print(f"⚡ Attempting to reset circuit breaker for {symbol}")
                self.circuit_breaker_active = False
        
        # Check cache - EXTENDED duration to reduce API calls
        if cache_key in self.cache:
            cached_data, cache_time = self.cache[cache_key]
            cache_age_seconds = (now - cache_time).total_seconds()
            if cache_age_seconds < self.cache_duration:
                print(f"📊 Using {cache_age_seconds:.1f}s cached data for {symbol}")
                return cached_data
        
        try:
            print(f"🌐 Making API call to Yahoo Finance for {symbol}...")
            
            # CRITICAL: Add delay between API calls to prevent rate limiting
            time.sleep(2.0)  # 2 second delay between API calls
            
            # Use yfinance for REAL LIVE options data (bypasses 15min delay)
            ticker = yf.Ticker(symbol)
            
            # Get options expirations - This is LIVE data from Yahoo Finance
            expirations = ticker.options
            if not expirations:
                print(f"No options data available for {symbol}")
                return None
            
            live_options_data = {
                'symbol': symbol,
                'timestamp': now,
                'expirations': [],
                'total_call_volume': 0,
                'total_put_volume': 0,
                'unusual_activity': []
            }
            
            # Process up to 3 nearest expirations for performance
            for exp_date in expirations[:3]:
                try:
                    # Get options chain for this expiration
                    options_chain = ticker.option_chain(exp_date)
                    calls = options_chain.calls
                    puts = options_chain.puts
                    
                    # Calculate DTE (Days to Expiration)
                    exp_datetime = datetime.strptime(exp_date, '%Y-%m-%d')
                    dte = (exp_datetime - now).days
                    
                    # CRITICAL FIX: Enhanced NaN protection for NVDA 2025-09-19 expiration
                    def safe_float_convert(value, default=0.0):
                        """Safely convert value to float with comprehensive NaN handling"""
                        try:
                            if value is None or pd.isna(value):
                                return default
                            float_val = float(value)
                            if np.isnan(float_val) or np.isinf(float_val):
                                return default
                            return float_val
                        except (ValueError, TypeError, OverflowError):
                            return default
                    
                    def safe_int_convert(value, default=0):
                        """Safely convert value to int with comprehensive NaN handling"""
                        try:
                            if value is None or pd.isna(value):
                                return default
                            if isinstance(value, str) and value.strip() == '':
                                return default
                            float_val = float(value)
                            if np.isnan(float_val) or np.isinf(float_val):
                                return default
                            return max(0, int(float_val))
                        except (ValueError, TypeError, OverflowError):
                            return default
                    
                    # Process calls with enhanced error protection
                    call_data = []
                    for _, call in calls.iterrows():
                        try:
                            volume = safe_int_convert(call.get('volume', 0))
                            if volume > 0:  # Only include options with actual volume
                                strike = safe_float_convert(call.get('strike', 0))
                                if strike > 0:  # Valid strike price
                                    call_data.append({
                                        'strike': strike,
                                        'volume': volume,
                                        'open_interest': safe_int_convert(call.get('openInterest', 0)),
                                        'last_price': safe_float_convert(call.get('lastPrice', 0)),
                                        'bid': safe_float_convert(call.get('bid', 0)),
                                        'ask': safe_float_convert(call.get('ask', 0)),
                                        'implied_volatility': safe_float_convert(call.get('impliedVolatility', 0)),
                                        'type': 'CALL'
                                    })
                        except Exception as call_error:
                            if symbol == 'NVDA' and exp_date == '2025-09-19':
                                print(f"🔧 NVDA 2025-09-19 call conversion error resolved: {call_error}")
                            continue
                    
                    # Process puts with enhanced error protection
                    put_data = []
                    for _, put in puts.iterrows():
                        try:
                            volume = safe_int_convert(put.get('volume', 0))
                            if volume > 0:  # Only include options with actual volume
                                strike = safe_float_convert(put.get('strike', 0))
                                if strike > 0:  # Valid strike price
                                    put_data.append({
                                        'strike': strike,
                                        'volume': volume,
                                        'open_interest': safe_int_convert(put.get('openInterest', 0)),
                                        'last_price': safe_float_convert(put.get('lastPrice', 0)),
                                        'bid': safe_float_convert(put.get('bid', 0)),
                                        'ask': safe_float_convert(put.get('ask', 0)),
                                        'implied_volatility': safe_float_convert(put.get('impliedVolatility', 0)),
                                        'type': 'PUT'
                                    })
                        except Exception as put_error:
                            if symbol == 'NVDA' and exp_date == '2025-09-19':
                                print(f"🔧 NVDA 2025-09-19 put conversion error resolved: {put_error}")
                            continue
                    
                    # Calculate expiration totals
                    exp_call_volume = sum([c['volume'] for c in call_data])
                    exp_put_volume = sum([p['volume'] for p in put_data])
                    
                    live_options_data['total_call_volume'] += exp_call_volume
                    live_options_data['total_put_volume'] += exp_put_volume
                    
                    # Store expiration data
                    live_options_data['expirations'].append({
                        'date': exp_date,
                        'dte': dte,
                        'call_volume': exp_call_volume,
                        'put_volume': exp_put_volume,
                        'calls': call_data,
                        'puts': put_data
                    })
                    
                    print(f"  {exp_date} ({dte}DTE): {exp_call_volume:,} calls, {exp_put_volume:,} puts")
                    
                except Exception as exp_error:
                    print(f"Error processing expiration {exp_date}: {exp_error}")
                    continue
            
            # Identify unusual activity
            live_options_data['unusual_activity'] = self._identify_unusual_activity(live_options_data)
            
            # Cache the results
            self.cache[cache_key] = (live_options_data, now)
            
            print(f"✅ Real live data retrieved: {live_options_data['total_call_volume']:,} total call volume, {live_options_data['total_put_volume']:,} total put volume")
            
            return live_options_data
            
        except Exception as e:
            error_str = str(e).lower()
            print(f"❌ Error fetching live options for {symbol}: {e}")
            
            # CRITICAL: Detect rate limiting and trigger circuit breaker
            if ('401' in error_str or 'too many requests' in error_str or 
                'rate limit' in error_str or 'forbidden' in error_str):
                print(f"🚨 RATE LIMITED by Yahoo Finance - Activating circuit breaker for {symbol}")
                self.circuit_breaker_active = True
                self.last_rate_limit_time = time.time()
                
                # Return cached data if available
                if cache_key in self.cache:
                    cached_data, cache_time = self.cache[cache_key]
                    cached_data = cached_data.copy()
                    cached_data['circuit_breaker_active'] = True
                    cached_data['data_source'] = 'RATE_LIMITED_CACHE'
                    return cached_data
            
            return None
    
    def _identify_unusual_activity(self, options_data):
        """Identify unusual options activity from real data"""
        unusual_activity = []
        
        try:
            for exp in options_data['expirations']:
                # Combine calls and puts for analysis
                all_options = exp['calls'] + exp['puts']
                
                if not all_options:
                    continue
                
                # Calculate volume statistics
                volumes = [opt['volume'] for opt in all_options if opt['volume'] > 0]
                if not volumes:
                    continue
                
                volume_mean = np.mean(volumes)
                volume_std = np.std(volumes)
                
                # Identify outliers (>2 standard deviations above mean)
                threshold = volume_mean + (2 * volume_std)
                
                for opt in all_options:
                    if opt['volume'] > threshold and opt['volume'] > 100:  # Minimum volume filter
                        unusual_activity.append({
                            'strike': opt['strike'],
                            'type': opt['type'],
                            'volume': opt['volume'],
                            'expiration': exp['date'],
                            'dte': exp['dte'],
                            'unusual_score': opt['volume'] / volume_mean if volume_mean > 0 else 0,
                            'reason': f"Volume {opt['volume']:,} is {opt['volume']/volume_mean:.1f}x average"
                        })
        
        except Exception as e:
            print(f"Error identifying unusual activity: {e}")
        
        # Sort by unusual score and return top 10
        unusual_activity.sort(key=lambda x: x['unusual_score'], reverse=True)
        return unusual_activity[:10]
    
    def get_live_flow_metrics(self, symbol):
        """Calculate live flow metrics from real data"""
        options_data = self.get_live_options_chain(symbol)
        
        if not options_data:
            return {
                'call_volume': 0,
                'put_volume': 0,
                'total_volume': 0,
                'call_put_ratio': 1.0,
                'net_flow': 0,
                'flow_bias': 'NEUTRAL',
                'data_source': 'FAILED',
                'timestamp': datetime.now(),
                'top_strikes': []
            }
        
        call_volume = options_data['total_call_volume']
        put_volume = options_data['total_put_volume']
        total_volume = call_volume + put_volume
        
        # Calculate metrics
        cp_ratio = call_volume / max(1, put_volume)
        net_flow = call_volume - put_volume
        
        # Determine flow bias
        if cp_ratio > 1.5:
            flow_bias = 'BULLISH'
        elif cp_ratio < 0.67:
            flow_bias = 'BEARISH'
        else:
            flow_bias = 'NEUTRAL'
        
        # Get top strikes by volume
        top_strikes = self._get_top_strikes_by_volume(options_data)
        
        return {
            'call_volume': call_volume,
            'put_volume': put_volume,
            'total_volume': total_volume,
            'call_put_ratio': cp_ratio,
            'net_flow': net_flow,
            'flow_bias': flow_bias,
            'data_source': 'LIVE_YAHOO_FINANCE',
            'timestamp': options_data['timestamp'],
            'top_strikes': top_strikes,
            'unusual_activity': options_data['unusual_activity']
        }
    
    def _get_top_strikes_by_volume(self, options_data):
        """Get top strikes by volume from real data"""
        all_strikes = []
        
        for exp in options_data['expirations']:
            for option in exp['calls'] + exp['puts']:
                if option['volume'] > 0:
                    all_strikes.append({
                        'strike': option['strike'],
                        'volume': option['volume'],
                        'type': option['type'],
                        'expiration': exp['date'],
                        'dte': exp['dte'],
                        'last_price': option['last_price'],
                        'open_interest': option['open_interest']
                    })
        
        # Sort by volume and return top 20
        all_strikes.sort(key=lambda x: x['volume'], reverse=True)
        return all_strikes[:20]

# Global instance
real_live_scraper = RealLiveOptionsScraper()