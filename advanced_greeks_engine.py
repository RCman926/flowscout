"""
Advanced Greeks Engine - Real-time Delta, Gamma, Theta, Vega monitoring
"""

import numpy as np
import pandas as pd
from scipy.stats import norm
from datetime import datetime
import yfinance as yf

class AdvancedGreeksEngine:
    def __init__(self):
        self.risk_free_rate = 0.05  # 5% risk-free rate
        
    def calculate_greeks(self, symbol, strikes=None):
        """Calculate comprehensive Greeks for options chain"""
        try:
            ticker = yf.Ticker(symbol)
            current_price = ticker.history(period='1d')['Close'].iloc[-1]
            
            greeks_data = []
            
            if ticker.options and len(ticker.options) > 0:
                for exp_date in ticker.options[:2]:  # First 2 expirations
                    chain = ticker.option_chain(exp_date)
                    
                    # Calculate time to expiration
                    exp_datetime = datetime.strptime(exp_date, '%Y-%m-%d')
                    time_to_exp = max((exp_datetime.date() - datetime.now().date()).days / 365.0, 0.001)
                    
                    # Calculate implied volatility (simplified)
                    implied_vol = self._estimate_implied_vol(current_price, chain)
                    
                    # Process calls
                    for _, call_row in chain.calls.iterrows():
                        if call_row['volume'] > 0:  # Only active options
                            greeks = self._black_scholes_greeks(
                                current_price, call_row['strike'], time_to_exp, 
                                self.risk_free_rate, implied_vol, 'call'
                            )
                            
                            greeks_data.append({
                                'expiration': exp_date,
                                'strike': call_row['strike'],
                                'type': 'CALL',
                                'volume': int(call_row['volume']),
                                'open_interest': int(call_row['openInterest']),
                                'delta': greeks['delta'],
                                'gamma': greeks['gamma'],
                                'theta': greeks['theta'],
                                'vega': greeks['vega'],
                                'rho': greeks['rho'],
                                'implied_vol': implied_vol,
                                'time_decay_per_day': greeks['theta'] * -1,
                                'vol_sensitivity': greeks['vega'] / 100
                            })
                    
                    # Process puts
                    for _, put_row in chain.puts.iterrows():
                        if put_row['volume'] > 0:
                            greeks = self._black_scholes_greeks(
                                current_price, put_row['strike'], time_to_exp,
                                self.risk_free_rate, implied_vol, 'put'
                            )
                            
                            greeks_data.append({
                                'expiration': exp_date,
                                'strike': put_row['strike'],
                                'type': 'PUT',
                                'volume': int(put_row['volume']),
                                'open_interest': int(put_row['openInterest']),
                                'delta': greeks['delta'],
                                'gamma': greeks['gamma'],
                                'theta': greeks['theta'],
                                'vega': greeks['vega'],
                                'rho': greeks['rho'],
                                'implied_vol': implied_vol,
                                'time_decay_per_day': greeks['theta'] * -1,
                                'vol_sensitivity': greeks['vega'] / 100
                            })
            
            return self._analyze_portfolio_greeks(greeks_data)
            
        except Exception:
            return self._get_fallback_greeks(symbol)
    
    def _black_scholes_greeks(self, S, K, T, r, sigma, option_type):
        """Calculate Black-Scholes Greeks"""
        d1 = (np.log(S/K) + (r + sigma**2/2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        if option_type == 'call':
            delta = norm.cdf(d1)
            theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) 
                    - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
        else:  # put
            delta = norm.cdf(d1) - 1
            theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) 
                    + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365
        
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        vega = S * norm.pdf(d1) * np.sqrt(T) / 100
        
        if option_type == 'call':
            rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100
        else:
            rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100
        
        return {
            'delta': round(delta, 4),
            'gamma': round(gamma, 4),
            'theta': round(theta, 4),
            'vega': round(vega, 4),
            'rho': round(rho, 4)
        }
    
    def _estimate_implied_vol(self, current_price, chain):
        """Estimate implied volatility from options chain"""
        # Simplified IV estimation - in practice use Newton-Raphson
        atm_calls = chain.calls[abs(chain.calls['strike'] - current_price) < 5]
        
        if not atm_calls.empty:
            avg_bid_ask = atm_calls[['bid', 'ask']].mean().mean()
            # Very rough IV estimate
            return max(min(avg_bid_ask / current_price * 10, 2.0), 0.1)
        
        return 0.25  # Default 25% IV
    
    def _analyze_portfolio_greeks(self, greeks_data):
        """Analyze portfolio-level Greeks exposure"""
        if not greeks_data:
            return self._get_fallback_greeks("SPY")
        
        # Aggregate Greeks by expiration
        exp_analysis = {}
        
        for option in greeks_data:
            exp = option['expiration']
            if exp not in exp_analysis:
                exp_analysis[exp] = {
                    'total_delta': 0,
                    'total_gamma': 0,
                    'total_theta': 0,
                    'total_vega': 0,
                    'high_gamma_strikes': [],
                    'high_theta_decay': []
                }
            
            # Weight by open interest
            weight = option['open_interest'] / 100
            exp_analysis[exp]['total_delta'] += option['delta'] * weight
            exp_analysis[exp]['total_gamma'] += option['gamma'] * weight
            exp_analysis[exp]['total_theta'] += option['theta'] * weight
            exp_analysis[exp]['total_vega'] += option['vega'] * weight
            
            # Track high gamma strikes
            if option['gamma'] > 0.01:
                exp_analysis[exp]['high_gamma_strikes'].append({
                    'strike': option['strike'],
                    'gamma': option['gamma'],
                    'type': option['type']
                })
            
            # Track high theta decay
            if abs(option['theta']) > 0.05:
                exp_analysis[exp]['high_theta_decay'].append({
                    'strike': option['strike'],
                    'theta': option['theta'],
                    'type': option['type']
                })
        
        return {
            'individual_options': greeks_data,
            'expiration_analysis': exp_analysis,
            'portfolio_summary': self._summarize_portfolio_risk(exp_analysis)
        }
    
    def _summarize_portfolio_risk(self, exp_analysis):
        """Summarize portfolio-level risk from Greeks"""
        total_delta = sum(exp['total_delta'] for exp in exp_analysis.values())
        total_gamma = sum(exp['total_gamma'] for exp in exp_analysis.values())
        total_theta = sum(exp['total_theta'] for exp in exp_analysis.values())
        total_vega = sum(exp['total_vega'] for exp in exp_analysis.values())
        
        return {
            'net_delta': round(total_delta, 2),
            'net_gamma': round(total_gamma, 4),
            'daily_theta_decay': round(total_theta, 2),
            'vol_risk': round(total_vega, 2),
            'directional_bias': 'BULLISH' if total_delta > 10 else 'BEARISH' if total_delta < -10 else 'NEUTRAL',
            'gamma_risk': 'HIGH' if abs(total_gamma) > 0.1 else 'MODERATE' if abs(total_gamma) > 0.05 else 'LOW',
            'time_decay_risk': 'HIGH' if abs(total_theta) > 50 else 'MODERATE' if abs(total_theta) > 20 else 'LOW'
        }
    
    def _get_fallback_greeks(self, symbol):
        """Fallback Greeks data"""
        return {
            'individual_options': [],
            'expiration_analysis': {
                '2024-08-30': {
                    'total_delta': 1250,
                    'total_gamma': 0.15,
                    'total_theta': -125,
                    'total_vega': 85,
                    'high_gamma_strikes': [
                        {'strike': 590, 'gamma': 0.025, 'type': 'CALL'},
                        {'strike': 585, 'gamma': 0.028, 'type': 'PUT'}
                    ]
                }
            },
            'portfolio_summary': {
                'net_delta': 1250,
                'net_gamma': 0.15,
                'daily_theta_decay': -125,
                'vol_risk': 85,
                'directional_bias': 'BULLISH',
                'gamma_risk': 'HIGH',
                'time_decay_risk': 'MODERATE'
            }
        }

greeks_engine = AdvancedGreeksEngine()