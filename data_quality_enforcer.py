"""
Data Quality Enforcer - Implements Zero Tolerance Policy for Synthetic Data
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging

class DataQualityEnforcer:
    """Enforces strict data quality standards with zero tolerance for synthetic data"""
    
    def __init__(self):
        self.quality_thresholds = {
            'INSTITUTIONAL': 95,  # 95%+ for institutional grade
            'PROFESSIONAL': 85,   # 85%+ for professional grade
            'ACCEPTABLE': 70,     # 70%+ for basic usage
            'REJECT': 69          # Below 70% gets rejected
        }
        
        self.authentic_sources = {
            'yahoo_finance_authenticated',
            'ibkr_live',
            'schwab_live',
            'td_ameritrade_live',
            'fidelity_live'
        }
        
        self.synthetic_indicators = {
            'random_walk',
            'simulated',
            'mock',
            'demo',
            'test',
            'fallback_synthetic',
            'generated'
        }
    
    def enforce_quality_standards(self, data: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """
        Enforce zero tolerance quality standards
        
        Args:
            data: Market data to validate
            symbol: Trading symbol
            
        Returns:
            Validation result with enforcement actions
        """
        result = {
            'passed': False,
            'quality_grade': 'REJECTED',
            'enforcement_actions': [],
            'data_source': 'UNKNOWN',
            'authenticity_score': 0,
            'reasons': []
        }
        
        # Check data source authenticity
        data_source = data.get('data_source', '').lower()
        
        # Immediate rejection for synthetic sources
        if any(indicator in data_source for indicator in self.synthetic_indicators):
            result['enforcement_actions'].append('REJECT_SYNTHETIC')
            result['reasons'].append(f"Synthetic data source detected: {data_source}")
            return result
        
        # Check if source is in approved list
        is_authentic_source = any(auth_source in data_source for auth_source in self.authentic_sources)
        
        if not is_authentic_source:
            result['enforcement_actions'].append('REJECT_UNAUTHENTICATED')
            result['reasons'].append(f"Unauthenticated source: {data_source}")
            return result
        
        # Calculate authenticity score
        authenticity_score = self._calculate_authenticity_score(data)
        result['authenticity_score'] = authenticity_score
        
        # Determine quality grade
        if authenticity_score >= self.quality_thresholds['INSTITUTIONAL']:
            result['quality_grade'] = 'INSTITUTIONAL'
            result['passed'] = True
        elif authenticity_score >= self.quality_thresholds['PROFESSIONAL']:
            result['quality_grade'] = 'PROFESSIONAL'
            result['passed'] = True
        elif authenticity_score >= self.quality_thresholds['ACCEPTABLE']:
            result['quality_grade'] = 'ACCEPTABLE'
            result['passed'] = True
        else:
            result['quality_grade'] = 'REJECTED'
            result['enforcement_actions'].append('REJECT_LOW_QUALITY')
            result['reasons'].append(f"Quality score {authenticity_score}% below minimum threshold")
        
        # Check data freshness
        freshness_penalty = self._check_data_freshness(data)
        if freshness_penalty > 0:
            result['authenticity_score'] -= freshness_penalty
            result['reasons'].append(f"Data freshness penalty: -{freshness_penalty}%")
        
        result['data_source'] = data_source
        
        return result
    
    def _calculate_authenticity_score(self, data: Dict[str, Any]) -> float:
        """Calculate authenticity score based on data characteristics"""
        score = 0
        
        # Base score for having essential fields
        required_fields = ['price', 'volume', 'timestamp']
        field_score = sum(30 for field in required_fields if field in data) / len(required_fields)
        score += field_score
        
        # Bonus for bid/ask spread (indicates real market data)
        if 'bid' in data and 'ask' in data:
            spread = abs(data['ask'] - data['bid'])
            if 0 < spread < data['price'] * 0.1:  # Reasonable spread
                score += 20
        
        # Bonus for realistic volume
        volume = data.get('volume', 0)
        if volume > 0 and volume < 1e12:  # Not zero, not impossibly high
            score += 15
        
        # Bonus for recent timestamp
        timestamp = data.get('timestamp', datetime.now())
        if isinstance(timestamp, datetime):
            age_minutes = (datetime.now() - timestamp).total_seconds() / 60
            if age_minutes < 5:
                score += 25
            elif age_minutes < 30:
                score += 15
            elif age_minutes < 60:
                score += 10
        
        # Bonus for quality indicators
        if data.get('data_freshness') == 'LIVE_SCRAPED':
            score += 10
        
        return min(100, max(0, score))
    
    def _check_data_freshness(self, data: Dict[str, Any]) -> float:
        """Check data freshness and return penalty if stale"""
        timestamp = data.get('timestamp', datetime.now())
        if not isinstance(timestamp, datetime):
            return 20  # No valid timestamp = 20% penalty
        
        age_minutes = (datetime.now() - timestamp).total_seconds() / 60
        
        if age_minutes > 1440:  # More than 24 hours
            return 50
        elif age_minutes > 60:  # More than 1 hour
            return 30
        elif age_minutes > 15:  # More than 15 minutes
            return 10
        else:
            return 0
    
    def create_rejection_message(self, validation_result: Dict[str, Any]) -> str:
        """Create user-friendly rejection message"""
        if not validation_result['passed']:
            reasons = " | ".join(validation_result['reasons'])
            return f"❌ DATA REJECTED: {reasons}"
        else:
            grade = validation_result['quality_grade']
            score = validation_result['authenticity_score']
            return f"✅ {grade} GRADE: {score:.0f}% authentic"
    
    def get_enforcement_recommendations(self, validation_result: Dict[str, Any]) -> List[str]:
        """Get recommendations for improving data quality"""
        recommendations = []
        
        if 'REJECT_SYNTHETIC' in validation_result['enforcement_actions']:
            recommendations.append("Enable authentic data sources (IBKR, Yahoo Finance live)")
            recommendations.append("Disable all synthetic and demo data feeds")
        
        if 'REJECT_UNAUTHENTICATED' in validation_result['enforcement_actions']:
            recommendations.append("Configure authenticated data sources")
            recommendations.append("Verify API keys and connection settings")
        
        if 'REJECT_LOW_QUALITY' in validation_result['enforcement_actions']:
            recommendations.append("Check data feed connectivity")
            recommendations.append("Ensure real-time data subscriptions are active")
        
        return recommendations

# Global instance
data_quality_enforcer = DataQualityEnforcer()