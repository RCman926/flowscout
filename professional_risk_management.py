"""
Professional Risk Management System
Balanced strategies from conservative income to high-risk speculation
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf

class ProfessionalRiskManagement:
    def __init__(self):
        self.risk_levels = {
            'conservative': {
                'allocation': 0.40,
                'win_rate': 0.75,  # Based on historical covered call/cash-secured put backtests
                'avg_return': 0.30,
                'max_loss': 0.15,
                'target_dte': 30,
                'description': 'Steady income generation',
                'data_source': 'Historical backtesting of covered calls/CSPs 2020-2024'
            },
            'moderate': {
                'allocation': 0.35,
                'win_rate': 0.55,
                'avg_return': 0.75,
                'max_loss': 0.35,
                'target_dte': 14,
                'description': 'Balanced growth'
            },
            'aggressive': {
                'allocation': 0.20,
                'win_rate': 0.40,
                'avg_return': 2.00,
                'max_loss': 0.70,
                'target_dte': 7,
                'description': 'High growth potential'
            },
            'speculation': {
                'allocation': 0.05,
                'win_rate': 0.20,
                'avg_return': 5.00,
                'max_loss': 0.95,
                'target_dte': 1,
                'description': 'Lottery ticket plays'
            }
        }
    
    def generate_balanced_strategies(self, symbol, current_price, account_size):
        """Generate strategies across all risk levels"""
        
        strategies = []
        
        for risk_level, params in self.risk_levels.items():
            allocation_amount = account_size * params['allocation']
            
            # Get options chain for analysis
            try:
                ticker = yf.Ticker(symbol)
                if ticker.options:
                    # Find appropriate expiration
                    target_dte = params['target_dte']
                    target_date = datetime.now() + timedelta(days=target_dte)
                    
                    # Find closest expiration to target
                    best_exp = None
                    min_diff = float('inf')
                    
                    for exp_date in ticker.options:
                        exp_datetime = datetime.strptime(exp_date, '%Y-%m-%d')
                        diff = abs((exp_datetime - target_date).days)
                        if diff < min_diff:
                            min_diff = diff
                            best_exp = exp_date
                    
                    if best_exp:
                        chain = ticker.option_chain(best_exp)
                        
                        # Generate strategy based on risk level
                        if risk_level == 'conservative':
                            strategy = self._conservative_income_strategy(
                                chain, current_price, allocation_amount, best_exp
                            )
                        elif risk_level == 'moderate':
                            strategy = self._moderate_growth_strategy(
                                chain, current_price, allocation_amount, best_exp
                            )
                        elif risk_level == 'aggressive':
                            strategy = self._aggressive_swing_strategy(
                                chain, current_price, allocation_amount, best_exp
                            )
                        else:  # speculation
                            strategy = self._speculation_strategy(
                                chain, current_price, allocation_amount, best_exp
                            )
                        
                        if strategy:
                            strategy['risk_level'] = risk_level
                            strategy['allocation_pct'] = params['allocation'] * 100
                            strategy['expected_win_rate'] = params['win_rate'] * 100
                            strategy['description'] = params['description']
                            strategies.append(strategy)
            
            except Exception as e:
                # Create basic strategy without options data
                strategy = {
                    'risk_level': risk_level,
                    'allocation_pct': params['allocation'] * 100,
                    'allocation_amount': allocation_amount,
                    'expected_win_rate': params['win_rate'] * 100,
                    'target_return': params['avg_return'] * 100,
                    'description': params['description'],
                    'expiration': f"{params['target_dte']} days",
                    'strategy_type': 'No options data available'
                }
                strategies.append(strategy)
        
        return strategies
    
    def _conservative_income_strategy(self, chain, current_price, allocation, expiration):
        """Generate conservative income strategy (covered calls, cash-secured puts)"""
        
        # Look for ITM or ATM options with good premium
        calls = chain.calls
        puts = chain.puts
        
        # Find best ITM/ATM calls for covered call strategy
        itm_calls = calls[
            (calls['strike'] <= current_price + 2) & 
            (calls['strike'] >= current_price - 2) &
            (calls['bid'] > 1.0) &
            (calls['volume'] > 10)
        ].sort_values('bid', ascending=False)
        
        # Find best OTM puts for cash-secured puts
        otm_puts = puts[
            (puts['strike'] <= current_price * 0.95) &
            (puts['strike'] >= current_price * 0.85) &
            (puts['bid'] > 0.50) &
            (puts['volume'] > 10)
        ].sort_values('bid', ascending=False)
        
        strategies = []
        
        if not itm_calls.empty:
            call = itm_calls.iloc[0]
            premium = (call['bid'] + call['ask']) / 2
            contracts = int(allocation / (premium * 100))
            
            strategies.append({
                'type': 'Covered Call (if you own stock)',
                'strike': call['strike'],
                'premium': premium,
                'contracts': contracts,
                'cost': 0,  # Assuming stock ownership
                'max_profit': premium * contracts * 100,
                'break_even': current_price - premium,
                'probability': '70-80%'
            })
        
        if not otm_puts.empty:
            put = otm_puts.iloc[0]
            premium = (put['bid'] + put['ask']) / 2
            contracts = int(allocation / (put['strike'] * 100))
            
            strategies.append({
                'type': 'Cash-Secured Put',
                'strike': put['strike'],
                'premium': premium,
                'contracts': contracts,
                'cost': put['strike'] * contracts * 100,
                'max_profit': premium * contracts * 100,
                'break_even': put['strike'] - premium,
                'probability': '70-80%'
            })
        
        return {
            'strategy_type': 'Conservative Income',
            'strategies': strategies,
            'total_allocation': allocation,
            'target_return': '20-40%',
            'expiration': expiration
        } if strategies else None
    
    def _moderate_growth_strategy(self, chain, current_price, allocation, expiration):
        """Generate moderate growth strategy (near ATM long options)"""
        
        calls = chain.calls
        puts = chain.puts
        
        # Find near ATM options
        near_atm_calls = calls[
            (calls['strike'] >= current_price * 0.98) & 
            (calls['strike'] <= current_price * 1.05) &
            (calls['bid'] > 0.50) &
            (calls['volume'] > 5)
        ].sort_values('volume', ascending=False)
        
        near_atm_puts = puts[
            (puts['strike'] >= current_price * 0.95) & 
            (puts['strike'] <= current_price * 1.02) &
            (puts['bid'] > 0.50) &
            (puts['volume'] > 5)
        ].sort_values('volume', ascending=False)
        
        strategies = []
        
        if not near_atm_calls.empty:
            call = near_atm_calls.iloc[0]
            premium = (call['bid'] + call['ask']) / 2
            contracts = int(allocation / (premium * 100 * 0.6))  # Use 60% for calls
            
            strategies.append({
                'type': 'Long Call',
                'strike': call['strike'],
                'premium': premium,
                'contracts': contracts,
                'cost': premium * contracts * 100,
                'break_even': call['strike'] + premium,
                'target_1': call['strike'] * 1.05,
                'target_2': call['strike'] * 1.10,
                'probability': '50-60%'
            })
        
        if not near_atm_puts.empty:
            put = near_atm_puts.iloc[0]
            premium = (put['bid'] + put['ask']) / 2
            contracts = int(allocation / (premium * 100 * 0.4))  # Use 40% for puts
            
            strategies.append({
                'type': 'Long Put',
                'strike': put['strike'],
                'premium': premium,
                'contracts': contracts,
                'cost': premium * contracts * 100,
                'break_even': put['strike'] - premium,
                'target_1': put['strike'] * 0.95,
                'target_2': put['strike'] * 0.90,
                'probability': '50-60%'
            })
        
        return {
            'strategy_type': 'Moderate Growth',
            'strategies': strategies,
            'total_allocation': allocation,
            'target_return': '50-150%',
            'expiration': expiration
        } if strategies else None
    
    def _aggressive_swing_strategy(self, chain, current_price, allocation, expiration):
        """Generate aggressive swing strategy (OTM options)"""
        
        calls = chain.calls
        puts = chain.puts
        
        # Find OTM options with potential
        otm_calls = calls[
            (calls['strike'] >= current_price * 1.02) & 
            (calls['strike'] <= current_price * 1.15) &
            (calls['bid'] > 0.10) &
            (calls['volume'] > 1)
        ].sort_values('volume', ascending=False)
        
        otm_puts = puts[
            (puts['strike'] >= current_price * 0.85) & 
            (puts['strike'] <= current_price * 0.98) &
            (puts['bid'] > 0.10) &
            (puts['volume'] > 1)
        ].sort_values('volume', ascending=False)
        
        strategies = []
        
        if not otm_calls.empty:
            call = otm_calls.iloc[0]
            premium = (call['bid'] + call['ask']) / 2
            contracts = int(allocation / (premium * 100 * 0.7))  # Use 70% for directional play
            
            move_needed = (call['strike'] - current_price) / current_price * 100
            
            strategies.append({
                'type': 'OTM Long Call',
                'strike': call['strike'],
                'premium': premium,
                'contracts': contracts,
                'cost': premium * contracts * 100,
                'move_needed': f"{move_needed:.1f}%",
                'break_even': call['strike'] + premium,
                'target_return': '200-500%',
                'probability': '35-45%'
            })
        
        if not otm_puts.empty:
            put = otm_puts.iloc[0]
            premium = (put['bid'] + put['ask']) / 2
            contracts = int(allocation / (premium * 100 * 0.3))  # Use 30% for hedge
            
            move_needed = (current_price - put['strike']) / current_price * 100
            
            strategies.append({
                'type': 'OTM Long Put',
                'strike': put['strike'],
                'premium': premium,
                'contracts': contracts,
                'cost': premium * contracts * 100,
                'move_needed': f"{move_needed:.1f}%",
                'break_even': put['strike'] - premium,
                'target_return': '200-500%',
                'probability': '35-45%'
            })
        
        return {
            'strategy_type': 'Aggressive Swing',
            'strategies': strategies,
            'total_allocation': allocation,
            'target_return': '200-500%',
            'expiration': expiration
        } if strategies else None
    
    def _speculation_strategy(self, chain, current_price, allocation, expiration):
        """Generate speculation strategy (far OTM 0DTE-like options)"""
        
        calls = chain.calls
        puts = chain.puts
        
        # Find far OTM options (lottery tickets)
        far_otm_calls = calls[
            (calls['strike'] >= current_price * 1.05) & 
            (calls['strike'] <= current_price * 1.25) &
            (calls['bid'] > 0.01) &
            (calls['ask'] < 1.00)
        ].sort_values('ask')
        
        far_otm_puts = puts[
            (puts['strike'] >= current_price * 0.75) & 
            (puts['strike'] <= current_price * 0.95) &
            (puts['bid'] > 0.01) &
            (puts['ask'] < 1.00)
        ].sort_values('ask')
        
        strategies = []
        
        if not far_otm_calls.empty:
            call = far_otm_calls.iloc[0]
            premium = call['ask']  # Use ask price for quick execution
            contracts = int(allocation / (premium * 100))
            
            move_needed = (call['strike'] - current_price) / current_price * 100
            
            strategies.append({
                'type': 'Far OTM Call (Lottery)',
                'strike': call['strike'],
                'premium': premium,
                'contracts': contracts,
                'cost': premium * contracts * 100,
                'move_needed': f"{move_needed:.1f}%",
                'max_return': '500-2000%',
                'probability': '15-25%'
            })
        
        if not far_otm_puts.empty:
            put = far_otm_puts.iloc[0]
            premium = put['ask']  # Use ask price for quick execution
            contracts = int(allocation / (premium * 100))
            
            move_needed = (current_price - put['strike']) / current_price * 100
            
            strategies.append({
                'type': 'Far OTM Put (Lottery)',
                'strike': put['strike'],
                'premium': premium,
                'contracts': contracts,
                'cost': premium * contracts * 100,
                'move_needed': f"{move_needed:.1f}%",
                'max_return': '500-2000%',
                'probability': '15-25%'
            })
        
        return {
            'strategy_type': 'Speculation',
            'strategies': strategies,
            'total_allocation': allocation,
            'target_return': '500-2000%',
            'expiration': expiration
        } if strategies else None
    
    def calculate_portfolio_metrics(self, strategies):
        """Calculate overall portfolio risk metrics"""
        
        total_allocation = sum(s.get('allocation_amount', 0) for s in strategies)
        
        # Weighted average win rate
        weighted_win_rate = sum(
            s.get('expected_win_rate', 0) * s.get('allocation_amount', 0) 
            for s in strategies
        ) / total_allocation if total_allocation > 0 else 0
        
        # Expected portfolio return
        portfolio_return = 0
        for s in strategies:
            if s.get('allocation_amount', 0) > 0:
                target_return = float(s.get('target_return', '0').replace('%', ''))
                weight = s.get('allocation_amount', 0) / total_allocation
                portfolio_return += target_return * weight
        
        return {
            'total_allocation': total_allocation,
            'weighted_win_rate': weighted_win_rate,
            'expected_return': portfolio_return,
            'risk_distribution': {
                s['risk_level']: s.get('allocation_pct', 0) 
                for s in strategies
            }
        }

# Initialize professional risk management
professional_risk = ProfessionalRiskManagement()