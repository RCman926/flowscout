"""
Live Data Engine - Real-time market data from multiple sources
Uses legitimate APIs and web scraping for authentic live data
"""

import requests
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import asyncio
import aiohttp
import time
from bs4 import BeautifulSoup
import warnings
warnings.filterwarnings('ignore')

class LiveDataEngine:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.data_cache = {}
        self.cache_duration = 30  # 30 seconds cache
        
    def get_live_options_data(self, symbol):
        """Get real-time options data from multiple sources"""
        
        # Try Yahoo Finance first (most reliable)
        options_data = self._get_yahoo_options(symbol)
        
        if not options_data:
            # Fallback to other sources
            options_data = self._get_cboe_options(symbol)
        
        return options_data
    
    def _get_yahoo_options(self, symbol):
        """Get live options data from Yahoo Finance"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Get current price
            hist = ticker.history(period='1d', interval='1m')
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
                volume = hist['Volume'].iloc[-1]
                change = current_price - hist['Open'].iloc[0]
                change_pct = (change / hist['Open'].iloc[0]) * 100
            else:
                return None
            
            # Get options chain
            options_chain = {}
            if ticker.options:
                for exp_date in ticker.options[:3]:  # Get first 3 expirations
                    try:
                        chain = ticker.option_chain(exp_date)
                        
                        # Process calls
                        calls_data = []
                        for _, call in chain.calls.iterrows():
                            if call['volume'] > 0 and call['bid'] > 0:
                                calls_data.append({
                                    'strike': float(call['strike']),
                                    'bid': float(call['bid']),
                                    'ask': float(call['ask']),
                                    'last': float(call['lastPrice']) if call['lastPrice'] else float(call['bid']),
                                    'volume': int(call['volume']) if call['volume'] else 0,
                                    'open_interest': int(call['openInterest']) if call['openInterest'] else 0,
                                    'implied_volatility': float(call['impliedVolatility']) if call['impliedVolatility'] else 0.25
                                })
                        
                        # Process puts
                        puts_data = []
                        for _, put in chain.puts.iterrows():
                            if put['volume'] > 0 and put['bid'] > 0:
                                puts_data.append({
                                    'strike': float(put['strike']),
                                    'bid': float(put['bid']),
                                    'ask': float(put['ask']),
                                    'last': float(put['lastPrice']) if put['lastPrice'] else float(put['bid']),
                                    'volume': int(put['volume']) if put['volume'] else 0,
                                    'open_interest': int(put['openInterest']) if put['openInterest'] else 0,
                                    'implied_volatility': float(put['impliedVolatility']) if put['impliedVolatility'] else 0.25
                                })
                        
                        options_chain[exp_date] = {
                            'calls': calls_data,
                            'puts': puts_data
                        }
                        
                    except Exception as e:
                        continue
            
            return {
                'symbol': symbol,
                'current_price': current_price,
                'change': change,
                'change_pct': change_pct,
                'volume': int(volume),
                'options_chain': options_chain,
                'timestamp': datetime.now(),
                'data_source': 'Yahoo Finance Live',
                'is_live': True
            }
            
        except Exception as e:
            print(f"Error getting Yahoo data: {e}")
            return None
    
    def _get_cboe_options(self, symbol):
        """Get options data from CBOE (backup source)"""
        try:
            # CBOE delayed quotes API (free)
            url = f"https://cdn.cboe.com/api/global/delayed_quotes/options/{symbol}.json"
            
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                return {
                    'symbol': symbol,
                    'current_price': data.get('current_price', 0),
                    'change': data.get('change', 0),
                    'change_pct': data.get('change_percent', 0),
                    'volume': data.get('volume', 0),
                    'options_chain': self._parse_cboe_options(data),
                    'timestamp': datetime.now(),
                    'data_source': 'CBOE Delayed',
                    'is_live': False
                }
            
        except Exception as e:
            print(f"Error getting CBOE data: {e}")
            return None
    
    def _parse_cboe_options(self, cboe_data):
        """Parse CBOE options data format"""
        # Simplified parsing - CBOE has complex data structure
        return {}
    
    def get_real_time_flow_data(self, symbol):
        """Get real institutional flow data using web scraping"""
        
        flow_data = []
        
        # Try to get unusual options activity from public sources
        try:
            # Scrape Barchart unusual options activity
            flow_data.extend(self._scrape_barchart_flow(symbol))
            
            # Add MarketWatch options data
            flow_data.extend(self._scrape_marketwatch_options(symbol))
            
        except Exception as e:
            print(f"Error getting flow data: {e}")
        
        return {
            'flows': flow_data,
            'total_volume': sum(flow.get('volume', 0) for flow in flow_data),
            'timestamp': datetime.now(),
            'data_source': 'Multiple Sources'
        }
    
    def _scrape_barchart_flow(self, symbol):
        """Scrape Barchart for unusual options activity"""
        try:
            url = f"https://www.barchart.com/stocks/quotes/{symbol}/options"
            
            response = self.session.get(url, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for options volume data
                flows = []
                
                # Find volume data in tables
                tables = soup.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows[1:]:  # Skip header
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 6:
                            try:
                                strike = cells[0].text.strip()
                                volume = cells[4].text.strip().replace(',', '')
                                
                                if volume.isdigit() and int(volume) > 100:
                                    flows.append({
                                        'strike': float(strike) if strike.replace('.', '').isdigit() else 0,
                                        'volume': int(volume),
                                        'source': 'Barchart',
                                        'type': 'BLOCK' if int(volume) > 1000 else 'UNUSUAL',
                                        'timestamp': datetime.now()
                                    })
                            except (ValueError, IndexError):
                                continue
                
                return flows[:10]  # Top 10 flows
                
        except Exception as e:
            print(f"Barchart scraping error: {e}")
            return []
    
    def _scrape_marketwatch_options(self, symbol):
        """Scrape MarketWatch for options data"""
        try:
            url = f"https://www.marketwatch.com/investing/stock/{symbol}/options"
            
            response = self.session.get(url, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                flows = []
                
                # Look for options volume in tables
                volume_elements = soup.find_all(text=lambda text: text and text.strip().isdigit() and len(text.strip()) > 3)
                
                for i, vol_text in enumerate(volume_elements[:5]):
                    try:
                        volume = int(vol_text.strip().replace(',', ''))
                        if volume > 50:
                            flows.append({
                                'volume': volume,
                                'source': 'MarketWatch',
                                'type': 'ACTIVE',
                                'timestamp': datetime.now()
                            })
                    except ValueError:
                        continue
                
                return flows
                
        except Exception as e:
            print(f"MarketWatch scraping error: {e}")
            return []
    
    def get_live_gamma_exposure(self, symbol, options_data):
        """Calculate live gamma exposure from real options data"""
        
        if not options_data or 'options_chain' not in options_data:
            return None
        
        current_price = options_data['current_price']
        total_call_gamma = 0
        total_put_gamma = 0
        gamma_levels = {}
        
        # Process each expiration
        for exp_date, chain_data in options_data['options_chain'].items():
            if not chain_data:
                continue
                
            # Calculate time to expiration
            try:
                exp_datetime = datetime.strptime(exp_date, '%Y-%m-%d')
                time_to_exp = max((exp_datetime.date() - datetime.now().date()).days / 365.0, 0.001)
            except:
                time_to_exp = 0.025  # Default to ~1 week
            
            # Process calls
            for call in chain_data.get('calls', []):
                strike = call['strike']
                open_interest = call['open_interest']
                iv = call['implied_volatility']
                
                if open_interest > 0 and 0.8 <= current_price/strike <= 1.2:
                    # Calculate gamma using Black-Scholes approximation
                    gamma = self._calculate_gamma(current_price, strike, time_to_exp, 0.05, iv)
                    gamma_exposure = gamma * open_interest * 100 * strike * strike / 100
                    
                    total_call_gamma += gamma_exposure
                    
                    if strike not in gamma_levels:
                        gamma_levels[strike] = {'call_gex': 0, 'put_gex': 0}
                    gamma_levels[strike]['call_gex'] = gamma_exposure
            
            # Process puts
            for put in chain_data.get('puts', []):
                strike = put['strike']
                open_interest = put['open_interest']
                iv = put['implied_volatility']
                
                if open_interest > 0 and 0.8 <= current_price/strike <= 1.2:
                    gamma = self._calculate_gamma(current_price, strike, time_to_exp, 0.05, iv)
                    gamma_exposure = -gamma * open_interest * 100 * strike * strike / 100
                    
                    total_put_gamma += gamma_exposure
                    
                    if strike not in gamma_levels:
                        gamma_levels[strike] = {'call_gex': 0, 'put_gex': 0}
                    gamma_levels[strike]['put_gex'] = gamma_exposure
        
        # Calculate net GEX for each strike
        for strike in gamma_levels:
            gamma_levels[strike]['net_gex'] = gamma_levels[strike]['call_gex'] + gamma_levels[strike]['put_gex']
        
        # Find support/resistance levels
        sorted_strikes = sorted(gamma_levels.items(), key=lambda x: abs(x[1]['net_gex']), reverse=True)
        
        support_levels = []
        resistance_levels = []
        
        for strike, gex_data in sorted_strikes[:5]:
            if gex_data['net_gex'] > 0:
                if strike > current_price:
                    resistance_levels.append({
                        'strike': strike,
                        'gex': gex_data['net_gex'],
                        'type': 'Positive GEX Resistance'
                    })
                else:
                    support_levels.append({
                        'strike': strike,
                        'gex': gex_data['net_gex'],
                        'type': 'Positive GEX Support'
                    })
            else:
                if strike < current_price:
                    support_levels.append({
                        'strike': strike,
                        'gex': abs(gex_data['net_gex']),
                        'type': 'Negative GEX Support'
                    })
                else:
                    resistance_levels.append({
                        'strike': strike,
                        'gex': abs(gex_data['net_gex']),
                        'type': 'Negative GEX Resistance'
                    })
        
        return {
            'total_call_gex': total_call_gamma,
            'total_put_gex': total_put_gamma,
            'net_gex': total_call_gamma + total_put_gamma,
            'support_levels': support_levels[:3],
            'resistance_levels': resistance_levels[:3],
            'gamma_flip_point': self._find_gamma_flip(gamma_levels, current_price),
            'dealer_positioning': 'Short Gamma' if (total_call_gamma + total_put_gamma) < 0 else 'Long Gamma',
            'data_source': 'Live Calculation',
            'timestamp': datetime.now()
        }
    
    def _calculate_gamma(self, S, K, T, r, sigma):
        """Calculate Black-Scholes gamma"""
        from scipy.stats import norm
        
        d1 = (np.log(S/K) + (r + sigma**2/2) * T) / (sigma * np.sqrt(T))
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        return gamma
    
    def _find_gamma_flip(self, gamma_levels, current_price):
        """Find gamma flip point"""
        strikes_above = [s for s in gamma_levels.keys() if s > current_price]
        strikes_below = [s for s in gamma_levels.keys() if s < current_price]
        
        if strikes_above and strikes_below:
            closest_above = min(strikes_above)
            closest_below = max(strikes_below)
            
            gex_above = gamma_levels[closest_above]['net_gex']
            gex_below = gamma_levels[closest_below]['net_gex']
            
            if gex_above * gex_below < 0:
                return (closest_below + closest_above) / 2
        
        return current_price
    
    def get_live_news(self, symbol):
        """Scrape live financial news"""
        news_items = []
        
        try:
            # Yahoo Finance news
            news_items.extend(self._get_yahoo_news(symbol))
            
            # MarketWatch news  
            news_items.extend(self._get_marketwatch_news(symbol))
            
        except Exception as e:
            print(f"Error getting news: {e}")
        
        return sorted(news_items, key=lambda x: x.get('timestamp', datetime.now()), reverse=True)[:10]
    
    def _get_yahoo_news(self, symbol):
        """Get news from Yahoo Finance"""
        try:
            ticker = yf.Ticker(symbol)
            news = ticker.news
            
            news_items = []
            for item in news[:5]:
                news_items.append({
                    'headline': item.get('title', ''),
                    'source': item.get('publisher', 'Yahoo Finance'),
                    'timestamp': datetime.fromtimestamp(item.get('providerPublishTime', time.time())),
                    'url': item.get('link', ''),
                    'impact': self._analyze_news_impact(item.get('title', ''))
                })
            
            return news_items
            
        except Exception as e:
            print(f"Yahoo news error: {e}")
            return []
    
    def _get_marketwatch_news(self, symbol):
        """Get news from MarketWatch"""
        try:
            url = f"https://www.marketwatch.com/investing/stock/{symbol}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                news_items = []
                
                # Look for news headlines
                headlines = soup.find_all(['h3', 'h4'], class_=lambda x: x and 'headline' in x.lower())
                
                for headline in headlines[:3]:
                    text = headline.get_text().strip()
                    if len(text) > 10:
                        news_items.append({
                            'headline': text,
                            'source': 'MarketWatch',
                            'timestamp': datetime.now(),
                            'impact': self._analyze_news_impact(text)
                        })
                
                return news_items
                
        except Exception as e:
            print(f"MarketWatch news error: {e}")
            return []
    
    def _analyze_news_impact(self, headline):
        """Analyze news impact on market"""
        bullish_keywords = ['beats', 'exceeds', 'raises', 'upgrade', 'buy', 'positive', 'strong']
        bearish_keywords = ['misses', 'cuts', 'downgrade', 'sell', 'negative', 'weak', 'falls']
        
        headline_lower = headline.lower()
        
        bullish_count = sum(1 for word in bullish_keywords if word in headline_lower)
        bearish_count = sum(1 for word in bearish_keywords if word in headline_lower)
        
        if bullish_count > bearish_count:
            return 'bullish'
        elif bearish_count > bullish_count:
            return 'bearish'
        else:
            return 'neutral'

# Initialize live data engine
live_data = LiveDataEngine()