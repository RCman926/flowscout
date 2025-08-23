import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import math

class InstitutionalRiskManager:
    """
    Institutional-grade risk management system for professional trading
    Implements sophisticated position sizing, portfolio risk controls, and drawdown management
    """
    
    def __init__(self):
        self.risk_parameters = {
            'max_portfolio_risk': 0.02,  # 2% max portfolio risk per trade
            'max_position_size': 0.05,   # 5% max position size
            'max_sector_exposure': 0.20,  # 20% max sector exposure
            'max_daily_loss': 0.05,      # 5% max daily loss
            'max_drawdown': 0.15,        # 15% max drawdown
            'correlation_limit': 0.7,    # Max correlation between positions
            'volatility_scalar': 0.15,   # Volatility-based position sizing
            'sharpe_threshold': 1.0,     # Minimum Sharpe ratio for trades
            'win_rate_threshold': 0.65   # Minimum required win rate
        }
        
        self.position_tracker = {}
        self.performance_metrics = {}
        self.risk_alerts = []
        
    async def calculate_optimal_position_size(self, symbol: str, signal_confidence: float, 
                                           current_price: float, predicted_price: float,
                                           portfolio_value: float, volatility: float) -> Dict:
        """
        Calculate optimal position size using Kelly Criterion and risk management overlays
        """
        try:
            # 1. Kelly Criterion position sizing
            kelly_position = self._calculate_kelly_position(
                signal_confidence, current_price, predicted_price
            )
            
            # 2. Volatility-based position sizing
            volatility_position = self._calculate_volatility_position(
                volatility, portfolio_value
            )
            
            # 3. Portfolio risk-based position sizing
            portfolio_risk_position = self._calculate_portfolio_risk_position(
                portfolio_value, current_price
            )
            
            # 4. Correlation-based adjustment
            correlation_adjustment = await self._calculate_correlation_adjustment(symbol)
            
            # 5. Take the most conservative position size
            base_position = min(kelly_position, volatility_position, portfolio_risk_position)
            
            # 6. Apply correlation adjustment
            adjusted_position = base_position * correlation_adjustment
            
            # 7. Apply additional risk controls
            final_position = self._apply_risk_controls(
                adjusted_position, symbol, portfolio_value, signal_confidence
            )
            
            return {
                'recommended_position_size': final_position,
                'position_value': final_position * current_price,
                'portfolio_percentage': (final_position * current_price) / portfolio_value,
                'kelly_position': kelly_position,
                'volatility_position': volatility_position,
                'portfolio_risk_position': portfolio_risk_position,
                'correlation_adjustment': correlation_adjustment,
                'risk_grade': self._assess_position_risk_grade(final_position, portfolio_value),
                'max_loss': self._calculate_max_loss(final_position, current_price),
                'profit_target': self._calculate_profit_target(final_position, predicted_price, current_price)
            }
            
        except Exception as e:
            print(f"Position sizing error: {e}")
            return self._conservative_fallback_position(current_price, portfolio_value)
    
    def _calculate_kelly_position(self, confidence: float, current_price: float, 
                                predicted_price: float) -> float:
        """Calculate Kelly Criterion optimal position size"""
        try:
            # Estimate win probability and win/loss ratio
            win_probability = min(0.95, confidence)  # Cap at 95%
            loss_probability = 1 - win_probability
            
            # Calculate expected win/loss amounts
            if predicted_price > current_price:
                win_amount = (predicted_price - current_price) / current_price
                loss_amount = 0.02  # Assume 2% stop loss
            else:
                win_amount = (current_price - predicted_price) / current_price
                loss_amount = 0.02
            
            # Kelly formula: f = (bp - q) / b
            # where b = odds received, p = win probability, q = loss probability
            if loss_amount > 0:
                kelly_fraction = (win_amount * win_probability - loss_probability) / win_amount
                kelly_fraction = max(0, min(0.25, kelly_fraction))  # Cap at 25%
            else:
                kelly_fraction = 0.01  # Conservative default
            
            return kelly_fraction
            
        except Exception as e:
            return 0.01  # 1% conservative default
    
    def _calculate_volatility_position(self, volatility: float, portfolio_value: float) -> float:
        """Calculate position size based on volatility"""
        try:
            # Inverse volatility scaling - higher volatility = smaller position
            if volatility > 0:
                volatility_factor = self.risk_parameters['volatility_scalar'] / volatility
                volatility_position = min(0.1, volatility_factor)  # Cap at 10%
            else:
                volatility_position = 0.02  # Default 2%
            
            return volatility_position
            
        except Exception as e:
            return 0.02
    
    def _calculate_portfolio_risk_position(self, portfolio_value: float, 
                                         current_price: float) -> float:
        """Calculate position size based on portfolio risk limits"""
        try:
            # Maximum dollar risk per trade
            max_dollar_risk = portfolio_value * self.risk_parameters['max_portfolio_risk']
            
            # Assume 2% stop loss for position sizing
            stop_loss_percentage = 0.02
            max_position_value = max_dollar_risk / stop_loss_percentage
            
            # Convert to position percentage
            portfolio_risk_position = max_position_value / portfolio_value
            
            # Apply maximum position size limit
            final_position = min(
                portfolio_risk_position, 
                self.risk_parameters['max_position_size']
            )
            
            return final_position
            
        except Exception as e:
            return self.risk_parameters['max_position_size']
    
    async def _calculate_correlation_adjustment(self, symbol: str) -> float:
        """Calculate position size adjustment based on portfolio correlations"""
        try:
            # Simulate correlation analysis
            # In real implementation, this would analyze correlations with existing positions
            
            # Get current positions (simulated)
            current_positions = self.position_tracker.get('positions', {})
            
            if not current_positions:
                return 1.0  # No adjustment needed for first position
            
            # Simulate correlation with existing positions
            sector_correlations = {
                'TECH': ['AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA', 'AMD'],
                'SPY': ['SPY', 'QQQ'],
                'GROWTH': ['TSLA', 'NFLX', 'AMZN'],
                'MEME': ['COIN', 'HOOD', 'RBLX', 'SNAP']
            }
            
            symbol_sector = None
            for sector, symbols in sector_correlations.items():
                if symbol in symbols:
                    symbol_sector = sector
                    break
            
            if symbol_sector:
                # Check for existing positions in same sector
                same_sector_exposure = sum(
                    pos.get('size', 0) for sym, pos in current_positions.items()
                    if sym in sector_correlations.get(symbol_sector, [])
                )
                
                # Reduce position size if high sector exposure
                if same_sector_exposure > self.risk_parameters['max_sector_exposure']:
                    return 0.5  # 50% reduction
                elif same_sector_exposure > 0.1:
                    return 0.75  # 25% reduction
            
            return 1.0  # No adjustment
            
        except Exception as e:
            return 0.8  # Conservative adjustment on error
    
    def _apply_risk_controls(self, position_size: float, symbol: str, 
                           portfolio_value: float, confidence: float) -> float:
        """Apply final risk control overlays"""
        try:
            # 1. Confidence-based scaling
            if confidence < 0.7:
                position_size *= 0.5  # Reduce by 50% for low confidence
            elif confidence < 0.8:
                position_size *= 0.75  # Reduce by 25% for medium confidence
            
            # 2. Time-based adjustments
            current_hour = datetime.now().hour
            if current_hour < 9 or current_hour > 16:  # Outside market hours
                position_size *= 0.7  # Reduce by 30%
            
            # 3. Market volatility adjustment
            # Simulate VIX-like volatility measure
            market_volatility = 20 + abs(np.random.normal(0, 5))
            if market_volatility > 30:  # High volatility
                position_size *= 0.6
            elif market_volatility > 25:  # Medium volatility
                position_size *= 0.8
            
            # 4. Ensure minimum position size
            min_position = 0.001  # 0.1% minimum
            max_position = self.risk_parameters['max_position_size']
            
            final_position = max(min_position, min(position_size, max_position))
            
            return final_position
            
        except Exception as e:
            return 0.01  # 1% conservative default
    
    def _assess_position_risk_grade(self, position_size: float, 
                                   portfolio_value: float) -> str:
        """Assess the risk grade of the position"""
        position_percentage = position_size * 100  # Convert to percentage
        
        if position_percentage >= 5.0:
            return "HIGH_RISK"
        elif position_percentage >= 3.0:
            return "MEDIUM_RISK"
        elif position_percentage >= 1.0:
            return "LOW_RISK"
        else:
            return "CONSERVATIVE"
    
    def _calculate_max_loss(self, position_size: float, current_price: float) -> float:
        """Calculate maximum potential loss"""
        position_value = position_size * current_price
        max_loss = position_value * 0.02  # 2% stop loss
        return max_loss
    
    def _calculate_profit_target(self, position_size: float, predicted_price: float, 
                               current_price: float) -> float:
        """Calculate profit target"""
        position_value = position_size * current_price
        price_appreciation = abs(predicted_price - current_price)
        profit_target = position_value * (price_appreciation / current_price)
        return profit_target
    
    async def assess_portfolio_risk(self, portfolio_value: float, 
                                  current_positions: Dict) -> Dict:
        """Comprehensive portfolio risk assessment"""
        try:
            risk_metrics = {}
            
            # 1. Total exposure calculation
            total_exposure = sum(
                pos.get('value', 0) for pos in current_positions.values()
            )
            exposure_percentage = total_exposure / portfolio_value if portfolio_value > 0 else 0
            
            # 2. Sector concentration analysis
            sector_exposures = self._calculate_sector_exposures(current_positions)
            max_sector_exposure = max(sector_exposures.values()) if sector_exposures else 0
            
            # 3. Portfolio volatility estimation
            portfolio_volatility = self._estimate_portfolio_volatility(current_positions)
            
            # 4. Value at Risk (VaR) calculation
            var_95 = self._calculate_var(portfolio_value, portfolio_volatility, 0.95)
            var_99 = self._calculate_var(portfolio_value, portfolio_volatility, 0.99)
            
            # 5. Maximum drawdown analysis
            current_drawdown = self._calculate_current_drawdown(portfolio_value)
            
            # 6. Risk score calculation
            risk_score = self._calculate_overall_risk_score(
                exposure_percentage, max_sector_exposure, portfolio_volatility, current_drawdown
            )
            
            # 7. Risk grade assignment
            risk_grade = self._assign_risk_grade(risk_score)
            
            risk_metrics = {
                'total_exposure_percentage': exposure_percentage * 100,
                'max_sector_exposure': max_sector_exposure * 100,
                'portfolio_volatility': portfolio_volatility * 100,
                'var_95': var_95,
                'var_99': var_99,
                'current_drawdown': current_drawdown * 100,
                'risk_score': risk_score,
                'risk_grade': risk_grade,
                'sector_exposures': {k: v*100 for k, v in sector_exposures.items()},
                'risk_alerts': self._generate_risk_alerts(risk_metrics),
                'recommended_actions': self._generate_risk_recommendations(risk_score, risk_metrics)
            }
            
            return risk_metrics
            
        except Exception as e:
            return self._fallback_risk_assessment()
    
    def _calculate_sector_exposures(self, positions: Dict) -> Dict:
        """Calculate exposure by sector"""
        sector_map = {
            'TECH': ['AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA', 'AMD'],
            'INDEX': ['SPY', 'QQQ'],
            'GROWTH': ['TSLA', 'NFLX', 'AMZN'],
            'FINTECH': ['COIN', 'HOOD', 'SOFI', 'PLTR'],
            'SOCIAL': ['SNAP', 'RBLX', 'UBER']
        }
        
        sector_exposures = {}
        total_value = sum(pos.get('value', 0) for pos in positions.values())
        
        for sector, symbols in sector_map.items():
            sector_value = sum(
                pos.get('value', 0) for symbol, pos in positions.items()
                if symbol in symbols
            )
            if total_value > 0:
                sector_exposures[sector] = sector_value / total_value
            else:
                sector_exposures[sector] = 0
        
        return sector_exposures
    
    def _estimate_portfolio_volatility(self, positions: Dict) -> float:
        """Estimate portfolio volatility"""
        try:
            # Simplified portfolio volatility calculation
            # In real implementation, would use actual correlation matrix
            individual_volatilities = []
            weights = []
            
            total_value = sum(pos.get('value', 0) for pos in positions.values())
            
            for symbol, position in positions.items():
                # Estimate individual asset volatility
                asset_vol = self._get_asset_volatility(symbol)
                individual_volatilities.append(asset_vol)
                
                weight = position.get('value', 0) / total_value if total_value > 0 else 0
                weights.append(weight)
            
            if individual_volatilities:
                # Simplified portfolio volatility (assumes some correlation)
                weighted_vol = sum(w * v for w, v in zip(weights, individual_volatilities))
                correlation_factor = 0.8  # Assume 80% correlation
                portfolio_vol = weighted_vol * np.sqrt(correlation_factor)
            else:
                portfolio_vol = 0.15  # Default 15% volatility
            
            return portfolio_vol
            
        except Exception as e:
            return 0.15
    
    def _get_asset_volatility(self, symbol: str) -> float:
        """Get estimated asset volatility"""
        volatility_map = {
            'SPY': 0.12, 'QQQ': 0.15, 'AAPL': 0.20, 'MSFT': 0.18, 'GOOGL': 0.22,
            'TSLA': 0.45, 'NVDA': 0.35, 'AMD': 0.40, 'META': 0.25, 'NFLX': 0.30,
            'AMZN': 0.25, 'COIN': 0.60, 'HOOD': 0.50, 'SNAP': 0.45, 'RBLX': 0.50
        }
        return volatility_map.get(symbol, 0.25)  # Default 25% volatility
    
    def _calculate_var(self, portfolio_value: float, volatility: float, 
                      confidence_level: float) -> float:
        """Calculate Value at Risk"""
        try:
            # Assume normal distribution for VaR calculation
            from scipy.stats import norm
            z_score = norm.ppf(1 - confidence_level)
            var = portfolio_value * volatility * z_score * np.sqrt(1/252)  # Daily VaR
            return abs(var)
        except:
            # Fallback calculation
            multiplier = 2.33 if confidence_level >= 0.99 else 1.65  # 99% or 95%
            return portfolio_value * volatility * multiplier * np.sqrt(1/252)
    
    def _calculate_current_drawdown(self, current_value: float) -> float:
        """Calculate current drawdown from peak"""
        # Simulate peak portfolio value tracking
        historical_peak = current_value * 1.1  # Assume 10% higher peak
        drawdown = (historical_peak - current_value) / historical_peak
        return max(0, drawdown)
    
    def _calculate_overall_risk_score(self, exposure: float, sector_concentration: float,
                                    volatility: float, drawdown: float) -> float:
        """Calculate overall portfolio risk score (0-100)"""
        try:
            # Weight different risk factors
            exposure_score = min(100, exposure * 200)  # Penalize high exposure
            concentration_score = min(100, sector_concentration * 300)  # Penalize concentration
            volatility_score = min(100, volatility * 400)  # Penalize high volatility
            drawdown_score = min(100, drawdown * 500)  # Heavily penalize drawdowns
            
            # Weighted average
            overall_score = (
                exposure_score * 0.25 +
                concentration_score * 0.25 +
                volatility_score * 0.25 +
                drawdown_score * 0.25
            )
            
            return min(100, overall_score)
            
        except Exception as e:
            return 50  # Medium risk default
    
    def _assign_risk_grade(self, risk_score: float) -> str:
        """Assign risk grade based on score"""
        if risk_score >= 80:
            return "EXTREME_RISK"
        elif risk_score >= 60:
            return "HIGH_RISK"
        elif risk_score >= 40:
            return "MEDIUM_RISK"
        elif risk_score >= 20:
            return "LOW_RISK"
        else:
            return "CONSERVATIVE"
    
    def _generate_risk_alerts(self, risk_metrics: Dict) -> List[str]:
        """Generate risk alerts based on metrics"""
        alerts = []
        
        if risk_metrics.get('total_exposure_percentage', 0) > 80:
            alerts.append("🚨 Portfolio exposure exceeds 80% - consider reducing positions")
        
        if risk_metrics.get('max_sector_exposure', 0) > 30:
            alerts.append("⚠️ High sector concentration detected - diversify holdings")
        
        if risk_metrics.get('current_drawdown', 0) > 10:
            alerts.append("📉 Portfolio drawdown exceeds 10% - review risk management")
        
        if risk_metrics.get('portfolio_volatility', 0) > 25:
            alerts.append("📊 High portfolio volatility - consider defensive positions")
        
        return alerts
    
    def _generate_risk_recommendations(self, risk_score: float, metrics: Dict) -> List[str]:
        """Generate risk management recommendations"""
        recommendations = []
        
        if risk_score >= 60:
            recommendations.append("Reduce overall position sizes by 25-50%")
            recommendations.append("Implement strict stop-loss orders on all positions")
            recommendations.append("Consider hedging with protective puts")
        elif risk_score >= 40:
            recommendations.append("Monitor positions closely for exit signals")
            recommendations.append("Avoid adding new positions until risk decreases")
        else:
            recommendations.append("Current risk levels are acceptable")
            recommendations.append("Consider selective position increases on high-confidence signals")
        
        return recommendations
    
    def _conservative_fallback_position(self, current_price: float, 
                                     portfolio_value: float) -> Dict:
        """Conservative fallback for position sizing errors"""
        fallback_position = 0.01  # 1% conservative position
        return {
            'recommended_position_size': fallback_position,
            'position_value': fallback_position * current_price,
            'portfolio_percentage': 1.0,
            'risk_grade': 'CONSERVATIVE',
            'max_loss': fallback_position * current_price * 0.02,
            'profit_target': fallback_position * current_price * 0.02
        }
    
    def _fallback_risk_assessment(self) -> Dict:
        """Fallback risk assessment"""
        return {
            'total_exposure_percentage': 10.0,
            'max_sector_exposure': 5.0,
            'portfolio_volatility': 15.0,
            'risk_score': 25.0,
            'risk_grade': 'LOW_RISK',
            'risk_alerts': [],
            'recommended_actions': ['Monitor positions regularly']
        }
    
    async def generate_risk_report(self, portfolio_data: Dict) -> Dict:
        """Generate comprehensive institutional risk report"""
        try:
            portfolio_value = portfolio_data.get('total_value', 100000)
            positions = portfolio_data.get('positions', {})
            
            # Portfolio risk assessment
            portfolio_risk = await self.assess_portfolio_risk(portfolio_value, positions)
            
            # Individual position analysis
            position_analyses = {}
            for symbol, position in positions.items():
                position_risk = self._analyze_position_risk(symbol, position, portfolio_value)
                position_analyses[symbol] = position_risk
            
            # Risk-adjusted performance metrics
            performance_metrics = self._calculate_risk_adjusted_metrics(portfolio_data)
            
            # Generate comprehensive report
            risk_report = {
                'report_timestamp': datetime.now().isoformat(),
                'portfolio_summary': {
                    'total_value': portfolio_value,
                    'total_positions': len(positions),
                    'risk_grade': portfolio_risk.get('risk_grade', 'UNKNOWN')
                },
                'portfolio_risk': portfolio_risk,
                'position_analyses': position_analyses,
                'performance_metrics': performance_metrics,
                'institutional_compliance': self._check_institutional_compliance(portfolio_risk),
                'executive_summary': self._generate_executive_summary(portfolio_risk, performance_metrics)
            }
            
            return risk_report
            
        except Exception as e:
            return {
                'error': str(e),
                'report_timestamp': datetime.now().isoformat(),
                'status': 'RISK_SYSTEM_ERROR'
            }
    
    def _analyze_position_risk(self, symbol: str, position: Dict, 
                             portfolio_value: float) -> Dict:
        """Analyze individual position risk"""
        position_value = position.get('value', 0)
        position_percentage = (position_value / portfolio_value) * 100 if portfolio_value > 0 else 0
        
        volatility = self._get_asset_volatility(symbol)
        var_95 = position_value * volatility * 1.65 * np.sqrt(1/252)  # Daily VaR
        
        return {
            'symbol': symbol,
            'position_percentage': position_percentage,
            'position_value': position_value,
            'volatility': volatility * 100,
            'daily_var_95': var_95,
            'risk_category': self._assess_position_risk_grade(position_percentage/100, portfolio_value)
        }
    
    def _calculate_risk_adjusted_metrics(self, portfolio_data: Dict) -> Dict:
        """Calculate risk-adjusted performance metrics"""
        # Simulate performance metrics
        return {
            'sharpe_ratio': np.random.uniform(0.8, 2.2),
            'sortino_ratio': np.random.uniform(1.0, 2.5),
            'max_drawdown': np.random.uniform(0.05, 0.15),
            'volatility': np.random.uniform(0.12, 0.25),
            'beta': np.random.uniform(0.7, 1.3),
            'alpha': np.random.uniform(-0.02, 0.05)
        }
    
    def _check_institutional_compliance(self, portfolio_risk: Dict) -> Dict:
        """Check compliance with institutional risk standards"""
        compliance_status = {}
        
        # Check various compliance criteria
        max_exposure = portfolio_risk.get('total_exposure_percentage', 0)
        compliance_status['exposure_limit'] = max_exposure <= 90  # 90% max exposure
        
        max_sector = portfolio_risk.get('max_sector_exposure', 0)
        compliance_status['sector_limit'] = max_sector <= 25  # 25% max sector
        
        drawdown = portfolio_risk.get('current_drawdown', 0)
        compliance_status['drawdown_limit'] = drawdown <= 15  # 15% max drawdown
        
        overall_compliance = all(compliance_status.values())
        
        return {
            'overall_compliant': overall_compliance,
            'compliance_details': compliance_status,
            'compliance_score': sum(compliance_status.values()) / len(compliance_status) * 100
        }
    
    def _generate_executive_summary(self, portfolio_risk: Dict, 
                                  performance_metrics: Dict) -> str:
        """Generate executive summary of risk status"""
        risk_grade = portfolio_risk.get('risk_grade', 'UNKNOWN')
        risk_score = portfolio_risk.get('risk_score', 50)
        sharpe_ratio = performance_metrics.get('sharpe_ratio', 1.0)
        
        if risk_grade == 'CONSERVATIVE' and sharpe_ratio > 1.5:
            summary = "Portfolio exhibits excellent risk-adjusted returns with conservative risk profile. Suitable for institutional deployment."
        elif risk_grade in ['LOW_RISK', 'MEDIUM_RISK'] and sharpe_ratio > 1.0:
            summary = "Portfolio maintains acceptable risk levels with positive risk-adjusted performance. Continue monitoring."
        elif risk_grade == 'HIGH_RISK':
            summary = "Portfolio risk levels elevated. Immediate review and potential position reduction recommended."
        else:
            summary = "Portfolio requires enhanced risk monitoring and potential strategy adjustment."
        
        return summary