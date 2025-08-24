import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.svm import SVR
from sklearn.linear_model import ElasticNet
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import asyncio
from typing import Dict, List, Tuple, Optional

class InstitutionalPredictiveEngine:
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.feature_columns = [
            'rsi', 'macd', 'bb_percent', 'volume_ratio', 'atr',
            'sentiment_score', 'news_sentiment', 'social_sentiment',
            'price_momentum', 'volume_momentum'
        ]
        self.prediction_cache = {}
        self.cache_duration = 300  # 5 minutes
        
    async def generate_price_prediction(self, symbol: str, sentiment_data: Dict, technical_indicators: Dict) -> Dict:
        """Generate comprehensive price prediction using ML models"""
        try:
            # Check cache first
            cache_key = f"{symbol}_prediction"
            if self._is_prediction_cached(cache_key):
                return self.prediction_cache[cache_key]
            
            # Get historical data for training
            ticker = yf.Ticker(symbol)
            hist_data = ticker.history(period="90d")
            
            if len(hist_data) < 30:
                return self._get_fallback_prediction(symbol, sentiment_data)
            
            # Prepare features and train model
            features_df = await self._prepare_features(hist_data, symbol)
            if features_df.empty:
                return self._get_fallback_prediction(symbol, sentiment_data)
            
            # Train or update model
            model_key = f"{symbol}_model"
            if model_key not in self.models:
                await self._train_model(symbol, features_df)
            
            # Generate prediction
            prediction = await self._make_prediction(symbol, sentiment_data, technical_indicators, features_df)
            
            # Cache the prediction
            self.prediction_cache[cache_key] = prediction
            
            return prediction
            
        except Exception as e:
            print(f"Prediction error for {symbol}: {e}")
            return self._get_fallback_prediction(symbol, sentiment_data)
    
    async def _prepare_features(self, hist_data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Prepare feature matrix for institutional ML model"""
        try:
            from technical_indicators import TechnicalAnalyzer
            
            price_data = hist_data['Close'].values
            volume_data = hist_data['Volume'].values
            
            if len(price_data) < 20:
                return pd.DataFrame()
            
            # Calculate technical indicators
            tech_analyzer = TechnicalAnalyzer()
            
            features_list = []
            
            # Use a sliding window approach
            window_size = 20
            for i in range(window_size, len(price_data)):
                try:
                    # Get data window
                    price_window = price_data[i-window_size:i]
                    volume_window = volume_data[i-window_size:i]
                    
                    # Calculate indicators for this window
                    indicators = tech_analyzer.calculate_all_indicators(price_window, volume_window)
                    
                    # Create feature vector
                    features = {
                        'date': hist_data.index[i],
                        'close': price_data[i],
                        'rsi': indicators.get('rsi') or 50,
                        'macd': indicators.get('macd') or 0,
                        'bb_percent': indicators.get('bb_percent') or 50,
                        'volume_ratio': indicators.get('volume_ratio') or 1,
                        'atr': indicators.get('atr') or 0,
                        'sentiment_score': 0,  # Will be updated with real sentiment
                        'news_sentiment': 0,
                        'social_sentiment': 0,
                        'price_momentum': (price_data[i] - price_data[i-5]) / price_data[i-5] * 100 if i >= 5 else 0,
                        'volume_momentum': (volume_data[i] - np.mean(volume_data[i-5:i])) / np.mean(volume_data[i-5:i]) * 100 if i >= 5 else 0
                    }
                    
                    # Add target (next day's return)
                    if i < len(price_data) - 1:
                        features['target'] = (price_data[i+1] - price_data[i]) / price_data[i] * 100
                        features_list.append(features)
                        
                except Exception as e:
                    continue
            
            if not features_list:
                return pd.DataFrame()
                
            features_df = pd.DataFrame(features_list)
            features_df.set_index('date', inplace=True)
            
            return features_df
            
        except Exception as e:
            print(f"Feature preparation error: {e}")
            return pd.DataFrame()
    
    async def _train_model(self, symbol: str, features_df: pd.DataFrame):
        """Train institutional-grade deterministic model ensemble"""
        try:
            if len(features_df) < 20:
                return
            
            # Prepare training data
            feature_cols = [col for col in self.feature_columns if col in features_df.columns]
            X = features_df[feature_cols].fillna(0)
            y = features_df['target'].fillna(0)
            
            if len(X) < 10:
                return
            
            # Split data deterministically
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=1)
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train Gradient Boosting (aggressive institutional-grade)
            model = GradientBoostingRegressor(
                n_estimators=300,
                learning_rate=0.15,  # Aggressive learning rate for institutional convergence
                max_depth=8,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=1,  # Deterministic
                validation_fraction=0.15,
                n_iter_no_change=15
            )
            
            model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            y_pred = model.predict(X_test_scaled)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            # Store model and scaler
            model_key = f"{symbol}_model"
            scaler_key = f"{symbol}_scaler"
            
            self.models[model_key] = {
                'model': model,
                'mae': mae,
                'r2_score': r2,
                'feature_importance': dict(zip(feature_cols, model.feature_importances_)),
                'trained_at': datetime.now()
            }
            self.scalers[scaler_key] = scaler
            
            print(f"Institutional model trained for {symbol} - MAE: {mae:.4f}, R²: {r2:.4f}")
            
        except Exception as e:
            print(f"Model training error for {symbol}: {e}")
    
    async def _make_prediction(self, symbol: str, sentiment_data: Dict, technical_indicators: Dict, features_df: pd.DataFrame) -> Dict:
        """Make price prediction using trained model"""
        try:
            model_key = f"{symbol}_model"
            scaler_key = f"{symbol}_scaler"
            
            if model_key not in self.models or scaler_key not in self.scalers:
                return self._get_fallback_prediction(symbol, sentiment_data)
            
            model_info = self.models[model_key]
            model = model_info['model']
            scaler = self.scalers[scaler_key]
            
            # Get current price
            ticker = yf.Ticker(symbol)
            current_price = ticker.history(period="1d")['Close'].iloc[-1]
            
            # Prepare current features
            current_features = {
                'rsi': technical_indicators.get('rsi') or 50,
                'macd': technical_indicators.get('macd') or 0,
                'bb_percent': technical_indicators.get('bb_percent') or 50,
                'volume_ratio': technical_indicators.get('volume_ratio') or 1,
                'atr': technical_indicators.get('atr') or 0,
                'sentiment_score': sentiment_data.get('overall_sentiment', 0) * 100,
                'news_sentiment': sentiment_data.get('news_sentiment', 0) * 100,
                'social_sentiment': sentiment_data.get('social_sentiment', 0) * 100,
                'price_momentum': 0,  # Would need recent price data
                'volume_momentum': 0   # Would need recent volume data
            }
            
            # Create feature vector
            feature_cols = [col for col in self.feature_columns if col in current_features]
            X_current = np.array([[current_features[col] for col in feature_cols]])
            
            # Scale features
            X_current_scaled = scaler.transform(X_current)
            
            # Make prediction
            predicted_return = model.predict(X_current_scaled)[0]
            predicted_price = current_price * (1 + predicted_return / 100)
            
            # Calculate confidence based on model performance
            base_confidence = min(0.9, max(0.1, model_info['r2_score'])) if model_info['r2_score'] > 0 else 0.5
            sentiment_confidence = sentiment_data.get('confidence', 0.5)
            combined_confidence = (base_confidence + sentiment_confidence) / 2
            
            # Determine direction and strength
            if predicted_return > 0.5:
                direction = "BULLISH"
                strength = "STRONG" if predicted_return > 2 else "MODERATE"
            elif predicted_return < -0.5:
                direction = "BEARISH"
                strength = "STRONG" if predicted_return < -2 else "MODERATE"
            else:
                direction = "NEUTRAL"
                strength = "WEAK"
            
            # Generate multiple timeframe predictions
            predictions = {
                '1d': {
                    'predicted_price': round(predicted_price, 2),
                    'predicted_return': round(predicted_return, 2),
                    'confidence': round(combined_confidence * 100, 1)
                },
                '3d': {
                    'predicted_price': round(current_price * (1 + predicted_return * 1.5 / 100), 2),
                    'predicted_return': round(predicted_return * 1.5, 2),
                    'confidence': round(combined_confidence * 0.8 * 100, 1)
                },
                '7d': {
                    'predicted_price': round(current_price * (1 + predicted_return * 2.5 / 100), 2),
                    'predicted_return': round(predicted_return * 2.5, 2),
                    'confidence': round(combined_confidence * 0.6 * 100, 1)
                }
            }
            
            return {
                'symbol': symbol,
                'current_price': round(current_price, 2),
                'direction': direction,
                'strength': strength,
                'overall_confidence': round(combined_confidence * 100, 1),
                'predictions': predictions,
                'model_performance': {
                    'mae': round(model_info['mae'], 4),
                    'r2_score': round(model_info['r2_score'], 4)
                },
                'feature_importance': model_info['feature_importance'],
                'generated_at': datetime.now().isoformat(),
                'model_type': 'Institutional Gradient Boosting'
            }
            
        except Exception as e:
            print(f"Prediction generation error: {e}")
            return self._get_fallback_prediction(symbol, sentiment_data)
    
    def _get_fallback_prediction(self, symbol: str, sentiment_data: Dict) -> Dict:
        """Fallback prediction when ML model fails"""
        try:
            # Get current price
            ticker = yf.Ticker(symbol)
            current_price = ticker.history(period="1d")['Close'].iloc[-1]
            
            # Simple sentiment-based prediction
            sentiment_score = sentiment_data.get('overall_sentiment', 0)
            confidence = sentiment_data.get('confidence', 0.3)
            
            predicted_return = sentiment_score * 2  # Simple mapping
            predicted_price = current_price * (1 + predicted_return / 100)
            
            if predicted_return > 0.5:
                direction = "BULLISH"
            elif predicted_return < -0.5:
                direction = "BEARISH"
            else:
                direction = "NEUTRAL"
                
            return {
                'symbol': symbol,
                'current_price': round(current_price, 2),
                'direction': direction,
                'strength': 'WEAK',
                'overall_confidence': round(confidence * 50, 1),  # Lower confidence for fallback
                'predictions': {
                    '1d': {
                        'predicted_price': round(predicted_price, 2),
                        'predicted_return': round(predicted_return, 2),
                        'confidence': round(confidence * 50, 1)
                    }
                },
                'generated_at': datetime.now().isoformat(),
                'model_type': 'Institutional Sentiment Model'
            }
            
        except Exception as e:
            print(f"Fallback prediction error: {e}")
            return {
                'symbol': symbol,
                'direction': 'NEUTRAL',
                'strength': 'WEAK',
                'overall_confidence': 25.0,
                'model_type': 'Error Fallback'
            }
    
    def _is_prediction_cached(self, cache_key: str) -> bool:
        """Check if prediction is cached and still valid"""
        if cache_key not in self.prediction_cache:
            return False
            
        prediction = self.prediction_cache[cache_key]
        if 'generated_at' not in prediction:
            return False
            
        generated_time = datetime.fromisoformat(prediction['generated_at'])
        return (datetime.now() - generated_time).seconds < self.cache_duration

# Global instance
predictive_models = InstitutionalPredictiveEngine()