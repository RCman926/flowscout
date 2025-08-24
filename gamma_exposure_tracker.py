"""
GAMMA EXPOSURE TRACKER
Real-time gamma exposure monitoring and max pain calculation
"""

import numpy as np
import pandas as pd
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import yfinance as yf
from scipy.stats import norm
import math


class GammaExposureTracker:
    """Professional gamma exposure and max pain analysis"""
    
    def __init__(self):
        self.cache_duration = 300  # 5 minutes
        self.gamma_cache = {}
        
    async def calculate_gamma_exposure_profile(self, symbol: str) -> Dict:
        """Calculate comprehensive gamma exposure profile"""
        try:
            # Check cache
            cache_key = f"gamma_{symbol}"
            if self._is_cache_valid(cache_key):
                return self.gamma_cache[cache_key]
            
            # Get options chain data
            ticker = yf.Ticker(symbol)
            current_price = await self._get_current_price(symbol)
            
            if current_price is None:
                return self._empty_gamma_profile(symbol)
            
            # Get options data for nearest expiries
            exp_dates = ticker.options
            if not exp_dates:
                return self._empty_gamma_profile(symbol)
            
            gamma_profile = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'current_price': current_price,
                'total_gamma_exposure': 0.0,
                'dealer_gamma_exposure': 0.0,
                'max_pain': current_price,
                'gamma_flip_level': current_price,
                'zero_gamma_level': current_price,
                'expiry_analysis': [],
                'strike_analysis': {},
                'gamma_levels': [],
                'risk_reversal': 0.0,
                'put_call_ratio': 1.0,
                'volatility_impact': 'NEUTRAL'
            }
            
            total_call_gamma = 0.0
            total_put_gamma = 0.0
            total_call_volume = 0.0
            total_put_volume = 0.0
            all_strikes_data = []
            
            # Analyze first 3 expiries
            for i, exp_date in enumerate(exp_dates[:3]):
                try:
                    options_data = ticker.option_chain(exp_date)
                    calls = options_data.calls
                    puts = options_data.puts
                    
                    # Calculate time to expiry
                    exp_datetime = datetime.strptime(exp_date, '%Y-%m-%d')
                    dte = (exp_datetime - datetime.now()).days
                    time_to_expiry = max(1, dte) / 365.0
                    
                    expiry_analysis = await self._analyze_expiry_gamma(
                        calls, puts, current_price, time_to_expiry, exp_date
                    )
                    
                    gamma_profile['expiry_analysis'].append(expiry_analysis)
                    
                    # Accumulate totals
                    total_call_gamma += expiry_analysis['call_gamma_exposure']
                    total_put_gamma += expiry_analysis['put_gamma_exposure']
                    total_call_volume += expiry_analysis['call_volume']
                    total_put_volume += expiry_analysis['put_volume']
                    
                    # Collect strike data
                    all_strikes_data.extend(expiry_analysis['strike_data'])
                    
                except Exception as e:
                    print(f"Error analyzing expiry {exp_date}: {e}")
                    continue
            
            # Calculate aggregate metrics
            gamma_profile['total_gamma_exposure'] = total_call_gamma + total_put_gamma
            gamma_profile['dealer_gamma_exposure'] = -(total_call_gamma - total_put_gamma)  # Market makers are short gamma
            
            # Calculate Put/Call ratio
            if total_call_volume > 0:
                gamma_profile['put_call_ratio'] = total_put_volume / total_call_volume
            
            # Calculate Max Pain
            if all_strikes_data:
                gamma_profile['max_pain'] = self._calculate_max_pain(all_strikes_data)
                gamma_profile['gamma_flip_level'] = self._calculate_gamma_flip_level(all_strikes_data)
                gamma_profile['zero_gamma_level'] = self._calculate_zero_gamma_level(all_strikes_data)
                gamma_profile['gamma_levels'] = self._identify_gamma_levels(all_strikes_data, current_price)
            
            # Risk Reversal (25-delta call IV - 25-delta put IV proxy)
            gamma_profile['risk_reversal'] = self._estimate_risk_reversal(all_strikes_data, current_price)
            
            # Volatility impact assessment
            gamma_profile['volatility_impact'] = self._assess_volatility_impact(gamma_profile)
            
            # Cache result
            self.gamma_cache[cache_key] = gamma_profile
            return gamma_profile
            
        except Exception as e:
            print(f"Error calculating gamma exposure for {symbol}: {e}")
            return self._empty_gamma_profile(symbol)
    
    async def _analyze_expiry_gamma(self, calls: pd.DataFrame, puts: pd.DataFrame, 
                                   current_price: float, time_to_expiry: float, exp_date: str) -> Dict:
        """Analyze gamma exposure for a specific expiry"""
        try:
            call_gamma_exposure = 0.0
            put_gamma_exposure = 0.0
            call_volume = 0.0
            put_volume = 0.0
            strike_data = []
            
            # Risk-free rate (simplified)
            risk_free_rate = 0.05
            
            # Process calls
            for _, call in calls.iterrows():
                try:
                    strike = float(call['strike'])
                    volume = float(call.get('volume', 0) or 0)
                    open_interest = float(call.get('openInterest', 0) or 0)
                    implied_vol = float(call.get('impliedVolatility', 0.25) or 0.25)
                    
                    if volume > 0 and strike > 0 and time_to_expiry > 0:
                        # Calculate gamma using Black-Scholes
                        gamma = self._calculate_black_scholes_gamma(
                            current_price, strike, time_to_expiry, risk_free_rate, implied_vol
                        )
                        
                        # Gamma exposure (volume * gamma * shares per contract)
                        gamma_exposure = volume * gamma * 100 * current_price ** 2
                        call_gamma_exposure += gamma_exposure
                        call_volume += volume
                        
                        strike_data.append({
                            'strike': strike,
                            'type': 'call',
                            'volume': volume,
                            'open_interest': open_interest,
                            'gamma': gamma,
                            'gamma_exposure': gamma_exposure,
                            'implied_vol': implied_vol,
                            'expiry': exp_date
                        })
                        
                except Exception as e:
                    continue
            
            # Process puts
            for _, put in puts.iterrows():
                try:
                    strike = float(put['strike'])
                    volume = float(put.get('volume', 0) or 0)
                    open_interest = float(put.get('openInterest', 0) or 0)
                    implied_vol = float(put.get('impliedVolatility', 0.25) or 0.25)
                    
                    if volume > 0 and strike > 0 and time_to_expiry > 0:
                        # Calculate gamma using Black-Scholes
                        gamma = self._calculate_black_scholes_gamma(
                            current_price, strike, time_to_expiry, risk_free_rate, implied_vol
                        )
                        
                        # Gamma exposure (volume * gamma * shares per contract)  
                        gamma_exposure = volume * gamma * 100 * current_price ** 2
                        put_gamma_exposure += gamma_exposure
                        put_volume += volume
                        
                        strike_data.append({
                            'strike': strike,
                            'type': 'put',
                            'volume': volume,
                            'open_interest': open_interest,
                            'gamma': gamma,
                            'gamma_exposure': gamma_exposure,
                            'implied_vol': implied_vol,
                            'expiry': exp_date
                        })
                        
                except Exception as e:
                    continue
            
            return {
                'expiry': exp_date,
                'days_to_expiry': int(time_to_expiry * 365),
                'call_gamma_exposure': call_gamma_exposure,
                'put_gamma_exposure': put_gamma_exposure,
                'net_gamma_exposure': call_gamma_exposure + put_gamma_exposure,
                'call_volume': call_volume,
                'put_volume': put_volume,
                'strike_data': strike_data
            }
            
        except Exception as e:
            print(f"Error analyzing expiry gamma: {e}")
            return {
                'expiry': exp_date,
                'days_to_expiry': 0,
                'call_gamma_exposure': 0.0,
                'put_gamma_exposure': 0.0,
                'net_gamma_exposure': 0.0,
                'call_volume': 0.0,
                'put_volume': 0.0,
                'strike_data': []
            }
    
    def _calculate_black_scholes_gamma(self, S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate Black-Scholes gamma"""
        try:
            if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
                return 0.0
            
            d1 = (math.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma * math.sqrt(T))
            
            # Gamma formula
            gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))
            
            return gamma if not math.isnan(gamma) else 0.0
            
        except Exception as e:
            return 0.0
    
    def _calculate_max_pain(self, strike_data: List[Dict]) -> float:
        """Calculate max pain level"""
        try:
            if not strike_data:
                return 0.0
            
            # Group by strike
            strikes = {}
            for data in strike_data:
                strike = data['strike']
                if strike not in strikes:
                    strikes[strike] = {'call_oi': 0, 'put_oi': 0}
                
                if data['type'] == 'call':
                    strikes[strike]['call_oi'] += data['open_interest']
                else:
                    strikes[strike]['put_oi'] += data['open_interest']
            
            # Calculate pain for each potential price level
            pain_levels = []
            strike_list = sorted(strikes.keys())
            
            for test_price in strike_list:
                total_pain = 0.0
                
                for strike, oi_data in strikes.items():
                    # Call pain (if stock above strike)
                    if test_price > strike:
                        call_pain = (test_price - strike) * oi_data['call_oi']
                        total_pain += call_pain
                    
                    # Put pain (if stock below strike)
                    if test_price < strike:
                        put_pain = (strike - test_price) * oi_data['put_oi']
                        total_pain += put_pain
                
                pain_levels.append((test_price, total_pain))
            
            # Find strike with minimum pain
            if pain_levels:
                max_pain_level = min(pain_levels, key=lambda x: x[1])[0]
                return max_pain_level
            
            return 0.0
            
        except Exception as e:
            print(f"Error calculating max pain: {e}")
            return 0.0
    
    def _calculate_gamma_flip_level(self, strike_data: List[Dict]) -> float:
        """Calculate gamma flip level (where dealer gamma goes from negative to positive)"""
        try:
            if not strike_data:
                return 0.0
            
            # Group by strike and calculate net gamma
            strike_gamma = {}
            for data in strike_data:
                strike = data['strike']
                if strike not in strike_gamma:
                    strike_gamma[strike] = 0.0
                
                # Market makers are typically short options (negative gamma)
                # Call buying creates negative dealer gamma, put buying creates positive dealer gamma
                if data['type'] == 'call':
                    strike_gamma[strike] -= data['gamma_exposure']  # Dealer short calls
                else:
                    strike_gamma[strike] += data['gamma_exposure']  # Dealer short puts
            
            # Find where net gamma crosses zero
            sorted_strikes = sorted(strike_gamma.items())
            
            for i in range(len(sorted_strikes) - 1):
                current_strike, current_gamma = sorted_strikes[i]
                next_strike, next_gamma = sorted_strikes[i + 1]
                
                # Check for sign change
                if current_gamma <= 0 and next_gamma > 0:
                    # Linear interpolation to find exact flip level
                    if next_gamma != current_gamma:
                        flip_level = current_strike + (next_strike - current_strike) * (0 - current_gamma) / (next_gamma - current_gamma)
                        return flip_level
            
            # If no flip found, return middle of range
            if sorted_strikes:
                return (sorted_strikes[0][0] + sorted_strikes[-1][0]) / 2
            
            return 0.0
            
        except Exception as e:
            return 0.0
    
    def _calculate_zero_gamma_level(self, strike_data: List[Dict]) -> float:
        """Calculate zero gamma level"""
        try:
            # Simplified calculation - weighted average of strikes by gamma exposure
            total_weighted_strike = 0.0
            total_gamma_exposure = 0.0
            
            for data in strike_data:
                gamma_exposure = abs(data['gamma_exposure'])
                total_weighted_strike += data['strike'] * gamma_exposure
                total_gamma_exposure += gamma_exposure
            
            if total_gamma_exposure > 0:
                return total_weighted_strike / total_gamma_exposure
            
            return 0.0
            
        except Exception as e:
            return 0.0
    
    def _identify_gamma_levels(self, strike_data: List[Dict], current_price: float) -> List[Dict]:
        """Identify key gamma support/resistance levels"""
        try:
            # Group gamma exposure by strike
            strike_gamma = {}
            for data in strike_data:
                strike = data['strike']
                if strike not in strike_gamma:
                    strike_gamma[strike] = 0.0
                strike_gamma[strike] += abs(data['gamma_exposure'])
            
            # Sort by gamma exposure
            sorted_strikes = sorted(strike_gamma.items(), key=lambda x: x[1], reverse=True)
            
            # Identify top gamma levels
            gamma_levels = []
            for strike, gamma_exposure in sorted_strikes[:10]:  # Top 10 levels
                distance_pct = ((strike - current_price) / current_price) * 100
                
                level_type = 'RESISTANCE' if strike > current_price else 'SUPPORT'
                strength = 'HIGH' if gamma_exposure > np.mean([x[1] for x in sorted_strikes]) else 'MEDIUM'
                
                gamma_levels.append({
                    'strike': round(strike, 2),
                    'gamma_exposure': round(gamma_exposure, 0),
                    'distance_percent': round(distance_pct, 1),
                    'level_type': level_type,
                    'strength': strength
                })
            
            return gamma_levels
            
        except Exception as e:
            return []
    
    def _estimate_risk_reversal(self, strike_data: List[Dict], current_price: float) -> float:
        """Estimate 25-delta risk reversal"""
        try:
            # Find approximate 25-delta strikes (simplified)
            call_25_strike = current_price * 1.1  # Rough approximation
            put_25_strike = current_price * 0.9   # Rough approximation
            
            call_iv = 0.25  # Default
            put_iv = 0.25   # Default
            
            # Find closest strikes and their IVs
            for data in strike_data:
                if data['type'] == 'call' and abs(data['strike'] - call_25_strike) < abs(call_25_strike - current_price) * 0.1:
                    call_iv = data['implied_vol']
                elif data['type'] == 'put' and abs(data['strike'] - put_25_strike) < abs(put_25_strike - current_price) * 0.1:
                    put_iv = data['implied_vol']
            
            # Risk reversal = Call IV - Put IV
            return call_iv - put_iv
            
        except Exception as e:
            return 0.0
    
    def _assess_volatility_impact(self, gamma_profile: Dict) -> str:
        """Assess gamma impact on volatility"""
        try:
            dealer_gamma = gamma_profile['dealer_gamma_exposure']
            current_price = gamma_profile['current_price']
            
            # Normalize gamma exposure
            normalized_gamma = dealer_gamma / (current_price ** 2) if current_price > 0 else 0.0
            
            if normalized_gamma > 0.001:
                return 'VOLATILITY_SUPPRESSING'  # Positive dealer gamma suppresses volatility
            elif normalized_gamma < -0.001:
                return 'VOLATILITY_ENHANCING'   # Negative dealer gamma enhances volatility
            else:
                return 'NEUTRAL'
                
        except Exception as e:
            return 'NEUTRAL'
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current stock price"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d", interval="1m")
            if not hist.empty:
                return float(hist['Close'].iloc[-1])
            return None
        except Exception as e:
            return None
    
    def _empty_gamma_profile(self, symbol: str) -> Dict:
        """Return empty gamma profile"""
        return {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'current_price': 0.0,
            'total_gamma_exposure': 0.0,
            'dealer_gamma_exposure': 0.0,
            'max_pain': 0.0,
            'gamma_flip_level': 0.0,
            'zero_gamma_level': 0.0,
            'expiry_analysis': [],
            'strike_analysis': {},
            'gamma_levels': [],
            'risk_reversal': 0.0,
            'put_call_ratio': 1.0,
            'volatility_impact': 'NEUTRAL'
        }
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.gamma_cache:
            return False
        
        cached_time = datetime.fromisoformat(self.gamma_cache[cache_key]['timestamp'])
        return (datetime.now() - cached_time).seconds < self.cache_duration


# Global gamma exposure tracker instance
gamma_tracker = GammaExposureTracker()