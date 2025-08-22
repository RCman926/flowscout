import asyncio
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract

class MarketDataApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.price_data = {}
        self.historical_data = []
        self.error_messages = []
        
    def tickPrice(self, reqId, tickType, price, attrib):
        """Handle real-time price updates"""
        if tickType == 4:  # Last price
            self.price_data[reqId] = price
            
    def historicalData(self, reqId, bar):
        """Handle historical data"""
        self.historical_data.append({
            'date': bar.date,
            'open': bar.open,
            'high': bar.high,
            'low': bar.low,
            'close': bar.close,
            'volume': bar.volume
        })
        
    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        """Handle errors"""
        self.error_messages.append(f"Error {errorCode}: {errorString}")

class MarketDataManager:
    def __init__(self):
        self.app = None
        self.cache = {}
        self.cache_expiry = {}
        self.cache_duration = 30  # Cache duration in seconds
        
    async def connect_ibkr(self):
        """Connect to IBKR API"""
        try:
            self.app = MarketDataApp()
            self.app.connect("127.0.0.1", 7497, clientId=3)
            await asyncio.sleep(2)
            return True
        except Exception as e:
            print(f"IBKR connection failed: {e}")
            return False
            
    async def disconnect_ibkr(self):
        """Disconnect from IBKR"""
        if self.app:
            self.app.disconnect()
            
    def _is_cache_valid(self, key):
        """Check if cached data is still valid"""
        return (key in self.cache and 
                key in self.cache_expiry and 
                datetime.now() < self.cache_expiry[key])
                
    def _update_cache(self, key, data):
        """Update cache with new data"""
        self.cache[key] = data
        self.cache_expiry[key] = datetime.now() + timedelta(seconds=self.cache_duration)
        
    async def get_current_price(self, symbol):
        """Get current stock price"""
        cache_key = f"{symbol}_price"
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
            
        try:
            # Try IBKR first
            if await self.connect_ibkr():
                contract = Contract()
                contract.symbol = symbol
                contract.secType = "STK"
                contract.exchange = "SMART"
                contract.currency = "USD"
                
                self.app.reqMktData(1, contract, "", False, False, [])
                await asyncio.sleep(3)
                
                if 1 in self.app.price_data:
                    price = self.app.price_data[1]
                    await self.disconnect_ibkr()
                    self._update_cache(cache_key, price)
                    return price
                    
                await self.disconnect_ibkr()
            
            # Fallback to Yahoo Finance
            return await self._get_yahoo_price(symbol)
            
        except Exception as e:
            print(f"Current price fetch error: {e}")
            return await self._get_yahoo_price(symbol)
            
    async def _get_yahoo_price(self, symbol):
        """Get price from Yahoo Finance"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d", interval="1m")
            
            if not data.empty:
                price = data['Close'].iloc[-1]
                cache_key = f"{symbol}_price"
                self._update_cache(cache_key, price)
                return price
            return 0
            
        except Exception as e:
            print(f"Yahoo price fetch error: {e}")
            return 0
            
    async def get_price_change(self, symbol):
        """Get price change from previous close"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="2d")
            
            if len(data) >= 2:
                current_price = data['Close'].iloc[-1]
                previous_close = data['Close'].iloc[-2]
                return current_price - previous_close
            return 0
            
        except Exception as e:
            print(f"Price change calculation error: {e}")
            return 0
            
    async def get_historical_data(self, symbol, period="60d", interval="1d"):
        """Get historical market data"""
        cache_key = f"{symbol}_hist_{period}_{interval}"
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
            
        try:
            # Try IBKR first
            if await self.connect_ibkr():
                contract = Contract()
                contract.symbol = symbol
                contract.secType = "STK"
                contract.exchange = "SMART"
                contract.currency = "USD"
                
                # Request historical data
                self.app.reqHistoricalData(
                    2, contract, "", "60 D", "1 day", "TRADES", 1, 1, False, []
                )
                await asyncio.sleep(5)
                
                if self.app.historical_data:
                    df = pd.DataFrame(self.app.historical_data)
                    df['Date'] = pd.to_datetime(df['date'])
                    df.set_index('Date', inplace=True)
                    df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                    
                    await self.disconnect_ibkr()
                    self._update_cache(cache_key, df)
                    return df
                    
                await self.disconnect_ibkr()
            
            # Fallback to Yahoo Finance
            return await self._get_yahoo_historical(symbol, period, interval)
            
        except Exception as e:
            print(f"Historical data fetch error: {e}")
            return await self._get_yahoo_historical(symbol, period, interval)
            
    async def _get_yahoo_historical(self, symbol, period, interval):
        """Get historical data from Yahoo Finance"""
        try:
            loop = asyncio.get_event_loop()
            ticker = yf.Ticker(symbol)
            data = await loop.run_in_executor(None, lambda: ticker.history(period=period, interval=interval))
            
            if not data.empty:
                cache_key = f"{symbol}_hist_{period}_{interval}"
                self._update_cache(cache_key, data)
                return data
                
            return pd.DataFrame()
            
        except Exception as e:
            print(f"Yahoo historical data error: {e}")
            return pd.DataFrame()
            
    async def get_vix(self):
        """Get VIX (volatility index)"""
        cache_key = "VIX_price"
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
            
        try:
            ticker = yf.Ticker("^VIX")
            data = ticker.history(period="1d")
            
            if not data.empty:
                vix_value = data['Close'].iloc[-1]
                self._update_cache(cache_key, vix_value)
                return vix_value
            return 0
            
        except Exception as e:
            print(f"VIX fetch error: {e}")
            return 0
            
    async def get_market_stats(self, symbol):
        """Get comprehensive market statistics"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            stats = {
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('forwardPE', 0),
                'beta': info.get('beta', 0),
                'dividend_yield': info.get('dividendYield', 0),
                'volume': info.get('averageVolume', 0),
                'high_52w': info.get('fiftyTwoWeekHigh', 0),
                'low_52w': info.get('fiftyTwoWeekLow', 0)
            }
            
            return stats
            
        except Exception as e:
            print(f"Market stats error: {e}")
            return {}
            
    async def get_premarket_data(self, symbol):
        """Get pre-market trading data"""
        try:
            ticker = yf.Ticker(symbol)
            # Get pre-market data (if available)
            premarket = ticker.history(period="1d", interval="1m", prepost=True)
            
            if not premarket.empty:
                # Filter for pre-market hours (4:00 AM - 9:30 AM EST)
                market_open = premarket.index.normalize() + pd.Timedelta(hours=9, minutes=30)
                premarket_data = premarket[premarket.index < market_open]
                
                if not premarket_data.empty:
                    return {
                        'premarket_price': premarket_data['Close'].iloc[-1],
                        'premarket_change': premarket_data['Close'].iloc[-1] - premarket_data['Close'].iloc[0],
                        'premarket_volume': premarket_data['Volume'].sum()
                    }
            
            return {'premarket_price': 0, 'premarket_change': 0, 'premarket_volume': 0}
            
        except Exception as e:
            print(f"Pre-market data error: {e}")
            return {'premarket_price': 0, 'premarket_change': 0, 'premarket_volume': 0}
            
    async def get_sector_performance(self):
        """Get sector performance data"""
        try:
            sectors = {
                'Technology': 'XLK',
                'Healthcare': 'XLV',
                'Financial': 'XLF',
                'Energy': 'XLE',
                'Consumer Discretionary': 'XLY',
                'Consumer Staples': 'XLP',
                'Industrial': 'XLI',
                'Materials': 'XLB',
                'Real Estate': 'XLRE',
                'Utilities': 'XLU',
                'Communication': 'XLC'
            }
            
            sector_data = []
            
            for sector_name, etf_symbol in sectors.items():
                try:
                    ticker = yf.Ticker(etf_symbol)
                    data = ticker.history(period="2d")
                    
                    if len(data) >= 2:
                        current_price = data['Close'].iloc[-1]
                        previous_close = data['Close'].iloc[-2]
                        change_pct = ((current_price - previous_close) / previous_close) * 100
                        
                        sector_data.append({
                            'sector': sector_name,
                            'etf': etf_symbol,
                            'price': current_price,
                            'change_pct': change_pct
                        })
                        
                except Exception as e:
                    print(f"Error fetching {sector_name} data: {e}")
                    continue
            
            return pd.DataFrame(sector_data)
            
        except Exception as e:
            print(f"Sector performance error: {e}")
            return pd.DataFrame()
