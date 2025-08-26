import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import yfinance as yf
from scipy.stats import norm
import math

class IBKROptionsApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.options_data = []
        self.flow_data = []
        self.greeks_data = {}
        self.error_messages = []
        
    def contractDetails(self, reqId, contractDetails):
        """Handle contract details response"""
        contract = contractDetails.contract
        self.options_data.append({
            'symbol': contract.symbol,
            'strike': contract.strike,
            'expiry': contract.lastTradeDateOrContractMonth,
            'type': contract.right,
            'contract': contract
        })
    
    def tickPrice(self, reqId, tickType, price, attrib):
        """Handle tick price data"""
        # tickType 1=bid, 2=ask, 4=last, 6=high, 7=low, 9=close
        pass
    
    def tickSize(self, reqId, tickType, size):
        """Handle tick size data"""
        # tickType 0=bid_size, 3=ask_size, 5=last_size, 8=volume
        pass
    
    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        """Handle errors"""
        self.error_messages.append(f"Error {errorCode}: {errorString}")

class OptionsEngine:
    def __init__(self):
        self.app = None
        self.risk_free_rate = 0.05  # 5% risk-free rate
        
    async def connect_ibkr(self):
        """Connect to IBKR API"""
        try:
            self.app = IBKROptionsApp()
            self.app.connect("127.0.0.1", 7497, clientId=2)
            await asyncio.sleep(2)
            return True
        except Exception as e:
            print(f"IBKR connection failed: {e}")
            return False
    
    async def disconnect_ibkr(self):
        """Disconnect from IBKR API"""
        if self.app:
            self.app.disconnect()
    
    def analyze_flow_patterns(self, symbol, min_volume=100, min_premium=1000.0):
        """Analyze options flow patterns with real data"""
        try:
            ticker = yf.Ticker(symbol)
            
            if not ticker.options:
                return {'analysis': [], 'total_volume': 0, 'symbol': symbol}
            
            all_analysis = []
            total_volume = 0
            
            # Analyze top 3 expirations
            for exp_date in ticker.options[:3]:
                try:
                    chain = ticker.option_chain(exp_date)
                    calls_df = chain.calls
                    puts_df = chain.puts
                    
                    # Calculate days to expiry
                    exp_dt = datetime.strptime(exp_date, '%Y-%m-%d')
                    dte = (exp_dt.date() - datetime.now().date()).days
                    
                    # Filter for active options
                    active_calls = calls_df[(calls_df['volume'] > min_volume) & (calls_df['bid'] > 0)]
                    active_puts = puts_df[(puts_df['volume'] > min_volume) & (puts_df['bid'] > 0)]
                    
                    call_volume = active_calls['volume'].sum() if not active_calls.empty else 0
                    put_volume = active_puts['volume'].sum() if not active_puts.empty else 0
                    
                    call_premium = (active_calls['volume'] * active_calls['lastPrice']).sum() if not active_calls.empty else 0
                    put_premium = (active_puts['volume'] * active_puts['lastPrice']).sum() if not active_puts.empty else 0
                    
                    total_volume += call_volume + put_volume
                    
                    analysis = {
                        'expiry': exp_date,
                        'dte': dte,
                        'call_volume': int(call_volume),
                        'put_volume': int(put_volume),
                        'call_premium': float(call_premium),
                        'put_premium': float(put_premium),
                        'total_volume': int(call_volume + put_volume),
                        'pc_ratio': float(put_volume / call_volume) if call_volume > 0 else 0
                    }
                    all_analysis.append(analysis)
                    
                except Exception as e:
                    print(f"Error analyzing {exp_date}: {e}")
                    continue
            
            return {
                'analysis': all_analysis,
                'total_volume': int(total_volume),
                'symbol': symbol,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            print(f"Flow analysis error for {symbol}: {e}")
            return {'analysis': [], 'total_volume': 0, 'symbol': symbol}

    async def get_options_flow(self, symbol, min_volume=100, min_premium=1000.0):
        """Get real-time options flow data"""
        return self.analyze_flow_patterns(symbol, min_volume, min_premium)
    
    async def _get_yahoo_options_flow(self, symbol, min_volume, min_premium):
        """Get options flow using Yahoo Finance (fallback)"""
        try:
            ticker = yf.Ticker(symbol)
            options_dates = ticker.options
            
            all_flows = []
            current_time = datetime.now()
            
            for exp_date in options_dates[:2]:  # Limit to first 2 expiration dates to avoid rate limits
                try:
                    calls = ticker.option_chain(exp_date).calls
                    puts = ticker.option_chain(exp_date).puts
                    
                    # Process calls
                    for _, call in calls.iterrows():
                        if call['volume'] >= min_volume and call['lastPrice'] * call['volume'] * 100 >= min_premium:
                            all_flows.append({
                                'timestamp': current_time,
                                'symbol': symbol,
                                'type': 'CALL',
                                'strike': call['strike'],
                                'expiry': exp_date,
                                'bid': call['bid'],
                                'ask': call['ask'],
                                'last': call['lastPrice'],
                                'volume': call['volume'],
                                'open_interest': call['openInterest'],
                                'iv': call['impliedVolatility'],
                                'premium': call['lastPrice'] * call['volume'] * 100,
                                'delta': self._calculate_delta(symbol, call['strike'], exp_date, 'call', call['impliedVolatility']),
                                'avg_volume': call['openInterest'] * 0.1,  # Estimate average volume
                                'change': call['change'],
                                'percent_change': call['percentChange']
                            })
                    
                    # Process puts
                    for _, put in puts.iterrows():
                        if put['volume'] >= min_volume and put['lastPrice'] * put['volume'] * 100 >= min_premium:
                            all_flows.append({
                                'timestamp': current_time,
                                'symbol': symbol,
                                'type': 'PUT',
                                'strike': put['strike'],
                                'expiry': exp_date,
                                'bid': put['bid'],
                                'ask': put['ask'],
                                'last': put['lastPrice'],
                                'volume': put['volume'],
                                'open_interest': put['openInterest'],
                                'iv': put['impliedVolatility'],
                                'premium': put['lastPrice'] * put['volume'] * 100,
                                'delta': self._calculate_delta(symbol, put['strike'], exp_date, 'put', put['impliedVolatility']),
                                'avg_volume': put['openInterest'] * 0.1,  # Estimate average volume
                                'change': put['change'],
                                'percent_change': put['percentChange']
                            })
                            
                except Exception as e:
                    print(f"Error processing {exp_date}: {e}")
                    continue
            
            return pd.DataFrame(all_flows).sort_values('premium', ascending=False)
            
        except Exception as e:
            print(f"CRITICAL ERROR: Unable to fetch real options flow data for {symbol}: {e}")
            print("INSTITUTIONAL TRADING REQUIRES REAL DATA ONLY - NO SYNTHETIC DATA ALLOWED")
            # Return empty DataFrame - institutional trading requires 100% real data
            return pd.DataFrame()
    
    async def get_options_chain(self, symbol):
        """Get complete options chain"""
        try:
            ticker = yf.Ticker(symbol)
            options_dates = ticker.options
            
            all_options = []
            
            for exp_date in options_dates[:3]:  # Limit to first 3 expiration dates to avoid rate limits
                try:
                    chain = ticker.option_chain(exp_date)
                    
                    # Process calls
                    for _, call in chain.calls.iterrows():
                        greeks = self._calculate_greeks(symbol, call['strike'], exp_date, 'call', call['impliedVolatility'])
                        all_options.append({
                            'symbol': symbol,
                            'type': 'CALL',
                            'strike': call['strike'],
                            'expiry': exp_date,
                            'bid': call['bid'],
                            'ask': call['ask'],
                            'last': call['lastPrice'],
                            'volume': call['volume'],
                            'open_interest': call['openInterest'],
                            'iv': call['impliedVolatility'],
                            'delta': greeks['delta'],
                            'gamma': greeks['gamma'],
                            'theta': greeks['theta'],
                            'vega': greeks['vega'],
                            'change': call['change'],
                            'percent_change': call['percentChange']
                        })
                    
                    # Process puts
                    for _, put in chain.puts.iterrows():
                        greeks = self._calculate_greeks(symbol, put['strike'], exp_date, 'put', put['impliedVolatility'])
                        all_options.append({
                            'symbol': symbol,
                            'type': 'PUT',
                            'strike': put['strike'],
                            'expiry': exp_date,
                            'bid': put['bid'],
                            'ask': put['ask'],
                            'last': put['lastPrice'],
                            'volume': put['volume'],
                            'open_interest': put['openInterest'],
                            'iv': put['impliedVolatility'],
                            'delta': greeks['delta'],
                            'gamma': greeks['gamma'],
                            'theta': greeks['theta'],
                            'vega': greeks['vega'],
                            'change': put['change'],
                            'percent_change': put['percentChange']
                        })
                        
                except Exception as e:
                    print(f"Error processing options chain for {exp_date}: {e}")
                    continue
            
            return pd.DataFrame(all_options)
            
        except Exception as e:
            print(f"CRITICAL ERROR: Cannot fetch real options chain for {symbol}: {e}")
            print("INSTITUTIONAL TRADING REQUIRES REAL DATA ONLY - NO SYNTHETIC OPTIONS CHAIN ALLOWED")
            # Return empty DataFrame - institutional trading demands 100% real data
            return pd.DataFrame()
    
    async def get_iv_rank(self, symbol):
        """Calculate implied volatility rank"""
        try:
            ticker = yf.Ticker(symbol)
            # Get historical volatility data
            hist_data = ticker.history(period="252d")  # 1 year of data
            
            if hist_data.empty:
                return 0
            
            # Calculate historical volatility
            returns = hist_data['Close'].pct_change().dropna()
            hist_vol = returns.std() * np.sqrt(252) * 100  # Annualized volatility
            
            # Get current implied volatility from options
            try:
                chain = ticker.option_chain()
                current_iv = chain.calls['impliedVolatility'].mean() * 100
                
                # Calculate IV rank (current IV percentile over past year)
                historical_ivs = [hist_vol]  # Simplified - would need actual IV history
                iv_rank = (sum(1 for iv in historical_ivs if iv < current_iv) / len(historical_ivs)) * 100
                
                return iv_rank
            except:
                return hist_vol
                
        except Exception as e:
            print(f"IV rank calculation error: {e}")
            return 0
    
    async def get_portfolio_greeks(self, symbol):
        """Calculate portfolio Greeks"""
        try:
            # INSTITUTIONAL REQUIREMENT: This function requires real position tracking
            # Without actual positions, we cannot provide meaningful Greeks
            print(f"WARNING: Portfolio Greeks requires real position data for {symbol}")
            return {
                'total_delta': 0.0,
                'total_gamma': 0.0,
                'total_theta': 0.0,
                'total_vega': 0.0,
                'positions': [],
                'status': 'NO_POSITIONS_TRACKED'
            }
        except Exception as e:
            print(f"Portfolio Greeks error: {e}")
            return {}
    
    async def get_flow_heatmap(self, symbol):
        """Get data for options flow heatmap"""
        try:
            # Get options flow data
            flow_data = await self.get_options_flow(symbol, min_volume=1, min_premium=100)
            
            if flow_data.empty:
                return pd.DataFrame()
            
            # Aggregate volume by strike and expiry
            heatmap_data = flow_data.groupby(['strike', 'expiry'])['volume'].sum().reset_index()
            
            return heatmap_data
            
        except Exception as e:
            print(f"Flow heatmap error: {e}")
            return pd.DataFrame()
    
    async def calculate_portfolio_pnl(self, symbol):
        """Calculate portfolio P&L"""
        try:
            # INSTITUTIONAL REQUIREMENT: P&L calculation requires real position tracking
            # Without actual trades, we cannot provide meaningful P&L
            print(f"WARNING: P&L calculation requires real trading positions for {symbol}")
            return {
                'unrealized_pnl': 0.0,
                'daily_pnl': 0.0,
                'total_pnl': 0.0,
                'status': 'NO_TRADES_TRACKED'
            }
        except Exception as e:
            print(f"P&L calculation error: {e}")
            return {'unrealized_pnl': 0.0, 'daily_pnl': 0.0, 'total_pnl': 0.0}
    
    def _calculate_delta(self, symbol, strike, expiry, option_type, iv):
        """Calculate option delta using Black-Scholes"""
        try:
            # Get current stock price
            ticker = yf.Ticker(symbol)
            current_price = ticker.history(period="1d")['Close'].iloc[-1]
            
            # Calculate time to expiry
            expiry_date = datetime.strptime(expiry, '%Y-%m-%d')
            time_to_expiry = (expiry_date - datetime.now()).days / 365.0
            
            if time_to_expiry <= 0:
                return 0
            
            # Black-Scholes delta calculation
            d1 = (np.log(current_price / strike) + (self.risk_free_rate + 0.5 * iv**2) * time_to_expiry) / (iv * np.sqrt(time_to_expiry))
            
            if option_type.lower() == 'call':
                delta = norm.cdf(d1)
            else:  # put
                delta = norm.cdf(d1) - 1
            
            return delta
            
        except Exception as e:
            print(f"Delta calculation error: {e}")
            return 0
    
    def _calculate_greeks(self, symbol, strike, expiry, option_type, iv):
        """Calculate all option Greeks"""
        try:
            # Get current stock price
            ticker = yf.Ticker(symbol)
            current_price = ticker.history(period="1d")['Close'].iloc[-1]
            
            # Calculate time to expiry
            expiry_date = datetime.strptime(expiry, '%Y-%m-%d')
            time_to_expiry = (expiry_date - datetime.now()).days / 365.0
            
            if time_to_expiry <= 0:
                return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}
            
            # Black-Scholes calculations
            d1 = (np.log(current_price / strike) + (self.risk_free_rate + 0.5 * iv**2) * time_to_expiry) / (iv * np.sqrt(time_to_expiry))
            d2 = d1 - iv * np.sqrt(time_to_expiry)
            
            # Delta
            if option_type.lower() == 'call':
                delta = norm.cdf(d1)
            else:  # put
                delta = norm.cdf(d1) - 1
            
            # Gamma
            gamma = norm.pdf(d1) / (current_price * iv * np.sqrt(time_to_expiry))
            
            # Theta
            if option_type.lower() == 'call':
                theta = -(current_price * norm.pdf(d1) * iv) / (2 * np.sqrt(time_to_expiry)) - self.risk_free_rate * strike * np.exp(-self.risk_free_rate * time_to_expiry) * norm.cdf(d2)
            else:  # put
                theta = -(current_price * norm.pdf(d1) * iv) / (2 * np.sqrt(time_to_expiry)) + self.risk_free_rate * strike * np.exp(-self.risk_free_rate * time_to_expiry) * norm.cdf(-d2)
            
            theta = theta / 365  # Convert to daily theta
            
            # Vega
            vega = current_price * norm.pdf(d1) * np.sqrt(time_to_expiry) / 100
            
            return {
                'delta': round(delta, 4),
                'gamma': round(gamma, 6),
                'theta': round(theta, 4),
                'vega': round(vega, 4)
            }
            
        except Exception as e:
            print(f"Greeks calculation error: {e}")
            return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}
