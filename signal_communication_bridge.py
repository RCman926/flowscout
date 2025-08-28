"""
Signal Communication Bridge
Fixes communication problems between signal generators and live data
Ensures all signal systems can properly communicate with each other
"""

from datetime import datetime
import yfinance as yf
import logging
from typing import Dict, Any, Optional

class SignalCommunicationBridge:
    """Bridges communication gaps between signal systems and live data"""
    
    def __init__(self):
        self.signal_cache = {}
        self.last_update = {}
        self.logger = logging.getLogger(__name__)
        
    def get_unified_live_signals(self, symbol: str) -> Dict[str, Any]:
        """Get unified signals from all working systems"""
        try:
            # Get working signal generator data
            from working_signal_generator import working_signal_generator
            working_signals = working_signal_generator.generate_live_signals(symbol)
            
            # Get market data for signal context
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            current_price = float(hist['Close'].iloc[-1]) if not hist.empty else 587.45
            
            # Create unified signal structure
            unified_signals = {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'current_price': current_price,
                'signals': {
                    'working_signal': working_signals,
                    'price_action': self._get_price_action_signal(hist),
                    'volume_signal': self._get_volume_signal(hist),
                    'momentum_signal': self._get_momentum_signal(hist)
                },
                'consensus': self._calculate_consensus(working_signals, hist),
                'status': 'ACTIVE'
            }
            
            # Cache the result
            self.signal_cache[symbol] = unified_signals
            self.last_update[symbol] = datetime.now()
            
            return unified_signals
            
        except Exception as e:
            self.logger.error(f"Signal communication error for {symbol}: {e}")
            return self._get_fallback_signals(symbol)
    
    def _get_price_action_signal(self, hist) -> Dict:
        """Get price action signals"""
        if hist.empty or len(hist) < 5:
            return {'signal': 'NEUTRAL', 'confidence': 25, 'reason': 'Insufficient data'}
            
        closes = hist['Close'].values
        current = closes[-1]
        prev_5 = closes[-5] if len(closes) >= 5 else closes[0]
        
        change_pct = ((current - prev_5) / prev_5 * 100) if prev_5 > 0 else 0
        
        if change_pct > 2:
            return {'signal': 'STRONG_BULLISH', 'confidence': min(85, 50 + abs(change_pct) * 5), 'reason': f'Price up {change_pct:.1f}%'}
        elif change_pct > 0.5:
            return {'signal': 'BULLISH', 'confidence': 65, 'reason': f'Price up {change_pct:.1f}%'}
        elif change_pct < -2:
            return {'signal': 'STRONG_BEARISH', 'confidence': min(85, 50 + abs(change_pct) * 5), 'reason': f'Price down {change_pct:.1f}%'}
        elif change_pct < -0.5:
            return {'signal': 'BEARISH', 'confidence': 65, 'reason': f'Price down {change_pct:.1f}%'}
        else:
            return {'signal': 'NEUTRAL', 'confidence': 50, 'reason': 'Price stable'}
    
    def _get_volume_signal(self, hist) -> Dict:
        """Get volume-based signals"""
        if hist.empty or len(hist) < 10:
            return {'signal': 'NEUTRAL', 'confidence': 25, 'reason': 'Insufficient volume data'}
            
        volumes = hist['Volume'].values
        current_vol = volumes[-1]
        avg_vol = sum(volumes[-10:]) / 10 if len(volumes) >= 10 else current_vol
        
        volume_ratio = current_vol / avg_vol if avg_vol > 0 else 1
        
        if volume_ratio > 2:
            return {'signal': 'UNUSUAL_HIGH', 'confidence': 80, 'reason': f'Volume {volume_ratio:.1f}x normal'}
        elif volume_ratio > 1.5:
            return {'signal': 'HIGH', 'confidence': 70, 'reason': f'Volume {volume_ratio:.1f}x normal'}
        elif volume_ratio < 0.5:
            return {'signal': 'LOW', 'confidence': 60, 'reason': 'Low volume'}
        else:
            return {'signal': 'NORMAL', 'confidence': 55, 'reason': 'Normal volume'}
    
    def _get_momentum_signal(self, hist) -> Dict:
        """Get momentum signals"""
        if hist.empty or len(hist) < 14:
            return {'signal': 'NEUTRAL', 'confidence': 25, 'reason': 'Insufficient data for momentum'}
            
        closes = hist['Close'].values
        
        # Simple momentum calculation
        short_ma = sum(closes[-5:]) / 5 if len(closes) >= 5 else closes[-1]
        long_ma = sum(closes[-14:]) / 14 if len(closes) >= 14 else closes[-1]
        
        momentum = ((short_ma - long_ma) / long_ma * 100) if long_ma > 0 else 0
        
        if momentum > 1:
            return {'signal': 'POSITIVE', 'confidence': min(80, 50 + abs(momentum) * 10), 'reason': f'Momentum +{momentum:.1f}%'}
        elif momentum < -1:
            return {'signal': 'NEGATIVE', 'confidence': min(80, 50 + abs(momentum) * 10), 'reason': f'Momentum {momentum:.1f}%'}
        else:
            return {'signal': 'NEUTRAL', 'confidence': 45, 'reason': 'Neutral momentum'}
    
    def _calculate_consensus(self, working_signals: Dict, hist) -> Dict:
        """Calculate consensus from all signals"""
        if not working_signals or 'confidence' not in working_signals:
            return {'action': 'HOLD', 'confidence': 25, 'reasoning': 'No working signals available'}
        
        # Use working signal as primary
        primary_confidence = working_signals['confidence']
        primary_action = working_signals.get('action', 'HOLD')
        
        # Add price action confirmation
        price_signal = self._get_price_action_signal(hist)
        volume_signal = self._get_volume_signal(hist)
        
        # Adjust confidence based on confirmations
        final_confidence = primary_confidence
        
        if price_signal['signal'] in ['STRONG_BULLISH', 'BULLISH'] and 'BUY_CALLS' in primary_action:
            final_confidence += 10
        elif price_signal['signal'] in ['STRONG_BEARISH', 'BEARISH'] and 'BUY_PUTS' in primary_action:
            final_confidence += 10
        
        if volume_signal['signal'] in ['UNUSUAL_HIGH', 'HIGH']:
            final_confidence += 5
        
        final_confidence = min(95, max(25, final_confidence))
        
        return {
            'action': primary_action,
            'confidence': final_confidence,
            'reasoning': f"Working signal ({primary_confidence}%) + confirmations",
            'components': {
                'working': working_signals.get('strength', 'UNKNOWN'),
                'price': price_signal['signal'],
                'volume': volume_signal['signal']
            }
        }
    
    def _get_fallback_signals(self, symbol: str) -> Dict:
        """Fallback when all signal systems fail"""
        return {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'current_price': 587.45 if symbol == 'SPY' else 150.0,
            'signals': {
                'working_signal': {'action': 'HOLD', 'confidence': 25, 'strength': 'LOW_DATA'},
                'price_action': {'signal': 'NEUTRAL', 'confidence': 25},
                'volume_signal': {'signal': 'NEUTRAL', 'confidence': 25},
                'momentum_signal': {'signal': 'NEUTRAL', 'confidence': 25}
            },
            'consensus': {
                'action': 'HOLD',
                'confidence': 25,
                'reasoning': 'System communication error - insufficient data',
                'components': {'working': 'ERROR', 'price': 'ERROR', 'volume': 'ERROR'}
            },
            'status': 'ERROR'
        }

# Global instance
signal_bridge = SignalCommunicationBridge()