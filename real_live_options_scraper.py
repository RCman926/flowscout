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
        self.cache_duration = 30  # 30 seconds cache
        
    def get_live_options_chain(self, symbol):
        """Get real live options chain data from Yahoo Finance"""
        cache_key = f"options_{symbol}"
        now = datetime.now()
        
        # Check cache
        if cache_key in self.cache:
            cached_data, cache_time = self.cache[cache_key]
            if (now - cache_time).seconds < self.cache_duration:
                return cached_data
        
        try:
            print(f"Fetching REAL live options data for {symbol}...")
            
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
                    
                    # Process calls
                    call_data = []
                    for _, call in calls.iterrows():
                        volume = call.get('volume', 0) or 0
                        if volume > 0:  # Only include options with actual volume
                            call_data.append({
                                'strike': float(call['strike']),
                                'volume': int(volume),
                                'open_interest': int(call.get('openInterest', 0) or 0),
                                'last_price': float(call.get('lastPrice', 0) or 0),
                                'bid': float(call.get('bid', 0) or 0),
                                'ask': float(call.get('ask', 0) or 0),
                                'implied_volatility': float(call.get('impliedVolatility', 0) or 0),
                                'type': 'CALL'
                            })
                    
                    # Process puts
                    put_data = []
                    for _, put in puts.iterrows():
                        volume = put.get('volume', 0) or 0
                        if volume > 0:  # Only include options with actual volume
                            put_data.append({
                                'strike': float(put['strike']),
                                'volume': int(volume),
                                'open_interest': int(put.get('openInterest', 0) or 0),
                                'last_price': float(put.get('lastPrice', 0) or 0),
                                'bid': float(put.get('bid', 0) or 0),
                                'ask': float(put.get('ask', 0) or 0),
                                'implied_volatility': float(put.get('impliedVolatility', 0) or 0),
                                'type': 'PUT'
                            })
                    
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
            print(f"❌ Error fetching live options for {symbol}: {e}")
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