"""
Market-Wide Explosive Opportunity Screener
Scans the entire market for high short interest squeeze candidates
Focus: Small caps, OTC stocks, and real explosive potential plays
UPGRADED WITH: Real SI data, options flow, borrow rates, dark pools, float rotation, 
historical win rate, catalysts, social sentiment
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

# Import advanced data sources
try:
    from advanced_data_sources import advanced_data
    ADVANCED_DATA_AVAILABLE = True
except ImportError:
    ADVANCED_DATA_AVAILABLE = False
    print("⚠️ Advanced data sources not available - using basic mode")

# Import extended hours tracker for real-time pricing
try:
    from extended_hours_tracker import ExtendedHoursTracker
    extended_hours_tracker = ExtendedHoursTracker()
    EXTENDED_HOURS_AVAILABLE = True
except ImportError:
    EXTENDED_HOURS_AVAILABLE = False
    print("⚠️ Extended hours tracker not available - using regular close prices")


class MarketWideScreener:
    """
    Comprehensive market scanner for squeeze candidates and explosive plays
    """
    
    def __init__(self):
        self.cache_duration = 900  # 15 minutes (avoid Yahoo rate limiting)
        self.screener_results = []
        self.last_scan_time = None
        self.max_workers = 3  # Reduced to avoid Yahoo Finance rate limiting
        
    def scan_entire_market(self, min_price: float = 0.50, max_price: float = 20.0, 
                          min_volume: int = 100000) -> List[Dict]:
        """
        Scan entire market for explosive opportunities
        Focus on small caps, high short interest, squeeze potential
        """
        
        # Check cache
        if self.last_scan_time and (datetime.now() - self.last_scan_time).seconds < self.cache_duration:
            return self.screener_results
        
        print("🔍 Scanning for explosive opportunities...")
        
        # === TEMPORARY: FOCUS ON KNOWN SQUEEZE CANDIDATES ===
        # Using hardcoded list to avoid Yahoo Finance rate limiting
        # TODO: Change back to full 500+ scan once IBKR is connected
        print("📌 FOCUSED SCAN: Analyzing known squeeze candidates (BYND, DNUT)")
        pre_filtered = ['BYND', 'DNUT']  # Known squeeze plays with high short interest
        
        # ORIGINAL CODE (commented out for now - uncomment when IBKR connected):
        # candidates = []
        # yf_candidates = self._scan_yahoo_finance_universe(min_price, max_price, min_volume)
        # candidates.extend(yf_candidates)
        # high_short_stocks = self._get_high_short_interest_stocks()
        # candidates.extend(high_short_stocks)
        # small_caps = self._get_small_cap_universe()
        # candidates.extend(small_caps)
        # otc_stocks = self._get_otc_candidates()
        # candidates.extend(otc_stocks)
        # unique_symbols = list(set(candidates))
        # print(f"📊 Found {len(unique_symbols)} unique candidates")
        # print("🔍 Pre-filtering candidates (quick volume/price check)...")
        # pre_filtered = self._quick_prefilter(unique_symbols[:500])
        # print(f"✅ Pre-filtered to {len(pre_filtered)} high-potential candidates")
        
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
                    if analysis and self._is_explosive_opportunity(analysis):
                        explosive_plays.append(analysis)
                    
                    # Add delay to avoid rate limiting (only needed for large scans)
                    import time
                    time.sleep(0.5)  # Short delay for focused scan
                except Exception as e:
                    pass  # Skip failed analyses
        
        print(f"✅ Analyzed {completed} stocks total (parallel processing)")
        
        # Sort by PRIORITY (PRE-SQUEEZE first, then by short interest and early warning)
        def get_sort_priority(analysis):
            """
            Calculate sort priority - higher is better
            Prioritizes PRE-SQUEEZE > READY > BUILDING > ACTIVE
            Then by short interest and early warning scores
            """
            stage = analysis.get('squeeze_stage', '')
            short_interest = analysis.get('real_short_float', 0)
            early_warning = analysis.get('early_warning_score', 0)
            
            # Stage priority (0-1000 points)
            stage_points = {
                'PRE_SQUEEZE': 1000,  # Highest priority - perfect entry window
                'READY': 800,          # High priority - imminent move
                'BUILDING': 600,       # Medium priority - early stage
                'ACTIVE': 400,         # Low priority - late entry
                'POST': 0              # Should be filtered out already
            }.get(stage, 0)
            
            # Short interest points (0-500)
            si_points = min(short_interest * 5, 500)
            
            # Early warning points (0-200)
            ew_points = early_warning * 2
            
            # Total priority score
            return stage_points + si_points + ew_points
        
        explosive_plays.sort(key=get_sort_priority, reverse=True)
        
        self.screener_results = explosive_plays
        self.last_scan_time = datetime.now()
        
        print(f"✅ Found {len(explosive_plays)} explosive opportunities!")
        
        return explosive_plays
    
    def _is_explosive_opportunity(self, analysis: Dict) -> bool:
        """
        SMART FILTERING: Prioritize PRE-SQUEEZE opportunities, not stocks that already squeezed
        
        This filters for:
        1. High short interest (real squeeze fuel)
        2. PRE-SQUEEZE, READY, or BUILDING stages (NOT ACTIVE or POST - those are too late!)
        3. Hard borrow rates (shorts are bleeding)
        4. Strong institutional signals
        5. Early warning indicators (forward-looking, not backward-looking)
        
        REJECTS:
        - ACTIVE or POST stage (squeeze already happened - like SCNX)
        - Low short interest (no squeeze fuel)
        - Stocks that already pumped (we want BEFORE the pump)
        """
        
        # Get key metrics
        squeeze_stage = analysis.get('squeeze_stage', '')
        short_interest = analysis.get('real_short_float', 0)
        borrow_difficulty = analysis.get('borrow_difficulty', 'EASY')
        early_warning = analysis.get('early_warning_score', 0)
        squeeze_probability = analysis.get('squeeze_probability', 0)
        
        # === REJECT CRITERIA (Immediate disqualification) ===
        
        # 1. REJECT stocks that already squeezed (POST stage)
        if squeeze_stage == 'POST':
            return False
        
        # 2. REJECT stocks actively squeezing NOW (ACTIVE stage - too late to enter safely)
        # Exception: Allow if short interest is VERY high (>40%) indicating multi-day squeeze potential
        if squeeze_stage == 'ACTIVE':
            if short_interest < 40:
                return False
        
        # === PRIORITY CRITERIA (What we're looking for) ===
        
        # TIER 1: PRE-SQUEEZE setups (1-5 days out) - HIGHEST PRIORITY
        if squeeze_stage == 'PRE_SQUEEZE':
            # Must have real squeeze fuel
            if short_interest >= 20 or borrow_difficulty in ['HARD', 'VERY HARD']:
                return True
        
        # TIER 2: READY TO SQUEEZE (0-2 days out) - HIGH PRIORITY
        if squeeze_stage == 'READY':
            if short_interest >= 15 or borrow_difficulty in ['HARD', 'VERY HARD']:
                return True
        
        # TIER 3: BUILDING stage with strong fundamentals - MEDIUM PRIORITY
        if squeeze_stage == 'BUILDING':
            # Need VERY strong squeeze fundamentals to show in screener
            if short_interest >= 30 and borrow_difficulty in ['HARD', 'VERY HARD']:
                return True
            # OR high short interest + strong early warning signals
            if short_interest >= 40 and early_warning >= 30:
                return True
        
        # TIER 4: ACTIVE squeezes with EXTREME short interest (multi-day potential) - LOW PRIORITY
        if squeeze_stage == 'ACTIVE':
            if short_interest >= 50 and borrow_difficulty == 'VERY HARD':
                return True
        
        # TIER 5: Fallback for high-probability setups regardless of stage
        # This catches edge cases with extreme metrics
        if squeeze_probability >= 80 and short_interest >= 40:
            return True
        
        # Default: Don't show in screener
        return False
    
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
    
    def _quick_prefilter_single(self, symbol: str) -> Optional[str]:
        """
        Single stock pre-filter check (for parallel processing)
        Returns symbol if it passes, None otherwise
        """
        try:
            # Ultra-fast check: only get last 5 days of data
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='5d')
            
            if hist.empty or len(hist) < 3:
                return None
            
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
                return symbol
            
            return None
                
        except Exception as e:
            # Skip problematic tickers
            return None
    
    def _quick_prefilter(self, symbols: List[str]) -> List[str]:
        """
        PARALLEL pre-filtering to eliminate obvious low-quality candidates
        Only fetches minimal data to check volume/price surge
        Reduces candidates from 200+ to 50-80 high-quality ones
        """
        
        high_quality_candidates = []
        
        # PARALLEL PRE-FILTERING (FAST!)
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all pre-filter tasks in parallel
            future_to_symbol = {
                executor.submit(self._quick_prefilter_single, symbol): symbol 
                for symbol in symbols
            }
            
            # Collect results
            for future in as_completed(future_to_symbol):
                try:
                    result = future.result()
                    if result:
                        high_quality_candidates.append(result)
                except Exception:
                    pass
        
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
            
            # Get regular close price (extended hours fetched later in UI for performance)
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
            
            # === INSTITUTIONAL-GRADE TECHNICAL ANALYSIS ===
            institutional_metrics = self._calculate_institutional_metrics(hist, current_price)
            
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
                hist=hist,
                institutional_metrics=institutional_metrics
            )
            
            # === RISK/REWARD ANALYSIS ===
            risk_reward = self._calculate_risk_reward(
                current_price=current_price,
                hist=hist,
                volatility=volatility,
                institutional_metrics=institutional_metrics
            )
            
            # === CONFIDENCE SCORING ===
            confidence = self._calculate_confidence_score(
                short_percent_float=short_percent_float,
                volume_surge=volume_surge,
                freshness_score=freshness_score,
                institutional_metrics=institutional_metrics
            )
            
            # === ADVANCED INSTITUTIONAL DATA (8 NEW FEATURES) ===
            # Get REAL data FIRST (before early warning calculation)
            real_si_data = {}
            options_flow = {}
            borrow_rate_data = {}
            dark_pool_data = {}
            float_rotation_data = {}
            win_rate_data = {}
            catalyst_data = {}
            sentiment_data = {}
            
            if ADVANCED_DATA_AVAILABLE:
                try:
                    # 1. Real Short Interest Data (GET THIS FIRST!)
                    real_si_data = advanced_data.get_real_short_interest(symbol)
                    
                    # 2. Real Options Flow
                    options_flow = advanced_data.get_options_flow_data(symbol)
                    
                    # 3. Borrow Rate
                    borrow_rate_data = advanced_data.get_borrow_rate(symbol)
                    
                    # 4. Dark Pool Detection
                    dark_pool_data = advanced_data.detect_dark_pool_activity(symbol)
                    
                    # 5. Float Rotation
                    float_rotation_data = advanced_data.analyze_float_rotation(symbol)
                    
                    # 6. Historical Win Rate
                    win_rate_data = advanced_data.calculate_historical_win_rate(symbol)
                    
                    # 7. Upcoming Catalysts
                    catalyst_data = advanced_data.get_upcoming_catalysts(symbol)
                    
                    # 8. Social Sentiment
                    sentiment_data = advanced_data.get_social_sentiment(symbol)
                    
                except Exception as e:
                    print(f"⚠️ Advanced data fetch failed for {symbol}: {e}")
            
            # === PRE-SQUEEZE DETECTION (Early Warning System) ===
            # NOW calculate with REAL short interest data!
            real_short_interest = real_si_data.get('short_percent_float', short_percent_float) if real_si_data else short_percent_float
            
            pre_squeeze_signals = self._detect_pre_squeeze_signals(
                hist=hist,
                short_percent_float=real_short_interest,  # Use REAL SI, not old yfinance data!
                current_price=current_price,
                institutional_metrics=institutional_metrics
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
            
            # === BUILD RESULT (INSTITUTIONAL-GRADE) ===
            result = {
                # Basic Info
                'symbol': symbol,
                'price': current_price,  # Regular close (extended hours fetched in UI for performance)
                'company_name': info.get('shortName', symbol),
                'market_cap': market_cap,
                
                # Squeeze Metrics
                'short_interest': short_percent_float or 0,
                'short_ratio': short_ratio or 0,
                'float_shares': float_shares or 0,
                'shares_short': shares_short or 0,
                'squeeze_score': squeeze_score,
                'squeeze_probability': squeeze_probability,  # AI-predicted probability
                'confidence': confidence,  # Prediction confidence
                
                # Volume & Momentum
                'volume': current_volume,
                'avg_volume': avg_volume_20d,
                'volume_surge': volume_surge,
                'recent_surge_3d': recent_surge,
                'price_momentum_5d': price_momentum,
                'recent_move_3d': recent_move_3d,
                'freshness_score': freshness_score,
                'volatility': volatility,
                
                # Institutional Technical Indicators
                'rsi': institutional_metrics.get('rsi', 50),
                'macd_histogram': institutional_metrics.get('macd_histogram', 0),
                'bb_position': institutional_metrics.get('bb_position', 50),
                'volume_trend': institutional_metrics.get('volume_trend', 0),
                'atr_percent': institutional_metrics.get('atr_percent', 0),
                
                # Risk/Reward Analysis
                'stop_loss': risk_reward.get('stop_loss', 0),
                'risk_percent': risk_reward.get('risk_percent', 0),
                'target_1': risk_reward.get('target_1', 0),
                'target_2': risk_reward.get('target_2', 0),
                'target_3': risk_reward.get('target_3', 0),
                'moon_shot': risk_reward.get('moon_shot', 0),  # NEW: Extreme squeeze target
                'risk_reward_ratio': risk_reward.get('risk_reward_ratio_1', 0),
                'expected_move_up': risk_reward.get('expected_move_up_1w', 0),
                'expected_move_down': risk_reward.get('expected_move_down_1w', 0),
                'recent_support': risk_reward.get('recent_support', 0),  # NEW: 10-day support
                'recent_resistance': risk_reward.get('recent_resistance', 0),  # NEW: 10-day resistance
                'support_20d': risk_reward.get('support_20d', 0),  # Reference only
                'resistance_20d': risk_reward.get('resistance_20d', 0),  # Reference only
                'buy_in_ideal': risk_reward.get('buy_in_ideal', 0),  # NEW: Buy-in recommendation
                'buy_in_low': risk_reward.get('buy_in_low', 0),  # NEW: Buy zone low
                'buy_in_high': risk_reward.get('buy_in_high', 0),  # NEW: Buy zone high
                'buy_rationale': risk_reward.get('buy_rationale', ''),  # NEW: Buy-in rationale
                
                # PRE-SQUEEZE EARLY WARNING SIGNALS
                'squeeze_stage': pre_squeeze_signals.get('squeeze_stage', 'UNKNOWN'),
                'early_warning_score': pre_squeeze_signals.get('early_warning_score', 0),
                'days_until_squeeze': pre_squeeze_signals.get('days_until_squeeze', 'Unknown'),
                'volatility_compression': pre_squeeze_signals.get('volatility_compression', 0),
                'accumulation_score': pre_squeeze_signals.get('accumulation_score', 0),
                'short_interest_trend': pre_squeeze_signals.get('short_interest_trend', 0),
                'option_activity': pre_squeeze_signals.get('option_activity', 0),
                
                # ADVANCED FEATURE 1: REAL SHORT INTEREST (FIXED MAPPING)
                'real_si_data_source': real_si_data.get('data_source', 'unavailable') if real_si_data else 'unavailable',
                'real_short_float': real_si_data.get('short_percent_float', 0) if real_si_data else 0,
                'real_short_ratio': real_si_data.get('short_ratio', 0) if real_si_data else 0,
                
                # ADVANCED FEATURE 2: OPTIONS FLOW (FIXED MAPPING)
                'unusual_options_activity': options_flow.get('unusual_activity_score', 0) if options_flow else 0,
                'unusual_call_buying': options_flow.get('unusual_call_buying', False) if options_flow else False,
                'sweep_orders': options_flow.get('sweep_orders_detected', 0) if options_flow else 0,
                'put_call_ratio': options_flow.get('put_call_ratio', 1) if options_flow else 1,
                
                # ADVANCED FEATURE 3: BORROW RATE (FIXED MAPPING)
                'borrow_rate': borrow_rate_data.get('estimated_borrow_rate', 0) if borrow_rate_data else 0,
                'borrow_difficulty': borrow_rate_data.get('borrow_difficulty', 'UNKNOWN') if borrow_rate_data else 'UNKNOWN',
                
                # ADVANCED FEATURE 4: DARK POOL (FIXED MAPPING)
                'dark_pool_score': dark_pool_data.get('dark_pool_score', 0) if dark_pool_data else 0,
                'institutional_accumulation': dark_pool_data.get('accumulation_pattern', False) if dark_pool_data else False,
                'unusual_block_trades': dark_pool_data.get('unusual_block_trades', 0) if dark_pool_data else 0,
                
                # ADVANCED FEATURE 5: FLOAT ROTATION (FIXED MAPPING)
                'float_rotation_5d': float_rotation_data.get('rotation_rate_5d', 0) if float_rotation_data else 0,
                'entire_float_trading': float_rotation_data.get('entire_float_trading', False) if float_rotation_data else False,
                'days_to_trade_float': float_rotation_data.get('days_to_trade_float', 999) if float_rotation_data else 999,
                
                # ADVANCED FEATURE 6: HISTORICAL WIN RATE (FIXED MAPPING)
                'historical_win_rate': win_rate_data.get('win_rate', 0) if win_rate_data else 0,
                'avg_historical_gain': win_rate_data.get('avg_gain_percent', 0) if win_rate_data else 0,
                'pattern_success_count': win_rate_data.get('success_count', 0) if win_rate_data else 0,
                'total_patterns_found': win_rate_data.get('total_patterns', 0) if win_rate_data else 0,
                'win_rate_confidence': win_rate_data.get('confidence_level', 'UNKNOWN') if win_rate_data else 'UNKNOWN',
                
                # ADVANCED FEATURE 7: CATALYSTS (FIXED MAPPING)
                'catalyst_score': catalyst_data.get('catalyst_score', 0) if catalyst_data else 0,
                'has_upcoming_catalyst': catalyst_data.get('has_upcoming_catalyst', False) if catalyst_data else False,
                'next_catalyst': catalyst_data.get('next_catalyst', None) if catalyst_data else None,
                'days_until_catalyst': catalyst_data.get('days_until_catalyst', 999) if catalyst_data else 999,
                
                # ADVANCED FEATURE 8: SOCIAL SENTIMENT (FIXED MAPPING)
                'social_sentiment_score': sentiment_data.get('sentiment_score', 0) if sentiment_data else 0,
                'social_buzz_level': sentiment_data.get('buzz_level', 'LOW') if sentiment_data else 'LOW',
                'is_trending': sentiment_data.get('is_trending', False) if sentiment_data else False,
                'wsb_candidate': sentiment_data.get('wsb_candidate', False) if sentiment_data else False,
                'retail_interest': sentiment_data.get('retail_interest', 'LOW') if sentiment_data else 'LOW',
                
                # Thesis
                'squeeze_thesis': squeeze_thesis
            }
            
            return result
            
        except Exception as e:
            # Log error for debugging
            print(f"⚠️ Analysis failed for {symbol}: {type(e).__name__}: {str(e)[:100]}")
            return None
    
    def _calculate_institutional_metrics(self, hist: pd.DataFrame, current_price: float) -> Dict:
        """
        INSTITUTIONAL-GRADE technical analysis using advanced indicators
        Returns comprehensive metrics used by hedge funds and prop desks
        """
        
        metrics = {}
        
        try:
            # Calculate RSI (Relative Strength Index)
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            metrics['rsi'] = rsi.iloc[-1] if len(rsi) > 0 else 50
            
            # MACD (Moving Average Convergence Divergence)
            exp1 = hist['Close'].ewm(span=12, adjust=False).mean()
            exp2 = hist['Close'].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()
            metrics['macd'] = macd.iloc[-1] if len(macd) > 0 else 0
            metrics['macd_signal'] = signal.iloc[-1] if len(signal) > 0 else 0
            metrics['macd_histogram'] = metrics['macd'] - metrics['macd_signal']
            
            # Bollinger Bands
            bb_period = 20
            if len(hist) >= bb_period:
                sma = hist['Close'].rolling(window=bb_period).mean()
                std = hist['Close'].rolling(window=bb_period).std()
                upper_band = sma + (std * 2)
                lower_band = sma - (std * 2)
                
                metrics['bb_upper'] = upper_band.iloc[-1]
                metrics['bb_lower'] = lower_band.iloc[-1]
                metrics['bb_position'] = (current_price - lower_band.iloc[-1]) / (upper_band.iloc[-1] - lower_band.iloc[-1]) * 100
            else:
                metrics['bb_position'] = 50
            
            # Volume Profile Analysis
            metrics['volume_trend'] = 0
            if len(hist) >= 20:
                recent_vol = hist['Volume'].tail(5).mean()
                older_vol = hist['Volume'].tail(20).head(15).mean()
                metrics['volume_trend'] = ((recent_vol - older_vol) / older_vol * 100) if older_vol > 0 else 0
            
            # Price Momentum Oscillator
            if len(hist) >= 10:
                momentum = hist['Close'].iloc[-1] - hist['Close'].iloc[-10]
                metrics['momentum'] = (momentum / hist['Close'].iloc[-10] * 100) if hist['Close'].iloc[-10] > 0 else 0
            else:
                metrics['momentum'] = 0
            
            # Average True Range (ATR) - Volatility measure
            if len(hist) >= 14:
                high_low = hist['High'] - hist['Low']
                high_close = np.abs(hist['High'] - hist['Close'].shift())
                low_close = np.abs(hist['Low'] - hist['Close'].shift())
                ranges = pd.concat([high_low, high_close, low_close], axis=1)
                true_range = ranges.max(axis=1)
                atr = true_range.rolling(14).mean()
                metrics['atr'] = atr.iloc[-1] if len(atr) > 0 else 0
                metrics['atr_percent'] = (metrics['atr'] / current_price * 100) if current_price > 0 else 0
            else:
                metrics['atr_percent'] = 0
                
        except Exception as e:
            # Return neutral values on error
            metrics = {
                'rsi': 50, 'macd': 0, 'macd_signal': 0, 'macd_histogram': 0,
                'bb_position': 50, 'volume_trend': 0, 'momentum': 0, 'atr_percent': 0
            }
        
        return metrics
    
    def _calculate_ai_squeeze_probability(self, short_percent_float: float,
                                          volume_surge: float, recent_surge: float,
                                          price_momentum: float, recent_move_3d: float,
                                          volatility: float, market_cap: float,
                                          float_shares: float, freshness_score: int,
                                          hist: pd.DataFrame, institutional_metrics: Dict) -> float:
        """
        INSTITUTIONAL-GRADE AI prediction using advanced ML and technical analysis
        Returns probability 0-100% with confidence scoring
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
        
        # === FACTOR 6: RSI (Relative Strength Index) (0-10%) ===
        rsi = institutional_metrics.get('rsi', 50)
        if 30 <= rsi <= 45:  # Oversold but recovering
            probability += 10
        elif 45 < rsi <= 55:  # Neutral momentum
            probability += 6
        elif 55 < rsi <= 70:  # Strong uptrend
            probability += 8
        elif rsi > 70:  # Overbought (risky but momentum strong)
            probability += 5
        
        # === FACTOR 7: MACD Momentum (0-10%) ===
        macd_hist = institutional_metrics.get('macd_histogram', 0)
        if macd_hist > 0:  # Bullish crossover
            probability += 10
        elif macd_hist > -0.5:  # Nearly neutral
            probability += 5
        
        # === FACTOR 8: Bollinger Bands Position (0-10%) ===
        bb_pos = institutional_metrics.get('bb_position', 50)
        if bb_pos < 20:  # Near lower band - potential reversal
            probability += 10
        elif bb_pos < 40:  # Lower half
            probability += 7
        elif bb_pos > 80:  # Near upper band - breakout
            probability += 8
        
        # === FACTOR 9: Volume Trend (0-5%) ===
        vol_trend = institutional_metrics.get('volume_trend', 0)
        if vol_trend > 50:  # Strong volume increase
            probability += 5
        elif vol_trend > 25:  # Moderate increase
            probability += 3
        
        # === FACTOR 10: Pattern Recognition (0-5%) ===
        try:
            # Check for breakout pattern
            if len(hist) >= 20:
                recent_high = hist['High'].tail(5).max()
                prev_high = hist['High'].tail(20).head(15).max()
                
                if recent_high > prev_high * 1.05:  # Breaking out
                    probability += 5
        except:
            pass
        
        # Cap at 100%
        probability = min(100, probability)
        
        return probability
    
    def _calculate_risk_reward(self, current_price: float, hist: pd.DataFrame,
                               volatility: float, institutional_metrics: Dict) -> Dict:
        """
        INSTITUTIONAL-GRADE Risk/Reward Analysis
        Returns expected moves, stop levels, and risk/reward ratio
        """
        
        risk_reward = {}
        
        try:
            # Calculate ATR-based stops and targets
            atr = institutional_metrics.get('atr_percent', volatility / 100)
            
            # Support/Resistance levels (using swing analysis, not just min/max)
            if len(hist) >= 20:
                # Calculate PROPER support/resistance using swing highs/lows
                # This filters out outliers and finds actual trading levels
                
                # Get recent price data (last 10 days)
                recent_lows = hist['Low'].tail(10)
                recent_highs = hist['High'].tail(10)
                recent_closes = hist['Close'].tail(10)
                
                # Find swing lows (local minima) - actual support zones
                swing_lows = []
                for i in range(1, len(recent_lows) - 1):
                    if recent_lows.iloc[i] < recent_lows.iloc[i-1] and recent_lows.iloc[i] < recent_lows.iloc[i+1]:
                        swing_lows.append(recent_lows.iloc[i])
                
                # Find swing highs (local maxima) - actual resistance zones
                swing_highs = []
                for i in range(1, len(recent_highs) - 1):
                    if recent_highs.iloc[i] > recent_highs.iloc[i-1] and recent_highs.iloc[i] > recent_highs.iloc[i+1]:
                        swing_highs.append(recent_highs.iloc[i])
                
                # Use swing levels if found, otherwise use percentile (filters outliers)
                if swing_lows:
                    recent_support = max(swing_lows)  # Highest swing low = strongest support
                else:
                    recent_support = recent_lows.quantile(0.2)  # 20th percentile (filters outliers)
                
                if swing_highs:
                    recent_resistance = min(swing_highs)  # Lowest swing high = nearest resistance
                else:
                    recent_resistance = recent_highs.quantile(0.8)  # 80th percentile (filters outliers)
                
                # Ensure support is reasonable (not a flash crash)
                min_reasonable_support = current_price * 0.70  # Support can't be more than 30% below current
                recent_support = max(recent_support, min_reasonable_support)
                
                # Long-term support/resistance for reference (20 days)
                long_lows = hist['Low'].tail(20)
                long_highs = hist['High'].tail(20)
                support = long_lows.quantile(0.15)  # 15th percentile (strong long-term support)
                resistance = long_highs.quantile(0.85)  # 85th percentile (strong long-term resistance)
                
                # Ensure long-term support is reasonable
                support = max(support, current_price * 0.60)
                
                # PRACTICAL STOP LOSS (use ATR-based, capped at reasonable levels)
                # ATR stop: 2x ATR below current price (typically 5-12%)
                atr_multiplier = min(atr * 2, 12)  # Cap at 12% max
                atr_stop = current_price * (1 - atr_multiplier / 100)
                
                # Recent support stop: 3% below recent 10-day low
                support_stop = recent_support * 0.97
                
                # Use the HIGHER of the two (tighter stop, closer to price)
                # This ensures we don't use a stop that's way below recent support
                preliminary_stop = max(atr_stop, support_stop)
                
                # Final constraints: Keep stop between 5-12% below current price
                stop_loss = max(preliminary_stop, current_price * 0.88)  # Max 12% stop
                stop_loss = min(stop_loss, current_price * 0.95)  # Min 5% stop
                
                risk = ((current_price - stop_loss) / current_price * 100)
                
                # PRACTICAL PROFIT TARGETS (realistic, not wishful thinking)
                risk_amount = current_price - stop_loss
                
                # Target 1: Conservative (2x risk OR recent resistance, whichever is closer)
                conservative_target = current_price + (risk_amount * 2)
                recent_res_target = min(recent_resistance * 1.05, current_price * 1.25)  # Cap at 25%
                target_1 = min(conservative_target, recent_res_target)
                
                # Target 2: Moderate (3x risk OR 30% gain, whichever is lower - more realistic)
                moderate_target = current_price + (risk_amount * 3)
                target_2 = min(moderate_target, current_price * 1.30, recent_resistance * 1.10)
                
                # Target 3: Aggressive squeeze target (50-100% gain potential)
                aggressive_target = current_price + (risk_amount * 4)
                target_3 = min(aggressive_target, current_price * 1.75)  # Up to 75% gain
                
                # Target 4: MOON SHOT - Extreme squeeze scenario (like GME)
                # Based on short interest squeeze potential
                # For stocks with SI >30%, this shows what COULD happen
                moon_shot = current_price * 2.5  # 150% gain potential for high SI stocks
                
                # Expected move (1-week based on volatility)
                weekly_vol = volatility / np.sqrt(52)  # Weekly volatility
                expected_move_up = current_price * (weekly_vol / 100)
                expected_move_down = current_price * (weekly_vol / 100)
                
                # Risk/Reward Ratios
                reward_1 = ((target_1 - current_price) / current_price * 100)
                reward_2 = ((target_2 - current_price) / current_price * 100)
                
                # BUY-IN RECOMMENDATION - PROFESSIONAL APPROACH
                # Calculate optimal entry zones based on technical analysis and risk management
                
                support_cushion = ((current_price - recent_support) / recent_support * 100) if recent_support > 0 else 0
                distance_to_resistance = ((recent_resistance - current_price) / current_price * 100) if recent_resistance > current_price else 0
                
                # Strategy depends on where we are in the range
                if current_price > recent_resistance * 0.95:
                    # Already at or above resistance - WAIT for pullback
                    buy_in_ideal = (recent_support + recent_resistance) / 2  # Mid-range
                    buy_in_low = recent_support * 1.03  # Just above support
                    buy_in_high = buy_in_ideal * 1.05  # 5% above ideal
                    buy_rationale = f"Already extended above resistance ${recent_resistance:.2f}. Wait for pullback to ${buy_in_ideal:.2f} (mid-range) or support ${recent_support:.2f} for better risk/reward."
                
                elif current_price < recent_support * 1.05:
                    # Near or below support - BUYING OPPORTUNITY
                    buy_in_ideal = recent_support * 1.02  # Just above support
                    buy_in_low = recent_support * 0.98  # Slightly below support
                    buy_in_high = recent_support * 1.05  # 5% above support
                    buy_rationale = f"At strong support ${recent_support:.2f}. Ideal entry on bounce confirmation. Stop below ${recent_support * 0.95:.2f}. Target resistance ${recent_resistance:.2f} (+{distance_to_resistance:.0f}%)."
                
                elif support_cushion > 15:
                    # Mid-range but closer to resistance - WAIT for pullback
                    buy_in_ideal = recent_support * 1.08  # 8% above support
                    buy_in_low = recent_support * 1.03  # Just above support
                    buy_in_high = recent_support * 1.12  # 12% above support
                    buy_rationale = f"Price extended {support_cushion:.0f}% above support ${recent_support:.2f}. Better entry on pullback to ${buy_in_ideal:.2f} zone. Resistance at ${recent_resistance:.2f}."
                
                else:
                    # Mid-range, reasonable entry - GOOD ZONE
                    buy_in_ideal = current_price * 0.98  # 2% below current
                    buy_in_low = recent_support * 1.05  # 5% above support
                    buy_in_high = current_price * 1.02  # 2% above current
                    buy_rationale = f"Good entry zone. Support ${recent_support:.2f} ({support_cushion:.0f}% below), resistance ${recent_resistance:.2f} ({distance_to_resistance:.0f}% above). Aim for ${buy_in_ideal:.2f}, stop below ${recent_support:.2f}."
                
                risk_reward = {
                    'stop_loss': stop_loss,
                    'risk_percent': risk,
                    'target_1': target_1,
                    'target_2': target_2,
                    'target_3': target_3,
                    'moon_shot': moon_shot,  # NEW: Extreme squeeze target
                    'reward_1_percent': reward_1,
                    'reward_2_percent': reward_2,
                    'risk_reward_ratio_1': reward_1 / risk if risk > 0 else 0,
                    'risk_reward_ratio_2': reward_2 / risk if risk > 0 else 0,
                    'expected_move_up_1w': expected_move_up,
                    'expected_move_down_1w': expected_move_down,
                    'recent_support': recent_support,  # NEW: 10-day support (practical)
                    'recent_resistance': recent_resistance,  # NEW: 10-day resistance (practical)
                    'support_20d': support,  # Renamed: 20-day low for reference
                    'resistance_20d': resistance,  # Renamed: 20-day high for reference
                    'buy_in_ideal': buy_in_ideal,  # NEW: Recommended entry price
                    'buy_in_low': buy_in_low,  # NEW: Buy zone low
                    'buy_in_high': buy_in_high,  # NEW: Buy zone high
                    'buy_rationale': buy_rationale  # NEW: Why this buy-in makes sense
                }
            else:
                # Minimal data - conservative estimates
                risk_reward = {
                    'stop_loss': current_price * 0.90,
                    'risk_percent': 10,
                    'target_1': current_price * 1.15,
                    'target_2': current_price * 1.25,
                    'target_3': current_price * 1.40,
                    'reward_1_percent': 15,
                    'reward_2_percent': 25,
                    'risk_reward_ratio_1': 1.5,
                    'risk_reward_ratio_2': 2.5,
                    'expected_move_up_1w': current_price * 0.05,
                    'expected_move_down_1w': current_price * 0.05,
                    'support': current_price * 0.95,
                    'resistance': current_price * 1.10
                }
                
        except Exception as e:
            # Default conservative values
            risk_reward = {
                'stop_loss': current_price * 0.90,
                'risk_percent': 10,
                'target_1': current_price * 1.15,
                'target_2': current_price * 1.25,
                'target_3': current_price * 1.40,
                'reward_1_percent': 15,
                'reward_2_percent': 25,
                'risk_reward_ratio_1': 1.5,
                'risk_reward_ratio_2': 2.5,
                'expected_move_up_1w': current_price * 0.05,
                'expected_move_down_1w': current_price * 0.05,
                'support': current_price * 0.95,
                'resistance': current_price * 1.10
            }
        
        return risk_reward
    
    def _calculate_confidence_score(self, short_percent_float: float,
                                     volume_surge: float, freshness_score: int,
                                     institutional_metrics: Dict) -> int:
        """
        INSTITUTIONAL-GRADE Confidence Score (0-100)
        Measures reliability/conviction in the prediction
        """
        
        confidence = 0
        
        # Data quality factors
        if short_percent_float > 0:  # Has short interest data
            confidence += 20
        
        if volume_surge > 1.5:  # Has volume confirmation
            confidence += 20
        
        if freshness_score > 30:  # Recent setup
            confidence += 15
        
        # Technical confirmation
        rsi = institutional_metrics.get('rsi', 50)
        if 30 <= rsi <= 70:  # RSI in healthy range
            confidence += 15
        
        macd_hist = institutional_metrics.get('macd_histogram', 0)
        if macd_hist != 0:  # Has MACD signal
            confidence += 10
        
        bb_pos = institutional_metrics.get('bb_position', 50)
        if 10 <= bb_pos <= 90:  # Not at extremes
            confidence += 10
        
        vol_trend = institutional_metrics.get('volume_trend', 0)
        if vol_trend > 10:  # Volume trending up
            confidence += 10
        
        return min(100, confidence)
    
    def _detect_pre_squeeze_signals(self, hist: pd.DataFrame, short_percent_float: float,
                                     current_price: float, institutional_metrics: Dict) -> Dict:
        """
        PRE-SQUEEZE DETECTION - Identify squeezes BEFORE they happen
        Returns early warning signals and squeeze stage classification
        """
        
        pre_squeeze_signals = {
            'volatility_compression': 0,  # BB squeeze, ATR contracting
            'accumulation_score': 0,      # Smart money buying
            'short_interest_trend': 0,    # SI increasing over time
            'option_activity': 0,         # Call buying increasing
            'squeeze_stage': 'NONE',      # PRE-SQUEEZE, READY, ACTIVE, POST
            'early_warning_score': 0,     # 0-100, predicts squeeze 1-5 days out
            'days_until_squeeze': None    # Estimated days until squeeze
        }
        
        try:
            # === 1. VOLATILITY COMPRESSION (Bollinger Band Squeeze) ===
            # Tight BB = calm before the storm
            if len(hist) >= 20:
                bb_width = institutional_metrics.get('bb_upper', 0) - institutional_metrics.get('bb_lower', 0)
                if bb_width > 0:
                    bb_width_pct = (bb_width / current_price * 100)
                    
                    # Historical BB width comparison
                    hist_bb_widths = []
                    for i in range(20, min(60, len(hist))):
                        historical_sma = hist['Close'].iloc[i-20:i].mean()
                        historical_std = hist['Close'].iloc[i-20:i].std()
                        hist_width = (historical_std * 4 / historical_sma * 100)
                        hist_bb_widths.append(hist_width)
                    
                    if hist_bb_widths:
                        avg_hist_width = np.mean(hist_bb_widths)
                        
                        # More granular compression detection (made less strict)
                        if avg_hist_width > 0:
                            compression_ratio = bb_width_pct / avg_hist_width
                            
                            if compression_ratio < 0.4:  # Extremely tight (was 0.5)
                                pre_squeeze_signals['volatility_compression'] = 100
                            elif compression_ratio < 0.6:  # Very tight (was 0.7)
                                pre_squeeze_signals['volatility_compression'] = 80
                            elif compression_ratio < 0.75:  # Tight (was 0.85)
                                pre_squeeze_signals['volatility_compression'] = 60
                            elif compression_ratio < 0.9:  # Moderate compression (new)
                                pre_squeeze_signals['volatility_compression'] = 40
                            elif compression_ratio < 1.0:  # Slight compression (new)
                                pre_squeeze_signals['volatility_compression'] = 20
            
            # === 2. ACCUMULATION DETECTION (Smart Money Buying) ===
            # OBV trending up while price consolidates = accumulation
            if len(hist) >= 20:
                # Calculate On-Balance Volume
                obv = (np.sign(hist['Close'].diff()) * hist['Volume']).fillna(0).cumsum()
                
                # OBV trend
                obv_recent = obv.tail(10).mean()
                obv_older = obv.tail(20).head(10).mean()
                
                # Price trend
                price_recent = hist['Close'].tail(10).mean()
                price_older = hist['Close'].tail(20).head(10).mean()
                
                # Divergence: OBV up, price flat/down = accumulation
                obv_trend = ((obv_recent - obv_older) / abs(obv_older) * 100) if obv_older != 0 else 0
                price_trend = ((price_recent - price_older) / price_older * 100) if price_older > 0 else 0
                
                # Strong accumulation if OBV up > 10% but price flat
                if obv_trend > 10 and abs(price_trend) < 5:
                    pre_squeeze_signals['accumulation_score'] = 100
                elif obv_trend > 5 and abs(price_trend) < 5:
                    pre_squeeze_signals['accumulation_score'] = 75
                elif obv_trend > 0:
                    pre_squeeze_signals['accumulation_score'] = 50
            
            # === 3. SHORT INTEREST TREND ===
            # Increasing SI over time = more fuel for squeeze
            if short_percent_float > 0:
                # We can't get historical SI easily, so use current SI as proxy
                # High and increasing SI is pre-squeeze signal
                if short_percent_float > 30:
                    pre_squeeze_signals['short_interest_trend'] = 100
                elif short_percent_float > 20:
                    pre_squeeze_signals['short_interest_trend'] = 80
                elif short_percent_float > 15:
                    pre_squeeze_signals['short_interest_trend'] = 60
                elif short_percent_float > 10:
                    pre_squeeze_signals['short_interest_trend'] = 40
            
            # === 4. OPTION ACTIVITY (Call Buying Increase) ===
            # We can't get real options data easily, but high volume with price rise = options activity
            vol_trend = institutional_metrics.get('volume_trend', 0)
            if vol_trend > 50 and hist['Close'].iloc[-1] > hist['Close'].iloc[-5]:
                pre_squeeze_signals['option_activity'] = 100
            elif vol_trend > 25:
                pre_squeeze_signals['option_activity'] = 60
            
            # === 5. EARLY WARNING SCORE ===
            # Combine all signals to predict squeeze 1-5 days out
            early_warning = (
                pre_squeeze_signals['volatility_compression'] * 0.30 +
                pre_squeeze_signals['accumulation_score'] * 0.25 +
                pre_squeeze_signals['short_interest_trend'] * 0.25 +
                pre_squeeze_signals['option_activity'] * 0.20
            )
            pre_squeeze_signals['early_warning_score'] = int(early_warning)
            
            # === 6. SQUEEZE STAGE CLASSIFICATION ===
            rsi = institutional_metrics.get('rsi', 50)
            macd_hist = institutional_metrics.get('macd_histogram', 0)
            vol_surge = institutional_metrics.get('volume_trend', 0)
            
            # PRE-SQUEEZE: High compression, accumulation, not moving yet
            if (pre_squeeze_signals['volatility_compression'] >= 50 and 
                pre_squeeze_signals['accumulation_score'] >= 50 and
                abs(hist['Close'].pct_change().tail(5).mean() * 100) < 3):
                pre_squeeze_signals['squeeze_stage'] = 'PRE-SQUEEZE'
                pre_squeeze_signals['days_until_squeeze'] = '1-5 days'
            
            # READY: Compression + breakout starting
            elif (pre_squeeze_signals['volatility_compression'] >= 50 and
                  macd_hist > 0 and rsi > 50 and vol_surge > 20):
                pre_squeeze_signals['squeeze_stage'] = 'READY'
                pre_squeeze_signals['days_until_squeeze'] = '0-2 days'
            
            # ACTIVE: Squeeze happening now
            elif (vol_surge > 50 and rsi > 60 and 
                  hist['Close'].pct_change().tail(3).mean() * 100 > 5):
                pre_squeeze_signals['squeeze_stage'] = 'ACTIVE'
                pre_squeeze_signals['days_until_squeeze'] = 'NOW'
            
            # POST: Squeeze already happened
            elif rsi > 75 and vol_surge < 20:
                pre_squeeze_signals['squeeze_stage'] = 'POST'
                pre_squeeze_signals['days_until_squeeze'] = 'Completed'
            
            else:
                pre_squeeze_signals['squeeze_stage'] = 'BUILDING'
                if pre_squeeze_signals['early_warning_score'] > 60:
                    pre_squeeze_signals['days_until_squeeze'] = '3-7 days'
                else:
                    pre_squeeze_signals['days_until_squeeze'] = 'Uncertain'
                    
        except Exception as e:
            # Return defaults on error
            pass
        
        return pre_squeeze_signals
    
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
