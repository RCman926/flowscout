"""
Signal Quality Analyzer - Meta-Learning System
Analyzes which signals work and which don't, learns what to keep/remove
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class SignalQualityAnalyzer:
    """
    Meta-learning system that analyzes signal performance
    Learns which signals are useful vs useless
    """
    
    def __init__(self):
        self.performance_file = "signal_performance.json"
        self.signal_history = []  # All signals with outcomes
        self.signal_stats = defaultdict(lambda: {
            'total_signals': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0,
            'avg_profit': 0.0,
            'avg_loss': 0.0,
            'total_profit': 0.0,
            'total_loss': 0.0,
            'signal_strength': 0.0,  # How reliable this signal is
            'last_updated': None
        })
        self.feature_importance = {}  # Feature -> importance score
        self.useless_signals = set()  # Signals that consistently fail
        self.high_value_signals = set()  # Signals that consistently win
        self.load_performance_data()
    
    def load_performance_data(self):
        """Load historical signal performance"""
        try:
            if os.path.exists(self.performance_file):
                with open(self.performance_file, 'r') as f:
                    data = json.load(f)
                    self.signal_stats = defaultdict(lambda: {
                        'total_signals': 0,
                        'wins': 0,
                        'losses': 0,
                        'win_rate': 0.0,
                        'avg_profit': 0.0,
                        'avg_loss': 0.0,
                        'total_profit': 0.0,
                        'total_loss': 0.0,
                        'signal_strength': 0.0,
                        'last_updated': None
                    }, data.get('signal_stats', {}))
                    self.useless_signals = set(data.get('useless_signals', []))
                    self.high_value_signals = set(data.get('high_value_signals', []))
                    self.feature_importance = data.get('feature_importance', {})
                    logger.info(f"Loaded signal performance: {len(self.signal_stats)} signals tracked")
        except Exception as e:
            logger.error(f"Error loading signal performance: {e}")
    
    def save_performance_data(self):
        """Save signal performance data"""
        try:
            data = {
                'signal_stats': dict(self.signal_stats),
                'useless_signals': list(self.useless_signals),
                'high_value_signals': list(self.high_value_signals),
                'feature_importance': self.feature_importance,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.performance_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving signal performance: {e}")
    
    def record_signal(self, signal_data: Dict, trade_outcome: Optional[Dict] = None):
        """
        Record a signal and its outcome
        
        Args:
            signal_data: Signal information (features, signals, confidence, etc.)
            trade_outcome: Trade result (WIN/LOSS, profit_pct, etc.)
        """
        signal_entry = {
            'timestamp': datetime.now().isoformat(),
            'signal_data': signal_data,
            'outcome': trade_outcome,
            'signal_id': signal_data.get('signal_id', f"signal_{datetime.now().timestamp()}")
        }
        self.signal_history.append(signal_entry)
        
        # Keep only last 1000 signals
        if len(self.signal_history) > 1000:
            self.signal_history = self.signal_history[-1000:]
        
        # Update stats if outcome available
        if trade_outcome:
            self._update_signal_stats(signal_data, trade_outcome)
    
    def _update_signal_stats(self, signal_data: Dict, outcome: Dict):
        """Update statistics for signals"""
        is_win = outcome.get('outcome') == 'WIN'
        profit_pct = outcome.get('profit_pct', 0)
        
        # Extract all signals from signal_data
        signals_to_track = self._extract_signals(signal_data)
        
        for signal_name, signal_value in signals_to_track.items():
            stats = self.signal_stats[signal_name]
            stats['total_signals'] += 1
            
            if is_win:
                stats['wins'] += 1
                stats['total_profit'] += profit_pct
                stats['avg_profit'] = stats['total_profit'] / stats['wins']
            else:
                stats['losses'] += 1
                stats['total_loss'] += abs(profit_pct)
                stats['avg_loss'] = stats['total_loss'] / stats['losses']
            
            # Calculate win rate
            if stats['total_signals'] > 0:
                stats['win_rate'] = (stats['wins'] / stats['total_signals']) * 100
            
            # Calculate signal strength (weighted by win rate and profit)
            # Higher win rate + higher profit = stronger signal
            profit_factor = stats['avg_profit'] / 100.0 if stats['avg_profit'] > 0 else 0
            loss_factor = stats['avg_loss'] / 100.0 if stats['avg_loss'] > 0 else 0
            net_factor = profit_factor - (loss_factor * 0.5)  # Losses hurt more
            
            stats['signal_strength'] = (stats['win_rate'] / 100.0) * 0.6 + net_factor * 0.4
            stats['last_updated'] = datetime.now().isoformat()
        
        # Auto-save periodically
        if len(self.signal_history) % 50 == 0:
            self.save_performance_data()
    
    def _extract_signals(self, signal_data: Dict) -> Dict[str, any]:
        """Extract all signals from signal data"""
        signals = {}
        
        # Extract from different sources
        if 'flow_metrics' in signal_data:
            metrics = signal_data['flow_metrics']
            signals['high_call_volume'] = 1.0 if metrics.get('total_call_volume', 0) > 100000 else 0.0
            signals['high_put_volume'] = 1.0 if metrics.get('total_put_volume', 0) > 100000 else 0.0
            signals['call_put_ratio_high'] = 1.0 if metrics.get('call_put_ratio', 1.0) > 1.5 else 0.0
            signals['call_put_ratio_low'] = 1.0 if metrics.get('call_put_ratio', 1.0) < 0.67 else 0.0
            signals['high_premium_flow'] = 1.0 if abs(metrics.get('net_premium_flow', 0)) > 5000000 else 0.0
        
        # EMA signals
        if 'ema_trend' in signal_data:
            signals['ema_bullish'] = 1.0 if signal_data.get('ema_trend', 0) > 0 else 0.0
            signals['ema_bearish'] = 1.0 if signal_data.get('ema_trend', 0) < 0 else 0.0
            signals['above_ema50'] = signal_data.get('above_ema50', 0.0)
            signals['price_vs_ema50_high'] = 1.0 if signal_data.get('price_vs_ema50', 0) > 2.0 else 0.0
            signals['price_vs_ema50_low'] = 1.0 if signal_data.get('price_vs_ema50', 0) < -2.0 else 0.0
        
        # Top/bottom prediction signals
        if 'approaching_top' in signal_data:
            signals['approaching_top'] = 1.0 if signal_data.get('approaching_top', False) else 0.0
        if 'approaching_bottom' in signal_data:
            signals['approaching_bottom'] = 1.0 if signal_data.get('approaching_bottom', False) else 0.0
        
        # Confidence levels
        confidence = signal_data.get('confidence', 50)
        signals['high_confidence'] = 1.0 if confidence >= 80 else 0.0
        signals['medium_confidence'] = 1.0 if 60 <= confidence < 80 else 0.0
        signals['low_confidence'] = 1.0 if confidence < 60 else 0.0
        
        # Market regime
        if 'market_regime' in signal_data:
            regime = signal_data.get('market_regime', {})
            signals['trending_market'] = 1.0 if regime.get('regime') == 'TRENDING' else 0.0
            signals['choppy_market'] = 1.0 if regime.get('regime') == 'CHOPPY' else 0.0
        
        return signals
    
    def analyze_signal_quality(self) -> Dict:
        """
        Analyze which signals are good vs useless
        Returns recommendations for what to keep/remove
        """
        analysis = {
            'high_value_signals': [],
            'useless_signals': [],
            'signals_to_weight_more': [],
            'signals_to_weight_less': [],
            'feature_importance': {},
            'recommendations': []
        }
        
        # Analyze each signal
        for signal_name, stats in self.signal_stats.items():
            if stats['total_signals'] < 10:  # Need minimum samples
                continue
            
            win_rate = stats['win_rate']
            signal_strength = stats['signal_strength']
            avg_profit = stats['avg_profit']
            
            # High value signals: >60% win rate AND positive avg profit
            if win_rate >= 60 and avg_profit > 5:
                analysis['high_value_signals'].append({
                    'signal': signal_name,
                    'win_rate': win_rate,
                    'avg_profit': avg_profit,
                    'strength': signal_strength
                })
                self.high_value_signals.add(signal_name)
            
            # Useless signals: <40% win rate OR negative avg profit with many samples
            elif (win_rate < 40 or (avg_profit < -5 and stats['total_signals'] > 20)):
                analysis['useless_signals'].append({
                    'signal': signal_name,
                    'win_rate': win_rate,
                    'avg_profit': avg_profit,
                    'strength': signal_strength
                })
                self.useless_signals.add(signal_name)
            
            # Signals to weight more: Good but not great
            elif win_rate >= 55 and avg_profit > 0:
                analysis['signals_to_weight_more'].append({
                    'signal': signal_name,
                    'win_rate': win_rate,
                    'avg_profit': avg_profit
                })
            
            # Signals to weight less: Poor but not terrible
            elif win_rate < 50 or avg_profit < 0:
                analysis['signals_to_weight_less'].append({
                    'signal': signal_name,
                    'win_rate': win_rate,
                    'avg_profit': avg_profit
                })
        
        # Calculate feature importance
        self._calculate_feature_importance()
        analysis['feature_importance'] = self.feature_importance
        
        # Generate recommendations
        analysis['recommendations'] = self._generate_recommendations(analysis)
        
        # Save updated data
        self.save_performance_data()
        
        return analysis
    
    def _calculate_feature_importance(self):
        """Calculate which features are most important"""
        feature_scores = defaultdict(float)
        
        for signal_entry in self.signal_history:
            if not signal_entry.get('outcome'):
                continue
            
            is_win = signal_entry['outcome'].get('outcome') == 'WIN'
            profit = signal_entry['outcome'].get('profit_pct', 0)
            
            signal_data = signal_entry.get('signal_data', {})
            
            # Extract features (simplified - would need full feature extraction)
            if 'features' in signal_data:
                features = signal_data['features']
                for feature_name, feature_value in features.items():
                    if isinstance(feature_value, (int, float)):
                        # Feature importance based on correlation with wins
                        if is_win:
                            feature_scores[feature_name] += abs(feature_value) * (profit / 100.0)
                        else:
                            feature_scores[feature_name] -= abs(feature_value) * (abs(profit) / 100.0)
        
        # Normalize feature importance
        if feature_scores:
            max_score = max(abs(s) for s in feature_scores.values())
            if max_score > 0:
                self.feature_importance = {
                    name: score / max_score
                    for name, score in feature_scores.items()
                }
    
    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # High value signals
        if analysis['high_value_signals']:
            top_signals = sorted(analysis['high_value_signals'], 
                               key=lambda x: x['strength'], reverse=True)[:5]
            recommendations.append(f"✅ KEEP & WEIGHT MORE: {', '.join([s['signal'] for s in top_signals])}")
        
        # Useless signals
        if analysis['useless_signals']:
            bad_signals = [s['signal'] for s in analysis['useless_signals']]
            recommendations.append(f"❌ REMOVE OR IGNORE: {', '.join(bad_signals[:5])}")
        
        # Feature importance
        if self.feature_importance:
            top_features = sorted(self.feature_importance.items(), 
                                key=lambda x: abs(x[1]), reverse=True)[:5]
            recommendations.append(f"📊 MOST IMPORTANT FEATURES: {', '.join([f[0] for f in top_features])}")
        
        return recommendations
    
    def get_signal_weights(self) -> Dict[str, float]:
        """
        Get dynamic weights for signals based on performance
        Returns signal_name -> weight (0.0 to 2.0)
        """
        weights = {}
        
        for signal_name, stats in self.signal_stats.items():
            if signal_name in self.useless_signals:
                weights[signal_name] = 0.0  # Disable useless signals
            elif signal_name in self.high_value_signals:
                weights[signal_name] = 2.0  # Double weight for high-value signals
            elif stats['total_signals'] >= 10:
                # Weight based on signal strength
                weights[signal_name] = 0.5 + (stats['signal_strength'] * 1.5)
            else:
                weights[signal_name] = 1.0  # Default weight
        
        return weights
    
    def should_use_signal(self, signal_name: str) -> bool:
        """Check if a signal should be used (not in useless list)"""
        return signal_name not in self.useless_signals
    
    def get_signal_boost(self, signal_name: str) -> float:
        """Get boost multiplier for high-value signals"""
        if signal_name in self.high_value_signals:
            return 1.5  # 50% boost
        return 1.0


# Global instance
signal_quality_analyzer = SignalQualityAnalyzer()

