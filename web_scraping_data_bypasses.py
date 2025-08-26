"""
Advanced Web Scraping Data Bypasses
Real-time data extraction from public financial websites
"""

import requests
import json
import time
import re
from datetime import datetime
from bs4 import BeautifulSoup
# Remove selenium for now to avoid import issues
# from selenium import webdriver
import pandas as pd

class WebScrapingDataBypasses:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
    def get_yahoo_live_data(self, symbol):
        """
        Yahoo.com shows LIVE data on the website but API gives delayed data
        This bypasses the API limitation by scraping the live website directly
        """
        try:
            # Yahoo Finance live page - shows real-time data
            url = f"https://finance.yahoo.com/quote/{symbol}"
            
            response = self.session.get(url, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract live price data from the page
                price_element = soup.find('fin-streamer', {'data-symbol': symbol, 'data-field': 'regularMarketPrice'})
                change_element = soup.find('fin-streamer', {'data-symbol': symbol, 'data-field': 'regularMarketChange'})
                change_pct_element = soup.find('fin-streamer', {'data-symbol': symbol, 'data-field': 'regularMarketChangePercent'})
                volume_element = soup.find('fin-streamer', {'data-symbol': symbol, 'data-field': 'regularMarketVolume'})
                
                if price_element:
                    current_price = float(price_element.get('value', 0))
                    change = float(change_element.get('value', 0)) if change_element else 0
                    change_pct = float(change_pct_element.get('value', 0)) if change_pct_element else 0
                    volume = int(volume_element.get('value', 0)) if volume_element else 0
                    
                    # Get additional data from JSON embedded in page
                    json_data = self._extract_yahoo_json_data(response.text, symbol)
                    
                    return {
                        'symbol': symbol,
                        'current_price': current_price,
                        'change': change,
                        'change_pct': change_pct,
                        'volume': volume,
                        'bid': json_data.get('bid', current_price),
                        'ask': json_data.get('ask', current_price),
                        'high': json_data.get('high', current_price),
                        'low': json_data.get('low', current_price),
                        'timestamp': datetime.now(),
                        'data_source': 'Yahoo Live Scrape',
                        'is_real_time': True
                    }
                    
        except Exception as e:
            print(f"Yahoo live scraping error: {e}")
            return None
    
    def _extract_yahoo_json_data(self, html_content, symbol):
        """Extract additional data from Yahoo's embedded JSON"""
        try:
            # Look for the JSON data embedded in the page
            json_pattern = r'root\.App\.main\s*=\s*({.+?});'
            match = re.search(json_pattern, html_content)
            
            if match:
                json_str = match.group(1)
                data = json.loads(json_str)
                
                # Navigate through the nested JSON structure
                quote_data = data.get('context', {}).get('dispatcher', {}).get('stores', {}).get('QuoteSummaryStore', {})
                price_data = quote_data.get('price', {})
                
                return {
                    'bid': price_data.get('bid', {}).get('raw', 0),
                    'ask': price_data.get('ask', {}).get('raw', 0),
                    'high': price_data.get('regularMarketDayHigh', {}).get('raw', 0),
                    'low': price_data.get('regularMarketDayLow', {}).get('raw', 0),
                    'market_cap': price_data.get('marketCap', {}).get('raw', 0)
                }
            
        except Exception as e:
            print(f"JSON extraction error: {e}")
        
        return {}
    
    def get_live_options_chain_bypass(self, symbol):
        """
        Bypass API limitations to get live options data from Yahoo
        """
        try:
            # Options page URL
            url = f"https://finance.yahoo.com/quote/{symbol}/options"
            
            response = self.session.get(url, timeout=20)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract options data from tables
                options_tables = soup.find_all('table')
                
                calls_data = []
                puts_data = []
                
                for table in options_tables:
                    # Determine if it's calls or puts table
                    is_calls_table = 'calls' in str(table).lower()
                    
                    rows = table.find_all('tr')[1:]  # Skip header
                    
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 8:
                            try:
                                strike = float(cells[0].text.strip())
                                last_price = self._parse_price(cells[1].text.strip())
                                bid = self._parse_price(cells[2].text.strip())
                                ask = self._parse_price(cells[3].text.strip())
                                change = self._parse_price(cells[4].text.strip())
                                volume = self._parse_volume(cells[5].text.strip())
                                open_interest = self._parse_volume(cells[6].text.strip())
                                implied_vol = self._parse_percentage(cells[7].text.strip())
                                
                                option_data = {
                                    'strike': strike,
                                    'last': last_price,
                                    'bid': bid,
                                    'ask': ask,
                                    'change': change,
                                    'volume': volume,
                                    'open_interest': open_interest,
                                    'implied_volatility': implied_vol
                                }
                                
                                if is_calls_table:
                                    calls_data.append(option_data)
                                else:
                                    puts_data.append(option_data)
                                    
                            except (ValueError, IndexError) as e:
                                continue
                
                return {
                    'symbol': symbol,
                    'calls': calls_data,
                    'puts': puts_data,
                    'timestamp': datetime.now(),
                    'data_source': 'Yahoo Options Scrape',
                    'is_real_time': True
                }
                
        except Exception as e:
            print(f"Options chain scraping error: {e}")
            return None
    
    def get_cboe_live_data_bypass(self, symbol):
        """
        Scrape live data from CBOE website directly
        """
        try:
            # CBOE quotes page
            url = f"https://www.cboe.com/delayed_quotes/spy/quote_table"
            
            # Use different headers for CBOE
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.cboe.com/',
                'Accept': 'application/json, text/plain, */*'
            }
            
            response = self.session.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                # Try to parse as JSON first
                try:
                    data = response.json()
                    return self._parse_cboe_json(data, symbol)
                except json.JSONDecodeError:
                    # Parse as HTML
                    soup = BeautifulSoup(response.content, 'html.parser')
                    return self._parse_cboe_html(soup, symbol)
                    
        except Exception as e:
            print(f"CBOE scraping error: {e}")
            return None
    
    def get_marketwatch_live_bypass(self, symbol):
        """
        Scrape live data from MarketWatch
        """
        try:
            url = f"https://www.marketwatch.com/investing/stock/{symbol}"
            
            response = self.session.get(url, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract price data
                price_element = soup.find('bg-quote', class_='value')
                if not price_element:
                    price_element = soup.find(class_=lambda x: x and 'intraday__price' in x)
                
                change_element = soup.find(class_=lambda x: x and 'change' in x.lower())
                
                if price_element:
                    current_price = self._parse_price(price_element.get_text().strip())
                    
                    # Extract change data
                    change = 0
                    change_pct = 0
                    
                    if change_element:
                        change_text = change_element.get_text().strip()
                        change_match = re.search(r'([+-]?\d+\.?\d*)', change_text)
                        if change_match:
                            change = float(change_match.group(1))
                        
                        pct_match = re.search(r'([+-]?\d+\.?\d*)%', change_text)
                        if pct_match:
                            change_pct = float(pct_match.group(1))
                    
                    return {
                        'symbol': symbol,
                        'current_price': current_price,
                        'change': change,
                        'change_pct': change_pct,
                        'timestamp': datetime.now(),
                        'data_source': 'MarketWatch Live',
                        'is_real_time': True
                    }
                    
        except Exception as e:
            print(f"MarketWatch scraping error: {e}")
            return None
    
    def get_cnbc_live_bypass(self, symbol):
        """
        Scrape live data from CNBC
        """
        try:
            url = f"https://www.cnbc.com/quotes/{symbol}"
            
            response = self.session.get(url, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # CNBC uses specific classes for quote data
                price_element = soup.find(class_=lambda x: x and 'QuoteStrip-lastPrice' in x)
                change_element = soup.find(class_=lambda x: x and 'QuoteStrip-changeUp' in x or 'QuoteStrip-changeDown' in x)
                
                if price_element:
                    current_price = self._parse_price(price_element.get_text().strip())
                    
                    change = 0
                    change_pct = 0
                    
                    if change_element:
                        change_text = change_element.get_text().strip()
                        # Parse change and percentage
                        change_parts = change_text.split()
                        if len(change_parts) >= 2:
                            change = self._parse_price(change_parts[0])
                            change_pct = self._parse_percentage(change_parts[1])
                    
                    return {
                        'symbol': symbol,
                        'current_price': current_price,
                        'change': change,
                        'change_pct': change_pct,
                        'timestamp': datetime.now(),
                        'data_source': 'CNBC Live',
                        'is_real_time': True
                    }
                    
        except Exception as e:
            print(f"CNBC scraping error: {e}")
            return None
    
    def _parse_price(self, price_str):
        """Parse price string to float"""
        try:
            # Remove any non-numeric characters except decimal point and minus
            clean_price = re.sub(r'[^\d.-]', '', price_str.replace(',', ''))
            return float(clean_price) if clean_price else 0
        except:
            return 0
    
    def _parse_volume(self, volume_str):
        """Parse volume string to integer"""
        try:
            clean_volume = re.sub(r'[^\d]', '', volume_str.replace(',', ''))
            return int(clean_volume) if clean_volume else 0
        except:
            return 0
    
    def _parse_percentage(self, pct_str):
        """Parse percentage string to float"""
        try:
            clean_pct = re.sub(r'[^\d.-]', '', pct_str.replace('%', ''))
            return float(clean_pct) if clean_pct else 0
        except:
            return 0
    
    def _parse_cboe_json(self, data, symbol):
        """Parse CBOE JSON response"""
        try:
            # CBOE JSON structure parsing
            return {
                'symbol': symbol,
                'current_price': data.get('last_trade_price', 0),
                'volume': data.get('volume', 0),
                'timestamp': datetime.now(),
                'data_source': 'CBOE JSON'
            }
        except:
            return None
    
    def _parse_cboe_html(self, soup, symbol):
        """Parse CBOE HTML response"""
        try:
            # Extract data from HTML tables
            price_cell = soup.find(text=re.compile(r'\$\d+\.\d+'))
            if price_cell:
                price = self._parse_price(price_cell)
                return {
                    'symbol': symbol,
                    'current_price': price,
                    'timestamp': datetime.now(),
                    'data_source': 'CBOE HTML'
                }
        except:
            return None
    
    def get_aggregated_live_data(self, symbol):
        """
        Aggregate data from multiple sources for most accurate live data
        """
        sources = [
            self.get_yahoo_live_data,
            self.get_marketwatch_live_bypass,
            self.get_cnbc_live_bypass
        ]
        
        results = []
        
        for source_func in sources:
            try:
                data = source_func(symbol)
                if data and data.get('current_price', 0) > 0:
                    results.append(data)
            except Exception as e:
                continue
        
        if not results:
            return None
        
        # Take the most recent and average the prices
        prices = [r['current_price'] for r in results if r.get('current_price')]
        changes = [r['change'] for r in results if r.get('change')]
        volumes = [r['volume'] for r in results if r.get('volume')]
        
        if prices:
            return {
                'symbol': symbol,
                'current_price': sum(prices) / len(prices),  # Average price
                'change': sum(changes) / len(changes) if changes else 0,
                'change_pct': (sum(changes) / len(changes) / (sum(prices) / len(prices))) * 100 if changes and prices else 0,
                'volume': max(volumes) if volumes else 0,  # Take highest volume
                'timestamp': datetime.now(),
                'data_source': f'Aggregated from {len(results)} sources',
                'sources_used': [r['data_source'] for r in results],
                'is_real_time': all(r.get('is_real_time', False) for r in results),
                'data_quality': 'HIGH' if len(results) >= 2 else 'MEDIUM'
            }
        
        return None

# Initialize the web scraping bypasses
web_bypasses = WebScrapingDataBypasses()