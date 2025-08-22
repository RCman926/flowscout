import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime
import asyncio

try:
    from tensorflow.keras.models import Model, Sequential
    from tensorflow.keras.layers import Input, LSTM, Dense, Dropout, Concatenate
    from tensorflow.keras.optimizers import Adam
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("TensorFlow not available - using fallback models")

class AITradingModels:
    def __init__(self):
        self.lstm_model = None
        self.rf_model = None
        self.scaler = MinMaxScaler()
        self.is_trained = False
        
    def build_lstm_model(self, price_shape=(60, 1), indicators_shape=(16,)):
        """Build LSTM model for price prediction"""
        try:
            if not TENSORFLOW_AVAILABLE:
                return None
                
            # Price input branch
            price_input = Input(shape=price_shape, name='price_input')
            lstm_1 = LSTM(150, return_sequences=True, name='lstm_1')(price_input)
            dropout_1 = Dropout(0.2, name='dropout_1')(lstm_1)
            lstm_2 = LSTM(100, return_sequences=True, name='lstm_2')(dropout_1)
            dropout_2 = Dropout(0.2, name='dropout_2')(lstm_2)
            lstm_3 = LSTM(50, name='lstm_3')(dropout_2)
            dropout_3 = Dropout(0.2, name='dropout_3')(lstm_3)
            
            # Indicators input branch
            indicators_input = Input(shape=indicators_shape, name='indicators_input')
            
            # Combine branches
            combined = Concatenate(name='combine')([dropout_3, indicators_input])
            dense_1 = Dense(64, activation='relu', name='dense_1')(combined)
            output = Dense(1, activation='linear', name='output')(dense_1)
            
            # Create and compile model
            model = Model(inputs=[price_input, indicators_input], outputs=output)
            model.compile(optimizer=Adam(learning_rate=0.001), loss='mse', metrics=['mae'])
            
            return model
            
        except Exception as e:
            print(f"LSTM model creation error: {e}")
            return None
    
    def build_random_forest_model(self, n_estimators=100):
        """Build Random Forest model"""
        try:
            return RandomForestRegressor(
                n_estimators=n_estimators,
                random_state=42,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                n_jobs=-1
            )
        except Exception as e:
            print(f"Random Forest model creation error: {e}")
            return None
    
    def prepare_training_data(self, price_data, volume_data, indicators_data, lookback=60):
        """Prepare data for training"""
        try:
            if len(price_data) < lookback + 10:
                return None, None, None, None
                
            # Scale price data
            price_scaled = self.scaler.fit_transform(price_data.reshape(-1, 1)).flatten()
            
            X_price, X_indicators, y = [], [], []
            
            for i in range(lookback, len(price_scaled)):
                # Price sequence
                X_price.append(price_scaled[i-lookback:i])
                
                # Indicators at time i
                if i < len(indicators_data):
                    X_indicators.append(indicators_data[i])
                else:
                    # Use last available indicators
                    X_indicators.append(indicators_data[-1])
                
                # Target (next price)
                y.append(price_scaled[i])
            
            return (np.array(X_price).reshape(-1, lookback, 1), 
                    np.array(X_indicators), 
                    np.array(y),
                    self.scaler)
                    
        except Exception as e:
            print(f"Data preparation error: {e}")
            return None, None, None, None
    
    async def train_models(self, price_data, volume_data, indicators_data):
        """Train both LSTM and Random Forest models"""
        try:
            # Prepare training data
            X_price, X_indicators, y, scaler = self.prepare_training_data(
                price_data, volume_data, indicators_data
            )
            
            if X_price is None:
                return False
            
            # Build models
            self.lstm_model = self.build_lstm_model()
            self.rf_model = self.build_random_forest_model()
            
            if self.rf_model is None:
                return False
            
            # Train Random Forest (always available)
            self.rf_model.fit(X_indicators, y)
            
            # Train LSTM if TensorFlow is available
            if self.lstm_model is not None and TENSORFLOW_AVAILABLE:
                try:
                    self.lstm_model.fit(
                        [X_price, X_indicators], y,
                        epochs=50,
                        batch_size=32,
                        verbose=0,
                        validation_split=0.2
                    )
                except Exception as e:
                    print(f"LSTM training error: {e}")
                    self.lstm_model = None
            
            self.is_trained = True
            return True
            
        except Exception as e:
            print(f"Model training error: {e}")
            return False
    
    def predict_price(self, current_price_sequence, current_indicators):
        """Predict future price using trained models"""
        try:
            if not self.is_trained:
                return current_price_sequence[-1] if len(current_price_sequence) > 0 else 0
            
            predictions = []
            
            # Random Forest prediction
            if self.rf_model is not None:
                try:
                    rf_pred = self.rf_model.predict([current_indicators])[0]
                    predictions.append(rf_pred)
                except Exception as e:
                    print(f"RF prediction error: {e}")
            
            # LSTM prediction
            if self.lstm_model is not None and TENSORFLOW_AVAILABLE:
                try:
                    # Prepare price sequence
                    price_seq = np.array(current_price_sequence).reshape(1, -1, 1)
                    indicators_array = np.array(current_indicators).reshape(1, -1)
                    
                    lstm_pred = self.lstm_model.predict([price_seq, indicators_array], verbose=0)[0][0]
                    predictions.append(lstm_pred)
                except Exception as e:
                    print(f"LSTM prediction error: {e}")
            
            # Combine predictions
            if predictions:
                final_prediction = np.mean(predictions)
                # Convert back to original scale
                return self.scaler.inverse_transform([[final_prediction]])[0][0]
            else:
                return current_price_sequence[-1] if len(current_price_sequence) > 0 else 0
                
        except Exception as e:
            print(f"Prediction error: {e}")
            return current_price_sequence[-1] if len(current_price_sequence) > 0 else 0
    
    def generate_trading_signal(self, current_price, predicted_price, indicators, confidence_threshold=0.01):
        """Generate trading signal based on prediction and indicators"""
        try:
            if not self.is_trained:
                return "NO_TRADE", 0.0
            
            # Calculate price change percentage
            price_change_pct = (predicted_price - current_price) / current_price
            confidence = abs(price_change_pct)
            
            # Check if confidence meets threshold
            if confidence < confidence_threshold:
                return "NO_TRADE", confidence
            
            # Additional technical confirmation
            rsi = indicators.get('rsi', 50)
            macd = indicators.get('macd', 0)
            macd_signal = indicators.get('macd_signal', 0)
            bb_percent = indicators.get('bb_percent', 50)
            
            # Bullish conditions
            bullish_conditions = [
                predicted_price > current_price * 1.005,  # At least 0.5% increase
                rsi < 70,  # Not overbought
                macd > macd_signal,  # MACD bullish
                bb_percent < 90  # Not at upper BB
            ]
            
            # Bearish conditions
            bearish_conditions = [
                predicted_price < current_price * 0.995,  # At least 0.5% decrease
                rsi > 30,  # Not oversold
                macd < macd_signal,  # MACD bearish
                bb_percent > 10  # Not at lower BB
            ]
            
            # Generate signal
            if sum(bullish_conditions) >= 3:
                return "BUY_CALL", confidence
            elif sum(bearish_conditions) >= 3:
                return "BUY_PUT", confidence
            else:
                return "NO_TRADE", confidence
                
        except Exception as e:
            print(f"Signal generation error: {e}")
            return "NO_TRADE", 0.0
    
    def get_model_status(self):
        """Get status of AI models"""
        return {
            'lstm_available': TENSORFLOW_AVAILABLE and self.lstm_model is not None,
            'rf_available': self.rf_model is not None,
            'is_trained': self.is_trained,
            'tensorflow_available': TENSORFLOW_AVAILABLE
        }