"""
Position Sizer - Kelly Criterion & Risk-Based Position Sizing
Calculates optimal position size based on win rate, risk/reward, and account size
"""

import numpy as np
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PositionSizer:
    """
    Position sizing using Kelly Criterion and risk management
    Calculates optimal position size based on:
    - Win rate
    - Average win/loss
    - Account size
    - Risk tolerance
    """
    
    def __init__(self):
        # REALISTIC RETAIL TRADING PARAMETERS (based on research)
        # Average retail options trade: ~$2,006, Median: ~$337
        # Typical account sizes: $10k-$50k for active retail traders
        self.default_account_size = 25000  # $25k default (more realistic for active traders)
        self.max_position_pct = 0.20  # Max 20% of account per trade (realistic limit)
        self.min_position_pct = 0.004  # Min 0.4% of account (~$100 minimum for $25k account)
        self.kelly_fraction = 0.5  # Use 50% of Kelly (half-Kelly for safety)
        self.risk_per_trade_pct = 0.02  # Risk 2% of account per trade
        
        # Realistic contract sizing
        self.min_contracts = 1  # Minimum 1 contract
        self.max_contracts = 20  # Maximum 20 contracts (realistic for retail)
        self.contract_rounding = [1, 5, 10, 20]  # Round to these contract counts
    
    def calculate_position_size(self, 
                                confidence: int,
                                win_rate: Optional[float] = None,
                                avg_win: Optional[float] = None,
                                avg_loss: Optional[float] = None,
                                account_size: Optional[float] = None,
                                risk_tolerance: str = 'MODERATE',
                                iv_percentile: Optional[float] = None,
                                market_regime: Optional[Dict] = None,
                                recent_performance: Optional[Dict] = None,
                                current_drawdown: Optional[float] = None) -> Dict:
        """
        Calculate optimal position size
        
        Args:
            confidence: Prediction confidence (0-100)
            win_rate: Historical win rate (0-1)
            avg_win: Average win amount ($)
            avg_loss: Average loss amount ($)
            account_size: Total account size ($)
            risk_tolerance: CONSERVATIVE, MODERATE, AGGRESSIVE
            iv_percentile: IV percentile (0-100) - adjusts size based on volatility
        
        Returns:
            Dict with position size, method, and reasoning
        """
        # Get account size
        if account_size is None:
            account_size = self.default_account_size
        
        # Get historical stats if not provided
        if win_rate is None or avg_win is None or avg_loss is None:
            stats = self._get_historical_stats()
            win_rate = stats.get('win_rate', 0.5)
            avg_win = stats.get('avg_win', 100)
            avg_loss = stats.get('avg_loss', 50)
        
        # Calculate position size using multiple methods
        kelly_size = self._kelly_criterion(win_rate, avg_win, avg_loss, account_size)
        confidence_size = self._confidence_based_size(confidence, account_size)
        risk_based_size = self._risk_based_size(account_size, risk_tolerance)
        
        # Combine methods (weighted average)
        final_size = self._combine_sizing_methods(
            kelly_size, confidence_size, risk_based_size, confidence
        )
        
        # Apply volatility adjustment (IV percentile)
        if iv_percentile is not None:
            # Low IV (0-30%) = cheaper options = can size larger
            # High IV (70-100%) = expensive options = size smaller
            if iv_percentile < 30:
                iv_multiplier = 1.2  # 20% larger when IV is low
            elif iv_percentile < 50:
                iv_multiplier = 1.0  # Normal size
            elif iv_percentile < 70:
                iv_multiplier = 0.9  # 10% smaller when IV is moderate-high
            else:  # IV >= 70%
                iv_multiplier = 0.75  # 25% smaller when IV is very high
            final_size = final_size * iv_multiplier
        
        # Apply risk tolerance adjustment
        risk_multiplier = self._get_risk_multiplier(risk_tolerance)
        final_size = final_size * risk_multiplier
        
        # Phase 2: Dynamic adjustments based on market regime and performance
        dynamic_adjustments = self._calculate_dynamic_adjustments(
            market_regime, recent_performance, current_drawdown, confidence
        )
        final_size = final_size * dynamic_adjustments['size_multiplier']
        
        # Enforce limits
        final_size = max(
            account_size * self.min_position_pct,
            min(account_size * self.max_position_pct, final_size)
        )
        
        position_pct = (final_size / account_size) * 100
        
        return {
            'position_size': round(final_size, 2),
            'position_pct': round(position_pct, 2),
            'account_size': account_size,
            'methods': {
                'kelly': round(kelly_size, 2),
                'confidence': round(confidence_size, 2),
                'risk_based': round(risk_based_size, 2)
            },
            'win_rate': win_rate,
            'risk_reward_ratio': round(avg_win / max(1, abs(avg_loss)), 2),
            'risk_tolerance': risk_tolerance,
            'reasoning': self._generate_reasoning(
                final_size, position_pct, win_rate, confidence, risk_tolerance, iv_percentile
            ),
            'dynamic_adjustments': dynamic_adjustments
        }
    
    def _kelly_criterion(self, win_rate: float, avg_win: float, 
                        avg_loss: float, account_size: float) -> float:
        """
        Calculate Kelly Criterion position size
        Kelly % = (Win Rate * Avg Win - Loss Rate * Avg Loss) / Avg Win
        
        Returns position size in dollars
        """
        if avg_win <= 0 or avg_loss <= 0:
            return account_size * 0.02  # Default 2%
        
        loss_rate = 1 - win_rate
        
        # Kelly percentage
        kelly_pct = (win_rate * avg_win - loss_rate * avg_loss) / avg_win
        
        # Use fractional Kelly (safer)
        kelly_pct = kelly_pct * self.kelly_fraction
        
        # Ensure positive
        kelly_pct = max(0, kelly_pct)
        
        # Cap at max position
        kelly_pct = min(kelly_pct, self.max_position_pct)
        
        return account_size * kelly_pct
    
    def _confidence_based_size(self, confidence: int, account_size: float) -> float:
        """
        Position size based on confidence level
        Higher confidence = larger position
        """
        # Map confidence (30-95) to position size (1%-20%)
        confidence_pct = (confidence - 30) / 65  # Normalize to 0-1
        position_pct = 0.01 + (confidence_pct * 0.19)  # 1% to 20%
        
        return account_size * position_pct
    
    def _risk_based_size(self, account_size: float, risk_tolerance: str) -> float:
        """
        Position size based on risk per trade
        Risk 2% of account per trade (default)
        """
        risk_pcts = {
            'CONSERVATIVE': 0.01,  # 1% risk
            'MODERATE': 0.02,      # 2% risk
            'AGGRESSIVE': 0.04     # 4% risk
        }
        
        risk_pct = risk_pcts.get(risk_tolerance, 0.02)
        return account_size * risk_pct
    
    def _combine_sizing_methods(self, kelly: float, confidence: float, 
                               risk: float, confidence_score: int) -> float:
        """
        Combine multiple sizing methods with weights
        """
        # Weight based on confidence
        if confidence_score >= 80:
            # High confidence: Trust Kelly more
            weights = {'kelly': 0.5, 'confidence': 0.3, 'risk': 0.2}
        elif confidence_score >= 65:
            # Medium confidence: Balanced
            weights = {'kelly': 0.4, 'confidence': 0.4, 'risk': 0.2}
        else:
            # Low confidence: Conservative
            weights = {'kelly': 0.3, 'confidence': 0.3, 'risk': 0.4}
        
        combined = (kelly * weights['kelly'] + 
                   confidence * weights['confidence'] + 
                   risk * weights['risk'])
        
        return combined
    
    def _get_risk_multiplier(self, risk_tolerance: str) -> float:
        """Get risk tolerance multiplier"""
        multipliers = {
            'CONSERVATIVE': 0.7,
            'MODERATE': 1.0,
            'AGGRESSIVE': 1.3
        }
        return multipliers.get(risk_tolerance, 1.0)
    
    def _get_historical_stats(self) -> Dict:
        """Stage A: size from Boss shadow summary, not quarantined performance_tracker."""
        try:
            from shadow_learning_engine import shadow_learning_engine
            s = shadow_learning_engine.summary()
            wr = s.get("win_rate_today")
            closed = int(s.get("closed_today") or 0)
            if wr is None or closed <= 0:
                return {"win_rate": 0.5, "avg_win": 100, "avg_loss": 50}
            # Shadow summary has W/L counts, not dollar avg win/loss — keep neutral R multiples
            return {
                "win_rate": float(wr) / 100.0 if wr > 1 else float(wr),
                "avg_win": 100,
                "avg_loss": 50,
            }
        except Exception as e:
            logger.debug(f"Shadow stats unavailable for sizing: {e}")
            return {"win_rate": 0.5, "avg_win": 100, "avg_loss": 50}
    
    def _generate_reasoning(self, size: float, pct: float, win_rate: float,
                           confidence: int, risk_tolerance: str, iv_percentile: Optional[float] = None) -> str:
        """Generate human-readable reasoning for position size"""
        reasoning_parts = []
        
        reasoning_parts.append(f"Position size: ${size:,.2f} ({pct:.1f}% of account)")
        
        if win_rate > 0.6:
            reasoning_parts.append(f"High win rate ({win_rate:.1%}) supports larger position")
        elif win_rate < 0.4:
            reasoning_parts.append(f"Low win rate ({win_rate:.1%}) suggests smaller position")
        
        if confidence >= 80:
            reasoning_parts.append(f"High confidence ({confidence}%) allows larger position")
        elif confidence < 60:
            reasoning_parts.append(f"Lower confidence ({confidence}%) requires smaller position")
        
        if iv_percentile is not None:
            if iv_percentile < 30:
                reasoning_parts.append(f"Low IV ({iv_percentile:.0f}%) - options cheap, sized larger")
            elif iv_percentile >= 70:
                reasoning_parts.append(f"High IV ({iv_percentile:.0f}%) - options expensive, sized smaller")
        
        reasoning_parts.append(f"Risk tolerance: {risk_tolerance}")
        
        return " | ".join(reasoning_parts)
    
    def _calculate_dynamic_adjustments(
        self,
        market_regime: Optional[Dict],
        recent_performance: Optional[Dict],
        current_drawdown: Optional[float],
        confidence: int
    ) -> Dict:
        """
        Phase 2: Calculate dynamic position size adjustments based on:
        - Market regime (trending vs choppy)
        - Recent performance (win rate)
        - Current drawdown
        - Volatility environment
        """
        try:
            size_multiplier = 1.0
            adjustments = []
            
            # 1. Market Regime Adjustment
            if market_regime:
                regime_type = market_regime.get('regime', 'CHOPPY')
                volatility = market_regime.get('volatility', 'NORMAL')
                
                if regime_type == 'TRENDING':
                    # Trending markets: Size larger (up to 20% increase)
                    size_multiplier *= 1.2
                    adjustments.append('Trending market: +20% size')
                elif regime_type == 'CHOPPY':
                    # Choppy markets: Size smaller (20% reduction)
                    size_multiplier *= 0.8
                    adjustments.append('Choppy market: -20% size')
                
                if volatility == 'HIGH':
                    # High volatility: Size smaller (15% reduction)
                    size_multiplier *= 0.85
                    adjustments.append('High volatility: -15% size')
                elif volatility == 'LOW':
                    # Low volatility: Size slightly larger (10% increase)
                    size_multiplier *= 1.1
                    adjustments.append('Low volatility: +10% size')
            
            # 2. Recent Performance Adjustment
            if recent_performance:
                recent_win_rate = recent_performance.get('win_rate', 0.5)
                recent_trades = recent_performance.get('total_trades', 0)
                
                if recent_trades >= 5:  # Need at least 5 trades for meaningful data
                    if recent_win_rate > 0.65:
                        # Strong recent performance: Size larger (15% increase)
                        size_multiplier *= 1.15
                        adjustments.append(f'Strong recent performance ({recent_win_rate:.1%}): +15% size')
                    elif recent_win_rate < 0.35:
                        # Poor recent performance: Size smaller (25% reduction)
                        size_multiplier *= 0.75
                        adjustments.append(f'Poor recent performance ({recent_win_rate:.1%}): -25% size')
            
            # 3. Drawdown Adjustment
            if current_drawdown is not None:
                if current_drawdown > 0.15:  # >15% drawdown
                    # Large drawdown: Size much smaller (40% reduction)
                    size_multiplier *= 0.6
                    adjustments.append(f'Large drawdown ({current_drawdown:.1%}): -40% size')
                elif current_drawdown > 0.10:  # >10% drawdown
                    # Moderate drawdown: Size smaller (20% reduction)
                    size_multiplier *= 0.8
                    adjustments.append(f'Moderate drawdown ({current_drawdown:.1%}): -20% size')
                elif current_drawdown < 0.05:  # <5% drawdown
                    # Small drawdown: Size slightly larger (10% increase)
                    size_multiplier *= 1.1
                    adjustments.append(f'Small drawdown ({current_drawdown:.1%}): +10% size')
            
            # 4. Confidence-Based Adjustment
            if confidence >= 85:
                # Very high confidence: Size larger (10% increase)
                size_multiplier *= 1.1
                adjustments.append(f'Very high confidence ({confidence}%): +10% size')
            elif confidence < 50:
                # Low confidence: Size smaller (20% reduction)
                size_multiplier *= 0.8
                adjustments.append(f'Low confidence ({confidence}%): -20% size')
            
            # Cap adjustments (don't go below 50% or above 150% of base size)
            size_multiplier = max(0.5, min(1.5, size_multiplier))
            
            return {
                'size_multiplier': round(size_multiplier, 4),
                'adjustments': adjustments,
                'final_adjustment_pct': round((size_multiplier - 1.0) * 100, 1)
            }
            
        except Exception as e:
            logger.error(f"Error calculating dynamic adjustments: {e}", exc_info=True)
            return {
                'size_multiplier': 1.0,
                'adjustments': ['Error in dynamic adjustments - using base size'],
                'final_adjustment_pct': 0.0
            }
    
    def calculate_contracts(self, position_size: float, option_price: float) -> Dict:
        """
        Calculate number of contracts from position size and option price
        Based on realistic retail trading patterns
        
        Args:
            position_size: Position size in dollars
            option_price: Option price per contract (e.g., 1.50)
        
        Returns:
            Dict with num_contracts, actual_cost, and reasoning
        """
        if option_price <= 0:
            return {
                'num_contracts': 1,
                'actual_cost': 0,
                'reasoning': 'Invalid option price - defaulting to 1 contract'
            }
        
        # Calculate raw number of contracts
        # Each contract costs: option_price * 100
        cost_per_contract = option_price * 100
        raw_contracts = position_size / cost_per_contract
        
        # Round to realistic contract counts (1, 5, 10, 20)
        # This matches how real retail traders think (not fractional contracts)
        if raw_contracts < 1:
            num_contracts = 1  # Minimum 1 contract
        elif raw_contracts < 3:
            num_contracts = 1  # Round down to 1 if less than 3
        elif raw_contracts < 7.5:
            num_contracts = 5  # Round to 5 contracts
        elif raw_contracts < 15:
            num_contracts = 10  # Round to 10 contracts
        elif raw_contracts < 20:
            num_contracts = 10  # Round down to 10 if less than 20
        else:
            num_contracts = 20  # Cap at 20 contracts (realistic max for retail)
        
        # Enforce min/max
        num_contracts = max(self.min_contracts, min(self.max_contracts, int(num_contracts)))
        
        # Calculate actual cost
        actual_cost = num_contracts * cost_per_contract
        
        # Generate reasoning
        reasoning = f"{num_contracts} contract(s) @ ${option_price:.2f} = ${actual_cost:.2f}"
        if actual_cost < position_size * 0.8:
            reasoning += f" (using {actual_cost/position_size:.0%} of allocated ${position_size:.2f})"
        
        return {
            'num_contracts': num_contracts,
            'actual_cost': round(actual_cost, 2),
            'cost_per_contract': round(cost_per_contract, 2),
            'raw_contracts': round(raw_contracts, 2),
            'reasoning': reasoning,
            'position_size_allocated': round(position_size, 2),
            'utilization_pct': round((actual_cost / position_size * 100) if position_size > 0 else 0, 1)
        }
    
    def calculate_stop_loss(self, entry_price: float, position_type: str,
                           account_size: float, position_size: float) -> Dict:
        """
        Calculate stop loss level based on risk per trade
        
        Args:
            entry_price: Entry price
            position_type: 'CALLS' or 'PUTS'
            account_size: Total account size
            position_size: Position size in dollars
        
        Returns:
            Dict with stop loss price and reasoning
        """
        # Risk 2% of account
        max_loss = account_size * self.risk_per_trade_pct
        
        # Calculate stop loss distance
        if position_type == 'CALLS':
            # For calls, stop loss is below entry
            stop_distance_pct = (max_loss / position_size) * 100
            stop_price = entry_price * (1 - stop_distance_pct / 100)
        else:  # PUTS
            # For puts, stop loss is above entry
            stop_distance_pct = (max_loss / position_size) * 100
            stop_price = entry_price * (1 + stop_distance_pct / 100)
        
        return {
            'stop_loss_price': round(stop_price, 2),
            'stop_distance_pct': round(stop_distance_pct, 2),
            'max_loss': round(max_loss, 2),
            'risk_pct': self.risk_per_trade_pct * 100
        }


# Global instance
position_sizer = PositionSizer()

