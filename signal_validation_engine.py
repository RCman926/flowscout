"""
Signal Validation Engine - Ensures all signals across the platform are consistent and properly hierarchical
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging

class SignalValidationEngine:
    """Validates and coordinates signals across the entire platform"""
    
    def __init__(self):
        self.confidence_threshold = 60  # Minimum confidence for actionable signals
        self.signal_hierarchy = {
            'MASTER': 'trading_decision_center',
            'SUPPORTING': 'symbol_selector', 
            'CONTEXT': 'live_battle',
            'BACKGROUND': 'market_intelligence'
        }
        
    def validate_signal_consistency(self, signals: Dict) -> Dict:
        """
        Cross-validate all signals and ensure consistency
        
        Args:
            signals: Dictionary containing all platform signals
            
        Returns:
            Validation report with conflicts and recommendations
        """
        validation_report = {
            'is_consistent': True,
            'conflicts': [],
            'recommendations': [],
            'master_signal': None,
            'confidence_scores': {},
            'data_quality_scores': {}
        }
        
        # Extract signals from different sources
        symbol_signal = signals.get('symbol_selector', {})
        trading_signal = signals.get('trading_decision_center', {})
        flow_signal = signals.get('live_battle', {})
        
        # Validate confidence thresholds
        for source, signal in signals.items():
            confidence = signal.get('confidence', 0)
            validation_report['confidence_scores'][source] = confidence
            
            if confidence > 0 and confidence < self.confidence_threshold:
                validation_report['conflicts'].append(
                    f"{source}: Low confidence ({confidence}%) should show NEUTRAL"
                )
                validation_report['is_consistent'] = False
        
        # Check signal alignment between symbol selector and trading center
        if symbol_signal and trading_signal:
            symbol_direction = symbol_signal.get('signal_type', 'NEUTRAL')
            trading_direction = trading_signal.get('action_recommendation', 'HOLD')
            
            # Convert trading center signals to comparable format
            trading_comparable = self._convert_trading_signal(trading_direction)
            
            if symbol_direction != 'NEUTRAL' and trading_comparable != 'NEUTRAL':
                if not self._signals_aligned(symbol_direction, trading_comparable):
                    validation_report['conflicts'].append(
                        f"Signal mismatch: Symbol shows {symbol_direction}, Trading center shows {trading_comparable}"
                    )
                    validation_report['is_consistent'] = False
        
        # Determine master signal (Trading Decision Center has authority)
        if trading_signal:
            validation_report['master_signal'] = trading_signal
        elif symbol_signal:
            validation_report['master_signal'] = symbol_signal
        
        # Generate recommendations
        if not validation_report['is_consistent']:
            validation_report['recommendations'] = self._generate_recommendations(validation_report['conflicts'])
        
        return validation_report
    
    def _convert_trading_signal(self, trading_action: str) -> str:
        """Convert trading center action to symbol selector format"""
        call_actions = ['BUY', 'STRONG_BUY', 'MAXIMUM_BUY', 'SMALL_BUY']
        put_actions = ['SELL', 'STRONG_SELL', 'MAXIMUM_SELL', 'SMALL_SELL']
        
        if trading_action in call_actions:
            return 'CALLS'
        elif trading_action in put_actions:
            return 'PUTS'
        else:
            return 'NEUTRAL'
    
    def _signals_aligned(self, symbol_signal: str, trading_signal: str) -> bool:
        """Check if signals are aligned"""
        bullish_signals = ['CALLS']
        bearish_signals = ['PUTS']
        
        if symbol_signal in bullish_signals and trading_signal in bullish_signals:
            return True
        elif symbol_signal in bearish_signals and trading_signal in bearish_signals:
            return True
        elif symbol_signal == 'NEUTRAL' or trading_signal == 'NEUTRAL':
            return True
        else:
            return False
    
    def _generate_recommendations(self, conflicts: List[str]) -> List[str]:
        """Generate recommendations to fix signal conflicts"""
        recommendations = []
        
        for conflict in conflicts:
            if "Low confidence" in conflict:
                recommendations.append("Set signal to NEUTRAL for confidence < 60%")
            elif "Signal mismatch" in conflict:
                recommendations.append("Use Trading Decision Center as master authority")
                recommendations.append("Align symbol selector with master signal")
        
        return recommendations
    
    def integrate_ml_prediction(self, ml_prediction: Dict, unified_signal: Dict) -> Dict:
        """
        Integrate ML prediction with unified signal while respecting confidence thresholds
        
        Args:
            ml_prediction: ML prediction with confidence
            unified_signal: Current unified signal
            
        Returns:
            Updated unified signal with ML integration
        """
        ml_confidence = ml_prediction.get('confidence', 0)
        ml_direction = ml_prediction.get('direction', 'NEUTRAL')
        
        # Only integrate ML if it meets confidence threshold
        if ml_confidence >= self.confidence_threshold:
            # Weight ML prediction (30%) with existing signal (70%)
            current_confidence = unified_signal.get('confidence', 50)
            
            # Calculate weighted confidence
            weighted_confidence = (current_confidence * 0.7) + (ml_confidence * 0.3)
            
            # Determine if ML and current signal agree
            current_direction = unified_signal.get('direction', 'NEUTRAL')
            
            if ml_direction == current_direction or current_direction == 'NEUTRAL':
                # Signals agree or current is neutral - boost confidence
                final_confidence = min(95, weighted_confidence * 1.1)
                final_direction = ml_direction if current_direction == 'NEUTRAL' else current_direction
            elif ml_direction == 'NEUTRAL':
                # ML is neutral - reduce confidence
                final_confidence = weighted_confidence * 0.8
                final_direction = current_direction
            else:
                # Signals conflict - average them and reduce confidence
                final_confidence = weighted_confidence * 0.6
                final_direction = 'NEUTRAL'  # Default to neutral on conflict
            
            unified_signal.update({
                'confidence': final_confidence,
                'direction': final_direction,
                'ml_integrated': True,
                'ml_confidence': ml_confidence,
                'ml_direction': ml_direction
            })
        else:
            # ML below threshold - mark as rejected
            unified_signal.update({
                'ml_integrated': False,
                'ml_confidence': ml_confidence,
                'ml_direction': ml_direction,
                'ml_rejection_reason': f'Below {self.confidence_threshold}% threshold'
            })
        
        return unified_signal

    def create_unified_signal(self, raw_signals: Dict, market_data: Dict, data_quality: Dict) -> Dict:
        """
        Create a unified signal that represents the platform's consensus
        
        Args:
            raw_signals: All platform signals
            market_data: Current market data
            data_quality: Data quality scores
            
        Returns:
            Unified signal with clear direction and confidence
        """
        # Get the master signal from trading decision center
        master_signal = raw_signals.get('trading_decision_center', {})
        
        # Get supporting signals
        symbol_signal = raw_signals.get('symbol_selector', {})
        flow_signal = raw_signals.get('live_battle', {})
        
        # Calculate weighted confidence
        master_confidence = master_signal.get('unified_confidence', 50)
        symbol_confidence = symbol_signal.get('confidence', 50)
        flow_confidence = flow_signal.get('confidence', 50)
        
        # Weight the confidences (Master = 60%, Symbol = 25%, Flow = 15%)
        weighted_confidence = (
            master_confidence * 0.60 +
            symbol_confidence * 0.25 +
            flow_confidence * 0.15
        )
        
        # Get data quality weighting
        avg_data_quality = sum(data_quality.values()) / max(len(data_quality), 1)
        quality_weight = avg_data_quality / 100  # Convert to 0-1 scale
        
        # Apply data quality penalty
        final_confidence = weighted_confidence * quality_weight
        
        # Determine unified direction
        master_action = master_signal.get('action_recommendation', 'HOLD')
        unified_direction = self._convert_trading_signal(master_action)
        
        # Apply confidence threshold
        if final_confidence < self.confidence_threshold:
            unified_direction = 'NEUTRAL'
            master_action = 'HOLD'
        
        return {
            'direction': unified_direction,
            'action': master_action,
            'confidence': final_confidence,
            'data_quality': avg_data_quality,
            'timestamp': datetime.now(),
            'signal_sources': {
                'master': master_signal.get('conviction_level', 'LOW_CONVICTION'),
                'symbol': symbol_signal.get('signal_type', 'NEUTRAL'),
                'flow': flow_signal.get('net_flow_direction', 'NEUTRAL')
            },
            'quality_breakdown': data_quality
        }

# Global instance
signal_validator = SignalValidationEngine()