"""
Market Regime Detector
Detects market conditions (trending, choppy, bull, bear) to adapt strategy
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
import yfinance as yf

logger = logging.getLogger(__name__)


class MarketRegimeDetector:
    """
    Detects market regimes to adapt trading strategy
    Regimes: TRENDING_UP, TRENDING_DOWN, CHOPPY, HIGH_VOLATILITY, LOW_VOLATILITY
    """
    
    def __init__(self):
        self.regime_cache = {}
        self.cache_duration = 300  # 5 minutes
        self.lookback_days = 20  # Days of history to analyze
    
    def detect_regime(self, symbol: str = "SPY") -> Dict:
        """
        Detect current market regime
        
        Returns:
            Dict with regime type, confidence, and characteristics
        """
        try:
            # Cache — this was defined but unused and was Yahoo-hammering every WS loop
            cached = self.regime_cache.get(symbol)
            if cached:
                ts = cached.get('_cached_at', 0)
                if (datetime.now().timestamp() - float(ts)) < float(self.cache_duration):
                    return {k: v for k, v in cached.items() if k != '_cached_at'}

            # Get price history
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=f"{self.lookback_days}d", interval="1d")
            
            if hist.empty or len(hist) < 10:
                return self._default_regime()
            
            # Calculate regime indicators
            prices = hist['Close'].values
            returns = np.diff(prices) / prices[:-1]
            
            # 1. Trend Detection
            trend_regime = self._detect_trend(prices, returns)
            
            # 2. Volatility Detection
            vol_regime = self._detect_volatility(returns)
            
            # 3. Momentum Detection
            momentum_regime = self._detect_momentum(prices, returns)
            
            # 4. Combine into final regime
            final_regime = self._combine_regimes(trend_regime, vol_regime, momentum_regime)
            
            # 5. Get VIX for additional context
            vix_context = self._get_vix_context()
            
            result = {
                'regime': final_regime['type'],
                'confidence': final_regime['confidence'],
                'trend': trend_regime,
                'volatility': vol_regime,
                'momentum': momentum_regime,
                'vix_context': vix_context,
                'characteristics': self._get_regime_characteristics(final_regime['type']),
                'strategy_adaptation': self._get_strategy_adaptation(final_regime['type']),
                'timestamp': datetime.now().isoformat()
            }
            payload = dict(result)
            payload['_cached_at'] = datetime.now().timestamp()
            self.regime_cache[symbol] = payload
            return result
            
        except Exception as e:
            logger.error(f"Error detecting regime: {e}")
            return self._default_regime()
    
    def _detect_trend(self, prices: np.ndarray, returns: np.ndarray) -> Dict:
        """Detect trending vs choppy market"""
        # Linear regression slope
        x = np.arange(len(prices))
        slope = np.polyfit(x, prices, 1)[0]
        slope_pct = (slope / prices[-1]) * 100
        
        # Trend strength (R-squared)
        trend_line = np.polyval(np.polyfit(x, prices, 1), x)
        ss_res = np.sum((prices - trend_line) ** 2)
        ss_tot = np.sum((prices - np.mean(prices)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        # Average return direction
        avg_return = np.mean(returns)
        
        # Determine trend
        if r_squared > 0.7:  # Strong trend
            if slope_pct > 0.1:
                trend_type = 'TRENDING_UP'
                confidence = min(95, 70 + int(r_squared * 25))
            elif slope_pct < -0.1:
                trend_type = 'TRENDING_DOWN'
                confidence = min(95, 70 + int(r_squared * 25))
            else:
                trend_type = 'CHOPPY'
                confidence = 50
        else:  # Weak trend = choppy
            trend_type = 'CHOPPY'
            confidence = min(95, 50 + int((1 - r_squared) * 45))
        
        return {
            'type': trend_type,
            'confidence': confidence,
            'slope_pct': float(slope_pct),
            'r_squared': float(r_squared),
            'avg_return': float(avg_return)
        }
    
    def _detect_volatility(self, returns: np.ndarray) -> Dict:
        """Detect volatility regime"""
        vol = np.std(returns) * np.sqrt(252)  # Annualized
        
        # Historical volatility percentiles
        # Typical SPY: 10-20% annual vol
        if vol > 0.25:  # >25% = high vol
            vol_type = 'HIGH_VOLATILITY'
            confidence = min(95, 60 + int((vol - 0.25) * 100))
        elif vol < 0.10:  # <10% = low vol
            vol_type = 'LOW_VOLATILITY'
            confidence = min(95, 60 + int((0.10 - vol) * 100))
        else:
            vol_type = 'NORMAL_VOLATILITY'
            confidence = 50
        
        return {
            'type': vol_type,
            'confidence': confidence,
            'volatility': float(vol),
            'volatility_pct': float(vol * 100)
        }
    
    def _detect_momentum(self, prices: np.ndarray, returns: np.ndarray) -> Dict:
        """Detect momentum (acceleration)"""
        # Short-term vs long-term momentum
        short_momentum = np.mean(returns[-5:]) if len(returns) >= 5 else 0
        long_momentum = np.mean(returns[-20:]) if len(returns) >= 20 else np.mean(returns)
        
        # Momentum acceleration
        if len(returns) >= 10:
            recent_mom = np.mean(returns[-5:])
            earlier_mom = np.mean(returns[-10:-5])
            acceleration = recent_mom - earlier_mom
        else:
            acceleration = 0
        
        # Determine momentum regime
        if abs(short_momentum) > 0.02:  # >2% daily move
            if short_momentum > 0:
                mom_type = 'STRONG_UP_MOMENTUM'
            else:
                mom_type = 'STRONG_DOWN_MOMENTUM'
            confidence = min(95, 70 + int(abs(short_momentum) * 1000))
        elif abs(acceleration) > 0.01:  # Accelerating
            if acceleration > 0:
                mom_type = 'ACCELERATING_UP'
            else:
                mom_type = 'ACCELERATING_DOWN'
            confidence = 65
        else:
            mom_type = 'NEUTRAL_MOMENTUM'
            confidence = 50
        
        return {
            'type': mom_type,
            'confidence': confidence,
            'short_momentum': float(short_momentum),
            'long_momentum': float(long_momentum),
            'acceleration': float(acceleration)
        }
    
    def _combine_regimes(self, trend: Dict, volatility: Dict, momentum: Dict) -> Dict:
        """Combine individual regime detections into final regime"""
        # Priority: Trend > Volatility > Momentum
        
        trend_type = trend['type']
        vol_type = volatility['type']
        mom_type = momentum['type']
        
        # High volatility overrides everything
        if vol_type == 'HIGH_VOLATILITY':
            return {
                'type': 'HIGH_VOLATILITY',
                'confidence': volatility['confidence']
            }
        
        # Strong trend
        if trend_type == 'TRENDING_UP' and trend['confidence'] > 75:
            return {
                'type': 'TRENDING_UP',
                'confidence': trend['confidence']
            }
        elif trend_type == 'TRENDING_DOWN' and trend['confidence'] > 75:
            return {
                'type': 'TRENDING_DOWN',
                'confidence': trend['confidence']
            }
        
        # Choppy market
        if trend_type == 'CHOPPY':
            return {
                'type': 'CHOPPY',
                'confidence': trend['confidence']
            }
        
        # Momentum-based
        if 'UP' in mom_type and momentum['confidence'] > 70:
            return {
                'type': 'TRENDING_UP',
                'confidence': momentum['confidence']
            }
        elif 'DOWN' in mom_type and momentum['confidence'] > 70:
            return {
                'type': 'TRENDING_DOWN',
                'confidence': momentum['confidence']
            }
        
        # Default
        return {
            'type': 'NEUTRAL',
            'confidence': 50
        }
    
    def _get_vix_context(self) -> Dict:
        """Get VIX context for additional regime confirmation"""
        try:
            vix = yf.Ticker("^VIX")
            vix_info = vix.fast_info
            vix_price = vix_info.get('lastPrice', 0)
            
            if vix_price == 0:
                return {'available': False}
            
            # VIX regimes
            if vix_price > 30:
                vix_regime = 'EXTREME_FEAR'
            elif vix_price > 20:
                vix_regime = 'FEAR'
            elif vix_price > 15:
                vix_regime = 'NORMAL'
            elif vix_price > 12:
                vix_regime = 'COMPLACENT'
            else:
                vix_regime = 'EXTREME_COMPLACENCY'
            
            return {
                'available': True,
                'vix': float(vix_price),
                'regime': vix_regime
            }
        except:
            return {'available': False}
    
    def _get_regime_characteristics(self, regime: str) -> Dict:
        """Get characteristics of each regime"""
        characteristics = {
            'TRENDING_UP': {
                'description': 'Strong upward trend',
                'typical_behavior': 'Momentum continues, pullbacks are buying opportunities',
                'risk_level': 'MEDIUM',
                'best_strategy': 'Trend following, momentum plays'
            },
            'TRENDING_DOWN': {
                'description': 'Strong downward trend',
                'typical_behavior': 'Selling pressure continues, rallies are selling opportunities',
                'risk_level': 'HIGH',
                'best_strategy': 'Short bias, put options'
            },
            'CHOPPY': {
                'description': 'Sideways, range-bound market',
                'typical_behavior': 'No clear direction, whipsaws common',
                'risk_level': 'HIGH',
                'best_strategy': 'Range trading, avoid trend following'
            },
            'HIGH_VOLATILITY': {
                'description': 'High volatility environment',
                'typical_behavior': 'Large swings, unpredictable moves',
                'risk_level': 'VERY_HIGH',
                'best_strategy': 'Reduce position size, wait for clarity'
            },
            'LOW_VOLATILITY': {
                'description': 'Low volatility, calm market',
                'typical_behavior': 'Small moves, trends hold better',
                'risk_level': 'LOW',
                'best_strategy': 'Trend following works well'
            },
            'NEUTRAL': {
                'description': 'Unclear regime',
                'typical_behavior': 'Mixed signals',
                'risk_level': 'MEDIUM',
                'best_strategy': 'Wait for clarity, reduce size'
            }
        }
        
        return characteristics.get(regime, characteristics['NEUTRAL'])
    
    def _get_strategy_adaptation(self, regime: str) -> Dict:
        """Get strategy adaptations for each regime"""
        adaptations = {
            'TRENDING_UP': {
                'confidence_multiplier': 1.1,  # Increase confidence in calls
                'position_size_multiplier': 1.0,
                'stop_loss_tighter': False,
                'prefer_direction': 'CALLS'
            },
            'TRENDING_DOWN': {
                'confidence_multiplier': 1.1,  # Increase confidence in puts
                'position_size_multiplier': 0.8,  # Reduce size in downtrends
                'stop_loss_tighter': True,
                'prefer_direction': 'PUTS'
            },
            'CHOPPY': {
                'confidence_multiplier': 0.7,  # Reduce confidence
                'position_size_multiplier': 0.5,  # Reduce size significantly
                'stop_loss_tighter': True,
                'prefer_direction': 'NEUTRAL'
            },
            'HIGH_VOLATILITY': {
                'confidence_multiplier': 0.6,  # Much lower confidence
                'position_size_multiplier': 0.4,  # Much smaller positions
                'stop_loss_tighter': True,
                'prefer_direction': 'NEUTRAL'
            },
            'LOW_VOLATILITY': {
                'confidence_multiplier': 1.15,  # Higher confidence
                'position_size_multiplier': 1.1,  # Slightly larger
                'stop_loss_tighter': False,
                'prefer_direction': 'TREND'
            },
            'NEUTRAL': {
                'confidence_multiplier': 0.9,
                'position_size_multiplier': 0.8,
                'stop_loss_tighter': False,
                'prefer_direction': 'NEUTRAL'
            }
        }
        
        return adaptations.get(regime, adaptations['NEUTRAL'])
    
    def _default_regime(self) -> Dict:
        """Default regime when detection fails"""
        return {
            'regime': 'NEUTRAL',
            'confidence': 50,
            'trend': {'type': 'UNKNOWN', 'confidence': 50},
            'volatility': {'type': 'UNKNOWN', 'confidence': 50},
            'momentum': {'type': 'UNKNOWN', 'confidence': 50},
            'vix_context': {'available': False},
            'characteristics': {
                'description': 'Unknown regime',
                'risk_level': 'MEDIUM'
            },
            'strategy_adaptation': {
                'confidence_multiplier': 0.9,
                'position_size_multiplier': 0.8
            },
            'timestamp': datetime.now().isoformat()
        }


# Global instance
market_regime_detector = MarketRegimeDetector()

