"""
Real-Time VIX Analysis
Analyzes VIX for volatility timing and market sentiment
Critical for 0DTE options trading
"""

import yfinance as yf
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
from collections import deque

logger = logging.getLogger(__name__)


class VIXAnalyzer:
    """
    Real-time VIX analysis for volatility timing
    Analyzes:
    - VIX percentile (current vs historical)
    - VIX/SPX correlation
    - VIX term structure
    - VIX spike detection
    - Volatility regime
    """
    
    def __init__(self):
        self.vix_history = deque(maxlen=252)  # 1 year of trading days
        self.spx_history = deque(maxlen=252)
        self.cache_duration = 60  # 1 minute cache
        self.last_update = None
        self.cached_data = None
    
    def analyze_vix(
        self,
        current_vix: Optional[float] = None,
        lookback_days: int = 252
    ) -> Dict:
        """
        Comprehensive VIX analysis
        
        Args:
            current_vix: Current VIX value (optional, will fetch if not provided)
            lookback_days: Days of history to analyze
            
        Returns:
            Dict with VIX percentile, correlation, signals, etc.
        """
        try:
            # Check cache
            if self._is_cache_valid():
                return self.cached_data
            
            # Fetch current VIX if not provided
            if current_vix is None:
                current_vix = self._fetch_current_vix()
            
            if current_vix is None or current_vix <= 0:
                return {'error': 'Unable to fetch VIX data'}
            
            # Fetch historical VIX
            vix_history = self._fetch_vix_history(lookback_days)
            
            # Fetch SPX for correlation
            spx_data = self._fetch_spx_data(lookback_days)
            
            # Calculate metrics
            vix_percentile = self._calculate_vix_percentile(current_vix, vix_history)
            vix_rank = self._calculate_vix_rank(current_vix, vix_history)
            vix_regime = self._classify_vix_regime(current_vix)
            
            # VIX/SPX correlation
            correlation = self._calculate_vix_spx_correlation(vix_history, spx_data)
            
            # VIX spike detection
            spike_analysis = self._detect_vix_spike(current_vix, vix_history)
            
            # Generate trading signals
            signals = self._generate_vix_signals(
                current_vix, vix_percentile, vix_regime, spike_analysis, correlation
            )
            
            result = {
                'current_vix': round(current_vix, 2),
                'vix_percentile': vix_percentile,
                'vix_rank': vix_rank,
                'vix_regime': vix_regime,
                'correlation': correlation,
                'spike_analysis': spike_analysis,
                'signals': signals,
                'historical_stats': {
                    'min_vix': round(min(vix_history), 2) if vix_history else 0,
                    'max_vix': round(max(vix_history), 2) if vix_history else 0,
                    'avg_vix': round(np.mean(vix_history), 2) if vix_history else 0,
                    'median_vix': round(np.median(vix_history), 2) if vix_history else 0
                },
                'timestamp': datetime.now().isoformat()
            }
            
            # Cache result
            self.cached_data = result
            self.last_update = datetime.now()
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing VIX: {e}", exc_info=True)
            return {'error': str(e)}
    
    def _fetch_current_vix(self) -> Optional[float]:
        """Fetch current VIX value"""
        try:
            vix = yf.Ticker("^VIX")
            vix_info = vix.fast_info
            current_price = vix_info.get('lastPrice', 0)
            return float(current_price) if current_price > 0 else None
        except Exception as e:
            logger.debug(f"Error fetching current VIX: {e}")
            return None
    
    def _fetch_vix_history(self, days: int) -> List[float]:
        """Fetch historical VIX data"""
        try:
            vix = yf.Ticker("^VIX")
            hist = vix.history(period=f"{days}d", interval="1d")
            
            if hist.empty:
                return []
            
            # Use Close prices
            vix_values = hist['Close'].tolist()
            self.vix_history.extend(vix_values)
            
            return vix_values
            
        except Exception as e:
            logger.debug(f"Error fetching VIX history: {e}")
            return list(self.vix_history) if self.vix_history else []
    
    def _fetch_spx_data(self, days: int) -> List[float]:
        """Fetch SPX data for correlation"""
        try:
            spx = yf.Ticker("^GSPC")
            hist = spx.history(period=f"{days}d", interval="1d")
            
            if hist.empty:
                return []
            
            # Use Close prices
            spx_values = hist['Close'].tolist()
            self.spx_history.extend(spx_values)
            
            return spx_values
            
        except Exception as e:
            logger.debug(f"Error fetching SPX data: {e}")
            return list(self.spx_history) if self.spx_history else []
    
    def _calculate_vix_percentile(
        self,
        current_vix: float,
        vix_history: List[float]
    ) -> Dict:
        """Calculate VIX percentile"""
        try:
            if not vix_history:
                return {'percentile': 50, 'interpretation': 'INSUFFICIENT_DATA'}
            
            # Calculate percentile
            percentile = (sum(1 for v in vix_history if v < current_vix) / len(vix_history)) * 100
            
            # Interpretation
            if percentile >= 90:
                interpretation = 'EXTREMELY_HIGH'
            elif percentile >= 75:
                interpretation = 'HIGH'
            elif percentile >= 50:
                interpretation = 'ABOVE_AVERAGE'
            elif percentile >= 25:
                interpretation = 'BELOW_AVERAGE'
            elif percentile >= 10:
                interpretation = 'LOW'
            else:
                interpretation = 'EXTREMELY_LOW'
            
            return {
                'percentile': round(percentile, 2),
                'interpretation': interpretation
            }
            
        except Exception as e:
            logger.error(f"Error calculating VIX percentile: {e}", exc_info=True)
            return {'percentile': 50, 'interpretation': 'ERROR'}
    
    def _calculate_vix_rank(
        self,
        current_vix: float,
        vix_history: List[float]
    ) -> float:
        """Calculate VIX rank (0-100)"""
        try:
            if not vix_history:
                return 50.0
            
            min_vix = min(vix_history)
            max_vix = max(vix_history)
            
            if max_vix == min_vix:
                return 50.0
            
            rank = ((current_vix - min_vix) / (max_vix - min_vix)) * 100
            return round(rank, 2)
            
        except Exception as e:
            logger.error(f"Error calculating VIX rank: {e}", exc_info=True)
            return 50.0
    
    def _classify_vix_regime(self, current_vix: float) -> Dict:
        """Classify VIX regime"""
        try:
            if current_vix >= 30:
                regime = 'EXTREME_FEAR'
                description = 'Panic selling, high volatility expected'
            elif current_vix >= 20:
                regime = 'FEAR'
                description = 'Elevated fear, increased volatility'
            elif current_vix >= 15:
                regime = 'NORMAL'
                description = 'Normal market conditions'
            elif current_vix >= 12:
                regime = 'COMPLACENT'
                description = 'Low fear, complacent market'
            else:
                regime = 'EXTREME_COMPLACENCY'
                description = 'Very low fear, potential complacency'
            
            return {
                'regime': regime,
                'description': description,
                'vix_value': round(current_vix, 2)
            }
            
        except Exception as e:
            logger.error(f"Error classifying VIX regime: {e}", exc_info=True)
            return {'regime': 'UNKNOWN', 'description': 'Error'}
    
    def _calculate_vix_spx_correlation(
        self,
        vix_history: List[float],
        spx_data: List[float]
    ) -> Dict:
        """Calculate VIX/SPX correlation"""
        try:
            if len(vix_history) < 20 or len(spx_data) < 20:
                return {'correlation': 0, 'interpretation': 'INSUFFICIENT_DATA'}
            
            # Align data (take minimum length)
            min_len = min(len(vix_history), len(spx_data))
            vix_aligned = vix_history[-min_len:]
            spx_aligned = spx_data[-min_len:]
            
            # Calculate returns
            vix_returns = np.diff(vix_aligned) / vix_aligned[:-1]
            spx_returns = np.diff(spx_aligned) / spx_aligned[:-1]
            
            # Calculate correlation
            if len(vix_returns) > 1 and len(spx_returns) > 1:
                correlation = np.corrcoef(vix_returns, spx_returns)[0, 1]
                
                # VIX and SPX are typically negatively correlated
                if correlation < -0.7:
                    interpretation = 'STRONG_INVERSE'
                elif correlation < -0.4:
                    interpretation = 'MODERATE_INVERSE'
                elif correlation < 0:
                    interpretation = 'WEAK_INVERSE'
                else:
                    interpretation = 'UNUSUAL_POSITIVE'  # Unusual if positive
            else:
                correlation = 0
                interpretation = 'INSUFFICIENT_DATA'
            
            return {
                'correlation': round(correlation, 4),
                'interpretation': interpretation
            }
            
        except Exception as e:
            logger.error(f"Error calculating correlation: {e}", exc_info=True)
            return {'correlation': 0, 'interpretation': 'ERROR'}
    
    def _detect_vix_spike(
        self,
        current_vix: float,
        vix_history: List[float]
    ) -> Dict:
        """Detect VIX spikes (sudden increases)"""
        try:
            if len(vix_history) < 5:
                return {'is_spike': False, 'spike_magnitude': 0}
            
            # Calculate recent average
            recent_avg = np.mean(vix_history[-5:])
            
            # Calculate spike magnitude
            spike_magnitude = ((current_vix - recent_avg) / recent_avg * 100) if recent_avg > 0 else 0
            
            # Detect spike (>20% increase)
            is_spike = spike_magnitude > 20
            
            return {
                'is_spike': is_spike,
                'spike_magnitude': round(spike_magnitude, 2),
                'recent_avg': round(recent_avg, 2),
                'current_vix': round(current_vix, 2)
            }
            
        except Exception as e:
            logger.error(f"Error detecting VIX spike: {e}", exc_info=True)
            return {'is_spike': False, 'spike_magnitude': 0}
    
    def _generate_vix_signals(
        self,
        current_vix: float,
        vix_percentile: Dict,
        vix_regime: Dict,
        spike_analysis: Dict,
        correlation: Dict
    ) -> Dict:
        """Generate trading signals based on VIX analysis"""
        try:
            signals = {
                'buy_calls_signal': 0,
                'buy_puts_signal': 0,
                'sell_premium_signal': 0,
                'buy_premium_signal': 0,
                'reasoning': []
            }
            
            # Signal 1: Low VIX = sell premium opportunity
            percentile = vix_percentile.get('percentile', 50)
            if percentile < 25:
                signals['sell_premium_signal'] += 20
                signals['reasoning'].append(f'Low VIX ({percentile:.0f}th percentile) - good for selling premium')
            
            # Signal 2: High VIX = buy premium opportunity (if expecting move)
            if percentile > 75:
                signals['buy_premium_signal'] += 15
                signals['reasoning'].append(f'High VIX ({percentile:.0f}th percentile) - expensive but may expand')
            
            # Signal 3: VIX spike = volatility expansion
            if spike_analysis.get('is_spike'):
                signals['buy_premium_signal'] += 10
                signals['reasoning'].append(f'VIX spike detected ({spike_analysis.get("spike_magnitude", 0):.1f}%) - volatility expanding')
            
            # Signal 4: Extreme fear = potential reversal (contrarian)
            if vix_regime.get('regime') == 'EXTREME_FEAR':
                signals['buy_calls_signal'] += 15
                signals['reasoning'].append('Extreme fear - potential bullish reversal')
            
            # Signal 5: Extreme complacency = potential correction
            if vix_regime.get('regime') == 'EXTREME_COMPLACENCY':
                signals['buy_puts_signal'] += 10
                signals['reasoning'].append('Extreme complacency - potential correction')
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating VIX signals: {e}", exc_info=True)
            return {'error': str(e)}
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if self.cached_data is None or self.last_update is None:
            return False
        
        age_seconds = (datetime.now() - self.last_update).total_seconds()
        return age_seconds < self.cache_duration


# Global instance
vix_analyzer = VIXAnalyzer()

