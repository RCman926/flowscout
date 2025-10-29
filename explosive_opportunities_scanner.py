"""
Explosive Opportunities Market Scanner
Scans entire market for unusual activity, volume spikes, and explosive moves
Uses IBKR for real-time data when available
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from typing import List, Dict, Optional
import asyncio

class ExplosiveOpportunitiesScanner:
    def __init__(self):
        self.cache = {}
        self.cache_expiry = {}
        self.cache_duration = 60  # 60 second cache for scanner results
        
        # Lazy-load scan universe to prevent page blocking
        self._scan_universe = None
    
    @property
    def scan_universe(self) -> List[str]:
        """Lazy-load scan universe only when needed"""
        if self._scan_universe is None:
            self._scan_universe = self._build_comprehensive_universe()
        return self._scan_universe
    
    @scan_universe.setter
    def scan_universe(self, value: List[str]):
        """Allow setting scan universe"""
        self._scan_universe = value
        
    def _build_comprehensive_universe(self) -> List[str]:
        """Build comprehensive scan universe with 300+ symbols"""
        symbols = []
        
        # Major Indices & ETFs (10)
        symbols.extend(['SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VOO', 'VXX', 'UVXY', 'SQQQ', 'TQQQ'])
        
        # Mega Cap Tech (15)
        symbols.extend(['AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'NVDA', 'TSLA', 'NFLX', 'ADBE', 'CRM', 'ORCL', 'CSCO', 'INTC', 'AVGO'])
        
        # AI & Semiconductor (25)
        symbols.extend(['AMD', 'TSM', 'ASML', 'QCOM', 'MU', 'AMAT', 'LRCX', 'KLAC', 'MRVL', 'MCHP', 'NXPI', 'TXN', 'ADI', 'ARM', 'SMCI', 'IONQ', 'QUBT', 'RGTI', 'SOUN', 'BBAI', 'AI', 'PLTR', 'SNOW', 'PATH', 'DDOG'])
        
        # Crypto & Blockchain (20)
        symbols.extend(['BTC-USD', 'ETH-USD', 'COIN', 'MARA', 'RIOT', 'CLSK', 'CIFR', 'HUT', 'BITF', 'MSTR', 'SQ', 'PYPL', 'HOOD', 'SOFI', 'AFRM', 'UPST', 'DOGE-USD', 'ADA-USD', 'SOL-USD', 'XRP-USD'])
        
        # Meme/Squeeze Stocks (30)
        symbols.extend(['GME', 'AMC', 'BBBY', 'BYND', 'CLOV', 'WISH', 'SKLZ', 'WKHS', 'RIDE', 'SPCE', 'IRNT', 'ATER', 'BBIG', 'PROG', 'CEI', 'GREE', 'RDBX', 'MULN', 'GRRR', 'RZLV', 'AVCT', 'NILE', 'RELI', 'IMPP', 'SST', 'ENDP', 'APRN', 'ENVB', 'DRUG', 'MEGL'])
        
        # Small Cap High Vol (50)
        symbols.extend(['SOXL', 'SOXS', 'LABU', 'LABD', 'TQQQ', 'SQQQ', 'UPRO', 'SPXU', 'FNGU', 'FNGD', 'TECL', 'TECS', 'NAIL', 'DUST', 'NUGT', 'JNUG', 'JDST', 'ERX', 'ERY', 'UCO', 'SCO', 'BOIL', 'KOLD', 'GUSH', 'DRIP', 'TNA', 'TZA', 'CURE', 'CRSP', 'EDIT', 'NTLA', 'BEAM', 'VRTX', 'MRNA', 'BNTX', 'NVAX', 'SAVA', 'RLYB', 'SRNE', 'INO', 'OCGN', 'ATOS', 'ATNF', 'DTST', 'PSTV', 'VKTX', 'AFMD', 'ALPP', 'BKKT', 'RCAT'])
        
        # EV & Clean Energy (25)
        symbols.extend(['LCID', 'RIVN', 'NIO', 'XPEV', 'LI', 'FSR', 'NKLA', 'GOEV', 'RIDE', 'WKHS', 'HYLN', 'BLNK', 'CHPT', 'PLUG', 'FCEL', 'BE', 'QS', 'ENPH', 'SEDG', 'RUN', 'NOVA', 'ARRY', 'SPWR', 'CSIQ', 'JKS'])
        
        # Biotech Small Caps (40)
        symbols.extend(['GILD', 'BIIB', 'REGN', 'VRTX', 'ALNY', 'BMRN', 'EXEL', 'IONS', 'JAZZ', 'INCY', 'UTHR', 'RGEN', 'FOLD', 'ARWR', 'RARE', 'BLUE', 'SAGE', 'ALLK', 'NBIX', 'ACAD', 'HALO', 'KRYS', 'APLS', 'RVMD', 'RVNC', 'CGEM', 'ARQT', 'KYMR', 'RCKT', 'LEGN', 'JANX', 'KURA', 'TGTX', 'FATE', 'DNLI', 'RXRX', 'SDGR', 'VERV', 'PRME', 'LYEL'])
        
        # High Beta Tech (25)
        symbols.extend(['SNAP', 'PINS', 'RBLX', 'DASH', 'ABNB', 'LYFT', 'UBER', 'Z', 'OPEN', 'WISH', 'CPNG', 'SE', 'MELI', 'SHOP', 'SQ', 'ROKU', 'DKNG', 'PENN', 'FUBO', 'SKLZ', 'TTWO', 'EA', 'RBLX', 'U', 'NET'])
        
        # Penny Stocks/OTC Style (30)
        symbols.extend(['SNDL', 'NAKD', 'BNGO', 'ZOM', 'HITIF', 'TLRY', 'ACB', 'CGC', 'CRON', 'APHA', 'HEXO', 'OGI', 'KERN', 'VERU', 'ONTX', 'IDEX', 'GEVO', 'PLUG', 'SOLO', 'WKHS', 'CLNE', 'BLNK', 'AYRO', 'NNDM', 'MARK', 'KODK', 'SINT', 'GNUS', 'XELA', 'HOFV'])
        
        # SPACs & Recent IPOs (20)
        symbols.extend(['PSTH', 'IPOF', 'IPOD', 'CCIV', 'SOFI', 'OPEN', 'DNA', 'IONQ', 'RKLB', 'BROS', 'RIVN', 'LCID', 'GRAB', 'BIRD', 'VLD', 'CURI', 'BGRY', 'GENI', 'SKIN', 'ZEV'])
        
        # Chinese Tech (15)
        symbols.extend(['BABA', 'JD', 'PDD', 'BIDU', 'NIO', 'XPEV', 'LI', 'BILI', 'IQ', 'YUMC', 'BEKE', 'TME', 'DIDI', 'TAL', 'EDU'])
        
        # Finance & Fintech (15)
        symbols.extend(['JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'SCHW', 'BLK', 'V', 'MA', 'AXP', 'SQ', 'PYPL', 'AFRM', 'UPST'])
        
        # Energy & Commodities (15)
        symbols.extend(['XOM', 'CVX', 'COP', 'EOG', 'SLB', 'HAL', 'OXY', 'DVN', 'FANG', 'MRO', 'APA', 'CLR', 'SM', 'RIG', 'VAL'])
        
        # Retail & Consumer (10)
        symbols.extend(['WMT', 'TGT', 'COST', 'HD', 'LOW', 'BBY', 'DG', 'DLTR', 'FIVE', 'OLLI'])
        
        return list(set(symbols))  # Remove duplicates
    
    def discover_new_symbols(self) -> List[str]:
        """
        Dynamically discover new high-potential symbols based on:
        - Top gainers
        - Top volume leaders  
        - Recently listed stocks
        """
        discovered = []
        
        try:
            # Method 1: Scan through a broader range of tickers to find active ones
            # Using common ticker patterns for small caps
            potential_symbols = []
            
            # Generate potential small cap tickers (common patterns)
            for letter1 in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                for letter2 in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                    for letter3 in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                        if len(potential_symbols) < 100:  # Limit to 100 checks per scan
                            potential_symbols.append(f"{letter1}{letter2}{letter3}")
            
            # Quick check which ones are valid and active
            for symbol in potential_symbols[:50]:  # Check first 50
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period='1d')
                    if not hist.empty:
                        volume = hist['Volume'].iloc[-1]
                        price = hist['Close'].iloc[-1]
                        # Look for small caps with good volume
                        if volume > 100000 and 0.50 < price < 50:
                            discovered.append(symbol)
                except:
                    continue
            
            print(f"✅ Discovered {len(discovered)} new active symbols")
            
        except Exception as e:
            print(f"Symbol discovery error: {e}")
        
        return discovered
    
    def auto_expand_universe(self):
        """Automatically expand scan universe with newly discovered symbols"""
        try:
            new_symbols = self.discover_new_symbols()
            
            # Add to universe if not already present
            added = 0
            for symbol in new_symbols:
                if symbol not in self.scan_universe:
                    self.scan_universe.append(symbol)
                    added += 1
            
            if added > 0:
                print(f"✅ Auto-added {added} new symbols to scan universe (Total: {len(self.scan_universe)})")
                # Update cache with new universe
                self.cache['scan_universe'] = self.scan_universe
                self.cache_expiry['scan_universe'] = datetime.now() + timedelta(hours=24)
            
            return added
        except Exception as e:
            print(f"Auto-expand error: {e}")
            return 0
        
    def _is_cache_valid(self, key):
        """Check if cached data is still valid"""
        return (key in self.cache and 
                key in self.cache_expiry and 
                datetime.now() < self.cache_expiry[key])
                
    def _update_cache(self, key, data):
        """Update cache with new data"""
        self.cache[key] = data
        self.cache_expiry[key] = datetime.now() + timedelta(seconds=self.cache_duration)
    
    def scan_for_explosive_moves(self, min_volume_spike: float = 2.0, 
                                      min_price_move: float = 3.0) -> List[Dict]:
        """
        Scan market for explosive opportunities (SYNCHRONOUS for Streamlit)
        
        Args:
            min_volume_spike: Minimum volume spike multiplier (default 2.0x average)
            min_price_move: Minimum price move % (default 3%)
        
        Returns:
            List of explosive opportunities with scores
        """
        cache_key = f"explosive_scan_{min_volume_spike}_{min_price_move}"
        
        # Check cache
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        opportunities = []
        
        print(f"🔍 Scanning {len(self.scan_universe)} symbols for explosive moves...")
        
        for symbol in self.scan_universe:
            try:
                opportunity = self._analyze_symbol_for_explosive_move(
                    symbol, min_volume_spike, min_price_move
                )
                if opportunity:
                    opportunities.append(opportunity)
            except Exception as e:
                continue
        
        # Sort by explosive score (highest first)
        opportunities.sort(key=lambda x: x['explosive_score'], reverse=True)
        
        # Cache results
        self._update_cache(cache_key, opportunities)
        
        print(f"✅ Found {len(opportunities)} explosive opportunities")
        return opportunities
    
    def _analyze_symbol_for_explosive_move(self, symbol: str, 
                                                 min_volume_spike: float,
                                                 min_price_move: float) -> Optional[Dict]:
        """Analyze single symbol for explosive characteristics"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Get recent data
            hist = ticker.history(period='5d', interval='1d')
            if len(hist) < 3:
                return None
            
            # Get intraday data for volume analysis
            intraday = ticker.history(period='1d', interval='5m')
            
            # Calculate metrics
            current_price = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2]
            price_change_pct = ((current_price - prev_close) / prev_close) * 100
            
            current_volume = hist['Volume'].iloc[-1]
            avg_volume = hist['Volume'].iloc[:-1].mean()
            volume_spike = current_volume / avg_volume if avg_volume > 0 else 0
            
            # Check if meets explosive criteria
            is_explosive_price = abs(price_change_pct) >= min_price_move
            is_explosive_volume = volume_spike >= min_volume_spike
            
            if not (is_explosive_price or is_explosive_volume):
                return None
            
            # Calculate explosive score (0-100)
            price_score = min(abs(price_change_pct) * 2, 50)
            volume_score = min(volume_spike * 10, 50)
            explosive_score = price_score + volume_score
            
            # Get additional metrics
            info = ticker.info
            
            # Determine move type
            if price_change_pct > 0:
                move_type = "🚀 PUMP"
                direction = "BULLISH"
            else:
                move_type = "💥 DUMP"
                direction = "BEARISH"
            
            # Intraday momentum
            if not intraday.empty and len(intraday) > 5:
                recent_high = intraday['High'].max()
                recent_low = intraday['Low'].min()
                intraday_range_pct = ((recent_high - recent_low) / recent_low) * 100
            else:
                intraday_range_pct = abs(price_change_pct)
            
            opportunity = {
                'symbol': symbol,
                'explosive_score': round(explosive_score, 1),
                'price': round(current_price, 2),
                'price_change_pct': round(price_change_pct, 2),
                'volume': int(current_volume),
                'avg_volume': int(avg_volume),
                'volume_spike': round(volume_spike, 2),
                'move_type': move_type,
                'direction': direction,
                'intraday_range_pct': round(intraday_range_pct, 2),
                'market_cap': info.get('marketCap', 0),
                'alert_level': self._get_alert_level(explosive_score),
                'timestamp': datetime.now()
            }
            
            return opportunity
            
        except Exception as e:
            return None
    
    def _get_alert_level(self, explosive_score: float) -> str:
        """Determine alert level based on explosive score"""
        if explosive_score >= 80:
            return "🔥 EXTREME"
        elif explosive_score >= 60:
            return "⚡ HIGH"
        elif explosive_score >= 40:
            return "⚠️ MODERATE"
        else:
            return "📊 MILD"
    
    def scan_for_volume_breakouts(self, min_multiplier: float = 3.0) -> List[Dict]:
        """Scan for unusual volume breakouts (SYNCHRONOUS for Streamlit)"""
        cache_key = f"volume_breakouts_{min_multiplier}"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        breakouts = []
        
        print(f"🔍 Scanning for volume breakouts (>{min_multiplier}x average)...")
        
        for symbol in self.scan_universe:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period='10d')
                
                if len(hist) < 5:
                    continue
                
                current_volume = hist['Volume'].iloc[-1]
                avg_volume_10d = hist['Volume'].iloc[:-1].mean()
                
                volume_multiplier = current_volume / avg_volume_10d if avg_volume_10d > 0 else 0
                
                if volume_multiplier >= min_multiplier:
                    current_price = hist['Close'].iloc[-1]
                    prev_close = hist['Close'].iloc[-2]
                    price_change_pct = ((current_price - prev_close) / prev_close) * 100
                    
                    breakouts.append({
                        'symbol': symbol,
                        'price': round(current_price, 2),
                        'volume': int(current_volume),
                        'avg_volume': int(avg_volume_10d),
                        'volume_multiplier': round(volume_multiplier, 2),
                        'price_change_pct': round(price_change_pct, 2),
                        'breakout_strength': round(volume_multiplier * 10, 1),
                        'timestamp': datetime.now()
                    })
            except:
                continue
        
        # Sort by volume multiplier
        breakouts.sort(key=lambda x: x['volume_multiplier'], reverse=True)
        
        self._update_cache(cache_key, breakouts)
        
        print(f"✅ Found {len(breakouts)} volume breakouts")
        return breakouts
    
    def scan_for_momentum_plays(self, min_consecutive_days: int = 3) -> List[Dict]:
        """Scan for multi-day momentum plays (SYNCHRONOUS for Streamlit)"""
        cache_key = f"momentum_plays_{min_consecutive_days}"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        momentum_plays = []
        
        print(f"🔍 Scanning for {min_consecutive_days}+ day momentum plays...")
        
        for symbol in self.scan_universe:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period='10d')
                
                if len(hist) < min_consecutive_days + 1:
                    continue
                
                # Check for consecutive green/red days
                closes = hist['Close'].values
                consecutive_up = 0
                consecutive_down = 0
                
                for i in range(len(closes) - 1, 0, -1):
                    if closes[i] > closes[i-1]:
                        consecutive_up += 1
                        consecutive_down = 0
                    elif closes[i] < closes[i-1]:
                        consecutive_down += 1
                        consecutive_up = 0
                    else:
                        break
                
                if consecutive_up >= min_consecutive_days or consecutive_down >= min_consecutive_days:
                    current_price = closes[-1]
                    start_price = closes[-max(consecutive_up, consecutive_down)-1]
                    total_move_pct = ((current_price - start_price) / start_price) * 100
                    
                    momentum_plays.append({
                        'symbol': symbol,
                        'price': round(current_price, 2),
                        'consecutive_days': max(consecutive_up, consecutive_down),
                        'direction': 'UP' if consecutive_up > 0 else 'DOWN',
                        'total_move_pct': round(total_move_pct, 2),
                        'momentum_strength': round(abs(total_move_pct) * max(consecutive_up, consecutive_down), 1),
                        'timestamp': datetime.now()
                    })
            except:
                continue
        
        # Sort by momentum strength
        momentum_plays.sort(key=lambda x: x['momentum_strength'], reverse=True)
        
        self._update_cache(cache_key, momentum_plays)
        
        print(f"✅ Found {len(momentum_plays)} momentum plays")
        return momentum_plays
    
    def get_hot_sector_rotation(self) -> Dict:
        """Identify hot sectors with money rotation (SYNCHRONOUS for Streamlit)"""
        cache_key = "sector_rotation"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        sectors = {
            'Technology': 'XLK',
            'Financial': 'XLF',
            'Healthcare': 'XLV',
            'Energy': 'XLE',
            'Consumer Discretionary': 'XLY',
            'Industrials': 'XLI',
            'Communication': 'XLC',
            'Consumer Staples': 'XLP',
            'Utilities': 'XLU',
            'Real Estate': 'XLRE',
            'Materials': 'XLB'
        }
        
        sector_performance = []
        
        for sector_name, etf in sectors.items():
            try:
                ticker = yf.Ticker(etf)
                hist = ticker.history(period='5d')
                
                if len(hist) < 2:
                    continue
                
                current_price = hist['Close'].iloc[-1]
                week_ago_price = hist['Close'].iloc[0]
                week_change_pct = ((current_price - week_ago_price) / week_ago_price) * 100
                
                current_volume = hist['Volume'].iloc[-1]
                avg_volume = hist['Volume'].mean()
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
                
                sector_performance.append({
                    'sector': sector_name,
                    'etf': etf,
                    'price': round(current_price, 2),
                    'week_change_pct': round(week_change_pct, 2),
                    'volume_ratio': round(volume_ratio, 2),
                    'strength': round(week_change_pct * volume_ratio, 2)
                })
            except:
                continue
        
        # Sort by strength
        sector_performance.sort(key=lambda x: x['strength'], reverse=True)
        
        result = {
            'hot_sectors': sector_performance[:3],
            'cold_sectors': sector_performance[-3:],
            'all_sectors': sector_performance,
            'timestamp': datetime.now()
        }
        
        self._update_cache(cache_key, result)
        
        return result

# Global scanner instance
explosive_scanner = ExplosiveOpportunitiesScanner()
