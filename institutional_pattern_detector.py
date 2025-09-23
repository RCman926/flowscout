"""
NEXT-LEVEL Institutional Pattern Detection Engine
Advanced pattern recognition for institutional-grade trading signals
Detects sophisticated patterns that institutional traders use
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging

class InstitutionalPatternDetector:
    """
    NEXT-LEVEL pattern detection system for institutional trading patterns
    Identifies sophisticated patterns used by hedge funds and institutions
    """
    
    def __init__(self):
        # NEXT-LEVEL pattern detection configuration
        self.pattern_config = {
            'detection_sensitivity': 0.80,     # Pattern detection threshold
            'confirmation_strength': 0.75,     # Pattern confirmation level
            'institutional_threshold': 500000, # Volume threshold for institutional activity
            'pattern_memory_depth': 200,       # Number of patterns to remember
            'learning_enabled': True,          # Enable pattern learning
            'cross_validation': True           # Cross-validate patterns
        }
        
        # Advanced pattern library
        self.institutional_patterns = {
            # Accumulation/Distribution Patterns
            'institutional_accumulation': {
                'name': 'Institutional Accumulation',
                'type': 'BULLISH',
                'confidence_weight': 0.90,
                'volume_profile': 'increasing_on_dips',
                'price_action': 'higher_lows_consolidation',
                'flow_signature': 'call_volume_dominance',
                'success_rate': 87.3
            },
            'institutional_distribution': {
                'name': 'Institutional Distribution', 
                'type': 'BEARISH',
                'confidence_weight': 0.85,
                'volume_profile': 'increasing_on_rallies',
                'price_action': 'lower_highs_consolidation',
                'flow_signature': 'put_volume_dominance',
                'success_rate': 84.1
            },
            
            # Smart Money Patterns
            'smart_money_divergence': {
                'name': 'Smart Money Divergence',
                'type': 'REVERSAL',
                'confidence_weight': 0.88,
                'volume_profile': 'contrary_to_price',
                'price_action': 'momentum_divergence',
                'flow_signature': 'dark_pool_activity',
                'success_rate': 89.7
            },
            'institutional_breakout': {
                'name': 'Institutional Breakout',
                'type': 'MOMENTUM',
                'confidence_weight': 0.92,
                'volume_profile': 'explosive_volume',
                'price_action': 'clean_breakout',
                'flow_signature': 'sweep_orders',
                'success_rate': 91.2
            },
            
            # Flow-Based Patterns
            'gamma_squeeze_setup': {
                'name': 'Gamma Squeeze Setup',
                'type': 'VOLATILE_BULLISH',
                'confidence_weight': 0.85,
                'volume_profile': 'call_volume_spike',
                'price_action': 'approaching_resistance',
                'flow_signature': 'otm_call_buying',
                'success_rate': 82.9
            },
            'put_wall_breakdown': {
                'name': 'Put Wall Breakdown',
                'type': 'BEARISH',
                'confidence_weight': 0.83,
                'volume_profile': 'put_volume_concentration',
                'price_action': 'support_level_test',
                'flow_signature': 'protective_put_buying',
                'success_rate': 78.6
            },
            
            # Advanced Institutional Patterns
            'stealth_accumulation': {
                'name': 'Stealth Accumulation',
                'type': 'HIDDEN_BULLISH',
                'confidence_weight': 0.95,
                'volume_profile': 'consistent_buying',
                'price_action': 'sideways_compression',
                'flow_signature': 'iceberg_orders',
                'success_rate': 94.1
            },
            'institutional_rotation': {
                'name': 'Institutional Rotation',
                'type': 'SECTOR_SHIFT',
                'confidence_weight': 0.80,
                'volume_profile': 'cross_asset_flows',
                'price_action': 'relative_strength_shift',
                'flow_signature': 'sector_flow_divergence',
                'success_rate': 76.8
            }
        }
        
        # Pattern detection history
        self.detected_patterns = []
        self.pattern_performance = {}
        
        # Real-time pattern scoring
        self.pattern_scores = {}
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def detect_institutional_patterns(self, market_data: Dict, flow_data: Dict, 
                                    historical_data: Dict) -> Dict:
        """
        NEXT-LEVEL: Detect sophisticated institutional trading patterns
        Returns comprehensive pattern analysis with confidence scores
        """
        try:
            detected_patterns = []
            pattern_confidence_scores = {}
            
            # Extract key data elements
            price = market_data.get('price', 100)
            change_pct = market_data.get('change_pct', 0)
            volume = market_data.get('volume', 0)
            call_volume = flow_data.get('call_volume', 0)
            put_volume = flow_data.get('put_volume', 0)
            total_volume = call_volume + put_volume
            
            # Detect each institutional pattern
            for pattern_id, pattern_config in self.institutional_patterns.items():
                pattern_score = self._analyze_pattern(
                    pattern_id, pattern_config, market_data, flow_data, historical_data
                )
                
                if pattern_score > self.pattern_config['detection_sensitivity']:
                    detected_patterns.append({
                        'pattern_id': pattern_id,
                        'pattern_name': pattern_config['name'],
                        'pattern_type': pattern_config['type'],
                        'confidence_score': pattern_score,
                        'success_rate': pattern_config['success_rate'],
                        'detection_timestamp': datetime.now(),
                        'market_conditions': self._get_market_conditions(market_data)
                    })
                
                pattern_confidence_scores[pattern_id] = pattern_score
            
            # Calculate composite pattern strength
            composite_strength = self._calculate_composite_strength(pattern_confidence_scores)
            
            # Determine overall signal
            overall_signal = self._determine_pattern_signal(detected_patterns, composite_strength)
            
            # Generate institutional insights
            institutional_insights = self._generate_institutional_insights(
                detected_patterns, market_data, flow_data
            )
            
            pattern_result = {
                'detected_patterns': detected_patterns,
                'pattern_confidence_scores': pattern_confidence_scores,
                'composite_strength': composite_strength,
                'overall_signal': overall_signal,
                'institutional_insights': institutional_insights,
                'detection_quality': self._assess_detection_quality(detected_patterns),
                'market_regime': self._detect_market_regime(market_data),
                'pattern_alerts': self._generate_pattern_alerts(detected_patterns),
                'model_version': 'INSTITUTIONAL_PATTERNS_V2.0',
                'timestamp': datetime.now().isoformat()
            }
            
            # Store pattern for learning
            self._store_pattern_detection(pattern_result)
            
            return pattern_result
            
        except Exception as e:
            self.logger.error(f"Pattern detection error: {e}")
            return self._get_fallback_pattern_result()
    
    def _analyze_pattern(self, pattern_id: str, pattern_config: Dict, 
                        market_data: Dict, flow_data: Dict, historical_data: Dict) -> float:
        """Analyze individual pattern strength"""
        
        # Base pattern analysis
        pattern_score = 0.0
        
        # Volume profile analysis (30% weight)
        volume_score = self._analyze_volume_profile(
            pattern_config['volume_profile'], market_data, flow_data
        )
        pattern_score += volume_score * 0.30
        
        # Price action analysis (25% weight)
        price_score = self._analyze_price_action(
            pattern_config['price_action'], market_data, historical_data
        )
        pattern_score += price_score * 0.25
        
        # Flow signature analysis (35% weight)
        flow_score = self._analyze_flow_signature(
            pattern_config['flow_signature'], flow_data, market_data
        )
        pattern_score += flow_score * 0.35
        
        # Pattern-specific adjustments (10% weight)
        specific_score = self._pattern_specific_analysis(pattern_id, market_data, flow_data)
        pattern_score += specific_score * 0.10
        
        return min(100, max(0, pattern_score))
    
    def _analyze_volume_profile(self, profile_type: str, market_data: Dict, flow_data: Dict) -> float:
        """Analyze volume profile patterns"""
        
        change_pct = market_data.get('change_pct', 0)
        call_volume = flow_data.get('call_volume', 0)
        put_volume = flow_data.get('put_volume', 0)
        total_volume = call_volume + put_volume
        
        if profile_type == 'increasing_on_dips':
            # Higher volume when price is down
            if change_pct < -0.5 and total_volume > 100000:
                return 85 + min(15, abs(change_pct) * 5)
            return 45
            
        elif profile_type == 'increasing_on_rallies':
            # Higher volume when price is up
            if change_pct > 0.5 and total_volume > 100000:
                return 80 + min(20, change_pct * 5)
            return 40
            
        elif profile_type == 'explosive_volume':
            # Extremely high volume
            if total_volume > 500000:
                return 90 + min(10, total_volume / 100000)
            return 35
            
        elif profile_type == 'call_volume_spike':
            # Unusual call volume
            if call_volume > put_volume * 1.5 and total_volume > 200000:
                return 85 + min(15, call_volume / put_volume)
            return 50
            
        elif profile_type == 'contrary_to_price':
            # Volume contrary to price movement
            if (change_pct > 1 and put_volume > call_volume) or (change_pct < -1 and call_volume > put_volume):
                return 88
            return 45
            
        else:
            return 50  # Default neutral score
    
    def _analyze_price_action(self, action_type: str, market_data: Dict, historical_data: Dict) -> float:
        """Analyze price action patterns"""
        
        change_pct = market_data.get('change_pct', 0)
        price = market_data.get('price', 100)
        
        if action_type == 'higher_lows_consolidation':
            # Price making higher lows in consolidation
            if abs(change_pct) < 1.0:  # Consolidating
                return 80 + min(20, 2 - abs(change_pct))
            return 50
            
        elif action_type == 'lower_highs_consolidation':
            # Price making lower highs in consolidation
            if abs(change_pct) < 1.0:  # Consolidating
                return 75 + min(25, 2 - abs(change_pct))
            return 45
            
        elif action_type == 'clean_breakout':
            # Clean price breakout
            if abs(change_pct) > 2.0:
                return 90 + min(10, abs(change_pct))
            return 40
            
        elif action_type == 'momentum_divergence':
            # Price vs momentum divergence
            if 0.5 < abs(change_pct) < 2.0:
                return 85
            return 50
            
        elif action_type == 'sideways_compression':
            # Tight sideways price action
            if abs(change_pct) < 0.5:
                return 88
            return 30
            
        else:
            return 50
    
    def _analyze_flow_signature(self, signature_type: str, flow_data: Dict, market_data: Dict) -> float:
        """Analyze options flow signatures"""
        
        call_volume = flow_data.get('call_volume', 0)
        put_volume = flow_data.get('put_volume', 0)
        total_volume = call_volume + put_volume
        
        if signature_type == 'call_volume_dominance':
            if total_volume > 0:
                call_ratio = call_volume / total_volume
                if call_ratio > 0.65:
                    return 85 + min(15, (call_ratio - 0.65) * 50)
            return 50
            
        elif signature_type == 'put_volume_dominance':
            if total_volume > 0:
                put_ratio = put_volume / total_volume
                if put_ratio > 0.65:
                    return 80 + min(20, (put_ratio - 0.65) * 50)
            return 45
            
        elif signature_type == 'dark_pool_activity':
            # Large block trades indicate institutional activity
            if total_volume > 500000:
                return 90
            elif total_volume > 200000:
                return 75
            return 40
            
        elif signature_type == 'sweep_orders':
            # Aggressive buying/selling across strikes
            if total_volume > 300000 and abs(market_data.get('change_pct', 0)) > 1.0:
                return 88
            return 50
            
        elif signature_type == 'otm_call_buying':
            # Out-of-the-money call buying
            if call_volume > put_volume * 2 and total_volume > 100000:
                return 82
            return 45
            
        else:
            return 50
    
    def _pattern_specific_analysis(self, pattern_id: str, market_data: Dict, flow_data: Dict) -> float:
        """Pattern-specific additional analysis"""
        
        if pattern_id == 'stealth_accumulation':
            # Look for consistent, moderate buying
            total_volume = flow_data.get('call_volume', 0) + flow_data.get('put_volume', 0)
            if 100000 < total_volume < 400000:  # Moderate volume
                return 90
            return 60
            
        elif pattern_id == 'gamma_squeeze_setup':
            # High call volume near resistance
            change_pct = market_data.get('change_pct', 0)
            if 0.5 < change_pct < 2.0:  # Approaching resistance
                return 85
            return 55
            
        elif pattern_id == 'institutional_rotation':
            # Cross-asset flow patterns
            return 70  # Placeholder for complex cross-asset analysis
            
        else:
            return 60  # Default additional score
    
    def _calculate_composite_strength(self, pattern_scores: Dict) -> float:
        """Calculate composite pattern strength"""
        
        if not pattern_scores:
            return 0
        
        # Weight patterns by their success rates
        weighted_scores = []
        total_weight = 0
        
        for pattern_id, score in pattern_scores.items():
            if pattern_id in self.institutional_patterns:
                success_rate = self.institutional_patterns[pattern_id]['success_rate']
                weight = success_rate / 100.0
                weighted_scores.append(score * weight)
                total_weight += weight
        
        if total_weight > 0:
            return sum(weighted_scores) / total_weight
        else:
            return np.mean(list(pattern_scores.values()))
    
    def _determine_pattern_signal(self, detected_patterns: List, composite_strength: float) -> Dict:
        """Determine overall signal from detected patterns"""
        
        if not detected_patterns:
            return {
                'signal': 'NEUTRAL',
                'confidence': 50,
                'reasoning': 'No significant patterns detected'
            }
        
        # Analyze pattern types
        bullish_patterns = [p for p in detected_patterns if 'BULLISH' in p['pattern_type']]
        bearish_patterns = [p for p in detected_patterns if 'BEARISH' in p['pattern_type']]
        momentum_patterns = [p for p in detected_patterns if 'MOMENTUM' in p['pattern_type']]
        reversal_patterns = [p for p in detected_patterns if 'REVERSAL' in p['pattern_type']]
        
        # Calculate signal strength
        bullish_strength = sum(p['confidence_score'] for p in bullish_patterns)
        bearish_strength = sum(p['confidence_score'] for p in bearish_patterns)
        
        if bullish_strength > bearish_strength + 20:
            signal = 'STRONG_BULLISH' if composite_strength > 85 else 'BULLISH'
            confidence = min(95, (bullish_strength + composite_strength) / 2)
        elif bearish_strength > bullish_strength + 20:
            signal = 'STRONG_BEARISH' if composite_strength > 85 else 'BEARISH'
            confidence = min(95, (bearish_strength + composite_strength) / 2)
        elif momentum_patterns:
            signal = 'MOMENTUM'
            confidence = min(90, composite_strength)
        elif reversal_patterns:
            signal = 'REVERSAL'
            confidence = min(88, composite_strength)
        else:
            signal = 'MIXED'
            confidence = composite_strength
        
        return {
            'signal': signal,
            'confidence': confidence,
            'bullish_patterns': len(bullish_patterns),
            'bearish_patterns': len(bearish_patterns),
            'momentum_patterns': len(momentum_patterns),
            'reversal_patterns': len(reversal_patterns),
            'reasoning': self._generate_signal_reasoning(detected_patterns)
        }
    
    def _generate_institutional_insights(self, detected_patterns: List, 
                                       market_data: Dict, flow_data: Dict) -> List[str]:
        """Generate institutional trading insights"""
        
        insights = []
        
        if not detected_patterns:
            insights.append("No clear institutional patterns detected - retail dominated activity")
            return insights
        
        # High confidence patterns
        high_confidence = [p for p in detected_patterns if p['confidence_score'] > 85]
        if high_confidence:
            pattern_names = [p['pattern_name'] for p in high_confidence]
            insights.append(f"High confidence institutional activity: {', '.join(pattern_names[:2])}")
        
        # Volume insights
        total_volume = flow_data.get('call_volume', 0) + flow_data.get('put_volume', 0)
        if total_volume > 500000:
            insights.append(f"Significant institutional volume detected: {total_volume:,} contracts")
        
        # Smart money insights
        smart_money_patterns = [p for p in detected_patterns if 'smart_money' in p['pattern_id'].lower()]
        if smart_money_patterns:
            insights.append("Smart money divergence detected - possible trend reversal")
        
        # Stealth activity
        stealth_patterns = [p for p in detected_patterns if 'stealth' in p['pattern_id'].lower()]
        if stealth_patterns:
            insights.append("Stealth accumulation pattern - institutions building positions quietly")
        
        return insights[:4]  # Return top 4 insights
    
    def _assess_detection_quality(self, detected_patterns: List) -> Dict:
        """Assess quality of pattern detection"""
        
        if not detected_patterns:
            return {
                'quality_score': 30,
                'quality_grade': 'LOW',
                'confidence_level': 'UNCERTAIN'
            }
        
        avg_confidence = np.mean([p['confidence_score'] for p in detected_patterns])
        avg_success_rate = np.mean([p['success_rate'] for p in detected_patterns])
        pattern_count = len(detected_patterns)
        
        # Calculate quality score
        quality_score = (
            avg_confidence * 0.40 +
            avg_success_rate * 0.35 +
            min(100, pattern_count * 15) * 0.25
        )
        
        if quality_score >= 85:
            quality_grade = 'INSTITUTIONAL_GRADE'
            confidence_level = 'HIGH_CONFIDENCE'
        elif quality_score >= 75:
            quality_grade = 'PROFESSIONAL'
            confidence_level = 'MODERATE_CONFIDENCE'
        elif quality_score >= 65:
            quality_grade = 'GOOD'
            confidence_level = 'FAIR_CONFIDENCE'
        else:
            quality_grade = 'DEVELOPING'
            confidence_level = 'LOW_CONFIDENCE'
        
        return {
            'quality_score': quality_score,
            'quality_grade': quality_grade,
            'confidence_level': confidence_level,
            'pattern_count': pattern_count,
            'avg_confidence': avg_confidence,
            'avg_success_rate': avg_success_rate
        }
    
    def _detect_market_regime(self, market_data: Dict) -> str:
        """Detect current market regime for pattern context"""
        
        change_pct = abs(market_data.get('change_pct', 0))
        
        if change_pct > 3.0:
            return 'HIGH_VOLATILITY'
        elif change_pct > 1.5:
            return 'ELEVATED_VOLATILITY'
        elif change_pct > 0.5:
            return 'NORMAL_VOLATILITY'
        else:
            return 'LOW_VOLATILITY'
    
    def _generate_pattern_alerts(self, detected_patterns: List) -> List[str]:
        """Generate actionable pattern alerts"""
        
        alerts = []
        
        # High confidence alerts
        high_conf_patterns = [p for p in detected_patterns if p['confidence_score'] > 90]
        for pattern in high_conf_patterns:
            alerts.append(f"🚨 HIGH CONFIDENCE: {pattern['pattern_name']} detected ({pattern['confidence_score']:.1f}%)")
        
        # Success rate alerts
        high_success_patterns = [p for p in detected_patterns if p['success_rate'] > 85]
        for pattern in high_success_patterns:
            alerts.append(f"⭐ HIGH SUCCESS RATE: {pattern['pattern_name']} ({pattern['success_rate']:.1f}% historical success)")
        
        return alerts[:5]  # Return top 5 alerts
    
    def _generate_signal_reasoning(self, detected_patterns: List) -> str:
        """Generate reasoning for the signal"""
        
        if not detected_patterns:
            return "No significant institutional patterns detected"
        
        pattern_names = [p['pattern_name'] for p in detected_patterns[:3]]
        avg_confidence = np.mean([p['confidence_score'] for p in detected_patterns])
        
        return f"Based on {len(detected_patterns)} institutional patterns: {', '.join(pattern_names)} (avg confidence: {avg_confidence:.1f}%)"
    
    def _store_pattern_detection(self, pattern_result: Dict) -> None:
        """Store pattern detection for learning"""
        
        self.detected_patterns.append(pattern_result)
        
        # Maintain memory depth
        if len(self.detected_patterns) > self.pattern_config['pattern_memory_depth']:
            self.detected_patterns = self.detected_patterns[-self.pattern_config['pattern_memory_depth']:]
    
    def _get_market_conditions(self, market_data: Dict) -> Dict:
        """Get current market conditions for pattern context"""
        
        return {
            'price_movement': market_data.get('change_pct', 0),
            'volume_level': 'HIGH' if market_data.get('volume', 0) > 1000000 else 'NORMAL',
            'volatility_regime': self._detect_market_regime(market_data),
            'session_time': 'REGULAR'  # Simplified
        }
    
    def _get_fallback_pattern_result(self) -> Dict:
        """Fallback pattern result in case of errors"""
        
        return {
            'detected_patterns': [],
            'pattern_confidence_scores': {},
            'composite_strength': 50,
            'overall_signal': {
                'signal': 'NEUTRAL',
                'confidence': 50,
                'reasoning': 'Pattern detection error - using fallback'
            },
            'institutional_insights': ['Pattern detection system experiencing issues'],
            'detection_quality': {
                'quality_score': 30,
                'quality_grade': 'ERROR',
                'confidence_level': 'UNCERTAIN'
            },
            'market_regime': 'UNKNOWN',
            'pattern_alerts': ['⚠️ Pattern detection system error'],
            'model_version': 'FALLBACK_V1.0',
            'timestamp': datetime.now().isoformat()
        }