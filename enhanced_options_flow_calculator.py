"""
Enhanced Options Flow Calculator
Advanced options flow analysis with sophisticated volume weighting and time decay considerations
SYNCHRONOUS implementation for institutional-grade accuracy
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import pandas as pd
from dataclasses import dataclass
import math

@dataclass
class FlowAnalysisResult:
    """Comprehensive options flow analysis result"""
    symbol: str
    total_call_volume: int
    total_put_volume: int
    weighted_call_dominance: float  # Volume-weighted call percentage
    weighted_put_dominance: float   # Volume-weighted put percentage
    flow_intensity_score: int       # 0-100 intensity score
    time_decay_adjusted_ratio: float # Time-decay adjusted put/call ratio
    unusual_activity_flags: List[str]
    confidence_score: int           # Calculation confidence level
    dominant_expiration: str        # Most significant expiration
    flow_trend: str                 # BULLISH, BEARISH, NEUTRAL
    institutional_bias: str         # CALLS, PUTS, BALANCED
    calculation_timestamp: datetime
    
@dataclass  
class ExpirationFlowData:
    """Flow data for individual expiration"""
    expiration_date: str
    days_to_expiry: int
    call_volume: int
    put_volume: int
    call_open_interest: int
    put_open_interest: int
    time_decay_weight: float
    volume_weight: float
    significance_score: float

class EnhancedOptionsFlowCalculator:
    """
    Institutional-grade options flow calculator with advanced analytics
    Implements sophisticated volume weighting and time decay considerations
    """
    
    def __init__(self):
        self.flow_history = {}  # Symbol -> List[FlowAnalysisResult]
        self.volume_baselines = {}  # Historical volume baselines
        self.calculation_config = {
            'min_volume_threshold': 100,        # Minimum volume to consider
            'unusual_volume_multiplier': 3.0,   # 3x normal = unusual
            'time_decay_base': 0.95,            # Daily decay factor
            'max_dte_weight': 45,               # Maximum days for full weight
            'volume_concentration_threshold': 0.6,  # 60% volume concentration
            'institutional_volume_threshold': 10000,  # Large institutional trades
            'flow_intensity_max_volume': 1000000,    # Normalize intensity against this
            'confidence_min_sample_size': 5,    # Minimum expirations for high confidence
        }
        
        self.calculation_stats = {
            'total_calculations': 0,
            'high_confidence_calculations': 0,
            'avg_calculation_time_ms': 0.0,
            'unusual_activity_detected': 0
        }
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def calculate_enhanced_flow(self, symbol: str, options_data: Dict) -> FlowAnalysisResult:
        """
        Primary enhanced flow calculation method
        Returns sophisticated flow analysis with institutional-grade accuracy
        """
        calc_start = time.time()
        self.calculation_stats['total_calculations'] += 1
        
        try:
            # 1. Parse and validate options data
            expiration_data = self._parse_options_data(symbol, options_data)
            
            if not expiration_data:
                return self._create_fallback_result(symbol, "No valid expiration data")
            
            # 2. Calculate time decay weights for each expiration
            for exp_data in expiration_data:
                exp_data.time_decay_weight = self._calculate_time_decay_weight(exp_data.days_to_expiry)
            
            # 3. Calculate volume weights based on significance
            self._calculate_volume_weights(expiration_data)
            
            # 4. Calculate enhanced call/put volumes with weighting
            weighted_calls, weighted_puts = self._calculate_weighted_volumes(expiration_data)
            
            # 5. Calculate time-decay adjusted ratios
            time_adjusted_ratio = self._calculate_time_adjusted_ratio(expiration_data)
            
            # 6. Analyze flow intensity and institutional bias
            flow_intensity = self._calculate_flow_intensity(expiration_data)
            institutional_bias = self._analyze_institutional_bias(expiration_data)
            
            # 7. Detect unusual activity patterns
            unusual_flags = self._detect_unusual_activity(symbol, expiration_data)
            
            # 8. Determine dominant expiration and flow trend
            dominant_exp = self._find_dominant_expiration(expiration_data)
            flow_trend = self._determine_flow_trend(expiration_data, weighted_calls, weighted_puts)
            
            # 9. Calculate confidence score
            confidence_score = self._calculate_flow_confidence(expiration_data, unusual_flags)
            
            # 10. Calculate final weighted dominance percentages
            total_weighted_volume = weighted_calls + weighted_puts
            if total_weighted_volume > 0:
                weighted_call_dominance = (weighted_calls / total_weighted_volume) * 100
                weighted_put_dominance = (weighted_puts / total_weighted_volume) * 100
            else:
                weighted_call_dominance = 50.0
                weighted_put_dominance = 50.0
            
            # Create comprehensive result
            result = FlowAnalysisResult(
                symbol=symbol,
                total_call_volume=int(sum(exp.call_volume for exp in expiration_data)),
                total_put_volume=int(sum(exp.put_volume for exp in expiration_data)),
                weighted_call_dominance=round(weighted_call_dominance, 2),
                weighted_put_dominance=round(weighted_put_dominance, 2),
                flow_intensity_score=flow_intensity,
                time_decay_adjusted_ratio=time_adjusted_ratio,
                unusual_activity_flags=unusual_flags,
                confidence_score=confidence_score,
                dominant_expiration=dominant_exp,
                flow_trend=flow_trend,
                institutional_bias=institutional_bias,
                calculation_timestamp=datetime.now()
            )
            
            # Store result and update stats
            self._store_flow_result(symbol, result)
            self._update_calculation_stats(calc_start, confidence_score, unusual_flags)
            
            # Enhanced logging with key metrics
            self.logger.info(
                f"🎯 ENHANCED FLOW {symbol}: {weighted_call_dominance:.1f}% calls, "
                f"{weighted_put_dominance:.1f}% puts, Intensity: {flow_intensity}%, "
                f"Confidence: {confidence_score}%, Trend: {flow_trend}, "
                f"Bias: {institutional_bias}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Enhanced flow calculation failed for {symbol}: {e}")
            return self._create_fallback_result(symbol, f"Calculation error: {str(e)}")
    
    def _parse_options_data(self, symbol: str, options_data: Dict) -> List[ExpirationFlowData]:
        """Parse and validate options data into structured format"""
        expiration_data = []
        
        try:
            # Handle different data formats
            if 'analysis' in options_data and isinstance(options_data['analysis'], list):
                # Format: {analysis: [{expiration: ..., call_volume: ..., put_volume: ...}, ...]}
                for exp_item in options_data['analysis']:
                    if not isinstance(exp_item, dict):
                        continue
                    
                    exp_data = self._parse_expiration_item(exp_item)
                    if exp_data and exp_data.call_volume > 0 or exp_data.put_volume > 0:
                        expiration_data.append(exp_data)
            
            elif 'call_volume' in options_data and 'put_volume' in options_data:
                # Format: {call_volume: 123, put_volume: 456} - single aggregated data
                total_calls = self._safe_int_convert(options_data['call_volume'])
                total_puts = self._safe_int_convert(options_data['put_volume'])
                
                if total_calls > 0 or total_puts > 0:
                    # Create synthetic expiration data
                    exp_data = ExpirationFlowData(
                        expiration_date='aggregated',
                        days_to_expiry=1,  # Assume near-term
                        call_volume=total_calls,
                        put_volume=total_puts,
                        call_open_interest=0,
                        put_open_interest=0,
                        time_decay_weight=1.0,
                        volume_weight=1.0,
                        significance_score=100.0
                    )
                    expiration_data.append(exp_data)
            
            # Filter by minimum volume threshold
            min_threshold = self.calculation_config['min_volume_threshold']
            expiration_data = [
                exp for exp in expiration_data 
                if (exp.call_volume + exp.put_volume) >= min_threshold
            ]
            
            return expiration_data
            
        except Exception as e:
            self.logger.warning(f"Error parsing options data for {symbol}: {e}")
            return []
    
    def _parse_expiration_item(self, exp_item: Dict) -> Optional[ExpirationFlowData]:
        """Parse individual expiration item"""
        try:
            expiration_date = exp_item.get('expiration', 'unknown')
            call_volume = self._safe_int_convert(exp_item.get('call_volume', 0))
            put_volume = self._safe_int_convert(exp_item.get('put_volume', 0))
            call_oi = self._safe_int_convert(exp_item.get('call_open_interest', 0))
            put_oi = self._safe_int_convert(exp_item.get('put_open_interest', 0))
            
            # Calculate days to expiry
            days_to_expiry = self._calculate_days_to_expiry(expiration_date)
            
            return ExpirationFlowData(
                expiration_date=expiration_date,
                days_to_expiry=days_to_expiry,
                call_volume=call_volume,
                put_volume=put_volume,
                call_open_interest=call_oi,
                put_open_interest=put_oi,
                time_decay_weight=0.0,  # Will be calculated later
                volume_weight=0.0,     # Will be calculated later
                significance_score=0.0  # Will be calculated later
            )
            
        except Exception as e:
            self.logger.warning(f"Error parsing expiration item: {e}")
            return None
    
    def _calculate_days_to_expiry(self, expiration_date: str) -> int:
        """Calculate days to expiry from expiration date string"""
        try:
            if expiration_date in ['aggregated', 'unknown']:
                return 1
            
            # Try different date formats
            date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%Y%m%d']
            
            for fmt in date_formats:
                try:
                    exp_dt = datetime.strptime(expiration_date, fmt)
                    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    days_diff = (exp_dt - today).days
                    return max(0, days_diff)
                except ValueError:
                    continue
            
            # If parsing fails, return default
            return 1
            
        except Exception:
            return 1
    
    def _calculate_time_decay_weight(self, days_to_expiry: int) -> float:
        """Calculate time decay weight - closer expirations have higher weight"""
        try:
            max_dte = self.calculation_config['max_dte_weight']
            decay_base = self.calculation_config['time_decay_base']
            
            if days_to_expiry <= 0:
                return 1.0  # Same day expiration gets full weight
            elif days_to_expiry >= max_dte:
                return 0.1  # Far out expirations get minimal weight
            else:
                # Exponential decay: weight = decay_base ^ days_to_expiry
                weight = decay_base ** days_to_expiry
                return max(0.1, weight)  # Minimum 10% weight
                
        except Exception:
            return 0.5  # Default moderate weight
    
    def _calculate_volume_weights(self, expiration_data: List[ExpirationFlowData]):
        """Calculate volume weights based on total volume significance"""
        try:
            if not expiration_data:
                return
            
            # Calculate total volumes for normalization
            total_all_volume = sum(exp.call_volume + exp.put_volume for exp in expiration_data)
            
            if total_all_volume == 0:
                for exp in expiration_data:
                    exp.volume_weight = 0.0
                    exp.significance_score = 0.0
                return
            
            # Calculate weights and significance scores
            for exp in expiration_data:
                exp_total_volume = exp.call_volume + exp.put_volume
                
                # Volume weight: proportion of total volume
                exp.volume_weight = exp_total_volume / total_all_volume
                
                # Significance score: combination of volume weight and time decay weight
                exp.significance_score = (exp.volume_weight * 0.7 + exp.time_decay_weight * 0.3) * 100
                
                # Cap significance at 100
                exp.significance_score = min(100.0, exp.significance_score)
                
        except Exception as e:
            self.logger.warning(f"Error calculating volume weights: {e}")
            # Set default weights
            for exp in expiration_data:
                exp.volume_weight = 1.0 / len(expiration_data)
                exp.significance_score = 50.0
    
    def _calculate_weighted_volumes(self, expiration_data: List[ExpirationFlowData]) -> Tuple[float, float]:
        """Calculate sophisticated weighted call and put volumes"""
        try:
            weighted_calls = 0.0
            weighted_puts = 0.0
            
            for exp in expiration_data:
                # Combined weight: time decay * volume significance
                combined_weight = exp.time_decay_weight * exp.volume_weight
                
                # Apply weights to volumes
                weighted_calls += exp.call_volume * combined_weight
                weighted_puts += exp.put_volume * combined_weight
            
            return weighted_calls, weighted_puts
            
        except Exception as e:
            self.logger.warning(f"Error calculating weighted volumes: {e}")
            # Fallback to simple totals
            total_calls = sum(exp.call_volume for exp in expiration_data)
            total_puts = sum(exp.put_volume for exp in expiration_data)
            return float(total_calls), float(total_puts)
    
    def _calculate_time_adjusted_ratio(self, expiration_data: List[ExpirationFlowData]) -> float:
        """Calculate time-decay adjusted put/call ratio"""
        try:
            time_weighted_calls = 0.0
            time_weighted_puts = 0.0
            
            for exp in expiration_data:
                weight = exp.time_decay_weight
                time_weighted_calls += exp.call_volume * weight
                time_weighted_puts += exp.put_volume * weight
            
            if time_weighted_calls > 0:
                return time_weighted_puts / time_weighted_calls
            else:
                return 1.0  # Neutral ratio if no call volume
                
        except Exception as e:
            self.logger.warning(f"Error calculating time adjusted ratio: {e}")
            return 1.0
    
    def _calculate_flow_intensity(self, expiration_data: List[ExpirationFlowData]) -> int:
        """Calculate flow intensity score (0-100)"""
        try:
            total_volume = sum(exp.call_volume + exp.put_volume for exp in expiration_data)
            max_volume = self.calculation_config['flow_intensity_max_volume']
            
            # Base intensity from volume
            base_intensity = min(100, (total_volume / max_volume) * 100)
            
            # Boost for concentration in near-term expirations
            near_term_volume = sum(
                exp.call_volume + exp.put_volume 
                for exp in expiration_data 
                if exp.days_to_expiry <= 7
            )
            
            concentration_boost = 0
            if total_volume > 0:
                concentration_ratio = near_term_volume / total_volume
                concentration_threshold = self.calculation_config['volume_concentration_threshold']
                
                if concentration_ratio > concentration_threshold:
                    concentration_boost = (concentration_ratio - concentration_threshold) * 50
            
            final_intensity = min(100, base_intensity + concentration_boost)
            return int(final_intensity)
            
        except Exception as e:
            self.logger.warning(f"Error calculating flow intensity: {e}")
            return 50  # Default moderate intensity
    
    def _analyze_institutional_bias(self, expiration_data: List[ExpirationFlowData]) -> str:
        """Analyze institutional bias based on large volume patterns"""
        try:
            institutional_threshold = self.calculation_config['institutional_volume_threshold']
            
            institutional_calls = 0
            institutional_puts = 0
            
            for exp in expiration_data:
                # Count volume that exceeds institutional threshold
                if exp.call_volume >= institutional_threshold:
                    institutional_calls += exp.call_volume
                if exp.put_volume >= institutional_threshold:
                    institutional_puts += exp.put_volume
            
            total_institutional = institutional_calls + institutional_puts
            
            if total_institutional == 0:
                return 'BALANCED'
            
            call_percentage = institutional_calls / total_institutional
            
            if call_percentage > 0.6:
                return 'CALLS'
            elif call_percentage < 0.4:
                return 'PUTS'
            else:
                return 'BALANCED'
                
        except Exception as e:
            self.logger.warning(f"Error analyzing institutional bias: {e}")
            return 'BALANCED'
    
    def _detect_unusual_activity(self, symbol: str, expiration_data: List[ExpirationFlowData]) -> List[str]:
        """Detect unusual activity patterns"""
        flags = []
        
        try:
            # Get historical baseline
            baseline = self._get_volume_baseline(symbol)
            total_volume = sum(exp.call_volume + exp.put_volume for exp in expiration_data)
            
            # Check for volume spikes
            if baseline > 0:
                volume_multiplier = total_volume / baseline
                unusual_threshold = self.calculation_config['unusual_volume_multiplier']
                
                if volume_multiplier > unusual_threshold:
                    flags.append(f"Volume spike: {volume_multiplier:.1f}x normal volume")
                    self.calculation_stats['unusual_activity_detected'] += 1
            
            # Check for extreme concentration in single expiration
            if expiration_data:
                max_exp_volume = max(exp.call_volume + exp.put_volume for exp in expiration_data)
                concentration = max_exp_volume / total_volume if total_volume > 0 else 0
                
                if concentration > 0.8:  # 80% concentrated in one expiration
                    flags.append(f"High concentration: {concentration:.1%} in single expiration")
            
            # Check for unusual call/put imbalances
            total_calls = sum(exp.call_volume for exp in expiration_data)
            total_puts = sum(exp.put_volume for exp in expiration_data)
            
            if total_calls + total_puts > 0:
                call_percentage = total_calls / (total_calls + total_puts)
                
                if call_percentage > 0.9:
                    flags.append(f"Extreme call bias: {call_percentage:.1%} calls")
                elif call_percentage < 0.1:
                    flags.append(f"Extreme put bias: {100-call_percentage*100:.1f}% puts")
            
            # Check for large single-expiration volumes
            institutional_threshold = self.calculation_config['institutional_volume_threshold']
            for exp in expiration_data:
                exp_volume = exp.call_volume + exp.put_volume
                if exp_volume > institutional_threshold:
                    flags.append(f"Large institutional flow in {exp.expiration_date}: {exp_volume:,} volume")
            
            return flags
            
        except Exception as e:
            self.logger.warning(f"Error detecting unusual activity: {e}")
            return []
    
    def _find_dominant_expiration(self, expiration_data: List[ExpirationFlowData]) -> str:
        """Find the expiration with highest significance"""
        try:
            if not expiration_data:
                return 'none'
            
            dominant_exp = max(expiration_data, key=lambda x: x.significance_score)
            return dominant_exp.expiration_date
            
        except Exception:
            return 'unknown'
    
    def _determine_flow_trend(self, expiration_data: List[ExpirationFlowData], 
                             weighted_calls: float, weighted_puts: float) -> str:
        """Determine overall flow trend"""
        try:
            total_weighted = weighted_calls + weighted_puts
            
            if total_weighted == 0:
                return 'NEUTRAL'
            
            call_percentage = weighted_calls / total_weighted
            
            # Consider time decay in trend determination
            near_term_calls = sum(
                exp.call_volume * exp.time_decay_weight 
                for exp in expiration_data 
                if exp.days_to_expiry <= 7
            )
            near_term_puts = sum(
                exp.put_volume * exp.time_decay_weight 
                for exp in expiration_data 
                if exp.days_to_expiry <= 7
            )
            
            # Give extra weight to near-term activity
            if near_term_calls + near_term_puts > 0:
                near_term_call_pct = near_term_calls / (near_term_calls + near_term_puts)
                # Blend overall and near-term percentages
                blended_call_pct = (call_percentage * 0.6) + (near_term_call_pct * 0.4)
            else:
                blended_call_pct = call_percentage
            
            if blended_call_pct > 0.6:
                return 'BULLISH'
            elif blended_call_pct < 0.4:
                return 'BEARISH'
            else:
                return 'NEUTRAL'
                
        except Exception as e:
            self.logger.warning(f"Error determining flow trend: {e}")
            return 'NEUTRAL'
    
    def _calculate_flow_confidence(self, expiration_data: List[ExpirationFlowData], 
                                 unusual_flags: List[str]) -> int:
        """Calculate confidence score for flow analysis"""
        try:
            base_confidence = 100
            
            # Penalize for insufficient data
            min_sample_size = self.calculation_config['confidence_min_sample_size']
            if len(expiration_data) < min_sample_size:
                penalty = (min_sample_size - len(expiration_data)) * 10
                base_confidence -= penalty
            
            # Penalize for unusual activity flags
            flag_penalty = min(30, len(unusual_flags) * 8)
            base_confidence -= flag_penalty
            
            # Boost for high volume
            total_volume = sum(exp.call_volume + exp.put_volume for exp in expiration_data)
            if total_volume > 50000:  # High volume = high confidence
                base_confidence += 10
            elif total_volume < 1000:  # Low volume = low confidence
                base_confidence -= 20
            
            # Boost for diverse expiration distribution
            if len(expiration_data) >= 3:
                base_confidence += 5
            
            return max(0, min(100, base_confidence))
            
        except Exception:
            return 70  # Default moderate confidence
    
    def _get_volume_baseline(self, symbol: str) -> float:
        """Get historical volume baseline for comparison"""
        if symbol not in self.volume_baselines:
            return 0.0
        
        baseline = self.volume_baselines[symbol]
        return baseline.get('avg_volume', 0.0)
    
    def _store_flow_result(self, symbol: str, result: FlowAnalysisResult):
        """Store flow analysis result"""
        if symbol not in self.flow_history:
            self.flow_history[symbol] = []
        
        history = self.flow_history[symbol]
        history.append(result)
        
        # Limit history length
        if len(history) > 50:
            history.pop(0)
        
        # Update volume baseline
        self._update_volume_baseline(symbol, result)
    
    def _update_volume_baseline(self, symbol: str, result: FlowAnalysisResult):
        """Update volume baseline for future comparisons"""
        if symbol not in self.volume_baselines:
            self.volume_baselines[symbol] = {
                'avg_volume': 0.0,
                'sample_count': 0,
                'last_update': datetime.now()
            }
        
        baseline = self.volume_baselines[symbol]
        current_volume = result.total_call_volume + result.total_put_volume
        
        # Simple moving average update
        sample_count = baseline['sample_count']
        if sample_count < 10:  # Build up initial samples
            baseline['avg_volume'] = ((baseline['avg_volume'] * sample_count) + current_volume) / (sample_count + 1)
            baseline['sample_count'] = sample_count + 1
        else:
            # Weighted update with more weight on recent data
            baseline['avg_volume'] = (baseline['avg_volume'] * 0.9) + (current_volume * 0.1)
        
        baseline['last_update'] = datetime.now()
    
    def _update_calculation_stats(self, calc_start: float, confidence_score: int, unusual_flags: List[str]):
        """Update calculation performance statistics"""
        calc_time = (time.time() - calc_start) * 1000
        
        stats = self.calculation_stats
        current_avg = stats['avg_calculation_time_ms']
        total_calcs = stats['total_calculations']
        
        # Update average calculation time
        stats['avg_calculation_time_ms'] = (
            (current_avg * (total_calcs - 1) + calc_time) / total_calcs
        )
        
        # Track high confidence calculations
        if confidence_score >= 80:
            stats['high_confidence_calculations'] += 1
    
    def _safe_int_convert(self, value: Any) -> int:
        """Safely convert value to integer"""
        try:
            if value is None:
                return 0
            return max(0, int(float(value)))
        except (ValueError, TypeError):
            return 0
    
    def _create_fallback_result(self, symbol: str, reason: str) -> FlowAnalysisResult:
        """Create fallback result when calculation fails"""
        return FlowAnalysisResult(
            symbol=symbol,
            total_call_volume=0,
            total_put_volume=0,
            weighted_call_dominance=50.0,
            weighted_put_dominance=50.0,
            flow_intensity_score=0,
            time_decay_adjusted_ratio=1.0,
            unusual_activity_flags=[f"Calculation failed: {reason}"],
            confidence_score=25,
            dominant_expiration='unknown',
            flow_trend='NEUTRAL',
            institutional_bias='BALANCED',
            calculation_timestamp=datetime.now()
        )
    
    def get_flow_summary(self, symbol: str = None) -> Dict:
        """Get comprehensive flow analysis summary"""
        if symbol:
            # Symbol-specific summary
            if symbol not in self.flow_history:
                return {'error': f'No flow data for {symbol}'}
            
            history = self.flow_history[symbol]
            if not history:
                return {'error': f'Empty flow history for {symbol}'}
            
            latest = history[-1]
            
            return {
                'symbol': symbol,
                'latest_call_dominance': latest.weighted_call_dominance,
                'latest_put_dominance': latest.weighted_put_dominance,
                'flow_intensity': latest.flow_intensity_score,
                'flow_trend': latest.flow_trend,
                'institutional_bias': latest.institutional_bias,
                'confidence_score': latest.confidence_score,
                'unusual_activity_count': len(latest.unusual_activity_flags),
                'dominant_expiration': latest.dominant_expiration,
                'last_calculation': latest.calculation_timestamp.isoformat()
            }
        else:
            # Global summary
            total_symbols = len(self.flow_history)
            if total_symbols == 0:
                return {'total_symbols': 0}
            
            # Calculate aggregate statistics
            all_confidences = []
            all_intensities = []
            
            for symbol_history in self.flow_history.values():
                if symbol_history:
                    latest = symbol_history[-1]
                    all_confidences.append(latest.confidence_score)
                    all_intensities.append(latest.flow_intensity_score)
            
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0
            avg_intensity = sum(all_intensities) / len(all_intensities) if all_intensities else 0
            
            return {
                'total_symbols_analyzed': total_symbols,
                'average_confidence_score': round(avg_confidence, 1),
                'average_flow_intensity': round(avg_intensity, 1),
                'total_calculations': self.calculation_stats['total_calculations'],
                'high_confidence_percentage': round(
                    (self.calculation_stats['high_confidence_calculations'] / 
                     max(1, self.calculation_stats['total_calculations'])) * 100, 1
                ),
                'avg_calculation_time_ms': round(self.calculation_stats['avg_calculation_time_ms'], 2),
                'unusual_activity_detected': self.calculation_stats['unusual_activity_detected']
            }

# Global instance for easy access
enhanced_options_flow_calculator = EnhancedOptionsFlowCalculator()