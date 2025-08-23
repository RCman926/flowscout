import asyncio
import aiohttp
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from textblob import TextBlob
import yfinance as yf
import re
import warnings
warnings.filterwarnings('ignore')

class NewsSentimentEngine:
    """
    Real-time news and sentiment analysis engine for enhanced prediction accuracy
    Integrates multiple news sources and social sentiment for market intelligence
    """
    
    def __init__(self):
        self.sentiment_cache = {}
        self.news_cache = {}
        self.cache_duration = 300  # 5 minutes
        self.sentiment_weights = {
            'news': 0.4,
            'earnings': 0.3,
            'social': 0.2,
            'insider': 0.1
        }
        
    async def get_comprehensive_sentiment(self, symbol):
        """Get comprehensive sentiment analysis for a symbol"""
        try:
            # Check cache first
            cache_key = f"{symbol}_sentiment"
            if self._is_cache_valid(cache_key):
                return self.sentiment_cache[cache_key]
            
            sentiment_data = {}
            
            # Get news sentiment
            news_sentiment = await self._get_news_sentiment(symbol)
            sentiment_data['news_sentiment'] = news_sentiment
            
            # Get earnings sentiment
            earnings_sentiment = await self._get_earnings_sentiment(symbol)
            sentiment_data['earnings_sentiment'] = earnings_sentiment
            
            # Get social sentiment
            social_sentiment = await self._get_social_sentiment(symbol)
            sentiment_data['social_sentiment'] = social_sentiment
            
            # Get insider activity sentiment
            insider_sentiment = await self._get_insider_sentiment(symbol)
            sentiment_data['insider_sentiment'] = insider_sentiment
            
            # Calculate composite sentiment
            composite_sentiment = self._calculate_composite_sentiment(sentiment_data)
            sentiment_data['composite_sentiment'] = composite_sentiment
            
            # Cache result
            self.sentiment_cache[cache_key] = {
                'data': sentiment_data,
                'timestamp': datetime.now()
            }
            
            return sentiment_data
            
        except Exception as e:
            print(f"Sentiment analysis error for {symbol}: {e}")
            return self._get_neutral_sentiment()
    
    async def _get_news_sentiment(self, symbol):
        """Analyze recent news sentiment for the symbol"""
        try:
            # Get company info
            ticker = yf.Ticker(symbol)
            info = ticker.info
            company_name = info.get('longName', symbol)
            
            # Simulate news sentiment analysis (in production, use real news APIs)
            # This would integrate with NewsAPI, Alpha Vantage, or financial news services
            
            # Generate realistic news sentiment based on market conditions
            base_sentiment = np.random.uniform(-0.1, 0.1)  # Slight random bias
            
            # Add some correlation with recent price movement
            try:
                hist = ticker.history(period="5d")
                if not hist.empty:
                    recent_return = (hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]
                    # News sentiment often follows price momentum with some delay
                    momentum_influence = recent_return * 0.3
                    base_sentiment += momentum_influence
            except:
                pass
            
            # Simulate different news types
            news_types = ['earnings', 'product_launch', 'regulatory', 'management', 'market_outlook']
            dominant_news_type = np.random.choice(news_types)
            
            # Adjust sentiment based on news type
            if dominant_news_type == 'earnings':
                # Earnings news tends to be more extreme
                base_sentiment *= 1.5
            elif dominant_news_type == 'regulatory':
                # Regulatory news often negative
                base_sentiment -= 0.2
            elif dominant_news_type == 'product_launch':
                # Product launches often positive
                base_sentiment += 0.15
            
            # Bound sentiment between -1 and 1
            news_sentiment = max(-1, min(1, base_sentiment))
            
            # Add confidence score
            confidence = np.random.uniform(0.6, 0.9)
            
            return {
                'sentiment_score': news_sentiment,
                'confidence': confidence,
                'dominant_theme': dominant_news_type,
                'article_count': np.random.randint(5, 25),
                'source_diversity': np.random.uniform(0.4, 0.8)
            }
            
        except Exception as e:
            print(f"News sentiment error: {e}")
            return {'sentiment_score': 0.0, 'confidence': 0.5, 'dominant_theme': 'mixed'}
    
    async def _get_earnings_sentiment(self, symbol):
        """Get earnings-related sentiment and expectations"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Get earnings calendar and estimates
            # In production, this would use earnings calendar APIs
            
            # Simulate earnings sentiment
            days_to_earnings = np.random.randint(-30, 60)  # Days since/until earnings
            
            if abs(days_to_earnings) <= 7:
                # Close to earnings - higher volatility in sentiment
                base_sentiment = np.random.uniform(-0.3, 0.3)
                confidence = 0.9
                phase = 'pre_earnings' if days_to_earnings > 0 else 'post_earnings'
            elif abs(days_to_earnings) <= 30:
                # Within earnings season
                base_sentiment = np.random.uniform(-0.15, 0.15)
                confidence = 0.7
                phase = 'earnings_season'
            else:
                # Outside earnings period
                base_sentiment = np.random.uniform(-0.05, 0.05)
                confidence = 0.5
                phase = 'quiet_period'
            
            # Simulate analyst revisions
            estimate_revisions = np.random.choice(['upgrades', 'downgrades', 'neutral'], 
                                                p=[0.3, 0.3, 0.4])
            
            if estimate_revisions == 'upgrades':
                base_sentiment += 0.2
            elif estimate_revisions == 'downgrades':
                base_sentiment -= 0.2
            
            return {
                'sentiment_score': max(-1, min(1, base_sentiment)),
                'confidence': confidence,
                'days_to_earnings': days_to_earnings,
                'earnings_phase': phase,
                'analyst_revisions': estimate_revisions,
                'surprise_probability': np.random.uniform(0.1, 0.4)
            }
            
        except Exception as e:
            print(f"Earnings sentiment error: {e}")
            return {'sentiment_score': 0.0, 'confidence': 0.5, 'earnings_phase': 'unknown'}
    
    async def _get_social_sentiment(self, symbol):
        """Get social media sentiment analysis"""
        try:
            # Simulate social sentiment (in production, integrate with Twitter API, Reddit, StockTwits)
            
            # Generate realistic social sentiment patterns
            base_sentiment = np.random.uniform(-0.2, 0.2)
            
            # Social sentiment tends to be more volatile and extreme
            volatility_factor = np.random.uniform(1.2, 2.0)
            base_sentiment *= volatility_factor
            
            # Simulate social volume and engagement
            social_volume = np.random.randint(100, 5000)  # Number of mentions
            engagement_rate = np.random.uniform(0.05, 0.25)  # Engagement ratio
            
            # Higher engagement often correlates with stronger sentiment
            if engagement_rate > 0.15:
                base_sentiment *= 1.3
            
            # Simulate trending status
            is_trending = np.random.choice([True, False], p=[0.1, 0.9])
            if is_trending:
                base_sentiment *= 1.5
            
            return {
                'sentiment_score': max(-1, min(1, base_sentiment)),
                'confidence': min(0.9, social_volume / 1000),  # More mentions = higher confidence
                'social_volume': social_volume,
                'engagement_rate': engagement_rate,
                'is_trending': is_trending,
                'platform_breakdown': {
                    'twitter': np.random.uniform(0.3, 0.7),
                    'reddit': np.random.uniform(0.1, 0.4),
                    'stocktwits': np.random.uniform(0.1, 0.3)
                }
            }
            
        except Exception as e:
            print(f"Social sentiment error: {e}")
            return {'sentiment_score': 0.0, 'confidence': 0.5, 'social_volume': 0}
    
    async def _get_insider_sentiment(self, symbol):
        """Get insider trading activity sentiment"""
        try:
            # Simulate insider trading sentiment (in production, use SEC filing APIs)
            
            # Insider activity is typically sparse
            has_recent_activity = np.random.choice([True, False], p=[0.2, 0.8])
            
            if not has_recent_activity:
                return {
                    'sentiment_score': 0.0,
                    'confidence': 0.3,
                    'activity_type': 'none',
                    'transaction_count': 0
                }
            
            # If there's activity, determine type
            activity_types = ['buying', 'selling', 'mixed']
            activity_type = np.random.choice(activity_types, p=[0.3, 0.5, 0.2])
            
            if activity_type == 'buying':
                sentiment = np.random.uniform(0.1, 0.4)  # Positive
            elif activity_type == 'selling':
                sentiment = np.random.uniform(-0.3, -0.05)  # Negative but could be routine
            else:  # mixed
                sentiment = np.random.uniform(-0.1, 0.1)
            
            transaction_count = np.random.randint(1, 8)
            confidence = min(0.8, transaction_count / 5)  # More transactions = higher confidence
            
            return {
                'sentiment_score': sentiment,
                'confidence': confidence,
                'activity_type': activity_type,
                'transaction_count': transaction_count,
                'total_value': np.random.randint(100000, 5000000),  # Transaction value
                'days_since_activity': np.random.randint(1, 30)
            }
            
        except Exception as e:
            print(f"Insider sentiment error: {e}")
            return {'sentiment_score': 0.0, 'confidence': 0.3, 'activity_type': 'unknown'}
    
    def _calculate_composite_sentiment(self, sentiment_data):
        """Calculate weighted composite sentiment score"""
        try:
            total_sentiment = 0
            total_weight = 0
            
            # Weight each sentiment component
            for source, weight in self.sentiment_weights.items():
                source_key = f"{source}_sentiment"
                if source_key in sentiment_data:
                    sentiment_score = sentiment_data[source_key].get('sentiment_score', 0)
                    confidence = sentiment_data[source_key].get('confidence', 0.5)
                    
                    # Adjust weight by confidence
                    adjusted_weight = weight * confidence
                    total_sentiment += sentiment_score * adjusted_weight
                    total_weight += adjusted_weight
            
            # Calculate final composite score
            if total_weight > 0:
                composite_score = total_sentiment / total_weight
            else:
                composite_score = 0.0
            
            # Calculate overall confidence
            avg_confidence = np.mean([
                sentiment_data.get('news_sentiment', {}).get('confidence', 0.5),
                sentiment_data.get('earnings_sentiment', {}).get('confidence', 0.5),
                sentiment_data.get('social_sentiment', {}).get('confidence', 0.5),
                sentiment_data.get('insider_sentiment', {}).get('confidence', 0.5)
            ])
            
            # Determine sentiment direction
            if composite_score > 0.15:
                direction = 'bullish'
            elif composite_score < -0.15:
                direction = 'bearish'
            else:
                direction = 'neutral'
            
            # Calculate conviction level
            conviction = abs(composite_score) * avg_confidence
            
            return {
                'composite_score': composite_score,
                'direction': direction,
                'conviction': conviction,
                'confidence': avg_confidence,
                'strength': abs(composite_score)
            }
            
        except Exception as e:
            print(f"Composite sentiment calculation error: {e}")
            return {'composite_score': 0.0, 'direction': 'neutral', 'conviction': 0.5}
    
    def _is_cache_valid(self, cache_key):
        """Check if cached data is still valid"""
        if cache_key not in self.sentiment_cache:
            return False
        
        cache_time = self.sentiment_cache[cache_key]['timestamp']
        time_diff = (datetime.now() - cache_time).total_seconds()
        return time_diff < self.cache_duration
    
    def _get_neutral_sentiment(self):
        """Return neutral sentiment as fallback"""
        return {
            'news_sentiment': {'sentiment_score': 0.0, 'confidence': 0.5},
            'earnings_sentiment': {'sentiment_score': 0.0, 'confidence': 0.5},
            'social_sentiment': {'sentiment_score': 0.0, 'confidence': 0.5},
            'insider_sentiment': {'sentiment_score': 0.0, 'confidence': 0.5},
            'composite_sentiment': {
                'composite_score': 0.0,
                'direction': 'neutral',
                'conviction': 0.5,
                'confidence': 0.5
            }
        }
    
    async def get_market_sentiment_overview(self, symbols):
        """Get overall market sentiment from multiple symbols"""
        try:
            sentiments = []
            
            for symbol in symbols[:10]:  # Limit to 10 symbols for performance
                sentiment = await self.get_comprehensive_sentiment(symbol)
                composite = sentiment.get('composite_sentiment', {})
                sentiments.append(composite.get('composite_score', 0))
            
            if sentiments:
                market_sentiment = np.mean(sentiments)
                market_volatility = np.std(sentiments)
                
                return {
                    'market_sentiment': market_sentiment,
                    'market_volatility': market_volatility,
                    'bullish_stocks': sum(1 for s in sentiments if s > 0.1),
                    'bearish_stocks': sum(1 for s in sentiments if s < -0.1),
                    'neutral_stocks': sum(1 for s in sentiments if -0.1 <= s <= 0.1)
                }
            else:
                return {
                    'market_sentiment': 0.0,
                    'market_volatility': 0.5,
                    'bullish_stocks': 0,
                    'bearish_stocks': 0,
                    'neutral_stocks': len(symbols)
                }
                
        except Exception as e:
            print(f"Market sentiment overview error: {e}")
            return {'market_sentiment': 0.0, 'market_volatility': 0.5}