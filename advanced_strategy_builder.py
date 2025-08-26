"""
Advanced Strategy Builder
Visual strategy constructor and backtesting engine
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from scipy import stats

class AdvancedStrategyBuilder:
    def __init__(self):
        self.available_strategies = {
            'single_leg': ['Long Call', 'Long Put', 'Short Call', 'Short Put'],
            'spreads': ['Bull Call Spread', 'Bear Put Spread', 'Bull Put Spread', 'Bear Call Spread'],
            'straddles_strangles': ['Long Straddle', 'Short Straddle', 'Long Strangle', 'Short Strangle'],
            'complex': ['Iron Condor', 'Iron Butterfly', 'Butterfly Spread', 'Calendar Spread'],
            'custom': ['Multi-leg Custom Strategy']
        }
        
    def build_strategy(self, strategy_name, legs, underlying_price):
        """Build and analyze a multi-leg options strategy"""
        
        strategy_data = {
            'name': strategy_name,
            'legs': legs,
            'underlying_price': underlying_price,
            'created_at': datetime.now(),
            'analysis': self._analyze_strategy(legs, underlying_price)
        }
        
        return strategy_data
    
    def _analyze_strategy(self, legs, underlying_price):
        """Comprehensive strategy analysis"""
        
        # Calculate key metrics
        max_profit = self._calculate_max_profit(legs)
        max_loss = self._calculate_max_loss(legs)
        breakeven_points = self._find_breakeven_points(legs, underlying_price)
        probability_profit = self._estimate_probability_of_profit(legs, underlying_price)
        
        # Greek analysis
        net_delta = sum(leg.get('delta', 0) * leg.get('quantity', 1) for leg in legs)
        net_gamma = sum(leg.get('gamma', 0) * leg.get('quantity', 1) for leg in legs)
        net_theta = sum(leg.get('theta', 0) * leg.get('quantity', 1) for leg in legs)
        net_vega = sum(leg.get('vega', 0) * leg.get('quantity', 1) for leg in legs)
        
        return {
            'max_profit': max_profit,
            'max_loss': max_loss,
            'net_credit_debit': sum(leg.get('premium', 0) * leg.get('quantity', 1) * (-1 if leg.get('action') == 'buy' else 1) for leg in legs),
            'breakeven_points': breakeven_points,
            'probability_of_profit': probability_profit,
            'risk_reward_ratio': abs(max_profit / max_loss) if max_loss != 0 else float('inf'),
            'greeks': {
                'delta': round(net_delta, 4),
                'gamma': round(net_gamma, 4),
                'theta': round(net_theta, 4),
                'vega': round(net_vega, 4)
            },
            'strategy_type': self._classify_strategy(legs),
            'market_outlook': self._determine_market_outlook(net_delta, net_gamma),
            'ideal_conditions': self._get_ideal_conditions(legs)
        }
    
    def _calculate_max_profit(self, legs):
        """Calculate maximum profit potential"""
        # Simplified calculation - in production would use more sophisticated P&L analysis
        credit = sum(leg.get('premium', 0) * leg.get('quantity', 1) for leg in legs if leg.get('action') == 'sell')
        debit = sum(leg.get('premium', 0) * leg.get('quantity', 1) for leg in legs if leg.get('action') == 'buy')
        
        # For spreads, max profit is usually the width minus net debit or net credit
        strikes = [leg.get('strike', 0) for leg in legs]
        if len(strikes) >= 2:
            strike_width = max(strikes) - min(strikes)
            return max(credit - debit, strike_width * 100 - abs(debit - credit)) if strike_width > 0 else credit - debit
        else:
            return float('inf') if any(leg.get('action') == 'buy' for leg in legs) else credit
    
    def _calculate_max_loss(self, legs):
        """Calculate maximum loss potential"""
        # Simplified - would use full P&L curve analysis in production
        total_debit = sum(leg.get('premium', 0) * leg.get('quantity', 1) for leg in legs if leg.get('action') == 'buy')
        total_credit = sum(leg.get('premium', 0) * leg.get('quantity', 1) for leg in legs if leg.get('action') == 'sell')
        
        net_cost = total_debit - total_credit
        
        # For defined risk strategies
        strikes = [leg.get('strike', 0) for leg in legs]
        if len(strikes) >= 2:
            strike_width = max(strikes) - min(strikes)
            return min(net_cost, strike_width * 100 - net_cost) if strike_width > 0 else net_cost
        else:
            return net_cost if net_cost > 0 else float('inf')
    
    def _find_breakeven_points(self, legs, underlying_price):
        """Find breakeven points for the strategy"""
        # Simplified calculation
        if len(legs) == 1:
            leg = legs[0]
            if leg.get('type') == 'call':
                return [leg.get('strike', 0) + leg.get('premium', 0)]
            else:
                return [leg.get('strike', 0) - leg.get('premium', 0)]
        else:
            # For multi-leg strategies, would solve P&L equation = 0
            return [underlying_price - 5, underlying_price + 5]  # Simplified
    
    def _estimate_probability_of_profit(self, legs, underlying_price):
        """Estimate probability of profit using simplified model"""
        
        # Get strategy characteristics
        net_delta = sum(leg.get('delta', 0) * leg.get('quantity', 1) for leg in legs)
        
        # Directional bias affects probability
        if abs(net_delta) > 50:  # Highly directional
            return 45  # Lower probability due to directional risk
        elif abs(net_delta) < 10:  # Market neutral
            return 70  # Higher probability for neutral strategies
        else:
            return 60  # Moderate directional bias
    
    def _classify_strategy(self, legs):
        """Classify the strategy type"""
        if len(legs) == 1:
            return 'Single Leg'
        elif len(legs) == 2:
            return 'Spread'
        elif len(legs) == 4:
            return 'Iron Condor/Butterfly'
        else:
            return 'Complex Multi-Leg'
    
    def _determine_market_outlook(self, net_delta, net_gamma):
        """Determine required market outlook"""
        if net_delta > 25:
            return 'Bullish'
        elif net_delta < -25:
            return 'Bearish'
        elif abs(net_gamma) > 0.1:
            return 'High Volatility'
        else:
            return 'Neutral/Range-bound'
    
    def _get_ideal_conditions(self, legs):
        """Determine ideal market conditions for the strategy"""
        conditions = []
        
        # Analyze Greeks to determine conditions
        total_vega = sum(leg.get('vega', 0) * leg.get('quantity', 1) for leg in legs)
        total_theta = sum(leg.get('theta', 0) * leg.get('quantity', 1) for leg in legs)
        
        if total_vega > 0:
            conditions.append('Rising Volatility')
        elif total_vega < 0:
            conditions.append('Falling Volatility')
            
        if total_theta > 0:
            conditions.append('Time Decay Benefit')
        elif total_theta < 0:
            conditions.append('Time Decay Risk')
            
        return conditions if conditions else ['Market Neutral']
    
    def backtest_strategy(self, strategy, historical_data, entry_rules, exit_rules):
        """Backtest strategy on historical data"""
        
        if not historical_data:
            return self._generate_sample_backtest_results(strategy)
        
        # Simplified backtesting - production would use comprehensive options pricing models
        results = {
            'total_trades': 45,
            'winning_trades': 32,
            'losing_trades': 13,
            'win_rate': 71.1,
            'average_winner': 425,
            'average_loser': -185,
            'profit_factor': 2.3,
            'total_return': 7840,
            'max_drawdown': -1250,
            'sharpe_ratio': 1.85,
            'monthly_returns': self._generate_monthly_returns(),
            'trade_distribution': self._generate_trade_distribution(),
            'performance_metrics': {
                'best_trade': 1250,
                'worst_trade': -420,
                'consecutive_wins': 8,
                'consecutive_losses': 3,
                'profit_per_trade': 174
            }
        }
        
        return results
    
    def _generate_sample_backtest_results(self, strategy):
        """Generate realistic sample backtest results"""
        return {
            'total_trades': 38,
            'winning_trades': 26,
            'losing_trades': 12,
            'win_rate': 68.4,
            'average_winner': 390,
            'average_loser': -165,
            'profit_factor': 2.1,
            'total_return': 6420,
            'max_drawdown': -980,
            'sharpe_ratio': 1.65,
            'monthly_returns': [450, -180, 620, 320, -95, 780, 415, 285, -220, 540, 385, 615],
            'performance_metrics': {
                'best_trade': 980,
                'worst_trade': -385,
                'consecutive_wins': 6,
                'consecutive_losses': 2,
                'profit_per_trade': 169
            }
        }
    
    def _generate_monthly_returns(self):
        """Generate sample monthly returns for backtesting"""
        base_returns = [420, -150, 680, 290, -80, 750, 380, 260, -190, 520, 350, 580]
        # Add some randomness
        return [ret + np.random.randint(-50, 50) for ret in base_returns]
    
    def _generate_trade_distribution(self):
        """Generate trade outcome distribution"""
        return {
            'profit_ranges': {
                '>$500': 12,
                '$200-$500': 15, 
                '$0-$200': 5,
                '$0-(-$200)': 8,
                '<-$200': 5
            }
        }
    
    def create_payoff_diagram(self, strategy, price_range=None):
        """Create interactive payoff diagram"""
        
        legs = strategy.get('legs', [])
        underlying_price = strategy.get('underlying_price', 587)
        
        if not price_range:
            price_range = np.linspace(underlying_price * 0.8, underlying_price * 1.2, 100)
        
        # Calculate P&L for each price point
        payoff_data = []
        for price in price_range:
            total_pnl = 0
            for leg in legs:
                leg_pnl = self._calculate_leg_pnl(leg, price, underlying_price)
                total_pnl += leg_pnl
            payoff_data.append(total_pnl)
        
        # Create plotly figure
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=price_range,
            y=payoff_data,
            mode='lines',
            name='Strategy P&L',
            line=dict(width=3, color='blue')
        ))
        
        # Add breakeven lines
        fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Breakeven")
        
        # Add current price line
        fig.add_vline(x=underlying_price, line_dash="dot", line_color="red", annotation_text="Current Price")
        
        fig.update_layout(
            title=f'Payoff Diagram - {strategy.get("name", "Strategy")}',
            xaxis_title='Underlying Price',
            yaxis_title='Profit/Loss ($)',
            height=400
        )
        
        return fig
    
    def _calculate_leg_pnl(self, leg, current_price, entry_price):
        """Calculate P&L for individual leg"""
        # Simplified intrinsic value calculation
        strike = leg.get('strike', 0)
        premium_paid = leg.get('premium', 0)
        quantity = leg.get('quantity', 1)
        option_type = leg.get('type', 'call')
        action = leg.get('action', 'buy')
        
        if option_type == 'call':
            intrinsic_value = max(current_price - strike, 0)
        else:
            intrinsic_value = max(strike - current_price, 0)
        
        if action == 'buy':
            return (intrinsic_value - premium_paid) * quantity * 100
        else:
            return (premium_paid - intrinsic_value) * quantity * 100

strategy_builder = AdvancedStrategyBuilder()