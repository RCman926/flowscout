"""
Prediction Tracker - Track wins/losses on expired options using REAL data
Shows if our predictions were correct when options expire
"""

import json
import os
from datetime import datetime, timedelta
import yfinance as yf

class PredictionTracker:
    """Track prediction accuracy using real market data"""
    
    def __init__(self):
        self.predictions_file = "prediction_history.json"
        self.load_predictions()
    
    def load_predictions(self):
        """Load prediction history from file"""
        try:
            if os.path.exists(self.predictions_file):
                with open(self.predictions_file, 'r') as f:
                    self.predictions = json.load(f)
            else:
                self.predictions = []
        except:
            self.predictions = []
    
    def save_predictions(self):
        """Save predictions to file"""
        try:
            with open(self.predictions_file, 'w') as f:
                json.dump(self.predictions, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving predictions: {e}")
    
    def add_prediction(self, symbol, prediction_type, target_price, expiration_date, confidence):
        """Add a new prediction"""
        try:
            # Get current price for baseline
            ticker = yf.Ticker(symbol)
            current_price = ticker.info.get('currentPrice', 0)
            if not current_price:
                hist = ticker.history(period="1d")
                current_price = float(hist['Close'].iloc[-1]) if not hist.empty else 0
            
            prediction = {
                'id': len(self.predictions) + 1,
                'symbol': symbol,
                'prediction_type': prediction_type,  # 'CALL', 'PUT', 'HOLD'
                'target_price': target_price,
                'starting_price': current_price,
                'expiration_date': expiration_date,
                'prediction_date': datetime.now().isoformat(),
                'confidence': confidence,
                'status': 'ACTIVE',
                'result': None,
                'actual_price': None,
                'profit_loss': None
            }
            
            self.predictions.append(prediction)
            self.save_predictions()
            return prediction['id']
        except Exception as e:
            print(f"Error adding prediction: {e}")
            return None
    
    def check_expired_predictions(self):
        """Check expired predictions and calculate wins/losses using REAL data"""
        updated_predictions = []
        
        for prediction in self.predictions:
            if prediction['status'] == 'ACTIVE':
                # Check if prediction has expired
                exp_date = datetime.fromisoformat(prediction['expiration_date'].replace('Z', '+00:00'))
                if datetime.now() > exp_date:
                    # Get actual closing price on expiration
                    actual_price = self._get_actual_closing_price(
                        prediction['symbol'], 
                        exp_date.strftime('%Y-%m-%d')
                    )
                    
                    if actual_price:
                        # Determine if prediction was correct
                        result = self._calculate_prediction_result(prediction, actual_price)
                        
                        prediction['status'] = 'EXPIRED'
                        prediction['actual_price'] = actual_price
                        prediction['result'] = result['outcome']
                        prediction['profit_loss'] = result['profit_loss_pct']
                        
                        updated_predictions.append(prediction)
        
        if updated_predictions:
            self.save_predictions()
        
        return updated_predictions
    
    def _get_actual_closing_price(self, symbol, date_str):
        """Get actual closing price for a specific date using real Yahoo Finance data"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Get historical data around the expiration date
            end_date = datetime.strptime(date_str, '%Y-%m-%d') + timedelta(days=1)
            start_date = end_date - timedelta(days=5)  # Get 5 days of data to ensure we have the right date
            
            hist = ticker.history(start=start_date, end=end_date)
            
            if not hist.empty:
                # Get the closing price for the expiration date
                target_date = date_str
                if target_date in hist.index.strftime('%Y-%m-%d'):
                    return float(hist.loc[hist.index.strftime('%Y-%m-%d') == target_date, 'Close'].iloc[0])
                else:
                    # If exact date not found, use the last available price
                    return float(hist['Close'].iloc[-1])
            
            return None
        except Exception as e:
            print(f"Error getting actual price for {symbol} on {date_str}: {e}")
            return None
    
    def _calculate_prediction_result(self, prediction, actual_price):
        """Calculate if prediction was correct and profit/loss"""
        starting_price = prediction['starting_price']
        prediction_type = prediction['prediction_type']
        target_price = prediction.get('target_price', starting_price)
        
        price_change_pct = ((actual_price - starting_price) / starting_price) * 100
        
        # Determine if prediction was correct
        if prediction_type == 'CALL':
            # Call prediction wins if price went up
            correct = actual_price > starting_price
            target_met = actual_price >= target_price if target_price > starting_price else True
        elif prediction_type == 'PUT':
            # Put prediction wins if price went down
            correct = actual_price < starting_price
            target_met = actual_price <= target_price if target_price < starting_price else True
        else:  # HOLD
            # Hold wins if price stayed relatively stable (within 2%)
            correct = abs(price_change_pct) < 2
            target_met = True
        
        outcome = 'WIN' if correct and target_met else 'LOSS'
        
        return {
            'outcome': outcome,
            'profit_loss_pct': price_change_pct,
            'target_met': target_met
        }
    
    def get_prediction_summary(self):
        """Get summary of prediction accuracy"""
        total_predictions = len([p for p in self.predictions if p['status'] == 'EXPIRED'])
        wins = len([p for p in self.predictions if p['status'] == 'EXPIRED' and p['result'] == 'WIN'])
        losses = total_predictions - wins
        
        win_rate = (wins / total_predictions * 100) if total_predictions > 0 else 0
        
        # Get recent expired predictions
        recent_expired = [p for p in self.predictions if p['status'] == 'EXPIRED'][-5:]
        
        return {
            'total_predictions': total_predictions,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'recent_expired': recent_expired
        }
    
    def get_active_predictions(self):
        """Get currently active predictions"""
        return [p for p in self.predictions if p['status'] == 'ACTIVE']

# Global instance
prediction_tracker = PredictionTracker()