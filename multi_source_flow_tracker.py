"""
Multi-Source 0DTE Flow Tracker
Tries multiple data sources in priority order:
1. IBKR (best - real-time)
2. Polygon/Massive (professional)
3. Finnhub (good free tier)
4. Alpha Vantage (if available)
5. yfinance (fallback)
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import logging
import json
import os

logger = logging.getLogger(__name__)


def resolve_yfinance_marks(ticker, session: str = "REGULAR") -> Dict[str, float]:
    """
    Resolve display marks from Yahoo.

    Outside regular hours, prefer the official session close (regularMarketPrice /
    daily Close) — NOT the last 1-minute bar, which often differs by a few cents
    (e.g. 746.81 vs official 747.03).
    """
    regular_close = 0.0
    last_1m = 0.0
    post_market = 0.0
    pre_market = 0.0

    try:
        daily = ticker.history(period="5d", interval="1d")
        if daily is not None and not daily.empty:
            regular_close = float(daily["Close"].iloc[-1])
    except Exception as e:
        logger.debug(f"Daily close fetch failed: {e}")

    try:
        info = ticker.info or {}
        rmp = info.get("regularMarketPrice")
        if rmp:
            # Prefer Yahoo's official regular-session mark when available
            regular_close = float(rmp) or regular_close
        pm = info.get("postMarketPrice")
        if pm:
            post_market = float(pm)
        pre = info.get("preMarketPrice")
        if pre:
            pre_market = float(pre)
    except Exception as e:
        logger.debug(f"Ticker info marks failed: {e}")

    session_u = (session or "REGULAR").upper()
    if session_u == "REGULAR":
        try:
            m1 = ticker.history(period="1d", interval="1m")
            if m1 is not None and not m1.empty:
                last_1m = float(m1["Close"].iloc[-1])
        except Exception as e:
            logger.debug(f"1m mark fetch failed: {e}")
        stock_price = last_1m or regular_close
    else:
        # Closed / extended / weekend: show official close as the main price
        stock_price = regular_close or last_1m

    return {
        "stock_price": float(stock_price or 0),
        "regular_close": float(regular_close or stock_price or 0),
        "aftermarket_price": float(post_market or 0),
        "premarket_price": float(pre_market or 0),
        "last_1m": float(last_1m or 0),
    }


class MultiSourceFlowTracker:
    """0DTE flow tracker with multiple data source support with automatic rotation"""
    
    def __init__(self):
        self.cache = {}
        # Align with yahoo_throttle MIN_INTERVAL — avoid duplicate chain pulls
        self.cache_duration = 2.5
        self.flow_history = {}
        self.last_source_used = {}
        
        # Rotation tracking with persistent storage
        try:
            from cloud_runtime import state_path
            self.rotation_stats_file = str(state_path("api_rotation_stats.json"))
        except Exception:
            self.rotation_stats_file = "api_rotation_stats.json"
        self.source_rotation_index = {}  # Track rotation per symbol
        self.source_use_count = {}  # Track how many times each source was used (per symbol)
        self.total_source_use_count = {}  # Track total uses across all symbols
        self.rotation_interval = 3  # Soft preference sticky uses; health override jumps sooner
        self.available_sources = []  # List of available sources (checked on init)
        self.rotation_history = []  # History of rotations (last 100)
        # Health failover: source_name -> unix ts until which source is cold
        self.source_cold_until = {}
        self.source_cold_seconds = {
            'IBKR': 30,
            'Polygon': 90,
            'Finnhub': 120,
            'AlphaVantage': 180,
            'yfinance': 60,
        }
        # Entitlement / bad-key: do NOT 90s-retry forever (looks like "stuck cooling")
        self.source_plan_limited = {}  # name -> reason string
        self.plan_limited_seconds = 6 * 3600  # 6 hours
        
        # Load saved rotation stats
        self._load_rotation_stats()
        
        # Initialize available sources
        self._detect_available_sources()
        
    def primary_source(self) -> str:
        """Best source we will actually use right now (skip plan-limited / cold)."""
        warm = self._warm_sources()
        return warm[0] if warm else (self.available_sources[0] if self.available_sources else 'yfinance')

    def _detect_available_sources(self):
        """Detect which data sources are available and configured"""
        self.available_sources = []

        try:
            from cloud_runtime import allow_source_for_0dte, is_cloud_mode
            cloud = is_cloud_mode()
        except Exception:
            cloud = False

            def allow_source_for_0dte(name: str) -> bool:
                return True

        if cloud:
            # Always-on host: delayed Yahoo is the working free path.
            # IBKR stays off. Polygon/Finnhub/AV are not required.
            if allow_source_for_0dte("yfinance") and self._check_yfinance_available():
                self.available_sources.append("yfinance")
            if allow_source_for_0dte("Polygon") and self._check_polygon_available():
                self.available_sources.insert(0, "Polygon")
            if not self.available_sources:
                self.available_sources = ["yfinance"]
            logger.info(
                "Cloud 0DTE feed (priority): %s — delayed Yahoo, not live Polygon",
                ", ".join(self.available_sources),
            )
            return

        # Local Stage A: live broker → paid cloud options → secondary APIs → Yahoo last
        all_sources = [
            ('Polygon', self._check_polygon_available),
            ('Finnhub', self._check_finnhub_available),
            ('AlphaVantage', self._check_alphavantage_available),
            ('yfinance', self._check_yfinance_available),
        ]
        if os.getenv("IBKR_ENABLED", "").lower() in ("1", "true", "yes"):
            all_sources.insert(0, ('IBKR', self._check_ibkr_available))
        
        for source_name, check_func in all_sources:
            if check_func():
                self.available_sources.append(source_name)
                logger.info(f"✅ {source_name} is available")
        
        if not self.available_sources:
            logger.warning("No data sources available! Using yfinance as fallback.")
            self.available_sources = ['yfinance']
        
        logger.info(f"Available sources (priority order): {', '.join(self.available_sources)}")

    def _mark_source_plan_limited(self, source_name: str, reason: str = '') -> None:
        """Stop thrashing APIs that cannot return a usable options book on this key/plan."""
        why = reason or 'plan_limited'
        self.source_plan_limited[source_name] = why
        until = time.time() + float(self.plan_limited_seconds)
        prev = float(self.source_cold_until.get(source_name, 0) or 0)
        self.source_cold_until[source_name] = max(prev, until)
        logger.warning(
            f"🚫 {source_name} PLAN LIMITED for {self.plan_limited_seconds/3600:.0f}h — {why} "
            f"(no cool-retry loop; using next warm source)"
        )

    def _mark_source_cold(self, source_name: str, reason: str = '') -> None:
        """Temporarily remove a source from the happy path after failure / rate limit."""
        # Entitlement failures → long gate, not 90s disco
        low = (reason or '').lower()
        if any(x in low for x in ('plan', 'options basic', 'unpaid', '401', '403', 'not entitled', 'invalid api key', 'no bid/ask')):
            self._mark_source_plan_limited(source_name, reason)
            return
        if source_name in self.source_plan_limited:
            until = time.time() + float(self.plan_limited_seconds)
            prev = float(self.source_cold_until.get(source_name, 0) or 0)
            self.source_cold_until[source_name] = max(prev, until)
            return
        secs = float(self.source_cold_seconds.get(source_name, 90))
        until = time.time() + secs
        prev = float(self.source_cold_until.get(source_name, 0) or 0)
        self.source_cold_until[source_name] = max(prev, until)
        logger.warning(
            f"❄️ {source_name} marked cold for {secs:.0f}s"
            + (f" ({reason})" if reason else "")
            + " — jumping to next healthy source"
        )

    def _is_source_warm(self, source_name: str) -> bool:
        if source_name in self.source_plan_limited:
            until = float(self.source_cold_until.get(source_name, 0) or 0)
            if until > time.time():
                return False
            # Plan gate expired — allow one retry
            self.source_plan_limited.pop(source_name, None)
            self.source_cold_until.pop(source_name, None)
            return True
        until = float(self.source_cold_until.get(source_name, 0) or 0)
        if until <= 0:
            return True
        if time.time() >= until:
            self.source_cold_until.pop(source_name, None)
            return True
        return False

    def _warm_sources(self) -> list:
        """Configured sources that are not in a cold window (Yahoo always last)."""
        warm = [s for s in self.available_sources if self._is_source_warm(s)]
        if not warm:
            # Everything cold — allow Yahoo if present, else first configured
            if 'yfinance' in self.available_sources:
                return ['yfinance']
            return list(self.available_sources[:1]) or ['yfinance']
        return warm
    
    def _check_ibkr_available(self) -> bool:
        """Check if IBKR is available with REAL-TIME data (not delayed) - AUTO-CONNECTS if not connected"""
        try:
            from ibkr_client import get_ibkr_client
            ibkr = get_ibkr_client()
            
            if not ibkr:
                return False
            
            # Check connection health first
            health = ibkr.get_connection_health()
            
            # If not connected, try to connect automatically
            if not ibkr.is_connected():
                logger.info("🔌 IBKR not connected - attempting auto-connect...")
                connected = ibkr.connect(timeout=5, auto_detect_port=True)
                if connected:
                    logger.info("✅ IBKR auto-connected successfully!")
                else:
                    logger.warning("⚠️ IBKR auto-connect failed - will try again on next check")
                    return False
            
            # Check connection status and health
            if ibkr.is_connected():
                # FIXED: Check for delayed data only (error 10089) - bypass IBKR if only delayed data available
                if hasattr(ibkr, 'wrapper') and hasattr(ibkr.wrapper, 'error_messages'):
                    recent_delayed_errors = [e for e in ibkr.wrapper.error_messages[-10:] 
                                            if e.get('code') == 10089]  # Error 10089 = delayed data only
                    if recent_delayed_errors:
                        logger.info("⚠️ IBKR only has delayed data (subscription required) - bypassing IBKR, using free sources")
                        return False  # Don't use IBKR if only delayed data
                
                # Check health score - only consider unavailable if health is very poor
                if health.get('health_score', 100) < 20:
                    logger.warning(f"⚠️ IBKR connection health is poor (score: {health.get('health_score', 0)}) - may be unreliable")
                    return False
                
                logger.debug(f"✅ IBKR is connected with real-time data (health: {health.get('health_score', 100)})")
                return True
            else:
                logger.debug("❌ IBKR is not connected")
                return False
        except Exception as e:
            logger.debug(f"IBKR check error: {e}")
            return False
    
    def _check_polygon_available(self) -> bool:
        """Check if Polygon is available"""
        try:
            from config_loader import get_api_key
            api_key = get_api_key('POLYGON_API_KEY') or get_api_key('MASSIVE_API_KEY')
            if api_key and api_key not in ['your_key_here', 'your_polygon_key_here', '']:
                # Check if MassiveAPIClient is available (our custom client - preferred)
                try:
                    from massive_api_client import MassiveAPIClient
                    logger.info(f"✅ Polygon: API key found + MassiveAPIClient available")
                    return True
                except ImportError:
                    # Fallback: check if official Polygon SDK is available
                    try:
                        from polygon import RESTClient
                        logger.info(f"✅ Polygon: API key found + official SDK installed")
                        return True
                    except ImportError:
                        logger.warning(f"⚠️ Polygon: API key found but no client available")
                        logger.warning(f"   Install: pip install polygon-api-client OR ensure massive_api_client.py exists")
                        return False
            else:
                logger.debug(f"Polygon: No API key found")
            return False
        except Exception as e:
            logger.debug(f"Polygon check error: {e}")
            return False
    
    def _check_finnhub_available(self) -> bool:
        """Check if Finnhub is available"""
        try:
            from config_loader import get_api_key
            key = get_api_key('FINNHUB_API_KEY')
            if key and key not in ['your_finnhub_key_here', 'your_key_here', '']:
                logger.info(f"✅ Finnhub: API key found")
                return True
            else:
                logger.debug(f"Finnhub: No API key found")
            return False
        except Exception as e:
            logger.debug(f"Finnhub check error: {e}")
            return False
    
    def _check_alphavantage_available(self) -> bool:
        """Check if Alpha Vantage is available"""
        try:
            from config_loader import get_api_key
            key = get_api_key('ALPHA_VANTAGE_API_KEY')
            return key and key not in ['your_key_here', 'your_alpha_vantage_key_here', '']
        except:
            return False
    
    def _check_yfinance_available(self) -> bool:
        """Check if yfinance is available (always available)"""
        return True
    
    def _load_rotation_stats(self):
        """Load rotation statistics from file"""
        try:
            if os.path.exists(self.rotation_stats_file):
                with open(self.rotation_stats_file, 'r') as f:
                    data = json.load(f)
                    self.source_rotation_index = data.get('rotation_index', {})
                    self.source_use_count = data.get('use_count', {})
                    self.total_source_use_count = data.get('total_use_count', {})
                    self.rotation_history = data.get('rotation_history', [])[-100:]  # Keep last 100
                    # Clamp per-cycle counters (legacy bug stacked to thousands)
                    try:
                        interval = max(1, int(getattr(self, 'rotation_interval', 3) or 3))
                        for sym, counts in list((self.source_use_count or {}).items()):
                            if not isinstance(counts, dict):
                                continue
                            for src, n in list(counts.items()):
                                try:
                                    n_i = int(n or 0)
                                except (TypeError, ValueError):
                                    n_i = 0
                                if n_i > interval:
                                    counts[src] = n_i % interval
                    except Exception:
                        pass
                    logger.info(f"Loaded rotation stats: {len(self.rotation_history)} rotations recorded")
        except Exception as e:
            logger.warning(f"Could not load rotation stats: {e}")
            self.source_rotation_index = {}
            self.source_use_count = {}
            self.total_source_use_count = {}
            self.rotation_history = []
    
    def _save_rotation_stats(self):
        """Save rotation statistics to file"""
        try:
            data = {
                'rotation_index': self.source_rotation_index,
                'use_count': self.source_use_count,
                'total_use_count': self.total_source_use_count,
                'rotation_history': self.rotation_history[-100:],  # Keep last 100
                'last_updated': datetime.now().isoformat(),
                'rotation_interval': self.rotation_interval
            }
            with open(self.rotation_stats_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Could not save rotation stats: {e}")
    
    def _get_next_source(self, symbol: str) -> tuple:
        """
        Primary + backup selection (no round-robin).
        Always use the best warm source; only land on backups when higher ones are cold.
        Returns: (source_name, source_function, uses_until_rotation)
        """
        # Re-detect available sources periodically (every 10 requests)
        if not hasattr(self, '_detection_counter'):
            self._detection_counter = 0
        self._detection_counter += 1
        if self._detection_counter % 10 == 0:
            self._detect_available_sources()
        
        warm = self._warm_sources()
        if not warm:
            return ('yfinance', self._get_yfinance_data, self.rotation_interval)
        
        if symbol not in self.source_rotation_index:
            self.source_rotation_index[symbol] = 0
            self.source_use_count[symbol] = {}
        
        # Sticky primary: always prefer highest-priority warm API.
        # Jump home to primary when it recovers (don't linger on Yahoo/Finnhub).
        primary = warm[0]
        last = self.last_source_used.get(symbol)
        if last and last in warm and last != primary:
            # Stay on backup only while it's still the best warm? No — promote primary.
            logger.info(f"🏠 Promoting primary {primary} over sticky backup {last} for {symbol}")
        current_source = primary
        
        use_count = self.source_use_count[symbol].get(current_source, 0)
        uses_until_rotation = 0  # no forced rotate; failover is health-based only
        self.source_use_count[symbol][current_source] = use_count + 1
        self.total_source_use_count[current_source] = self.total_source_use_count.get(current_source, 0) + 1
        
        if (self.total_source_use_count.get(current_source, 0) % 5 == 0):
            self._save_rotation_stats()
        
        source_map = {
            'IBKR': self._get_ibkr_data,
            'Polygon': self._get_polygon_data,
            'Finnhub': self._get_finnhub_data,
            'AlphaVantage': self._get_alphavantage_data,
            'yfinance': self._get_yfinance_data
        }
        
        return (current_source, source_map.get(current_source, self._get_yfinance_data), uses_until_rotation)
    
    def get_0dte_options_chain(self, symbol: str = "SPY", preferred_source: Optional[str] = None) -> Dict:
        """
        Get 0DTE options chain with automatic source rotation
        ALWAYS tries IBKR first if available (real-time data)
        Rotates through other sources only if IBKR is unavailable
        
        Args:
            symbol: Symbol to fetch (default: "SPY")
            preferred_source: Manually selected source (e.g., "IBKR", "Polygon", "yfinance")
                             If set, will try this source first before rotation
        """
        cache_key = f"{symbol}_0dte"
        current_time = time.time()
        
        # Check cache
        if cache_key in self.cache:
            cached_data, cache_time = self.cache[cache_key]
            if current_time - cache_time < self.cache_duration:
                return cached_data
        
        # If preferred_source is set, try it first (user manual selection)
        if preferred_source and preferred_source in self.available_sources:
            logger.info(f"🎯 Using preferred source for {symbol}: {preferred_source}")
            source_map = {
                'IBKR': self._get_ibkr_data,
                'Polygon': self._get_polygon_data,
                'Finnhub': self._get_finnhub_data,
                'AlphaVantage': self._get_alphavantage_data,
                'yfinance': self._get_yfinance_data
            }
            source_func = source_map.get(preferred_source)
            if source_func:
                try:
                    data = source_func(symbol)
                    if data and data.get('stock_price', 0) > 0:
                        data['data_source'] = preferred_source
                        data['rotation_info'] = {
                            'current_source': preferred_source,
                            'preferred_source': True,
                            'available_sources': self.available_sources
                        }
                        self.last_source_used[symbol] = preferred_source
                        self.cache[cache_key] = (data, current_time)
                        logger.info(f"✅ Successfully got data from preferred source: {preferred_source}")
                        return data
                    else:
                        logger.warning(f"⚠️ Preferred source {preferred_source} returned no data, falling back to rotation")
                        self._mark_source_cold(preferred_source, 'empty payload')
                except Exception as e:
                    logger.warning(f"⚠️ Preferred source {preferred_source} failed: {e}, falling back to rotation")
                    self._mark_source_cold(preferred_source, str(e)[:120])
        
        # PRIORITY: Always try IBKR first if available (real-time data)
        # Only rotate away if IBKR is truly unavailable or health is very poor
        if 'IBKR' in self.available_sources:
            try:
                from ibkr_client import get_ibkr_client
                ibkr = get_ibkr_client()
                
                # Check connection health before attempting
                if ibkr:
                    health = ibkr.get_connection_health()
                    # If health is very poor (< 20), skip IBKR and use rotation
                    if health.get('health_score', 100) < 20:
                        logger.warning(f"⚠️ IBKR health too poor (score: {health.get('health_score', 0)}) - using rotation instead")
                    else:
                        logger.info(f"🎯 Trying IBKR first for {symbol} (real-time data priority, health: {health.get('health_score', 100)})")
                        data = self._get_ibkr_data(symbol)
                        
                        if data and data.get('stock_price', 0) > 0:
                            # IBKR succeeded - use it! Don't rotate away
                            data['data_source'] = 'IBKR'
                            data['rotation_info'] = {
                                'current_source': 'IBKR',
                                'priority_source': True,
                                'available_sources': self.available_sources,
                                'connection_health': health
                            }
                            self.last_source_used[symbol] = 'IBKR'
                            self.cache[cache_key] = (data, current_time)
                            logger.info(f"✅ Successfully got data from IBKR (real-time, health: {health.get('health_score', 100)})")
                            return data
                        elif data and data.get('quality_score', 0) >= 90:
                            # IBKR is connected and healthy, even if no stock price yet
                            # This happens when options chain is loading
                            data['data_source'] = 'IBKR'
                            data['rotation_info'] = {
                                'current_source': 'IBKR',
                                'priority_source': True,
                                'available_sources': self.available_sources,
                                'connection_health': health,
                                'note': 'IBKR connected, waiting for data'
                            }
                            self.last_source_used[symbol] = 'IBKR'
                            self.cache[cache_key] = (data, current_time)
                            logger.info(f"✅ IBKR connected for {symbol} (data loading, health: {health.get('health_score', 100)})")
                            return data
                        else:
                            logger.debug(f"IBKR returned no data for {symbol}, trying other sources...")
                            self._mark_source_cold('IBKR', 'empty IBKR payload')
                else:
                    logger.debug(f"IBKR client not available for {symbol}")
            except Exception as e:
                logger.warning(f"IBKR failed for {symbol}: {e}, trying other sources...")
                self._mark_source_cold('IBKR', str(e)[:120])
        
        # Health-ordered attempt: warm sources in priority (Polygon → Finnhub → … → Yahoo)
        source_map = {
            'IBKR': self._get_ibkr_data,
            'Polygon': self._get_polygon_data,
            'Finnhub': self._get_finnhub_data,
            'AlphaVantage': self._get_alphavantage_data,
            'yfinance': self._get_yfinance_data
        }
        warm = [s for s in self._warm_sources() if s != 'IBKR']  # IBKR tried above
        try:
            from cloud_runtime import allow_source_for_0dte
            warm = [s for s in warm if allow_source_for_0dte(s)]
        except Exception:
            pass
        if not warm:
            warm = [s for s in self.available_sources if s != 'IBKR'] or ['yfinance']

        last_error = None
        for source_name in warm:
            source_func = source_map.get(source_name)
            if not source_func:
                continue
            try:
                logger.info(f"🔄 Trying {source_name} for {symbol} (health failover)")
                data = source_func(symbol)
                if data and data.get('stock_price', 0) > 0:
                    data['data_source'] = source_name
                    all_source_use_counts = {}
                    for src in self.available_sources:
                        all_source_use_counts[src] = self.source_use_count.get(symbol, {}).get(src, 0)
                    data['rotation_info'] = {
                        'current_source': source_name,
                        'primary_source': self.primary_source(),
                        'role': 'primary' if source_name == self.primary_source() else 'backup',
                        'available_sources': self.available_sources,
                        'warm_sources': warm,
                        'health_failover': True,
                        'use_count': self.source_use_count.get(symbol, {}).get(source_name, 0),
                        'uses_until_rotation': 0,
                        'rotation_interval': self.rotation_interval,
                        'total_uses': self.total_source_use_count.get(source_name, 0),
                        'all_source_use_counts': all_source_use_counts,
                        'cold_sources': {k: int(v - time.time()) for k, v in self.source_cold_until.items() if v > time.time()},
                        'policy': 'primary_sticky_backup_failover',
                    }
                    self.last_source_used[symbol] = source_name
                    self.source_use_count.setdefault(symbol, {})
                    self.source_use_count[symbol][source_name] = self.source_use_count[symbol].get(source_name, 0) + 1
                    self.cache[cache_key] = (data, current_time)
                    self._save_rotation_stats()
                    logger.info(f"✅ Successfully got data from {source_name}")
                    return data
                self._mark_source_cold(source_name, 'empty or zero price')
            except Exception as e:
                last_error = e
                logger.warning(f"{source_name} failed: {e}")
                self._mark_source_cold(source_name, str(e)[:120])

        logger.warning(f"All warm sources failed for {symbol}" + (f": {last_error}" if last_error else ""))
        
        # All sources failed - try to get at least stock price as fallback
        logger.warning(f"Attempting stock price fallback for {symbol}...")
        try:
            from market_hours_detector import get_market_status
            session = (get_market_status() or {}).get('session', 'REGULAR')
            ticker = yf.Ticker(symbol)
            marks = resolve_yfinance_marks(ticker, session=session)
            stock_price = marks["stock_price"]

            if stock_price > 0:
                logger.info(f"✅ Got stock price fallback for {symbol}: ${stock_price:.2f} (session={session})")
                # Return minimal data structure with just stock price
                return {
                    'symbol': symbol,
                    'stock_price': stock_price,
                    'regular_close': marks["regular_close"],
                    'aftermarket_price': marks["aftermarket_price"],
                    'premarket_price': marks["premarket_price"],
                    'expiration': None,
                    'calls': {'total_volume': 0, 'total_open_interest': 0, 'by_strike': []},
                    'puts': {'total_volume': 0, 'total_open_interest': 0, 'by_strike': []},
                    'flow_metrics': {
                        'total_call_volume': 0,
                        'total_put_volume': 0,
                        'call_put_ratio': 1.0,
                        'flow_direction': 'NEUTRAL'
                    },
                    'strikes': {'calls_by_strike': [], 'puts_by_strike': []},
                    'data_source': 'yfinance_fallback',
                    'options_available': False,
                    'rotation_info': {
                        'current_source': 'yfinance_fallback',
                        'available_sources': self.available_sources,
                        'fallback_used': True,
                        'note': 'Options data unavailable, showing stock price only'
                    }
                }
            else:
                logger.warning(f"Stock price fallback failed for {symbol} - could not get price from any method")
        except Exception as e:
            logger.error(f"Stock price fallback exception for {symbol}: {e}", exc_info=True)
        
        # If even stock price fails, return None
        logger.warning(f"All data sources failed for {symbol} - returning None (REAL DATA ONLY, NO DEMO DATA)")
        return None
    
    def _get_ibkr_data(self, symbol: str) -> Optional[Dict]:
        """Get data from IBKR - AUTO-CONNECTS if not connected with health monitoring"""
        try:
            from ibkr_client import get_ibkr_client
            ibkr = get_ibkr_client()
            
            # Auto-connect if not connected
            if not ibkr:
                logger.warning("⚠️ IBKR client not available")
                return None
            
            # Check connection and health
            if not ibkr.is_connected():
                logger.info(f"🔌 IBKR not connected for {symbol} - attempting auto-connect...")
                connected = ibkr.connect(timeout=5, auto_detect_port=True)
                if not connected:
                    logger.warning(f"⚠️ IBKR auto-connect failed for {symbol}")
                    return None
                logger.info(f"✅ IBKR auto-connected for {symbol}")
            
            # Get connection health
            health = ibkr.get_connection_health()
            if health.get('health_score', 100) < 20:
                logger.warning(f"⚠️ IBKR health too poor for {symbol} (score: {health.get('health_score', 0)})")
                return None
            
            # Check for delayed data only (Error 10089)
            # This means no market data subscription
            if hasattr(ibkr.wrapper, 'error_messages'):
                recent_errors = [e for e in ibkr.wrapper.error_messages[-5:] if e.get('code') == 10089]
                if recent_errors:
                    logger.warning("IBKR: Delayed data only - market data subscription required. See IBKR_MARKET_DATA_SUBSCRIPTIONS.md")
                    return None
            
            # Get options flow
            flow_data = ibkr.get_options_flow(symbol)
            if not flow_data:
                logger.debug(f"IBKR: No options flow data returned for {symbol}")
                return None
            
            # IBKR returns quality_score 98 when connected (even if volume is 0)
            # This ensures IBKR is preferred over delayed yfinance
            quality_score = flow_data.get('quality_score', 0)
            connection_health = flow_data.get('connection_health', {})
            
            if quality_score < 50:
                logger.debug(f"IBKR: Low quality_score ({quality_score}) for {symbol}")
                return None
            
            # Log that IBKR is being used (even if volume is 0, it's still preferred)
            if quality_score >= 90:
                health_score = connection_health.get('health_score', 100)
                logger.info(f"✅ IBKR connected for {symbol} (quality_score={quality_score}, health={health_score}) - using IBKR over delayed sources")
            
            # Get stock price
            price_data = ibkr.get_live_price(symbol, timeout=2)
            stock_price = price_data.get('price', 0) if price_data else 0
            
            # If IBKR is connected (high quality_score) but stock price is 0,
            # try yfinance fallback for stock price only (IBKR is still preferred for options)
            if stock_price == 0 and quality_score >= 90:
                logger.info(f"⚠️ IBKR connected but no stock price for {symbol} - using yfinance fallback for price only")
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    if info and 'currentPrice' in info:
                        stock_price = float(info.get('currentPrice', 0))
                    elif info and 'regularMarketPrice' in info:
                        stock_price = float(info.get('regularMarketPrice', 0))
                    if stock_price > 0:
                        logger.info(f"✅ Got stock price from yfinance fallback: ${stock_price:.2f}")
                except Exception as e:
                    logger.debug(f"yfinance fallback for stock price failed: {e}")
            
            if stock_price == 0:
                logger.warning(f"IBKR: No stock price available for {symbol} (even with fallback)")
                return None
            
            # Convert IBKR flow format to our format
            call_volume = flow_data.get('call_volume', 0)
            put_volume = flow_data.get('put_volume', 0)
            
            return {
                'symbol': symbol,
                'stock_price': stock_price,
                'expiration': datetime.now().strftime('%Y-%m-%d'),
                'timestamp': datetime.now(),
                'calls': {
                    'total_volume': call_volume,
                    'total_open_interest': 0,
                    'by_strike': []
                },
                'puts': {
                    'total_volume': put_volume,
                    'total_open_interest': 0,
                    'by_strike': []
                },
                'flow_metrics': {
                    'total_call_volume': call_volume,
                    'total_put_volume': put_volume,
                    'net_volume_flow': call_volume - put_volume,
                    'call_put_ratio': call_volume / max(1, put_volume),
                    'flow_direction': 'CALLS' if call_volume > put_volume else 'PUTS' if put_volume > call_volume else 'NEUTRAL'
                },
                'strikes': {
                    'calls_by_strike': [],
                    'puts_by_strike': []
                }
            }
        except Exception as e:
            logger.debug(f"IBKR error: {e}")
            return None
    
    def _get_polygon_data(self, symbol: str) -> Optional[Dict]:
        """Get data from Polygon/Massive"""
        try:
            # Check for API key from .env first, then api_config.json
            from config_loader import get_api_key
            api_key = get_api_key('POLYGON_API_KEY') or get_api_key('MASSIVE_API_KEY')
            
            # Fallback to api_config.json for backward compatibility
            if not api_key and os.path.exists('api_config.json'):
                with open('api_config.json', 'r') as f:
                    config = json.load(f)
                    api_key = config.get('massive_api_key') or config.get('polygon_api_key')
            
            if not api_key or api_key in ['your_key_here', 'your_polygon_key_here', '']:
                return None
            
            from massive_api_client import MassiveAPIClient
            client = MassiveAPIClient(api_key)
            
            if not client.client:
                return None
            
            # Get options chain
            today = datetime.now().strftime('%Y-%m-%d')
            chain_data = client.get_options_chain(symbol, expiration=today)
            
            if not chain_data:
                logger.warning(
                    "Polygon options unpaid/empty for %s — plan-limited failover "
                    "(need Massive Options Starter+ for chain snapshot)",
                    symbol,
                )
                self._mark_source_plan_limited(
                    'Polygon',
                    'Options Basic: no snapshot quotes — upgrade to Starter+',
                )
                return None
            
            # Get stock price
            quote = client.get_quote(symbol)
            stock_price = quote.get('price', 0) if quote else 0
            
            if stock_price == 0:
                return None
            
            # Process chain data
            calls = chain_data.get('calls', [])
            puts = chain_data.get('puts', [])

            # Guard: never treat strike shells without marks as a live book
            has_marks = any(
                float(c.get('bid') or 0) > 0 or float(c.get('ask') or 0) > 0
                or float(c.get('last_price') or 0) > 0 or int(c.get('volume') or 0) > 0
                for c in (calls + puts)
            )
            if not has_marks:
                logger.warning(f"Polygon chain for {symbol} has no quotes/volume — plan-limited failover")
                self._mark_source_plan_limited(
                    'Polygon',
                    'Options Basic: contract shells without bid/ask/volume',
                )
                return None
            calls_by_strike = []
            puts_by_strike = []
            
            for call in calls:
                calls_by_strike.append({
                    'strike': call.get('strike', 0),
                    'volume': call.get('volume', 0),
                    'open_interest': call.get('open_interest', 0),
                    'last_price': call.get('last_price', 0),
                    'bid': call.get('bid', 0),
                    'ask': call.get('ask', 0),
                    'iv': call.get('iv', 0),
                    'moneyness': 'ITM' if call.get('strike', 0) < stock_price else 'OTM' if call.get('strike', 0) > stock_price else 'ATM',
                    'premium_flow': call.get('volume', 0) * call.get('last_price', 0) * 100
                })
            
            for put in puts:
                puts_by_strike.append({
                    'strike': put.get('strike', 0),
                    'volume': put.get('volume', 0),
                    'open_interest': put.get('open_interest', 0),
                    'last_price': put.get('last_price', 0),
                    'bid': put.get('bid', 0),
                    'ask': put.get('ask', 0),
                    'iv': put.get('iv', 0),
                    'moneyness': 'ITM' if put.get('strike', 0) > stock_price else 'OTM' if put.get('strike', 0) < stock_price else 'ATM',
                    'premium_flow': put.get('volume', 0) * put.get('last_price', 0) * 100
                })
            
            total_call_volume = sum(c.get('volume', 0) for c in calls)
            total_put_volume = sum(p.get('volume', 0) for p in puts)
            total_call_oi = sum(c.get('open_interest', 0) for c in calls)
            total_put_oi = sum(p.get('open_interest', 0) for p in puts)
            call_premium_flow = sum(c.get('premium_flow', 0) for c in calls_by_strike)
            put_premium_flow = sum(p.get('premium_flow', 0) for p in puts_by_strike)
            cp_ratio = total_call_volume / max(1, total_put_volume) if (total_call_volume or total_put_volume) else 1.0
            
            return {
                'symbol': symbol,
                'stock_price': stock_price,
                'expiration': today,
                'timestamp': datetime.now(),
                'calls': {
                    'total_volume': total_call_volume,
                    'total_open_interest': total_call_oi,
                    'by_strike': calls_by_strike
                },
                'puts': {
                    'total_volume': total_put_volume,
                    'total_open_interest': total_put_oi,
                    'by_strike': puts_by_strike
                },
                'flow_metrics': {
                    'total_call_volume': total_call_volume,
                    'total_put_volume': total_put_volume,
                    'total_call_oi': total_call_oi,
                    'total_put_oi': total_put_oi,
                    'call_premium_flow': call_premium_flow,
                    'put_premium_flow': put_premium_flow,
                    'net_volume_flow': total_call_volume - total_put_volume,
                    'net_premium_flow': call_premium_flow - put_premium_flow,
                    'call_put_ratio': round(cp_ratio, 3),
                    'put_call_ratio': round((1.0 / cp_ratio), 3) if cp_ratio else 1.0,
                    'flow_direction': 'CALLS' if total_call_volume > total_put_volume else 'PUTS' if total_put_volume > total_call_volume else 'NEUTRAL'
                },
                'strikes': {
                    'calls_by_strike': sorted(calls_by_strike, key=lambda x: x.get('volume', 0), reverse=True),
                    'puts_by_strike': sorted(puts_by_strike, key=lambda x: x.get('volume', 0), reverse=True)
                }
            }
        except Exception as e:
            logger.warning(f"⚠️ Polygon error for {symbol}: {e}")
            logger.warning(f"   This may be due to: API key invalid, rate limit, SDK issue, or network problem")
            return None
    
    def _get_finnhub_data(self, symbol: str) -> Optional[Dict]:
        """Get real-time options data from Finnhub (requires paid tier for options)"""
        try:
            from config_loader import get_api_key
            import requests
            from datetime import datetime, timedelta
            
            api_key = get_api_key('FINNHUB_API_KEY')
            if not api_key or api_key == 'your_finnhub_key_here':
                return None
            
            # Get real-time stock quote (real-time data)
            quote_url = f'https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}'
            quote_resp = requests.get(quote_url, timeout=5)
            
            if quote_resp.status_code != 200:
                logger.warning(f"⚠️ Finnhub quote failed: HTTP {quote_resp.status_code}")
                if quote_resp.status_code == 429:
                    logger.warning(f"   Rate limit exceeded - consider upgrading API tier")
                    self._mark_source_cold('Finnhub', 'HTTP 429 rate limit')
                elif quote_resp.status_code == 401:
                    logger.warning(f"   Invalid API key - check FINNHUB_API_KEY in .env file")
                    self._mark_source_plan_limited('Finnhub', 'Invalid API key (401)')
                return None
            
            # Check if response has content before parsing JSON
            if not quote_resp.text or quote_resp.text.strip() == '':
                logger.warning(f"⚠️ Finnhub error for {symbol}: Empty response from API")
                logger.warning(f"   This may be due to: API key invalid, rate limit, or free tier limitations")
                return None
            
            try:
                quote_data = quote_resp.json()
            except ValueError as e:
                # JSON decode error - response is not valid JSON
                logger.warning(f"⚠️ Finnhub error for {symbol}: Invalid JSON response - {str(e)}")
                logger.warning(f"   Response text: {quote_resp.text[:200]}")  # Log first 200 chars for debugging
                logger.warning(f"   This may be due to: API key invalid, rate limit, or free tier limitations")
                return None
            
            # Check for API error messages
            if isinstance(quote_data, dict) and 'error' in quote_data:
                error_msg = quote_data.get('error', 'Unknown error')
                logger.warning(f"⚠️ Finnhub API error: {error_msg}")
                return None
            
            stock_price = quote_data.get('c', 0)  # current price (real-time)
            
            if stock_price == 0:
                logger.debug(f"Finnhub: Stock price is 0 for {symbol} (may be market closed or invalid symbol)")
                return None
            
            # Try to get options chain (requires paid tier)
            # Get today's date for 0DTE options
            today = datetime.now().date()
            today_str = today.strftime('%Y-%m-%d')
            
            # Finnhub options chain endpoint (premium feature)
            options_url = f'https://finnhub.io/api/v1/stock/option-chain?symbol={symbol}&token={api_key}'
            options_resp = requests.get(options_url, timeout=10)
            
            calls_by_strike = []
            puts_by_strike = []
            total_call_volume = 0
            total_put_volume = 0
            total_call_oi = 0
            total_put_oi = 0
            call_premium_flow = 0
            put_premium_flow = 0
            
            if options_resp.status_code == 200:
                try:
                    # Check if response has content before parsing JSON
                    if not options_resp.text or options_resp.text.strip() == '':
                        logger.debug(f"Finnhub: Empty options response for {symbol} (options may require paid tier)")
                        options_data = {}
                    else:
                        try:
                            options_data = options_resp.json()
                        except ValueError as e:
                            logger.debug(f"Finnhub: Invalid JSON in options response for {symbol}: {e}")
                            options_data = {}
                    
                    # Finnhub returns options in different format - parse it
                    if 'data' in options_data and isinstance(options_data.get('data'), list):
                        for option in options_data['data']:
                            # Check if it's 0DTE (expires today)
                            exp_date_str = option.get('expirationDate', '')
                            if exp_date_str.startswith(today_str):
                                strike = float(option.get('strike', 0))
                                option_type = option.get('type', '').upper()
                                volume = int(option.get('volume', 0))
                                open_interest = int(option.get('openInterest', 0))
                                last_price = float(option.get('lastPrice', 0))
                                
                                if option_type == 'CALL':
                                    calls_by_strike.append({
                                        'strike': strike,
                                        'volume': volume,
                                        'open_interest': open_interest,
                                        'last_price': last_price,
                                        'premium_flow': last_price * volume if last_price > 0 else 0
                                    })
                                    total_call_volume += volume
                                    total_call_oi += open_interest
                                    call_premium_flow += last_price * volume if last_price > 0 else 0
                                elif option_type == 'PUT':
                                    puts_by_strike.append({
                                        'strike': strike,
                                        'volume': volume,
                                        'open_interest': open_interest,
                                        'last_price': last_price,
                                        'premium_flow': last_price * volume if last_price > 0 else 0
                                    })
                                    total_put_volume += volume
                                    total_put_oi += open_interest
                                    put_premium_flow += last_price * volume if last_price > 0 else 0
                except Exception as e:
                    logger.debug(f"Finnhub options parsing error: {e}")
                    # If options parsing fails, still return stock price data
                    pass
            
            # If no options data but have stock price, try alternative method
            # Some Finnhub tiers might use different endpoints
            if not calls_by_strike and not puts_by_strike:
                # Try alternative: get stock options expiration dates first
                expirations_url = f'https://finnhub.io/api/v1/stock/option/expiration?symbol={symbol}&token={api_key}'
                exp_resp = requests.get(expirations_url, timeout=5)
                
                if exp_resp.status_code == 200:
                    exp_data = exp_resp.json()
                    # Check if today is in expiration list
                    if today_str in exp_data.get('expiration', []):
                        # Get options for today's expiration
                        chain_url = f'https://finnhub.io/api/v1/stock/option/chain?symbol={symbol}&expiration={today_str}&token={api_key}'
                        chain_resp = requests.get(chain_url, timeout=10)
                        
                        if chain_resp.status_code == 200:
                            chain_data = chain_resp.json()
                            # Parse chain data (format varies by tier)
                            # This is a simplified parser - may need adjustment based on actual response
                            if 'data' in chain_data:
                                for option in chain_data['data']:
                                    strike = float(option.get('strike', 0))
                                    option_type = option.get('type', '').upper()
                                    volume = int(option.get('volume', 0))
                                    open_interest = int(option.get('openInterest', 0))
                                    last_price = float(option.get('lastPrice', 0))
                                    
                                    if option_type == 'CALL':
                                        calls_by_strike.append({
                                            'strike': strike,
                                            'volume': volume,
                                            'open_interest': open_interest,
                                            'last_price': last_price,
                                            'premium_flow': last_price * volume if last_price > 0 else 0
                                        })
                                        total_call_volume += volume
                                        total_call_oi += open_interest
                                        call_premium_flow += last_price * volume if last_price > 0 else 0
                                    elif option_type == 'PUT':
                                        puts_by_strike.append({
                                            'strike': strike,
                                            'volume': volume,
                                            'open_interest': open_interest,
                                            'last_price': last_price,
                                            'premium_flow': last_price * volume if last_price > 0 else 0
                                        })
                                        total_put_volume += volume
                                        total_put_oi += open_interest
                                        put_premium_flow += last_price * volume if last_price > 0 else 0
            
            # If no options data but we have stock price, return stock price with empty options
            # This allows the system to at least show stock price even if options aren't available
            if not calls_by_strike and not puts_by_strike:
                if stock_price > 0:
                    logger.info(f"✅ Finnhub: Got stock price for {symbol}: ${stock_price:.2f} (options not available - may require paid tier)")
                    return {
                        'symbol': symbol,
                        'stock_price': stock_price,
                        'expiration': None,
                        'calls': {'total_volume': 0, 'total_open_interest': 0, 'by_strike': []},
                        'puts': {'total_volume': 0, 'total_open_interest': 0, 'by_strike': []},
                        'flow_metrics': {
                            'total_call_volume': 0,
                            'total_put_volume': 0,
                            'call_put_ratio': 1.0,
                            'flow_direction': 'NEUTRAL'
                        },
                        'strikes': {'calls_by_strike': [], 'puts_by_strike': []},
                        'data_source': 'Finnhub',
                        'options_available': False,
                        'options_error': 'Finnhub free tier may not include options data - consider upgrading or using Polygon'
                    }
                else:
                    logger.warning(f"⚠️ Finnhub: No stock price or options data available for {symbol}")
                    logger.warning(f"   This may be due to: Free tier limitations, wrong endpoint, or API key issues")
                    return None
            
            # Sort by strike
            calls_by_strike.sort(key=lambda x: x['strike'])
            puts_by_strike.sort(key=lambda x: x['strike'])
            
            # Build response in our standard format
            return {
                'symbol': symbol,
                'stock_price': stock_price,
                'data_source': 'Finnhub',
                'timestamp': datetime.now().isoformat(),
                'strikes': {
                    'calls_by_strike': calls_by_strike,
                    'puts_by_strike': puts_by_strike
                },
                'summary': {
                    'total_call_volume': total_call_volume,
                    'total_put_volume': total_put_volume,
                    'total_call_oi': total_call_oi,
                    'total_put_oi': total_put_oi,
                    'call_premium_flow': call_premium_flow,
                    'put_premium_flow': put_premium_flow,
                    'put_call_ratio': total_put_volume / total_call_volume if total_call_volume > 0 else 0
                }
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Finnhub error for {symbol}: {e}")
            logger.warning(f"   This may be due to: API key invalid, rate limit, or free tier limitations")
            return None
    
    def _get_alphavantage_data(self, symbol: str) -> Optional[Dict]:
        """Get data from Alpha Vantage (stock price only - options require paid tier)"""
        try:
            from config_loader import get_api_key
            import requests
            from datetime import datetime
            
            api_key = get_api_key('ALPHA_VANTAGE_API_KEY')
            if not api_key or api_key == 'your_key_here' or api_key == 'your_alpha_vantage_key_here':
                logger.debug(f"Alpha Vantage: No API key configured")
                return None
            
            # Alpha Vantage free tier only provides stock quotes, not options
            # Get real-time stock quote
            quote_url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}'
            quote_resp = requests.get(quote_url, timeout=5)
            
            if quote_resp.status_code != 200:
                logger.debug(f"Alpha Vantage quote failed: {quote_resp.status_code}")
                return None
            
            quote_data = quote_resp.json()
            
            # Check for API error messages
            if 'Error Message' in quote_data:
                logger.warning(f"⚠️ Alpha Vantage error: {quote_data['Error Message']}")
                return None
            
            if 'Note' in quote_data:
                logger.warning(f"⚠️ Alpha Vantage rate limit: {quote_data['Note']}")
                return None
            
            # Extract stock price
            global_quote = quote_data.get('Global Quote', {})
            if not global_quote:
                logger.debug(f"Alpha Vantage: No quote data in response")
                return None
            
            stock_price_str = global_quote.get('05. price', '0')
            try:
                stock_price = float(stock_price_str)
            except (ValueError, TypeError):
                logger.debug(f"Alpha Vantage: Invalid price format: {stock_price_str}")
                return None
            
            if stock_price <= 0:
                logger.debug(f"Alpha Vantage: Invalid stock price: {stock_price}")
                return None
            
            # Alpha Vantage free tier doesn't provide options data
            # Return stock price with empty options (similar to yfinance fallback)
            logger.info(f"✅ Alpha Vantage: Got stock price for {symbol}: ${stock_price:.2f} (options not available in free tier)")
            return {
                'symbol': symbol,
                'stock_price': stock_price,
                'expiration': None,
                'calls': {'total_volume': 0, 'total_open_interest': 0, 'by_strike': []},
                'puts': {'total_volume': 0, 'total_open_interest': 0, 'by_strike': []},
                'flow_metrics': {
                    'total_call_volume': 0,
                    'total_put_volume': 0,
                    'call_put_ratio': 1.0,
                    'flow_direction': 'NEUTRAL'
                },
                'strikes': {'calls_by_strike': [], 'puts_by_strike': []},
                'data_source': 'AlphaVantage',
                'options_available': False,
                'options_error': 'Alpha Vantage free tier does not include options data'
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Alpha Vantage error for {symbol}: {e}")
            return None
    
    def _get_yfinance_data(self, symbol: str) -> Optional[Dict]:
        """Get data from yfinance (fallback) — gated by shared yahoo_throttle."""
        try:
            import time
            from yahoo_throttle import (
                yahoo_throttle,
                MIN_INTERVAL_SECONDS,
                CACHE_TTL_SECONDS,
            )

            cache_key = f"{symbol}_0dte"

            # Shared gate: prefer fresh cache / last snapshot over another Yahoo hit
            gated = yahoo_throttle.get_cached(cache_key, max_age=CACHE_TTL_SECONDS)
            if gated is not None:
                return gated

            ok, reason = yahoo_throttle.can_fetch()
            if not ok:
                stale = yahoo_throttle.get_stale(cache_key)
                if stale is None and cache_key in self.cache:
                    stale = self.cache[cache_key][0]
                if stale is not None:
                    logger.debug(f"yfinance {symbol}: {reason} — serving last snapshot")
                    return stale
                logger.warning(f"yfinance {symbol}: {reason} — no snapshot yet")
                return None

            yahoo_throttle.mark_request_started()
            ticker = yf.Ticker(symbol)
            
            # Get available expiration dates
            try:
                exp_dates = ticker.options
            except Exception as e:
                error_msg = str(e)
                if yahoo_throttle.is_rate_limit_error(error_msg):
                    yahoo_throttle.record_rate_limit(error_msg)
                    try:
                        from api_tracker import api_tracker
                        api_tracker.record_request('yfinance', success=False, error='Rate limited')
                    except Exception:
                        pass
                    stale = yahoo_throttle.get_stale(cache_key)
                    if stale is None and cache_key in self.cache:
                        stale = self.cache[cache_key][0]
                    return stale
                else:
                    raise e
            
            # If no expiration dates, still try to get stock price
            if not exp_dates:
                logger.warning(f"{symbol}: No expiration dates available, fetching stock price only...")
                # Get stock price as fallback
                try:
                    hist = ticker.history(period="1d", interval="1m")
                    if hist.empty:
                        hist = ticker.history(period="2d")
                    if not hist.empty:
                        stock_price = float(hist['Close'].iloc[-1])
                        if stock_price > 0:
                            logger.info(f"✅ Got stock price for {symbol} (no options): ${stock_price:.2f}")
                            return {
                                'symbol': symbol,
                                'stock_price': stock_price,
                                'expiration': None,
                                'calls': {'total_volume': 0, 'total_open_interest': 0, 'by_strike': []},
                                'puts': {'total_volume': 0, 'total_open_interest': 0, 'by_strike': []},
                                'flow_metrics': {
                                    'total_call_volume': 0,
                                    'total_put_volume': 0,
                                    'call_put_ratio': 1.0,
                                    'flow_direction': 'NEUTRAL'
                                },
                                'strikes': {'calls_by_strike': [], 'puts_by_strike': []},
                                'data_source': 'yfinance',
                                'options_available': False,
                                'options_error': 'No expiration dates available'
                            }
                except Exception as e:
                    logger.debug(f"Could not get stock price for {symbol}: {e}")
                return None
            
            # Get market status
            from market_hours_detector import get_market_status
            market_status = get_market_status()
            session = market_status['session']
            
            # During regular hours: use 0DTE (today)
            # During after-hours/pre-market: use 1DTE (tomorrow) for preview
            today = datetime.now().date()
            if session == 'REGULAR':
                target_dte = 0
                target_date = today
            else:
                # After-hours/pre-market: show tomorrow's expiration as preview
                target_dte = 1
                target_date = today + timedelta(days=1)
            
            today_exp = None
            for exp in exp_dates:
                exp_date = datetime.strptime(exp, '%Y-%m-%d').date()
                if exp_date == target_date:
                    today_exp = exp
                    break
            
            # If no exact match, try nearest
            if not today_exp and exp_dates:
                today_exp = exp_dates[0]
                exp_date = datetime.strptime(today_exp, '%Y-%m-%d').date()
                dte = (exp_date - today).days
                # Accept if it matches target DTE, or if it's 1DTE during extended hours
                # For extended hours, be more flexible - accept nearest expiration if no 1DTE
                if dte != target_dte:
                    if session == 'REGULAR' and dte != 0:
                        return None  # Need 0DTE during regular hours
                    elif session != 'REGULAR':
                        # During extended hours, if no 1DTE, try to use nearest expiration (but prefer 1DTE)
                        # Only reject if it's way off (more than 7 days)
                        if dte > 7:
                            logger.debug(f"{symbol}: Nearest expiration is {dte}DTE (too far), but will try anyway")
                        # Accept nearest expiration during extended hours as fallback
                        logger.info(f"{symbol}: Using {dte}DTE expiration (target was {target_dte}DTE) during {session}")

            # Official close outside RTH; 1m only during regular session
            marks = resolve_yfinance_marks(ticker, session=session)
            stock_price = marks["stock_price"]
            if stock_price == 0:
                return None

            # No expiration list / no target — return stock-only (avoid option_chain IndexError)
            if not today_exp:
                logger.warning(f"{symbol}: No options expiration available (session={session}) — stock-only payload")
                return {
                    'symbol': symbol,
                    'stock_price': stock_price,
                    'regular_close': marks["regular_close"],
                    'aftermarket_price': marks["aftermarket_price"],
                    'premarket_price': marks["premarket_price"],
                    'expiration': None,
                    'timestamp': datetime.now(),
                    'calls': {'total_volume': 0, 'total_open_interest': 0, 'by_strike': []},
                    'puts': {'total_volume': 0, 'total_open_interest': 0, 'by_strike': []},
                    'flow_metrics': {
                        'total_call_volume': 0,
                        'total_put_volume': 0,
                        'total_call_oi': 0,
                        'total_put_oi': 0,
                        'call_premium_flow': 0,
                        'put_premium_flow': 0,
                        'net_volume_flow': 0,
                        'net_premium_flow': 0,
                        'call_put_ratio': 1.0,
                        'flow_direction': 'NEUTRAL'
                    },
                    'strikes': {'calls_by_strike': [], 'puts_by_strike': []},
                    'data_source': 'yfinance',
                    'options_available': False,
                    'options_error': 'No expirations',
                }

            # Get options chain (may fail for some symbols, but we have stock price)
            try:
                options_chain = ticker.option_chain(today_exp)
                calls_df = options_chain.calls
                puts_df = options_chain.puts
            except Exception as e:
                logger.warning(f"{symbol}: Could not get options chain for {today_exp}: {e}")
                # Return stock price only if options fail
                return {
                    'symbol': symbol,
                    'stock_price': stock_price,
                    'expiration': today_exp,
                    'timestamp': datetime.now(),
                    'calls': {'total_volume': 0, 'total_open_interest': 0, 'by_strike': []},
                    'puts': {'total_volume': 0, 'total_open_interest': 0, 'by_strike': []},
                    'flow_metrics': {
                        'total_call_volume': 0,
                        'total_put_volume': 0,
                        'total_call_oi': 0,
                        'total_put_oi': 0,
                        'call_premium_flow': 0,
                        'put_premium_flow': 0,
                        'net_volume_flow': 0,
                        'net_premium_flow': 0,
                        'call_put_ratio': 1.0,
                        'flow_direction': 'NEUTRAL'
                    },
                    'strikes': {
                        'calls_by_strike': [],
                        'puts_by_strike': []
                    },
                    'data_source': 'yfinance',
                    'options_available': False,
                    'options_error': str(e)
                }
            
            # Process calls
            calls_data = self._process_options(calls_df, 'CALL', stock_price)
            
            # Process puts
            puts_data = self._process_options(puts_df, 'PUT', stock_price)
            
            # Calculate flow metrics
            total_call_volume = calls_data['total_volume']
            total_put_volume = puts_data['total_volume']
            
            call_premium_flow = sum([
                row.get('volume', 0) * row.get('lastPrice', 0) * 100 
                for _, row in calls_df.iterrows() 
                if pd.notna(row.get('volume')) and pd.notna(row.get('lastPrice'))
            ])
            
            put_premium_flow = sum([
                row.get('volume', 0) * row.get('lastPrice', 0) * 100 
                for _, row in puts_df.iterrows() 
                if pd.notna(row.get('volume')) and pd.notna(row.get('lastPrice'))
            ])
            
            net_volume_flow = total_call_volume - total_put_volume
            cp_ratio = total_call_volume / max(1, total_put_volume)
            
            if net_volume_flow > 10000:
                flow_direction = "STRONG_CALLS"
            elif net_volume_flow > 2000:
                flow_direction = "CALLS"
            elif net_volume_flow < -10000:
                flow_direction = "STRONG_PUTS"
            elif net_volume_flow < -2000:
                flow_direction = "PUTS"
            else:
                flow_direction = "NEUTRAL"
            
            result = {
                'symbol': symbol,
                'stock_price': stock_price,
                'regular_close': marks["regular_close"],
                'aftermarket_price': marks["aftermarket_price"],
                'premarket_price': marks["premarket_price"],
                'expiration': today_exp,
                'timestamp': datetime.now(),
                'calls': calls_data,
                'puts': puts_data,
                'flow_metrics': {
                    'total_call_volume': int(total_call_volume),
                    'total_put_volume': int(total_put_volume),
                    'total_call_oi': int(calls_data['total_open_interest']),
                    'total_put_oi': int(puts_data['total_open_interest']),
                    'call_premium_flow': call_premium_flow,
                    'put_premium_flow': put_premium_flow,
                    'net_volume_flow': int(net_volume_flow),
                    'net_premium_flow': call_premium_flow - put_premium_flow,
                    'call_put_ratio': round(cp_ratio, 2),
                    'flow_direction': flow_direction
                },
                'strikes': {
                    'calls_by_strike': calls_data['by_strike'],
                    'puts_by_strike': puts_data['by_strike']
                },
                'data_source': 'yfinance'
            }
            
            # Update flow history for momentum tracking
            if symbol not in self.flow_history:
                self.flow_history[symbol] = []
            
            self.flow_history[symbol].append({
                'timestamp': datetime.now(),
                'call_volume': total_call_volume,
                'put_volume': total_put_volume,
                'net_flow': net_volume_flow,
                'flow_direction': flow_direction
            })
            
            # Keep only last 100 data points
            if len(self.flow_history[symbol]) > 100:
                self.flow_history[symbol] = self.flow_history[symbol][-100:]
            
            try:
                from yahoo_throttle import yahoo_throttle
                yahoo_throttle.put_cache(cache_key, result)
                yahoo_throttle.record_success()
            except Exception:
                pass
            self.cache[cache_key] = (result, time.time())
            return result
        except Exception as e:
            try:
                from yahoo_throttle import yahoo_throttle
                if yahoo_throttle.is_rate_limit_error(e):
                    yahoo_throttle.record_rate_limit(str(e))
                    stale = yahoo_throttle.get_stale(f"{symbol}_0dte")
                    if stale is not None:
                        return stale
            except Exception:
                pass
            logger.debug(f"yfinance error: {e}")
            return None
    
    def _process_options(self, df: pd.DataFrame, option_type: str, stock_price: float) -> Dict:
        """Process options DataFrame into structured data"""
        if df.empty:
            return {
                'total_volume': 0,
                'total_open_interest': 0,
                'by_strike': []
            }
        
        total_volume = 0
        total_oi = 0
        by_strike = []
        
        for _, row in df.iterrows():
            strike = float(row.get('strike', 0))
            volume = float(row.get('volume', 0)) if pd.notna(row.get('volume')) else 0
            oi = float(row.get('openInterest', 0)) if pd.notna(row.get('openInterest')) else 0
            last_price = float(row.get('lastPrice', 0)) if pd.notna(row.get('lastPrice')) else 0
            bid = float(row.get('bid', 0)) if pd.notna(row.get('bid')) else 0
            ask = float(row.get('ask', 0)) if pd.notna(row.get('ask')) else 0
            iv = float(row.get('impliedVolatility', 0)) if pd.notna(row.get('impliedVolatility')) else 0
            
            if option_type == 'CALL':
                moneyness = "ITM" if strike < stock_price else "OTM" if strike > stock_price else "ATM"
            else:
                moneyness = "ITM" if strike > stock_price else "OTM" if strike < stock_price else "ATM"
            
            premium_flow = volume * last_price * 100 if last_price > 0 else 0
            
            total_volume += volume
            total_oi += oi
            
            by_strike.append({
                'strike': strike,
                'volume': int(volume),
                'open_interest': int(oi),
                'last_price': last_price,
                'bid': bid,
                'ask': ask,
                'iv': iv,
                'moneyness': moneyness,
                'premium_flow': premium_flow,
                'distance_from_price': abs(strike - stock_price)
            })
        
        by_strike.sort(key=lambda x: x['volume'], reverse=True)
        
        return {
            'total_volume': int(total_volume),
            'total_open_interest': int(total_oi),
            'by_strike': by_strike
        }
    
    def _get_demo_data(self, symbol: str) -> Dict:
        """Generate realistic demo data for testing when all sources fail (cached for performance)"""
        # Cache demo data for 30 seconds to avoid regenerating constantly
        cache_key = f"demo_{symbol}"
        current_time = time.time()
        
        if cache_key in self.cache:
            cached_data, cache_time = self.cache[cache_key]
            if current_time - cache_time < 30:  # Cache demo data for 30 seconds
                return cached_data
        
        import random
        import numpy as np
        
        # Get approximate stock price from yfinance (even if delayed)
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d", interval="1d")
            if not hist.empty:
                stock_price = float(hist['Close'].iloc[-1])
            else:
                # Default prices for common symbols
                defaults = {'SPY': 450.0, 'QQQ': 380.0, 'IWM': 190.0, 'DIA': 340.0}
                stock_price = defaults.get(symbol, 100.0)
        except:
            defaults = {'SPY': 450.0, 'QQQ': 380.0, 'IWM': 190.0, 'DIA': 340.0}
            stock_price = defaults.get(symbol, 100.0)
        
        # Generate realistic strikes around current price
        strike_range = int(stock_price * 0.05)  # 5% range
        strikes = [stock_price - strike_range + i * 2 for i in range(21)]
        
        # Generate demo calls and puts
        calls_by_strike = []
        puts_by_strike = []
        total_call_volume = 0
        total_put_volume = 0
        total_call_oi = 0
        total_put_oi = 0
        call_premium_flow = 0
        put_premium_flow = 0
        
        for strike in strikes:
            # ATM has higher volume
            distance_from_atm = abs(strike - stock_price) / stock_price
            volume_multiplier = max(0.3, 1.0 - distance_from_atm * 5)
            
            # Calls
            call_volume = int(random.uniform(5000, 50000) * volume_multiplier)
            call_oi = int(call_volume * random.uniform(1.2, 2.5))
            call_price = max(0.01, (stock_price - strike) * 0.1 + random.uniform(0.5, 5.0))
            call_premium = call_volume * call_price * 100
            
            calls_by_strike.append({
                'strike': round(strike, 2),
                'volume': call_volume,
                'open_interest': call_oi,
                'last_price': round(call_price, 2),
                'bid': round(call_price * 0.98, 2),
                'ask': round(call_price * 1.02, 2),
                'implied_volatility': round(random.uniform(0.15, 0.35), 4),
                'moneyness': 'ITM' if strike < stock_price else 'OTM' if strike > stock_price else 'ATM',
                'premium_flow': call_premium
            })
            
            total_call_volume += call_volume
            total_call_oi += call_oi
            call_premium_flow += call_premium
            
            # Puts
            put_volume = int(random.uniform(5000, 50000) * volume_multiplier)
            put_oi = int(put_volume * random.uniform(1.2, 2.5))
            put_price = max(0.01, (strike - stock_price) * 0.1 + random.uniform(0.5, 5.0))
            put_premium = put_volume * put_price * 100
            
            puts_by_strike.append({
                'strike': round(strike, 2),
                'volume': put_volume,
                'open_interest': put_oi,
                'last_price': round(put_price, 2),
                'bid': round(put_price * 0.98, 2),
                'ask': round(put_price * 1.02, 2),
                'implied_volatility': round(random.uniform(0.15, 0.35), 4),
                'moneyness': 'ITM' if strike > stock_price else 'OTM' if strike < stock_price else 'ATM',
                'premium_flow': put_premium
            })
            
            total_put_volume += put_volume
            total_put_oi += put_oi
            put_premium_flow += put_premium
        
        net_volume_flow = total_call_volume - total_put_volume
        cp_ratio = total_call_volume / max(1, total_put_volume)
        
        if net_volume_flow > 10000:
            flow_direction = "STRONG_CALLS"
        elif net_volume_flow > 2000:
            flow_direction = "CALLS"
        elif net_volume_flow < -10000:
            flow_direction = "STRONG_PUTS"
        elif net_volume_flow < -2000:
            flow_direction = "PUTS"
        else:
            flow_direction = "NEUTRAL"
        
        today_exp = datetime.now().strftime('%Y-%m-%d')
        
        return {
            'symbol': symbol,
            'stock_price': round(stock_price, 2),
            'expiration': today_exp,
            'timestamp': datetime.now(),
            'calls': {
                'total_volume': total_call_volume,
                'total_open_interest': total_call_oi,
                'by_strike': calls_by_strike
            },
            'puts': {
                'total_volume': total_put_volume,
                'total_open_interest': total_put_oi,
                'by_strike': puts_by_strike
            },
            'flow_metrics': {
                'total_call_volume': total_call_volume,
                'total_put_volume': total_put_volume,
                'total_call_oi': total_call_oi,
                'total_put_oi': total_put_oi,
                'call_premium_flow': call_premium_flow,
                'put_premium_flow': put_premium_flow,
                'net_volume_flow': net_volume_flow,
                'net_premium_flow': call_premium_flow - put_premium_flow,
                'call_put_ratio': round(cp_ratio, 2),
                'flow_direction': flow_direction
            },
            'strikes': {
                'calls_by_strike': calls_by_strike,
                'puts_by_strike': puts_by_strike
            },
            'data_source': 'demo',
            'demo_mode': True,
            'warning': 'Demo data - All data sources unavailable. Connect to a data provider for live data.'
        }
        
        # Cache the demo data for 30 seconds
        self.cache[cache_key] = (result, current_time)
        return result
    
    def _get_empty_chain(self, symbol: str, reason: str = "No data available") -> Dict:
        """Return empty chain structure"""
        return {
            'symbol': symbol,
            'stock_price': 0,
            'expiration': None,
            'timestamp': datetime.now(),
            'calls': {
                'total_volume': 0,
                'total_open_interest': 0,
                'by_strike': []
            },
            'puts': {
                'total_volume': 0,
                'total_open_interest': 0,
                'by_strike': []
            },
            'flow_metrics': {
                'total_call_volume': 0,
                'total_put_volume': 0,
                'total_call_oi': 0,
                'total_put_oi': 0,
                'call_premium_flow': 0,
                'put_premium_flow': 0,
                'net_volume_flow': 0,
                'net_premium_flow': 0,
                'call_put_ratio': 1.0,
                'flow_direction': 'NEUTRAL'
            },
            'strikes': {
                'calls_by_strike': [],
                'puts_by_strike': []
            },
            'error': reason,
            'data_source': 'none'
        }
    
    def get_flow_momentum(self, symbol: str) -> Dict:
        """Calculate flow momentum from history"""
        if symbol not in self.flow_history or len(self.flow_history[symbol]) < 3:
            return {
                'trend': 'NEUTRAL',
                'momentum': 0,
                'acceleration': 0
            }
        
        history = self.flow_history[symbol][-20:]
        net_flows = [h['net_flow'] for h in history]
        
        if len(net_flows) > 1:
            slope = np.polyfit(range(len(net_flows)), net_flows, 1)[0]
        else:
            slope = 0
        
        if slope > 500:
            trend = 'STRONG_BULLISH'
        elif slope > 100:
            trend = 'BULLISH'
        elif slope < -500:
            trend = 'STRONG_BEARISH'
        elif slope < -100:
            trend = 'BEARISH'
        else:
            trend = 'NEUTRAL'
        
        if len(net_flows) >= 6:
            recent_slope = np.polyfit(range(len(net_flows[-6:])), net_flows[-6:], 1)[0]
            earlier_slope = np.polyfit(range(len(net_flows[-12:-6])), net_flows[-12:-6], 1)[0] if len(net_flows) >= 12 else 0
            acceleration = recent_slope - earlier_slope
        else:
            acceleration = 0
        
        return {
            'trend': trend,
            'momentum': slope,
            'acceleration': acceleration,
            'recent_net_flow': net_flows[-1] if net_flows else 0
        }

# Global instance
multi_source_tracker = MultiSourceFlowTracker()

