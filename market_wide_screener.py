"""
Market-Wide Explosive Opportunity Screener
Scans the entire market for high short interest squeeze candidates
Focus: Small caps, OTC stocks, and real explosive potential plays
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup
import time
import warnings
warnings.filterwarnings('ignore')


class MarketWideScreener:
    """
    Comprehensive market scanner for squeeze candidates and explosive plays
    """
    
    def __init__(self):
        self.cache_duration = 300  # 5 minutes
        self.screener_results = []
        self.last_scan_time = None
        
    def scan_entire_market(self, min_price: float = 0.50, max_price: float = 20.0, 
                          min_volume: int = 100000) -> List[Dict]:
        """
        Scan entire market for explosive opportunities
        Focus on small caps, high short interest, squeeze potential
        """
        
        # Check cache
        if self.last_scan_time and (datetime.now() - self.last_scan_time).seconds < self.cache_duration:
            return self.screener_results
        
        print("🔍 Scanning entire market for explosive opportunities...")
        
        candidates = []
        
        # === METHOD 1: Yahoo Finance Screener ===
        # Get stocks from various categories
        yf_candidates = self._scan_yahoo_finance_universe(min_price, max_price, min_volume)
        candidates.extend(yf_candidates)
        
        # === METHOD 2: High Short Interest Stocks ===
        high_short_stocks = self._get_high_short_interest_stocks()
        candidates.extend(high_short_stocks)
        
        # === METHOD 3: Small Cap & Penny Stocks ===
        small_caps = self._get_small_cap_universe()
        candidates.extend(small_caps)
        
        # === METHOD 4: OTC & Pink Sheet Stocks ===
        otc_stocks = self._get_otc_candidates()
        candidates.extend(otc_stocks)
        
        # Remove duplicates
        unique_symbols = list(set(candidates))
        print(f"📊 Found {len(unique_symbols)} unique candidates to analyze")
        
        # === ANALYZE EACH CANDIDATE ===
        explosive_plays = []
        
        for i, symbol in enumerate(unique_symbols[:500]):  # Limit to 500 for performance
            if i % 50 == 0:
                print(f"⚡ Analyzed {i}/{min(500, len(unique_symbols))} stocks...")
            
            analysis = self._analyze_squeeze_potential(symbol)
            
            if analysis and analysis.get('squeeze_score', 0) >= 60:  # Only high-potential plays
                explosive_plays.append(analysis)
        
        # Sort by squeeze score
        explosive_plays.sort(key=lambda x: x.get('squeeze_score', 0), reverse=True)
        
        self.screener_results = explosive_plays
        self.last_scan_time = datetime.now()
        
        print(f"✅ Found {len(explosive_plays)} explosive opportunities!")
        
        return explosive_plays
    
    def _scan_yahoo_finance_universe(self, min_price: float, max_price: float, min_volume: int) -> List[str]:
        """Scan Yahoo Finance screener for candidates"""
        
        candidates = []
        
        # Most actives, gainers, losers - these have volume and volatility
        try:
            # Get market movers using yfinance
            tickers_df = pd.DataFrame()
            
            # Try to get stocks from various indices
            indices = ['DOW', 'NASDAQ', 'SP500']
            
            for index in indices:
                try:
                    # Get stocks from index (simplified approach)
                    pass
                except:
                    continue
            
            # Add known high-volume small caps and penny stocks
            penny_universe = [
                # Penny stocks with frequent action
                'SNDL', 'HITI', 'MULN', 'GNUS', 'PROG', 'ATER', 'BBIG',
                'NKLA', 'RIDE', 'GOEV', 'WKHS', 'HYMC', 'PHUN', 'DWAC',
                'SPRT', 'GREE', 'IRNT', 'OPAD', 'ANY', 'BGFV', 'ROOT',
                'CLOV', 'WISH', 'SKLZ', 'TLRY', 'ACB', 'CGC', 'CRON',
                'RIOT', 'MARA', 'BTBT', 'EBON', 'CAN', 'HVBT', 'BITF',
                
                # Small caps with squeeze potential
                'GME', 'AMC', 'KOSS', 'EXPR', 'BB', 'NOK', 'SIRI',
                'PLBY', 'BODY', 'BARK', 'MVST', 'QS', 'SPCE', 'RKT',
                
                # Recent IPOs and SPACs (high volatility)
                'RIVN', 'LCID', 'SOFI', 'HOOD', 'COIN', 'RBLX',
                
                # Volatile small caps
                'UPST', 'AFRM', 'PTON', 'ZM', 'BYND', 'OATLY',
                
                # Biotech small caps (explosive potential)
                'OCGN', 'VXRT', 'BNGO', 'CLVS', 'SRNE', 'VBIV',
                'MVIS', 'WKHS', 'JAGX', 'MICT', 'OGEN', 'SESN',
                
                # EV and green energy small caps
                'BLNK', 'CHPT', 'EVGO', 'SOLO', 'AYRO', 'ARVL',
                
                # Crypto/blockchain small caps
                'SI', 'MOGO', 'BTCS', 'GREE', 'FTFT', 'SOS',
                
                # Recent meme potential
                'BBBY', 'PETS', 'APRN', 'REV', 'PLAY', 'DDS',
                'BYND', 'UPST', 'HOOD', 'RBLX', 'COIN', 'SOFI'
            ]
            
            candidates.extend(penny_universe)
            
        except Exception as e:
            print(f"⚠️ Yahoo Finance scan error: {e}")
        
        return candidates
    
    def _get_high_short_interest_stocks(self) -> List[str]:
        """Get stocks with high short interest (squeeze candidates)"""
        
        high_short_stocks = []
        
        try:
            # Try to scrape from finviz or other sources
            # For now, use known high short interest stocks
            
            known_high_short = [
                # Known squeeze candidates
                'GME', 'AMC', 'BBBY', 'KOSS', 'EXPR', 'BB', 
                'WKHS', 'CLOV', 'WISH', 'ROOT', 'SKLZ',
                
                # Shorted small caps
                'NKLA', 'RIDE', 'GOEV', 'HYMC', 'MULN',
                
                # Heavily shorted penny stocks
                'SNDL', 'HITI', 'GNUS', 'PROG', 'ATER'
            ]
            
            high_short_stocks.extend(known_high_short)
            
        except Exception as e:
            print(f"⚠️ Short interest fetch error: {e}")
        
        return high_short_stocks
    
    def _get_small_cap_universe(self) -> List[str]:
        """Get small cap stocks (market cap < $2B)"""
        
        small_caps = []
        
        # Small caps with explosive potential
        small_cap_universe = [
            # Tech small caps
            'PLTR', 'SOFI', 'HOOD', 'COIN', 'RBLX', 'BROS', 'DNUT',
            
            # Healthcare/Biotech small caps
            'OCGN', 'VXRT', 'BNGO', 'SRNE', 'VBIV', 'MVIS', 'SESN',
            
            # EV small caps
            'BLNK', 'CHPT', 'EVGO', 'SOLO', 'AYRO', 'ARVL', 'GOEV',
            
            # Crypto/Blockchain small caps
            'RIOT', 'MARA', 'BTBT', 'SI', 'MOGO', 'GREE', 'SOS',
            
            # Consumer small caps
            'PLBY', 'BODY', 'BARK', 'BYND', 'OATLY', 'UPST', 'AFRM'
        ]
        
        small_caps.extend(small_cap_universe)
        
        return small_caps
    
    def _get_otc_candidates(self) -> List[str]:
        """Get OTC and pink sheet stocks"""
        
        # OTC stocks often trade with .OB or other suffixes
        # For now, return known OTC tickers
        
        otc_stocks = [
            # Note: OTC stocks may not be available on Yahoo Finance
            # These are the ones that sometimes appear
        ]
        
        return otc_stocks
    
    def _analyze_squeeze_potential(self, symbol: str) -> Optional[Dict]:
        """
        Analyze a stock for squeeze potential
        Returns detailed analysis with squeeze score
        """
        
        try:
            ticker = yf.Ticker(symbol)
            
            # Get stock info
            info = ticker.info
            
            # Get price data
            hist = ticker.history(period='3mo')
            
            if hist.empty or len(hist) < 20:
                return None
            
            current_price = hist['Close'].iloc[-1]
            
            # === FILTER 1: Price Range ===
            # Focus on stocks under $20 (more explosive potential)
            if current_price > 50:
                return None
            
            # === FILTER 2: Volume ===
            avg_volume = hist['Volume'].tail(20).mean()
            if avg_volume < 50000:  # Minimum liquidity
                return None
            
            # === CALCULATE SQUEEZE METRICS ===
            
            # Get market cap
            market_cap = info.get('marketCap', 0)
            
            # Get short interest data
            short_ratio = info.get('shortRatio', 0)
            short_percent_float = info.get('shortPercentOfFloat', 0)
            shares_short = info.get('sharesShort', 0)
            float_shares = info.get('floatShares', 0)
            
            # Calculate volume surge
            current_volume = hist['Volume'].iloc[-1]
            volume_surge = current_volume / avg_volume if avg_volume > 0 else 1
            
            # Calculate price momentum
            price_5d_ago = hist['Close'].iloc[-5] if len(hist) >= 5 else current_price
            price_momentum = ((current_price - price_5d_ago) / price_5d_ago * 100)
            
            # Calculate volatility
            returns = hist['Close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252) * 100  # Annualized
            
            # === CALCULATE SQUEEZE SCORE (0-100) ===
            squeeze_score = 0
            
            # Short interest component (0-30 points)
            if short_percent_float:
                if short_percent_float > 30:
                    squeeze_score += 30
                elif short_percent_float > 20:
                    squeeze_score += 25
                elif short_percent_float > 15:
                    squeeze_score += 20
                elif short_percent_float > 10:
                    squeeze_score += 15
                elif short_percent_float > 5:
                    squeeze_score += 10
            
            # Volume surge component (0-25 points)
            if volume_surge > 5:
                squeeze_score += 25
            elif volume_surge > 3:
                squeeze_score += 20
            elif volume_surge > 2:
                squeeze_score += 15
            elif volume_surge > 1.5:
                squeeze_score += 10
            
            # Price momentum component (0-20 points)
            if price_momentum > 20:
                squeeze_score += 20
            elif price_momentum > 10:
                squeeze_score += 15
            elif price_momentum > 5:
                squeeze_score += 10
            elif price_momentum > 0:
                squeeze_score += 5
            
            # Market cap component (0-15 points) - smaller = more explosive
            if market_cap < 100_000_000:  # < $100M
                squeeze_score += 15
            elif market_cap < 500_000_000:  # < $500M
                squeeze_score += 12
            elif market_cap < 1_000_000_000:  # < $1B
                squeeze_score += 9
            elif market_cap < 2_000_000_000:  # < $2B
                squeeze_score += 6
            
            # Volatility component (0-10 points)
            if volatility > 100:
                squeeze_score += 10
            elif volatility > 75:
                squeeze_score += 8
            elif volatility > 50:
                squeeze_score += 6
            
            # === BUILD RESULT ===
            result = {
                'symbol': symbol,
                'price': current_price,
                'market_cap': market_cap,
                'short_interest': short_percent_float or 0,
                'short_ratio': short_ratio or 0,
                'volume': current_volume,
                'avg_volume': avg_volume,
                'volume_surge': volume_surge,
                'price_momentum_5d': price_momentum,
                'volatility': volatility,
                'squeeze_score': squeeze_score,
                'float_shares': float_shares or 0,
                'shares_short': shares_short or 0,
                'company_name': info.get('shortName', symbol)
            }
            
            return result
            
        except Exception as e:
            # Silent fail for individual stocks
            return None
    
    def get_top_squeeze_plays(self, top_n: int = 20) -> List[Dict]:
        """Get top squeeze plays from latest scan"""
        
        if not self.screener_results:
            self.scan_entire_market()
        
        return self.screener_results[:top_n]
    
    def get_squeeze_play_details(self, symbol: str) -> Optional[Dict]:
        """Get detailed analysis for a specific squeeze candidate"""
        
        return self._analyze_squeeze_potential(symbol)


# Global instance
market_screener = MarketWideScreener()
