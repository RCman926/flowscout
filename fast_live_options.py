"""
Fast Live Options - Optimized for speed
Quick options data without delays
"""

import yfinance as yf
from datetime import datetime
import streamlit as st
import pandas as pd

class FastLiveOptions:
    """Fast options data with caching for speed"""
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 60  # 1 minute cache for speed
        
    @st.cache_data(ttl=60)  # Streamlit cache for extra speed
    def get_quick_options_data(_self, symbol):
        """Get quick options data with aggressive caching"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Get only nearest expiration for speed
            expirations = ticker.options
            if not expirations:
                return None
            
            # Filter out expired options and get valid expiration
            valid_expirations = []
            current_date = datetime.now().date()
            
            for exp_date in expirations:
                exp_datetime = datetime.strptime(exp_date, '%Y-%m-%d').date()
                dte = (exp_datetime - current_date).days
                
                # Only include non-expired options (DTE >= 0)
                if dte >= 0:
                    valid_expirations.append((exp_date, dte))
            
            if not valid_expirations:
                # No valid expirations found
                return {
                    'call_volume': 0,
                    'put_volume': 0,
                    'total_volume': 0,
                    'cp_ratio': 1.0,
                    'timestamp': datetime.now(),
                    'expiration': 'No valid options',
                    'dte': 'N/A'
                }
            
            # Use nearest valid expiration for speed
            exp_date, dte = valid_expirations[0]
            options_chain = ticker.option_chain(exp_date)
            
            calls = options_chain.calls
            puts = options_chain.puts
            
            # Quick volume calculations
            call_volume = calls['volume'].fillna(0).sum()
            put_volume = puts['volume'].fillna(0).sum()
            
            return {
                'call_volume': int(call_volume),
                'put_volume': int(put_volume),
                'total_volume': int(call_volume + put_volume),
                'cp_ratio': call_volume / max(1, put_volume),
                'timestamp': datetime.now(),
                'expiration': exp_date,
                'dte': dte
            }
            
        except Exception as e:
            print(f"Fast options error: {e}")
            return {
                'call_volume': 0,
                'put_volume': 0,
                'total_volume': 0,
                'cp_ratio': 1.0,
                'timestamp': datetime.now(),
                'expiration': 'N/A'
            }

fast_options = FastLiveOptions()