import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
import asyncio

class SignalValidator:
    def __init__(self):
        self.signals_file = "signal_history.json"
        self.validation_file = "signal_validation.json"
        self.ensure_files_exist()
    
    def ensure_files_exist(self):
        """Ensure signal tracking files exist"""
        for file_path in [self.signals_file, self.validation_file]:
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    json.dump([], f)
    
    def log_signal(self, symbol, signal_type, confidence, current_price, predicted_price, entry_premium=None, target_premium=None):
        """Log a new signal for validation"""
        signal_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        signal_data = {
            "id": signal_id,
            "symbol": symbol,
            "signal_type": signal_type,
            "confidence": confidence,
            "current_price": current_price,
            "predicted_price": predicted_price,
            "entry_premium": entry_premium,
            "target_premium": target_premium,
            "timestamp": datetime.now().isoformat(),
            "status": "active",
            "actual_outcome": None,
            "profit_loss": None,
            "validation_time": None,
            "success": None
        }
        
        try:
            with open(self.signals_file, 'r') as f:
                signals = json.load(f)
        except:
            signals = []
        
        signals.append(signal_data)
        
        # Keep only last 100 signals
        if len(signals) > 100:
            signals = signals[-100:]
        
        with open(self.signals_file, 'w') as f:
            json.dump(signals, f, indent=2)
        
        return signal_id
    
    def validate_signals(self, hours_to_validate=4):
        """Validate signals after specified hours"""
        try:
            with open(self.signals_file, 'r') as f:
                signals = json.load(f)
            
            updated_signals = []
            validation_results = []
            
            for signal in signals:
                if signal['status'] == 'active':
                    signal_time = datetime.fromisoformat(signal['timestamp'])
                    hours_elapsed = (datetime.now() - signal_time).total_seconds() / 3600
                    
                    if hours_elapsed >= hours_to_validate:
                        # Validate this signal
                        validation = self._validate_single_signal(signal, hours_elapsed)
                        signal.update(validation)
                        signal['status'] = 'validated'
                        validation_results.append(validation)
                
                updated_signals.append(signal)
            
            # Save updated signals
            with open(self.signals_file, 'w') as f:
                json.dump(updated_signals, f, indent=2)
            
            # Save validation results
            if validation_results:
                try:
                    with open(self.validation_file, 'r') as f:
                        all_validations = json.load(f)
                except:
                    all_validations = []
                
                all_validations.extend(validation_results)
                
                # Keep only last 500 validations
                if len(all_validations) > 500:
                    all_validations = all_validations[-500:]
                
                with open(self.validation_file, 'w') as f:
                    json.dump(all_validations, f, indent=2)
            
            return len(validation_results)
            
        except Exception as e:
            print(f"Signal validation error: {e}")
            return 0
    
    def _validate_single_signal(self, signal, hours_elapsed):
        """Validate a single signal based on market movement"""
        try:
            # Simulate market movement validation
            # In real implementation, this would fetch actual market data
            
            symbol = signal['symbol']
            signal_type = signal['signal_type']
            predicted_price = signal['predicted_price']
            current_price = signal['current_price']
            confidence = signal['confidence']
            
            # Simulate actual price after time elapsed
            # Add some randomness but bias toward the predicted direction
            direction_multiplier = 1 if signal_type == "BUY_CALL" else -1
            
            # Higher confidence signals have higher probability of success
            success_probability = 0.4 + (confidence * 0.4)  # 40-80% success rate based on confidence
            
            is_successful = np.random.random() < success_probability
            
            if is_successful:
                # Successful signal - price moved in predicted direction
                price_movement = direction_multiplier * abs(predicted_price - current_price) * np.random.uniform(0.8, 1.5)
                actual_price = current_price + price_movement
                
                # Calculate profit for options
                if signal['entry_premium'] and signal['target_premium']:
                    profit_loss = (signal['target_premium'] - signal['entry_premium']) / signal['entry_premium'] * 100
                else:
                    profit_loss = (price_movement / current_price) * 100
                    
            else:
                # Failed signal - price moved against prediction or sideways
                price_movement = direction_multiplier * abs(predicted_price - current_price) * np.random.uniform(-0.5, 0.3)
                actual_price = current_price + price_movement
                
                # Calculate loss
                if signal['entry_premium']:
                    # Options typically lose 20-60% on failed signals
                    profit_loss = -np.random.uniform(20, 60)
                else:
                    profit_loss = (price_movement / current_price) * 100
            
            return {
                "actual_outcome": actual_price,
                "profit_loss": profit_loss,
                "validation_time": datetime.now().isoformat(),
                "success": is_successful,
                "hours_elapsed": hours_elapsed
            }
            
        except Exception as e:
            print(f"Single signal validation error: {e}")
            return {
                "actual_outcome": signal['current_price'],
                "profit_loss": 0,
                "validation_time": datetime.now().isoformat(),
                "success": False,
                "hours_elapsed": hours_elapsed
            }
    
    def get_signal_performance(self, days=30):
        """Get signal performance metrics"""
        try:
            with open(self.validation_file, 'r') as f:
                validations = json.load(f)
            
            if not validations:
                return self._get_default_performance()
            
            # Filter recent validations
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_validations = []
            
            for validation in validations:
                if 'validation_time' in validation:
                    val_time = datetime.fromisoformat(validation['validation_time'])
                    if val_time >= cutoff_date:
                        recent_validations.append(validation)
            
            if not recent_validations:
                return self._get_default_performance()
            
            # Calculate metrics
            total_signals = len(recent_validations)
            successful_signals = sum(1 for v in recent_validations if v.get('success', False))
            success_rate = (successful_signals / total_signals) * 100
            
            # Calculate average profit/loss
            profits = [v.get('profit_loss', 0) for v in recent_validations if v.get('success', False)]
            losses = [v.get('profit_loss', 0) for v in recent_validations if not v.get('success', False)]
            
            avg_profit = np.mean(profits) if profits else 0
            avg_loss = np.mean(losses) if losses else 0
            
            # Calculate by signal type
            call_signals = [v for v in recent_validations if 'signal_type' in v and v['signal_type'] == 'BUY_CALL']
            put_signals = [v for v in recent_validations if 'signal_type' in v and v['signal_type'] == 'BUY_PUT']
            
            call_success = (sum(1 for v in call_signals if v.get('success', False)) / len(call_signals) * 100) if call_signals else 0
            put_success = (sum(1 for v in put_signals if v.get('success', False)) / len(put_signals) * 100) if put_signals else 0
            
            return {
                "total_signals": total_signals,
                "success_rate": success_rate,
                "successful_signals": successful_signals,
                "failed_signals": total_signals - successful_signals,
                "avg_profit": avg_profit,
                "avg_loss": avg_loss,
                "call_success_rate": call_success,
                "put_success_rate": put_success,
                "profit_factor": abs(avg_profit / avg_loss) if avg_loss != 0 else 1,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Performance calculation error: {e}")
            return self._get_default_performance()
    
    def _get_default_performance(self):
        """Return default performance metrics"""
        return {
            "total_signals": 0,
            "success_rate": 0,
            "successful_signals": 0,
            "failed_signals": 0,
            "avg_profit": 0,
            "avg_loss": 0,
            "call_success_rate": 0,
            "put_success_rate": 0,
            "profit_factor": 1,
            "last_updated": datetime.now().isoformat()
        }
    
    def get_recent_signals(self, limit=10):
        """Get recent signals with their outcomes"""
        try:
            with open(self.signals_file, 'r') as f:
                signals = json.load(f)
            
            # Sort by timestamp and limit
            signals.sort(key=lambda x: x['timestamp'], reverse=True)
            return signals[:limit]
            
        except:
            return []
    
    def generate_signal_quality_score(self):
        """Generate overall signal quality score"""
        performance = self.get_signal_performance()
        
        if performance['total_signals'] == 0:
            return 0
        
        # Calculate composite score based on multiple factors
        success_weight = 0.4
        profit_weight = 0.3
        consistency_weight = 0.2
        volume_weight = 0.1
        
        # Success rate component (0-100)
        success_score = performance['success_rate']
        
        # Profit factor component (normalize to 0-100 scale)
        profit_score = min(100, performance['profit_factor'] * 25)  # 4.0 profit factor = 100 score
        
        # Consistency (balance between call and put success)
        consistency_score = 100 - abs(performance['call_success_rate'] - performance['put_success_rate'])
        
        # Volume (more signals = higher confidence in score)
        volume_score = min(100, performance['total_signals'] * 5)  # 20 signals = 100 score
        
        # Calculate weighted score
        quality_score = (
            success_score * success_weight +
            profit_score * profit_weight +
            consistency_score * consistency_weight +
            volume_score * volume_weight
        )
        
        return round(quality_score, 1)
    
    def get_signal_recommendations(self):
        """Get recommendations for improving signal quality"""
        performance = self.get_signal_performance()
        recommendations = []
        
        if performance['success_rate'] < 60:
            recommendations.append("⚠️ Success rate below 60% - consider adjusting signal criteria")
        
        if performance['profit_factor'] < 1.5:
            recommendations.append("📉 Low profit factor - review risk management")
        
        if abs(performance['call_success_rate'] - performance['put_success_rate']) > 20:
            recommendations.append("⚖️ Imbalanced call/put performance - review directional bias")
        
        if performance['total_signals'] < 10:
            recommendations.append("📊 Limited signal history - continue tracking for better analysis")
        
        if not recommendations:
            recommendations.append("✅ Signal quality looks good - maintain current strategy")
        
        return recommendations