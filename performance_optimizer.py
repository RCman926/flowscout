"""
Performance optimization utilities for faster loading
"""

import streamlit as st
import time
import json
from datetime import datetime, timedelta
from functools import lru_cache
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

class PerformanceOptimizer:
    def __init__(self):
        self.cache_duration = 120  # 2 minutes for faster loading
        self.executor = ThreadPoolExecutor(max_workers=6)
        
    def setup_session_cache(self):
        """Initialize aggressive caching in session state"""
        if 'perf_cache' not in st.session_state:
            st.session_state.perf_cache = {}
        if 'last_cache_update' not in st.session_state:
            st.session_state.last_cache_update = {}
        if 'batch_data' not in st.session_state:
            st.session_state.batch_data = {}
    
    def is_cache_valid(self, key):
        """Check if cached data is still valid"""
        if key not in st.session_state.perf_cache:
            return False
        
        last_update = st.session_state.last_cache_update.get(key, 0)
        return time.time() - last_update < self.cache_duration
    
    def set_cache(self, key, data):
        """Store data in cache with timestamp"""
        st.session_state.perf_cache[key] = data
        st.session_state.last_cache_update[key] = time.time()
    
    def get_cache(self, key):
        """Get cached data if valid"""
        if self.is_cache_valid(key):
            return st.session_state.perf_cache[key]
        return None
    
    def batch_fetch_market_data(self, symbols):
        """Fetch market data for multiple symbols in parallel"""
        cache_key = f"batch_market_{','.join(symbols)}"
        cached = self.get_cache(cache_key)
        if cached:
            return cached
        
        def fetch_single(symbol):
            try:
                from dashboard_data_coordinator import coordinator
                return symbol, coordinator.get_market_data(symbol)
            except Exception as e:
                return symbol, {'error': str(e)}
        
        # Parallel execution
        futures = {self.executor.submit(fetch_single, symbol): symbol for symbol in symbols}
        results = {}
        
        for future in as_completed(futures, timeout=10):
            try:
                symbol, data = future.result()
                results[symbol] = data
            except Exception as e:
                symbol = futures[future]
                results[symbol] = {'error': str(e)}
        
        self.set_cache(cache_key, results)
        return results
    
    def batch_fetch_signals(self, symbols):
        """Fetch trading signals for multiple symbols in parallel"""
        cache_key = f"batch_signals_{','.join(symbols)}"
        cached = self.get_cache(cache_key)
        if cached:
            return cached
        
        def fetch_signal(symbol):
            try:
                from dashboard_data_coordinator import coordinator
                return symbol, coordinator.generate_trading_signal(symbol)
            except Exception as e:
                return symbol, {'signal': 'HOLD', 'confidence': 50, 'reasons': [str(e)]}
        
        futures = {self.executor.submit(fetch_signal, symbol): symbol for symbol in symbols}
        results = {}
        
        for future in as_completed(futures, timeout=8):
            try:
                symbol, data = future.result()
                results[symbol] = data
            except Exception as e:
                symbol = futures[future]
                results[symbol] = {'signal': 'HOLD', 'confidence': 50, 'reasons': ['Timeout']}
        
        self.set_cache(cache_key, results)
        return results
    
    def preload_essential_data(self, symbol):
        """Preload essential data for a symbol to speed up initial load"""
        cache_key = f"essential_{symbol}"
        cached = self.get_cache(cache_key)
        if cached:
            return cached
        
        def load_market_data():
            from dashboard_data_coordinator import coordinator
            return coordinator.get_market_data(symbol)
        
        def load_options_flow():
            from dashboard_data_coordinator import coordinator
            return coordinator.get_options_flow(symbol)
        
        def load_technical_data():
            from dashboard_data_coordinator import coordinator
            return coordinator.get_technical_indicators(symbol)
        
        # Load in parallel
        futures = {
            self.executor.submit(load_market_data): 'market',
            self.executor.submit(load_options_flow): 'options',
            self.executor.submit(load_technical_data): 'technical'
        }
        
        results = {}
        for future in as_completed(futures, timeout=12):
            try:
                data_type = futures[future]
                results[data_type] = future.result()
            except Exception as e:
                data_type = futures[future]
                results[data_type] = {'error': str(e)}
        
        self.set_cache(cache_key, results)
        return results
    
    @lru_cache(maxsize=32)
    def cached_strategy_generation(self, symbol, price_key):
        """Cache strategy generation with price as part of key"""
        try:
            from professional_risk_management import professional_risk
            return professional_risk.generate_balanced_strategies(symbol, 50000)
        except Exception as e:
            return []

# Initialize global performance optimizer
perf_optimizer = PerformanceOptimizer()