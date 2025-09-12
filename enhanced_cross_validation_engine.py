"""
Enhanced Cross-Validation Engine
Multi-source data comparison with consensus scoring for institutional-grade accuracy
SYNCHRONOUS implementation - NO asyncio/async for compatibility
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import yfinance as yf
import numpy as np
import pandas as pd
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Cross-validation result with detailed scoring"""
    symbol: str
    consensus_score: int  # 0-100 overall validation score
    source_scores: Dict[str, int]  # Individual source scores
    discrepancies: List[str]  # List of discrepancy warnings
    confidence_level: int  # Final confidence in data accuracy
    validation_timestamp: datetime
    primary_source: str
    backup_sources: List[str]
    price_consistency: bool
    volume_consistency: bool
    historical_consistency: bool

class EnhancedCrossValidationEngine:
    """
    Institutional-grade cross-validation system for market data accuracy
    Compares multiple data sources and generates consensus scores
    """
    
    def __init__(self):
        self.validation_cache = {}
        self.cache_duration = 30  # 30 second validation cache
        self.historical_data_cache = {}
        self.price_tolerance = 0.05  # 5% price discrepancy threshold
        self.volume_tolerance = 0.15  # 15% volume discrepancy threshold
        self.validation_log = []
        
        # Data source configurations with reliability weights
        self.data_sources = {
            'yahoo_finance': {
                'weight': 0.9,  # Primary source weight
                'fetch_function': self._fetch_yahoo_data,
                'reliability_score': 90
            },
            'yahoo_options': {
                'weight': 0.8,  # Options-specific Yahoo data
                'fetch_function': self._fetch_yahoo_options_data,
                'reliability_score': 85
            },
            'historical_context': {
                'weight': 0.7,  # Historical validation
                'fetch_function': self._fetch_historical_context,
                'reliability_score': 80
            },
            'price_range_validator': {
                'weight': 0.6,  # Price reasonableness check
                'fetch_function': self._validate_price_range,
                'reliability_score': 75
            }
        }
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def validate_market_data(self, symbol: str, primary_data: Dict) -> ValidationResult:
        """
        Primary validation method - cross-validates market data using multiple sources
        Returns institutional-grade validation result with consensus scoring
        """
        cache_key = f"validation_{symbol}"
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            return self.validation_cache[cache_key]
        
        validation_start = time.time()
        
        # Initialize validation tracking
        source_results = {}
        discrepancies = []
        confidence_factors = []
        
        try:
            # 1. Fetch data from all sources SYNCHRONOUSLY
            for source_name, source_config in self.data_sources.items():
                try:
                    source_data = source_config['fetch_function'](symbol, primary_data)
                    source_results[source_name] = {
                        'data': source_data,
                        'score': self._score_source_data(source_data, primary_data, source_name),
                        'weight': source_config['weight'],
                        'reliability': source_config['reliability_score']
                    }
                except Exception as e:
                    self.logger.warning(f"Source {source_name} failed for {symbol}: {e}")
                    source_results[source_name] = {
                        'data': None,
                        'score': 0,
                        'weight': source_config['weight'],
                        'reliability': 0,
                        'error': str(e)
                    }
            
            # 2. Cross-validate price consistency
            price_consistency, price_discrepancies = self._validate_price_consistency(
                symbol, primary_data, source_results
            )
            discrepancies.extend(price_discrepancies)
            confidence_factors.append(90 if price_consistency else 40)
            
            # 3. Cross-validate volume consistency
            volume_consistency, volume_discrepancies = self._validate_volume_consistency(
                symbol, primary_data, source_results
            )
            discrepancies.extend(volume_discrepancies)
            confidence_factors.append(85 if volume_consistency else 50)
            
            # 4. Validate historical consistency
            historical_consistency, hist_discrepancies = self._validate_historical_consistency(
                symbol, primary_data, source_results
            )
            discrepancies.extend(hist_discrepancies)
            confidence_factors.append(80 if historical_consistency else 60)
            
            # 5. Calculate weighted consensus score
            consensus_score = self._calculate_consensus_score(source_results, confidence_factors)
            
            # 6. Determine confidence level
            confidence_level = self._calculate_confidence_level(
                consensus_score, len(discrepancies), confidence_factors
            )
            
            # 7. Select best sources
            primary_source = self._select_primary_source(source_results)
            backup_sources = self._select_backup_sources(source_results, primary_source)
            
            # Create validation result
            validation_result = ValidationResult(
                symbol=symbol,
                consensus_score=consensus_score,
                source_scores={name: result['score'] for name, result in source_results.items()},
                discrepancies=discrepancies,
                confidence_level=confidence_level,
                validation_timestamp=datetime.now(),
                primary_source=primary_source,
                backup_sources=backup_sources,
                price_consistency=price_consistency,
                volume_consistency=volume_consistency,
                historical_consistency=historical_consistency
            )
            
            # Cache result
            self._cache_validation_result(cache_key, validation_result)
            
            # Log validation performance
            validation_time = time.time() - validation_start
            self.logger.info(
                f"✅ CROSS-VALIDATED {symbol}: Consensus {consensus_score}%, "
                f"Confidence {confidence_level}%, {len(discrepancies)} discrepancies, "
                f"Validated in {validation_time:.2f}s"
            )
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Cross-validation failed for {symbol}: {e}")
            return ValidationResult(
                symbol=symbol,
                consensus_score=50,  # Neutral score on error
                source_scores={},
                discrepancies=[f"Validation error: {str(e)}"],
                confidence_level=30,
                validation_timestamp=datetime.now(),
                primary_source='unknown',
                backup_sources=[],
                price_consistency=False,
                volume_consistency=False,
                historical_consistency=False
            )
    
    def _fetch_yahoo_data(self, symbol: str, primary_data: Dict) -> Dict:
        """Fetch fresh Yahoo Finance data for comparison"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Get info and recent history
            info = ticker.info
            hist = ticker.history(period="2d", interval="1h")
            
            if hist.empty:
                return {'error': 'No historical data available'}
            
            current_price = float(hist['Close'].iloc[-1])
            current_volume = float(hist['Volume'].iloc[-1])
            
            return {
                'price': current_price,
                'volume': current_volume,
                'previous_close': info.get('previousClose', current_price),
                'market_cap': info.get('marketCap', 0),
                'avg_volume': info.get('averageVolume', current_volume),
                'data_source': 'yahoo_finance_fresh',
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            return {'error': f'Yahoo fetch failed: {str(e)}'}
    
    def _fetch_yahoo_options_data(self, symbol: str, primary_data: Dict) -> Dict:
        """Fetch Yahoo options data for additional validation"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Get options chain for additional price validation
            options_dates = ticker.options
            if not options_dates:
                return {'error': 'No options data available'}
            
            # Use nearest expiration for validation
            nearest_exp = options_dates[0]
            options_chain = ticker.option_chain(nearest_exp)
            
            if options_chain.calls.empty:
                return {'error': 'Empty options chain'}
            
            # Extract implied price from ATM options
            calls = options_chain.calls
            puts = options_chain.puts
            
            # Find ATM strike (closest to current price)
            current_price = primary_data.get('price', 150.0)
            atm_strike = calls.iloc[(calls['strike'] - current_price).abs().argsort()[:1]]['strike'].iloc[0]
            
            # Get ATM call and put data
            atm_call = calls[calls['strike'] == atm_strike].iloc[0] if len(calls[calls['strike'] == atm_strike]) > 0 else None
            atm_put = puts[puts['strike'] == atm_strike].iloc[0] if len(puts[puts['strike'] == atm_strike]) > 0 else None
            
            validation_data = {
                'atm_strike': atm_strike,
                'reference_price': current_price,
                'data_source': 'yahoo_options',
                'timestamp': datetime.now()
            }
            
            if atm_call is not None:
                validation_data.update({
                    'call_volume': atm_call.get('volume', 0),
                    'call_last': atm_call.get('lastPrice', 0),
                    'call_bid': atm_call.get('bid', 0),
                    'call_ask': atm_call.get('ask', 0)
                })
            
            if atm_put is not None:
                validation_data.update({
                    'put_volume': atm_put.get('volume', 0),
                    'put_last': atm_put.get('lastPrice', 0),
                    'put_bid': atm_put.get('bid', 0),
                    'put_ask': atm_put.get('ask', 0)
                })
            
            return validation_data
            
        except Exception as e:
            return {'error': f'Options fetch failed: {str(e)}'}
    
    def _fetch_historical_context(self, symbol: str, primary_data: Dict) -> Dict:
        """Fetch historical context for validation"""
        try:
            # Use cached historical data if available
            cache_key = f"hist_{symbol}"
            if cache_key in self.historical_data_cache:
                cached_time, cached_data = self.historical_data_cache[cache_key]
                if datetime.now() - cached_time < timedelta(hours=1):
                    return cached_data
            
            ticker = yf.Ticker(symbol)
            
            # Get 30-day history for context
            hist_30d = ticker.history(period="30d", interval="1d")
            hist_5d = ticker.history(period="5d", interval="1h")
            
            if hist_30d.empty or hist_5d.empty:
                return {'error': 'Insufficient historical data'}
            
            # Calculate historical metrics
            price_30d_high = float(hist_30d['High'].max())
            price_30d_low = float(hist_30d['Low'].min())
            price_30d_avg = float(hist_30d['Close'].mean())
            volume_30d_avg = float(hist_30d['Volume'].mean())
            
            price_5d_high = float(hist_5d['High'].max())
            price_5d_low = float(hist_5d['Low'].min())
            volume_5d_avg = float(hist_5d['Volume'].mean())
            
            # Calculate volatility
            returns = hist_30d['Close'].pct_change().dropna()
            volatility_30d = float(returns.std() * np.sqrt(252))  # Annualized
            
            context_data = {
                'price_30d_range': [price_30d_low, price_30d_high],
                'price_30d_avg': price_30d_avg,
                'price_5d_range': [price_5d_low, price_5d_high],
                'volume_30d_avg': volume_30d_avg,
                'volume_5d_avg': volume_5d_avg,
                'volatility_30d': volatility_30d,
                'data_source': 'historical_context',
                'timestamp': datetime.now()
            }
            
            # Cache the result
            self.historical_data_cache[cache_key] = (datetime.now(), context_data)
            
            return context_data
            
        except Exception as e:
            return {'error': f'Historical context failed: {str(e)}'}
    
    def _validate_price_range(self, symbol: str, primary_data: Dict) -> Dict:
        """Validate price against reasonable ranges"""
        try:
            current_price = primary_data.get('price', 0)
            
            if current_price <= 0:
                return {'error': 'Invalid price <= 0', 'validation': False}
            
            # Known price ranges for major symbols (updated periodically)
            symbol_ranges = {
                'SPY': [200, 800],
                'QQQ': [200, 800], 
                'AAPL': [100, 300],
                'TSLA': [50, 500],
                'NVDA': [50, 400],
                'MSFT': [200, 600],
                'GOOGL': [50, 300],
                'AMZN': [50, 300],
                'META': [200, 800],
                'NFLX': [200, 1200]
            }
            
            expected_range = symbol_ranges.get(symbol, [1, 2000])  # Default wide range
            
            price_valid = expected_range[0] <= current_price <= expected_range[1]
            
            return {
                'price_validation': price_valid,
                'expected_range': expected_range,
                'current_price': current_price,
                'data_source': 'price_range_validator',
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            return {'error': f'Price validation failed: {str(e)}'}
    
    def _validate_price_consistency(self, symbol: str, primary_data: Dict, 
                                  source_results: Dict) -> Tuple[bool, List[str]]:
        """Validate price consistency across sources"""
        discrepancies = []
        primary_price = primary_data.get('price', 0)
        
        if primary_price <= 0:
            return False, ['Primary price is invalid or missing']
        
        price_values = []
        
        # Collect all valid price values
        for source_name, result in source_results.items():
            if result['data'] and 'price' in result['data']:
                source_price = result['data'].get('price', 0)
                if source_price > 0:
                    price_values.append((source_name, source_price))
        
        # Check for significant discrepancies
        consistent = True
        for source_name, source_price in price_values:
            price_diff = abs(primary_price - source_price) / primary_price
            
            if price_diff > self.price_tolerance:
                discrepancies.append(
                    f"Price discrepancy: {source_name} {source_price:.2f} vs primary {primary_price:.2f} "
                    f"({price_diff:.1%} difference)"
                )
                consistent = False
        
        return consistent, discrepancies
    
    def _validate_volume_consistency(self, symbol: str, primary_data: Dict,
                                   source_results: Dict) -> Tuple[bool, List[str]]:
        """Validate volume consistency across sources"""
        discrepancies = []
        primary_volume = primary_data.get('volume', 0)
        
        if primary_volume <= 0:
            return True, []  # Volume validation is optional
        
        volume_values = []
        
        # Collect valid volume values
        for source_name, result in source_results.items():
            if result['data'] and 'volume' in result['data']:
                source_volume = result['data'].get('volume', 0)
                if source_volume > 0:
                    volume_values.append((source_name, source_volume))
        
        # Check for unrealistic volume spikes or drops
        consistent = True
        for source_name, source_volume in volume_values:
            volume_ratio = abs(primary_volume - source_volume) / max(primary_volume, source_volume)
            
            if volume_ratio > self.volume_tolerance:
                discrepancies.append(
                    f"Volume discrepancy: {source_name} {source_volume:,} vs primary {primary_volume:,} "
                    f"({volume_ratio:.1%} difference)"
                )
                consistent = False
        
        return consistent, discrepancies
    
    def _validate_historical_consistency(self, symbol: str, primary_data: Dict,
                                       source_results: Dict) -> Tuple[bool, List[str]]:
        """Validate against historical context"""
        discrepancies = []
        primary_price = primary_data.get('price', 0)
        
        # Get historical context
        hist_result = source_results.get('historical_context', {})
        hist_data = hist_result.get('data', {})
        
        if not hist_data or 'error' in hist_data:
            return True, []  # Skip if no historical data
        
        consistent = True
        
        # Check if price is within reasonable historical range
        price_30d_range = hist_data.get('price_30d_range', [0, 999999])
        if not (price_30d_range[0] <= primary_price <= price_30d_range[1]):
            discrepancies.append(
                f"Price outside 30-day range: {primary_price:.2f} not in "
                f"[{price_30d_range[0]:.2f}, {price_30d_range[1]:.2f}]"
            )
            consistent = False
        
        # Check for extreme volatility
        price_30d_avg = hist_data.get('price_30d_avg', primary_price)
        price_deviation = abs(primary_price - price_30d_avg) / price_30d_avg
        
        if price_deviation > 0.20:  # 20% deviation from 30-day average
            discrepancies.append(
                f"High price deviation from 30d average: {price_deviation:.1%} "
                f"({primary_price:.2f} vs avg {price_30d_avg:.2f})"
            )
            # Don't mark as inconsistent for high volatility, just warn
        
        return consistent, discrepancies
    
    def _score_source_data(self, source_data: Dict, primary_data: Dict, source_name: str) -> int:
        """Score individual source data quality (0-100)"""
        if not source_data or 'error' in source_data:
            return 0
        
        score = 100
        
        # Penalize missing essential fields
        if 'price' not in source_data:
            score -= 30
        
        if 'timestamp' not in source_data:
            score -= 10
        
        # Reward data freshness
        if 'timestamp' in source_data:
            time_diff = (datetime.now() - source_data['timestamp']).total_seconds()
            if time_diff > 300:  # Older than 5 minutes
                score -= 20
            elif time_diff > 60:  # Older than 1 minute  
                score -= 10
        
        # Source-specific scoring
        if source_name == 'yahoo_finance' and 'market_cap' in source_data:
            score += 5  # Bonus for comprehensive data
        
        if source_name == 'yahoo_options' and 'call_volume' in source_data:
            score += 5  # Bonus for options data
        
        return max(0, min(100, score))
    
    def _calculate_consensus_score(self, source_results: Dict, confidence_factors: List[int]) -> int:
        """Calculate weighted consensus score"""
        if not source_results:
            return 50
        
        # Calculate weighted average of source scores
        total_weighted_score = 0
        total_weights = 0
        
        for source_name, result in source_results.items():
            if result['score'] > 0:
                total_weighted_score += result['score'] * result['weight']
                total_weights += result['weight']
        
        if total_weights == 0:
            return 50
        
        weighted_avg = total_weighted_score / total_weights
        
        # Adjust by confidence factors
        confidence_avg = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 75
        confidence_multiplier = confidence_avg / 100
        
        final_score = int(weighted_avg * confidence_multiplier)
        return max(0, min(100, final_score))
    
    def _calculate_confidence_level(self, consensus_score: int, num_discrepancies: int, 
                                  confidence_factors: List[int]) -> int:
        """Calculate overall confidence level"""
        base_confidence = consensus_score
        
        # Penalize discrepancies
        discrepancy_penalty = min(30, num_discrepancies * 10)
        base_confidence -= discrepancy_penalty
        
        # Boost for multiple validating sources
        if len(confidence_factors) >= 3:
            base_confidence += 5
        
        return max(0, min(100, base_confidence))
    
    def _select_primary_source(self, source_results: Dict) -> str:
        """Select the best primary source based on scores and weights"""
        best_source = 'yahoo_finance'  # Default
        best_score = 0
        
        for source_name, result in source_results.items():
            weighted_score = result['score'] * result['weight']
            if weighted_score > best_score:
                best_score = weighted_score
                best_source = source_name
        
        return best_source
    
    def _select_backup_sources(self, source_results: Dict, primary_source: str) -> List[str]:
        """Select backup sources ranked by quality"""
        backup_sources = []
        
        # Create list of (source_name, weighted_score) tuples, excluding primary
        source_scores = []
        for source_name, result in source_results.items():
            if source_name != primary_source and result['score'] > 50:
                weighted_score = result['score'] * result['weight']
                source_scores.append((source_name, weighted_score))
        
        # Sort by weighted score descending
        source_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return top 2 backup sources
        backup_sources = [source[0] for source in source_scores[:2]]
        
        return backup_sources
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached validation is still valid"""
        if cache_key not in self.validation_cache:
            return False
        
        cached_time = self.validation_cache[cache_key].validation_timestamp
        return (datetime.now() - cached_time).total_seconds() < self.cache_duration
    
    def _cache_validation_result(self, cache_key: str, result: ValidationResult):
        """Cache validation result"""
        self.validation_cache[cache_key] = result
        
        # Keep cache size manageable
        if len(self.validation_cache) > 100:
            # Remove oldest entries
            oldest_key = min(self.validation_cache.keys(), 
                           key=lambda k: self.validation_cache[k].validation_timestamp)
            del self.validation_cache[oldest_key]
    
    def get_validation_summary(self) -> Dict:
        """Get summary of recent validations"""
        if not self.validation_cache:
            return {'total_validations': 0}
        
        recent_validations = list(self.validation_cache.values())
        
        avg_consensus = sum(v.consensus_score for v in recent_validations) / len(recent_validations)
        avg_confidence = sum(v.confidence_level for v in recent_validations) / len(recent_validations)
        
        high_quality_count = sum(1 for v in recent_validations if v.consensus_score >= 80)
        
        return {
            'total_validations': len(recent_validations),
            'avg_consensus_score': round(avg_consensus, 1),
            'avg_confidence_level': round(avg_confidence, 1),
            'high_quality_percentage': round((high_quality_count / len(recent_validations)) * 100, 1),
            'last_validation': recent_validations[-1].validation_timestamp.isoformat()
        }

# Global instance for easy access
enhanced_cross_validator = EnhancedCrossValidationEngine()