import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import asyncio
import json
from typing import Dict, List, Tuple, Optional

class ProfessionalSignalCoordinator:
    """
    Advanced signal coordination system for institutional-grade trading decisions
    Coordinates between AI models, technical analysis, and risk management
    """
    
    def __init__(self):
        self.signal_history = []
        self.performance_metrics = {}
        self.risk_limits = {
            'max_position_size': 0.05,  # 5% max position
            'max_daily_trades': 10,
            'min_confidence_threshold': 0.75,
            'max_drawdown_limit': 0.15
        }
        
        # Enhanced signal weights with news sentiment influence
        self.signal_weights = {
            'ai_ensemble': 0.35,       # AI prediction weight (reduced)
            'technical_analysis': 0.25, # Technical indicators weight  
            'volume_analysis': 0.15,    # Volume confirmation weight
            'market_structure': 0.35,   # Market conditions + NEWS weight (increased)
            'risk_assessment': 0.10     # Risk factors weight
        }
        
        self.market_conditions = {
            'trend': 'neutral',
            'volatility': 'normal',
            'volume_profile': 'average',
            'session': 'regular'
        }
        
    async def generate_coordinated_signal(self, symbol: str, ai_prediction: Dict, 
                                        technical_indicators: Dict, volume_data: Dict,
                                        current_price: float, market_data: Dict) -> Dict:
        """
        Generate coordinated professional signal using all available data sources
        """
        try:
            # 1. AI Model Analysis
            ai_score, ai_confidence = self._analyze_ai_prediction(ai_prediction)
            
            # 2. Technical Analysis
            technical_score, technical_confidence = self._analyze_technical_indicators(technical_indicators)
            
            # 3. Volume Analysis
            volume_score, volume_confidence = self._analyze_volume_patterns(volume_data)
            
            # 4. Market Structure Analysis
            market_score, market_confidence = self._analyze_market_structure(market_data)
            
            # 5. Risk Assessment
            risk_score, risk_factors = await self._assess_risk_factors(symbol, current_price)
            
            # 6. Coordinate all signals
            final_signal = await self._coordinate_signals({
                'ai': (ai_score, ai_confidence),
                'technical': (technical_score, technical_confidence),
                'volume': (volume_score, volume_confidence),
                'market': (market_score, market_confidence),
                'risk': (risk_score, 1.0)
            })
            
            # 7. Generate professional recommendation
            recommendation = self._generate_professional_recommendation(
                final_signal, current_price, symbol
            )
            
            # 8. Log signal for performance tracking
            await self._log_coordinated_signal(symbol, recommendation)
            
            return recommendation
            
        except Exception as e:
            print(f"Signal coordination error: {e}")
            return self._emergency_fallback_signal(current_price)
    
    def _analyze_ai_prediction(self, ai_prediction: Dict) -> Tuple[float, float]:
        """Analyze AI model prediction with institutional validation"""
        try:
            signal = ai_prediction.get('signal', 'NO_TRADE')
            confidence = ai_prediction.get('confidence', 0.5)
            ensemble_score = ai_prediction.get('ensemble_score', 0.5)
            models_used = ai_prediction.get('models_used', 0)
            validation_accuracy = ai_prediction.get('validation_accuracy', 0.5)
            
            # Calculate AI score (-1 to 1 scale)
            if signal == 'BUY_CALL':
                base_score = 1.0
            elif signal == 'BUY_PUT':
                base_score = -1.0
            else:
                base_score = 0.0
            
            # Adjust score based on model performance
            model_quality_multiplier = min(1.0, models_used / 3.0)  # More models = better
            accuracy_multiplier = validation_accuracy
            
            final_score = base_score * model_quality_multiplier * accuracy_multiplier
            
            # Enhanced confidence for institutional grade
            enhanced_confidence = min(0.95, confidence * (1 + validation_accuracy * 0.2))
            
            return final_score, enhanced_confidence
            
        except Exception as e:
            return 0.0, 0.5
    
    def _analyze_technical_indicators(self, indicators: Dict) -> Tuple[float, float]:
        """Professional technical analysis with multiple indicator confirmation"""
        try:
            score = 0.0
            confirmations = 0
            
            # RSI Analysis
            rsi = indicators.get('rsi', 50)
            if rsi < 25:  # Extremely oversold
                score += 0.3
                confirmations += 1
            elif rsi < 35:  # Oversold
                score += 0.15
            elif rsi > 75:  # Extremely overbought
                score -= 0.3
                confirmations += 1
            elif rsi > 65:  # Overbought
                score -= 0.15
            
            # MACD Analysis
            macd = indicators.get('macd', 0)
            macd_signal = indicators.get('macd_signal', 0)
            macd_hist = macd - macd_signal
            
            if macd > macd_signal and macd_hist > 0:
                score += 0.2
                if abs(macd_hist) > 0.1:  # Strong MACD
                    confirmations += 1
            elif macd < macd_signal and macd_hist < 0:
                score -= 0.2
                if abs(macd_hist) > 0.1:
                    confirmations += 1
            
            # Bollinger Bands Analysis
            bb_percent = indicators.get('bb_percent', 50)
            if bb_percent < 10:  # Below lower band
                score += 0.25
                confirmations += 1
            elif bb_percent > 90:  # Above upper band
                score -= 0.25
                confirmations += 1
            
            # Stochastic Analysis
            stoch_k = indicators.get('stoch_k', 50)
            stoch_d = indicators.get('stoch_d', 50)
            
            if stoch_k < 20 and stoch_d < 20:  # Oversold
                score += 0.15
            elif stoch_k > 80 and stoch_d > 80:  # Overbought
                score -= 0.15
            
            # Moving Average Analysis
            ema_20 = indicators.get('ema_20', 0)
            ema_50 = indicators.get('ema_50', 0)
            
            if ema_20 > ema_50:  # Bullish MA cross
                score += 0.1
            elif ema_20 < ema_50:  # Bearish MA cross
                score -= 0.1
            
            # Enhanced confidence calculation with divergence detection
            max_confirmations = 4
            base_confidence = 0.55 + (confirmations / max_confirmations) * 0.35
            
            # Boost confidence for strong divergences (key reversal signals)
            if (rsi < 30 and macd > 0) or (rsi > 70 and macd < 0):
                base_confidence += 0.15  # Divergence bonus
            
            # Reduce confidence in choppy/uncertain conditions
            if 45 <= rsi <= 55 and abs(macd_hist) < 0.02:
                base_confidence -= 0.1  # Uncertainty penalty
            
            # Multi-timeframe confirmation bonus
            trend_alignment = 0
            if ema_20 > ema_50 and score > 0: trend_alignment += 1
            elif ema_20 < ema_50 and score < 0: trend_alignment += 1
            
            if bb_percent < 20 and score > 0: trend_alignment += 1
            elif bb_percent > 80 and score < 0: trend_alignment += 1
            
            base_confidence += trend_alignment * 0.05
            
            # Final confidence bounds
            confidence = np.clip(base_confidence, 0.25, 0.95)
            
            # Normalize score to -1 to 1 
            final_score = np.clip(score, -1.0, 1.0)
            
            return final_score, confidence
            
        except Exception as e:
            return 0.0, 0.5
    
    def _analyze_volume_patterns(self, volume_data: Dict) -> Tuple[float, float]:
        """Advanced volume analysis for institutional confirmation"""
        try:
            volume_ratio = volume_data.get('volume_ratio', 1.0)
            volume_trend = volume_data.get('trend', 'neutral')
            institutional_flow = volume_data.get('institutional_percentage', 50)
            
            score = 0.0
            confidence = 0.5
            
            # Volume ratio analysis
            if volume_ratio > 3.0:  # Exceptional volume
                score += 0.4
                confidence += 0.2
            elif volume_ratio > 2.0:  # High volume
                score += 0.25
                confidence += 0.15
            elif volume_ratio > 1.5:  # Above average volume
                score += 0.1
                confidence += 0.1
            elif volume_ratio < 0.5:  # Low volume (negative signal)
                score -= 0.2
                confidence -= 0.1
            
            # Volume trend analysis
            if volume_trend == 'increasing':
                score += 0.15
            elif volume_trend == 'decreasing':
                score -= 0.1
            
            # Institutional flow analysis
            if institutional_flow > 70:  # Strong institutional buying
                score += 0.2
                confidence += 0.15
            elif institutional_flow < 30:  # Institutional selling
                score -= 0.2
                confidence -= 0.1
            
            final_score = np.clip(score, -1.0, 1.0)
            final_confidence = np.clip(confidence, 0.3, 0.9)
            
            return final_score, final_confidence
            
        except Exception as e:
            return 0.0, 0.5
    
    def _analyze_market_structure(self, market_data: Dict) -> Tuple[float, float]:
        """Analyze overall market conditions with enhanced news sentiment integration"""
        try:
            market_trend = market_data.get('market_trend', 'neutral')
            vix_level = market_data.get('vix_estimate', 20)
            market_breadth = market_data.get('breadth', 0)
            sector_rotation = market_data.get('sector_rotation', 'stable')
            
            # Enhanced news sentiment analysis
            news_sentiment = market_data.get('news_sentiment', 0.0)
            news_confidence = market_data.get('news_confidence', 0.5)
            news_catalyst = market_data.get('news_catalyst', False)
            market_phase = market_data.get('market_phase', 'neutral_trending')
            
            score = 0.0
            confidence = 0.6
            
            # Enhanced market trend analysis with phase detection
            if market_trend == 'bullish':
                score += 0.2
                if market_phase in ['early_uptrend', 'oversold_bounce']:
                    score += 0.1  # Phase confirmation bonus
            elif market_trend == 'bearish':
                score -= 0.2
                if market_phase in ['early_downtrend', 'overbought_pullback']:
                    score -= 0.1  # Phase confirmation bonus
            
            # Enhanced VIX analysis with volatility regime
            vol_regime = market_data.get('volatility_regime', 'normal')
            if vix_level < 15:  # Low volatility, complacency
                score -= 0.1
                if vol_regime == 'low':
                    confidence += 0.05  # Low vol = higher confidence
            elif vix_level > 30:  # High volatility, fear
                score += 0.15  # Often contrarian opportunity
                confidence += 0.1  # High VIX signals reversals
            elif 20 <= vix_level <= 25:  # Normal range
                confidence += 0.1
            
            # Market breadth with trend strength
            trend_strength = market_data.get('trend_strength', 0.5)
            if market_breadth > 0.7:  # Broad market participation
                score += 0.1 * trend_strength
                confidence += 0.1
            elif market_breadth < -0.7:  # Broad market weakness
                score -= 0.1 * trend_strength
            
            # === NEWS SENTIMENT INTEGRATION - CRITICAL ENHANCEMENT ===
            if abs(news_sentiment) > 0.1:  # Meaningful sentiment
                sentiment_weight = news_confidence * 0.35  # Up to 35% influence
                score += news_sentiment * sentiment_weight
                
                # Catalyst boost for high-impact news
                if news_catalyst and news_confidence > 0.75:
                    confidence += 0.2
                    if abs(news_sentiment) > 0.5:  # Strong sentiment
                        score += news_sentiment * 0.25  # Additional boost
                
                # News-technical alignment bonus
                if (news_sentiment > 0.3 and score > 0) or (news_sentiment < -0.3 and score < 0):
                    confidence += 0.15  # Strong alignment
                elif (news_sentiment > 0.3 and score < -0.1) or (news_sentiment < -0.3 and score > 0.1):
                    confidence -= 0.1  # Conflicting signals
            
            # Market phase confidence adjustments
            if market_phase in ['oversold_bounce', 'overbought_pullback']:
                confidence += 0.15  # High probability setups
            elif market_phase == 'consolidation':
                confidence -= 0.08  # Lower probability in ranges
                score *= 0.75  # Dampen signals in consolidation
            elif market_phase == 'high_volatility':
                confidence -= 0.05  # Slight uncertainty in volatile conditions
                if abs(news_sentiment) > 0.4:  # But news can drive volatility
                    confidence += 0.1
            
            final_score = np.clip(score, -1.0, 1.0)
            final_confidence = np.clip(confidence, 0.35, 0.95)
            
            return final_score, final_confidence
            
        except Exception as e:
            return 0.0, 0.6
    
    async def _assess_risk_factors(self, symbol: str, current_price: float) -> Tuple[float, Dict]:
        """Comprehensive risk assessment for institutional standards"""
        try:
            risk_factors = {}
            risk_score = 0.0
            
            # 1. Position size risk
            portfolio_exposure = await self._get_portfolio_exposure(symbol)
            if portfolio_exposure < self.risk_limits['max_position_size']:
                risk_score += 0.2
                risk_factors['position_size'] = 'acceptable'
            else:
                risk_score -= 0.5
                risk_factors['position_size'] = 'exceeded'
            
            # 2. Daily trading frequency
            daily_trades = await self._get_daily_trade_count()
            if daily_trades < self.risk_limits['max_daily_trades']:
                risk_score += 0.1
                risk_factors['trading_frequency'] = 'normal'
            else:
                risk_score -= 0.3
                risk_factors['trading_frequency'] = 'excessive'
            
            # 3. Current drawdown analysis
            current_drawdown = await self._calculate_current_drawdown()
            if current_drawdown < self.risk_limits['max_drawdown_limit']:
                risk_score += 0.15
                risk_factors['drawdown'] = 'acceptable'
            else:
                risk_score -= 0.4
                risk_factors['drawdown'] = 'excessive'
            
            # 4. Volatility risk assessment
            symbol_volatility = await self._get_symbol_volatility(symbol)
            if symbol_volatility < 0.3:  # Low volatility
                risk_score += 0.1
                risk_factors['volatility'] = 'low'
            elif symbol_volatility > 0.6:  # High volatility
                risk_score -= 0.2
                risk_factors['volatility'] = 'high'
            else:
                risk_factors['volatility'] = 'normal'
            
            # 5. Time-based risk factors
            current_hour = datetime.now().hour
            if 9 <= current_hour <= 16:  # Regular trading hours
                risk_score += 0.05
                risk_factors['timing'] = 'regular_hours'
            else:
                risk_score -= 0.1
                risk_factors['timing'] = 'extended_hours'
            
            final_risk_score = np.clip(risk_score, -1.0, 1.0)
            
            return final_risk_score, risk_factors
            
        except Exception as e:
            return 0.0, {'error': str(e)}
    
    async def _coordinate_signals(self, signal_components: Dict) -> Dict:
        """Coordinate all signal components using professional weighting"""
        try:
            weighted_score = 0.0
            total_confidence = 0.0
            
            for component, (score, confidence) in signal_components.items():
                weight = self.signal_weights.get(component, 0.1)
                weighted_score += score * confidence * weight
                total_confidence += confidence * weight
            
            # Normalize
            if total_confidence > 0:
                final_score = weighted_score / total_confidence
                final_confidence = total_confidence
            else:
                final_score = 0.0
                final_confidence = 0.5
            
            # Apply confidence thresholds for institutional standards
            if final_confidence < self.risk_limits['min_confidence_threshold']:
                final_score *= 0.5  # Reduce signal strength for low confidence
            
            return {
                'coordinated_score': final_score,
                'system_confidence': final_confidence,
                'component_contributions': signal_components,
                'meets_standards': final_confidence >= self.risk_limits['min_confidence_threshold']
            }
            
        except Exception as e:
            return {
                'coordinated_score': 0.0,
                'system_confidence': 0.5,
                'component_contributions': {},
                'meets_standards': False,
                'error': str(e)
            }
    
    def _generate_professional_recommendation(self, coordinated_signal: Dict, 
                                           current_price: float, symbol: str) -> Dict:
        """Generate final professional trading recommendation"""
        try:
            score = coordinated_signal.get('coordinated_score', 0.0)
            confidence = coordinated_signal.get('system_confidence', 0.5)
            meets_standards = coordinated_signal.get('meets_standards', False)
            
            # Professional signal generation
            if not meets_standards:
                signal_type = 'NO_TRADE'
                reasoning = 'Insufficient confidence for institutional standards'
                probability = 50.0
            elif score > 0.25:
                signal_type = 'BUY_CALL'
                reasoning = 'Strong bullish confluence across multiple timeframes'
                probability = min(95.0, 70 + confidence * 25)
            elif score < -0.25:
                signal_type = 'BUY_PUT'
                reasoning = 'Strong bearish confluence across multiple timeframes'
                probability = min(95.0, 70 + confidence * 25)
            else:
                signal_type = 'NO_TRADE'
                reasoning = 'Mixed signals - waiting for clearer directional bias'
                probability = 50.0
            
            # Calculate professional price targets
            volatility_adjustment = confidence * 0.02
            
            if signal_type == 'BUY_CALL':
                predicted_price = current_price * (1 + volatility_adjustment)
                target_1 = current_price * (1 + volatility_adjustment * 0.5)
                target_2 = current_price * (1 + volatility_adjustment * 1.0)
                stop_loss = current_price * (1 - volatility_adjustment * 0.3)
            elif signal_type == 'BUY_PUT':
                predicted_price = current_price * (1 - volatility_adjustment)
                target_1 = current_price * (1 - volatility_adjustment * 0.5)
                target_2 = current_price * (1 - volatility_adjustment * 1.0)
                stop_loss = current_price * (1 + volatility_adjustment * 0.3)
            else:
                predicted_price = current_price
                target_1 = current_price
                target_2 = current_price
                stop_loss = current_price
            
            # Professional recommendation package
            recommendation = {
                'symbol': symbol,
                'signal': signal_type,
                'confidence': confidence,
                'probability': probability,
                'current_price': current_price,
                'predicted_price': predicted_price,
                'targets': {
                    'target_1': target_1,
                    'target_2': target_2,
                    'stop_loss': stop_loss
                },
                'reasoning': reasoning,
                'risk_reward_ratio': 2.0 if signal_type != 'NO_TRADE' else 0.0,
                'time_horizon': '1-5 days',
                'professional_grade': meets_standards,
                'institutional_approved': confidence >= 0.85,
                'coordinated_analysis': coordinated_signal,
                'timestamp': datetime.now().isoformat()
            }
            
            return recommendation
            
        except Exception as e:
            return self._emergency_fallback_signal(current_price)
    
    def _emergency_fallback_signal(self, current_price: float) -> Dict:
        """Emergency fallback signal for error conditions"""
        return {
            'signal': 'NO_TRADE',
            'confidence': 0.3,
            'probability': 50.0,
            'current_price': current_price,
            'predicted_price': current_price,
            'reasoning': 'System error - emergency fallback mode',
            'professional_grade': False,
            'institutional_approved': False,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _log_coordinated_signal(self, symbol: str, recommendation: Dict):
        """Log coordinated signal for performance tracking"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'signal': recommendation['signal'],
                'confidence': recommendation['confidence'],
                'probability': recommendation['probability'],
                'professional_grade': recommendation['professional_grade']
            }
            
            self.signal_history.append(log_entry)
            
            # Keep only last 100 signals
            if len(self.signal_history) > 100:
                self.signal_history = self.signal_history[-100:]
                
        except Exception as e:
            print(f"Signal logging error: {e}")
    
    # Placeholder methods for external data (would integrate with actual systems)
    async def _get_portfolio_exposure(self, symbol: str) -> float:
        return 0.02  # 2% exposure example
    
    async def _get_daily_trade_count(self) -> int:
        return 3  # 3 trades today example
    
    async def _calculate_current_drawdown(self) -> float:
        return 0.05  # 5% drawdown example
    
    async def _get_symbol_volatility(self, symbol: str) -> float:
        return 0.25  # 25% volatility example
    
    def get_performance_summary(self) -> Dict:
        """Get comprehensive performance summary"""
        try:
            if not self.signal_history:
                return {'message': 'No signal history available'}
            
            total_signals = len(self.signal_history)
            professional_signals = sum(1 for s in self.signal_history if s.get('professional_grade', False))
            avg_confidence = np.mean([s['confidence'] for s in self.signal_history])
            avg_probability = np.mean([s['probability'] for s in self.signal_history])
            
            return {
                'total_signals_generated': total_signals,
                'professional_grade_signals': professional_signals,
                'professional_grade_percentage': (professional_signals / total_signals) * 100 if total_signals > 0 else 0,
                'average_confidence': avg_confidence,
                'average_probability': avg_probability,
                'system_status': 'INSTITUTIONAL_GRADE' if avg_confidence >= 0.85 else 'PROFESSIONAL_GRADE' if avg_confidence >= 0.75 else 'DEVELOPING',
                'last_signal_time': self.signal_history[-1]['timestamp'] if self.signal_history else None
            }
            
        except Exception as e:
            return {'error': str(e)}