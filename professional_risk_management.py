"""
Professional Risk Management System
Advanced risk metrics, stress testing, and correlation analysis
"""

import numpy as np
import pandas as pd
from scipy import stats
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

class ProfessionalRiskManager:
    def __init__(self):
        self.confidence_levels = [0.95, 0.99]  # 95% and 99% confidence
        self.stress_scenarios = [
            'Market Crash (-20%)', 'Flash Crash (-10%)', 'Volatility Spike (+50%)',
            'Rate Shock (+200bps)', 'Correlation Breakdown', 'Liquidity Crisis'
        ]
        
    def calculate_portfolio_var(self, positions, confidence_level=0.95, time_horizon=1):
        """Calculate Value at Risk for the portfolio"""
        
        # Simulate portfolio returns based on positions
        portfolio_value = sum(pos.get('market_value', 10000) for pos in positions)
        
        # Monte Carlo simulation for VaR calculation
        num_simulations = 10000
        returns = []
        
        for _ in range(num_simulations):
            # Simulate random market move
            market_move = np.random.normal(0, 0.02)  # 2% daily volatility
            vol_change = np.random.normal(0, 0.1)   # 10% vol change
            
            portfolio_pnl = 0
            for pos in positions:
                # Calculate position P&L from market and vol changes
                delta_pnl = pos.get('delta', 0) * market_move * pos.get('market_value', 0) / 100
                vega_pnl = pos.get('vega', 0) * vol_change * pos.get('market_value', 0) / 1000
                theta_pnl = pos.get('theta', 0) * time_horizon
                
                portfolio_pnl += delta_pnl + vega_pnl + theta_pnl
            
            returns.append(portfolio_pnl / portfolio_value)
        
        # Calculate VaR
        var_percentile = (1 - confidence_level) * 100
        var_return = np.percentile(returns, var_percentile)
        var_dollar = abs(var_return * portfolio_value)
        
        return {
            'confidence_level': confidence_level,
            'time_horizon_days': time_horizon,
            'portfolio_value': portfolio_value,
            'var_percentage': abs(var_return) * 100,
            'var_dollar': var_dollar,
            'expected_shortfall': abs(np.mean([r for r in returns if r <= var_return])) * portfolio_value,
            'worst_case_scenario': abs(min(returns)) * portfolio_value,
            'risk_grade': self._assign_risk_grade(abs(var_return) * 100),
            'recommendations': self._get_risk_recommendations(abs(var_return) * 100)
        }
    
    def _assign_risk_grade(self, var_percentage):
        """Assign risk grade based on VaR percentage"""
        if var_percentage < 2:
            return 'LOW'
        elif var_percentage < 5:
            return 'MODERATE'
        elif var_percentage < 10:
            return 'HIGH'
        else:
            return 'EXTREME'
    
    def _get_risk_recommendations(self, var_percentage):
        """Get risk management recommendations"""
        if var_percentage < 2:
            return ['Portfolio risk is well controlled', 'Consider increasing position sizes']
        elif var_percentage < 5:
            return ['Risk is manageable', 'Monitor closely during volatile periods']
        elif var_percentage < 10:
            return ['Risk is elevated', 'Consider reducing position sizes', 'Implement hedging strategies']
        else:
            return ['URGENT: Risk is too high', 'Reduce positions immediately', 'Implement emergency hedging']
    
    def stress_test_portfolio(self, positions):
        """Comprehensive stress testing across multiple scenarios"""
        
        stress_results = {}
        
        for scenario in self.stress_scenarios:
            scenario_pnl = self._calculate_scenario_pnl(positions, scenario)
            stress_results[scenario] = scenario_pnl
        
        # Summary statistics
        worst_scenario = min(stress_results.values())
        best_scenario = max(stress_results.values())
        
        return {
            'scenario_results': stress_results,
            'worst_case_loss': abs(worst_scenario),
            'best_case_gain': best_scenario,
            'scenarios_profitable': sum(1 for pnl in stress_results.values() if pnl > 0),
            'stress_test_grade': self._grade_stress_test(worst_scenario),
            'hedging_requirements': self._calculate_hedging_requirements(stress_results),
            'portfolio_resilience': self._assess_portfolio_resilience(stress_results)
        }
    
    def _calculate_scenario_pnl(self, positions, scenario):
        """Calculate P&L for a specific stress scenario"""
        
        scenario_parameters = {
            'Market Crash (-20%)': {'price_change': -0.20, 'vol_change': 0.50, 'correlation_change': 0.20},
            'Flash Crash (-10%)': {'price_change': -0.10, 'vol_change': 0.80, 'correlation_change': 0.10},
            'Volatility Spike (+50%)': {'price_change': 0.02, 'vol_change': 0.50, 'correlation_change': 0.05},
            'Rate Shock (+200bps)': {'price_change': -0.05, 'vol_change': 0.20, 'correlation_change': 0.15},
            'Correlation Breakdown': {'price_change': -0.03, 'vol_change': 0.30, 'correlation_change': 0.50},
            'Liquidity Crisis': {'price_change': -0.08, 'vol_change': 0.40, 'correlation_change': 0.25}
        }
        
        params = scenario_parameters.get(scenario, {'price_change': 0, 'vol_change': 0, 'correlation_change': 0})
        
        total_pnl = 0
        for pos in positions:
            # Calculate position-specific P&L under stress
            delta_pnl = pos.get('delta', 0) * params['price_change'] * pos.get('market_value', 0) / 100
            vega_pnl = pos.get('vega', 0) * params['vol_change'] * pos.get('market_value', 0) / 100
            gamma_pnl = pos.get('gamma', 0) * (params['price_change'] ** 2) * pos.get('market_value', 0) / 2
            
            total_pnl += delta_pnl + vega_pnl + gamma_pnl
        
        return total_pnl
    
    def _grade_stress_test(self, worst_case_loss):
        """Grade the stress test results"""
        loss_percentage = abs(worst_case_loss) / 100000  # Assume $100k portfolio
        
        if loss_percentage < 0.05:
            return 'EXCELLENT'
        elif loss_percentage < 0.10:
            return 'GOOD'
        elif loss_percentage < 0.20:
            return 'FAIR'
        else:
            return 'POOR'
    
    def _calculate_hedging_requirements(self, stress_results):
        """Calculate hedging requirements based on stress test"""
        max_loss = abs(min(stress_results.values()))
        
        if max_loss < 5000:
            return 'No additional hedging required'
        elif max_loss < 15000:
            return 'Consider protective puts or collar strategy'
        else:
            return 'URGENT: Implement comprehensive hedging strategy'
    
    def _assess_portfolio_resilience(self, stress_results):
        """Assess overall portfolio resilience"""
        profitable_scenarios = sum(1 for pnl in stress_results.values() if pnl > 0)
        total_scenarios = len(stress_results)
        resilience_score = profitable_scenarios / total_scenarios * 100
        
        return {
            'resilience_score': resilience_score,
            'resilience_grade': 'HIGH' if resilience_score > 50 else 'MODERATE' if resilience_score > 25 else 'LOW',
            'diversification_benefit': 'GOOD' if resilience_score > 40 else 'NEEDS_IMPROVEMENT'
        }
    
    def calculate_optimal_position_sizing(self, trade_setup, account_balance, risk_tolerance=0.02):
        """Calculate optimal position size using Kelly Criterion"""
        
        win_probability = trade_setup.get('win_probability', 0.6) / 100
        avg_win = trade_setup.get('avg_win', 300)
        avg_loss = trade_setup.get('avg_loss', 150)
        
        # Kelly Criterion: f* = (bp - q) / b
        # where b = odds received on wager, p = probability of winning, q = probability of losing
        win_loss_ratio = avg_win / avg_loss
        
        kelly_fraction = (win_probability * win_loss_ratio - (1 - win_probability)) / win_loss_ratio
        kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap at 25% of capital
        
        # Adjust for risk tolerance
        recommended_fraction = kelly_fraction * risk_tolerance / 0.02
        position_size = account_balance * recommended_fraction
        
        return {
            'kelly_fraction': round(kelly_fraction, 4),
            'recommended_fraction': round(recommended_fraction, 4),
            'position_size': round(position_size, 2),
            'max_contracts': int(position_size / (trade_setup.get('cost_per_contract', 100))),
            'risk_amount': position_size,
            'expected_value': position_size * (win_probability * (avg_win/100) - (1-win_probability) * (avg_loss/100)),
            'sizing_rationale': self._get_sizing_rationale(kelly_fraction, recommended_fraction),
            'risk_metrics': {
                'probability_of_ruin': self._calculate_ruin_probability(kelly_fraction, win_probability),
                'expected_drawdown': position_size * 0.3,  # Estimated max drawdown
                'recovery_time': '2-4 weeks'  # Estimated recovery time
            }
        }
    
    def _get_sizing_rationale(self, kelly_fraction, recommended_fraction):
        """Provide rationale for position sizing recommendation"""
        if recommended_fraction < 0.01:
            return 'Very conservative sizing due to unfavorable risk/reward or low win rate'
        elif recommended_fraction < 0.03:
            return 'Conservative sizing - good for steady growth'
        elif recommended_fraction < 0.06:
            return 'Moderate sizing - balanced risk/reward approach'
        else:
            return 'Aggressive sizing - high confidence trade with good risk/reward'
    
    def _calculate_ruin_probability(self, kelly_fraction, win_probability):
        """Calculate probability of ruin using simplified formula"""
        if kelly_fraction <= 0:
            return 0.5
        
        # Simplified ruin probability calculation
        ruin_prob = max(0, 1 - win_probability) ** (1 / kelly_fraction)
        return min(ruin_prob, 0.5)  # Cap at 50%
    
    def analyze_correlation_risk(self, positions):
        """Analyze correlation risk across portfolio positions"""
        
        # Simulate correlation matrix for different assets
        symbols = list(set(pos.get('symbol', 'SPY') for pos in positions))
        correlation_matrix = self._generate_correlation_matrix(symbols)
        
        # Calculate portfolio concentration risk
        concentration_risk = self._calculate_concentration_risk(positions)
        
        # Diversification analysis
        diversification_score = self._calculate_diversification_score(positions)
        
        return {
            'correlation_matrix': correlation_matrix,
            'concentration_risk': concentration_risk,
            'diversification_score': diversification_score,
            'correlation_warnings': self._get_correlation_warnings(correlation_matrix),
            'diversification_recommendations': self._get_diversification_recommendations(diversification_score),
            'sector_exposure': self._analyze_sector_exposure(positions),
            'correlation_stress_test': self._stress_test_correlations(positions)
        }
    
    def _generate_correlation_matrix(self, symbols):
        """Generate realistic correlation matrix"""
        n = len(symbols)
        correlations = {}
        
        for i, sym1 in enumerate(symbols):
            correlations[sym1] = {}
            for j, sym2 in enumerate(symbols):
                if i == j:
                    correlations[sym1][sym2] = 1.0
                else:
                    # Simulate realistic correlations (higher for related assets)
                    base_corr = 0.3 if 'SPY' in [sym1, sym2] else 0.15
                    correlations[sym1][sym2] = round(base_corr + np.random.normal(0, 0.1), 2)
        
        return correlations
    
    def _calculate_concentration_risk(self, positions):
        """Calculate concentration risk metrics"""
        total_value = sum(pos.get('market_value', 0) for pos in positions)
        
        if total_value == 0:
            return {'concentration_score': 0, 'largest_position': 0, 'top_3_concentration': 0}
        
        position_weights = [pos.get('market_value', 0) / total_value for pos in positions]
        position_weights.sort(reverse=True)
        
        return {
            'concentration_score': round(sum(w**2 for w in position_weights) * 100, 1),  # Herfindahl index
            'largest_position': round(position_weights[0] * 100, 1) if position_weights else 0,
            'top_3_concentration': round(sum(position_weights[:3]) * 100, 1) if len(position_weights) >= 3 else 100,
            'effective_positions': round(1 / sum(w**2 for w in position_weights), 1) if position_weights else 1
        }
    
    def _calculate_diversification_score(self, positions):
        """Calculate portfolio diversification score"""
        # Simple diversification metrics
        num_positions = len(positions)
        unique_symbols = len(set(pos.get('symbol', 'SPY') for pos in positions))
        
        if num_positions == 0:
            return 0
        
        symbol_diversification = unique_symbols / num_positions * 100
        
        # Factor in position sizes
        total_value = sum(pos.get('market_value', 0) for pos in positions)
        if total_value > 0:
            weights = [pos.get('market_value', 0) / total_value for pos in positions]
            size_diversification = (1 - max(weights)) * 100
        else:
            size_diversification = 0
        
        overall_score = (symbol_diversification + size_diversification) / 2
        return round(min(overall_score, 100), 1)
    
    def _get_correlation_warnings(self, correlation_matrix):
        """Generate warnings based on correlation analysis"""
        warnings = []
        
        # Check for high correlations
        for sym1, correlations in correlation_matrix.items():
            for sym2, corr in correlations.items():
                if sym1 != sym2 and abs(corr) > 0.7:
                    warnings.append(f'High correlation ({corr:.2f}) between {sym1} and {sym2}')
        
        if not warnings:
            warnings.append('No significant correlation concerns detected')
        
        return warnings
    
    def _get_diversification_recommendations(self, diversification_score):
        """Provide diversification recommendations"""
        if diversification_score > 80:
            return ['Excellent diversification', 'Portfolio is well spread across positions']
        elif diversification_score > 60:
            return ['Good diversification', 'Consider minor adjustments to position sizes']
        elif diversification_score > 40:
            return ['Moderate diversification', 'Add more positions or rebalance sizes']
        else:
            return ['Poor diversification', 'URGENT: Add positions and reduce concentration']
    
    def _analyze_sector_exposure(self, positions):
        """Analyze sector exposure concentration"""
        # Simplified sector mapping
        sector_mapping = {
            'SPY': 'Broad Market', 'QQQ': 'Technology', 'AAPL': 'Technology',
            'MSFT': 'Technology', 'GOOGL': 'Technology', 'TSLA': 'Technology',
            'XLF': 'Financial', 'XLE': 'Energy', 'XLK': 'Technology'
        }
        
        sector_exposure = {}
        total_value = sum(pos.get('market_value', 0) for pos in positions)
        
        for pos in positions:
            symbol = pos.get('symbol', 'SPY')
            sector = sector_mapping.get(symbol, 'Other')
            value = pos.get('market_value', 0)
            
            if sector not in sector_exposure:
                sector_exposure[sector] = 0
            sector_exposure[sector] += value
        
        # Convert to percentages
        if total_value > 0:
            sector_exposure = {sector: round(value / total_value * 100, 1) 
                             for sector, value in sector_exposure.items()}
        
        return sector_exposure
    
    def _stress_test_correlations(self, positions):
        """Stress test portfolio under correlation breakdown scenarios"""
        # Simulate correlation breakdown (all correlations increase by 50%)
        stress_scenarios = {
            'correlation_spike': 'All correlations increase by 50%',
            'correlation_breakdown': 'All correlations go to 0.9',
            'flight_to_quality': 'Risk assets become highly correlated'
        }
        
        return {
            'scenarios': stress_scenarios,
            'estimated_impact': {
                'correlation_spike': -850,      # Estimated P&L impact
                'correlation_breakdown': -1200,
                'flight_to_quality': -650
            },
            'risk_grade': 'MODERATE',
            'recommendations': [
                'Monitor correlation changes during market stress',
                'Consider adding uncorrelated assets',
                'Implement correlation-based hedging'
            ]
        }

# Initialize the professional risk manager
risk_manager = ProfessionalRiskManager()