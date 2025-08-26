import asyncio
import aiohttp
import yfinance as yf
from datetime import datetime, timedelta
import re
import warnings
warnings.filterwarnings('ignore')

class RealNewsEngine:
    """
    Real financial news engine using actual news sources
    Fetches earnings, market news, and analyst reports
    """
    
    def __init__(self):
        self.news_cache = {}
        self.cache_duration = 600  # 10 minutes
        
    async def get_real_market_news(self, symbol):
        """Get real financial news for a symbol"""
        try:
            # Check cache first
            cache_key = f"news_{symbol}"
            if self._is_cache_valid(cache_key):
                return self.news_cache[cache_key]
            
            ticker = yf.Ticker(symbol)
            
            # Get real news from Yahoo Finance
            news_items = []
            try:
                news = ticker.news
                for article in news[:10]:  # Get top 10 news items
                    news_items.append({
                        'title': article.get('title', 'No Title'),
                        'publisher': article.get('publisher', 'Unknown'),
                        'link': article.get('link', ''),
                        'publish_time': datetime.fromtimestamp(article.get('providerPublishTime', 0)),
                        'type': self._classify_news_type(article.get('title', '')),
                        'summary': article.get('summary', '')[:200] + '...' if article.get('summary', '') else ''
                    })
            except Exception as e:
                print(f"Error fetching news for {symbol}: {e}")
                
            # Get earnings calendar
            earnings_info = await self._get_earnings_info(symbol)
            
            # Get analyst ratings
            analyst_info = await self._get_analyst_ratings(symbol)
            
            result = {
                'symbol': symbol,
                'news_items': news_items,
                'earnings_info': earnings_info,
                'analyst_info': analyst_info,
                'last_updated': datetime.now()
            }
            
            # Cache result
            self.news_cache[cache_key] = result
            return result
            
        except Exception as e:
            print(f"Real news error for {symbol}: {e}")
            return {
                'symbol': symbol,
                'news_items': [],
                'earnings_info': {},
                'analyst_info': {},
                'last_updated': datetime.now()
            }
    
    async def _get_earnings_info(self, symbol):
        """Get real earnings information"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Get earnings calendar
            calendar = ticker.calendar
            earnings_data = {}
            
            if calendar is not None and not calendar.empty:
                earnings_data = {
                    'next_earnings_date': calendar.index[0].strftime('%Y-%m-%d') if len(calendar) > 0 else None,
                    'eps_estimate': float(calendar.iloc[0]['EPS Estimate']) if 'EPS Estimate' in calendar.columns and len(calendar) > 0 else None,
                    'revenue_estimate': float(calendar.iloc[0]['Revenue Estimate']) if 'Revenue Estimate' in calendar.columns and len(calendar) > 0 else None
                }
            
            # Get recent earnings
            earnings_history = ticker.quarterly_earnings
            if earnings_history is not None and not earnings_history.empty:
                latest_earnings = earnings_history.iloc[0]
                earnings_data.update({
                    'latest_earnings': latest_earnings['Earnings'].item() if 'Earnings' in latest_earnings else None,
                    'latest_revenue': latest_earnings['Revenue'].item() if 'Revenue' in latest_earnings else None,
                    'earnings_growth': self._calculate_earnings_growth(earnings_history)
                })
            
            return earnings_data
            
        except Exception as e:
            print(f"Earnings info error for {symbol}: {e}")
            return {}
    
    async def _get_analyst_ratings(self, symbol):
        """Get real analyst ratings and recommendations"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Get recommendations
            recommendations = ticker.recommendations
            analyst_data = {}
            
            if recommendations is not None and not recommendations.empty:
                latest_rec = recommendations.iloc[-1]
                analyst_data = {
                    'strong_buy': int(latest_rec.get('strongBuy', 0)),
                    'buy': int(latest_rec.get('buy', 0)),
                    'hold': int(latest_rec.get('hold', 0)),
                    'sell': int(latest_rec.get('sell', 0)),
                    'strong_sell': int(latest_rec.get('strongSell', 0)),
                    'recommendation_trend': self._get_recommendation_trend(latest_rec)
                }
            
            # Get analyst price targets
            try:
                info = ticker.info
                analyst_data.update({
                    'target_high_price': info.get('targetHighPrice'),
                    'target_low_price': info.get('targetLowPrice'),
                    'target_mean_price': info.get('targetMeanPrice'),
                    'current_price': info.get('currentPrice', info.get('regularMarketPrice'))
                })
                
                # Calculate potential upside
                if analyst_data.get('target_mean_price') and analyst_data.get('current_price'):
                    upside = ((analyst_data['target_mean_price'] - analyst_data['current_price']) / analyst_data['current_price']) * 100
                    analyst_data['upside_potential'] = round(upside, 1)
                    
            except Exception:
                pass
            
            return analyst_data
            
        except Exception as e:
            print(f"Analyst ratings error for {symbol}: {e}")
            return {}
    
    def _classify_news_type(self, title):
        """Classify news type based on title"""
        title_lower = title.lower()
        
        if any(word in title_lower for word in ['earnings', 'quarter', 'q1', 'q2', 'q3', 'q4', 'revenue']):
            return 'earnings'
        elif any(word in title_lower for word in ['upgrade', 'downgrade', 'rating', 'analyst', 'target']):
            return 'analyst'
        elif any(word in title_lower for word in ['merger', 'acquisition', 'deal', 'buyout']):
            return 'ma'
        elif any(word in title_lower for word in ['fda', 'approval', 'regulatory', 'lawsuit']):
            return 'regulatory'
        elif any(word in title_lower for word in ['ceo', 'management', 'executive', 'resignation', 'appointment']):
            return 'management'
        else:
            return 'general'
    
    def _calculate_earnings_growth(self, earnings_history):
        """Calculate earnings growth rate"""
        try:
            if len(earnings_history) >= 2:
                current = earnings_history.iloc[0]['Earnings']
                previous = earnings_history.iloc[1]['Earnings']
                if previous != 0:
                    growth = ((current - previous) / abs(previous)) * 100
                    return round(growth, 1)
            return None
        except Exception:
            return None
    
    def _get_recommendation_trend(self, recommendation):
        """Determine if recommendations are getting more positive or negative"""
        try:
            strong_buy = recommendation.get('strongBuy', 0)
            buy = recommendation.get('buy', 0)
            hold = recommendation.get('hold', 0)
            sell = recommendation.get('sell', 0)
            strong_sell = recommendation.get('strongSell', 0)
            
            positive = strong_buy + buy
            negative = sell + strong_sell
            
            if positive > negative * 2:
                return 'very_bullish'
            elif positive > negative:
                return 'bullish'
            elif negative > positive * 2:
                return 'very_bearish'
            elif negative > positive:
                return 'bearish'
            else:
                return 'neutral'
                
        except Exception:
            return 'neutral'
    
    def _is_cache_valid(self, cache_key):
        """Check if cached data is still valid"""
        if cache_key not in self.news_cache:
            return False
        
        cache_time = self.news_cache[cache_key]['last_updated']
        time_diff = (datetime.now() - cache_time).total_seconds()
        return time_diff < self.cache_duration

    async def get_market_overview_news(self, symbols):
        """Get market overview with real news for multiple symbols"""
        try:
            market_news = {}
            
            for symbol in symbols[:5]:  # Limit for performance
                news_data = await self.get_real_market_news(symbol)
                
                # Summarize key info for each symbol
                market_news[symbol] = {
                    'latest_news_count': len(news_data['news_items']),
                    'has_earnings_soon': bool(news_data['earnings_info'].get('next_earnings_date')),
                    'analyst_trend': news_data['analyst_info'].get('recommendation_trend', 'neutral'),
                    'upside_potential': news_data['analyst_info'].get('upside_potential', 0)
                }
            
            return market_news
            
        except Exception as e:
            print(f"Market overview error: {e}")
            return {}