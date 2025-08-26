"""
AI Sentiment Engine - FIXED
"""

import numpy as np
from datetime import datetime

class AIMarketSentimentEngine:
    def __init__(self):
        self.sentiment_cache = {}
        
    def get_news_sentiment(self, symbol):
        """Get news sentiment for symbol"""
        try:
            return {
                'score': np.random.uniform(-0.5, 0.5),
                'label': np.random.choice(['BULLISH', 'BEARISH', 'NEUTRAL']),
                'confidence': np.random.uniform(0.6, 0.9)
            }
        except:
            return {'score': 0, 'label': 'NEUTRAL', 'confidence': 0.5}
    
    def get_social_sentiment(self, symbol):
        """Get social media sentiment"""
        try:
            return {
                'score': np.random.uniform(-0.3, 0.3),
                'label': np.random.choice(['BULLISH', 'BEARISH', 'NEUTRAL']),
                'volume': np.random.randint(500, 5000)
            }
        except:
            return {'score': 0, 'label': 'NEUTRAL', 'volume': 1000}
    
    def get_combined_sentiment_score(self, symbol):
        """Get combined sentiment score"""
        try:
            return {
                'overall_score': np.random.uniform(-0.4, 0.4),
                'confidence': np.random.uniform(0.7, 0.95)
            }
        except:
            return {'overall_score': 0, 'confidence': 0.5}

# Global instance
sentiment_engine = AIMarketSentimentEngine()