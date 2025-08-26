"""
Advanced Prediction Engine - Free ML-based improvements
Uses scikit-learn for pattern recognition and prediction scoring
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
import warnings
warnings.filterwarnings('ignore')

class AdvancedPredictionEngine:
    """Enhanced prediction engine using machine learning"""
    
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=50, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_history = []
        
    def extract_features(self, market_data, tech_data, flow_data):
        """Extract features for ML prediction"""
        try:
            features = {
                # Price momentum features
                'price_change_pct': market_data.get('change_pct', 0),
                'volume_ratio': market_data.get('volume', 1) / max(1, market_data.get('avg_volume', 1)),
                'price_vs_sma20': (market_data.get('price', 100) - tech_data.get('sma_20', 100)) / tech_data.get('sma_20', 100),
                
                # Technical indicator features
                'rsi': tech_data.get('rsi', 50),
                'rsi_momentum': tech_data.get('rsi', 50) - 50,  # Distance from neutral
                'macd': tech_data.get('macd', 0),
                'macd_signal_diff': tech_data.get('macd', 0) - tech_data.get('macd_signal', 0),
                
                # Bollinger band features
                'bb_position': self._calculate_bb_position(market_data, tech_data),
                'bb_squeeze': self._calculate_bb_squeeze(tech_data),
                
                # Options flow features
                'total_flow': flow_data.get('total_volume', 0),
                'call_put_ratio': self._calculate_cp_ratio(flow_data),
                'flow_momentum': self._calculate_flow_momentum(flow_data),
                
                # Time-based features
                'hour_of_day': datetime.now().hour,
                'day_of_week': datetime.now().weekday(),
                'time_to_close': self._time_to_market_close()
            }
            
            return list(features.values())
            
        except Exception as e:
            print(f"Feature extraction error: {e}")
            return [0] * 14  # Default feature vector
    
    def _calculate_bb_position(self, market_data, tech_data):
        """Calculate position within Bollinger Bands"""
        try:
            price = market_data.get('price', 100)
            bb_upper = tech_data.get('bb_upper', 105)
            bb_lower = tech_data.get('bb_lower', 95)
            bb_middle = tech_data.get('bb_middle', 100)
            
            if bb_upper == bb_lower:
                return 0.5
            
            return (price - bb_lower) / (bb_upper - bb_lower)
        except:
            return 0.5
    
    def _calculate_bb_squeeze(self, tech_data):
        """Calculate Bollinger Band squeeze indicator"""
        try:
            bb_upper = tech_data.get('bb_upper', 105)
            bb_lower = tech_data.get('bb_lower', 95)
            sma_20 = tech_data.get('sma_20', 100)
            
            band_width = (bb_upper - bb_lower) / sma_20
            return band_width
        except:
            return 0.02
    
    def _calculate_cp_ratio(self, flow_data):
        """Calculate call/put ratio from flow data"""
        try:
            analysis = flow_data.get('analysis', [])
            total_calls = sum([exp.get('call_volume', 0) for exp in analysis])
            total_puts = sum([exp.get('put_volume', 0) for exp in analysis])
            
            if total_puts == 0:
                return 2.0
            
            return total_calls / total_puts
        except:
            return 1.0
    
    def _calculate_flow_momentum(self, flow_data):
        """Calculate options flow momentum"""
        try:
            analysis = flow_data.get('analysis', [])
            if not analysis:
                return 0
            
            # Weight recent expirations more heavily
            weighted_flow = 0
            total_weight = 0
            
            for exp in analysis[:5]:  # Only consider first 5 expirations
                call_vol = exp.get('call_volume', 0)
                put_vol = exp.get('put_volume', 0)
                dte = exp.get('dte', 30)
                
                # Weight by inverse of DTE (closer expiration = higher weight)
                weight = 1 / max(1, dte)
                net_flow = call_vol - put_vol
                
                weighted_flow += net_flow * weight
                total_weight += weight
            
            return weighted_flow / max(1, total_weight)
        except:
            return 0
    
    def _time_to_market_close(self):
        """Calculate hours until market close"""
        now = datetime.now()
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        if now > market_close:
            # Next day's close
            market_close += timedelta(days=1)
        
        time_diff = (market_close - now).total_seconds() / 3600
        return min(24, max(0, time_diff))
    
    def generate_advanced_prediction(self, market_data, tech_data, flow_data):
        """Generate ML-enhanced predictions"""
        features = self.extract_features(market_data, tech_data, flow_data)
        
        # Store features for training
        self.feature_history.append({
            'features': features,
            'timestamp': datetime.now(),
            'price': market_data.get('price', 100)
        })
        
        # Keep only recent history (last 100 data points)
        if len(self.feature_history) > 100:
            self.feature_history = self.feature_history[-100:]
        
        # Pattern-based prediction scoring
        prediction_score = self._calculate_pattern_score(features)
        confidence_score = self._calculate_confidence_score(features)
        
        # Enhanced signal generation
        signal = self._generate_enhanced_signal(features, prediction_score)
        
        # Price target calculation
        price_targets = self._calculate_price_targets(market_data, tech_data, prediction_score)
        
        return {
            'prediction_score': prediction_score,
            'confidence': confidence_score,
            'enhanced_signal': signal,
            'price_targets': price_targets,
            'pattern_strength': self._assess_pattern_strength(features),
            'risk_level': self._calculate_risk_level(features),
            'time_horizon': self._suggest_time_horizon(features)
        }
    
    def _calculate_pattern_score(self, features):
        """Calculate pattern-based prediction score"""
        try:
            # Weighted scoring based on feature importance
            weights = [
                0.20,  # price_change_pct
                0.15,  # volume_ratio
                0.10,  # price_vs_sma20
                0.15,  # rsi
                0.08,  # rsi_momentum
                0.05,  # macd
                0.07,  # macd_signal_diff
                0.08,  # bb_position
                0.03,  # bb_squeeze
                0.04,  # total_flow
                0.15,  # call_put_ratio
                0.08,  # flow_momentum
                0.01,  # hour_of_day
                0.01,  # day_of_week
                0.00   # time_to_close
            ]
            
            # Normalize features to [-1, 1] range
            normalized_features = []
            for i, feature in enumerate(features):
                if i == 0:  # price_change_pct
                    normalized_features.append(np.tanh(feature / 2))
                elif i == 1:  # volume_ratio
                    normalized_features.append(np.tanh((feature - 1) * 2))
                elif i == 3:  # rsi
                    normalized_features.append((feature - 50) / 50)
                elif i == 10:  # call_put_ratio
                    normalized_features.append(np.tanh((feature - 1) * 0.5))
                else:
                    normalized_features.append(np.tanh(feature))
            
            # Calculate weighted score
            score = sum(w * f for w, f in zip(weights, normalized_features))
            return max(-1, min(1, score))
            
        except Exception as e:
            print(f"Pattern score calculation error: {e}")
            return 0
    
    def _calculate_confidence_score(self, features):
        """Calculate prediction confidence"""
        try:
            # Confidence based on signal alignment
            confidence_factors = []
            
            # Volume confirmation
            if features[1] > 1.5:  # High volume
                confidence_factors.append(20)
            elif features[1] > 1.2:
                confidence_factors.append(10)
            
            # RSI extremes
            rsi = features[3]
            if rsi < 30 or rsi > 70:
                confidence_factors.append(15)
            elif rsi < 40 or rsi > 60:
                confidence_factors.append(8)
            
            # Price momentum
            price_change = abs(features[0])
            if price_change > 2:
                confidence_factors.append(20)
            elif price_change > 1:
                confidence_factors.append(10)
            
            # Options flow strength
            cp_ratio = features[10]
            if cp_ratio > 2 or cp_ratio < 0.5:
                confidence_factors.append(15)
            
            # BB position extremes
            bb_pos = features[7]
            if bb_pos < 0.1 or bb_pos > 0.9:
                confidence_factors.append(10)
            
            base_confidence = 50
            total_confidence = base_confidence + sum(confidence_factors)
            
            return min(95, max(30, total_confidence))
            
        except Exception as e:
            print(f"Confidence calculation error: {e}")
            return 60
    
    def _generate_enhanced_signal(self, features, prediction_score):
        """Generate enhanced trading signal"""
        if prediction_score > 0.3:
            return "STRONG_BUY_CALLS"
        elif prediction_score > 0.1:
            return "BUY_CALLS"
        elif prediction_score < -0.3:
            return "STRONG_BUY_PUTS"
        elif prediction_score < -0.1:
            return "BUY_PUTS"
        else:
            return "HOLD"
    
    def _calculate_price_targets(self, market_data, tech_data, prediction_score):
        """Calculate dynamic price targets"""
        current_price = market_data.get('price', 100)
        volatility = abs(market_data.get('change_pct', 1)) / 100
        
        # Base target multipliers
        if abs(prediction_score) > 0.5:
            multipliers = [0.02, 0.05, 0.08]  # High confidence targets
        elif abs(prediction_score) > 0.3:
            multipliers = [0.015, 0.035, 0.06]  # Medium confidence
        else:
            multipliers = [0.01, 0.025, 0.04]   # Low confidence
        
        # Adjust for volatility
        volatility_factor = max(0.5, min(2.0, volatility * 50))
        adjusted_multipliers = [m * volatility_factor for m in multipliers]
        
        if prediction_score > 0:  # Bullish targets
            return {
                'target_1': current_price * (1 + adjusted_multipliers[0]),
                'target_2': current_price * (1 + adjusted_multipliers[1]),
                'target_3': current_price * (1 + adjusted_multipliers[2])
            }
        else:  # Bearish targets
            return {
                'target_1': current_price * (1 - adjusted_multipliers[0]),
                'target_2': current_price * (1 - adjusted_multipliers[1]),
                'target_3': current_price * (1 - adjusted_multipliers[2])
            }
    
    def _assess_pattern_strength(self, features):
        """Assess overall pattern strength"""
        signal_count = 0
        
        # Count confirming signals
        if abs(features[0]) > 1:  # Strong price move
            signal_count += 1
        if features[1] > 1.3:  # High volume
            signal_count += 1
        if features[3] < 30 or features[3] > 70:  # RSI extreme
            signal_count += 1
        if features[10] > 1.5 or features[10] < 0.67:  # Strong C/P ratio
            signal_count += 1
        if abs(features[11]) > 10000:  # Strong flow momentum
            signal_count += 1
        
        strength_levels = ['WEAK', 'MODERATE', 'STRONG', 'VERY_STRONG']
        return strength_levels[min(3, signal_count)]
    
    def _calculate_risk_level(self, features):
        """Calculate trade risk level"""
        risk_factors = 0
        
        # High volatility indicators
        if abs(features[0]) > 3:  # Extreme price moves
            risk_factors += 2
        if features[8] < 0.015:  # BB squeeze (low volatility before explosion)
            risk_factors += 1
        if features[12] < 10 or features[12] > 15:  # Market open/close volatility
            risk_factors += 1
        
        if risk_factors >= 3:
            return "HIGH"
        elif risk_factors == 2:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _suggest_time_horizon(self, features):
        """Suggest optimal time horizon"""
        # Based on pattern characteristics
        if abs(features[0]) > 2:  # Strong momentum
            return "0-1 DTE"
        elif features[1] > 1.5:  # High volume
            return "1-3 DTE"
        else:
            return "3-7 DTE"

# Global instance
prediction_engine = AdvancedPredictionEngine()