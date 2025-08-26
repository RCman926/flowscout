"""
Real-Time Data Infrastructure
Implementation of live data feeds using API bypasses and web scraping
"""

import requests
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import re
import asyncio
import aiohttp
import time
from bs4 import BeautifulSoup
import warnings
warnings.filterwarnings('ignore')

class RealTimeDataInfrastructure:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://finance.yahoo.com/',
            'Connection': 'keep-alive'
        })
        self.cache = {}
        self.cache_duration = 15  # 15 seconds cache for real-time data
        
    def get_live_stock_data(self, symbol):
        """
        Get LIVE stock data by bypassing Yahoo Finance API limitations
        Yahoo.com shows live data but API gives 15-minute delay
        """
        cache_key = f"live_{symbol}"
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
        
        try:
            # Method 1: Scrape Yahoo Finance website directly for live data
            live_data = self._scrape_yahoo_live_data(symbol)
            
            if live_data and live_data.get('price', 0) > 0:
                self._cache_data(cache_key, live_data)
                return live_data
                
            # Method 2: Try alternative sources
            alt_data = self._get_alternative_live_data(symbol)
            
            if alt_data and alt_data.get('price', 0) > 0:
                self._cache_data(cache_key, alt_data)
                return alt_data
                
        except Exception as e:
            print(f"Live data error for {symbol}: {e}")
        
        # Fallback to Yahoo API (delayed but functional)
        return self._get_yahoo_api_fallback(symbol)
    
    def _scrape_yahoo_live_data(self, symbol):
        """Scrape live data directly from Yahoo Finance website"""
        try:
            url = f"https://finance.yahoo.com/quote/{symbol}"
            
            # Make request with realistic headers
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                # Parse the HTML response
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract live price from fin-streamer elements
                price_elem = soup.find('fin-streamer', {'data-symbol': symbol, 'data-field': 'regularMarketPrice'})
                change_elem = soup.find('fin-streamer', {'data-symbol': symbol, 'data-field': 'regularMarketChange'})
                change_pct_elem = soup.find('fin-streamer', {'data-symbol': symbol, 'data-field': 'regularMarketChangePercent'})
                volume_elem = soup.find('fin-streamer', {'data-symbol': symbol, 'data-field': 'regularMarketVolume'})
                
                if price_elem:
                    price = float(price_elem.get('value', 0))
                    change = float(change_elem.get('value', 0)) if change_elem else 0
                    change_pct = float(change_pct_elem.get('value', 0)) if change_pct_elem else 0
                    volume = int(volume_elem.get('value', 0)) if volume_elem else 0
                    
                    # Extract additional data from the page
                    additional_data = self._extract_yahoo_page_data(response.text, symbol)
                    
                    return {
                        'symbol': symbol,
                        'price': price,
                        'change': change,
                        'change_pct': change_pct,
                        'volume': volume,
                        'bid': additional_data.get('bid', price),
                        'ask': additional_data.get('ask', price),
                        'high': additional_data.get('dayHigh', price),
                        'low': additional_data.get('dayLow', price),
                        'timestamp': datetime.now(),
                        'data_source': 'Yahoo Finance Live Scrape',
                        'is_real_time': True,
                        'data_quality': 'HIGH'
                    }
        
        except Exception as e:
            print(f"Yahoo scraping failed: {e}")
            
        return None
    
    def _extract_yahoo_page_data(self, html_content, symbol):
        """Extract additional data from Yahoo Finance page JSON"""
        try:
            # Look for embedded JSON data in the page
            json_pattern = r'root\.App\.main\s*=\s*({.+?});'
            match = re.search(json_pattern, html_content)
            
            if match:
                json_str = match.group(1)
                data = json.loads(json_str)
                
                # Navigate through nested JSON structure
                quote_data = data.get('context', {}).get('dispatcher', {}).get('stores', {}).get('QuoteSummaryStore', {})
                price_data = quote_data.get('price', {})
                
                return {
                    'bid': price_data.get('bid', {}).get('raw', 0),
                    'ask': price_data.get('ask', {}).get('raw', 0),
                    'dayHigh': price_data.get('regularMarketDayHigh', {}).get('raw', 0),
                    'dayLow': price_data.get('regularMarketDayLow', {}).get('raw', 0),
                    'marketCap': price_data.get('marketCap', {}).get('raw', 0)
                }
        
        except Exception as e:
            print(f"JSON extraction error: {e}")
        
        return {}
    
    def _get_alternative_live_data(self, symbol):
        """Get data from alternative sources"""
        sources = [
            self._get_marketwatch_data,
            self._get_cnbc_data,
            self._get_bloomberg_data
        ]
        
        for source in sources:
            try:
                data = source(symbol)
                if data and data.get('price', 0) > 0:
                    return data
            except Exception as e:
                continue
        
        return None
    
    def _get_marketwatch_data(self, symbol):
        """Scrape MarketWatch for live data"""
        try:
            url = f"https://www.marketwatch.com/investing/stock/{symbol}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find price element
                price_elem = soup.find('bg-quote', class_='value')
                if not price_elem:
                    price_elem = soup.find(class_=lambda x: x and 'intraday__price' in x)
                
                if price_elem:
                    price_text = price_elem.get_text().strip()
                    price = float(re.sub(r'[^\d.-]', '', price_text))
                    
                    return {
                        'symbol': symbol,
                        'price': price,
                        'timestamp': datetime.now(),
                        'data_source': 'MarketWatch Live',
                        'is_real_time': True
                    }
        
        except Exception as e:
            print(f"MarketWatch error: {e}")
        
        return None
    
    def _get_cnbc_data(self, symbol):
        """Scrape CNBC for live data"""
        try:
            url = f"https://www.cnbc.com/quotes/{symbol}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                price_elem = soup.find(class_=lambda x: x and 'QuoteStrip-lastPrice' in x)
                
                if price_elem:
                    price_text = price_elem.get_text().strip()
                    price = float(re.sub(r'[^\d.-]', '', price_text))
                    
                    return {
                        'symbol': symbol,
                        'price': price,
                        'timestamp': datetime.now(),
                        'data_source': 'CNBC Live',
                        'is_real_time': True
                    }
        
        except Exception as e:
            print(f"CNBC error: {e}")
        
        return None
    
    def _get_bloomberg_data(self, symbol):
        """Scrape Bloomberg for live data (public quotes)"""
        try:
            # Bloomberg has public quote data
            url = f"https://www.bloomberg.com/quote/{symbol}:US"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                # Bloomberg uses dynamic content, look for price patterns
                price_pattern = r'"price":"([\d.]+)"'
                match = re.search(price_pattern, response.text)
                
                if match:
                    price = float(match.group(1))
                    
                    return {
                        'symbol': symbol,
                        'price': price,
                        'timestamp': datetime.now(),
                        'data_source': 'Bloomberg Public',
                        'is_real_time': True
                    }
        
        except Exception as e:
            print(f"Bloomberg error: {e}")
        
        return None
    
    def _get_yahoo_api_fallback(self, symbol):
        """Fallback to Yahoo Finance API (delayed but reliable)"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='1d', interval='1m')
            
            if not hist.empty:
                current_price = float(hist['Close'].iloc[-1])
                volume = int(hist['Volume'].iloc[-1])
                
                # Calculate change from previous close
                if len(hist) > 1:
                    prev_close = float(hist['Close'].iloc[-2])
                    change = current_price - prev_close
                    change_pct = (change / prev_close) * 100
                else:
                    change = 0
                    change_pct = 0
                
                return {
                    'symbol': symbol,
                    'price': current_price,
                    'change': change,
                    'change_pct': change_pct,
                    'volume': volume,
                    'timestamp': datetime.now(),
                    'data_source': 'Yahoo API (Delayed)',
                    'is_real_time': False,
                    'data_quality': 'MEDIUM'
                }
        
        except Exception as e:
            print(f"Yahoo API fallback error: {e}")
        
        return None
    
    def get_live_options_chain(self, symbol):
        """Get live options data by scraping Yahoo Finance options page"""
        try:
            url = f"https://finance.yahoo.com/quote/{symbol}/options"
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find options tables
                calls_data = self._parse_options_table(soup, 'calls')
                puts_data = self._parse_options_table(soup, 'puts')
                
                # Get underlying price
                underlying_price = self._get_underlying_price_from_options_page(soup)
                
                return {
                    'symbol': symbol,
                    'underlying_price': underlying_price,
                    'calls': calls_data,
                    'puts': puts_data,
                    'timestamp': datetime.now(),
                    'data_source': 'Yahoo Options Live Scrape',
                    'is_real_time': True
                }
                
        except Exception as e:
            print(f"Options chain scraping error: {e}")
        
        return None
    
    def _parse_options_table(self, soup, option_type):
        """Parse options table from Yahoo Finance"""
        options_data = []
        
        try:
            # Yahoo has separate tables for calls and puts
            tables = soup.find_all('table')
            
            # Determine which table to use based on option type
            table_index = 0 if option_type == 'calls' else 1
            
            if len(tables) > table_index:
                table = tables[table_index]
                rows = table.find('tbody').find_all('tr') if table.find('tbody') else []
                
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 10:
                        try:
                            option_data = {
                                'strike': float(cells[2].get_text().strip()),
                                'last': self._parse_price(cells[3].get_text()),
                                'bid': self._parse_price(cells[4].get_text()),
                                'ask': self._parse_price(cells[5].get_text()),
                                'change': self._parse_price(cells[6].get_text()),
                                'volume': self._parse_volume(cells[8].get_text()),
                                'open_interest': self._parse_volume(cells[9].get_text()),
                                'implied_volatility': self._parse_percentage(cells[10].get_text()) if len(cells) > 10 else 0
                            }
                            
                            if option_data['strike'] > 0:
                                options_data.append(option_data)
                                
                        except (ValueError, IndexError):
                            continue
        
        except Exception as e:
            print(f"Options table parsing error: {e}")
        
        return options_data
    
    def _get_underlying_price_from_options_page(self, soup):
        """Extract underlying price from options page"""
        try:
            price_elem = soup.find('fin-streamer', {'data-field': 'regularMarketPrice'})
            if price_elem:
                return float(price_elem.get('value', 0))
        except:
            pass
        
        return 0
    
    def _parse_price(self, text):
        """Parse price from text"""
        try:
            clean_text = re.sub(r'[^\d.-]', '', text.strip())
            return float(clean_text) if clean_text else 0
        except:
            return 0
    
    def _parse_volume(self, text):
        """Parse volume with K/M notation"""
        try:
            text = text.strip().upper()
            if 'K' in text:
                return int(float(text.replace('K', '')) * 1000)
            elif 'M' in text:
                return int(float(text.replace('M', '')) * 1000000)
            else:
                clean_text = re.sub(r'[^\d]', '', text)
                return int(clean_text) if clean_text else 0
        except:
            return 0
    
    def _parse_percentage(self, text):
        """Parse percentage value"""
        try:
            clean_text = re.sub(r'[^\d.-]', '', text.strip().replace('%', ''))
            return float(clean_text) if clean_text else 0
        except:
            return 0
    
    def _is_cache_valid(self, key):
        """Check if cached data is still valid"""
        if key not in self.cache:
            return False
        age = (datetime.now() - self.cache[key]['timestamp']).seconds
        return age < self.cache_duration
    
    def _cache_data(self, key, data):
        """Cache data with timestamp"""
        self.cache[key] = {
            'data': data,
            'timestamp': datetime.now()
        }
    
    def get_data_feed_comparison(self):
        """Show comparison of different data feed options"""
        return {
            'tier_1_institutional': {
                'name': 'OPRA Direct Feed',
                'latency': '<10ms',
                'cost': '$1,500-10,000/month',
                'coverage': 'All US exchanges',
                'accuracy': '100%',
                'reliability': '99.99%'
            },
            'tier_2_professional': {
                'name': 'Interactive Brokers API',
                'latency': '<100ms',
                'cost': '$4-25/month',
                'coverage': 'Most exchanges',
                'accuracy': '99.9%',
                'reliability': '99.5%'
            },
            'tier_3_bypasses': {
                'name': 'Web Scraping Bypasses',
                'latency': '1-5 seconds',
                'cost': 'FREE',
                'coverage': 'Major symbols',
                'accuracy': '95-99%',
                'reliability': '90-95%'
            },
            'current_implementation': {
                'primary': 'Yahoo Finance Live Scraping',
                'fallback': 'Yahoo Finance API',
                'advantages': [
                    'Bypasses 15-minute API delay',
                    'Multiple source aggregation',
                    'No cost for development',
                    'Real-time during market hours'
                ],
                'limitations': [
                    'Dependent on website structure',
                    'Rate limiting possible',
                    'No official API guarantee'
                ]
            }
        }

# Initialize the real-time data infrastructure
real_time_data = RealTimeDataInfrastructure()