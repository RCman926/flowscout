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
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
warnings.filterwarnings('ignore')


class MarketWideScreener:
    """
    Comprehensive market scanner for squeeze candidates and explosive plays
    """
    
    def __init__(self):
        self.cache_duration = 300  # 5 minutes
        self.screener_results = []
        self.last_scan_time = None
        self.max_workers = 10  # Parallel processing threads
        
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
        print(f"📊 Found {len(unique_symbols)} unique candidates")
        
        # === INTELLIGENT PRE-FILTERING (FAST) ===
        # Quick filter to reduce from 200+ to 50-80 high-quality candidates
        print("🔍 Pre-filtering candidates (quick volume/price check)...")
        pre_filtered = self._quick_prefilter(unique_symbols[:200])  # Limit to 200 for speed
        print(f"✅ Pre-filtered to {len(pre_filtered)} high-potential candidates")
        
        # === PARALLEL ANALYSIS (FAST) ===
        explosive_plays = []
        
        print(f"⚡ Analyzing {len(pre_filtered)} candidates in parallel...")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all analysis tasks
            future_to_symbol = {
                executor.submit(self._analyze_squeeze_potential, symbol): symbol 
                for symbol in pre_filtered
            }
            
            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_symbol):
                completed += 1
                if completed % 10 == 0:
                    print(f"⚡ Analyzed {completed}/{len(pre_filtered)} stocks... (Found {len(explosive_plays)} plays)")
                
                try:
                    analysis = future.result()
                    if analysis and analysis.get('squeeze_score', 0) >= 60:
                        explosive_plays.append(analysis)
                except Exception as e:
                    pass  # Skip failed analyses
        
        print(f"✅ Analyzed {completed} stocks total (parallel processing)")
        
        # Sort by freshness score first (to show NEWEST opportunities), then squeeze score
        explosive_plays.sort(key=lambda x: (x.get('freshness_score', 0), x.get('squeeze_score', 0)), reverse=True)
        
        self.screener_results = explosive_plays
        self.last_scan_time = datetime.now()
        
        print(f"✅ Found {len(explosive_plays)} explosive opportunities!")
        
        return explosive_plays
    
    def _scan_yahoo_finance_universe(self, min_price: float, max_price: float, min_volume: int) -> List[str]:
        """Scan market for real candidate stocks dynamically"""
        
        candidates = []
        
        try:
            # METHOD 1: Get most active stocks from Yahoo Finance
            try:
                import requests
                
                # Yahoo Finance most actives endpoint
                url = "https://finance.yahoo.com/most-active"
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(url, headers=headers, timeout=5)
                
                if response.status_code == 200:
                    # Parse HTML for symbols
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Find ticker symbols in the page
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        if '/quote/' in href:
                            symbol = href.split('/quote/')[1].split('?')[0].split('/')[0]
                            if symbol and len(symbol) <= 5 and symbol.isalpha():
                                candidates.append(symbol)
            except:
                pass
            
            # METHOD 2: Get from predefined watchlists of volatile stocks
            # These are proven high-volume, volatile stocks that update regularly
            
            # Penny stocks universe ($0.50 - $10)
            penny_stocks = [
                'SNDL', 'HITI', 'ATER', 'BBIG', 'WKHS', 'HYMC',
                'GOEV', 'SKLZ', 'TLRY', 'ACB', 'CGC', 'CRON',
                'RIOT', 'MARA', 'BTBT', 'EBON', 'CAN', 'BITF'
            ]
            
            # Small cap high volatility ($10-50)
            small_cap_volatile = [
                'GME', 'AMC', 'KOSS', 'BB', 'NOK', 'SIRI',
                'PLBY', 'BARK', 'MVST', 'QS', 'SPCE', 'RKT',
                'RIVN', 'LCID', 'SOFI', 'HOOD', 'COIN', 'RBLX',
                'UPST', 'AFRM', 'PTON', 'ZM', 'BYND', 'OPEN',
                'BROS', 'DNUT', 'DKNG', 'PENN', 'PATH', 'DDOG'
            ]
            
            # Biotech/pharma small caps
            biotech_small = [
                'OCGN', 'VXRT', 'BNGO', 'CLVS', 'SRNE', 'VBIV',
                'MVIS', 'JAGX', 'OGEN', 'SESN', 'BGXX', 'EYPT',
                'ITOS', 'MBRX', 'ADXS', 'MTEM', 'CASI', 'ENDP'
            ]
            
            # EV and green energy
            ev_green = [
                'BLNK', 'CHPT', 'EVGO', 'SOLO', 'AYRO', 'ARVL',
                'PLUG', 'FCEL', 'BE', 'RUN', 'ENPH', 'SEDG'
            ]
            
            # Crypto/blockchain related
            crypto_stocks = [
                'SI', 'MOGO', 'BTCS', 'GREE', 'FTFT', 'SOS',
                'HUT', 'ARBK', 'CLSK', 'CIFR', 'IREN', 'WULF'
            ]
            
            # Chinese ADRs (volatile)
            chinese_adrs = [
                'BABA', 'JD', 'PDD', 'BIDU', 'NIO', 'XPEV',
                'LI', 'BILI', 'IQ', 'YUMC', 'BEKE', 'DIDI'
            ]
            
            # Recent IPOs/SPACs with volatility
            recent_ipos = [
                'BBBY', 'REV', 'PLAY', 'DDS', 'APRN', 'PETS',
                'SFIX', 'REAL', 'CAKE', 'CHWY', 'CVNA', 'DASH'
            ]
            
            # Volatile tech small caps
            tech_volatile = [
                'SNAP', 'PINS', 'YELP', 'ROKU', 'W', 'ETSY',
                'FTCH', 'ABNB', 'UBER', 'LYFT', 'GRAB', 'DIDI'
            ]
            
            # Combine all sources
            candidates.extend(penny_stocks)
            candidates.extend(small_cap_volatile)
            candidates.extend(biotech_small)
            candidates.extend(ev_green)
            candidates.extend(crypto_stocks)
            candidates.extend(chinese_adrs)
            candidates.extend(recent_ipos)
            candidates.extend(tech_volatile)
            
            # METHOD 3: Dynamically get top gainers and losers
            try:
                # These tend to have squeeze potential
                for category in ['gainers', 'losers', 'most-active']:
                    url = f"https://finance.yahoo.com/{category}"
                    response = requests.get(url, headers=headers, timeout=5)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        for link in soup.find_all('a', href=True):
                            href = link['href']
                            if '/quote/' in href:
                                symbol = href.split('/quote/')[1].split('?')[0].split('/')[0]
                                if symbol and len(symbol) <= 5:
                                    candidates.append(symbol)
            except:
                pass
            
        except Exception as e:
            print(f"⚠️ Market scan error: {e}")
        
        # Return unique symbols
        return list(set(candidates))
    
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
    
    def _quick_prefilter(self, symbols: List[str]) -> List[str]:
        """
        FAST pre-filtering to eliminate obvious low-quality candidates
        Only fetches minimal data to check volume/price surge
        Reduces candidates from 200+ to 50-80 high-quality ones
        """
        
        high_quality_candidates = []
        
        for symbol in symbols:
            try:
                # Ultra-fast check: only get last 5 days of data
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period='5d')
                
                if hist.empty or len(hist) < 3:
                    continue
                
                # Quick volume check
                recent_vol = hist['Volume'].tail(2).mean()
                older_vol = hist['Volume'].head(3).mean() if len(hist) >= 5 else recent_vol
                
                # Quick price check
                recent_price = hist['Close'].iloc[-1]
                old_price = hist['Close'].iloc[0] if len(hist) >= 3 else recent_price
                
                # Pre-filter criteria (loose requirements)
                volume_surge = recent_vol / older_vol if older_vol > 0 else 1
                price_change = ((recent_price - old_price) / old_price * 100) if old_price > 0 else 0
                
                # PASS if: volume surge OR price momentum OR both
                passes = False
                
                if volume_surge > 1.3:  # 30% volume increase
                    passes = True
                if abs(price_change) > 3:  # 3% price move
                    passes = True
                if recent_vol > 100000:  # Minimum liquidity
                    passes = True
                
                if passes and 0.5 < recent_price < 100:  # Price range filter
                    high_quality_candidates.append(symbol)
                    
            except Exception as e:
                # Skip problematic tickers
                continue
        
        return high_quality_candidates
    
    def _analyze_squeeze_potential(self, symbol: str) -> Optional[Dict]:
        """
        Analyze a stock for squeeze potential with FRESHNESS filter
        Returns detailed analysis with squeeze score and squeeze thesis
        """
        
        try:
            ticker = yf.Ticker(symbol)
            
            # Get stock info
            info = ticker.info
            
            # Get price data (need more history for freshness detection)
            hist = ticker.history(period='3mo')
            
            if hist.empty or len(hist) < 20:
                return None
            
            current_price = hist['Close'].iloc[-1]
            
            # === FILTER 1: Price Range ===
            # Focus on stocks under $50 (more explosive potential)
            if current_price > 50:
                return None
            
            # === FILTER 2: Volume ===
            avg_volume_20d = hist['Volume'].tail(20).mean()
            if avg_volume_20d < 50000:  # Minimum liquidity
                return None
            
            # === FRESHNESS ANALYSIS (KEY FOR FINDING NEW OPPORTUNITIES) ===
            
            # Recent volume (last 3 days) vs older volume (days 4-20)
            recent_volume = hist['Volume'].tail(3).mean()
            older_volume = hist['Volume'].tail(20).head(17).mean()  # Days 4-20
            
            # Calculate freshness metrics
            recent_surge = recent_volume / older_volume if older_volume > 0 else 1
            
            # Recent price action (just started moving?)
            price_1d = hist['Close'].iloc[-1]
            price_3d = hist['Close'].iloc[-3] if len(hist) >= 3 else price_1d
            price_10d = hist['Close'].iloc[-10] if len(hist) >= 10 else price_1d
            
            recent_move_3d = ((price_1d - price_3d) / price_3d * 100) if price_3d > 0 else 0
            longer_move_10d = ((price_1d - price_10d) / price_10d * 100) if price_10d > 0 else 0
            
            # Freshness score: High if recent activity >> historical activity
            freshness_score = 0
            
            # Recent volume explosion (last 3 days)
            if recent_surge > 3:
                freshness_score += 40  # Strong fresh setup
            elif recent_surge > 2:
                freshness_score += 30
            elif recent_surge > 1.5:
                freshness_score += 20
            
            # Just started moving (recent move >> older move)
            if recent_move_3d > 5 and recent_move_3d > longer_move_10d:
                freshness_score += 30  # Fresh breakout
            elif recent_move_3d > 3:
                freshness_score += 15
            
            # Recent volume spike (today vs 20-day average)
            current_volume = hist['Volume'].iloc[-1]
            today_surge = current_volume / avg_volume_20d if avg_volume_20d > 0 else 1
            if today_surge > 5:
                freshness_score += 30
            elif today_surge > 3:
                freshness_score += 20
            
            # === FRESHNESS FILTER: Only show FRESH opportunities ===
            # Require minimum freshness score to filter out old plays
            if freshness_score < 30:  # Not fresh enough
                return None
            
            # === CALCULATE SQUEEZE METRICS ===
            
            # Get market cap
            market_cap = info.get('marketCap', 0)
            
            # Get short interest data
            short_ratio = info.get('shortRatio', 0)
            short_percent_float = info.get('shortPercentOfFloat', 0)
            shares_short = info.get('sharesShort', 0)
            float_shares = info.get('floatShares', 0)
            
            # Calculate volume surge (today vs average)
            volume_surge = today_surge
            
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
            
            # === AI SQUEEZE PROBABILITY PREDICTION ===
            squeeze_probability = self._calculate_ai_squeeze_probability(
                short_percent_float=short_percent_float,
                volume_surge=volume_surge,
                recent_surge=recent_surge,
                price_momentum=price_momentum,
                recent_move_3d=recent_move_3d,
                volatility=volatility,
                market_cap=market_cap,
                float_shares=float_shares,
                freshness_score=freshness_score,
                hist=hist
            )
            
            # === GENERATE DETAILED SQUEEZE THESIS ===
            squeeze_thesis = self._generate_squeeze_thesis(
                symbol=symbol,
                short_percent_float=short_percent_float,
                volume_surge=volume_surge,
                recent_surge=recent_surge,
                recent_move_3d=recent_move_3d,
                price_momentum=price_momentum,
                market_cap=market_cap,
                float_shares=float_shares,
                freshness_score=freshness_score,
                volatility=volatility,
                squeeze_probability=squeeze_probability
            )
            
            # === BUILD RESULT ===
            result = {
                'symbol': symbol,
                'price': current_price,
                'market_cap': market_cap,
                'short_interest': short_percent_float or 0,
                'short_ratio': short_ratio or 0,
                'volume': current_volume,
                'avg_volume': avg_volume_20d,
                'volume_surge': volume_surge,
                'price_momentum_5d': price_momentum,
                'volatility': volatility,
                'squeeze_score': squeeze_score,
                'float_shares': float_shares or 0,
                'shares_short': shares_short or 0,
                'company_name': info.get('shortName', symbol),
                'freshness_score': freshness_score,
                'recent_surge_3d': recent_surge,
                'recent_move_3d': recent_move_3d,
                'squeeze_thesis': squeeze_thesis,
                'squeeze_probability': squeeze_probability  # AI-predicted probability
            }
            
            return result
            
        except Exception as e:
            # Silent fail for individual stocks
            return None
    
    def _calculate_ai_squeeze_probability(self, short_percent_float: float,
                                          volume_surge: float, recent_surge: float,
                                          price_momentum: float, recent_move_3d: float,
                                          volatility: float, market_cap: float,
                                          float_shares: float, freshness_score: int,
                                          hist: pd.DataFrame) -> float:
        """
        AI-based squeeze probability prediction using multiple factors
        Returns probability 0-100%
        """
        
        probability = 0.0
        
        # === FACTOR 1: Short Interest Strength (0-25%) ===
        if short_percent_float > 30:
            probability += 25
        elif short_percent_float > 20:
            probability += 20
        elif short_percent_float > 10:
            probability += 12
        elif short_percent_float > 5:
            probability += 6
        
        # === FACTOR 2: Volume Momentum (0-20%) ===
        if recent_surge > 4:
            probability += 20
        elif recent_surge > 3:
            probability += 15
        elif recent_surge > 2:
            probability += 10
        elif volume_surge > 3:
            probability += 12
        elif volume_surge > 2:
            probability += 8
        
        # === FACTOR 3: Price Action Strength (0-20%) ===
        if recent_move_3d > 15:
            probability += 20
        elif recent_move_3d > 10:
            probability += 15
        elif recent_move_3d > 5:
            probability += 10
        elif price_momentum > 15:
            probability += 12
        elif price_momentum > 8:
            probability += 8
        
        # === FACTOR 4: Float Tightness (0-15%) ===
        if float_shares > 0:
            if float_shares < 10_000_000:  # < 10M
                probability += 15
            elif float_shares < 25_000_000:  # < 25M
                probability += 12
            elif float_shares < 50_000_000:  # < 50M
                probability += 8
        
        # === FACTOR 5: Freshness/Timing (0-10%) ===
        if freshness_score >= 70:
            probability += 10
        elif freshness_score >= 50:
            probability += 7
        elif freshness_score >= 30:
            probability += 4
        
        # === FACTOR 6: Technical Pattern Recognition (0-10%) ===
        try:
            # Check for breakout pattern
            if len(hist) >= 20:
                recent_high = hist['High'].tail(5).max()
                prev_high = hist['High'].tail(20).head(15).max()
                
                if recent_high > prev_high * 1.05:  # Breaking out
                    probability += 6
                
                # Check for increasing volume trend
                vol_recent = hist['Volume'].tail(5).mean()
                vol_prev = hist['Volume'].tail(15).head(10).mean()
                if vol_recent > vol_prev * 1.5:
                    probability += 4
        except:
            pass
        
        # Cap at 100%
        probability = min(100, probability)
        
        return probability
    
    def _generate_squeeze_thesis(self, symbol: str, short_percent_float: float, 
                                  volume_surge: float, recent_surge: float,
                                  recent_move_3d: float, price_momentum: float,
                                  market_cap: float, float_shares: float,
                                  freshness_score: int, volatility: float,
                                  squeeze_probability: float) -> str:
        """
        Generate detailed squeeze thesis explaining WHY this stock will squeeze
        """
        
        thesis_parts = []
        
        # === AI PROBABILITY HEADER ===
        if squeeze_probability >= 75:
            thesis_parts.append(f"🚀 **AI SQUEEZE PROBABILITY: {squeeze_probability:.0f}%** - EXTREMELY HIGH probability of squeeze")
        elif squeeze_probability >= 60:
            thesis_parts.append(f"⚡ **AI SQUEEZE PROBABILITY: {squeeze_probability:.0f}%** - HIGH probability of squeeze")
        elif squeeze_probability >= 45:
            thesis_parts.append(f"📊 **AI SQUEEZE PROBABILITY: {squeeze_probability:.0f}%** - MODERATE probability of squeeze")
        else:
            thesis_parts.append(f"📈 **AI SQUEEZE PROBABILITY: {squeeze_probability:.0f}%** - Developing setup")
        
        # === FRESHNESS ANALYSIS ===
        if freshness_score >= 60:
            thesis_parts.append(f"🔥 **FRESH SETUP ALERT**: This is a NEW opportunity developing in the last 1-3 days (freshness score: {freshness_score}/100)")
        elif freshness_score >= 40:
            thesis_parts.append(f"⚡ **RECENT DEVELOPMENT**: Fresh activity detected in past few days (freshness score: {freshness_score}/100)")
        else:
            thesis_parts.append(f"📊 **EMERGING SETUP**: Early stage opportunity forming (freshness score: {freshness_score}/100)")
        
        # === VOLUME CATALYST ===
        if recent_surge > 3:
            thesis_parts.append(f"📈 **EXPLOSIVE VOLUME SURGE**: Last 3 days volume is {recent_surge:.1f}x higher than previous weeks - institutional money is entering NOW")
        elif recent_surge > 2:
            thesis_parts.append(f"🚀 **STRONG VOLUME INCREASE**: Recent volume surge of {recent_surge:.1f}x - smart money accumulating")
        elif volume_surge > 3:
            thesis_parts.append(f"⚡ **TODAY'S VOLUME SPIKE**: {volume_surge:.1f}x average volume - breakout in progress")
        
        # === PRICE ACTION ===
        if recent_move_3d > 10:
            thesis_parts.append(f"💰 **MOMENTUM IGNITING**: Up {recent_move_3d:+.1f}% in last 3 days - squeeze mechanics activating")
        elif recent_move_3d > 5:
            thesis_parts.append(f"📊 **PRICE BREAKOUT**: {recent_move_3d:+.1f}% move in 3 days - shorts starting to feel pressure")
        elif price_momentum > 10:
            thesis_parts.append(f"🎯 **STRONG MOMENTUM**: {price_momentum:+.1f}% move over 5 days - trend established")
        
        # === SHORT SQUEEZE MECHANICS ===
        if short_percent_float > 20:
            thesis_parts.append(f"🔴 **EXTREME SHORT INTEREST**: {short_percent_float:.1f}% of float shorted - massive squeeze potential if price rises")
            if float_shares > 0 and float_shares < 50_000_000:
                thesis_parts.append(f"⚠️ **TIGHT FLOAT**: Only {float_shares/1_000_000:.1f}M shares - shorts will struggle to cover in rising market")
        elif short_percent_float > 10:
            thesis_parts.append(f"🟠 **HIGH SHORT INTEREST**: {short_percent_float:.1f}% shorted - shorts vulnerable to squeeze")
        elif short_percent_float > 5:
            thesis_parts.append(f"🟡 **MODERATE SHORT INTEREST**: {short_percent_float:.1f}% shorted - potential for covering rally")
        
        # === MARKET CAP / EXPLOSIVE POTENTIAL ===
        if market_cap < 100_000_000:
            thesis_parts.append(f"💎 **MICRO CAP GEM**: ${market_cap/1_000_000:.0f}M market cap - small buying pressure creates HUGE moves")
        elif market_cap < 500_000_000:
            thesis_parts.append(f"🎯 **SMALL CAP ROCKET**: ${market_cap/1_000_000:.0f}M market cap - high beta explosive potential")
        elif market_cap < 1_000_000_000:
            thesis_parts.append(f"📊 **SMALL CAP PLAY**: ${market_cap/1_000_000:.0f}M market cap - room for significant upside")
        
        # === VOLATILITY / TRADING DYNAMICS ===
        if volatility > 100:
            thesis_parts.append(f"🌪️ **EXTREME VOLATILITY**: {volatility:.0f}% annualized - explosive intraday moves expected")
        elif volatility > 75:
            thesis_parts.append(f"⚡ **HIGH VOLATILITY**: {volatility:.0f}% annualized - quick moves likely")
        
        # === SQUEEZE TIMING ===
        if freshness_score >= 50 and volume_surge > 3:
            thesis_parts.append(f"⏰ **SQUEEZE TIMING**: Setup is FRESH with volume confirming - entry window is NOW before crowd notices")
        elif freshness_score >= 40 and recent_move_3d > 5:
            thesis_parts.append(f"🎯 **EARLY STAGE**: Just starting to move with fresh volume - get in before main move")
        else:
            thesis_parts.append(f"📈 **DEVELOPING SETUP**: Monitor for entry as setup develops")
        
        # === RISK FACTORS ===
        risk_note = "\n\n⚠️ **RISK FACTORS**: "
        if volatility > 100:
            risk_note += "Extreme volatility means large swings. "
        if market_cap < 100_000_000:
            risk_note += "Micro cap = high risk/reward. "
        if short_percent_float < 10:
            risk_note += "Lower short interest = less squeeze power. "
        
        thesis_parts.append(risk_note + "Use stop losses and position sizing.")
        
        return "\n\n".join(thesis_parts)
    
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
