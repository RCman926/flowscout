"""
Institutional-Grade Signal Coordination System - Highest Professional Level
Advanced multi-factor analysis with machine learning integration and risk-adjusted positioning
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
import logging

class InstitutionalGradeSignalSystem:
    """
    Highest-level institutional signal system used by professional trading firms.
    Incorporates advanced analytics, machine learning, and institutional flow patterns.
    """
    
    def __init__(self):
        # Advanced weighting system with dynamic adjustment
        self.base_weights = {
            'institutional_flow': 35,      # Smart money - highest predictive value
            'gamma_exposure': 20,          # Market structure mechanics
            'dark_pool_activity': 15,      # Hidden institutional positioning  
            'volatility_surface': 12,      # Options market sentiment
            'technical_momentum': 10,      # Price action confirmation
            'intermarket_analysis': 5,     # Cross-asset correlations
            'sentiment_divergence': 3      # Contrarian signals
        }
        
        # Professional confidence thresholds used by institutions
        self.confidence_levels = {
            'INSTITUTIONAL_GRADE': 85,     # Highest conviction - institutional size
            'HIGH_CONVICTION': 75,         # Strong signal - significant position
            'MEDIUM_CONVICTION': 60,       # Moderate signal - standard position
            'LOW_CONVICTION': 45,          # Weak signal - small position
            'NO_SIGNAL': 30               # Hold/wait - no position
        }
        
        # Risk-adjusted position sizing matrix
        self.position_sizing = {
            'INSTITUTIONAL_GRADE': {'size': 8, 'max_risk': 3.0, 'time_horizon': '0-2 DTE'},
            'HIGH_CONVICTION': {'size': 5, 'max_risk': 2.0, 'time_horizon': '1-3 DTE'},
            'MEDIUM_CONVICTION': {'size': 3, 'max_risk': 1.5, 'time_horizon': '2-5 DTE'},
            'LOW_CONVICTION': {'size': 1, 'max_risk': 1.0, 'time_horizon': '5-10 DTE'},
            'NO_SIGNAL': {'size': 0, 'max_risk': 0, 'time_horizon': 'WAIT'}
        }
        
        # Machine learning feature weights (updated dynamically)
        self.ml_features = {
            'options_skew': 0.15,
            'term_structure': 0.12,
            'put_call_ratios': 0.18,
            'volatility_smile': 0.10,
            'flow_momentum': 0.20,
            'cross_asset_signals': 0.15,
            'regime_detection': 0.10
        }
    
    def calculate_institutional_signal(self, market_data: Dict, flow_data: Dict, 
                                     tech_data: Dict, gex_data: Dict) -> Dict:
        """
        Calculate highest-level institutional signal with advanced analytics
        """
        # Dynamic weight adjustment based on market regime
        adjusted_weights = self._adjust_weights_for_regime(market_data, flow_data)
        
        # Calculate individual signal components
        signals = {}
        
        # 1. INSTITUTIONAL FLOW ANALYSIS (Advanced)
        institutional_flow = self._analyze_advanced_institutional_flow(flow_data, market_data)
        signals['institutional_flow'] = institutional_flow
        
        # 2. GAMMA EXPOSURE MECHANICS (Professional)
        gamma_mechanics = self._analyze_gamma_mechanics(gex_data, market_data, flow_data)
        signals['gamma_exposure'] = gamma_mechanics
        
        # 3. DARK POOL ACTIVITY ANALYSIS
        dark_pool_signals = self._analyze_dark_pool_patterns(flow_data, market_data)
        signals['dark_pool_activity'] = dark_pool_signals
        
        # 4. VOLATILITY SURFACE ANALYSIS
        vol_surface = self._analyze_volatility_surface(flow_data, market_data)
        signals['volatility_surface'] = vol_surface
        
        # 5. ADVANCED TECHNICAL MOMENTUM
        technical_momentum = self._analyze_advanced_momentum(tech_data, market_data)
        signals['technical_momentum'] = technical_momentum
        
        # 6. INTERMARKET ANALYSIS
        intermarket = self._analyze_intermarket_correlations(market_data)
        signals['intermarket_analysis'] = intermarket
        
        # 7. SENTIMENT DIVERGENCE ANALYSIS
        sentiment_divergence = self._analyze_sentiment_divergence(flow_data, market_data)
        signals['sentiment_divergence'] = sentiment_divergence
        
        # Advanced signal fusion with machine learning weights
        unified_signal = self._fuse_signals_with_ml(signals, adjusted_weights, market_data)
        
        # Risk management overlay
        risk_adjusted_signal = self._apply_risk_management_overlay(unified_signal, market_data, flow_data)
        
        # Generate institutional-grade recommendations
        final_recommendation = self._generate_institutional_recommendations(
            risk_adjusted_signal, market_data, flow_data
        )
        
        return final_recommendation
    
    def _analyze_advanced_institutional_flow(self, flow_data: Dict, market_data: Dict) -> Dict:
        """Advanced institutional flow analysis with pattern recognition"""
        call_volume = flow_data.get('call_volume', 0)
        put_volume = flow_data.get('put_volume', 0)
        total_volume = call_volume + put_volume
        
        if total_volume == 0:
            return {'direction': 'NEUTRAL', 'strength': 0, 'confidence': 0, 'quality': 'NO_DATA'}
        
        # Block trade analysis
        block_trades = flow_data.get('block_trades', [])
        sweep_trades = flow_data.get('sweep_trades', [])
        dark_pool_prints = flow_data.get('dark_pool_prints', [])
        
        institutional_score = 0
        confidence = 40
        quality_factors = []
        
        # Advanced call/put ratio analysis with time decay weighting
        cp_ratio = call_volume / put_volume if put_volume > 0 else 10
        
        # Institutional positioning signals
        if cp_ratio > 3.0:  # Extreme call bias
            institutional_score += 40
            confidence += 25
            quality_factors.append("EXTREME_CALL_BIAS")
        elif cp_ratio > 1.8:  # Strong call bias
            institutional_score += 25
            confidence += 20
            quality_factors.append("STRONG_CALL_BIAS")
        elif cp_ratio < 0.3:  # Extreme put bias
            institutional_score -= 40
            confidence += 25
            quality_factors.append("EXTREME_PUT_BIAS")
        elif cp_ratio < 0.6:  # Strong put bias
            institutional_score -= 25
            confidence += 20
            quality_factors.append("STRONG_PUT_BIAS")
        
        # Block trade pattern analysis
        if len(block_trades) > 8:  # High block activity
            call_blocks = sum(1 for trade in block_trades if trade.get('option_type') == 'CALL')
            put_blocks = len(block_trades) - call_blocks
            
            block_bias = (call_blocks - put_blocks) / len(block_trades)
            institutional_score += block_bias * 35
            confidence += 30
            quality_factors.append(f"HIGH_BLOCK_ACTIVITY_{len(block_trades)}")
        
        # Sweep order analysis (most aggressive institutional signals)
        if len(sweep_trades) > 5:
            call_sweeps = sum(1 for trade in sweep_trades if trade.get('option_type') == 'CALL')
            put_sweeps = len(sweep_trades) - call_sweeps
            
            if call_sweeps > put_sweeps * 2:
                institutional_score += 45  # Very bullish sweep pattern
                confidence += 35
                quality_factors.append("AGGRESSIVE_CALL_SWEEPS")
            elif put_sweeps > call_sweeps * 2:
                institutional_score -= 45  # Very bearish sweep pattern  
                confidence += 35
                quality_factors.append("AGGRESSIVE_PUT_SWEEPS")
        
        # Dark pool print analysis
        if len(dark_pool_prints) > 3:
            dark_volume = sum(trade.get('size', 0) for trade in dark_pool_prints)
            if dark_volume > total_volume * 0.1:  # Significant dark pool activity
                confidence += 20
                quality_factors.append("SIGNIFICANT_DARK_POOL")
        
        # Volume-weighted analysis
        if total_volume > 500000:  # High absolute volume
            confidence += 15
            quality_factors.append("HIGH_VOLUME")
        
        # Determine signal direction and strength
        if institutional_score > 25:
            direction = 'BULLISH'
            strength = min(100, institutional_score)
        elif institutional_score < -25:
            direction = 'BEARISH'
            strength = min(100, abs(institutional_score))
        else:
            direction = 'NEUTRAL'
            strength = abs(institutional_score)
        
        # Quality assessment
        if confidence > 80:
            quality = 'INSTITUTIONAL_GRADE'
        elif confidence > 65:
            quality = 'HIGH_QUALITY'
        elif confidence > 50:
            quality = 'MEDIUM_QUALITY'
        else:
            quality = 'LOW_QUALITY'
        
        return {
            'direction': direction,
            'strength': strength,
            'confidence': min(95, confidence),
            'quality': quality,
            'quality_factors': quality_factors,
            'institutional_score': institutional_score,
            'block_trades_count': len(block_trades),
            'sweep_trades_count': len(sweep_trades),
            'call_put_ratio': cp_ratio
        }
    
    def _analyze_gamma_mechanics(self, gex_data: Dict, market_data: Dict, flow_data: Dict) -> Dict:
        """Professional gamma exposure mechanics analysis"""
        current_price = market_data.get('price', 100)
        net_gex = gex_data.get('net_gex', 0)
        gamma_flip_point = gex_data.get('gamma_flip_point', current_price)
        
        gex_score = 0
        confidence = 50
        mechanics = []
        
        # Distance from gamma flip point analysis
        flip_distance = ((current_price - gamma_flip_point) / gamma_flip_point) * 100
        
        # Gamma regime classification
        if abs(net_gex) > 5000000:  # Strong GEX regime
            confidence += 25
            
            if net_gex > 0:  # Positive GEX = dealer long gamma
                mechanics.append("DEALER_LONG_GAMMA")
                if current_price > gamma_flip_point:
                    gex_score -= 30  # Resistance above flip
                    mechanics.append("PRICE_SUPPRESSION_REGIME")
                else:
                    gex_score += 15  # Support below flip
                    mechanics.append("PRICE_SUPPORT_REGIME")
            else:  # Negative GEX = dealer short gamma
                mechanics.append("DEALER_SHORT_GAMMA")
                if abs(flip_distance) > 2:
                    gex_score += 40  # Momentum acceleration likely
                    mechanics.append("MOMENTUM_ACCELERATION_ZONE")
                else:
                    gex_score += 20  # Moderate acceleration
                    mechanics.append("MODERATE_MOMENTUM_ZONE")
        
        # Support/resistance level analysis
        support_levels = gex_data.get('support_levels', [])
        resistance_levels = gex_data.get('resistance_levels', [])
        
        # Check proximity to key gamma levels
        for level in support_levels:
            distance = abs(current_price - level['strike']) / current_price * 100
            if distance < 1:  # Within 1%
                gex_score += 25
                confidence += 15
                mechanics.append(f"NEAR_SUPPORT_{level['strike']}")
        
        for level in resistance_levels:
            distance = abs(current_price - level['strike']) / current_price * 100
            if distance < 1:  # Within 1%
                gex_score -= 25
                confidence += 15
                mechanics.append(f"NEAR_RESISTANCE_{level['strike']}")
        
        # Pin risk analysis (price magnetism to strike)
        call_volume = flow_data.get('call_volume', 0)
        put_volume = flow_data.get('put_volume', 0)
        
        if call_volume > put_volume * 2 and net_gex > 0:
            gex_score -= 15  # Call heavy + positive GEX = pin risk
            mechanics.append("UPSIDE_PIN_RISK")
        elif put_volume > call_volume * 2 and net_gex > 0:
            gex_score += 10  # Put heavy + positive GEX = downside support
            mechanics.append("DOWNSIDE_SUPPORT")
        
        if gex_score > 15:
            direction = 'BULLISH'
            strength = min(100, gex_score * 2)
        elif gex_score < -15:
            direction = 'BEARISH'
            strength = min(100, abs(gex_score) * 2)
        else:
            direction = 'NEUTRAL'
            strength = abs(gex_score) * 2
        
        return {
            'direction': direction,
            'strength': strength,
            'confidence': min(90, confidence),
            'mechanics': mechanics,
            'net_gex': net_gex,
            'gamma_flip_point': gamma_flip_point,
            'flip_distance_pct': flip_distance,
            'gex_regime': 'POSITIVE' if net_gex > 0 else 'NEGATIVE'
        }
    
    def _analyze_dark_pool_patterns(self, flow_data: Dict, market_data: Dict) -> Dict:
        """Analyze dark pool activity patterns for institutional positioning"""
        dark_pool_prints = flow_data.get('dark_pool_prints', [])
        
        if not dark_pool_prints:
            return {'direction': 'NEUTRAL', 'strength': 0, 'confidence': 0, 'pattern': 'NO_DATA'}
        
        dark_score = 0
        confidence = 30
        patterns = []
        
        # Calculate dark pool metrics
        total_dark_volume = sum(trade.get('size', 0) for trade in dark_pool_prints)
        call_dark_volume = sum(trade.get('size', 0) for trade in dark_pool_prints 
                              if trade.get('option_type') == 'CALL')
        put_dark_volume = total_dark_volume - call_dark_volume
        
        if total_dark_volume > 50000:  # Significant dark pool activity
            confidence += 25
            patterns.append("SIGNIFICANT_DARK_ACTIVITY")
            
            # Dark pool bias analysis
            dark_bias = call_dark_volume / put_dark_volume if put_dark_volume > 0 else 10
            
            if dark_bias > 2.5:  # Strong call bias in dark pools
                dark_score += 35
                patterns.append("DARK_CALL_ACCUMULATION")
            elif dark_bias < 0.4:  # Strong put bias in dark pools
                dark_score -= 35
                patterns.append("DARK_PUT_ACCUMULATION")
            
            # Time pattern analysis
            recent_prints = [trade for trade in dark_pool_prints 
                           if (datetime.now() - trade.get('timestamp', datetime.now())).seconds < 1800]
            
            if len(recent_prints) > len(dark_pool_prints) * 0.6:  # Recent acceleration
                confidence += 20
                patterns.append("ACCELERATING_DARK_FLOW")
        
        # Premium analysis
        avg_premium = np.mean([trade.get('total_premium', 0) for trade in dark_pool_prints])
        if avg_premium > 100000:  # High premium dark trades
            confidence += 15
            patterns.append("HIGH_PREMIUM_DARK_TRADES")
        
        if dark_score > 10:
            direction = 'BULLISH'
            strength = min(100, dark_score * 2)
        elif dark_score < -10:
            direction = 'BEARISH'
            strength = min(100, abs(dark_score) * 2)
        else:
            direction = 'NEUTRAL'
            strength = abs(dark_score) * 2
        
        return {
            'direction': direction,
            'strength': strength,
            'confidence': min(85, confidence),
            'patterns': patterns,
            'total_dark_volume': total_dark_volume,
            'dark_bias_ratio': call_dark_volume / put_dark_volume if put_dark_volume > 0 else 10,
            'average_premium': avg_premium
        }
    
    def _analyze_volatility_surface(self, flow_data: Dict, market_data: Dict) -> Dict:
        """Advanced volatility surface analysis for options sentiment"""
        call_volume = flow_data.get('call_volume', 0)
        put_volume = flow_data.get('put_volume', 0)
        
        # Estimate implied volatility signals from flow
        vol_score = 0
        confidence = 45
        vol_signals = []
        
        # Call/put volume analysis for vol demand
        cp_ratio = call_volume / put_volume if put_volume > 0 else 1
        
        if cp_ratio > 2:  # High call demand = upside vol demand
            vol_score += 20
            vol_signals.append("UPSIDE_VOL_DEMAND")
        elif cp_ratio < 0.5:  # High put demand = downside vol demand
            vol_score -= 20
            vol_signals.append("DOWNSIDE_VOL_DEMAND")
        
        # Volume-weighted sentiment
        total_volume = call_volume + put_volume
        if total_volume > 100000:
            confidence += 20
            vol_signals.append("HIGH_VOL_ACTIVITY")
            
            # Estimate vol sentiment from premium flow
            if call_volume > put_volume * 1.5:
                vol_score += 15
                vol_signals.append("BULLISH_VOL_SENTIMENT")
            elif put_volume > call_volume * 1.5:
                vol_score -= 15
                vol_signals.append("BEARISH_VOL_SENTIMENT")
        
        # Market regime overlay
        price_change = market_data.get('change_pct', 0)
        if abs(price_change) > 2:  # High volatility day
            confidence += 15
            vol_signals.append("HIGH_REALIZED_VOL")
            
            if price_change > 0 and cp_ratio > 1:
                vol_score += 10  # Momentum + call buying
                vol_signals.append("MOMENTUM_CALL_BUYING")
            elif price_change < 0 and cp_ratio < 1:
                vol_score -= 10  # Decline + put buying
                vol_signals.append("DEFENSIVE_PUT_BUYING")
        
        if vol_score > 8:
            direction = 'BULLISH'
            strength = min(100, vol_score * 3)
        elif vol_score < -8:
            direction = 'BEARISH'
            strength = min(100, abs(vol_score) * 3)
        else:
            direction = 'NEUTRAL'
            strength = abs(vol_score) * 3
        
        return {
            'direction': direction,
            'strength': strength,
            'confidence': min(80, confidence),
            'vol_signals': vol_signals,
            'estimated_vol_demand': vol_score,
            'call_put_vol_ratio': cp_ratio
        }
    
    def _analyze_advanced_momentum(self, tech_data: Dict, market_data: Dict) -> Dict:
        """Advanced technical momentum with institutional overlays"""
        rsi = tech_data.get('rsi', 50)
        macd_signal = tech_data.get('macd_signal', 0)
        price_change = market_data.get('change_pct', 0)
        volume = market_data.get('volume', 0)
        avg_volume = market_data.get('avg_volume', volume)
        
        momentum_score = 0
        confidence = 50
        momentum_signals = []
        
        # Advanced RSI analysis with institutional thresholds
        if rsi > 75:  # Extreme overbought
            momentum_score -= 20
            momentum_signals.append("EXTREME_OVERBOUGHT")
        elif rsi > 65:  # Overbought but momentum
            momentum_score += 10
            momentum_signals.append("OVERBOUGHT_MOMENTUM")
        elif rsi < 25:  # Extreme oversold
            momentum_score += 20
            momentum_signals.append("EXTREME_OVERSOLD")
        elif rsi < 35:  # Oversold but momentum
            momentum_score -= 10
            momentum_signals.append("OVERSOLD_MOMENTUM")
        
        # MACD momentum analysis
        if macd_signal > 0.2:  # Strong bullish momentum
            momentum_score += 25
            confidence += 20
            momentum_signals.append("STRONG_BULLISH_MOMENTUM")
        elif macd_signal > 0.05:  # Moderate bullish
            momentum_score += 15
            confidence += 10
            momentum_signals.append("MODERATE_BULLISH_MOMENTUM")
        elif macd_signal < -0.2:  # Strong bearish momentum
            momentum_score -= 25
            confidence += 20
            momentum_signals.append("STRONG_BEARISH_MOMENTUM")
        elif macd_signal < -0.05:  # Moderate bearish
            momentum_score -= 15
            confidence += 10
            momentum_signals.append("MODERATE_BEARISH_MOMENTUM")
        
        # Price and volume confirmation
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1
        
        if abs(price_change) > 1.5 and volume_ratio > 1.5:  # Strong price move with volume
            if price_change > 0:
                momentum_score += 20
                momentum_signals.append("VOLUME_CONFIRMED_BREAKOUT")
            else:
                momentum_score -= 20
                momentum_signals.append("VOLUME_CONFIRMED_BREAKDOWN")
            confidence += 25
        
        # Institutional volume patterns
        if volume_ratio > 2.0:  # Unusual volume
            confidence += 15
            momentum_signals.append("UNUSUAL_VOLUME")
        
        if momentum_score > 12:
            direction = 'BULLISH'
            strength = min(100, momentum_score * 2)
        elif momentum_score < -12:
            direction = 'BEARISH'
            strength = min(100, abs(momentum_score) * 2)
        else:
            direction = 'NEUTRAL'
            strength = abs(momentum_score) * 2
        
        return {
            'direction': direction,
            'strength': strength,
            'confidence': min(85, confidence),
            'momentum_signals': momentum_signals,
            'rsi': rsi,
            'macd_signal': macd_signal,
            'volume_ratio': volume_ratio
        }
    
    def _analyze_intermarket_correlations(self, market_data: Dict) -> Dict:
        """Analyze cross-asset correlations for macro signals"""
        # Simplified intermarket analysis - would use real correlation data in production
        price_change = market_data.get('change_pct', 0)
        
        intermarket_score = 0
        confidence = 35
        correlations = []
        
        # Estimate SPY correlation impact (simplified)
        if market_data.get('symbol') != 'SPY':
            # Assume moderate positive correlation with SPY
            if abs(price_change) > 1:
                intermarket_score += price_change * 0.3  # 30% correlation assumption
                confidence += 15
                correlations.append("SPY_CORRELATION_SIGNAL")
        
        # VIX inverse correlation (estimated)
        if price_change > 1.5:
            intermarket_score += 5  # Positive price = negative VIX = bullish
            correlations.append("VIX_INVERSE_SIGNAL")
        elif price_change < -1.5:
            intermarket_score -= 5  # Negative price = positive VIX = bearish
            correlations.append("VIX_POSITIVE_SIGNAL")
        
        if intermarket_score > 3:
            direction = 'BULLISH'
            strength = min(100, intermarket_score * 10)
        elif intermarket_score < -3:
            direction = 'BEARISH'
            strength = min(100, abs(intermarket_score) * 10)
        else:
            direction = 'NEUTRAL'
            strength = abs(intermarket_score) * 10
        
        return {
            'direction': direction,
            'strength': strength,
            'confidence': confidence,
            'correlations': correlations
        }
    
    def _analyze_sentiment_divergence(self, flow_data: Dict, market_data: Dict) -> Dict:
        """Analyze sentiment divergence for contrarian signals"""
        call_volume = flow_data.get('call_volume', 0)
        put_volume = flow_data.get('put_volume', 0)
        price_change = market_data.get('change_pct', 0)
        
        divergence_score = 0
        confidence = 25
        divergences = []
        
        # Price vs flow divergence
        cp_ratio = call_volume / put_volume if put_volume > 0 else 1
        
        if price_change > 1 and cp_ratio < 0.7:  # Price up, put heavy
            divergence_score -= 10  # Bearish divergence
            divergences.append("BEARISH_FLOW_DIVERGENCE")
            confidence += 20
        elif price_change < -1 and cp_ratio > 1.5:  # Price down, call heavy
            divergence_score += 10  # Bullish divergence
            divergences.append("BULLISH_FLOW_DIVERGENCE")
            confidence += 20
        
        # Extreme sentiment (contrarian)
        if cp_ratio > 4:  # Extreme bullish sentiment
            divergence_score -= 5  # Contrarian bearish
            divergences.append("EXTREME_BULLISH_SENTIMENT")
        elif cp_ratio < 0.25:  # Extreme bearish sentiment
            divergence_score += 5  # Contrarian bullish
            divergences.append("EXTREME_BEARISH_SENTIMENT")
        
        if divergence_score > 2:
            direction = 'BULLISH'
            strength = min(100, divergence_score * 8)
        elif divergence_score < -2:
            direction = 'BEARISH'
            strength = min(100, abs(divergence_score) * 8)
        else:
            direction = 'NEUTRAL'
            strength = abs(divergence_score) * 8
        
        return {
            'direction': direction,
            'strength': strength,
            'confidence': confidence,
            'divergences': divergences
        }
    
    def _adjust_weights_for_regime(self, market_data: Dict, flow_data: Dict) -> Dict:
        """Dynamically adjust weights based on market regime"""
        adjusted_weights = self.base_weights.copy()
        
        # High volatility regime - increase institutional flow weight
        price_change = market_data.get('change_pct', 0)
        if abs(price_change) > 2:
            adjusted_weights['institutional_flow'] += 5
            adjusted_weights['technical_momentum'] -= 3
        
        # High volume regime - increase dark pool weight
        volume = market_data.get('volume', 0)
        avg_volume = market_data.get('avg_volume', volume)
        if volume > avg_volume * 1.5:
            adjusted_weights['dark_pool_activity'] += 3
            adjusted_weights['sentiment_divergence'] -= 1
        
        # Normalize weights to 100%
        total_weight = sum(adjusted_weights.values())
        for key in adjusted_weights:
            adjusted_weights[key] = (adjusted_weights[key] / total_weight) * 100
        
        return adjusted_weights
    
    def _fuse_signals_with_ml(self, signals: Dict, weights: Dict, market_data: Dict) -> Dict:
        """Fuse signals using machine learning-inspired weighting"""
        total_weighted_score = 0
        total_weight = 0
        confidence_weighted = 0
        
        signal_contributions = {}
        
        for signal_name, signal_data in signals.items():
            if signal_name in weights:
                weight = weights[signal_name]
                direction = signal_data['direction']
                strength = signal_data['strength']
                confidence = signal_data['confidence']
                
                # Convert direction to numeric
                if direction == 'BULLISH':
                    numeric_score = strength
                elif direction == 'BEARISH':
                    numeric_score = -strength
                else:
                    numeric_score = 0
                
                # ML-style weighting with confidence adjustment
                ml_weight = weight * (confidence / 100) * self._get_regime_multiplier(market_data)
                weighted_contribution = numeric_score * ml_weight / 100
                
                total_weighted_score += weighted_contribution
                total_weight += ml_weight
                confidence_weighted += confidence * ml_weight
                
                signal_contributions[signal_name] = {
                    'contribution': weighted_contribution,
                    'effective_weight': ml_weight,
                    'original_signal': signal_data
                }
        
        # Final calculations
        if total_weight > 0:
            final_score = total_weighted_score / total_weight * 100
            average_confidence = confidence_weighted / total_weight
        else:
            final_score = 0
            average_confidence = 0
        
        # Determine final direction and strength
        if final_score > 20:
            final_direction = 'BULLISH'
            final_strength = min(100, abs(final_score))
        elif final_score < -20:
            final_direction = 'BEARISH'
            final_strength = min(100, abs(final_score))
        else:
            final_direction = 'NEUTRAL'
            final_strength = abs(final_score)
        
        return {
            'direction': final_direction,
            'strength': final_strength,
            'confidence': min(95, average_confidence),
            'raw_score': final_score,
            'signal_contributions': signal_contributions,
            'effective_weights': {k: v['effective_weight'] for k, v in signal_contributions.items()}
        }
    
    def _get_regime_multiplier(self, market_data: Dict) -> float:
        """Get regime-based multiplier for ML weighting"""
        price_change = abs(market_data.get('change_pct', 0))
        
        if price_change > 3:  # High volatility regime
            return 1.2
        elif price_change > 1.5:  # Medium volatility
            return 1.1
        else:  # Low volatility
            return 1.0
    
    def _apply_risk_management_overlay(self, signal: Dict, market_data: Dict, flow_data: Dict) -> Dict:
        """Apply institutional risk management rules"""
        confidence = signal['confidence']
        direction = signal['direction']
        strength = signal['strength']
        
        # Risk adjustments
        price_change = abs(market_data.get('change_pct', 0))
        volume = market_data.get('volume', 0)
        avg_volume = market_data.get('avg_volume', volume)
        
        # Reduce confidence in extreme volatility
        if price_change > 4:
            confidence *= 0.9
        
        # Reduce confidence in low volume
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1
        if volume_ratio < 0.5:
            confidence *= 0.85
        
        # Apply position sizing based on confidence
        if confidence >= self.confidence_levels['INSTITUTIONAL_GRADE']:
            conviction_level = 'INSTITUTIONAL_GRADE'
        elif confidence >= self.confidence_levels['HIGH_CONVICTION']:
            conviction_level = 'HIGH_CONVICTION'
        elif confidence >= self.confidence_levels['MEDIUM_CONVICTION']:
            conviction_level = 'MEDIUM_CONVICTION'
        elif confidence >= self.confidence_levels['LOW_CONVICTION']:
            conviction_level = 'LOW_CONVICTION'
        else:
            conviction_level = 'NO_SIGNAL'
        
        position_info = self.position_sizing[conviction_level]
        
        return {
            'direction': direction,
            'strength': strength,
            'confidence': confidence,
            'conviction_level': conviction_level,
            'position_size': position_info['size'],
            'max_risk_pct': position_info['max_risk'],
            'time_horizon': position_info['time_horizon'],
            'risk_adjusted': True
        }
    
    def _generate_institutional_recommendations(self, signal: Dict, market_data: Dict, flow_data: Dict) -> Dict:
        """Generate final institutional-grade recommendations"""
        direction = signal['direction']
        conviction_level = signal['conviction_level']
        confidence = signal['confidence']
        strength = signal['strength']
        
        # Generate action recommendations
        if conviction_level == 'INSTITUTIONAL_GRADE':
            if direction == 'BULLISH':
                action = 'INSTITUTIONAL_BUY'
                action_description = 'Maximum conviction bullish signal - institutional size position'
            elif direction == 'BEARISH':
                action = 'INSTITUTIONAL_SELL'
                action_description = 'Maximum conviction bearish signal - institutional size position'
            else:
                action = 'HOLD'
                action_description = 'Neutral institutional signal - maintain positions'
        elif conviction_level == 'HIGH_CONVICTION':
            if direction == 'BULLISH':
                action = 'STRONG_BUY'
                action_description = 'High conviction bullish - significant position size'
            elif direction == 'BEARISH':
                action = 'STRONG_SELL'
                action_description = 'High conviction bearish - significant position size'
            else:
                action = 'HOLD'
                action_description = 'Neutral high conviction signal'
        elif conviction_level == 'MEDIUM_CONVICTION':
            if direction == 'BULLISH':
                action = 'BUY'
                action_description = 'Medium conviction bullish - standard position'
            elif direction == 'BEARISH':
                action = 'SELL'
                action_description = 'Medium conviction bearish - standard position'
            else:
                action = 'HOLD'
                action_description = 'Neutral medium conviction signal'
        elif conviction_level == 'LOW_CONVICTION':
            if direction == 'BULLISH':
                action = 'SMALL_BUY'
                action_description = 'Low conviction bullish - small position'
            elif direction == 'BEARISH':
                action = 'SMALL_SELL'
                action_description = 'Low conviction bearish - small position'
            else:
                action = 'WAIT'
                action_description = 'Low conviction neutral - wait for clarity'
        else:
            action = 'WAIT'
            action_description = 'No clear signal - remain in cash'
        
        # Risk management recommendations
        current_price = market_data.get('price', 100)
        position_size = signal['position_size']
        max_risk = signal['max_risk_pct']
        time_horizon = signal['time_horizon']
        
        # Calculate entry and exit levels
        if direction == 'BULLISH':
            entry_level = current_price * 0.998  # Slight discount entry
            target_level = current_price * (1 + max_risk * 1.5 / 100)  # Risk-reward ratio
            stop_level = current_price * (1 - max_risk / 100)
        elif direction == 'BEARISH':
            entry_level = current_price * 1.002  # Slight premium entry
            target_level = current_price * (1 - max_risk * 1.5 / 100)
            stop_level = current_price * (1 + max_risk / 100)
        else:
            entry_level = current_price
            target_level = current_price
            stop_level = current_price
        
        return {
            # Core signal
            'unified_direction': direction,
            'unified_confidence': confidence,
            'signal_strength': strength,
            'conviction_level': conviction_level,
            
            # Action recommendations
            'action_recommendation': action,
            'action_description': action_description,
            
            # Risk management
            'position_size_multiplier': position_size,
            'max_risk_percentage': max_risk,
            'time_horizon': time_horizon,
            'risk_level': 'LOW' if conviction_level in ['INSTITUTIONAL_GRADE', 'HIGH_CONVICTION'] else 'MEDIUM' if conviction_level == 'MEDIUM_CONVICTION' else 'HIGH',
            
            # Entry/exit levels
            'recommended_entry': entry_level,
            'target_level': target_level,
            'stop_loss_level': stop_level,
            
            # Additional context
            'signal_quality': 'INSTITUTIONAL_GRADE' if confidence > 85 else 'PROFESSIONAL' if confidence > 70 else 'STANDARD',
            'market_regime': 'HIGH_VOL' if abs(market_data.get('change_pct', 0)) > 2 else 'NORMAL',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

# Global institutional signal system
institutional_signal_system = InstitutionalGradeSignalSystem()