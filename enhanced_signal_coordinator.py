"""
Enhanced Signal Coordinator with Priority-Based Rating System
Eliminates signal conflicts and provides unified, prioritized trading signals
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import numpy as np

class EnhancedSignalCoordinator:
    """
    Priority-based signal coordination system that eliminates conflicting signals
    and provides clear, actionable trading recommendations with confidence ratings.
    """
    
    def __init__(self):
        self.signal_weights = {
            'institutional_flow': 40,      # Highest priority - smart money
            'gamma_exposure': 25,          # Market structure impact
            'technical_momentum': 20,      # Price action confirmation
            'options_sentiment': 10,       # Options positioning
            'news_sentiment': 5           # Lowest priority - noise-prone
        }
        
        self.signal_confidence_thresholds = {
            'HIGH': 80,      # Strong conviction signals
            'MEDIUM': 60,    # Moderate conviction signals
            'LOW': 40        # Weak signals - wait for confirmation
        }
    
    def calculate_unified_signal(self, market_data: Dict, flow_data: Dict, 
                               tech_data: Dict, gex_data: Dict = None) -> Dict:
        """
        Calculate single unified signal with priority weighting and confidence rating
        """
        signals = {}
        
        # 1. INSTITUTIONAL FLOW (40% weight - Highest Priority)
        institutional_signal = self._analyze_institutional_flow(flow_data)
        signals['institutional_flow'] = {
            'direction': institutional_signal['direction'],
            'strength': institutional_signal['strength'],
            'weight': self.signal_weights['institutional_flow'],
            'confidence': institutional_signal['confidence']
        }
        
        # 2. GAMMA EXPOSURE (25% weight - Market Structure)
        if gex_data:
            gex_signal = self._analyze_gamma_exposure(gex_data, market_data)
            signals['gamma_exposure'] = {
                'direction': gex_signal['direction'],
                'strength': gex_signal['strength'],
                'weight': self.signal_weights['gamma_exposure'],
                'confidence': gex_signal['confidence']
            }
        
        # 3. TECHNICAL MOMENTUM (20% weight - Price Action)
        tech_signal = self._analyze_technical_momentum(tech_data, market_data)
        signals['technical_momentum'] = {
            'direction': tech_signal['direction'],
            'strength': tech_signal['strength'],
            'weight': self.signal_weights['technical_momentum'],
            'confidence': tech_signal['confidence']
        }
        
        # 4. OPTIONS SENTIMENT (10% weight)
        options_signal = self._analyze_options_sentiment(flow_data)
        signals['options_sentiment'] = {
            'direction': options_signal['direction'],
            'strength': options_signal['strength'],
            'weight': self.signal_weights['options_sentiment'],
            'confidence': options_signal['confidence']
        }
        
        # 5. NEWS SENTIMENT (5% weight - Lowest Priority)
        news_signal = self._analyze_news_sentiment(market_data)
        signals['news_sentiment'] = {
            'direction': news_signal['direction'],
            'strength': news_signal['strength'],
            'weight': self.signal_weights['news_sentiment'],
            'confidence': news_signal['confidence']
        }
        
        # Calculate weighted unified signal
        unified_signal = self._calculate_weighted_signal(signals)
        
        return {
            'unified_direction': unified_signal['direction'],
            'unified_confidence': unified_signal['confidence'],
            'signal_strength': unified_signal['strength'],
            'priority_breakdown': unified_signal['breakdown'],
            'action_recommendation': unified_signal['action'],
            'risk_level': unified_signal['risk_level'],
            'time_horizon': unified_signal['time_horizon'],
            'individual_signals': signals
        }
    
    def _analyze_institutional_flow(self, flow_data: Dict) -> Dict:
        """Analyze institutional flow patterns - HIGHEST PRIORITY"""
        call_volume = flow_data.get('call_volume', 0)
        put_volume = flow_data.get('put_volume', 0)
        total_volume = call_volume + put_volume
        
        if total_volume == 0:
            return {'direction': 'NEUTRAL', 'strength': 0, 'confidence': 0}
        
        # Institutional bias calculation
        call_put_ratio = call_volume / put_volume if put_volume > 0 else 10
        
        # Block trades and sweep analysis
        block_trades = flow_data.get('block_trades', [])
        sweep_trades = flow_data.get('sweep_trades', [])
        
        institutional_score = 0
        confidence = 50
        
        # Analyze call/put ratio
        if call_put_ratio > 2.0:
            institutional_score += 30
            confidence += 20
        elif call_put_ratio < 0.5:
            institutional_score -= 30
            confidence += 20
        
        # Block trades analysis
        if len(block_trades) > 5:
            call_blocks = sum(1 for trade in block_trades if trade.get('option_type') == 'CALL')
            put_blocks = len(block_trades) - call_blocks
            
            if call_blocks > put_blocks:
                institutional_score += 20
            else:
                institutional_score -= 20
            confidence += 15
        
        # Sweep trades (aggressive institutional orders)
        if len(sweep_trades) > 3:
            call_sweeps = sum(1 for trade in sweep_trades if trade.get('option_type') == 'CALL')
            put_sweeps = len(sweep_trades) - call_sweeps
            
            if call_sweeps > put_sweeps:
                institutional_score += 25
            else:
                institutional_score -= 25
            confidence += 20
        
        # Determine direction and strength
        if institutional_score > 15:
            direction = 'BULLISH'
            strength = min(100, institutional_score)
        elif institutional_score < -15:
            direction = 'BEARISH'
            strength = min(100, abs(institutional_score))
        else:
            direction = 'NEUTRAL'
            strength = abs(institutional_score)
        
        return {
            'direction': direction,
            'strength': strength,
            'confidence': min(95, confidence)
        }
    
    def _analyze_gamma_exposure(self, gex_data: Dict, market_data: Dict) -> Dict:
        """Analyze gamma exposure impact on price action"""
        current_price = market_data.get('price', 100)
        net_gex = gex_data.get('net_gex', 0)
        gex_flip_point = gex_data.get('gamma_flip_point', current_price)
        
        # Distance from gamma flip point
        distance_from_flip = ((current_price - gex_flip_point) / gex_flip_point) * 100
        
        gex_score = 0
        confidence = 60
        
        # Positive GEX = dealer long gamma = price suppression
        # Negative GEX = dealer short gamma = price acceleration
        if net_gex > 1000000:  # Strong positive GEX
            if current_price > gex_flip_point:
                gex_score -= 20  # Resistance above flip point
            else:
                gex_score += 10  # Support below flip point
            confidence += 20
        elif net_gex < -1000000:  # Strong negative GEX
            if distance_from_flip > 2:
                gex_score += 25  # Momentum continuation likely
            elif distance_from_flip < -2:
                gex_score -= 25  # Downward momentum
            confidence += 25
        
        # Support/resistance levels
        support_levels = gex_data.get('support_levels', [])
        resistance_levels = gex_data.get('resistance_levels', [])
        
        # Check proximity to key levels
        for level in support_levels:
            if abs(current_price - level['strike']) / current_price < 0.02:  # Within 2%
                gex_score += 15
                confidence += 10
        
        for level in resistance_levels:
            if abs(current_price - level['strike']) / current_price < 0.02:  # Within 2%
                gex_score -= 15
                confidence += 10
        
        if gex_score > 10:
            direction = 'BULLISH'
            strength = min(100, gex_score * 2)
        elif gex_score < -10:
            direction = 'BEARISH'
            strength = min(100, abs(gex_score) * 2)
        else:
            direction = 'NEUTRAL'
            strength = abs(gex_score) * 2
        
        return {
            'direction': direction,
            'strength': strength,
            'confidence': min(90, confidence)
        }
    
    def _analyze_technical_momentum(self, tech_data: Dict, market_data: Dict) -> Dict:
        """Analyze technical indicators for momentum confirmation"""
        rsi = tech_data.get('rsi', 50)
        macd_signal = tech_data.get('macd_signal', 0)
        price_change = market_data.get('price_change_pct', 0)
        volume_ratio = market_data.get('volume', 1) / market_data.get('avg_volume', 1)
        
        tech_score = 0
        confidence = 55
        
        # RSI analysis
        if rsi > 70:
            tech_score -= 15  # Overbought
            confidence += 15
        elif rsi > 60:
            tech_score += 10  # Bullish momentum
            confidence += 10
        elif rsi < 30:
            tech_score += 15  # Oversold bounce
            confidence += 15
        elif rsi < 40:
            tech_score -= 10  # Bearish momentum
            confidence += 10
        
        # MACD signal
        if macd_signal > 0.1:
            tech_score += 20
            confidence += 15
        elif macd_signal < -0.1:
            tech_score -= 20
            confidence += 15
        
        # Price momentum
        if abs(price_change) > 2:
            if price_change > 0:
                tech_score += 15
            else:
                tech_score -= 15
            confidence += 20
        
        # Volume confirmation
        if volume_ratio > 1.5:
            if price_change > 0:
                tech_score += 10
            else:
                tech_score -= 10
            confidence += 10
        
        if tech_score > 15:
            direction = 'BULLISH'
            strength = min(100, tech_score * 2)
        elif tech_score < -15:
            direction = 'BEARISH'
            strength = min(100, abs(tech_score) * 2)
        else:
            direction = 'NEUTRAL'
            strength = abs(tech_score) * 2
        
        return {
            'direction': direction,
            'strength': strength,
            'confidence': min(85, confidence)
        }
    
    def _analyze_options_sentiment(self, flow_data: Dict) -> Dict:
        """Analyze options sentiment and positioning"""
        call_volume = flow_data.get('call_volume', 0)
        put_volume = flow_data.get('put_volume', 0)
        sentiment = flow_data.get('sentiment', 'NEUTRAL')
        
        sentiment_score = 0
        confidence = 45
        
        # Call/Put ratio sentiment
        if call_volume > 0 and put_volume > 0:
            cp_ratio = call_volume / put_volume
            if cp_ratio > 1.5:
                sentiment_score += 20
                confidence += 20
            elif cp_ratio < 0.67:
                sentiment_score -= 20
                confidence += 20
        
        # Explicit sentiment signal
        if sentiment == 'BULLISH':
            sentiment_score += 15
            confidence += 10
        elif sentiment == 'BEARISH':
            sentiment_score -= 15
            confidence += 10
        
        if sentiment_score > 10:
            direction = 'BULLISH'
            strength = min(100, sentiment_score * 3)
        elif sentiment_score < -10:
            direction = 'BEARISH'
            strength = min(100, abs(sentiment_score) * 3)
        else:
            direction = 'NEUTRAL'
            strength = abs(sentiment_score) * 3
        
        return {
            'direction': direction,
            'strength': strength,
            'confidence': min(75, confidence)
        }
    
    def _analyze_news_sentiment(self, market_data: Dict) -> Dict:
        """Analyze news sentiment - LOWEST PRIORITY due to noise"""
        # Simple news sentiment analysis
        news_sentiment = market_data.get('news_sentiment', 0)  # -1 to 1 scale
        
        news_score = news_sentiment * 20  # Scale to -20 to 20
        confidence = 30  # Low confidence due to news noise
        
        if news_score > 5:
            direction = 'BULLISH'
            strength = min(100, news_score * 3)
        elif news_score < -5:
            direction = 'BEARISH'
            strength = min(100, abs(news_score) * 3)
        else:
            direction = 'NEUTRAL'
            strength = abs(news_score) * 3
        
        return {
            'direction': direction,
            'strength': strength,
            'confidence': confidence
        }
    
    def _calculate_weighted_signal(self, signals: Dict) -> Dict:
        """Calculate final weighted signal with priority system"""
        total_weight = 0
        weighted_score = 0
        confidence_sum = 0
        breakdown = {}
        
        for signal_name, signal_data in signals.items():
            weight = signal_data['weight']
            direction = signal_data['direction']
            strength = signal_data['strength']
            confidence = signal_data['confidence']
            
            # Convert direction to numeric score
            if direction == 'BULLISH':
                numeric_score = strength
            elif direction == 'BEARISH':
                numeric_score = -strength
            else:
                numeric_score = 0
            
            # Weight the score
            weighted_contribution = (numeric_score * weight * confidence) / 100
            weighted_score += weighted_contribution
            total_weight += weight
            confidence_sum += confidence * weight
            
            breakdown[signal_name] = {
                'direction': direction,
                'strength': strength,
                'confidence': confidence,
                'weight': weight,
                'contribution': weighted_contribution
            }
        
        # Calculate final metrics
        if total_weight > 0:
            final_score = weighted_score / total_weight
            average_confidence = confidence_sum / total_weight
        else:
            final_score = 0
            average_confidence = 0
        
        # Determine final direction
        if final_score > 15:
            final_direction = 'BULLISH'
            final_strength = min(100, abs(final_score))
        elif final_score < -15:
            final_direction = 'BEARISH'
            final_strength = min(100, abs(final_score))
        else:
            final_direction = 'NEUTRAL'
            final_strength = abs(final_score)
        
        # Action recommendation
        if average_confidence >= self.signal_confidence_thresholds['HIGH']:
            if final_strength > 60:
                action = 'STRONG_BUY' if final_direction == 'BULLISH' else 'STRONG_SELL' if final_direction == 'BEARISH' else 'HOLD'
                risk_level = 'MEDIUM'
                time_horizon = '0-1 DTE'
            else:
                action = 'BUY' if final_direction == 'BULLISH' else 'SELL' if final_direction == 'BEARISH' else 'HOLD'
                risk_level = 'LOW'
                time_horizon = '1-3 DTE'
        elif average_confidence >= self.signal_confidence_thresholds['MEDIUM']:
            action = 'CAUTIOUS_BUY' if final_direction == 'BULLISH' else 'CAUTIOUS_SELL' if final_direction == 'BEARISH' else 'WAIT'
            risk_level = 'MEDIUM'
            time_horizon = '2-5 DTE'
        else:
            action = 'WAIT'
            risk_level = 'HIGH'
            time_horizon = '5+ DTE'
        
        return {
            'direction': final_direction,
            'strength': final_strength,
            'confidence': average_confidence,
            'action': action,
            'risk_level': risk_level,
            'time_horizon': time_horizon,
            'breakdown': breakdown,
            'raw_score': final_score
        }
    
    def get_signal_priority_explanation(self) -> List[Dict]:
        """Return explanation of signal priority system"""
        return [
            {
                'priority': 1,
                'signal': 'Institutional Flow',
                'weight': '40%',
                'reason': 'Smart money moves - highest predictive value',
                'indicators': ['Block trades', 'Sweep orders', 'Dark pool prints']
            },
            {
                'priority': 2,
                'signal': 'Gamma Exposure',
                'weight': '25%',
                'reason': 'Market structure impact on price movement',
                'indicators': ['GEX levels', 'Gamma flip point', 'Dealer positioning']
            },
            {
                'priority': 3,
                'signal': 'Technical Momentum',
                'weight': '20%',
                'reason': 'Price action confirmation and trend direction',
                'indicators': ['RSI', 'MACD', 'Volume', 'Price momentum']
            },
            {
                'priority': 4,
                'signal': 'Options Sentiment',
                'weight': '10%',
                'reason': 'Overall options positioning and sentiment',
                'indicators': ['Call/Put ratio', 'Sentiment indicators']
            },
            {
                'priority': 5,
                'signal': 'News Sentiment',
                'weight': '5%',
                'reason': 'Often noisy - lowest priority for confirmation only',
                'indicators': ['News sentiment', 'Market headlines']
            }
        ]

# Global enhanced signal coordinator
enhanced_signal_coordinator = EnhancedSignalCoordinator()