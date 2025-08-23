import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
from pathlib import Path

class PerformanceTracker:
    def __init__(self):
        self.performance_file = "trading_performance.json"
        self.predictions_file = "predictions_history.json"
        self.ensure_files_exist()
    
    def ensure_files_exist(self):
        """Ensure performance tracking files exist"""
        if not os.path.exists(self.performance_file):
            initial_data = {
                "total_predictions": 0,
                "correct_predictions": 0,
                "accuracy": 0.0,
                "daily_performance": {},
                "symbol_performance": {},
                "signal_performance": {"BUY_CALL": {"total": 0, "correct": 0}, "BUY_PUT": {"total": 0, "correct": 0}}
            }
            with open(self.performance_file, 'w') as f:
                json.dump(initial_data, f, indent=2)
        
        if not os.path.exists(self.predictions_file):
            with open(self.predictions_file, 'w') as f:
                json.dump([], f)
    
    def log_prediction(self, symbol, signal, confidence, current_price, predicted_price, timestamp=None):
        """Log a new prediction"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        prediction = {
            "id": f"{symbol}_{timestamp}",
            "symbol": symbol,
            "signal": signal,
            "confidence": confidence,
            "current_price": current_price,
            "predicted_price": predicted_price,
            "timestamp": timestamp,
            "result": None,  # Will be updated later
            "actual_price": None,
            "profit_loss": None
        }
        
        # Load existing predictions
        try:
            with open(self.predictions_file, 'r') as f:
                predictions = json.load(f)
        except:
            predictions = []
        
        # Add new prediction
        predictions.append(prediction)
        
        # Keep only last 1000 predictions to prevent file from growing too large
        if len(predictions) > 1000:
            predictions = predictions[-1000:]
        
        # Save predictions
        with open(self.predictions_file, 'w') as f:
            json.dump(predictions, f, indent=2)
        
        return prediction["id"]
    
    def update_prediction_result(self, prediction_id, actual_price, hours_elapsed=24):
        """Update prediction result after time has passed"""
        try:
            with open(self.predictions_file, 'r') as f:
                predictions = json.load(f)
            
            # Find and update the prediction
            for prediction in predictions:
                if prediction["id"] == prediction_id:
                    prediction["actual_price"] = actual_price
                    
                    # Determine if prediction was correct
                    signal = prediction["signal"]
                    current_price = prediction["current_price"]
                    
                    if signal == "BUY_CALL":
                        prediction["result"] = "correct" if actual_price > current_price else "incorrect"
                        prediction["profit_loss"] = ((actual_price - current_price) / current_price) * 100
                    elif signal == "BUY_PUT":
                        prediction["result"] = "correct" if actual_price < current_price else "incorrect"
                        prediction["profit_loss"] = ((current_price - actual_price) / current_price) * 100
                    else:
                        prediction["result"] = "neutral"
                        prediction["profit_loss"] = 0
                    
                    break
            
            # Save updated predictions
            with open(self.predictions_file, 'w') as f:
                json.dump(predictions, f, indent=2)
            
            # Update overall performance stats
            self._update_performance_stats()
            
        except Exception as e:
            print(f"Error updating prediction result: {e}")
    
    def _update_performance_stats(self):
        """Update overall performance statistics"""
        try:
            with open(self.predictions_file, 'r') as f:
                predictions = json.load(f)
            
            # Calculate overall stats
            total_predictions = len([p for p in predictions if p["result"] is not None])
            correct_predictions = len([p for p in predictions if p["result"] == "correct"])
            accuracy = (correct_predictions / total_predictions * 100) if total_predictions > 0 else 0
            
            # Calculate daily performance
            daily_performance = {}
            symbol_performance = {}
            signal_performance = {"BUY_CALL": {"total": 0, "correct": 0}, "BUY_PUT": {"total": 0, "correct": 0}}
            
            for prediction in predictions:
                if prediction["result"] is None:
                    continue
                
                # Daily performance
                date = prediction["timestamp"][:10]  # YYYY-MM-DD
                if date not in daily_performance:
                    daily_performance[date] = {"total": 0, "correct": 0, "accuracy": 0}
                daily_performance[date]["total"] += 1
                if prediction["result"] == "correct":
                    daily_performance[date]["correct"] += 1
                daily_performance[date]["accuracy"] = (daily_performance[date]["correct"] / daily_performance[date]["total"]) * 100
                
                # Symbol performance
                symbol = prediction["symbol"]
                if symbol not in symbol_performance:
                    symbol_performance[symbol] = {"total": 0, "correct": 0, "accuracy": 0}
                symbol_performance[symbol]["total"] += 1
                if prediction["result"] == "correct":
                    symbol_performance[symbol]["correct"] += 1
                symbol_performance[symbol]["accuracy"] = (symbol_performance[symbol]["correct"] / symbol_performance[symbol]["total"]) * 100
                
                # Signal performance
                signal = prediction["signal"]
                if signal in signal_performance:
                    signal_performance[signal]["total"] += 1
                    if prediction["result"] == "correct":
                        signal_performance[signal]["correct"] += 1
            
            # Update performance file
            performance_data = {
                "total_predictions": total_predictions,
                "correct_predictions": correct_predictions,
                "accuracy": accuracy,
                "daily_performance": daily_performance,
                "symbol_performance": symbol_performance,
                "signal_performance": signal_performance,
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.performance_file, 'w') as f:
                json.dump(performance_data, f, indent=2)
            
        except Exception as e:
            print(f"Error updating performance stats: {e}")
    
    def get_performance_stats(self):
        """Get current performance statistics"""
        try:
            with open(self.performance_file, 'r') as f:
                return json.load(f)
        except:
            return {
                "total_predictions": 0,
                "correct_predictions": 0,
                "accuracy": 0.0,
                "daily_performance": {},
                "symbol_performance": {},
                "signal_performance": {"BUY_CALL": {"total": 0, "correct": 0}, "BUY_PUT": {"total": 0, "correct": 0}}
            }
    
    def get_recent_predictions(self, days=7):
        """Get recent predictions for analysis"""
        try:
            with open(self.predictions_file, 'r') as f:
                predictions = json.load(f)
            
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_predictions = []
            
            for prediction in predictions:
                pred_date = datetime.fromisoformat(prediction["timestamp"])
                if pred_date >= cutoff_date:
                    recent_predictions.append(prediction)
            
            return recent_predictions
        except:
            return []
    
    def get_accuracy_by_symbol(self):
        """Get accuracy breakdown by symbol"""
        stats = self.get_performance_stats()
        return stats.get("symbol_performance", {})
    
    def get_accuracy_by_signal_type(self):
        """Get accuracy breakdown by signal type"""
        stats = self.get_performance_stats()
        signal_perf = stats.get("signal_performance", {})
        
        result = {}
        for signal, data in signal_perf.items():
            if data["total"] > 0:
                result[signal] = {
                    "accuracy": (data["correct"] / data["total"]) * 100,
                    "total": data["total"],
                    "correct": data["correct"]
                }
            else:
                result[signal] = {"accuracy": 0, "total": 0, "correct": 0}
        
        return result
    
    def simulate_historical_performance(self):
        """Generate simulated historical performance for demo purposes"""
        # Create 30 days of simulated performance data
        performance_data = []
        base_accuracy = 68.5  # Base accuracy around 68.5%
        
        for i in range(30):
            date = (datetime.now() - timedelta(days=30-i)).strftime('%Y-%m-%d')
            
            # Simulate daily performance with some variation
            daily_accuracy = base_accuracy + np.random.normal(0, 8)  # +/- 8% variation
            daily_accuracy = max(45, min(85, daily_accuracy))  # Keep between 45-85%
            
            total_predictions = np.random.randint(8, 25)  # 8-25 predictions per day
            correct_predictions = int((daily_accuracy / 100) * total_predictions)
            
            performance_data.append({
                'date': date,
                'accuracy': daily_accuracy,
                'total_predictions': total_predictions,
                'correct_predictions': correct_predictions,
                'profit_loss': np.random.normal(2.1, 3.5)  # Average 2.1% with variation
            })
        
        return pd.DataFrame(performance_data)