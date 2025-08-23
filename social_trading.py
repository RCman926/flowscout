import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
import asyncio
from typing import Dict, List, Optional

class SocialTradingManager:
    def __init__(self):
        self.community_data_file = "community_data.json"
        self.traders_file = "traders_data.json"
        self.trade_ideas_file = "trade_ideas.json"
        self.social_sentiment_file = "social_sentiment.json"
        self.ensure_files_exist()
    
    def ensure_files_exist(self):
        """Ensure all social trading files exist"""
        default_data = {
            self.community_data_file: {"total_members": 12847, "active_traders": 3421, "signals_today": 156},
            self.traders_file: [],
            self.trade_ideas_file: [],
            self.social_sentiment_file: {}
        }
        
        for file_path, default in default_data.items():
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    json.dump(default, f)
    
    async def get_community_overview(self):
        """Get community overview statistics"""
        try:
            with open(self.community_data_file, 'r') as f:
                community_data = json.load(f)
            
            # Simulate real-time updates
            base_members = community_data.get("total_members", 12847)
            active_traders = community_data.get("active_traders", 3421)
            signals_today = community_data.get("signals_today", 156)
            
            # Add some realistic variation
            current_hour = datetime.now().hour
            activity_multiplier = 1.2 if 9 <= current_hour <= 16 else 0.8  # Market hours
            
            return {
                "total_members": base_members + np.random.randint(-50, 100),
                "active_traders": int(active_traders * activity_multiplier) + np.random.randint(-20, 50),
                "signals_today": signals_today + np.random.randint(0, 25),
                "online_now": np.random.randint(800, 1500),
                "signals_last_hour": np.random.randint(8, 35),
                "top_accuracy_today": np.random.uniform(78, 95),
                "community_sentiment": np.random.choice(["Bullish", "Bearish", "Neutral"], p=[0.4, 0.35, 0.25])
            }
        except:
            return self._get_default_community_data()
    
    def _get_default_community_data(self):
        return {
            "total_members": 12847,
            "active_traders": 3421,
            "signals_today": 156,
            "online_now": 1247,
            "signals_last_hour": 23,
            "top_accuracy_today": 84.2,
            "community_sentiment": "Bullish"
        }
    
    async def get_top_traders(self, limit=10):
        """Get top performing traders leaderboard"""
        try:
            # Generate realistic top traders data
            trader_names = [
                "QuantKing_2024", "OptionsWizard", "DeepValue_Pro", "TechAnalyst_X", "FlowMaster",
                "RiskManager_Elite", "VolumeHunter", "SwingTrader_Pro", "DayTrader_Alpha", "InstitutionalMind",
                "OptionsSniffer", "MarketMaker_99", "VolatilityExpert", "TrendFollower_X", "ArbitrageKing"
            ]
            
            top_traders = []
            for i in range(limit):
                accuracy = np.random.uniform(65, 95)
                total_signals = np.random.randint(50, 500)
                profit_factor = np.random.uniform(1.2, 4.5)
                followers = np.random.randint(100, 5000)
                
                # Recent performance trend
                recent_trades = np.random.randint(5, 25)
                recent_wins = int(recent_trades * (accuracy / 100))
                
                top_traders.append({
                    "rank": i + 1,
                    "username": trader_names[i],
                    "accuracy": accuracy,
                    "total_signals": total_signals,
                    "profit_factor": profit_factor,
                    "followers": followers,
                    "recent_trades": recent_trades,
                    "recent_wins": recent_wins,
                    "specialty": np.random.choice(["Options Flow", "Technical Analysis", "Volume Analysis", "Swing Trading", "Day Trading"]),
                    "last_active": np.random.choice(["1m ago", "5m ago", "12m ago", "25m ago", "1h ago"]),
                    "verified": np.random.random() > 0.3  # 70% are verified
                })
            
            return sorted(top_traders, key=lambda x: x["accuracy"], reverse=True)
        except:
            return []
    
    async def get_popular_trades(self, symbol=None, limit=15):
        """Get most popular/trending trades in the community"""
        symbols = ["SPY", "QQQ", "TSLA", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AMD"] if not symbol else [symbol]
        
        popular_trades = []
        for i in range(limit):
            trade_symbol = np.random.choice(symbols)
            signal_type = np.random.choice(["BUY_CALL", "BUY_PUT"], p=[0.6, 0.4])
            
            # Generate realistic strike and expiry
            base_price = np.random.uniform(50, 500)
            strike = int(base_price * np.random.uniform(0.95, 1.05))
            days_to_expiry = np.random.choice([1, 2, 7, 14, 30])
            expiry = (datetime.now() + timedelta(days=days_to_expiry)).strftime('%Y-%m-%d')
            
            popularity_score = np.random.uniform(50, 100)
            traders_count = int(popularity_score * np.random.uniform(2, 8))
            
            popular_trades.append({
                "symbol": trade_symbol,
                "signal_type": signal_type,
                "strike": strike,
                "expiry": expiry,
                "popularity_score": popularity_score,
                "traders_count": traders_count,
                "avg_confidence": np.random.uniform(70, 95),
                "expected_move": np.random.uniform(2, 12),
                "premium_range": f"${np.random.uniform(0.10, 2.50):.2f} - ${np.random.uniform(2.51, 8.00):.2f}",
                "time_posted": f"{np.random.randint(1, 120)}m ago",
                "sentiment": np.random.choice(["🔥 Hot", "📈 Trending", "⭐ Popular", "💎 Hidden Gem"]),
                "community_rating": np.random.uniform(3.2, 4.9)
            })
        
        return sorted(popular_trades, key=lambda x: x["popularity_score"], reverse=True)
    
    async def get_social_sentiment(self, symbol):
        """Get community sentiment for a specific symbol"""
        try:
            # Generate realistic sentiment distribution
            bullish_pct = np.random.uniform(25, 65)
            bearish_pct = np.random.uniform(15, 45)
            neutral_pct = 100 - bullish_pct - bearish_pct
            
            if neutral_pct < 0:
                # Adjust if percentages exceed 100
                total = bullish_pct + bearish_pct
                bullish_pct = (bullish_pct / total) * 85
                bearish_pct = (bearish_pct / total) * 85
                neutral_pct = 15
            
            # Recent sentiment change
            sentiment_change = np.random.uniform(-15, 15)
            
            # Top sentiment drivers
            drivers = [
                "Options flow activity", "Technical breakout", "Volume surge", "Institutional buying",
                "Earnings expectations", "Sector rotation", "News catalyst", "Analyst upgrades",
                "Short squeeze potential", "Support/resistance levels"
            ]
            
            return {
                "symbol": symbol,
                "bullish_pct": bullish_pct,
                "bearish_pct": bearish_pct,
                "neutral_pct": neutral_pct,
                "sentiment_change_24h": sentiment_change,
                "total_votes": np.random.randint(150, 800),
                "confidence_level": np.random.uniform(65, 90),
                "top_drivers": np.random.choice(drivers, size=3, replace=False).tolist(),
                "last_updated": datetime.now().strftime('%H:%M'),
                "trending": abs(sentiment_change) > 10
            }
        except:
            return self._get_default_sentiment(symbol)
    
    def _get_default_sentiment(self, symbol):
        return {
            "symbol": symbol,
            "bullish_pct": 45.0,
            "bearish_pct": 35.0,
            "neutral_pct": 20.0,
            "sentiment_change_24h": 2.3,
            "total_votes": 342,
            "confidence_level": 72.5,
            "top_drivers": ["Options flow activity", "Technical breakout", "Volume surge"],
            "last_updated": datetime.now().strftime('%H:%M'),
            "trending": False
        }
    
    async def get_trade_ideas(self, limit=8):
        """Get community trade ideas and setups"""
        trade_ideas = []
        
        symbols = ["SPY", "QQQ", "TSLA", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AMD"]
        setups = [
            "Bullish breakout", "Bear flag setup", "Cup and handle", "Head and shoulders",
            "Support bounce", "Resistance test", "Trend continuation", "Reversal play",
            "Volatility crush", "Earnings play", "Technical squeeze", "Flow-based entry"
        ]
        
        for i in range(limit):
            symbol = np.random.choice(symbols)
            setup = np.random.choice(setups)
            author = f"Trader_{np.random.randint(1000, 9999)}"
            
            # Generate realistic trade idea
            signal_type = np.random.choice(["CALL", "PUT"], p=[0.65, 0.35])
            timeframe = np.random.choice(["Intraday", "1-3 days", "1 week", "2 weeks", "1 month"])
            confidence = np.random.uniform(65, 95)
            
            trade_ideas.append({
                "id": f"idea_{i+1}",
                "symbol": symbol,
                "setup_type": setup,
                "signal_type": signal_type,
                "timeframe": timeframe,
                "confidence": confidence,
                "author": author,
                "author_rating": np.random.uniform(3.5, 4.9),
                "likes": np.random.randint(5, 150),
                "comments": np.random.randint(2, 45),
                "views": np.random.randint(50, 500),
                "entry_price": f"${np.random.uniform(0.15, 3.50):.2f}",
                "target_price": f"${np.random.uniform(3.51, 8.00):.2f}",
                "stop_loss": f"${np.random.uniform(0.05, 1.00):.2f}",
                "risk_reward": np.random.uniform(2.0, 5.0),
                "posted_time": f"{np.random.randint(1, 180)}m ago",
                "status": np.random.choice(["Active", "Triggered", "Watching"], p=[0.7, 0.2, 0.1]),
                "tags": np.random.choice([
                    ["#breakout", "#momentum"], ["#reversal", "#oversold"], ["#earnings", "#volatility"],
                    ["#flow", "#unusual"], ["#technical", "#support"], ["#resistance", "#breakdown"]
                ])
            })
        
        return sorted(trade_ideas, key=lambda x: x["confidence"], reverse=True)
    
    async def get_community_stats(self):
        """Get comprehensive community statistics"""
        try:
            # Performance metrics
            today_signals = np.random.randint(150, 250)
            avg_accuracy = np.random.uniform(68, 82)
            total_profit = np.random.uniform(15000, 85000)
            
            # Activity metrics
            active_discussions = np.random.randint(25, 60)
            new_ideas_today = np.random.randint(15, 40)
            trending_symbols = ["SPY", "TSLA", "NVDA", "AAPL", "QQQ"]
            
            return {
                "signals_today": today_signals,
                "avg_accuracy": avg_accuracy,
                "total_community_profit": total_profit,
                "active_discussions": active_discussions,
                "new_ideas_today": new_ideas_today,
                "trending_symbols": trending_symbols,
                "top_performer_accuracy": np.random.uniform(85, 96),
                "community_mood": np.random.choice(["Optimistic", "Cautious", "Aggressive", "Conservative"]),
                "market_consensus": np.random.choice(["Bullish", "Bearish", "Mixed", "Neutral"]),
                "volatility_sentiment": np.random.choice(["High", "Medium", "Low"])
            }
        except:
            return {
                "signals_today": 187,
                "avg_accuracy": 74.2,
                "total_community_profit": 42750,
                "active_discussions": 34,
                "new_ideas_today": 23,
                "trending_symbols": ["SPY", "TSLA", "NVDA", "AAPL", "QQQ"],
                "top_performer_accuracy": 89.3,
                "community_mood": "Optimistic",
                "market_consensus": "Bullish",
                "volatility_sentiment": "Medium"
            }
    
    async def get_copytrading_opportunities(self, limit=5):
        """Get top copy trading opportunities"""
        opportunities = []
        
        for i in range(limit):
            trader_name = f"ProTrader_{np.random.randint(100, 999)}"
            strategy = np.random.choice([
                "Options Scalping", "Swing Trading", "Momentum Plays", "Contrarian Bets",
                "Technical Breakouts", "Volume Analysis", "Earnings Plays"
            ])
            
            opportunities.append({
                "trader_id": f"trader_{i+1}",
                "trader_name": trader_name,
                "strategy": strategy,
                "monthly_return": np.random.uniform(5, 35),
                "win_rate": np.random.uniform(60, 85),
                "max_drawdown": np.random.uniform(3, 15),
                "avg_trade_duration": np.random.choice(["2h", "4h", "1d", "2d", "1w"]),
                "followers": np.random.randint(50, 1000),
                "min_copy_amount": np.random.choice([100, 250, 500, 1000]),
                "risk_level": np.random.choice(["Low", "Medium", "High"]),
                "recent_performance": np.random.uniform(-5, 15),
                "verified": np.random.random() > 0.4,
                "subscription_fee": np.random.choice([0, 29, 49, 99]),  # 0 means free
                "last_signal": f"{np.random.randint(1, 180)}m ago"
            })
        
        return sorted(opportunities, key=lambda x: x["monthly_return"], reverse=True)
    
    def add_community_signal(self, symbol, signal_type, confidence, user_id="anonymous"):
        """Add a signal from community member"""
        try:
            signal_data = {
                "symbol": symbol,
                "signal_type": signal_type,
                "confidence": confidence,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "likes": 0,
                "status": "active"
            }
            
            # This would be saved to a community signals database
            # For now, just return success
            return True
        except:
            return False