"""
INSTITUTIONAL RISK MANAGEMENT ENGINE
Real-time risk monitoring, position sizing, and portfolio protection
"""

import numpy as np
import pandas as pd
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import yfinance as yf
import json


class InstitutionalRiskEngine:
    """Professional risk management with real-time monitoring"""
    
    def __init__(self):
        self.risk_limits = {
            'max_portfolio_risk': 0.02,  # 2% max portfolio risk
            'max_position_size': 0.10,   # 10% max position size
            'max_correlation': 0.70,     # 70% max correlation
            'max_delta_exposure': 1000,  # Max net delta
            'max_gamma_exposure': 500,   # Max net gamma
            'max_theta_decay': -200,     # Max daily theta decay
            'volatility_threshold': 0.30, # 30% volatility alert
            'liquidity_minimum': 1000   # Min daily volume
        }
        
        self.alerts_sent = {}  # Cooldown tracking
        
    async def calculate_portfolio_risk_metrics(self, positions: Dict) -> Dict:
        """Calculate comprehensive portfolio risk metrics"""
        try:
            metrics = {
                'portfolio_var': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'portfolio_beta': 0.0,
                'concentration_risk': 0.0,
                'correlation_risk': 0.0,
                'liquidity_risk': 0.0,
                'volatility_risk': 0.0,
                'risk_score': 0.0,
                'risk_alerts': []
            }
            
            if not positions.get('stocks') and not positions.get('options'):
                return metrics
            
            # Get portfolio value
            total_value = 0.0
            position_values = []
            symbols = []
            
            # Calculate stock positions value
            for symbol, position in positions.get('stocks', {}).items():
                value = position['quantity'] * position.get('current_price', position['entry_price'])
                total_value += abs(value)
                position_values.append(abs(value))
                symbols.append(symbol)
            
            # Calculate options positions value
            for pos_id, position in positions.get('options', {}).items():
                value = position['quantity'] * position.get('current_price', position['entry_price']) * 100
                total_value += abs(value)
                position_values.append(abs(value))
                symbols.append(position['symbol'])
            
            if total_value == 0:
                return metrics
            
            # Concentration risk (largest position as % of portfolio)
            metrics['concentration_risk'] = max(position_values) / total_value if position_values else 0.0
            
            # Correlation risk assessment
            if len(set(symbols)) > 1:
                correlations = await self._calculate_correlation_matrix(list(set(symbols)))
                avg_correlation = np.mean(np.abs(correlations)) if correlations.size > 0 else 0.0
                metrics['correlation_risk'] = avg_correlation
            
            # Liquidity risk assessment
            liquidity_scores = []
            for symbol in set(symbols):
                liquidity_score = await self._assess_liquidity_risk(symbol)
                liquidity_scores.append(liquidity_score)
            
            metrics['liquidity_risk'] = 1.0 - np.mean(liquidity_scores) if liquidity_scores else 0.5
            
            # Volatility risk assessment
            volatility_scores = []
            for symbol in set(symbols):
                vol_score = await self._assess_volatility_risk(symbol)
                volatility_scores.append(vol_score)
            
            metrics['volatility_risk'] = np.mean(volatility_scores) if volatility_scores else 0.0
            
            # Overall risk score (0-100)
            risk_components = [
                metrics['concentration_risk'] * 0.3,
                metrics['correlation_risk'] * 0.2,
                metrics['liquidity_risk'] * 0.2,
                metrics['volatility_risk'] * 0.3
            ]
            
            metrics['risk_score'] = min(100, sum(risk_components) * 100)
            
            # Generate risk alerts
            metrics['risk_alerts'] = self._generate_risk_alerts(metrics)
            
            return metrics
            
        except Exception as e:
            print(f"Error calculating portfolio risk: {e}")
            return metrics
    
    async def _calculate_correlation_matrix(self, symbols: List[str]) -> np.ndarray:
        """Calculate correlation matrix for symbols"""
        try:
            if len(symbols) < 2:
                return np.array([])
            
            # Get price data for all symbols
            price_data = {}
            for symbol in symbols[:10]:  # Limit to 10 symbols for performance
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="90d")  # 90 days of data
                if not hist.empty:
                    price_data[symbol] = hist['Close'].pct_change().dropna()
            
            if len(price_data) < 2:
                return np.array([])
            
            # Create correlation matrix
            df = pd.DataFrame(price_data)
            correlation_matrix = df.corr().values
            
            # Remove diagonal (self-correlation)
            np.fill_diagonal(correlation_matrix, 0)
            
            return correlation_matrix
            
        except Exception as e:
            print(f"Error calculating correlations: {e}")
            return np.array([])
    
    async def _assess_liquidity_risk(self, symbol: str) -> float:
        """Assess liquidity risk for a symbol (0=high risk, 1=low risk)"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="30d")
            
            if hist.empty:
                return 0.3  # High risk for unknown liquidity
            
            avg_volume = hist['Volume'].mean()
            avg_price = hist['Close'].mean()
            dollar_volume = avg_volume * avg_price
            
            # Scoring based on dollar volume
            if dollar_volume > 100_000_000:  # >$100M daily
                return 1.0  # Excellent liquidity
            elif dollar_volume > 50_000_000:   # >$50M daily
                return 0.8  # Good liquidity
            elif dollar_volume > 10_000_000:   # >$10M daily
                return 0.6  # Moderate liquidity
            elif dollar_volume > 1_000_000:    # >$1M daily
                return 0.4  # Poor liquidity
            else:
                return 0.2  # Very poor liquidity
                
        except Exception as e:
            return 0.3  # Default moderate risk
    
    async def _assess_volatility_risk(self, symbol: str) -> float:
        """Assess volatility risk for a symbol (0=low vol, 1=high vol)"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="30d")
            
            if hist.empty:
                return 0.5  # Default moderate volatility
            
            # Calculate 30-day realized volatility
            returns = hist['Close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252)  # Annualized
            
            # Risk scoring based on volatility
            if volatility > 0.6:    # >60% annualized
                return 1.0  # Very high risk
            elif volatility > 0.4:  # >40% annualized
                return 0.8  # High risk
            elif volatility > 0.25: # >25% annualized
                return 0.6  # Moderate risk
            elif volatility > 0.15: # >15% annualized
                return 0.4  # Low risk
            else:
                return 0.2  # Very low risk
                
        except Exception as e:
            return 0.5  # Default moderate risk
    
    def _generate_risk_alerts(self, metrics: Dict) -> List[str]:
        """Generate risk alerts based on metrics"""
        alerts = []
        
        # Concentration risk alert
        if metrics['concentration_risk'] > self.risk_limits['max_position_size']:
            alerts.append(f"🚨 CONCENTRATION RISK: Single position is {metrics['concentration_risk']:.1%} of portfolio")
        
        # Correlation risk alert
        if metrics['correlation_risk'] > self.risk_limits['max_correlation']:
            alerts.append(f"⚠️ CORRELATION RISK: High correlation {metrics['correlation_risk']:.1%} detected")
        
        # Liquidity risk alert
        if metrics['liquidity_risk'] > 0.6:
            alerts.append("💧 LIQUIDITY RISK: Low liquidity positions detected")
        
        # Volatility risk alert
        if metrics['volatility_risk'] > 0.7:
            alerts.append("📈 VOLATILITY RISK: High volatility exposure")
        
        # Overall risk score alert
        if metrics['risk_score'] > 70:
            alerts.append(f"🔥 HIGH RISK PORTFOLIO: Risk score {metrics['risk_score']:.0f}/100")
        
        return alerts
    
    def calculate_position_size(self, symbol: str, entry_price: float, 
                               stop_loss: float, portfolio_value: float,
                               risk_percentage: float = 0.01) -> Dict:
        """Calculate optimal position size based on risk management"""
        try:
            # Risk per share
            risk_per_share = abs(entry_price - stop_loss)
            
            if risk_per_share == 0:
                return {
                    'recommended_shares': 0,
                    'risk_amount': 0.0,
                    'position_value': 0.0,
                    'risk_percentage': 0.0,
                    'warning': 'Invalid stop loss - no risk per share'
                }
            
            # Maximum risk amount
            max_risk = portfolio_value * risk_percentage
            
            # Calculate recommended shares
            recommended_shares = int(max_risk / risk_per_share)
            position_value = recommended_shares * entry_price
            actual_risk = recommended_shares * risk_per_share
            actual_risk_pct = actual_risk / portfolio_value
            
            # Position size as percentage of portfolio
            position_pct = position_value / portfolio_value
            
            warnings = []
            if position_pct > self.risk_limits['max_position_size']:
                warnings.append(f"Position size {position_pct:.1%} exceeds limit {self.risk_limits['max_position_size']:.1%}")
            
            if actual_risk_pct > self.risk_limits['max_portfolio_risk']:
                warnings.append(f"Risk {actual_risk_pct:.1%} exceeds limit {self.risk_limits['max_portfolio_risk']:.1%}")
            
            return {
                'recommended_shares': recommended_shares,
                'risk_amount': actual_risk,
                'position_value': position_value,
                'risk_percentage': actual_risk_pct,
                'position_percentage': position_pct,
                'warnings': warnings
            }
            
        except Exception as e:
            print(f"Error calculating position size: {e}")
            return {
                'recommended_shares': 0,
                'risk_amount': 0.0,
                'position_value': 0.0,
                'risk_percentage': 0.0,
                'warnings': [f'Calculation error: {e}']
            }
    
    async def monitor_real_time_risk(self, positions: Dict) -> Dict:
        """Real-time risk monitoring with alerts"""
        try:
            risk_status = {
                'status': 'NORMAL',  # NORMAL, WARNING, CRITICAL
                'alerts': [],
                'metrics': {},
                'recommendations': []
            }
            
            # Calculate current risk metrics
            metrics = await self.calculate_portfolio_risk_metrics(positions)
            risk_status['metrics'] = metrics
            
            # Determine overall status
            if metrics['risk_score'] > 80:
                risk_status['status'] = 'CRITICAL'
                risk_status['recommendations'].append('🚨 IMMEDIATE ACTION: Reduce position sizes or hedge exposure')
            elif metrics['risk_score'] > 60:
                risk_status['status'] = 'WARNING'
                risk_status['recommendations'].append('⚠️ CAUTION: Consider rebalancing portfolio')
            
            # Add specific alerts
            risk_status['alerts'] = metrics.get('risk_alerts', [])
            
            # Add recommendations based on risk factors
            if metrics['concentration_risk'] > 0.15:
                risk_status['recommendations'].append('📊 DIVERSIFY: Reduce large position concentrations')
            
            if metrics['correlation_risk'] > 0.6:
                risk_status['recommendations'].append('🔀 DECORRELATE: Add uncorrelated assets')
            
            if metrics['liquidity_risk'] > 0.5:
                risk_status['recommendations'].append('💧 LIQUIDITY: Focus on high-volume securities')
            
            return risk_status
            
        except Exception as e:
            print(f"Error monitoring risk: {e}")
            return {
                'status': 'ERROR',
                'alerts': [f'Risk monitoring error: {e}'],
                'metrics': {},
                'recommendations': []
            }


# Global risk engine instance
risk_engine = InstitutionalRiskEngine()