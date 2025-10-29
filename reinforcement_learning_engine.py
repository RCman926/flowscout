"""
Reinforcement Learning Engine - Learn from Real Trading Results
Automatically improves AI predictions by analyzing win/loss patterns
"""

import json
import os
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
import pickle

class ReinforcementLearningEngine:
    """
    Learns from real trading results to improve future predictions
    - Analyzes what features led to wins vs losses
    - Retrains models based on actual outcomes
    - Adjusts confidence scoring based on historical accuracy
    - Tracks improvement over time
    """
    
    def __init__(self):
        self.learning_history_file = "learning_history.json"
        self.model_checkpoint_file = "rl_model_checkpoint.pkl"
        
        # Learning configuration
        self.min_predictions_for_learning = 10  # Need at least 10 results to learn
        self.learning_trigger_interval = 10     # Retrain after every 10 new predictions
        
        # Reinforcement learning models
        self.outcome_predictor = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.confidence_adjuster = GradientBoostingClassifier(
            n_estimators=50,
            max_depth=5,
            random_state=42
        )
        
        self.scaler = StandardScaler()
        self.is_trained = False
        
        # Learning statistics
        self.learning_stats = {
            'total_retrains': 0,
            'last_retrain_date': None,
            'improvement_history': [],
            'feature_importance': {},
            'model_version': '1.0_rl'
        }
        
        self.load_learning_history()
        self.load_model_checkpoint()
    
    def load_learning_history(self):
        """Load learning history from file"""
        try:
            if os.path.exists(self.learning_history_file):
                with open(self.learning_history_file, 'r') as f:
                    self.learning_stats = json.load(f)
            else:
                self.save_learning_history()
        except Exception as e:
            print(f"Error loading learning history: {e}")
    
    def save_learning_history(self):
        """Save learning history to file"""
        try:
            with open(self.learning_history_file, 'w') as f:
                json.dump(self.learning_stats, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving learning history: {e}")
    
    def load_model_checkpoint(self):
        """Load trained model checkpoint"""
        try:
            if os.path.exists(self.model_checkpoint_file):
                with open(self.model_checkpoint_file, 'rb') as f:
                    checkpoint = pickle.load(f)
                    self.outcome_predictor = checkpoint['outcome_predictor']
                    self.confidence_adjuster = checkpoint['confidence_adjuster']
                    self.scaler = checkpoint['scaler']
                    self.is_trained = checkpoint['is_trained']
                    print(f"✅ Loaded RL model checkpoint (v{checkpoint.get('version', '1.0')})")
        except Exception as e:
            print(f"No existing model checkpoint: {e}")
    
    def save_model_checkpoint(self):
        """Save trained model checkpoint"""
        try:
            checkpoint = {
                'outcome_predictor': self.outcome_predictor,
                'confidence_adjuster': self.confidence_adjuster,
                'scaler': self.scaler,
                'is_trained': self.is_trained,
                'version': self.learning_stats['model_version'],
                'saved_at': datetime.now().isoformat()
            }
            with open(self.model_checkpoint_file, 'wb') as f:
                pickle.dump(checkpoint, f)
            print(f"💾 Saved RL model checkpoint")
        except Exception as e:
            print(f"Error saving model checkpoint: {e}")
    
    def extract_features_from_prediction(self, prediction: Dict) -> np.ndarray:
        """
        Extract features from a prediction for learning
        Returns feature vector that AI can learn from
        """
        features = []
        
        # Market conditions at prediction time
        features.append(prediction.get('confidence', 50) / 100)  # Original confidence
        features.append(1 if prediction.get('prediction_type') == 'CALL' else -1 if prediction.get('prediction_type') == 'PUT' else 0)
        
        # Price and target features
        starting_price = prediction.get('starting_price', 100)
        target_price = prediction.get('target_price', starting_price)
        price_delta_pct = ((target_price - starting_price) / starting_price) * 100 if starting_price > 0 else 0
        features.append(price_delta_pct / 10)  # Normalize to -10 to +10 range
        
        # AI ensemble data
        ai_data = prediction.get('ai_ensemble_data', {})
        features.append(ai_data.get('model_agreement', 0.5))
        features.append(ai_data.get('model_count', 1) / 5)  # Normalize
        features.append(1 if ai_data.get('market_regime') == 'bullish' else -1 if ai_data.get('market_regime') == 'bearish' else 0)
        
        # Network quality metrics
        network_data = prediction.get('network_metrics', {})
        features.append(network_data.get('network_quality', 50) / 100)
        features.append(min(1.0, network_data.get('fetch_latency_ms', 100) / 1000))  # Normalize latency
        
        # Time-based features
        try:
            pred_date = datetime.fromisoformat(prediction.get('prediction_date', datetime.now().isoformat()))
            exp_date = datetime.fromisoformat(prediction.get('expiration_date', (datetime.now() + timedelta(days=1)).isoformat()).replace('Z', '+00:00'))
            days_to_expiry = (exp_date - pred_date).days
            features.append(min(1.0, days_to_expiry / 30))  # Normalize to 0-1
        except:
            features.append(0.5)  # Default mid-range
        
        # Feature count (more features = potentially better analysis)
        features.append(ai_data.get('feature_count', 10) / 40)  # Normalize
        
        return np.array(features)
    
    def learn_from_results(self, predictions: List[Dict]) -> Dict:
        """
        Main reinforcement learning function
        Analyzes completed predictions and retrains models
        """
        print(f"\n🧠 REINFORCEMENT LEARNING: Analyzing {len(predictions)} completed predictions...")
        
        # Filter for completed predictions with results
        completed = [p for p in predictions if p['status'] == 'EXPIRED' and p.get('result')]
        
        if len(completed) < self.min_predictions_for_learning:
            return {
                'learned': False,
                'reason': f'Need at least {self.min_predictions_for_learning} completed predictions (have {len(completed)})',
                'completed_predictions': len(completed)
            }
        
        # Extract features and labels
        X = []
        y_outcome = []  # 1 for WIN, 0 for LOSS
        
        for pred in completed:
            features = self.extract_features_from_prediction(pred)
            X.append(features)
            y_outcome.append(1 if pred['result'] == 'WIN' else 0)
        
        X = np.array(X)
        y_outcome = np.array(y_outcome)
        
        # Calculate win rate before learning
        old_win_rate = np.mean(y_outcome) * 100
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train outcome predictor
        self.outcome_predictor.fit(X_scaled, y_outcome)
        
        # Train confidence adjuster (predicts if high confidence predictions succeed)
        high_conf_mask = X[:, 0] > 0.6  # Original confidence > 60%
        if np.sum(high_conf_mask) > 5:
            self.confidence_adjuster.fit(X_scaled[high_conf_mask], y_outcome[high_conf_mask])
        
        self.is_trained = True
        
        # Analyze feature importance
        feature_names = [
            'original_confidence', 'prediction_direction', 'price_delta',
            'model_agreement', 'model_count', 'market_regime',
            'network_quality', 'fetch_latency', 'days_to_expiry', 'feature_count'
        ]
        
        feature_importance = dict(zip(
            feature_names,
            self.outcome_predictor.feature_importances_
        ))
        
        # Sort by importance
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
        
        # Update learning statistics
        self.learning_stats['total_retrains'] += 1
        self.learning_stats['last_retrain_date'] = datetime.now().isoformat()
        self.learning_stats['feature_importance'] = feature_importance
        self.learning_stats['improvement_history'].append({
            'retrain_number': self.learning_stats['total_retrains'],
            'date': datetime.now().isoformat(),
            'training_samples': len(completed),
            'win_rate': old_win_rate,
            'top_features': sorted_features[:3]
        })
        
        # Save progress
        self.save_learning_history()
        self.save_model_checkpoint()
        
        print(f"✅ LEARNED from {len(completed)} predictions!")
        print(f"📊 Win Rate: {old_win_rate:.1f}%")
        print(f"🔑 Top 3 Important Features:")
        for i, (feature, importance) in enumerate(sorted_features[:3], 1):
            print(f"   {i}. {feature}: {importance:.3f}")
        
        return {
            'learned': True,
            'training_samples': len(completed),
            'win_rate': old_win_rate,
            'top_features': sorted_features[:3],
            'total_retrains': self.learning_stats['total_retrains']
        }
    
    def adjust_prediction_confidence(self, features: Dict, original_confidence: float) -> Tuple[float, str]:
        """
        Adjust prediction confidence based on learned patterns
        Returns (adjusted_confidence, reason)
        """
        if not self.is_trained:
            return original_confidence, "Model not yet trained"
        
        try:
            # Create feature vector similar to training
            feature_vector = np.array([
                original_confidence / 100,
                1 if features.get('signal_type') == 'CALL' else -1,
                features.get('price_delta_pct', 0) / 10,
                features.get('model_agreement', 0.5),
                features.get('model_count', 1) / 5,
                1 if features.get('market_regime') == 'bullish' else -1,
                features.get('network_quality', 50) / 100,
                0.5,  # Default latency
                features.get('days_to_expiry', 1) / 30,
                features.get('feature_count', 10) / 40
            ]).reshape(1, -1)
            
            # Scale features
            feature_vector_scaled = self.scaler.transform(feature_vector)
            
            # Predict win probability
            win_probability = self.outcome_predictor.predict_proba(feature_vector_scaled)[0][1]
            
            # Adjust confidence based on historical patterns
            adjusted_confidence = (original_confidence * 0.5) + (win_probability * 100 * 0.5)
            
            # Determine reason
            if adjusted_confidence > original_confidence + 5:
                reason = "Increased (similar patterns won before)"
            elif adjusted_confidence < original_confidence - 5:
                reason = "Decreased (similar patterns lost before)"
            else:
                reason = "Confirmed (matches historical accuracy)"
            
            return adjusted_confidence, reason
            
        except Exception as e:
            print(f"Confidence adjustment error: {e}")
            return original_confidence, "Error in adjustment"
    
    def get_learning_summary(self) -> Dict:
        """Get summary of reinforcement learning progress"""
        return {
            'is_trained': self.is_trained,
            'total_retrains': self.learning_stats['total_retrains'],
            'last_retrain': self.learning_stats.get('last_retrain_date'),
            'model_version': self.learning_stats['model_version'],
            'top_features': sorted(
                self.learning_stats.get('feature_importance', {}).items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            'improvement_history': self.learning_stats.get('improvement_history', [])[-5:]
        }
    
    def should_trigger_learning(self, prediction_tracker) -> bool:
        """
        Check if we should trigger automatic learning
        Returns True if enough new predictions since last retrain
        """
        completed = [p for p in prediction_tracker.predictions if p['status'] == 'EXPIRED']
        
        # Check if we have minimum predictions
        if len(completed) < self.min_predictions_for_learning:
            return False
        
        # Check if enough new predictions since last retrain
        last_retrain_count = 0
        if self.learning_stats.get('improvement_history'):
            last_retrain_count = self.learning_stats['improvement_history'][-1].get('training_samples', 0)
        
        new_predictions = len(completed) - last_retrain_count
        
        return new_predictions >= self.learning_trigger_interval

# Global instance
rl_engine = ReinforcementLearningEngine()
