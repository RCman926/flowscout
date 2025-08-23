import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
import asyncio
from typing import Dict, List, Optional

class EnhancedSocialTradingHub:
    """
    Enhanced social trading platform with advanced community features,
    real-time trader interactions, and comprehensive analytics
    """
    
    def __init__(self):
        self.community_data_file = "community_data.json"
        self.traders_file = "traders_data.json"
        self.trade_ideas_file = "trade_ideas.json"
        self.social_sentiment_file = "social_sentiment.json"
        self.live_signals_file = "live_signals.json"
        self.trader_profiles_file = "trader_profiles.json"
        self.ensure_files_exist()
        
        # Enhanced trader categories
        self.trader_tiers = {
            'LEGEND': {'min_accuracy': 90, 'min_signals': 500, 'badge': '🏆', 'color': '#FFD700'},
            'MASTER': {'min_accuracy': 85, 'min_signals': 300, 'badge': '⭐', 'color': '#C0C0C0'},
            'EXPERT': {'min_accuracy': 80, 'min_signals': 150, 'badge': '💎', 'color': '#CD7F32'},
            'PRO': {'min_accuracy': 75, 'min_signals': 75, 'badge': '🔥', 'color': '#059669'},
            'RISING': {'min_accuracy': 70, 'min_signals': 25, 'badge': '📈', 'color': '#3B82F6'},
        }
    
    def ensure_files_exist(self):
        """Initialize all data files with enhanced structures"""
        default_data = {
            self.community_data_file: {
                "total_members": 18247,
                "active_traders": 4821,
                "signals_today": 287,
                "verified_traders": 156,
                "institutional_members": 42
            },
            self.traders_file: [],
            self.trade_ideas_file: [],
            self.social_sentiment_file: {},
            self.live_signals_file: [],
            self.trader_profiles_file: {}
        }
        
        for file_path, default in default_data.items():
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    json.dump(default, f)
    
    async def get_real_time_community_metrics(self):
        """Get enhanced real-time community metrics"""
        try:
            with open(self.community_data_file, 'r') as f:
                community_data = json.load(f)
            
            # Enhanced metrics with real-time simulation
            current_hour = datetime.now().hour
            market_session = self._get_market_session(current_hour)
            activity_multiplier = self._get_activity_multiplier(market_session)
            
            base_members = community_data.get("total_members", 18247)
            base_active = community_data.get("active_traders", 4821)
            base_signals = community_data.get("signals_today", 287)
            verified_count = community_data.get("verified_traders", 156)
            institutional_count = community_data.get("institutional_members", 42)
            
            # Real-time variations
            return {
                "total_members": base_members + np.random.randint(-100, 200),
                "active_traders": int(base_active * activity_multiplier) + np.random.randint(-50, 100),
                "signals_today": base_signals + np.random.randint(0, 45),
                "verified_traders": verified_count + np.random.randint(-5, 15),
                "institutional_members": institutional_count + np.random.randint(-2, 8),
                "online_now": np.random.randint(1200, 2500),
                "signals_last_hour": np.random.randint(15, 55),
                "live_discussions": np.random.randint(25, 85),
                "top_accuracy_today": np.random.uniform(82, 96),
                "community_sentiment": self._calculate_dynamic_sentiment(),
                "market_session": market_session,
                "trending_alert": np.random.random() < 0.3,  # 30% chance of trending alert
                "whale_activity": np.random.random() < 0.15,  # 15% chance of whale activity
                "momentum_score": np.random.uniform(65, 95)
            }
        except:
            return self._get_enhanced_default_data()
    
    def _get_market_session(self, hour):
        """Determine current market session"""
        if 4 <= hour < 9:
            return "PRE_MARKET"
        elif 9 <= hour < 16:
            return "MARKET_HOURS"
        elif 16 <= hour < 20:
            return "AFTER_HOURS"
        else:
            return "OVERNIGHT"
    
    def _get_activity_multiplier(self, session):
        """Get activity multiplier based on market session"""
        multipliers = {
            "PRE_MARKET": 0.6,
            "MARKET_HOURS": 1.4,
            "AFTER_HOURS": 0.8,
            "OVERNIGHT": 0.3
        }
        return multipliers.get(session, 1.0)
    
    def _calculate_dynamic_sentiment(self):
        """Calculate dynamic community sentiment"""
        sentiments = ["Extremely Bullish", "Bullish", "Cautiously Optimistic", 
                     "Neutral", "Cautious", "Bearish", "Extremely Bearish"]
        weights = [0.05, 0.25, 0.20, 0.20, 0.15, 0.10, 0.05]
        return np.random.choice(sentiments, p=weights)
    
    async def get_elite_traders_leaderboard(self, category="ALL", limit=15):
        """Get enhanced traders leaderboard with categories and detailed metrics"""
        try:
            # Elite trader names with specialties
            elite_traders = [
                ("AlphaWolfTrader", "Institutional Flow Analysis", "LEGEND"),
                ("QuantumSignals_Pro", "Algorithmic Trading", "LEGEND"),
                ("OptionsViper_Elite", "High-Frequency Options", "MASTER"),
                ("FlowKing_2024", "Dark Pool Analysis", "MASTER"),
                ("TechWhisperer", "Technical Pattern Recognition", "MASTER"),
                ("VolatilityHunter", "Volatility Arbitrage", "EXPERT"),
                ("MomentumMaster_X", "Momentum Breakouts", "EXPERT"),
                ("DeepValueSeeker", "Contrarian Value Plays", "EXPERT"),
                ("SwingKing_Alpha", "Multi-Timeframe Swings", "PRO"),
                ("ScalpLord_99", "Ultra-Short Scalping", "PRO"),
                ("BreakoutSpecialist", "Breakout Confirmation", "PRO"),
                ("TrendFollower_Elite", "Trend Continuation", "RISING"),
                ("RiskManager_Pro", "Risk-Adjusted Returns", "RISING"),
                ("NewbieDestroyer", "Beginner Strategies", "RISING"),
                ("CryptoCorrelation", "Cross-Asset Analysis", "RISING")
            ]
            
            traders_list = []
            for i, (name, specialty, tier) in enumerate(elite_traders[:limit]):
                if category != "ALL" and tier != category:
                    continue
                
                tier_info = self.trader_tiers[tier]
                
                # Generate realistic performance metrics based on tier
                base_accuracy = tier_info['min_accuracy']
                accuracy = np.random.uniform(base_accuracy, min(98, base_accuracy + 8))
                
                total_signals = np.random.randint(tier_info['min_signals'], 
                                                 tier_info['min_signals'] * 3)
                
                # Advanced metrics
                sharpe_ratio = np.random.uniform(1.5, 4.5)
                max_drawdown = np.random.uniform(2, 15)
                avg_return_per_trade = np.random.uniform(0.8, 4.2)
                consistency_score = np.random.uniform(75, 95)
                
                # Recent performance
                recent_trades = np.random.randint(8, 35)
                recent_wins = int(recent_trades * (accuracy / 100))
                
                # Social metrics
                followers = np.random.randint(200, 8000)
                if tier in ['LEGEND', 'MASTER']:
                    followers = np.random.randint(2000, 15000)
                
                traders_list.append({
                    "rank": i + 1,
                    "username": name,
                    "specialty": specialty,
                    "tier": tier,
                    "tier_badge": tier_info['badge'],
                    "tier_color": tier_info['color'],
                    "accuracy": accuracy,
                    "total_signals": total_signals,
                    "sharpe_ratio": sharpe_ratio,
                    "max_drawdown": max_drawdown,
                    "avg_return_per_trade": avg_return_per_trade,
                    "consistency_score": consistency_score,
                    "recent_trades": recent_trades,
                    "recent_wins": recent_wins,
                    "followers": followers,
                    "following": np.random.randint(10, 200),
                    "profit_factor": np.random.uniform(1.8, 6.2),
                    "win_streak": np.random.randint(0, 25),
                    "last_active": np.random.choice(["Live", "2m ago", "5m ago", "15m ago", "1h ago"]),
                    "verified": np.random.random() > 0.2,  # 80% verified
                    "institutional": tier in ['LEGEND', 'MASTER'] and np.random.random() > 0.4,
                    "subscription_fee": np.random.choice([0, 49, 99, 199, 299]) if tier in ['LEGEND', 'MASTER'] else np.random.choice([0, 29, 49]),
                    "avg_holding_period": np.random.choice(["2h", "4h", "8h", "1d", "2d", "1w"]),
                    "risk_score": np.random.uniform(20, 80),
                    "social_score": np.random.uniform(60, 100)
                })
            
            return sorted(traders_list, key=lambda x: x["accuracy"], reverse=True)
            
        except Exception as e:
            return []
    
    async def get_live_signal_feed(self, limit=20):
        """Get real-time live signal feed from community"""
        try:
            signals = []
            symbols = ["SPY", "QQQ", "TSLA", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AMD", "COIN", "HOOD"]
            
            # Generate live signals with timestamps
            for i in range(limit):
                timestamp = datetime.now() - timedelta(minutes=np.random.randint(1, 180))
                symbol = np.random.choice(symbols)
                signal_type = np.random.choice(["BUY_CALL", "BUY_PUT"], p=[0.65, 0.35])
                
                # Generate trader tier for signal quality
                tier_prob = [0.05, 0.15, 0.25, 0.35, 0.20]  # Legend to Rising
                tier = np.random.choice(list(self.trader_tiers.keys()), p=tier_prob)
                tier_info = self.trader_tiers[tier]
                
                # Signal confidence based on tier
                base_confidence = np.random.uniform(70, 95)
                if tier in ['LEGEND', 'MASTER']:
                    base_confidence = np.random.uniform(85, 98)
                
                # Generate strike and expiry
                base_price = np.random.uniform(50, 600)
                strike = int(base_price * np.random.uniform(0.95, 1.05))
                days_to_expiry = np.random.choice([0, 1, 2, 7, 14, 30, 45])
                expiry = (datetime.now() + timedelta(days=days_to_expiry)).strftime('%Y-%m-%d')
                
                signals.append({
                    "id": f"signal_{i+1}",
                    "timestamp": timestamp.strftime('%H:%M:%S'),
                    "time_ago": self._format_time_ago(timestamp),
                    "trader": f"Trader_{np.random.randint(1000, 9999)}",
                    "trader_tier": tier,
                    "tier_badge": tier_info['badge'],
                    "tier_color": tier_info['color'],
                    "symbol": symbol,
                    "signal_type": signal_type,
                    "strike": strike,
                    "expiry": expiry,
                    "confidence": base_confidence,
                    "entry_price": f"${np.random.uniform(0.10, 5.00):.2f}",
                    "target_price": f"${np.random.uniform(5.01, 15.00):.2f}",
                    "stop_loss": f"${np.random.uniform(0.05, 1.50):.2f}",
                    "expected_move": np.random.uniform(2, 25),
                    "volume_alert": np.random.random() < 0.3,  # 30% have volume alerts
                    "unusual_activity": np.random.random() < 0.2,  # 20% unusual activity
                    "likes": np.random.randint(0, 45),
                    "comments": np.random.randint(0, 12),
                    "followers_count": np.random.randint(50, 2000),
                    "signal_strength": np.random.choice(["🔥 STRONG", "⚡ MODERATE", "📊 WEAK"]),
                    "market_condition": np.random.choice(["Trending", "Ranging", "Volatile", "Quiet"]),
                    "risk_level": np.random.choice(["Low", "Medium", "High"])
                })
            
            # Sort by timestamp (most recent first)
            return sorted(signals, key=lambda x: x["timestamp"], reverse=True)
            
        except Exception as e:
            return []
    
    def _format_time_ago(self, timestamp):
        """Format time difference as human readable"""
        diff = datetime.now() - timestamp
        minutes = int(diff.total_seconds() / 60)
        
        if minutes < 1:
            return "Just now"
        elif minutes < 60:
            return f"{minutes}m ago"
        elif minutes < 1440:
            hours = minutes // 60
            return f"{hours}h ago"
        else:
            days = minutes // 1440
            return f"{days}d ago"
    
    async def get_trending_discussions(self, limit=10):
        """Get trending community discussions and hot topics"""
        try:
            discussion_topics = [
                "🔥 NVDA earnings play - who's holding through?",
                "📊 SPY looks ready for breakout - technical analysis inside",
                "⚡ Unusual options activity in TSLA today",
                "💎 Hidden gem alert: Small cap with huge volume",
                "🎯 Weekly expiry plays - what's your strategy?",
                "📈 Market sentiment shifting - time to adjust positions?",
                "🚀 Crypto correlation trades - BTC vs traditional markets",
                "⚠️ VIX spike incoming? Protective puts discussion",
                "🏆 Who called the AAPL reversal? Show your analysis",
                "💰 Profit taking strategies in this market environment"
            ]
            
            discussions = []
            for i in range(limit):
                topic = np.random.choice(discussion_topics)
                
                discussions.append({
                    "id": f"discussion_{i+1}",
                    "title": topic,
                    "author": f"Trader_{np.random.randint(1000, 9999)}",
                    "author_tier": np.random.choice(list(self.trader_tiers.keys())),
                    "replies": np.random.randint(5, 150),
                    "views": np.random.randint(100, 2500),
                    "likes": np.random.randint(10, 200),
                    "last_activity": f"{np.random.randint(1, 120)}m ago",
                    "trending_score": np.random.uniform(60, 100),
                    "category": np.random.choice([
                        "Options Strategy", "Technical Analysis", "Market News", 
                        "Earnings Plays", "Unusual Activity", "Risk Management"
                    ]),
                    "is_hot": np.random.random() < 0.4,  # 40% are hot topics
                    "is_pinned": np.random.random() < 0.1,  # 10% are pinned
                    "sentiment": np.random.choice(["Bullish", "Bearish", "Neutral"]),
                    "urgency": np.random.choice(["🔥 High", "⚡ Medium", "📊 Low"])
                })
            
            return sorted(discussions, key=lambda x: x["trending_score"], reverse=True)
            
        except Exception as e:
            return []
    
    async def get_advanced_sentiment_analysis(self, symbol):
        """Get advanced multi-dimensional sentiment analysis"""
        try:
            # Base sentiment calculation
            bullish_pct = np.random.uniform(25, 65)
            bearish_pct = np.random.uniform(15, 45)
            neutral_pct = max(5, 100 - bullish_pct - bearish_pct)
            
            # Normalize if needed
            total = bullish_pct + bearish_pct + neutral_pct
            if total > 100:
                bullish_pct = (bullish_pct / total) * 100
                bearish_pct = (bearish_pct / total) * 100
                neutral_pct = (neutral_pct / total) * 100
            
            # Advanced sentiment metrics
            institutional_sentiment = np.random.uniform(30, 70)
            retail_sentiment = np.random.uniform(40, 80)
            whale_sentiment = np.random.uniform(20, 90)
            
            # Timeframe analysis
            sentiment_1h = np.random.uniform(-20, 20)
            sentiment_4h = np.random.uniform(-15, 15)
            sentiment_24h = np.random.uniform(-25, 25)
            sentiment_7d = np.random.uniform(-30, 30)
            
            # Volume-weighted sentiment
            volume_weighted_score = np.random.uniform(40, 85)
            
            # Key drivers with weights
            drivers = [
                {"driver": "Technical breakout pattern", "weight": np.random.uniform(15, 30)},
                {"driver": "Unusual options activity", "weight": np.random.uniform(10, 25)},
                {"driver": "Institutional accumulation", "weight": np.random.uniform(8, 20)},
                {"driver": "Earnings expectations", "weight": np.random.uniform(5, 15)},
                {"driver": "Sector momentum", "weight": np.random.uniform(3, 12)},
                {"driver": "Market correlation", "weight": np.random.uniform(2, 10)}
            ]
            
            # Social indicators
            mention_frequency = np.random.randint(50, 300)
            sentiment_velocity = np.random.uniform(-50, 50)  # Rate of change
            controversy_score = np.random.uniform(0, 100)
            
            return {
                "symbol": symbol,
                "overall_sentiment": {
                    "bullish_pct": bullish_pct,
                    "bearish_pct": bearish_pct,
                    "neutral_pct": neutral_pct
                },
                "segment_analysis": {
                    "institutional": institutional_sentiment,
                    "retail": retail_sentiment,
                    "whale_traders": whale_sentiment
                },
                "timeframe_analysis": {
                    "1h_change": sentiment_1h,
                    "4h_change": sentiment_4h,
                    "24h_change": sentiment_24h,
                    "7d_change": sentiment_7d
                },
                "advanced_metrics": {
                    "volume_weighted_score": volume_weighted_score,
                    "mention_frequency": mention_frequency,
                    "sentiment_velocity": sentiment_velocity,
                    "controversy_score": controversy_score,
                    "consensus_strength": 100 - controversy_score
                },
                "key_drivers": sorted(drivers, key=lambda x: x["weight"], reverse=True),
                "social_indicators": {
                    "total_mentions": mention_frequency,
                    "trending_hashtags": [f"#{symbol}calls", f"#{symbol}puts", f"#{symbol}breakout"],
                    "influencer_sentiment": np.random.choice(["Bullish", "Bearish", "Mixed"]),
                    "community_conviction": np.random.uniform(60, 95)
                },
                "ai_confidence": np.random.uniform(75, 95),
                "last_updated": datetime.now().strftime('%H:%M:%S'),
                "next_update": (datetime.now() + timedelta(minutes=5)).strftime('%H:%M:%S')
            }
            
        except Exception as e:
            return self._get_default_sentiment_analysis(symbol)
    
    async def get_copy_trading_analytics(self, limit=8):
        """Get enhanced copy trading opportunities with detailed analytics"""
        try:
            strategies = [
                "Momentum Breakouts", "Mean Reversion", "Volatility Harvesting",
                "Flow-Based Signals", "Technical Patterns", "Earnings Plays",
                "Options Spreads", "Scalping Alpha", "Swing Positioning"
            ]
            
            opportunities = []
            for i in range(limit):
                trader_name = f"Elite_{np.random.choice(['Alpha', 'Beta', 'Gamma', 'Delta', 'Sigma'])}_{np.random.randint(100, 999)}"
                strategy = np.random.choice(strategies)
                
                # Performance metrics based on strategy
                monthly_return = np.random.uniform(3, 45)
                if strategy in ["Scalping Alpha", "Flow-Based Signals"]:
                    monthly_return = np.random.uniform(8, 35)
                    
                win_rate = np.random.uniform(55, 88)
                max_drawdown = np.random.uniform(2, 18)
                sharpe_ratio = np.random.uniform(1.2, 4.8)
                
                # Advanced metrics
                calmar_ratio = monthly_return / max_drawdown if max_drawdown > 0 else 0
                profit_factor = np.random.uniform(1.5, 6.2)
                avg_winner = np.random.uniform(1.2, 4.5)
                avg_loser = np.random.uniform(0.3, 1.8)
                
                # Social metrics
                followers = np.random.randint(25, 3000)
                copiers = np.random.randint(10, int(followers * 0.3))
                
                opportunities.append({
                    "trader_id": f"trader_{i+1}",
                    "trader_name": trader_name,
                    "strategy": strategy,
                    "tier": np.random.choice(list(self.trader_tiers.keys())),
                    "performance": {
                        "monthly_return": monthly_return,
                        "yearly_return": monthly_return * 12 * np.random.uniform(0.7, 1.2),
                        "win_rate": win_rate,
                        "max_drawdown": max_drawdown,
                        "sharpe_ratio": sharpe_ratio,
                        "calmar_ratio": calmar_ratio,
                        "profit_factor": profit_factor,
                        "avg_winner": avg_winner,
                        "avg_loser": avg_loser
                    },
                    "trading_stats": {
                        "avg_trade_duration": np.random.choice(["30m", "2h", "4h", "1d", "3d", "1w"]),
                        "trades_per_week": np.random.randint(5, 50),
                        "avg_position_size": np.random.uniform(2, 15),
                        "risk_per_trade": np.random.uniform(0.5, 3.0)
                    },
                    "social_metrics": {
                        "followers": followers,
                        "active_copiers": copiers,
                        "total_copied_volume": np.random.randint(10000, 500000),
                        "community_rating": np.random.uniform(3.8, 4.9),
                        "reviews_count": np.random.randint(15, 200)
                    },
                    "subscription": {
                        "fee_monthly": np.random.choice([0, 49, 99, 199, 299, 499]),
                        "min_copy_amount": np.random.choice([100, 250, 500, 1000, 2500]),
                        "max_copiers": np.random.choice([50, 100, 250, 500, 1000]),
                        "profit_sharing": np.random.choice([0, 10, 15, 20, 25]) if np.random.random() > 0.7 else 0
                    },
                    "recent_activity": {
                        "last_trade": f"{np.random.randint(1, 360)}m ago",
                        "recent_performance_7d": np.random.uniform(-8, 25),
                        "recent_trades_count": np.random.randint(3, 25),
                        "recent_win_rate": np.random.uniform(50, 90)
                    },
                    "risk_metrics": {
                        "risk_score": np.random.uniform(20, 85),
                        "volatility": np.random.uniform(15, 45),
                        "beta": np.random.uniform(0.6, 1.8),
                        "var_95": np.random.uniform(2, 12)
                    },
                    "verification": {
                        "verified": np.random.random() > 0.3,
                        "kyc_verified": np.random.random() > 0.2,
                        "track_record_verified": np.random.random() > 0.4,
                        "institutional": np.random.random() > 0.8
                    }
                })
            
            return sorted(opportunities, key=lambda x: x["performance"]["sharpe_ratio"], reverse=True)
            
        except Exception as e:
            return []
    
    async def get_market_pulse(self):
        """Get real-time market pulse and community activity overview"""
        try:
            # Current market conditions
            vix_level = np.random.uniform(12, 35)
            market_sentiment = "High Fear" if vix_level > 25 else "Moderate Fear" if vix_level > 20 else "Low Fear"
            
            # Activity heatmap
            activity_by_hour = [np.random.randint(10, 100) for _ in range(24)]
            current_hour = datetime.now().hour
            current_activity = activity_by_hour[current_hour]
            
            # Hot sectors
            sectors = ["Technology", "Healthcare", "Finance", "Energy", "Consumer", "Industrial"]
            sector_sentiment = {sector: np.random.uniform(-20, 20) for sector in sectors}
            
            # Trending symbols with reasons
            trending_symbols = [
                {"symbol": "SPY", "reason": "Index rebalancing", "change": np.random.uniform(-3, 3)},
                {"symbol": "TSLA", "reason": "Earnings anticipation", "change": np.random.uniform(-5, 8)},
                {"symbol": "NVDA", "reason": "AI developments", "change": np.random.uniform(-4, 6)},
                {"symbol": "AAPL", "reason": "Product launch rumors", "change": np.random.uniform(-2, 4)},
                {"symbol": "QQQ", "reason": "Tech rotation", "change": np.random.uniform(-3, 5)}
            ]
            
            return {
                "market_conditions": {
                    "vix_level": vix_level,
                    "market_sentiment": market_sentiment,
                    "session_type": self._get_market_session(datetime.now().hour),
                    "volatility_regime": "High" if vix_level > 25 else "Normal",
                    "trend_direction": np.random.choice(["Bullish", "Bearish", "Sideways"])
                },
                "community_activity": {
                    "current_activity_score": current_activity,
                    "peak_activity_hour": np.argmax(activity_by_hour),
                    "activity_trend": "Increasing" if current_activity > 60 else "Decreasing",
                    "most_discussed": np.random.choice(["Options strategies", "Earnings plays", "Technical analysis"])
                },
                "sector_pulse": sector_sentiment,
                "trending_symbols": trending_symbols,
                "alerts": self._generate_market_alerts(),
                "whale_activity": {
                    "detected": np.random.random() < 0.2,
                    "symbols": ["SPY", "QQQ"] if np.random.random() < 0.2 else [],
                    "volume_spike": np.random.uniform(150, 500) if np.random.random() < 0.2 else 0
                },
                "social_sentiment_score": np.random.uniform(30, 80),
                "fear_greed_index": 100 - min(100, max(0, vix_level * 3))
            }
            
        except Exception as e:
            return {}
    
    def _generate_market_alerts(self):
        """Generate dynamic market alerts"""
        possible_alerts = [
            "🔥 Unusual options volume detected in SPY",
            "⚡ VIX spike above 25 - increased volatility expected",
            "📊 Major support level test in progress",
            "🎯 Multiple breakout setups forming",
            "⚠️ After-hours volatility increasing",
            "💎 Institutional accumulation patterns detected"
        ]
        
        num_alerts = np.random.randint(0, 4)
        return np.random.choice(possible_alerts, size=num_alerts, replace=False).tolist()
    
    def _get_enhanced_default_data(self):
        """Enhanced fallback data"""
        return {
            "total_members": 18247,
            "active_traders": 4821,
            "signals_today": 287,
            "verified_traders": 156,
            "institutional_members": 42,
            "online_now": 1654,
            "signals_last_hour": 34,
            "live_discussions": 67,
            "top_accuracy_today": 87.3,
            "community_sentiment": "Cautiously Optimistic",
            "market_session": "MARKET_HOURS",
            "trending_alert": False,
            "whale_activity": False,
            "momentum_score": 78.5
        }
    
    def _get_default_sentiment_analysis(self, symbol):
        """Default sentiment analysis fallback"""
        return {
            "symbol": symbol,
            "overall_sentiment": {"bullish_pct": 45.0, "bearish_pct": 35.0, "neutral_pct": 20.0},
            "segment_analysis": {"institutional": 55, "retail": 65, "whale_traders": 40},
            "timeframe_analysis": {"1h_change": 2.3, "4h_change": -1.2, "24h_change": 4.7, "7d_change": -2.1},
            "advanced_metrics": {"volume_weighted_score": 67.5, "sentiment_velocity": 12.3, "controversy_score": 25.8},
            "ai_confidence": 82.4,
            "last_updated": datetime.now().strftime('%H:%M:%S')
        }