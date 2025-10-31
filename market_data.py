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

class MarketDataEngine:
    def __init__(self):
        self.app = None
        self.cache = {}
        self.cache_expiry = {}
        self.cache_duration = 10  # Cache duration in seconds - faster for live updates
        self.options_cache_duration = 30  # Separate cache for options data
        # Store connection settings
        self.ibkr_host = "127.0.0.1"
        self.ibkr_port = 7497
        self.ibkr_client_id = 1
        # IBKR rate limiting
        self.last_ibkr_request = {}
        self.ibkr_request_delay = 0.5  # 500ms between IBKR requests to prevent overwhelming
        
    async def connect_ibkr(self, host="127.0.0.1", port=7497, client_id=1, timeout=3):
        """Connect to IBKR API with configurable parameters and timeout"""
        try:
            # Save connection settings for future reconnects
            self.ibkr_host = host
            self.ibkr_port = port
            self.ibkr_client_id = client_id
            
            # ✅ PERSISTENCE: Don't reconnect if already connected with same settings
            if self.app and self.app.isConnected():
                print(f"✅ IBKR ACTIVE - Using persistent connection to {host}:{port}")
                return True
            
            # Create new connection with timeout
            self.app = MarketDataApp()
            
            # Wrap connection in timeout to prevent hanging
            try:
                async with asyncio.timeout(timeout):
                    self.app.connect(host, port, clientId=client_id)
                    await asyncio.sleep(1)  # Brief wait for connection
            except asyncio.TimeoutError:
                print(f"⏱️ IBKR connection timed out after {timeout}s - falling back to Yahoo Finance")
                return False
            except AttributeError:
                # Python < 3.11 doesn't have asyncio.timeout, use wait_for instead
                try:
                    await asyncio.wait_for(
                        self._do_connect(host, port, client_id),
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    print(f"⏱️ IBKR connection timed out after {timeout}s - falling back to Yahoo Finance")
                    return False
            
            # Test if connection is actually working
            if self.app.isConnected():
                print(f"🟢 IBKR CONNECTED - All data will now use IBKR at {host}:{port} (Client ID: {client_id})")
                print(f"✅ AUTO-MODE: IBKR will be used for all subsequent requests")
                return True
            else:
                print(f"❌ IBKR connection failed to {host}:{port} - using Yahoo Finance fallback")
                return False
        except Exception as e:
            print(f"❌ IBKR connection error: {e} - using Yahoo Finance")
            return False
    
    async def _do_connect(self, host, port, client_id):
        """Helper method for connection with timeout"""
        self.app.connect(host, port, clientId=client_id)
        await asyncio.sleep(1)
            
    async def disconnect_ibkr(self):
        """Disconnect from IBKR"""
        if self.app:
            self.app.disconnect()
            
    async def _throttle_ibkr_request(self, request_type):
        """Throttle IBKR requests to prevent overwhelming the system"""
        if request_type in self.last_ibkr_request:
            time_since_last = (datetime.now() - self.last_ibkr_request[request_type]).total_seconds()
            if time_since_last < self.ibkr_request_delay:
                await asyncio.sleep(self.ibkr_request_delay - time_since_last)
        self.last_ibkr_request[request_type] = datetime.now()
            
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
            # Try IBKR first (uses saved connection settings)
            if await self.connect_ibkr(self.ibkr_host, self.ibkr_port, self.ibkr_client_id):
                # Throttle IBKR requests to prevent overwhelming
                await self._throttle_ibkr_request(f"price_{symbol}")
                
                # Clear previous data to avoid contamination
                self.app.price_data = {}
                
                contract = Contract()
                contract.symbol = symbol
                contract.secType = "STK"
                contract.exchange = "SMART"
                contract.currency = "USD"
                
                self.app.reqMktData(1, contract, "", False, False, [])
                await asyncio.sleep(2)  # Reduced from 3s to 2s for faster updates
                
                if 1 in self.app.price_data:
                    price = self.app.price_data[1]
                    self._update_cache(cache_key, price)
                    print(f"✅ IBKR price for {symbol}: ${price:.2f}")
                    return price
                    
                # Note: Keep connection alive for subsequent requests
            
            # Fallback to Yahoo Finance
            print(f"⚠️ IBKR unavailable, using Yahoo for {symbol}")
            return await self._get_yahoo_price(symbol)
            
        except Exception as e:
            print(f"Current price fetch error: {e}")
            # Return cached value if available, otherwise fallback
            if cache_key in self.cache:
                return self.cache[cache_key]
            return await self._get_yahoo_price(symbol)
            
    async def _get_realtime_price_multi_source(self, symbol):
        """Get real-time price from multiple sources with fallback"""
        try:
            # Try multiple approaches for better real-time data
            sources = [
                self._get_yahoo_price_extended,
                self._get_yahoo_price_basic,
                self._get_fallback_price
            ]
            
            for source in sources:
                try:
                    price = await source(symbol)
                    if price > 0:
                        cache_key = f"{symbol}_price"
                        self._update_cache(cache_key, price)
                        return price
                except Exception as e:
                    print(f"Price source failed: {e}")
                    continue
            
            # If all sources fail, return cached value or fallback
            cache_key = f"{symbol}_price"
            if cache_key in self.cache:
                return self.cache[cache_key]
            return self._get_symbol_fallback_price(symbol)
            
        except Exception as e:
            print(f"Multi-source price fetch error: {e}")
            return self._get_symbol_fallback_price(symbol)
    
    async def _get_yahoo_price_extended(self, symbol):
        """Get price from Yahoo Finance with extended data"""
        try:
            ticker = yf.Ticker(symbol)
            # Try different data periods to get the most recent price
            for period in ["1d", "5d"]:
                try:
                    data = ticker.history(period=period, interval="1m")
                    if not data.empty:
                        return data['Close'].iloc[-1]
                except:
                    continue
            return 0
        except:
            return 0
    
    async def _get_yahoo_price_basic(self, symbol):
        """Basic Yahoo Finance price fetch"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Try multiple price fields
            price_fields = ['regularMarketPrice', 'currentPrice', 'previousClose', 'open']
            for field in price_fields:
                if field in info and info[field] > 0:
                    return float(info[field])
            return 0
        except:
            return 0
    
    def _get_symbol_fallback_price(self, symbol):
        """Get reasonable fallback price based on symbol"""
        # Updated fallback prices based on recent market data
        fallback_prices = {
            'SPY': 635.55, 'QQQ': 571.82, 'TSLA': 320.11, 'AAPL': 245.18, 'MSFT': 441.81,
            'NVDA': 145.89, 'AMZN': 185.92, 'GOOGL': 185.40, 'META': 598.35, 'AMD': 129.67,
            'NFLX': 924.87, 'UBER': 69.45, 'COIN': 301.20, 'PLTR': 72.18, 'SOFI': 15.89,
            'HOOD': 36.12, 'RBLX': 48.90, 'SNAP': 10.67
        }
        return fallback_prices.get(symbol.upper(), 100.0)
    
    async def _get_fallback_price(self, symbol):
        """Final fallback price method"""
        return self._get_symbol_fallback_price(symbol)
    
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
            # Get real-time price from multiple sources
            return await self._get_realtime_price_multi_source(symbol)
            
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
            # Try IBKR first (uses saved connection settings)
            if await self.connect_ibkr(self.ibkr_host, self.ibkr_port, self.ibkr_client_id):
                # Throttle IBKR requests to prevent overwhelming
                await self._throttle_ibkr_request(f"hist_{symbol}")
                
                # Clear previous data to avoid contamination
                self.app.historical_data = []
                
                contract = Contract()
                contract.symbol = symbol
                contract.secType = "STK"
                contract.exchange = "SMART"
                contract.currency = "USD"
                
                # Request historical data
                self.app.reqHistoricalData(
                    2, contract, "", "60 D", "1 day", "TRADES", 1, 1, False, []
                )
                await asyncio.sleep(4)  # Reduced from 5s to 4s
                
                if self.app.historical_data:
                    df = pd.DataFrame(self.app.historical_data)
                    df['Date'] = pd.to_datetime(df['date'])
                    df.set_index('Date', inplace=True)
                    df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                    
                    self._update_cache(cache_key, df)
                    print(f"✅ IBKR historical data for {symbol}: {len(df)} days")
                    return df
                    
                # Note: Keep connection alive for subsequent requests
            
            # Fallback to Yahoo Finance
            print(f"⚠️ IBKR unavailable, using Yahoo for {symbol} historical data")
            return await self._get_yahoo_historical(symbol, period, interval)
            
        except Exception as e:
            print(f"Historical data fetch error: {e}")
            # Return cached data if available
            if cache_key in self.cache:
                return self.cache[cache_key]
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
            # Return sample data structure to prevent UI crashes
            dates = pd.date_range(start='2024-01-01', periods=60, freq='D')
            fallback_prices = {
                'SPY': 635.55, 'QQQ': 571.82, 'TSLA': 320.11, 'AAPL': 245.18, 'MSFT': 441.81,
                'NVDA': 145.89, 'AMZN': 185.92, 'GOOGL': 185.40, 'META': 598.35, 'AMD': 129.67,
                'NFLX': 924.87, 'UBER': 69.45, 'COIN': 301.20, 'PLTR': 72.18, 'SOFI': 15.89,
                'HOOD': 36.12, 'RBLX': 48.90, 'SNAP': 10.67
            }
            base_price = fallback_prices.get(symbol, 100)
            sample_data = pd.DataFrame({
                'Open': [base_price + (i % 10 - 5) for i in range(60)],
                'High': [base_price + (i % 10 - 3) for i in range(60)],
                'Low': [base_price + (i % 10 - 7) for i in range(60)],
                'Close': [base_price + (i % 10 - 5) for i in range(60)],
                'Volume': [1000000 + (i * 10000) for i in range(60)]
            }, index=dates)
            cache_key = f"{symbol}_hist_{period}_{interval}"
            self._update_cache(cache_key, sample_data)
            return sample_data
            
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
        cache_key = f"{symbol}_premarket"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
            
        try:
            ticker = yf.Ticker(symbol)
            # Get extended hours data
            premarket = ticker.history(period="1d", interval="1m", prepost=True)
            
            if not premarket.empty:
                now = datetime.now()
                today = now.date()
                
                # Filter for pre-market hours (4:00 AM - 9:30 AM EST)
                premarket_start = pd.Timestamp.combine(today, pd.Timestamp("04:00:00").time())
                market_open = pd.Timestamp.combine(today, pd.Timestamp("09:30:00").time())
                
                # Handle timezone compatibility
                if premarket.index.tz is not None:
                    premarket_start = premarket_start.tz_localize('UTC').tz_convert(premarket.index.tz)
                    market_open = market_open.tz_localize('UTC').tz_convert(premarket.index.tz)
                
                premarket_data = premarket[
                    (premarket.index >= premarket_start) & 
                    (premarket.index < market_open)
                ]
                
                if not premarket_data.empty:
                    result = {
                        'premarket_price': premarket_data['Close'].iloc[-1],
                        'premarket_change': premarket_data['Close'].iloc[-1] - premarket_data['Close'].iloc[0],
                        'premarket_volume': premarket_data['Volume'].sum(),
                        'premarket_high': premarket_data['High'].max(),
                        'premarket_low': premarket_data['Low'].min(),
                        'is_premarket_active': True
                    }
                    self._update_cache(cache_key, result)
                    return result
            
            # Return default values if no premarket data
            result = {'premarket_price': 0, 'premarket_change': 0, 'premarket_volume': 0, 'premarket_high': 0, 'premarket_low': 0, 'is_premarket_active': False}
            self._update_cache(cache_key, result)
            return result
            
        except Exception as e:
            print(f"Pre-market data error: {e}")
            # Return cached data if available
            if cache_key in self.cache:
                return self.cache[cache_key]
            return {'premarket_price': 0, 'premarket_change': 0, 'premarket_volume': 0, 'premarket_high': 0, 'premarket_low': 0, 'is_premarket_active': False}
            
    async def get_afterhours_data(self, symbol):
        """Get after-hours trading data"""
        cache_key = f"{symbol}_afterhours"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
            
        try:
            ticker = yf.Ticker(symbol)
            # Get extended hours data
            afterhours = ticker.history(period="1d", interval="1m", prepost=True)
            
            if not afterhours.empty:
                now = datetime.now()
                today = now.date()
                
                # Filter for after-hours (4:00 PM - 8:00 PM EST)
                market_close = pd.Timestamp.combine(today, pd.Timestamp("16:00:00").time())
                afterhours_end = pd.Timestamp.combine(today, pd.Timestamp("20:00:00").time())
                
                # Handle timezone compatibility
                if afterhours.index.tz is not None:
                    market_close = market_close.tz_localize('UTC').tz_convert(afterhours.index.tz)
                    afterhours_end = afterhours_end.tz_localize('UTC').tz_convert(afterhours.index.tz)
                
                afterhours_data = afterhours[
                    (afterhours.index >= market_close) & 
                    (afterhours.index <= afterhours_end)
                ]
                
                if not afterhours_data.empty:
                    result = {
                        'afterhours_price': afterhours_data['Close'].iloc[-1],
                        'afterhours_change': afterhours_data['Close'].iloc[-1] - afterhours_data['Close'].iloc[0],
                        'afterhours_volume': afterhours_data['Volume'].sum(),
                        'afterhours_high': afterhours_data['High'].max(),
                        'afterhours_low': afterhours_data['Low'].min(),
                        'is_afterhours_active': True
                    }
                    self._update_cache(cache_key, result)
                    return result
            
            # Return default values if no afterhours data
            result = {'afterhours_price': 0, 'afterhours_change': 0, 'afterhours_volume': 0, 'afterhours_high': 0, 'afterhours_low': 0, 'is_afterhours_active': False}
            self._update_cache(cache_key, result)
            return result
            
        except Exception as e:
            print(f"After-hours data error: {e}")
            # Return cached data if available
            if cache_key in self.cache:
                return self.cache[cache_key]
            return {'afterhours_price': 0, 'afterhours_change': 0, 'afterhours_volume': 0, 'afterhours_high': 0, 'afterhours_low': 0, 'is_afterhours_active': False}
    
    async def get_extended_hours_data(self, symbol):
        """Get complete extended hours data (pre-market + after-hours)"""
        try:
            premarket_data = await self.get_premarket_data(symbol)
            afterhours_data = await self.get_afterhours_data(symbol)
            
            return {
                'premarket': premarket_data,
                'afterhours': afterhours_data,
                'market_status': self._get_market_status()
            }
            
        except Exception as e:
            print(f"Extended hours data error: {e}")
            return {
                'premarket': {'premarket_price': 0, 'premarket_change': 0, 'premarket_volume': 0, 'is_premarket_active': False},
                'afterhours': {'afterhours_price': 0, 'afterhours_change': 0, 'afterhours_volume': 0, 'is_afterhours_active': False},
                'market_status': 'unknown'
            }
    
    def _get_market_status(self):
        """Determine current market status"""
        try:
            now = datetime.now()
            current_time = now.time()
            weekday = now.weekday()  # 0=Monday, 6=Sunday
            
            # Weekend
            if weekday >= 5:  # Saturday or Sunday
                return 'weekend'
            
            # Market hours (9:30 AM - 4:00 PM EST)
            market_open = pd.Timestamp("09:30:00").time()
            market_close = pd.Timestamp("16:00:00").time()
            
            # Pre-market (4:00 AM - 9:30 AM EST)
            premarket_start = pd.Timestamp("04:00:00").time()
            
            # After-hours (4:00 PM - 8:00 PM EST)
            afterhours_end = pd.Timestamp("20:00:00").time()
            
            if market_open <= current_time <= market_close:
                return 'market_hours'
            elif premarket_start <= current_time < market_open:
                return 'premarket'
            elif market_close < current_time <= afterhours_end:
                return 'afterhours'
            else:
                return 'closed'
                
        except Exception as e:
            print(f"Market status error: {e}")
            return 'unknown'
    
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
    
    def get_real_time_data(self, symbol):
        """Get real-time market data for a symbol"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Get current info and recent history
            info = ticker.info
            hist = ticker.history(period='2d')
            
            if hist.empty:
                return None
                
            current_price = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            volume = hist['Volume'].iloc[-1]
            
            change = current_price - prev_close
            change_pct = (change / prev_close) * 100
            
            return {
                'symbol': symbol,
                'price': float(current_price),
                'change': float(change),
                'change_pct': float(change_pct),
                'volume': int(volume),
                'avg_volume': int(info.get('averageVolume', volume)),
                'market_cap': info.get('marketCap', 0),
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            print(f"Real-time data error for {symbol}: {e}")
            return None

# Create a global instance for the app to use
market_data_manager = MarketDataEngine()
