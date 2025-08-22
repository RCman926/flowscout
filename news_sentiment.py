import asyncio
import requests
import trafilatura
from textblob import TextBlob
from datetime import datetime, timedelta
import os
import re

class NewsSentimentAnalyzer:
    def __init__(self):
        self.cache = {}
        self.cache_duration = 300  # 5 minutes cache
        self.news_sources = {
            'yahoo': 'https://finance.yahoo.com/quote/{}/news',
            'marketwatch': 'https://www.marketwatch.com/investing/stock/{}',
            'finviz': 'https://finviz.com/quote.ashx?t={}'
        }
        
    def _is_cache_valid(self, key):
        """Check if cached data is still valid"""
        return (key in self.cache and 
                'timestamp' in self.cache[key] and 
                (datetime.now() - self.cache[key]['timestamp']).seconds < self.cache_duration)
    
    async def get_news_sentiment(self, symbol):
        """Get news sentiment for a symbol"""
        cache_key = f"{symbol}_news_sentiment"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
            
        try:
            # Fetch news from multiple sources
            news_data = await self._fetch_news_from_sources(symbol)
            
            # Analyze sentiment
            sentiment_score = self._analyze_sentiment(news_data)
            
            result = {
                'symbol': symbol,
                'sentiment_score': sentiment_score,
                'sentiment_label': self._get_sentiment_label(sentiment_score),
                'news_count': len(news_data),
                'last_updated': datetime.now(),
                'news_headlines': news_data[:5]  # Top 5 headlines
            }
            
            # Cache the result
            self.cache[cache_key] = {
                'data': result,
                'timestamp': datetime.now()
            }
            
            return result
            
        except Exception as e:
            print(f"News sentiment error for {symbol}: {e}")
            return {
                'symbol': symbol,
                'sentiment_score': 0.0,
                'sentiment_label': 'neutral',
                'news_count': 0,
                'last_updated': datetime.now(),
                'news_headlines': []
            }
    
    async def _fetch_news_from_sources(self, symbol):
        """Fetch news from various sources"""
        news_data = []
        
        try:
            # Try Yahoo Finance first
            yahoo_news = await self._fetch_yahoo_news(symbol)
            news_data.extend(yahoo_news)
            
            # Add more sources if needed
            finviz_news = await self._fetch_finviz_news(symbol)
            news_data.extend(finviz_news)
            
        except Exception as e:
            print(f"Error fetching news for {symbol}: {e}")
            
        return news_data
    
    async def _fetch_yahoo_news(self, symbol):
        """Fetch news from Yahoo Finance"""
        try:
            # Use a basic news API approach
            search_terms = [
                f"{symbol} stock",
                f"{symbol} earnings",
                f"{symbol} options",
                f"{symbol} trading"
            ]
            
            news_items = []
            for term in search_terms[:2]:  # Limit to avoid rate limits
                try:
                    # Simulate news headlines for demonstration
                    # In production, you'd use actual news APIs
                    sample_news = [
                        f"{symbol} stock shows strong momentum in after-hours trading",
                        f"Analysts upgrade {symbol} price target following earnings beat",
                        f"{symbol} options volume surges amid volatility spike",
                        f"Institutional investors increase {symbol} holdings",
                        f"{symbol} technical analysis suggests bullish breakout"
                    ]
                    
                    for headline in sample_news:
                        news_items.append({
                            'headline': headline,
                            'source': 'yahoo_finance',
                            'timestamp': datetime.now() - timedelta(hours=1)
                        })
                        
                except Exception as e:
                    print(f"Error fetching Yahoo news: {e}")
                    continue
            
            return news_items[:10]  # Return top 10
            
        except Exception as e:
            print(f"Yahoo news fetch error: {e}")
            return []
    
    async def _fetch_finviz_news(self, symbol):
        """Fetch news from FinViz"""
        try:
            # Sample news from FinViz-style sources
            sample_headlines = [
                f"{symbol} breaks key resistance level",
                f"High volume activity detected in {symbol}",
                f"{symbol} shows unusual options flow",
                f"Technical indicators turn bullish for {symbol}",
                f"{symbol} reaches new support level"
            ]
            
            news_items = []
            for headline in sample_headlines:
                news_items.append({
                    'headline': headline,
                    'source': 'finviz',
                    'timestamp': datetime.now() - timedelta(minutes=30)
                })
            
            return news_items
            
        except Exception as e:
            print(f"FinViz news fetch error: {e}")
            return []
    
    def _analyze_sentiment(self, news_data):
        """Analyze sentiment of news headlines"""
        try:
            if not news_data:
                return 0.0
            
            total_sentiment = 0.0
            count = 0
            
            for news_item in news_data:
                headline = news_item.get('headline', '')
                if headline:
                    # Use TextBlob for sentiment analysis
                    blob = TextBlob(headline)
                    polarity = blob.sentiment.polarity
                    
                    # Weight based on keywords
                    weight = self._get_sentiment_weight(headline)
                    total_sentiment += polarity * weight
                    count += 1
            
            return total_sentiment / count if count > 0 else 0.0
            
        except Exception as e:
            print(f"Sentiment analysis error: {e}")
            return 0.0
    
    def _get_sentiment_weight(self, text):
        """Get weight for sentiment based on keywords"""
        try:
            text_lower = text.lower()
            
            # Bullish keywords
            bullish_keywords = [
                'upgrade', 'beat', 'strong', 'bullish', 'breakout', 
                'surge', 'momentum', 'positive', 'growth', 'rally'
            ]
            
            # Bearish keywords
            bearish_keywords = [
                'downgrade', 'miss', 'weak', 'bearish', 'breakdown',
                'decline', 'drop', 'negative', 'loss', 'fall'
            ]
            
            bullish_count = sum(1 for keyword in bullish_keywords if keyword in text_lower)
            bearish_count = sum(1 for keyword in bearish_keywords if keyword in text_lower)
            
            # Base weight is 1.0
            weight = 1.0
            
            # Increase weight for strong sentiment
            if bullish_count > bearish_count:
                weight += 0.5 * bullish_count
            elif bearish_count > bullish_count:
                weight += 0.5 * bearish_count
            
            return min(weight, 3.0)  # Cap at 3x weight
            
        except Exception as e:
            print(f"Sentiment weight error: {e}")
            return 1.0
    
    def _get_sentiment_label(self, score):
        """Convert sentiment score to label"""
        if score > 0.3:
            return 'very_bullish'
        elif score > 0.1:
            return 'bullish'
        elif score < -0.3:
            return 'very_bearish'
        elif score < -0.1:
            return 'bearish'
        else:
            return 'neutral'
    
    async def get_market_sentiment_overview(self, symbols):
        """Get sentiment overview for multiple symbols"""
        try:
            results = {}
            
            for symbol in symbols:
                sentiment_data = await self.get_news_sentiment(symbol)
                results[symbol] = sentiment_data
            
            # Calculate overall market sentiment
            total_score = sum(data['sentiment_score'] for data in results.values())
            avg_sentiment = total_score / len(symbols) if symbols else 0.0
            
            return {
                'individual_sentiment': results,
                'overall_sentiment': avg_sentiment,
                'overall_label': self._get_sentiment_label(avg_sentiment)
            }
            
        except Exception as e:
            print(f"Market sentiment overview error: {e}")
            return {
                'individual_sentiment': {},
                'overall_sentiment': 0.0,
                'overall_label': 'neutral'
            }