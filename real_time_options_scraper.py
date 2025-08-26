"""
Real-Time Options Data Scraper
Bypasses API limitations to get live options data from Yahoo Finance website
"""

import requests
import json
import re
from datetime import datetime
from bs4 import BeautifulSoup
import pandas as pd

class RealTimeOptionsScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://finance.yahoo.com/',
            'Connection': 'keep-alive'
        })
    
    def get_live_options_data(self, symbol):
        """
        Scrape live options data directly from Yahoo Finance website
        This bypasses the API 15-minute delay to get real-time data
        """
        try:
            # Get the options page with live data
            url = f"https://finance.yahoo.com/quote/{symbol}/options"
            
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract the underlying stock price first
            underlying_price = self._extract_underlying_price(soup)
            
            # Find all expiration dates available
            expiration_select = soup.find('select', {'data-testid': 'expiry-select'})
            expirations = []
            if expiration_select:
                for option in expiration_select.find_all('option'):
                    expirations.append({
                        'date': option.get('value'),
                        'text': option.text.strip()
                    })
            
            # Get options data for current expiration
            calls_data = self._scrape_options_table(soup, 'calls')
            puts_data = self._scrape_options_table(soup, 'puts')
            
            # Calculate total volume and open interest
            total_call_volume = sum(opt.get('volume', 0) for opt in calls_data)
            total_put_volume = sum(opt.get('volume', 0) for opt in puts_data)
            total_call_oi = sum(opt.get('openInterest', 0) for opt in calls_data)
            total_put_oi = sum(opt.get('openInterest', 0) for opt in puts_data)
            
            return {
                'symbol': symbol,
                'underlying_price': underlying_price,
                'calls': calls_data,
                'puts': puts_data,
                'expirations': expirations,
                'total_call_volume': total_call_volume,
                'total_put_volume': total_put_volume,
                'total_call_oi': total_call_oi,
                'total_put_oi': total_put_oi,
                'call_put_ratio': total_call_volume / max(total_put_volume, 1),
                'timestamp': datetime.now(),
                'data_source': 'Yahoo Finance Live Scrape',
                'is_real_time': True
            }
            
        except Exception as e:
            print(f"Options scraping error for {symbol}: {e}")
            return None
    
    def _extract_underlying_price(self, soup):
        """Extract the current underlying stock price"""
        try:
            # Look for the price element
            price_element = soup.find('fin-streamer', {'data-field': 'regularMarketPrice'})
            if price_element:
                return float(price_element.get('value', 0))
            
            # Fallback: look for price in text
            price_pattern = r'\$(\d+\.\d+)'
            price_match = re.search(price_pattern, str(soup))
            if price_match:
                return float(price_match.group(1))
            
            return 0
        except:
            return 0
    
    def _scrape_options_table(self, soup, option_type):
        """Scrape options data from calls or puts table"""
        options_data = []
        
        try:
            # Find the options table for calls or puts
            table_selector = f"table[data-test*='{option_type}']" if option_type in ['calls', 'puts'] else "table"
            tables = soup.find_all('table')
            
            # Yahoo Finance typically has calls table first, then puts
            target_table = None
            for i, table in enumerate(tables):
                table_text = table.get_text().lower()
                if option_type == 'calls' and 'strike' in table_text and i == 0:
                    target_table = table
                    break
                elif option_type == 'puts' and 'strike' in table_text and i > 0:
                    target_table = table
                    break
            
            if not target_table:
                # Fallback: use table index
                table_index = 0 if option_type == 'calls' else 1
                if len(tables) > table_index:
                    target_table = tables[table_index]
            
            if target_table:
                # Extract data from table rows
                rows = target_table.find('tbody').find_all('tr') if target_table.find('tbody') else target_table.find_all('tr')[1:]
                
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 10:  # Yahoo typically has 10+ columns
                        try:
                            option_data = {
                                'strike': self._parse_number(cells[2].get_text()),
                                'lastPrice': self._parse_number(cells[3].get_text()),
                                'bid': self._parse_number(cells[4].get_text()),
                                'ask': self._parse_number(cells[5].get_text()),
                                'change': self._parse_number(cells[6].get_text()),
                                'percentChange': self._parse_percentage(cells[7].get_text()),
                                'volume': self._parse_volume(cells[8].get_text()),
                                'openInterest': self._parse_volume(cells[9].get_text()),
                                'impliedVolatility': self._parse_percentage(cells[10].get_text()) if len(cells) > 10 else 25.0
                            }
                            
                            # Only include options with valid data
                            if option_data['strike'] > 0:
                                options_data.append(option_data)
                                
                        except (IndexError, ValueError) as e:
                            continue
            
        except Exception as e:
            print(f"Table scraping error for {option_type}: {e}")
        
        return options_data
    
    def _parse_number(self, text):
        """Parse a number from text, handling various formats"""
        try:
            clean_text = re.sub(r'[^\d.-]', '', text.strip())
            return float(clean_text) if clean_text else 0
        except:
            return 0
    
    def _parse_volume(self, text):
        """Parse volume, handling formats like 1.2K, 5.4M"""
        try:
            text = text.strip().upper()
            if 'K' in text:
                return int(float(text.replace('K', '')) * 1000)
            elif 'M' in text:
                return int(float(text.replace('M', '')) * 1000000)
            else:
                return int(float(re.sub(r'[^\d]', '', text))) if text else 0
        except:
            return 0
    
    def _parse_percentage(self, text):
        """Parse percentage value"""
        try:
            clean_text = re.sub(r'[^\d.-]', '', text.strip().replace('%', ''))
            return float(clean_text) if clean_text else 0
        except:
            return 0
    
    def get_institutional_flow_data(self, symbol):
        """
        Scrape institutional flow data from multiple sources
        """
        flow_data = []
        
        # Try Barchart unusual options activity
        flow_data.extend(self._scrape_barchart_flow(symbol))
        
        # Try MarketWatch options volume
        flow_data.extend(self._scrape_marketwatch_flow(symbol))
        
        return {
            'symbol': symbol,
            'flows': flow_data,
            'total_unusual_volume': sum(f.get('volume', 0) for f in flow_data),
            'block_trades': len([f for f in flow_data if f.get('volume', 0) > 1000]),
            'sweep_orders': len([f for f in flow_data if f.get('type') == 'SWEEP']),
            'timestamp': datetime.now(),
            'data_source': 'Multiple Flow Sources'
        }
    
    def _scrape_barchart_flow(self, symbol):
        """Scrape unusual options activity from Barchart"""
        flow_data = []
        
        try:
            url = f"https://www.barchart.com/stocks/quotes/{symbol}/options"
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for volume data in options tables
                tables = soup.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows[1:]:  # Skip header
                        cells = row.find_all('td')
                        if len(cells) >= 6:
                            try:
                                volume = self._parse_volume(cells[5].get_text())
                                if volume > 100:  # Only unusual volume
                                    flow_data.append({
                                        'strike': self._parse_number(cells[0].get_text()),
                                        'volume': volume,
                                        'type': 'BLOCK' if volume > 1000 else 'UNUSUAL',
                                        'source': 'Barchart'
                                    })
                            except:
                                continue
        except Exception as e:
            print(f"Barchart flow scraping error: {e}")
        
        return flow_data[:10]  # Top 10
    
    def _scrape_marketwatch_flow(self, symbol):
        """Scrape options flow from MarketWatch"""
        flow_data = []
        
        try:
            url = f"https://www.marketwatch.com/investing/stock/{symbol}/options"
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract volume data from tables
                volume_cells = soup.find_all(text=re.compile(r'\d{3,}'))  # Numbers with 3+ digits
                
                for vol_text in volume_cells:
                    try:
                        volume = int(re.sub(r'[^\d]', '', vol_text))
                        if volume > 50:
                            flow_data.append({
                                'volume': volume,
                                'type': 'ACTIVE',
                                'source': 'MarketWatch'
                            })
                    except:
                        continue
                        
        except Exception as e:
            print(f"MarketWatch flow scraping error: {e}")
        
        return flow_data[:5]  # Top 5

# Initialize the real-time scraper
options_scraper = RealTimeOptionsScraper()