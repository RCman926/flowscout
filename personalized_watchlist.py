import streamlit as st
import json
import os
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import asyncio


class PersonalizedWatchlist:
    """
    Advanced personalized watchlist system with real-time price alerts
    """
    
    def __init__(self):
        self.watchlist_file = "user_watchlists.json"
        self.alerts_file = "price_alerts.json" 
        self.price_cache = {}
        self.cache_duration = 30  # 30 seconds cache
        self.alert_cooldown = 300  # 5 minute cooldown between same alerts
        self.last_alert_times = {}
        
        # Initialize storage files
        self._ensure_storage_files()
        
        # Start background monitoring if not already running
        if 'watchlist_monitor_active' not in st.session_state:
            st.session_state.watchlist_monitor_active = True
    
    def _ensure_storage_files(self):
        """Ensure storage files exist with default structure"""
        if not os.path.exists(self.watchlist_file):
            default_watchlists = {
                "My Stocks": {
                    "symbols": ["AAPL", "TSLA", "NVDA"],
                    "created": datetime.now().isoformat(),
                    "description": "My favorite tech stocks"
                },
                "Penny Stocks": {
                    "symbols": ["SNDL", "HITI", "MULN"],
                    "created": datetime.now().isoformat(), 
                    "description": "High-risk penny stock plays"
                }
            }
            with open(self.watchlist_file, 'w') as f:
                json.dump(default_watchlists, f, indent=2)
        
        if not os.path.exists(self.alerts_file):
            default_alerts = {}
            with open(self.alerts_file, 'w') as f:
                json.dump(default_alerts, f, indent=2)
    
    def get_watchlists(self) -> Dict:
        """Get all user watchlists"""
        try:
            with open(self.watchlist_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._ensure_storage_files()
            return self.get_watchlists()
    
    def save_watchlists(self, watchlists: Dict):
        """Save watchlists to storage"""
        with open(self.watchlist_file, 'w') as f:
            json.dump(watchlists, f, indent=2)
    
    def create_watchlist(self, name: str, symbols: List[str] = None, description: str = ""):
        """Create a new watchlist"""
        watchlists = self.get_watchlists()
        
        if name in watchlists:
            return False, f"Watchlist '{name}' already exists"
        
        watchlists[name] = {
            "symbols": symbols or [],
            "created": datetime.now().isoformat(),
            "description": description,
            "last_modified": datetime.now().isoformat()
        }
        
        self.save_watchlists(watchlists)
        return True, f"Created watchlist '{name}'"
    
    def delete_watchlist(self, name: str):
        """Delete a watchlist"""
        watchlists = self.get_watchlists()
        
        if name not in watchlists:
            return False, f"Watchlist '{name}' not found"
        
        del watchlists[name]
        self.save_watchlists(watchlists)
        
        # Also remove associated alerts
        self._remove_alerts_for_watchlist(name)
        
        return True, f"Deleted watchlist '{name}'"
    
    def add_symbol_to_watchlist(self, watchlist_name: str, symbol: str):
        """Add symbol to watchlist"""
        watchlists = self.get_watchlists()
        
        if watchlist_name not in watchlists:
            return False, f"Watchlist '{watchlist_name}' not found"
        
        symbol = symbol.upper().strip()
        
        # Validate symbol exists
        if not self._validate_symbol(symbol):
            return False, f"Invalid symbol: {symbol}"
        
        if symbol in watchlists[watchlist_name]["symbols"]:
            return False, f"{symbol} already in '{watchlist_name}'"
        
        watchlists[watchlist_name]["symbols"].append(symbol)
        watchlists[watchlist_name]["last_modified"] = datetime.now().isoformat()
        
        self.save_watchlists(watchlists)
        return True, f"Added {symbol} to '{watchlist_name}'"
    
    def remove_symbol_from_watchlist(self, watchlist_name: str, symbol: str):
        """Remove symbol from watchlist"""
        watchlists = self.get_watchlists()
        
        if watchlist_name not in watchlists:
            return False, f"Watchlist '{watchlist_name}' not found"
        
        symbol = symbol.upper()
        
        if symbol not in watchlists[watchlist_name]["symbols"]:
            return False, f"{symbol} not in '{watchlist_name}'"
        
        watchlists[watchlist_name]["symbols"].remove(symbol)
        watchlists[watchlist_name]["last_modified"] = datetime.now().isoformat()
        
        self.save_watchlists(watchlists)
        
        # Remove associated alerts
        self._remove_alerts_for_symbol(symbol)
        
        return True, f"Removed {symbol} from '{watchlist_name}'"
    
    def _validate_symbol(self, symbol: str) -> bool:
        """Validate if a stock symbol exists"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return bool(info and 'symbol' in info)
        except:
            return False
    
    def get_real_time_prices(self, symbols: List[str]) -> Dict:
        """Get real-time prices for symbols with caching"""
        current_time = time.time()
        prices = {}
        
        symbols_to_fetch = []
        
        # Check cache first
        for symbol in symbols:
            cache_key = symbol
            if (cache_key in self.price_cache and 
                current_time - self.price_cache[cache_key].get('timestamp', 0) < self.cache_duration):
                prices[symbol] = self.price_cache[cache_key]['data']
            else:
                symbols_to_fetch.append(symbol)
        
        # Fetch missing prices
        if symbols_to_fetch:
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_symbol = {
                    executor.submit(self._fetch_single_price, symbol): symbol 
                    for symbol in symbols_to_fetch
                }
                
                for future in future_to_symbol:
                    symbol = future_to_symbol[future]
                    try:
                        price_data = future.result(timeout=5)
                        if price_data:
                            prices[symbol] = price_data
                            
                            # Cache the result
                            self.price_cache[symbol] = {
                                'data': price_data,
                                'timestamp': current_time
                            }
                    except Exception as e:
                        print(f"Error fetching {symbol}: {e}")
                        prices[symbol] = {
                            'current_price': 0,
                            'change': 0,
                            'change_percent': 0,
                            'error': str(e)
                        }
        
        return prices
    
    def _fetch_single_price(self, symbol: str) -> Optional[Dict]:
        """Fetch real-time price for a single symbol"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d")
            
            if hist.empty:
                return None
            
            current_price = float(hist['Close'].iloc[-1])
            prev_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
            
            change = current_price - prev_close
            change_percent = (change / prev_close) * 100 if prev_close != 0 else 0
            
            # Get additional info
            info = ticker.info
            
            return {
                'current_price': current_price,
                'prev_close': prev_close,
                'change': change,
                'change_percent': change_percent,
                'volume': int(hist['Volume'].iloc[-1]) if 'Volume' in hist.columns else 0,
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol
            }
            
        except Exception as e:
            print(f"Price fetch error for {symbol}: {e}")
            return None
    
    def get_alerts(self) -> Dict:
        """Get all price alerts"""
        try:
            with open(self.alerts_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def save_alerts(self, alerts: Dict):
        """Save alerts to storage"""
        with open(self.alerts_file, 'w') as f:
            json.dump(alerts, f, indent=2)
    
    def create_price_alert(self, symbol: str, alert_type: str, price_threshold: float, 
                          watchlist_name: str = "", note: str = ""):
        """Create a price alert"""
        alerts = self.get_alerts()
        
        alert_id = f"{symbol}_{alert_type}_{price_threshold}_{int(time.time())}"
        
        alerts[alert_id] = {
            'symbol': symbol.upper(),
            'alert_type': alert_type,  # 'above', 'below'
            'price_threshold': price_threshold,
            'watchlist_name': watchlist_name,
            'note': note,
            'created': datetime.now().isoformat(),
            'active': True,
            'triggered_count': 0,
            'last_triggered': None
        }
        
        self.save_alerts(alerts)
        return True, f"Created {alert_type} alert for {symbol} at ${price_threshold:.2f}"
    
    def remove_alert(self, alert_id: str):
        """Remove a price alert"""
        alerts = self.get_alerts()
        
        if alert_id not in alerts:
            return False, "Alert not found"
        
        del alerts[alert_id]
        self.save_alerts(alerts)
        return True, "Alert removed"
    
    def check_price_alerts(self, price_data: Dict):
        """Check if any alerts should be triggered"""
        alerts = self.get_alerts()
        triggered_alerts = []
        
        current_time = time.time()
        
        for alert_id, alert in alerts.items():
            if not alert['active']:
                continue
            
            symbol = alert['symbol']
            if symbol not in price_data:
                continue
            
            current_price = price_data[symbol].get('current_price', 0)
            if current_price == 0:
                continue
            
            # Check cooldown
            if alert_id in self.last_alert_times:
                time_since_last = current_time - self.last_alert_times[alert_id]
                if time_since_last < self.alert_cooldown:
                    continue
            
            # Check alert conditions
            should_trigger = False
            
            if alert['alert_type'] == 'above' and current_price >= alert['price_threshold']:
                should_trigger = True
            elif alert['alert_type'] == 'below' and current_price <= alert['price_threshold']:
                should_trigger = True
            
            if should_trigger:
                # Update alert
                alert['triggered_count'] += 1
                alert['last_triggered'] = datetime.now().isoformat()
                
                # Record cooldown
                self.last_alert_times[alert_id] = current_time
                
                triggered_alerts.append({
                    'alert_id': alert_id,
                    'symbol': symbol,
                    'alert_type': alert['alert_type'],
                    'price_threshold': alert['price_threshold'],
                    'current_price': current_price,
                    'note': alert.get('note', ''),
                    'watchlist_name': alert.get('watchlist_name', '')
                })
        
        # Save updated alerts
        if triggered_alerts:
            self.save_alerts(alerts)
        
        return triggered_alerts
    
    def _remove_alerts_for_watchlist(self, watchlist_name: str):
        """Remove all alerts associated with a watchlist"""
        alerts = self.get_alerts()
        to_remove = [
            alert_id for alert_id, alert in alerts.items() 
            if alert.get('watchlist_name') == watchlist_name
        ]
        
        for alert_id in to_remove:
            del alerts[alert_id]
        
        if to_remove:
            self.save_alerts(alerts)
    
    def _remove_alerts_for_symbol(self, symbol: str):
        """Remove all alerts for a specific symbol"""
        alerts = self.get_alerts()
        to_remove = [
            alert_id for alert_id, alert in alerts.items() 
            if alert['symbol'] == symbol
        ]
        
        for alert_id in to_remove:
            del alerts[alert_id]
        
        if to_remove:
            self.save_alerts(alerts)
    
    def get_watchlist_performance(self, watchlist_name: str) -> Dict:
        """Get performance summary for a watchlist"""
        watchlists = self.get_watchlists()
        
        if watchlist_name not in watchlists:
            return {}
        
        symbols = watchlists[watchlist_name]["symbols"]
        if not symbols:
            return {}
        
        prices = self.get_real_time_prices(symbols)
        
        total_change = 0
        winning_stocks = 0
        losing_stocks = 0
        total_volume = 0
        
        for symbol in symbols:
            if symbol in prices and 'change_percent' in prices[symbol]:
                change_pct = prices[symbol]['change_percent']
                total_change += change_pct
                
                if change_pct > 0:
                    winning_stocks += 1
                elif change_pct < 0:
                    losing_stocks += 1
                
                total_volume += prices[symbol].get('volume', 0)
        
        avg_change = total_change / len(symbols) if symbols else 0
        
        return {
            'total_symbols': len(symbols),
            'avg_change_percent': avg_change,
            'winning_stocks': winning_stocks,
            'losing_stocks': losing_stocks,
            'neutral_stocks': len(symbols) - winning_stocks - losing_stocks,
            'total_volume': total_volume,
            'performance_grade': self._get_performance_grade(avg_change)
        }
    
    def _get_performance_grade(self, avg_change: float) -> str:
        """Get letter grade for performance"""
        if avg_change >= 5:
            return "A+"
        elif avg_change >= 3:
            return "A"
        elif avg_change >= 1:
            return "B+"
        elif avg_change >= 0:
            return "B"
        elif avg_change >= -1:
            return "C"
        elif avg_change >= -3:
            return "D"
        else:
            return "F"


# Global instance
watchlist_manager = PersonalizedWatchlist()