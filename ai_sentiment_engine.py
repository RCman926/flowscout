import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import requests
from textblob import TextBlob
import yfinance as yf
from trafilatura import fetch_url, extract
import re
import json
import os
from typing import Dict, List, Tuple

class AIMarketSentimentEngine:
    def __init__(self):
        self.sentiment_cache = {}
        self.news_sources = [
            'https://feeds.finance.yahoo.com/rss/2.0/headline',
            'https://www.marketwatch.com/rss/',
            'https://feeds.bloomberg.com/markets/news.rss'
        ]
        self.social_keywords = ['bullish', 'bearish', 'moon', 'dump', 'rally', 'crash', 'squeeze']
        
    async def analyze_market_sentiment(self, symbol: str) -> Dict:
        """Comprehensive market sentiment analysis for a symbol"""
        try:
            sentiment_data = {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'overall_sentiment': 0.0,
                'confidence': 0.0,
                'news_sentiment': 0.0,
                'technical_sentiment': 0.0,
                'social_sentiment': 0.0,
                'prediction': None,
                'sentiment_breakdown': {},
                'key_factors': [],
                'risk_assessment': 'MODERATE'
            }
            
            # Get multiple sentiment sources
            news_sentiment = await self._analyze_news_sentiment(symbol)
            technical_sentiment = await self._analyze_technical_sentiment(symbol)
            social_sentiment = await self._analyze_social_sentiment(symbol)
            market_structure = await self._analyze_market_structure(symbol)
            
            # Weighted sentiment calculation (institutional approach)
            weights = {
                'news': 0.35,
                'technical': 0.25,
                'social': 0.20,
                'market_structure': 0.20
            }
            
            overall_sentiment = (
                news_sentiment['score'] * weights['news'] +
                technical_sentiment['score'] * weights['technical'] +
                social_sentiment['score'] * weights['social'] +
                market_structure['score'] * weights['market_structure']
            )
            
            # Calculate confidence based on agreement between sources
            sentiments = [news_sentiment['score'], technical_sentiment['score'], 
                         social_sentiment['score'], market_structure['score']]
            confidence = 1.0 - (np.std(sentiments) / 2.0)  # Lower std = higher confidence
            
            sentiment_data.update({
                'overall_sentiment': round(overall_sentiment, 3),
                'confidence': round(confidence, 3),
                'news_sentiment': news_sentiment['score'],
                'technical_sentiment': technical_sentiment['score'],
                'social_sentiment': social_sentiment['score'],
                'sentiment_breakdown': {
                    'news': news_sentiment,
                    'technical': technical_sentiment,
                    'social': social_sentiment,
                    'market_structure': market_structure
                }
            })
            
            # Generate prediction
            prediction = await self._generate_prediction(sentiment_data, symbol)
            sentiment_data['prediction'] = prediction
            
            # Assess risk
            sentiment_data['risk_assessment'] = self._assess_risk_level(sentiment_data)
            
            return sentiment_data
            
        except Exception as e:
            print(f"Sentiment analysis error for {symbol}: {e}")
            return self._get_neutral_sentiment(symbol)
    
    async def _analyze_news_sentiment(self, symbol: str) -> Dict:
        """Analyze news sentiment for the symbol"""
        try:
            # Get recent news using Yahoo Finance
            ticker = yf.Ticker(symbol)
            news = ticker.news
            
            if not news:
                return {'score': 0.0, 'articles_count': 0, 'key_themes': []}
            
            sentiments = []
            key_themes = []
            
            for article in news[:10]:  # Analyze recent 10 articles
                try:
                    # Extract article content
                    title = article.get('title', '')
                    summary = article.get('summary', '')
                    
                    # Combine title and summary for analysis
                    text = f"{title} {summary}"
                    
                    if text.strip():
                        # Analyze sentiment
                        blob = TextBlob(text)
                        sentiment_score = blob.sentiment.polarity
                        sentiments.append(sentiment_score)
                        
                        # Extract key themes
                        if sentiment_score > 0.1:
                            key_themes.append('positive_news')
                        elif sentiment_score < -0.1:
                            key_themes.append('negative_news')
                            
                except Exception as e:
                    continue
            
            if sentiments:
                avg_sentiment = np.mean(sentiments)
                return {
                    'score': round(avg_sentiment, 3),
                    'articles_count': len(sentiments),
                    'key_themes': list(set(key_themes)),
                    'sentiment_distribution': {
                        'positive': len([s for s in sentiments if s > 0.1]),
                        'negative': len([s for s in sentiments if s < -0.1]),
                        'neutral': len([s for s in sentiments if -0.1 <= s <= 0.1])
                    }
                }
            
            return {'score': 0.0, 'articles_count': 0, 'key_themes': []}
            
        except Exception as e:
            print(f"News sentiment analysis error: {e}")
            return {'score': 0.0, 'articles_count': 0, 'key_themes': []}
    
    async def _analyze_technical_sentiment(self, symbol: str) -> Dict:
        """Convert technical indicators to sentiment score"""
        try:
            from technical_indicators import TechnicalAnalyzer
            
            # Get price data
            ticker = yf.Ticker(symbol)
            hist_data = ticker.history(period="30d")
            
            if hist_data.empty:
                return {'score': 0.0, 'indicators': {}}
            
            price_data = hist_data['Close'].values
            volume_data = hist_data['Volume'].values
            
            # Calculate technical indicators
            tech_analyzer = TechnicalAnalyzer()
            indicators = tech_analyzer.calculate_all_indicators(price_data, volume_data)
            
            # Convert indicators to sentiment scores
            sentiment_components = []
            
            # RSI sentiment
            rsi = indicators.get('rsi')
            if rsi is not None and isinstance(rsi, (int, float)):
                if rsi > 70:
                    sentiment_components.append(-0.3)  # Overbought = bearish
                elif rsi < 30:
                    sentiment_components.append(0.3)   # Oversold = bullish
                else:
                    sentiment_components.append((50 - rsi) / 100)  # Normalize
            
            # MACD sentiment
            macd = indicators.get('macd')
            macd_signal = indicators.get('macd_signal')
            if (macd is not None and macd_signal is not None and
                isinstance(macd, (int, float)) and isinstance(macd_signal, (int, float))):
                if macd > macd_signal:
                    sentiment_components.append(0.2)  # Bullish crossover
                else:
                    sentiment_components.append(-0.2)  # Bearish crossover
            
            # Moving average sentiment
            ema_20 = indicators.get('ema_20')
            ema_50 = indicators.get('ema_50')
            if (ema_20 is not None and ema_50 is not None and 
                isinstance(ema_20, (int, float)) and isinstance(ema_50, (int, float))):
                if ema_20 > ema_50:
                    sentiment_components.append(0.25)  # Bullish trend
                elif ema_20 < ema_50:
                    sentiment_components.append(-0.25)  # Bearish trend
            
            # Volume sentiment
            volume_ratio = indicators.get('volume_ratio', 1)
            if volume_ratio > 1.5:
                sentiment_components.append(0.15)  # High volume = bullish
            elif volume_ratio < 0.7:
                sentiment_components.append(-0.1)  # Low volume = bearish
            
            technical_sentiment = np.mean(sentiment_components) if sentiment_components else 0.0
            
            return {
                'score': round(technical_sentiment, 3),
                'indicators': indicators,
                'components': len(sentiment_components)
            }
            
        except Exception as e:
            print(f"Technical sentiment error: {e}")
            return {'score': 0.0, 'indicators': {}}
    
    async def _analyze_social_sentiment(self, symbol: str) -> Dict:
        """Analyze social media sentiment (simulated based on volume and volatility)"""
        try:
            # Get market data for social sentiment proxy
            ticker = yf.Ticker(symbol)
            hist_data = ticker.history(period="7d")
            
            if hist_data.empty:
                return {'score': 0.0, 'social_activity': 'LOW'}
            
            # Use volume and volatility as proxy for social sentiment
            recent_volume = hist_data['Volume'].iloc[-1]
            avg_volume = hist_data['Volume'].mean()
            
            recent_price = hist_data['Close'].iloc[-1]
            prev_price = hist_data['Close'].iloc[-2] if len(hist_data) > 1 else recent_price
            
            price_change = (recent_price - prev_price) / prev_price
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
            
            # Social sentiment based on activity and price movement
            social_sentiment = 0.0
            activity_level = "LOW"
            
            if volume_ratio > 2.0:
                activity_level = "HIGH"
                if price_change > 0.02:  # Strong positive move with high volume
                    social_sentiment = 0.4
                elif price_change < -0.02:  # Strong negative move with high volume
                    social_sentiment = -0.4
                else:
                    social_sentiment = 0.1  # High volume, sideways = neutral/positive
            elif volume_ratio > 1.5:
                activity_level = "MODERATE"
                social_sentiment = price_change * 2  # Moderate activity follows price
            else:
                activity_level = "LOW"
                social_sentiment = price_change * 0.5  # Low activity, weak sentiment
            
            return {
                'score': round(social_sentiment, 3),
                'social_activity': activity_level,
                'volume_ratio': round(volume_ratio, 2),
                'price_momentum': round(price_change * 100, 2)
            }
            
        except Exception as e:
            print(f"Social sentiment error: {e}")
            return {'score': 0.0, 'social_activity': 'LOW'}
    
    async def _analyze_market_structure(self, symbol: str) -> Dict:
        """Analyze overall market structure sentiment"""
        try:
            # Get broader market data (SPY as proxy)
            spy = yf.Ticker("SPY")
            spy_data = spy.history(period="5d")
            
            # Get symbol data
            ticker = yf.Ticker(symbol)
            symbol_data = ticker.history(period="5d")
            
            if spy_data.empty or symbol_data.empty:
                return {'score': 0.0, 'market_correlation': 0.0}
            
            # Calculate market sentiment based on structure
            spy_change = (spy_data['Close'].iloc[-1] - spy_data['Close'].iloc[0]) / spy_data['Close'].iloc[0]
            symbol_change = (symbol_data['Close'].iloc[-1] - symbol_data['Close'].iloc[0]) / symbol_data['Close'].iloc[0]
            
            # Market structure sentiment
            market_sentiment = 0.0
            
            if spy_change > 0.01:  # Market up > 1%
                market_sentiment = 0.2
                if symbol_change > spy_change:  # Symbol outperforming
                    market_sentiment = 0.4
            elif spy_change < -0.01:  # Market down > 1%
                market_sentiment = -0.2
                if symbol_change < spy_change:  # Symbol underperforming
                    market_sentiment = -0.4
            
            # Correlation analysis
            if len(spy_data) >= 5 and len(symbol_data) >= 5:
                spy_returns = spy_data['Close'].pct_change().dropna()
                symbol_returns = symbol_data['Close'].pct_change().dropna()
                correlation = spy_returns.corr(symbol_returns) if len(spy_returns) > 1 else 0
            else:
                correlation = 0
            
            return {
                'score': round(market_sentiment, 3),
                'market_correlation': round(correlation, 3),
                'market_performance': round(spy_change * 100, 2),
                'relative_performance': round((symbol_change - spy_change) * 100, 2)
            }
            
        except Exception as e:
            print(f"Market structure analysis error: {e}")
            return {'score': 0.0, 'market_correlation': 0.0}
    
    async def _generate_prediction(self, sentiment_data: Dict, symbol: str) -> Dict:
        """Generate AI prediction based on sentiment analysis"""
        try:
            overall_sentiment = sentiment_data['overall_sentiment']
            confidence = sentiment_data['confidence']
            
            # Get current price for prediction target
            ticker = yf.Ticker(symbol)
            current_price = ticker.history(period="1d")['Close'].iloc[-1]
            
            # Generate prediction based on sentiment strength and confidence
            if overall_sentiment > 0.2 and confidence > 0.6:
                direction = "BULLISH"
                probability = min(95, 50 + (overall_sentiment * confidence * 100))
                price_target = current_price * (1 + overall_sentiment * 0.1)
            elif overall_sentiment < -0.2 and confidence > 0.6:
                direction = "BEARISH" 
                probability = min(95, 50 + (abs(overall_sentiment) * confidence * 100))
                price_target = current_price * (1 + overall_sentiment * 0.1)
            else:
                direction = "NEUTRAL"
                probability = 50 + (confidence * 10)
                price_target = current_price
            
            timeframe = "1-3 days" if confidence > 0.7 else "3-7 days"
            
            return {
                'direction': direction,
                'probability': round(probability, 1),
                'current_price': round(current_price, 2),
                'predicted_price': round(price_target, 2),
                'price_change_percent': round(((price_target - current_price) / current_price) * 100, 2),
                'timeframe': timeframe,
                'strength': 'STRONG' if confidence > 0.7 else 'MODERATE' if confidence > 0.5 else 'WEAK'
            }
            
        except Exception as e:
            print(f"Prediction generation error: {e}")
            return {
                'direction': 'NEUTRAL',
                'probability': 50.0,
                'strength': 'WEAK'
            }
    
    def _assess_risk_level(self, sentiment_data: Dict) -> str:
        """Assess risk level based on sentiment analysis"""
        try:
            confidence = sentiment_data['confidence']
            overall_sentiment = abs(sentiment_data['overall_sentiment'])
            
            if confidence > 0.8 and overall_sentiment > 0.3:
                return "HIGH"
            elif confidence > 0.6 and overall_sentiment > 0.2:
                return "MODERATE"
            elif confidence < 0.4 or overall_sentiment < 0.1:
                return "LOW"
            else:
                return "MODERATE"
                
        except:
            return "MODERATE"
    
    def _get_neutral_sentiment(self, symbol: str) -> Dict:
        """Return neutral sentiment when analysis fails"""
        return {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'overall_sentiment': 0.0,
            'confidence': 0.5,
            'news_sentiment': 0.0,
            'technical_sentiment': 0.0,
            'social_sentiment': 0.0,
            'prediction': {
                'direction': 'NEUTRAL',
                'probability': 50.0,
                'strength': 'WEAK'
            },
            'sentiment_breakdown': {},
            'key_factors': [],
            'risk_assessment': 'MODERATE',
            'status': 'ANALYSIS_ERROR'
        }

# Global instance
ai_sentiment = AIMarketSentimentEngine()