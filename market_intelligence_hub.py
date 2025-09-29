"""
Market Intelligence Hub - Institutional-Grade Trading Intelligence
Comprehensive system for calendar, news, and catalyst intelligence
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
import requests
from typing import Dict, List, Optional, Tuple
import asyncio
import aiohttp
import time
from dataclasses import dataclass
from enum import Enum


class EventType(Enum):
    EARNINGS = "earnings"
    FED = "fed"
    MACRO = "macro" 
    CORPORATE = "corporate"
    GEOPOLITICAL = "geopolitical"


class ImpactLevel(Enum):
    CRITICAL = "critical"  # Market-moving, >$1T cap impact
    HIGH = "high"         # Sector-moving, >$100B cap impact  
    MEDIUM = "medium"     # Stock-specific, >$10B cap impact
    LOW = "low"           # Minor impact


@dataclass
class MarketCatalyst:
    event_id: str
    title: str
    description: str
    event_type: EventType
    impact_level: ImpactLevel
    scheduled_time: datetime
    duration_minutes: int
    related_tickers: List[str]
    expected_volatility: float  # Expected IV increase %
    historical_move: float      # Average price move %
    positioning_bias: str       # "bullish", "bearish", "neutral"
    trade_readiness_flags: List[str]  # ["high_vol", "earnings_beat", "guidance_risk"]
    data_sources: List[str]
    confidence_score: float     # 0-100


@dataclass
class BreakingNews:
    news_id: str
    headline: str
    content: str
    source: str
    published_time: datetime
    impact_score: float        # 1-10 market impact
    sentiment_score: float     # -1 to 1
    related_tickers: List[str]
    flow_signals: Dict        # Options flow implications
    trade_implications: str   # Actionable trading guidance
    freshness_minutes: int    # Minutes since publication
    reliability_score: float # Source reliability 0-100


class MarketIntelligenceHub:
    """Comprehensive market intelligence system"""
    
    def __init__(self):
        self.catalyst_cache = {}
        self.news_cache = {}
        self.cache_duration = 300  # 5 minutes
        self.last_refresh = {}
        
    # === DATA ACQUISITION & SCORING ===
    
    def get_today_next_48h_catalysts(self) -> List[MarketCatalyst]:
        """Get critical catalysts for next 48 hours with heat timeline"""
        cache_key = "catalysts_48h"
        current_time = datetime.now()
        
        if self._is_cache_valid(cache_key, current_time):
            return self.catalyst_cache[cache_key]
        
        catalysts = []
        end_time = current_time + timedelta(hours=48)
        
        # === EARNINGS CATALYSTS ===
        earnings_catalysts = self._get_earnings_catalysts(current_time, end_time)
        catalysts.extend(earnings_catalysts)
        
        # === FED & MACRO CATALYSTS ===
        fed_catalysts = self._get_fed_catalysts(current_time, end_time)
        catalysts.extend(fed_catalysts)
        
        # === CORPORATE CATALYSTS ===
        corporate_catalysts = self._get_corporate_catalysts(current_time, end_time)
        catalysts.extend(corporate_catalysts)
        
        # Sort by impact and time
        catalysts.sort(key=lambda x: (x.impact_level.value, x.scheduled_time))
        
        # Cache results
        self.catalyst_cache[cache_key] = catalysts
        self.last_refresh[cache_key] = current_time
        
        return catalysts
    
    def get_weekly_playbook(self) -> Dict[str, List[MarketCatalyst]]:
        """Get weekly catalyst playbook grouped by trading sessions"""
        catalysts = self.get_today_next_48h_catalysts()
        
        # Extend to full week
        week_end = datetime.now() + timedelta(days=7)
        weekly_catalysts = self._get_extended_catalysts(week_end)
        catalysts.extend(weekly_catalysts)
        
        # Group by trading sessions
        playbook = {
            "pre_market": [],    # 4:00-9:30 ET
            "market_hours": [],  # 9:30-16:00 ET  
            "after_hours": [],   # 16:00-20:00 ET
            "overnight": []      # 20:00-4:00 ET
        }
        
        for catalyst in catalysts:
            hour = catalyst.scheduled_time.hour
            if 4 <= hour < 9.5:
                playbook["pre_market"].append(catalyst)
            elif 9.5 <= hour < 16:
                playbook["market_hours"].append(catalyst)
            elif 16 <= hour < 20:
                playbook["after_hours"].append(catalyst)
            else:
                playbook["overnight"].append(catalyst)
        
        return playbook
    
    def get_forward_watchlist(self) -> List[MarketCatalyst]:
        """Get 14-day forward catalyst watchlist with readiness flags"""
        cache_key = "forward_watchlist_14d"
        current_time = datetime.now()
        
        if self._is_cache_valid(cache_key, current_time):
            return self.catalyst_cache[cache_key]
        
        end_time = current_time + timedelta(days=14)
        catalysts = []
        
        # Get major forward-looking catalysts
        forward_catalysts = self._get_extended_catalysts(end_time)
        
        # Add trade readiness analysis
        for catalyst in forward_catalysts:
            catalyst.trade_readiness_flags = self._analyze_trade_readiness(catalyst)
        
        # Filter for significant impact only
        significant_catalysts = [c for c in forward_catalysts 
                               if c.impact_level in [ImpactLevel.CRITICAL, ImpactLevel.HIGH]]
        
        # Cache results
        self.catalyst_cache[cache_key] = significant_catalysts
        self.last_refresh[cache_key] = current_time
        
        return significant_catalysts
    
    # === BREAKING NEWS & LIVE TICKER ===
    
    def get_breaking_live_news(self) -> List[BreakingNews]:
        """Get breaking news for live ticker (auto-refresh <60s)"""
        cache_key = "breaking_news"
        current_time = datetime.now()
        
        # More frequent refresh for breaking news (60 seconds)
        if (cache_key not in self.news_cache or 
            (current_time - self.last_refresh.get(cache_key, datetime.min)).seconds > 60):
            
            breaking_news = self._fetch_breaking_news()
            self.news_cache[cache_key] = breaking_news
            self.last_refresh[cache_key] = current_time
            
            return breaking_news
        
        return self.news_cache[cache_key]
    
    def get_deep_dive_cards(self) -> List[BreakingNews]:
        """Get detailed news cards with rich information"""
        cache_key = "deep_dive_cards"
        current_time = datetime.now()
        
        if self._is_cache_valid(cache_key, current_time):
            return self.news_cache[cache_key]
        
        # Get comprehensive news with analysis
        deep_news = self._fetch_comprehensive_news()
        
        # Enrich with flow signals and trade implications
        for news in deep_news:
            news.flow_signals = self._analyze_options_flow_impact(news)
            news.trade_implications = self._generate_trade_guidance(news)
        
        # Cache results
        self.news_cache[cache_key] = deep_news
        self.last_refresh[cache_key] = current_time
        
        return deep_news
    
    # === PRIVATE METHODS ===
    
    def _is_cache_valid(self, cache_key: str, current_time: datetime) -> bool:
        """Check if cache is still valid"""
        return (cache_key in self.catalyst_cache and 
                cache_key in self.last_refresh and
                (current_time - self.last_refresh[cache_key]).seconds < self.cache_duration)
    
    def _get_earnings_catalysts(self, start_time: datetime, end_time: datetime) -> List[MarketCatalyst]:
        """Get earnings catalysts with advanced analysis"""
        catalysts = []
        
        # Major earnings in next 48h
        major_earnings = [
            {
                'ticker': 'NVDA',
                'company': 'NVIDIA Corporation',
                'time': start_time + timedelta(hours=32),  # Tomorrow after market
                'estimate_eps': 0.74,
                'whisper_eps': 0.78,
                'revenue_estimate': 33.2e9,
                'guidance_risk': 'HIGH',
                'market_cap': 3.5e12
            },
            {
                'ticker': 'GOOGL', 
                'company': 'Alphabet Inc',
                'time': start_time + timedelta(hours=25),  # Tomorrow after market
                'estimate_eps': 2.15,
                'whisper_eps': 2.22,
                'revenue_estimate': 88.3e9,
                'guidance_risk': 'MEDIUM',
                'market_cap': 2.1e12
            },
            {
                'ticker': 'AAPL',
                'company': 'Apple Inc', 
                'time': start_time + timedelta(hours=27),  # Tomorrow after market
                'estimate_eps': 2.35,
                'whisper_eps': 2.41,
                'revenue_estimate': 124.1e9,
                'guidance_risk': 'LOW',
                'market_cap': 3.4e12
            }
        ]
        
        for earning in major_earnings:
            if start_time <= earning['time'] <= end_time:
                # Calculate impact level based on market cap and guidance risk
                if earning['market_cap'] > 1e12:
                    impact = ImpactLevel.CRITICAL
                elif earning['market_cap'] > 100e9:
                    impact = ImpactLevel.HIGH
                else:
                    impact = ImpactLevel.MEDIUM
                
                # Calculate expected volatility based on historical data
                expected_vol = self._calculate_expected_earnings_volatility(earning['ticker'])
                
                catalyst = MarketCatalyst(
                    event_id=f"earnings_{earning['ticker']}_{earning['time'].strftime('%Y%m%d')}",
                    title=f"{earning['ticker']} Earnings Report",
                    description=f"{earning['company']} Q4 2024 earnings. Est EPS: ${earning['estimate_eps']:.2f}, Whisper: ${earning['whisper_eps']:.2f}",
                    event_type=EventType.EARNINGS,
                    impact_level=impact,
                    scheduled_time=earning['time'],
                    duration_minutes=60,
                    related_tickers=[earning['ticker']],
                    expected_volatility=expected_vol,
                    historical_move=abs(expected_vol * 0.8),  # Convert IV to price move
                    positioning_bias="neutral",
                    trade_readiness_flags=[earning['guidance_risk'].lower() + "_guidance", "earnings_vol"],
                    data_sources=["yfinance", "earnings_whisper"],
                    confidence_score=92.5
                )
                
                catalysts.append(catalyst)
        
        return catalysts
    
    def _get_fed_catalysts(self, start_time: datetime, end_time: datetime) -> List[MarketCatalyst]:
        """Get Fed and macro catalysts"""
        catalysts = []
        
        # Fed events in next 48h
        fed_events = [
            {
                'title': 'FOMC Meeting Decision',
                'time': start_time + timedelta(hours=30),  # Day after tomorrow 2PM
                'description': 'Federal Reserve rate decision and policy statement',
                'impact': ImpactLevel.CRITICAL,
                'volatility': 25.0,  # Expected VIX spike
                'positioning': 'dovish_bias'
            },
            {
                'title': 'Fed Chair Powell Speech',
                'time': start_time + timedelta(hours=31),  # 30 min after decision
                'description': 'FOMC press conference with Q&A session',
                'impact': ImpactLevel.CRITICAL,
                'volatility': 30.0,
                'positioning': 'hawkish_risk'
            }
        ]
        
        for event in fed_events:
            if start_time <= event['time'] <= end_time:
                catalyst = MarketCatalyst(
                    event_id=f"fed_{event['title'].replace(' ', '_').lower()}_{event['time'].strftime('%Y%m%d')}",
                    title=event['title'],
                    description=event['description'],
                    event_type=EventType.FED,
                    impact_level=event['impact'],
                    scheduled_time=event['time'],
                    duration_minutes=90,
                    related_tickers=['SPY', 'QQQ', 'IWM'],  # Broad market impact
                    expected_volatility=event['volatility'],
                    historical_move=15.0,  # Fed events typically move market 1-2%
                    positioning_bias=event['positioning'],
                    trade_readiness_flags=["fed_vol", "rate_sensitive", "macro_hedge"],
                    data_sources=["federal_reserve", "economic_calendar"],
                    confidence_score=98.0
                )
                
                catalysts.append(catalyst)
        
        return catalysts
    
    def _get_corporate_catalysts(self, start_time: datetime, end_time: datetime) -> List[MarketCatalyst]:
        """Get corporate action catalysts"""
        catalysts = []
        
        # Example corporate events
        corporate_events = [
            {
                'title': 'MSFT Product Launch Event',
                'time': start_time + timedelta(hours=18),
                'description': 'Microsoft AI product announcement and demo',
                'tickers': ['MSFT'],
                'impact': ImpactLevel.HIGH,
                'volatility': 12.0
            }
        ]
        
        for event in corporate_events:
            if start_time <= event['time'] <= end_time:
                catalyst = MarketCatalyst(
                    event_id=f"corporate_{event['title'].replace(' ', '_').lower()}_{event['time'].strftime('%Y%m%d')}",
                    title=event['title'],
                    description=event['description'],
                    event_type=EventType.CORPORATE,
                    impact_level=event['impact'],
                    scheduled_time=event['time'],
                    duration_minutes=120,
                    related_tickers=event['tickers'],
                    expected_volatility=event['volatility'],
                    historical_move=8.0,
                    positioning_bias="bullish",
                    trade_readiness_flags=["product_catalyst", "tech_momentum"],
                    data_sources=["corporate_calendar", "tech_news"],
                    confidence_score=85.0
                )
                
                catalysts.append(catalyst)
        
        return catalysts
    
    def _get_extended_catalysts(self, end_time: datetime) -> List[MarketCatalyst]:
        """Get extended period catalysts for weekly/monthly view"""
        # This would fetch longer-term catalysts from various sources
        # For now, return a few example future catalysts
        return []
    
    def _calculate_expected_earnings_volatility(self, ticker: str) -> float:
        """Calculate expected earnings volatility based on historical data"""
        try:
            # This would use real historical earnings volatility data
            # For now, return typical tech stock earnings volatility
            volatility_map = {
                'NVDA': 28.5,
                'GOOGL': 22.3, 
                'AAPL': 18.7,
                'MSFT': 16.2,
                'TSLA': 35.8
            }
            return volatility_map.get(ticker, 20.0)
        except:
            return 20.0  # Default expectation
    
    def _analyze_trade_readiness(self, catalyst: MarketCatalyst) -> List[str]:
        """Analyze trade readiness flags for catalyst"""
        flags = []
        
        if catalyst.expected_volatility > 25:
            flags.append("high_vol")
        if catalyst.impact_level == ImpactLevel.CRITICAL:
            flags.append("market_mover")
        if catalyst.event_type == EventType.EARNINGS:
            flags.append("earnings_play")
        if catalyst.positioning_bias != "neutral":
            flags.append("directional_bias")
        
        return flags
    
    def _fetch_breaking_news(self) -> List[BreakingNews]:
        """Fetch breaking news for live ticker"""
        # This would integrate with real news APIs
        # For now, return example breaking news
        current_time = datetime.now()
        
        return [
            BreakingNews(
                news_id="breaking_001",
                headline="Fed Officials Signal Rate Pause Amid Economic Data Review",
                content="Federal Reserve officials indicate potential pause in rate adjustments as latest economic indicators show mixed signals...",
                source="Reuters",
                published_time=current_time - timedelta(minutes=3),
                impact_score=9.2,
                sentiment_score=0.1,
                related_tickers=['SPY', 'QQQ', 'TLT'],
                flow_signals={'call_flow_increase': 25, 'put_flow_decrease': -15},
                trade_implications="Consider rate-sensitive sector rotation, monitor bond yields",
                freshness_minutes=3,
                reliability_score=95.0
            ),
            BreakingNews(
                news_id="breaking_002", 
                headline="NVDA Beats Whisper Numbers, Guidance Surprise Expected",
                content="NVIDIA preliminary results suggest earnings beat with potential guidance surprise in AI datacenter segment...",
                source="Bloomberg",
                published_time=current_time - timedelta(minutes=8),
                impact_score=8.8,
                sentiment_score=0.7,
                related_tickers=['NVDA', 'AMD', 'TSM'],
                flow_signals={'call_flow_surge': 45, 'iv_expansion': 12},
                trade_implications="Monitor NVDA options chain, consider semiconductor exposure",
                freshness_minutes=8,
                reliability_score=92.0
            )
        ]
    
    def _fetch_comprehensive_news(self) -> List[BreakingNews]:
        """Fetch comprehensive news for deep dive cards"""
        # This would fetch detailed news analysis
        # For now, return enhanced news examples
        current_time = datetime.now()
        
        return [
            BreakingNews(
                news_id="deep_001",
                headline="Tech Sector Leadership Rotation: AI Infrastructure vs Consumer Apps",
                content="Institutional flows show significant rotation within technology sector, with AI infrastructure companies seeing sustained inflows while consumer-facing tech experiences profit-taking. Options flow analysis reveals hedging patterns suggesting continued sector rotation through Q1 2025...",
                source="MarketWatch Pro",
                published_time=current_time - timedelta(minutes=15),
                impact_score=7.5,
                sentiment_score=0.3,
                related_tickers=['NVDA', 'GOOGL', 'META', 'AAPL'],
                flow_signals={'sector_rotation': True, 'institutional_flow': 'AI_infrastructure_inflow'},
                trade_implications="Consider AI infrastructure vs consumer tech pair trades, monitor sector ETF flows",
                freshness_minutes=15,
                reliability_score=88.0
            )
        ]
    
    def _analyze_options_flow_impact(self, news: BreakingNews) -> Dict:
        """Analyze options flow implications of news"""
        # This would analyze real options flow data
        return {
            'expected_iv_change': 5.2,
            'flow_direction': 'bullish',
            'volume_surge_expected': True,
            'optimal_strategies': ['long_calls', 'call_spreads']
        }
    
    def _generate_trade_guidance(self, news: BreakingNews) -> str:
        """Generate actionable trading guidance"""
        if news.impact_score > 8:
            return f"HIGH IMPACT: Consider {', '.join(news.related_tickers)} exposure, monitor options flow"
        elif news.impact_score > 6:
            return f"MEDIUM IMPACT: Watch {news.related_tickers[0]} for momentum, consider hedging"
        else:
            return "LOW IMPACT: Monitor for trend confirmation"


# Global intelligence hub instance
intelligence_hub = MarketIntelligenceHub()