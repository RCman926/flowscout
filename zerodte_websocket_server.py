"""
0DTE Flow Tracker - WebSocket Server
FastAPI + WebSocket for sub-second real-time updates
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import asyncio
import json
import os
import time
import math
from datetime import datetime, timedelta, time as dt_time
from typing import Dict, List, Set, Optional, Tuple
import logging
import signal
import sys
from contextlib import asynccontextmanager
import requests

from zerodte_flow_tracker import flow_tracker
from multi_source_flow_tracker import multi_source_tracker
from market_hours_detector import get_market_status
from api_tracker import api_tracker
from zerodte_signal_analyzer import ZeroDTESignalAnalyzer
from enhanced_signal_analyzer import EnhancedSignalAnalyzer
from order_flow_history import order_flow_history

# Initialize logging first (before any try/except that uses logger)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Startup progress logging
print("🔄 [1/5] Loading core modules...", file=sys.stderr, flush=True)

# Initialize signal analyzer instance (lazy load history to speed up startup)
print("🔄 [2/5] Initializing signal analyzer...", file=sys.stderr, flush=True)
signal_analyzer = ZeroDTESignalAnalyzer(load_history_immediately=False)  # Load history in background

# Make ML/advanced features optional - server can run without PyTorch and heavy ML dependencies
# ML modules are lazy-loaded to avoid startup delays
print("🔄 [3/5] Stage A core (Boss + shadow + Big Run) — no elite/ensemble bots...", file=sys.stderr, flush=True)
institutional_optimizer = None
INSTITUTIONAL_OPTIMIZER_AVAILABLE = False
advanced_prediction_bot_system = None
ADVANCED_PREDICTION_AVAILABLE = False
institutional_prediction_system = None
INSTITUTIONAL_PREDICTION_AVAILABLE = False
ai_rendering_engine = None
AI_RENDERING_AVAILABLE = False
active_learning_system = None
ACTIVE_LEARNING_AVAILABLE = False
pattern_memory_system = None
enhanced_bot_consensus = None
autonomous_improvement_system = None
from unusual_activity_detector import unusual_activity_detector

try:
    from session_structure_workers import evaluate_session_structure, ingest_price
    SESSION_STRUCTURE_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"Session structure workers not available: {e}")
    evaluate_session_structure = None
    ingest_price = None
    SESSION_STRUCTURE_AVAILABLE = False

try:
    from expiry_term_scanner import expiry_term_scanner
    EXPIRY_TERM_SCANNER_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"Expiry term scanner not available: {e}")
    expiry_term_scanner = None
    EXPIRY_TERM_SCANNER_AVAILABLE = False

try:
    from boss_decision_engine import boss_decision_engine
    from paper_trading_engine import paper_trading_engine
    from paper_arm_state import paper_arm_state
    BOSS_ENGINE_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"Boss decision engine not available: {e}")
    boss_decision_engine = None
    paper_trading_engine = None
    paper_arm_state = None
    BOSS_ENGINE_AVAILABLE = False

# Phase 1: Critical Upgrades - Real-Time Analysis
try:
    from realtime_greeks_calculator import realtime_greeks_calculator
    REALTIME_GREEKS_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"Real-time Greeks calculator not available: {e}")
    realtime_greeks_calculator = None
    REALTIME_GREEKS_AVAILABLE = False

try:
    from iv_surface_analyzer import iv_surface_analyzer
    IV_SURFACE_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"IV Surface analyzer not available: {e}")
    iv_surface_analyzer = None
    IV_SURFACE_AVAILABLE = False

try:
    from order_flow_imbalance_detector import order_flow_imbalance_detector
    ORDER_FLOW_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"Order flow imbalance detector not available: {e}")
    order_flow_imbalance_detector = None
    ORDER_FLOW_AVAILABLE = False
# PERFORMANCE TRACKER: quarantined — Stage A uses shadow-learning
advanced_confidence_analyzer = None
ADVANCED_CONFIDENCE_AVAILABLE = False
confidence_visualizer = None
ml_ensemble_predictor = None
ML_ENSEMBLE_AVAILABLE = False
ml_prediction_engine = None
ML_PREDICTION_ENGINE_AVAILABLE = False

def get_ml_prediction_engine():
    return None
try:
    from ml_feature_engineer import ml_feature_engineer
except (ImportError, ModuleNotFoundError):
    ml_feature_engineer = None
from market_regime_detector import market_regime_detector
from position_sizer import position_sizer
from position_monitor import position_monitor
try:
    from gamma_risk_calculator import gamma_risk_calculator
except (ImportError, ModuleNotFoundError):
    gamma_risk_calculator = None
try:
    from model_performance_monitor import model_performance_monitor
except (ImportError, ModuleNotFoundError):
    model_performance_monitor = None
from user_auth import user_auth
from data_persistence import data_persistence
from error_handler import error_handler
from backtesting_engine import backtesting_engine
from export_manager import export_manager
from signal_quality_analyzer import signal_quality_analyzer
try:
    from signal_review_bot import signal_review_bot
except (ImportError, ModuleNotFoundError):
    signal_review_bot = None
signal_review_bot = None
from telegram_notifier import init_telegram_notifier, get_telegram_notifier
print("🔄 [4/5] Loading data and analysis modules...", file=sys.stderr, flush=True)
import yfinance as yf  # Import at top level for better performance
try:
    from market_data_scanner import market_data_scanner
except (ImportError, ModuleNotFoundError):
    market_data_scanner = None
print("✅ [5/5] All modules loaded! Starting server...", file=sys.stderr, flush=True)

# Function to get performance tracker instance (never importlib.reload — that froze the WS loop)
_PERF_TRACKER_SINGLETON = None

def get_performance_tracker():
    """Quarantined. Stage A ledger is /api/shadow-learning/today."""
    return None


def _trade_lesson_payload(boss_decision=None, paper_boss=None):
    """Why you're in (or sitting out) — no extra APIs."""
    try:
        from trade_lesson import pack
        from shadow_learning_engine import shadow_learning_engine as _sh
        from squeeze_radar import squeeze_radar as _sq
        opens = []
        for t in list(_sh.open)[:4]:
            opens.append({
                "id": t.get("id"),
                "action": t.get("action"),
                "strike": t.get("strike"),
                "tenor": t.get("tenor"),
                "pnl_pct": t.get("last_pnl_pct"),
                "entry_ask": t.get("entry_ask"),
                "mark": t.get("last_mark"),
                "right": t.get("right"),
                "lesson": t.get("lesson"),
            })
        return pack(
            boss_decision,
            shadow_opens=opens,
            paper=paper_boss,
            big_run=(_sq.snapshot() or {}).get("primary"),
        )
    except Exception:
        return None

# ========== INPUT VALIDATION & SANITIZATION ==========
# Production-grade security to prevent injection attacks and data corruption

def validate_symbol(symbol: str) -> Tuple[bool, Optional[str]]:
    """
    Validate and sanitize symbol input
    Returns: (is_valid, sanitized_symbol or error_message)
    """
    if not symbol or not isinstance(symbol, str):
        return False, "Symbol must be a non-empty string"
    
    # Sanitize: uppercase, strip whitespace, remove special characters
    sanitized = symbol.strip().upper()
    
    # Only allow alphanumeric characters (stock symbols are typically 1-5 letters)
    if not sanitized.isalnum() or len(sanitized) > 10:
        return False, f"Invalid symbol format: {symbol}"
    
    # Common valid symbols (add more as needed)
    valid_symbols = ['SPY', 'QQQ', 'IWM', 'DIA', 'SPX', 'NDX']
    if sanitized not in valid_symbols and len(sanitized) > 5:
        # Allow custom symbols but validate format
        if not (1 <= len(sanitized) <= 5 and sanitized.isalpha()):
            return False, f"Symbol must be 1-5 letters: {symbol}"
    
    return True, sanitized

def validate_numeric(value: any, min_val: float = None, max_val: float = None, 
                     allow_none: bool = False) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Validate and sanitize numeric input
    Returns: (is_valid, sanitized_value or None, error_message)
    """
    if value is None:
        if allow_none:
            return True, None, None
        return False, None, "Value cannot be None"
    
    try:
        num = float(value)
        if not (math.isfinite(num) and not math.isnan(num)):
            return False, None, "Value must be a finite number"
        
        if min_val is not None and num < min_val:
            return False, None, f"Value must be >= {min_val}"
        if max_val is not None and num > max_val:
            return False, None, f"Value must be <= {max_val}"
        
        return True, num, None
    except (ValueError, TypeError):
        return False, None, f"Invalid numeric value: {value}"

def extract_options_data(flow_data: dict, symbol: str = "") -> tuple:
    """
    Extract all_calls and all_puts from flow_data using multiple fallback paths.
    Returns: (calls_list, puts_list) - always returns lists (never None)
    """
    if not flow_data or not isinstance(flow_data, dict):
        return [], []
    
    calls_data = []
    puts_data = []
    
    # Try 1: Direct all_calls/all_puts (may already be extracted)
    if flow_data.get('all_calls') or flow_data.get('all_puts'):
        calls_data = flow_data.get('all_calls', [])
        puts_data = flow_data.get('all_puts', [])
        if symbol:
            logger.debug(f"[extract_options_data] {symbol}: Found direct all_calls/all_puts: {len(calls_data)} calls, {len(puts_data)} puts")
    
    # Try 2: strikes structure
    if (not calls_data or not puts_data):
        strikes = flow_data.get('strikes', {})
        if isinstance(strikes, dict):
            if not calls_data:
                calls_data = strikes.get('calls_by_strike', [])
                # Store back to flow_data for consistency
                if calls_data:
                    flow_data['all_calls'] = calls_data
            if not puts_data:
                puts_data = strikes.get('puts_by_strike', [])
                # Store back to flow_data for consistency
                if puts_data:
                    flow_data['all_puts'] = puts_data
            if (calls_data or puts_data) and symbol:
                logger.debug(f"[extract_options_data] {symbol}: Found options in strikes dict: {len(calls_data)} calls, {len(puts_data)} puts")
    
    # Try 3: calls/puts structure (backward compatibility)
    if (not calls_data or not puts_data):
        if not calls_data and flow_data.get('calls'):
            calls_dict = flow_data.get('calls', {})
            if isinstance(calls_dict, dict):
                calls_data = calls_dict.get('by_strike', [])
                if calls_data:
                    flow_data['all_calls'] = calls_data
        if not puts_data and flow_data.get('puts'):
            puts_dict = flow_data.get('puts', {})
            if isinstance(puts_dict, dict):
                puts_data = puts_dict.get('by_strike', [])
                if puts_data:
                    flow_data['all_puts'] = puts_data
        if (calls_data or puts_data) and symbol:
            logger.debug(f"[extract_options_data] {symbol}: Found options in calls/puts structure: {len(calls_data)} calls, {len(puts_data)} puts")
    
    # Ensure lists (never None)
    calls_data = calls_data if isinstance(calls_data, list) else []
    puts_data = puts_data if isinstance(puts_data, list) else []
    
    return calls_data, puts_data

def sanitize_string(value: any, max_length: int = 1000) -> str:
    """
    Sanitize string input to prevent injection attacks
    """
    if value is None:
        return ""
    
    if not isinstance(value, str):
        value = str(value)
    
    # Remove null bytes and control characters (except newlines and tabs)
    sanitized = ''.join(c for c in value if ord(c) >= 32 or c in '\n\t')
    
    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized

# Helper function for JSON responses with charset
def json_response(content: dict, status_code: int = 200):
    """Return JSON response with charset=utf-8"""
    return Response(
        content=json.dumps(content, ensure_ascii=False),
        media_type="application/json; charset=utf-8",
        status_code=status_code,
        headers={"Content-Type": "application/json; charset=utf-8"}
    )

# Production-ready FastAPI app with lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown"""
    # Startup
    logger.info("🚀 ShiftSignals - Starting up...")
    
    # CRITICAL: Ensure working directory is correct for file access
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if os.getcwd() != script_dir:
        logger.info(f"Changing working directory from {os.getcwd()} to {script_dir}")
        os.chdir(script_dir)
    logger.info(f"Working directory: {os.getcwd()}")

    # Hydrate last-good snapshot so a second offline boot still has paint
    try:
        from offline_mode import hydrate_last_good, live_market_blocked, annotate_stale, status_dict

        snap = hydrate_last_good()
        if snap:
            symbol = snap.get("symbol") or "SPY"
            flow = snap.get("flow") if isinstance(snap.get("flow"), dict) else None
            if flow:
                age = None
                if snap.get("captured_ts"):
                    try:
                        age = max(0.0, time.time() - float(snap["captured_ts"]))
                    except (TypeError, ValueError):
                        age = None
                painted = annotate_stale(
                    flow,
                    symbol=symbol,
                    captured_at=snap.get("captured_at"),
                    snapshot_age_sec=age,
                )
                if isinstance(snap.get("boss_decision"), dict):
                    from offline_mode import sit_out_boss

                    painted["boss_decision"] = sit_out_boss(snap["boss_decision"])
                _last_successful_flow_data[symbol] = painted
                _last_successful_data_timestamp[symbol] = float(snap.get("captured_ts") or 0)
                logger.info(
                    "Hydrated last-good snapshot for %s @ %s (age=%s)",
                    symbol,
                    painted.get("stock_price"),
                    age,
                )
        if live_market_blocked():
            st = status_dict()
            logger.info(
                "OFFLINE MODE — live Yahoo/Polygon/IBKR off. snapshot=%s paper stays DISARMED.",
                st.get("has_snapshot"),
            )
    except Exception as e:
        logger.warning(f"offline hydrate: {e}")
    
    try:
        from session_hygiene import apply_session_hygiene
        apply_session_hygiene()
    except Exception as e:
        logger.warning(f"session hygiene: {e}")
    
    logger.info("📊 Initializing background tasks...")
    _skip_unattended_arm = False
    try:
        from offline_mode import live_market_blocked as _off_arm

        _skip_unattended_arm = _off_arm()
    except Exception:
        _skip_unattended_arm = False
    if os.getenv("UNATTENDED", "").lower() in ("1", "true", "yes") and not _skip_unattended_arm:
        try:
            if paper_arm_state:
                paper_arm_state.set_armed(True)
                logger.info("UNATTENDED: paper auto-armed for this session")
        except Exception as e:
            logger.debug(f"unattended arm: {e}")
    
    # FIXED: Store all background tasks for proper shutdown
    app.state.background_tasks = []
    
    # signal_review_bot is archived theater — do not start

    async def squeeze_radar_loop():
        from squeeze_radar import squeeze_radar
        from market_hours_detector import session_clock
        logger.info("Big Run desk started (spikes+squeezes, off SPY cycle)")
        # One pass costs ~150-300 Yahoo requests. Running it flat out around the
        # clock is what tripped Yahoo's rate limiter, so cadence follows the
        # tape: full speed in RTH, slower extended, parked while closed.
        idle_logged = False
        try:
            while True:
                try:
                    try:
                        from offline_mode import live_market_blocked

                        if live_market_blocked():
                            if not idle_logged:
                                logger.info("Big Run parked — OFFLINE (no live Yahoo)")
                                idle_logged = True
                            await asyncio.sleep(600)
                            continue
                    except Exception:
                        pass
                    clock = session_clock()
                    if clock.get("closed"):
                        if not idle_logged:
                            logger.info(
                                f"Big Run parked — {clock.get('label')}; "
                                f"nothing can run until {clock.get('next_open')}"
                            )
                            idle_logged = True
                        await asyncio.sleep(600)
                        continue
                    idle_logged = False
                    hits = await asyncio.to_thread(squeeze_radar.scan_pass)
                    if hits:
                        try:
                            tn = get_telegram_notifier()
                            if tn and tn.enabled:
                                from squeeze_radar import format_big_run_telegram
                                top = hits[0]
                                plan = top.get("plan") or {}
                                conf = float(plan.get("confidence") or top.get("confidence") or 0)
                                lvl = str(top.get("level") or "")
                                if conf >= 55 and lvl != "HOT":
                                    await tn.send_message(format_big_run_telegram(top))
                        except Exception:
                            pass
                    # Extended hours move slowly and thin — stay under the
                    # 12 min Desk Health stale limit without burning quota.
                    await asyncio.sleep(45 if clock.get("rth") else 240)
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.debug(f"squeeze loop: {e}")
                    await asyncio.sleep(60)
        except asyncio.CancelledError:
            raise

    squeeze_task = asyncio.create_task(squeeze_radar_loop())
    app.state.background_tasks.append(squeeze_task)
    app.state.squeeze_radar_task = squeeze_task

    async def desk_health_loop():
        from desk_health import desk_health
        logger.info("Desk Health boss started (workers/managers — safe autofix + report)")
        try:
            while True:
                try:
                    updater = getattr(app.state, "background_updater_task", None)
                    sq_task = getattr(app.state, "squeeze_radar_task", None)
                    ctx = {
                        "ws_clients": len(manager.active_connections),
                        "updater_alive": updater is not None and not updater.done(),
                        "squeeze_task_alive": sq_task is not None and not sq_task.done(),
                        "last_broadcast_ts": getattr(manager, "last_broadcast_ts", None),
                        "last_boss_action": getattr(app.state, "last_boss_action", None),
                    }
                    snap = desk_health.evaluate(ctx)
                    from trade_health import trade_health
                    t_snap = trade_health.evaluate(ctx)
                    for action in snap.get("actions") or []:
                        if action == "RESTART_UPDATER":
                            try:
                                if updater is None or updater.done():
                                    t = asyncio.create_task(background_data_updater(update_interval=3.0))
                                    app.state.background_updater_task = t
                                    app.state.background_tasks.append(t)
                                    desk_health.record_fix("RESTART_UPDATER", "restarted SPY updater", True)
                                    logger.warning("Desk Health AUTOFIX: restarted SPY background updater")
                            except Exception as e:
                                desk_health.record_fix("RESTART_UPDATER", str(e), False)
                        elif action == "NUDGE_SQUEEZE":
                            try:
                                from squeeze_radar import squeeze_radar
                                await asyncio.to_thread(squeeze_radar.scan_pass)
                                desk_health.record_fix("NUDGE_SQUEEZE", "ran Big Run scan_pass", True)
                            except Exception as e:
                                desk_health.record_fix("NUDGE_SQUEEZE", str(e), False)
                    if desk_health.should_telegram() and (snap.get("reports") or snap.get("status") != "HEALTHY"):
                        try:
                            tn = get_telegram_notifier()
                            if tn and tn.enabled:
                                bits = "; ".join((snap.get("reports") or [])[:4]) or snap.get("status")
                                await tn.send_message(f"DESK HEALTH {snap.get('status')} — {bits}")
                        except Exception:
                            pass
                    if trade_health.should_telegram() and (t_snap.get("reports") or t_snap.get("status") != "HEALTHY"):
                        try:
                            tn = get_telegram_notifier()
                            if tn and tn.enabled:
                                bits = "; ".join((t_snap.get("reports") or [])[:4]) or t_snap.get("status")
                                await tn.send_message(f"TRADE HEALTH {t_snap.get('status')} — {bits}")
                        except Exception:
                            pass
                    await asyncio.sleep(25)
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.debug(f"desk health loop: {e}")
                    await asyncio.sleep(40)
        except asyncio.CancelledError:
            raise

    health_task = asyncio.create_task(desk_health_loop())
    app.state.background_tasks.append(health_task)
    
    # Start autonomous improvement system (learns and upgrades itself)
    async def autonomous_improvement_loop():
        """Continuously analyze and improve the system"""
        logger.info("🤖 AUTONOMOUS IMPROVEMENT SYSTEM: Started - will analyze and improve every hour")
        try:
            while True:
                try:
                    await asyncio.sleep(3600)  # Wait 1 hour
                    result = autonomous_improvement_system.analyze_and_improve()
                    logger.info(f"🤖 Autonomous improvement cycle complete: {result.get('improvements_applied', 0)} improvements applied")
                except asyncio.CancelledError:
                    # FIXED: Handle graceful cancellation for shutdown
                    logger.info("🛑 Autonomous improvement loop cancelled - shutting down gracefully")
                    raise
                except Exception as e:
                    logger.error(f"Error in autonomous improvement loop: {e}")
                    await asyncio.sleep(300)  # Wait 5 minutes before retry
        except asyncio.CancelledError:
            raise
    
    if autonomous_improvement_system is not None:
        improvement_task = asyncio.create_task(autonomous_improvement_loop())
        app.state.background_tasks.append(improvement_task)
        logger.info("✅ Autonomous Improvement System started")
    
    # CRITICAL: Start the background data updater (this is what sends continuous updates!)
    logger.info("🔄 Starting background data updater for continuous WebSocket updates...")
    # Initialize with default watchlist (SPY only - focusing on SPY data quality)
    default_watchlist = ['SPY']
    for symbol in default_watchlist:
        if symbol not in manager.symbol_subscriptions:
            manager.symbol_subscriptions[symbol] = set()
    logger.info(f"✅ Initialized watchlist: {default_watchlist}")
    
    # Start background updater - CRITICAL for auto-refresh
    # OPTIMIZED: Reduced from 3.0s to 2.0s for faster signal updates
    # RATE LIMIT AWARE: 2.5s cycle for Yahoo Stage A (shared yahoo_throttle + api_tracker)
    updater_task = asyncio.create_task(background_data_updater(update_interval=3.0))
    app.state.background_tasks.append(updater_task)
    logger.info("✅ Background data updater started — open-protect: PM rare chains, 9:25–10:00 ET 5s cadence")
    logger.info("🔄 AUTO-REFRESH ENABLED - Server will continuously send updates to all connected clients")
    
    # Store task reference to monitor it (for backward compatibility)
    app.state.background_updater_task = updater_task
    
    # Initialize Telegram Notifier from environment / .env (never hardcode tokens)
    try:
        from config_loader import get_config
        _cfg = get_config()
        telegram_bot_token = _cfg.get("telegram_bot_token")
        telegram_chat_id = _cfg.get("telegram_chat_id")
        telegram_bot_username = os.getenv("TELEGRAM_BOT_USERNAME", "@ShiftSignals_bot")
        if telegram_bot_token and telegram_chat_id:
            init_telegram_notifier(bot_token=telegram_bot_token, chat_id=telegram_chat_id)
            telegram_notifier = get_telegram_notifier()
            if telegram_notifier and telegram_notifier.enabled:
                logger.info(
                    f"✅ Telegram notifier initialized - Bot: {telegram_bot_username}, "
                    f"Chat ID: {telegram_chat_id}"
                )
                try:
                    asyncio.create_task(
                        telegram_notifier.send_message(
                            "🚀 ShiftSignals is now running! You will receive alerts for "
                            "high-confidence trading signals (80%+ confidence)."
                        )
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Failed to queue Telegram startup message: {e}")
            else:
                logger.warning("⚠️ Telegram notifier not enabled")
        else:
            logger.warning(
                "⚠️ Telegram skipped — set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env"
            )
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize Telegram: {e}")
    
    # Startup complete
    logger.info("✅ ShiftSignals is ready!")
    logger.info("🌐 Server accessible at: http://0.0.0.0:8000")
    
    yield
    
    # Shutdown
    logger.info("🛑 ShiftSignals - Shutting down gracefully...")
    
    # FIXED: Cancel ALL background tasks to prevent blocking shutdown
    try:
        # Cancel all background tasks
        if hasattr(app.state, 'background_tasks'):
            logger.info(f"Cancelling {len(app.state.background_tasks)} background task(s)...")
            for task in app.state.background_tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for all tasks to be cancelled (with timeout)
            cancelled_tasks = await asyncio.wait_for(
                asyncio.gather(*app.state.background_tasks, return_exceptions=True),
                timeout=2.0  # Max 2 seconds to cancel
            )
            logger.info("✅ All background tasks cancelled")
        else:
            # Fallback: Cancel individual tasks if background_tasks list doesn't exist
            if hasattr(app.state, 'background_updater_task'):
                app.state.background_updater_task.cancel()
                try:
                    await asyncio.wait_for(app.state.background_updater_task, timeout=1.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    logger.info("✅ Background data updater cancelled")
        
        # Close all WebSocket connections
        logger.info(f"Closing {len(manager.active_connections)} WebSocket connection(s)...")
        close_tasks = []
        for websocket in list(manager.active_connections):
            try:
                close_tasks.append(websocket.close())
            except Exception as e:
                logger.debug(f"Error initiating WebSocket close: {e}")
        
        # Wait for all connections to close (with timeout)
        if close_tasks:
            try:
                await asyncio.wait_for(asyncio.gather(*close_tasks, return_exceptions=True), timeout=1.0)
            except asyncio.TimeoutError:
                logger.warning("⚠️ Some WebSocket connections took too long to close")
        
        logger.info("✅ All connections closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    
    logger.info("✅ Shutdown complete")

app = FastAPI(
    title="ShiftSignals - 0DTE Options Flow Intelligence",
    description="Professional-grade real-time options flow tracking and analysis platform",
    version="2.0.0",
    lifespan=lifespan
)

# CORS Configuration - Allow access from any origin (for sharing with friends)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_LEGACY_LEDGER_PREFIXES = (
    "/performance-stats",
    "/performance/trades",
    "/trade-history",
    "/api/bot-performance",
    "/api/performance-diagnostics",
    "/api/analytics/time-of-day",
    "/api/analytics/historical-accuracy",
    "/api/export/performance",
    "/api/export/trades",
    "/api/ml-model-status",
    "/api/trade-history",
    "/close-trade",
    "/reload-trades",
    "/reset-trades",
    "/model-performance",
    "/ml-model-info",
    "/retrain-model",
    "/market-regime",
)

@app.middleware("http")
async def quarantine_legacy_ledger(request, call_next):
    path = request.url.path or ""
    if any(path == p or path.startswith(p + "/") or path.startswith(p + "?") for p in _LEGACY_LEDGER_PREFIXES) or path in _LEGACY_LEDGER_PREFIXES:
        return JSONResponse(
            {
                "error": "quarantined",
                "use": "/api/shadow-learning/today",
                "note": "Stage A ledger is Boss shadow (ask→bid), not performance_tracker",
            },
            status_code=410,
        )
    return await call_next(request)

def _legacy_ledger_gone():
    """Stage A stub — middleware also 410s these; body must not touch performance_tracker."""
    return JSONResponse(
        {
            "error": "quarantined",
            "use": "/api/shadow-learning/today",
            "note": "Stage A ledger is Boss shadow (ask→bid), not performance_tracker",
        },
        status_code=410,
    )

# Rate limiting storage (in-memory, for production use Redis)
_rate_limit_store: Dict[str, List[float]] = {}

# Performance monitoring
_performance_metrics = {
    'request_count': 0,
    'error_count': 0,
    'websocket_connections': 0,
    'average_response_time': 0.0,
    'last_cleanup': time.time()
}

# Memory cleanup function
async def cleanup_memory():
    """Periodic cleanup to prevent memory leaks"""
    global _rate_limit_store, _performance_metrics
    
    now = time.time()
    cleanup_interval = 300  # 5 minutes
    
    if now - _performance_metrics['last_cleanup'] < cleanup_interval:
        return
    
    # Clean up old rate limit entries (older than 1 hour)
    cutoff_time = now - 3600
    for ip in list(_rate_limit_store.keys()):
        _rate_limit_store[ip] = [
            req_time for req_time in _rate_limit_store[ip]
            if req_time > cutoff_time
        ]
        # Remove empty entries
        if not _rate_limit_store[ip]:
            del _rate_limit_store[ip]
    
    _performance_metrics['last_cleanup'] = now
    logger.debug(f"Memory cleanup completed. Rate limit entries: {len(_rate_limit_store)}")

def check_rate_limit(client_ip: str, max_requests: int = 100, window_seconds: int = 60) -> bool:
    """
    Simple rate limiting - allows max_requests per window_seconds
    Returns True if request is allowed, False if rate limited
    """
    now = time.time()
    if client_ip not in _rate_limit_store:
        _rate_limit_store[client_ip] = []
    
    # Remove old requests outside the window
    _rate_limit_store[client_ip] = [
        req_time for req_time in _rate_limit_store[client_ip]
        if now - req_time < window_seconds
    ]
    
    # Check if limit exceeded
    if len(_rate_limit_store[client_ip]) >= max_requests:
        return False
    
    # Add current request
    _rate_limit_store[client_ip].append(now)
    return True

# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting to prevent abuse"""
    # Skip rate limiting for WebSocket upgrade requests
    if request.url.path.startswith('/ws/'):
        return await call_next(request)
    
    client_ip = request.client.host if request.client else "unknown"
    
    # More lenient rate limiting for API endpoints
    max_requests = 200 if request.url.path.startswith('/api/') else 100
    window_seconds = 60
    
    if not check_rate_limit(client_ip, max_requests, window_seconds):
        logger.warning(f"Rate limit exceeded for {client_ip} on {request.url.path}")
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded. Please try again later."},
            headers={"Retry-After": str(window_seconds)}
        )
    
    return await call_next(request)

# Security and Performance Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security and performance headers to all responses - ENHANCED"""
    response = await call_next(request)
    
    # Enhanced security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"  # Added back for older browsers
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    # Content Security Policy (CSP) - strict but allows necessary resources
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com; "  # Allow Chart.js CDN
        "style-src 'self' 'unsafe-inline'; "  # Allow inline styles (needed for dynamic styling)
        "img-src 'self' data: https:; "
        "font-src 'self' data: https:; "
        "connect-src 'self' ws: wss:; "  # Allow WebSocket connections
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    response.headers["Content-Security-Policy"] = csp
    
    # HSTS (HTTP Strict Transport Security) - only for HTTPS
    if request.url.scheme == 'https':
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # Performance headers - cache static resources
    # Check if it's a static file by extension OR if it's the root HTML page
    is_static = (
        request.url.path.endswith(('.html', '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.eot')) or
        request.url.path == '/'  # Root path serves HTML
    )
    
    if is_static:
        # HTML must never be cached — UI ships as a single large file and updates often.
        # (Previously max-age=3600 overwrote the route's no-cache headers and hid live UI changes.)
        if (
            request.url.path.endswith('.html')
            or request.url.path == '/'
            or request.url.path in ('/lab-preview', '/hybrid-preview', '/calm-preview')
        ):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        else:
            # For other static resources, use long cache with immutable
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        if "Expires" in response.headers:
            del response.headers["Expires"]
    else:
        # For dynamic content (API endpoints), use no-cache
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        # Expires header removed - Cache-Control is preferred and sufficient
        if "Expires" in response.headers:
            del response.headers["Expires"]
    
    return response

# Request logging middleware with performance monitoring
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests for monitoring with performance tracking"""
    global _performance_metrics
    
    start_time = time.time()
    _performance_metrics['request_count'] += 1
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Update average response time (exponential moving average)
        alpha = 0.1  # Smoothing factor
        _performance_metrics['average_response_time'] = (
            alpha * process_time + (1 - alpha) * _performance_metrics['average_response_time']
        )
        
        # Track errors
        if response.status_code >= 400:
            _performance_metrics['error_count'] += 1
        
        logger.debug(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
        
        # Periodic memory cleanup
        await cleanup_memory()
        
        return response
    except Exception as e:
        _performance_metrics['error_count'] += 1
        logger.error(f"Request error: {e}", exc_info=True)
        raise

# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.symbol_subscriptions: Dict[str, Set[WebSocket]] = {}
        self.last_broadcast_ts: Optional[float] = None
        self.last_broadcast_symbol: Optional[str] = None
    
    async def connect(self, websocket: WebSocket, symbol: str = "SPY"):
        # OPTIMIZED: Reduced logging for faster connection
        logger.debug(f"[ConnectionManager] Accepting WebSocket connection for {symbol}...")
        try:
            await websocket.accept()
            logger.debug(f"[ConnectionManager] WebSocket accepted for {symbol}")
        except Exception as e:
            logger.error(f"[ConnectionManager] Failed to accept WebSocket: {e}")
            raise
        
        self.active_connections.add(websocket)
        logger.debug(f"[ConnectionManager] Added to active_connections. Total: {len(self.active_connections)}")
        
        if symbol not in self.symbol_subscriptions:
            self.symbol_subscriptions[symbol] = set()
            logger.debug(f"[ConnectionManager] Created subscription set for {symbol}")
        
        self.symbol_subscriptions[symbol].add(websocket)
        logger.debug(f"[ConnectionManager] Added websocket to {symbol} subscriptions. Count: {len(self.symbol_subscriptions[symbol])}")
        
        # OPTIMIZED: Only log summary at INFO level, details at DEBUG
        all_subs = {sym: len(conns) for sym, conns in self.symbol_subscriptions.items()}
        logger.info(f"[ConnectionManager] ✅ Client connected for {symbol}. Total: {len(self.active_connections)} connection(s)")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        
        # Remove from all symbol subscriptions
        for symbol, connections in self.symbol_subscriptions.items():
            connections.discard(websocket)
        
        # OPTIMIZED: Reduced logging verbosity
        logger.debug(f"Client disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except Exception as e:
            error_str = str(e).lower()
            # CRITICAL FIX: Better error handling - check for connection errors
            if any(keyword in error_str for keyword in ["disconnect", "closed", "not connected", "connection", "broken", "reset"]):
                logger.warning(f"Connection error sending message: {e} - disconnecting")
                self.disconnect(websocket)
            else:
                # Non-connection error - log but don't disconnect
                logger.debug(f"Error sending message (non-critical): {e}")
    
    async def broadcast_to_symbol(self, message: dict, symbol: str):
        """Broadcast to all clients subscribed to a symbol (never block the updater forever)."""
        if symbol not in self.symbol_subscriptions:
            all_subs = {sym: len(conns) for sym, conns in self.symbol_subscriptions.items()}
            total_subs = sum(len(conns) for conns in self.symbol_subscriptions.values())
            logger.debug(
                f"⚠️ No clients subscribed to {symbol} "
                f"(Total connections: {len(self.active_connections)}, Total subscriptions: {total_subs}, All: {all_subs})"
            )
            return

        disconnected = []
        client_count = len(self.symbol_subscriptions[symbol])
        if client_count > 0:
            logger.debug(f"📤 Broadcasting to {client_count} client(s) for {symbol}")
        self.last_broadcast_ts = time.time()
        self.last_broadcast_symbol = symbol

        # Pre-serialize once — much faster than send_json per client on large Boss payloads
        try:
            payload = json.dumps(message, default=str, allow_nan=False)
        except (TypeError, ValueError):
            try:
                payload = json.dumps(message, default=str)
            except Exception as ser_e:
                logger.warning(f"Broadcast serialize failed for {symbol}: {ser_e}")
                return

        for connection in list(self.symbol_subscriptions[symbol]):
            try:
                # Give real clients time for ~200KB payloads; only drop serial offenders
                await asyncio.wait_for(connection.send_text(payload), timeout=5.0)
                if not hasattr(connection, '_send_fail_streak'):
                    connection._send_fail_streak = 0
                connection._send_fail_streak = 0
            except asyncio.TimeoutError:
                streak = int(getattr(connection, '_send_fail_streak', 0) or 0) + 1
                connection._send_fail_streak = streak
                logger.warning(
                    f"⏱️ Client send slow for {symbol} (streak={streak}) — "
                    f"{'dropping stuck socket' if streak >= 3 else 'keeping connection'}"
                )
                if streak >= 3:
                    disconnected.append(connection)
            except Exception as e:
                error_str = str(e).lower()
                if any(keyword in error_str for keyword in ["disconnect", "closed", "not connected", "connection", "broken", "reset"]):
                    logger.warning(f"❌ Connection error broadcasting to client for {symbol}: {e} - removing from subscriptions")
                    disconnected.append(connection)
                else:
                    logger.debug(f"Non-critical error broadcasting to client for {symbol}: {e}")

        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

def _get_comprehensive_rotation_info(current_source: str, symbol: str = "SPY") -> dict:
    """
    Get comprehensive rotation info including all available APIs and their tracking status
    
    Args:
        current_source: Current data source name (e.g., 'yfinance')
        symbol: Symbol being tracked (default: 'SPY')
    """
    try:
        from multi_source_flow_tracker import multi_source_tracker
        import os
        
        # Get all available sources from tracker
        available_sources = multi_source_tracker.available_sources if hasattr(multi_source_tracker, 'available_sources') else []
        
        # Also check which sources are configured with API keys (even if not in tracker's list yet)
        configured_sources = []
        
        # Check yfinance (always available, no key needed)
        configured_sources.append('yfinance')
        
        # Check Polygon
        from config_loader import get_api_key
        if get_api_key('POLYGON_API_KEY') or get_api_key('MASSIVE_API_KEY'):
            if 'Polygon' not in available_sources:
                configured_sources.append('Polygon')
        
        # Check Finnhub
        if get_api_key('FINNHUB_API_KEY'):
            if 'Finnhub' not in available_sources:
                configured_sources.append('Finnhub')
        
        # Check Alpha Vantage
        if get_api_key('ALPHA_VANTAGE_API_KEY'):
            if 'AlphaVantage' not in available_sources:
                configured_sources.append('AlphaVantage')
        
        # Check IBKR (if configured)
        if os.getenv('IBKR_HOST') or get_api_key('IBKR_HOST'):
            if 'IBKR' not in available_sources:
                configured_sources.append('IBKR')
        
        # Merge lists, removing duplicates and normalizing names
        all_sources = list(set([s.lower() for s in available_sources] + [s.lower() for s in configured_sources]))
        # Convert back to proper case
        source_map = {
            'yfinance': 'yfinance',
            'polygon': 'Polygon',
            'finnhub': 'Finnhub',
            'alphavantage': 'AlphaVantage',
            'ibkr': 'IBKR'
        }
        available_sources = [source_map.get(s, s.title()) for s in all_sources if s in source_map]
        
        # Prefer tracker's canonical priority order when present
        tracker_avail = list(getattr(multi_source_tracker, 'available_sources', []) or [])
        if tracker_avail:
            # Keep tracker order; append any extra configured names not yet detected
            extras = [s for s in available_sources if s not in tracker_avail]
            available_sources = tracker_avail + extras

        primary_source = (
            multi_source_tracker.primary_source()
            if hasattr(multi_source_tracker, 'primary_source')
            else (tracker_avail[0] if tracker_avail else (available_sources[0] if available_sources else 'yfinance'))
        )
        cold_map = {}
        plan_limited = {}
        try:
            now_ts = __import__('time').time()
            for k, v in getattr(multi_source_tracker, 'source_cold_until', {}).items():
                if v and float(v) > now_ts:
                    cold_map[k] = int(float(v) - now_ts)
            plan_limited = dict(getattr(multi_source_tracker, 'source_plan_limited', {}) or {})
        except Exception:
            cold_map = {}
            plan_limited = {}

        # Normalize current_source casing to match badge names
        cur_l = (current_source or '').lower().replace(' ', '')
        norm_map = {
            'yfinance': 'yfinance',
            'yfinance_fallback': 'yfinance',
            'polygon': 'Polygon',
            'massive': 'Polygon',
            'finnhub': 'Finnhub',
            'alphavantage': 'AlphaVantage',
            'alpha_vantage': 'AlphaVantage',
            'ibkr': 'IBKR',
        }
        current_source = norm_map.get(cur_l, current_source or primary_source)

        # Get rotation info from multi_source_tracker (per-symbol tracking)
        rotation_interval = getattr(multi_source_tracker, 'rotation_interval', 3)
        
        # Get per-symbol rotation index
        source_rotation_index = getattr(multi_source_tracker, 'source_rotation_index', {})
        rotation_index = source_rotation_index.get(symbol, 0)
        
        # Get per-symbol use count for current source
        source_use_count = getattr(multi_source_tracker, 'source_use_count', {})
        symbol_use_counts = source_use_count.get(symbol, {})
        use_count = symbol_use_counts.get(current_source, 0)
        
        # Get total use counts (across all symbols)
        total_source_use_count = getattr(multi_source_tracker, 'total_source_use_count', {})
        
        # Get rotation history count
        rotation_history = getattr(multi_source_tracker, 'rotation_history', [])
        rotation_count = len(rotation_history)
        
        # Health failover — no timed rotate-away from primary
        uses_until_rotation = 0
        
        # Get rotation info
        rotation_info = {
            'available_sources': available_sources,
            'current_source': current_source,
            'primary_source': primary_source,
            'role': 'primary' if current_source == primary_source else 'backup',
            'policy': 'primary_sticky_backup_failover',
            'cold_sources': cold_map,
            'plan_limited': plan_limited,
            'rotation_interval': rotation_interval,
            'rotation_index': rotation_index,
            'use_count': use_count,
            'uses_until_rotation': uses_until_rotation,
            'all_source_use_counts': total_source_use_count,
            'rotation_count': rotation_count,
            'total_uses': sum(total_source_use_count.values()) if total_source_use_count else 0
        }
        
        # Get API tracking status for all configured sources
        api_status = {}
        for api_name in available_sources:
            try:
                can_request, reason = api_tracker.can_make_request(api_name)
                usage = api_tracker.get_usage_stats(api_name)
                api_status[api_name] = {
                    'available': api_name in available_sources,
                    'can_request': can_request,
                    'reason': reason if not can_request else 'OK',
                    'usage': usage,
                    'is_current': api_name == current_source
                }
            except Exception as e:
                api_status[api_name] = {
                    'available': False,
                    'can_request': False,
                    'reason': str(e),
                    'usage': {},
                    'is_current': False
                }
        
        rotation_info['api_status'] = api_status
        
        return rotation_info
    except Exception as e:
        logger.debug(f"Error getting comprehensive rotation info: {e}")
        # Fallback
        return {
            'available_sources': [current_source] if current_source else ['yfinance'],
            'current_source': current_source or 'yfinance',
            'rotation_interval': 3,
            'api_status': {}
        }


def _compute_signal_strength(boss_decision: dict, signal: dict, flow_metrics: dict, unusual_activity) -> dict:
    """
    Authoritative strength for UI / bubble — Boss confidence weighted with live chain volume.
    Avoids client scraping mismatched DOM fields from different sources.
    """
    boss = boss_decision if isinstance(boss_decision, dict) else {}
    sig = signal if isinstance(signal, dict) else {}
    fm = flow_metrics if isinstance(flow_metrics, dict) else {}

    conf = boss.get('confidence')
    if conf is None:
        conf = sig.get('confidence', 0)
    try:
        conf = float(conf or 0)
    except (TypeError, ValueError):
        conf = 0.0

    call_vol = float(fm.get('total_call_volume') or 0)
    put_vol = float(fm.get('total_put_volume') or 0)
    total_vol = call_vol + put_vol

    unusual_count = 0
    if isinstance(unusual_activity, dict):
        unusual_count = int(unusual_activity.get('count') or len(unusual_activity.get('trades') or []) or 0)
    elif isinstance(unusual_activity, list):
        unusual_count = len(unusual_activity)

    # Same banded formula as before, but server-side from Boss + live metrics
    strength = conf * 0.6
    strength += min(25.0, (total_vol / 50000.0) * 25.0)
    strength += min(15.0, unusual_count * 5.0)
    strength = int(min(100, max(0, round(strength))))

    action = (boss.get('action') or sig.get('action') or 'NO_TRADE')
    return {
        'score': strength,
        'confidence_used': conf,
        'volume_used': int(total_vol),
        'unusual_count': unusual_count,
        'source': 'boss+chain' if boss.get('confidence') is not None else 'signal+chain',
        'action': action,
    }


# Background task for continuous data updates
# Track if we've already checked 1DTE after market close
_after_hours_1dte_checked = {}  # symbol -> bool
_last_session = {}  # symbol -> str (to detect session changes)

# Performance optimization: Track update counts for throttling heavy calculations
# CHANGED: Reduced throttling interval from 3 to 2 for more consistent data
_update_counters = {}  # symbol -> counter
_HEAVY_CALC_INTERVAL = 2  # Default; open-protect uses 3+
_last_pm_options_fetch = {}  # symbol -> ts (rare pre-market chain warm-ups only)

# Track last known data source per symbol to avoid 'none' errors
_last_known_data_source = {}  # symbol -> str (e.g., 'yfinance', 'Finnhub')
_data_source_failure_count = {}  # symbol -> int (count consecutive failures)

# CRITICAL: Cache last successful flow_data per symbol - use when current fetch fails
_last_successful_flow_data = {}  # symbol -> dict (full flow_data structure)
_last_successful_data_timestamp = {}  # symbol -> float (timestamp of when data was cached)
_last_expiry_terms = {}  # symbol -> last good expiry_terms payload (with buckets)
# Backoff tracking for yfinance rate limits/errors
_yfinance_backoff_until = {}  # symbol -> timestamp
_rate_limit_last_log = {}  # api_name -> timestamp (throttle warning spam)
_yfinance_last_warning = {}  # symbol -> timestamp to prevent log spam


def _desk_offline() -> bool:
    try:
        from offline_mode import live_market_blocked

        return bool(live_market_blocked())
    except Exception:
        return False


def _offline_status() -> dict:
    try:
        from offline_mode import status_dict

        return status_dict()
    except Exception:
        return {"offline": False, "live_fetches": True}


def _flow_is_stale(flow_data) -> bool:
    if _desk_offline():
        return True
    try:
        from offline_mode import payload_is_stale

        return bool(payload_is_stale(flow_data if isinstance(flow_data, dict) else None))
    except Exception:
        return False


def _persist_live_snapshot(symbol: str, flow_data: dict, boss_decision=None) -> None:
    if not isinstance(flow_data, dict) or _flow_is_stale(flow_data):
        return
    if float(flow_data.get("stock_price") or 0) <= 0:
        return
    try:
        from offline_mode import capture_live_snapshot

        capture_live_snapshot(symbol, flow_data, boss=boss_decision or flow_data.get("boss_decision"))
    except Exception:
        pass


def _sit_out_boss_paint(flow_data=None, last_boss=None):
    try:
        from offline_mode import sit_out_boss

        prior = last_boss
        if not isinstance(prior, dict) and isinstance(flow_data, dict):
            prior = flow_data.get("boss_decision")
        return sit_out_boss(prior if isinstance(prior, dict) else None)
    except Exception:
        return {
            "action": "NO_TRADE",
            "can_auto_paper": False,
            "executable": False,
            "offline": True,
            "stale_paint": True,
            "data_quality": "offline_stale",
            "reason": "OFFLINE — sitting out",
            "veto_flags": ["OFFLINE_STALE"],
            "hard_vetoes": ["OFFLINE_STALE"],
        }


def _et_now_time():
    """Current time-of-day in America/New_York."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo('America/New_York')).time()
    except Exception:
        return datetime.now().time()


def _is_open_protect_window(session: str) -> bool:
    """9:25–10:00 ET REGULAR — protect Yahoo budget for the pump, not thrash it."""
    if session != 'REGULAR':
        return False
    t = _et_now_time()
    return dt_time(9, 25) <= t <= dt_time(10, 0)


def _loop_sleep_seconds(session: str, update_interval: float, time_spent: float) -> float:
    """Session-aware cadence. Burn rate at open is what nuked today's data."""
    if session == 'PRE_MARKET':
        return 15.0
    if _is_open_protect_window(session):
        return max(5.0, update_interval)
    if session == 'REGULAR':
        return max(0.5, float(update_interval) - float(time_spent))
    if session in ('AFTER_HOURS', 'OVERNIGHT'):
        return 12.0
    return 20.0

async def _send_immediate_symbol_data(websocket: WebSocket, symbol: str):
    """Send immediate data for a symbol when client subscribes"""
    try:
        logger.info(f"📡 Sending immediate data for {symbol} to new subscriber")
        from multi_source_flow_tracker import multi_source_tracker
        from market_hours_detector import get_market_status
        loop = asyncio.get_event_loop()
        session = (get_market_status() or {}).get('session', 'UNKNOWN')
        closed_session = session in ('WEEKEND', 'OVERNIGHT')

        flow_data = None

        if _desk_offline():
            try:
                from offline_mode import serve_offline_flow

                flow_data = serve_offline_flow(symbol)
                if symbol in _last_successful_flow_data and float((_last_successful_flow_data[symbol] or {}).get("stock_price") or 0) > 0:
                    # Prefer in-memory hydrate if disk snapshot was empty
                    if not flow_data or float(flow_data.get("stock_price") or 0) <= 0:
                        flow_data = _last_successful_flow_data[symbol]
            except Exception as e:
                logger.debug(f"offline immediate serve: {e}")
            if flow_data:
                await _format_and_send_data(websocket, symbol, flow_data)
            else:
                logger.warning(f"OFFLINE — no snapshot for {symbol} on connect")
            return

        # Prefer cache (accept stale on weekend/overnight — no live chain expected)
        try:
            cache_key = f"{symbol}_0dte"
            if hasattr(multi_source_tracker, 'cache') and cache_key in multi_source_tracker.cache:
                cached_data, cache_time = multi_source_tracker.cache[cache_key]
                current_time = time.time()
                max_age = multi_source_tracker.cache_duration * (20 if closed_session else 2)
                age = current_time - cache_time
                if age < max_age and cached_data:
                    logger.info(f"✅ Using cached data for {symbol} (age: {age:.1f}s, session={session})")
                    flow_data = cached_data
        except Exception as e:
            logger.debug(f"Cache check failed for {symbol}: {e}")

        # Fresh fetch — skip on weekend/overnight when we already have usable cache
        if not flow_data and not closed_session:
            try:
                logger.info(f"🔄 Fetching fresh data for {symbol}...")
                flow_data = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        multi_source_tracker.get_0dte_options_chain,
                        symbol
                    ),
                    timeout=15.0
                )
                if flow_data:
                    logger.info(f"✅ Got fresh data for {symbol}")
            except asyncio.TimeoutError:
                logger.warning(f"⏱️ Timeout fetching data for {symbol}")
            except (IndexError, ValueError) as e:
                logger.warning(f"❌ Fetch failed for {symbol} (empty/partial chain): {e}")
            except Exception as e:
                logger.warning(f"❌ Error fetching data for {symbol}: {e}")
        elif not flow_data and closed_session:
            # Last resort: one guarded fetch so reconnect still gets Friday close / nearest expiry
            try:
                logger.info(f"🔄 Weekend/overnight guarded fetch for {symbol}...")
                flow_data = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        multi_source_tracker.get_0dte_options_chain,
                        symbol
                    ),
                    timeout=20.0
                )
            except Exception as e:
                logger.info(f"ℹ️ Closed-session fetch skipped/failed for {symbol}: {e}")

        if flow_data:
            await _format_and_send_data(websocket, symbol, flow_data)
        else:
            logger.warning(
                f"⚠️ No data available for {symbol} on immediate fetch "
                f"(session={session}) — initial connect payload or next open will refresh"
            )
    except Exception as e:
        logger.error(f"❌ Error sending immediate data for {symbol}: {e}", exc_info=True)

async def _format_and_send_data(websocket: WebSocket, symbol: str, flow_data: dict):
    """Format and send data to client"""
    # CRITICAL: Defensive check - flow_data must be a dict
    if flow_data is None:
        logger.warning(f"⚠️ flow_data is None for {symbol} - cannot format and send")
        return
    if not isinstance(flow_data, dict):
        logger.warning(f"⚠️ flow_data is not a dict for {symbol} (type: {type(flow_data)}) - cannot format and send")
        return
    
    try:
        from market_hours_detector import get_market_status
        from zerodte_signal_analyzer import ZeroDTESignalAnalyzer
        from order_flow_history import order_flow_history
        
        market_status = get_market_status()
        flow_history_data = order_flow_history.get_recent_flow(symbol, count=50)
        
        # CRITICAL FIX: Get historical flow data for price momentum calculation
        historical_flow = []
        try:
            # Try to get from multi_source_tracker first
            if hasattr(multi_source_tracker, 'flow_history') and symbol in multi_source_tracker.flow_history:
                historical_flow = multi_source_tracker.flow_history[symbol][-10:]  # Last 10 data points
            # Fallback to flow_tracker
            elif hasattr(flow_tracker, 'flow_history') and symbol in flow_tracker.flow_history:
                historical_flow = flow_tracker.flow_history[symbol][-10:]
        except Exception as e:
            logger.debug(f"Could not get historical flow for momentum: {e}")
        
        # Get signal analysis using the correct analyzer
        signal_analyzer_instance = ZeroDTESignalAnalyzer()
        try:
            # CRITICAL FIX: Pass historical_flow for price momentum calculation
            signal_analysis = signal_analyzer_instance.analyze_flow_signal(flow_data, historical_flow)
        except Exception as e:
            logger.warning(f"Signal analysis failed for {symbol}: {e}")
            signal_analysis = {
                'action': 'NO_TRADE',
                'confidence': 0,
                'reasoning': 'Signal analysis unavailable',
                'signal_type': 'WAIT'
            }
        
        # Phase 1: Add Real-Time Greeks, IV Surface, and Order Flow Analysis
        advanced_analysis = {}
        
        # 1. Real-Time Greeks Calculation
        if REALTIME_GREEKS_AVAILABLE and realtime_greeks_calculator:
            try:
                options_chain = flow_data.get('options_chain', {})
                stock_price = flow_data.get('stock_price', 0)
                
                if options_chain and stock_price > 0:
                    greeks_analysis = realtime_greeks_calculator.calculate_greeks_for_chain(
                        options_chain, stock_price
                    )
                    advanced_analysis['greeks'] = greeks_analysis
            except Exception as e:
                logger.debug(f"Greeks calculation failed: {e}")
        
        # 2. IV Surface Analysis
        if IV_SURFACE_AVAILABLE and iv_surface_analyzer:
            try:
                options_chain = flow_data.get('options_chain', {})
                stock_price = flow_data.get('stock_price', 0)
                
                if options_chain and stock_price > 0:
                    iv_analysis = iv_surface_analyzer.analyze_iv_surface(
                        options_chain, stock_price
                    )
                    advanced_analysis['iv_surface'] = iv_analysis
            except Exception as e:
                logger.debug(f"IV surface analysis failed: {e}")
        
        # 3. Order Flow Imbalance Detection
        if ORDER_FLOW_AVAILABLE and order_flow_imbalance_detector:
            try:
                options_chain = flow_data.get('options_chain', {})
                stock_price = flow_data.get('stock_price', 0)
                
                if options_chain and stock_price > 0:
                    flow_imbalance = order_flow_imbalance_detector.detect_imbalance(
                        options_chain, None, stock_price
                    )
                    advanced_analysis['order_flow'] = flow_imbalance
            except Exception as e:
                logger.debug(f"Order flow analysis failed: {e}")
        
        # Format message - CRITICAL: symbol must be at top level
        # Convert any datetime objects and non-JSON types to strings for JSON serialization
        def convert_datetime(obj):
            import numpy as np
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, (np.bool_, bool)):
                # Handle numpy bool and regular bool
                return bool(obj)
            elif isinstance(obj, (np.integer, int)):
                return int(obj)
            elif isinstance(obj, (np.floating, float)):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetime(item) for item in obj]
            return obj
        
        # CRITICAL: Extract all_calls and all_puts using helper function
        calls_data, puts_data = extract_options_data(flow_data, symbol)
        
        # FINAL FALLBACK: Try cached data if still empty
        if (not calls_data or not puts_data) and symbol in _last_successful_flow_data:
            cached_data = _last_successful_flow_data[symbol]
            if cached_data:
                cached_calls, cached_puts = extract_options_data(cached_data, "")
                if not calls_data and cached_calls:
                    calls_data = cached_calls
                if not puts_data and cached_puts:
                    puts_data = cached_puts
                if calls_data or puts_data:
                    logger.info(f"✅ Using cached options data: {len(calls_data)} calls, {len(puts_data)} puts")
        
        # Clean data for JSON serialization
        clean_flow_data = convert_datetime(flow_data) if flow_data else {}
        clean_signal = convert_datetime(signal_analysis) if signal_analysis else {}
        
        # CRITICAL: Ensure all_calls and all_puts are at top level of data object
        clean_flow_data['all_calls'] = convert_datetime(calls_data)
        clean_flow_data['all_puts'] = convert_datetime(puts_data)

        # Closed / snapshot path used to omit Boss — attach a real decide() so UI isn't blank
        boss_decision = {}
        paper_boss = {}
        try:
            stock_px = float(clean_flow_data.get('stock_price') or 0)
            stale_now = _flow_is_stale(clean_flow_data)
            if stale_now:
                last_boss = None
                if isinstance(clean_flow_data.get('boss_decision'), dict):
                    last_boss = clean_flow_data.get('boss_decision')
                elif symbol in _last_successful_flow_data and isinstance((_last_successful_flow_data[symbol] or {}).get('boss_decision'), dict):
                    last_boss = _last_successful_flow_data[symbol].get('boss_decision')
                boss_decision = _sit_out_boss_paint(clean_flow_data, last_boss)
                clean_signal['boss_decision'] = boss_decision
                clean_flow_data['boss_decision'] = boss_decision
                clean_flow_data['offline'] = True
                clean_flow_data['stale'] = True
                clean_flow_data['data_freshness'] = 'OFFLINE'
                armed = False
                if paper_trading_engine:
                    paper_boss = {
                        'armed': False,
                        'arm_status': paper_arm_state.status() if paper_arm_state else {},
                        'open_positions': paper_trading_engine.get_open_positions(),
                        'performance': paper_trading_engine.get_performance(),
                        'risk': paper_trading_engine.risk_status(),
                        'offline': True,
                        'can_auto_paper': False,
                    }
                clean_signal['paper_boss'] = paper_boss
                clean_flow_data['paper_boss'] = paper_boss
            elif BOSS_ENGINE_AVAILABLE and boss_decision_engine and stock_px > 0:
                armed = bool(paper_arm_state.armed) if paper_arm_state else False
                boss_decision = boss_decision_engine.decide(
                    symbol=symbol,
                    stock_price=stock_px,
                    flow_signal={
                        'action': clean_signal.get('action', 'NO_TRADE'),
                        'confidence': clean_signal.get('confidence', 0),
                        'reason': clean_signal.get('reasoning') or clean_signal.get('reason') or 'snapshot',
                    },
                    calls=calls_data,
                    puts=puts_data,
                    options_chain={'calls': calls_data or [], 'puts': puts_data or []},
                    paper_armed=armed,
                )
                clean_signal['boss_decision'] = boss_decision
                clean_flow_data['boss_decision'] = boss_decision
                if paper_trading_engine:
                    paper_boss = {
                        'armed': armed,
                        'arm_status': paper_arm_state.status() if paper_arm_state else {},
                        'open_positions': paper_trading_engine.get_open_positions(),
                        'performance': paper_trading_engine.get_performance(),
                        'risk': paper_trading_engine.risk_status(),
                    }
                clean_signal['paper_boss'] = paper_boss
                clean_flow_data['paper_boss'] = paper_boss
                if not stale_now:
                    _persist_live_snapshot(symbol, clean_flow_data, boss_decision)
        except Exception as e:
            logger.debug(f"_format_and_send_data Boss attach failed for {symbol}: {e}")
            boss_decision = {'action': 'NO_TRADE', 'confidence': 0, 'reason': 'Boss unavailable on snapshot'}
            clean_flow_data['boss_decision'] = boss_decision
            clean_signal['boss_decision'] = boss_decision
        
        # Log what we're sending
        logger.info(f"[_format_and_send_data] Sending data for {symbol}: stock_price={clean_flow_data.get('stock_price', 0)}, calls={len(clean_flow_data.get('all_calls', []))}, puts={len(clean_flow_data.get('all_puts', []))}, boss={boss_decision.get('action')}")
        try:
            app.state.last_boss_action = (boss_decision or {}).get("action")
        except Exception:
            pass
        
        # Add advanced analysis to message
        clean_advanced_analysis = convert_datetime(advanced_analysis) if advanced_analysis else {}
        
        message = {
            'type': 'flow_update',
            'symbol': symbol,  # Top level - frontend reads this
            'timestamp': datetime.now().isoformat(),
            'data': clean_flow_data,
            'signal': clean_signal,
            'market_status': market_status,
            'offline': bool(clean_flow_data.get('offline') or _desk_offline()),
            'advanced_analysis': clean_advanced_analysis,  # Phase 1 upgrades
            # Also mirror Boss at top of data habit used by main updater
        }
        # Ensure client paths that read data.boss_decision work
        if isinstance(message['data'], dict):
            message['data']['boss_decision'] = convert_datetime(boss_decision) if boss_decision else {}
            message['data']['paper_boss'] = convert_datetime(paper_boss) if paper_boss else {}
            try:
                message['data']['trade_lesson'] = _trade_lesson_payload(boss_decision, paper_boss)
            except Exception:
                pass
            # Snapshot path omits tenor mix. Attach last-good buckets for this symbol only.
            existing_terms = message['data'].get('expiry_terms')
            if not (isinstance(existing_terms, dict) and existing_terms.get('buckets')):
                cached_terms = _last_expiry_terms.get(symbol)
                if isinstance(cached_terms, dict) and cached_terms.get('buckets'):
                    message['data']['expiry_terms'] = cached_terms
                else:
                    message['data'].pop('expiry_terms', None)
        
        await manager.send_personal_message(message, websocket)
        logger.info(f"✅ Sent immediate data for {symbol} (stock_price: {flow_data.get('stock_price', 0)})")
    except Exception as e:
        logger.error(f"❌ Error formatting data for {symbol}: {e}", exc_info=True)

async def background_data_updater(update_interval: float = 2.5):
    """
    Continuously fetch and broadcast flow data with API tracking and market hours logic
    
    Update Rules:
    - WEEKEND/OVERNIGHT: Rare closed snapshots (official close); do not hammer Yahoo
    - Options: Only update during REGULAR market hours (9:30 AM - 4:00 PM ET)
    - Stock prices: Update during PRE_MARKET, REGULAR, AFTER_HOURS (Yahoo-throttled)
    - Yahoo Stage A: min ~2.5s between chain fetches; rebroadcast last snapshot while cooling
    """
    logger.info(f"Starting background data updater with Yahoo throttle (interval={update_interval}s)")
    
    current_symbols = set()
    loop_iteration = 0
    loop_start_time = time.time()  # Track loop timing for consistent intervals
    last_market_scan = 0  # Track last market data scan time
    
    try:
        while True:
            loop_iteration += 1
            try:
                # Log every 20 iterations to confirm loop is running
                if loop_iteration % 20 == 0:
                    logger.info(f"💓 Background updater loop iteration #{loop_iteration} - still running!")

                if _desk_offline():
                    try:
                        from offline_mode import serve_offline_flow

                        market_status = get_market_status()
                        targets = {s for s in manager.symbol_subscriptions.keys() if s == 'SPY'} or {'SPY'}
                        for symbol in targets:
                            snap = None
                            if symbol in _last_successful_flow_data:
                                snap = _last_successful_flow_data[symbol]
                            if not snap or float((snap or {}).get('stock_price') or 0) <= 0:
                                snap = serve_offline_flow(symbol)
                            if not isinstance(snap, dict):
                                snap = serve_offline_flow(symbol)
                            snap = dict(snap)
                            snap['market_status'] = market_status
                            snap['offline'] = True
                            snap['stale'] = True
                            snap['data_freshness'] = 'OFFLINE'
                            snap['live'] = False
                            last_boss = snap.get('boss_decision') if isinstance(snap.get('boss_decision'), dict) else None
                            snap['boss_decision'] = _sit_out_boss_paint(snap, last_boss)
                            _last_successful_flow_data[symbol] = snap
                            subscribers = list(manager.symbol_subscriptions.get(symbol, set()) or [])
                            if subscribers:
                                for ws in subscribers:
                                    try:
                                        await _format_and_send_data(ws, symbol, snap)
                                    except Exception as e:
                                        logger.debug(f"offline broadcast failed for {symbol}: {e}")
                            else:
                                # Keep updater_alive even with no clients
                                pass
                        await asyncio.sleep(5.0)
                        continue
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        logger.debug(f"offline updater: {e}")
                        await asyncio.sleep(5.0)
                        continue
                
                # Periodic market data scan — NEVER during pre-market / open-protect (burns Yahoo)
                current_time = time.time()
                _sess_for_scan = (get_market_status() or {}).get('session', 'UNKNOWN')
                if (
                    current_time - last_market_scan >= 300
                    and _sess_for_scan == 'REGULAR'
                    and not _is_open_protect_window(_sess_for_scan)
                ):
                    try:
                        logger.info("📊 Running comprehensive market data scan for prediction enhancement...")
                        loop = asyncio.get_running_loop()
                        # Run market scan in executor to avoid blocking
                        if market_data_scanner is not None:
                            await loop.run_in_executor(
                                None,
                                market_data_scanner.scan_market_data,
                                "SPY"
                            )
                        last_market_scan = current_time
                        logger.debug("✅ Market data scan complete")
                    except Exception as e:
                        logger.debug(f"Market data scan error (non-critical): {e}")
                
                # Get all subscribed symbols - FILTER OUT QQQ (removed from app)
                # Only process SPY to avoid unnecessary data fetching and errors
                all_subscribed = set(manager.symbol_subscriptions.keys())
                current_symbols = {s for s in all_subscribed if s == 'SPY'}  # Only SPY
                
                if not current_symbols:
                    # No SPY subscriptions, wait a bit
                    logger.debug(f"⏸️ No SPY subscriptions - waiting... (Total connections: {len(manager.active_connections)}, All symbols: {all_subscribed})")
                    await asyncio.sleep(0.5)  # ACCELERATED: Reduced from 1.0s
                    continue
                
                # Get market status
                market_status = get_market_status()
                current_session = market_status.get('session', 'UNKNOWN')
                
                # WEEKEND / OVERNIGHT: rebroadcast closed snapshot (official close, not last 1m tick)
                if current_session in ('WEEKEND', 'OVERNIGHT'):
                    loop = asyncio.get_event_loop()
                    for symbol in current_symbols:
                        try:
                            snap = None
                            # Prefer a fresh Yahoo marks+chain pull so we don't stick on stale 1m close
                            try:
                                snap = await asyncio.wait_for(
                                    loop.run_in_executor(
                                        None,
                                        multi_source_tracker.get_0dte_options_chain,
                                        symbol,
                                    ),
                                    timeout=20.0,
                                )
                                if snap and isinstance(snap, dict) and float(snap.get('stock_price') or 0) > 0:
                                    _last_successful_flow_data[symbol] = snap.copy()
                            except Exception as e:
                                logger.info(f"Closed-session snapshot fetch for {symbol}: {e}")
                            if (not snap or float(snap.get('stock_price') or 0) <= 0) and symbol in _last_successful_flow_data:
                                snap = _last_successful_flow_data[symbol].copy()
                            if not snap or not isinstance(snap, dict):
                                continue
                            # Overlay official close marks if chain payload still has 1m drift
                            try:
                                from multi_source_flow_tracker import resolve_yfinance_marks
                                import yfinance as yf
                                marks = await loop.run_in_executor(
                                    None,
                                    lambda: resolve_yfinance_marks(yf.Ticker(symbol), session=current_session),
                                )
                                if marks.get('regular_close'):
                                    snap['regular_close'] = marks['regular_close']
                                    snap['stock_price'] = marks['stock_price'] or marks['regular_close']
                                if marks.get('aftermarket_price'):
                                    snap['aftermarket_price'] = marks['aftermarket_price']
                                if marks.get('premarket_price'):
                                    snap['premarket_price'] = marks['premarket_price']
                            except Exception as e:
                                logger.debug(f"Closed-session mark overlay failed for {symbol}: {e}")
                            snap['data_freshness'] = 'CLOSED'
                            snap['snapshot_mode'] = True
                            snap['market_status'] = market_status
                            # Do NOT delete tracker cache every closed cycle — that forces Yahoo spam.
                            # Closed loop already sleeps 180s between refreshes.
                            subscribers = list(manager.symbol_subscriptions.get(symbol, set()))
                            for ws in subscribers:
                                try:
                                    await _format_and_send_data(ws, symbol, snap)
                                except Exception as e:
                                    logger.debug(f"Closed snapshot send failed for {symbol}: {e}")
                            if subscribers:
                                logger.info(
                                    f"📦 Closed snapshot ({current_session}) for {symbol} "
                                    f"close={snap.get('regular_close') or snap.get('stock_price')} "
                                    f"ah={snap.get('aftermarket_price')} subs={len(subscribers)}"
                                )
                        except Exception as e:
                            logger.debug(f"Closed snapshot error for {symbol}: {e}")
                    await asyncio.sleep(180.0)
                    continue
                
                # Update each subscribed symbol (only SPY now)
                if current_symbols:
                    logger.debug(f"🔄 Background updater: Processing {len(current_symbols)} symbol(s): {current_symbols} | Session: {current_session}")
                else:
                    logger.debug(f"⚠️ Background updater: No SPY subscribed! Active connections: {len(manager.active_connections)}")
                    # If no symbols but we have connections, wait a bit for subscriptions
                    if len(manager.active_connections) > 0:
                        logger.info(f"⏳ Waiting for SPY subscription... ({len(manager.active_connections)} connection(s) active)")
                    await asyncio.sleep(0.5)  # ACCELERATED: Reduced from 1.0s
                    continue
                
                for symbol in current_symbols:
                    # Detect session change - reset 1DTE check flag when entering REGULAR hours
                    last_session = _last_session.get(symbol, '')
                if current_session == 'REGULAR' and last_session != 'REGULAR':
                    # Just entered regular hours - reset the flag and start constant 0DTE checks
                    _after_hours_1dte_checked[symbol] = False
                    logger.info(f"Market opened - starting constant 0DTE checks for {symbol}")
                _last_session[symbol] = current_session
                
                # Determine update behavior based on session
                # OPTIONS: Only update during REGULAR market hours
                # STOCK PRICES: Update during PRE_MARKET, REGULAR, AFTER_HOURS, OVERNIGHT
                
                if current_session == 'REGULAR':
                    # Regular hours: Update options (0DTE) and stock prices
                    should_update_options = True
                    should_update_stock_prices = True
                    target_dte = 0
                elif current_session == 'AFTER_HOURS':
                    # After hours: stock only — do NOT burn Yahoo on 1DTE preview every loop
                    should_update_options = False
                    should_update_stock_prices = True
                    target_dte = None
                elif current_session == 'OVERNIGHT':
                    should_update_options = False
                    should_update_stock_prices = True
                    target_dte = None
                elif current_session == 'PRE_MARKET':
                    # PRE-MARKET: spot/PM often; options rarely — thrashing chain all morning
                    # is exactly what opened the circuit breaker into today's pump.
                    should_update_stock_prices = True
                    now_ts = time.time()
                    last_opt = float(_last_pm_options_fetch.get(symbol, 0) or 0)
                    et_t = _et_now_time()
                    near_open = et_t >= dt_time(9, 15)
                    gap = 90.0 if near_open else 180.0
                    should_update_options = (now_ts - last_opt) >= gap
                    target_dte = 0 if should_update_options else None
                else:
                    # Should not reach here (WEEKEND handled above)
                    should_update_options = False
                    should_update_stock_prices = False
                    target_dte = None
                
                # Skip only if both options and stock prices are disabled (e.g., weekend)
                if not should_update_options and not should_update_stock_prices:
                    logger.debug(f"⏸️ Skipping {symbol} - options={should_update_options}, stock={should_update_stock_prices}, session={current_session}")
                    await asyncio.sleep(30.0)
                    continue
                
                # No forced extended-hours options fetches (was burning Yahoo into the open)
                
                try:
                    # Clear cache to get fresh data (but respect cache duration to avoid rate limiting)
                    # Only clear if cache is old
                    if hasattr(flow_tracker, 'cache'):
                        cache_key = f"{symbol}_0dte"
                        if cache_key in flow_tracker.cache:
                            cached_data, cache_time = flow_tracker.cache[cache_key]
                            current_time = time.time()
                            # Only clear if cache is older than cache_duration
                            if (current_time - cache_time) >= flow_tracker.cache_duration:
                                del flow_tracker.cache[cache_key]
                    
                    # Market status already retrieved above
                    
                    # Check API rate limits before making requests
                    # Determine which API will be used (from multi_source_tracker)
                    primary_api = multi_source_tracker.available_sources[0] if multi_source_tracker.available_sources else 'yfinance'
                    
                    # Check if we can make API request
                    can_request, reason = api_tracker.can_make_request(primary_api)
                    if not can_request:
                        # Sleep the full backoff — do NOT spin every 0.5s (Yahoo circuit thrash)
                        wait_s = float(api_tracker.seconds_until_available(primary_api) or 0.0)
                        if wait_s <= 0:
                            import re as _re
                            m = _re.search(r'(\d+(?:\.\d+)?)\s*seconds?', str(reason or ''), _re.I)
                            wait_s = float(m.group(1)) if m else 15.0
                        wait_s = min(max(wait_s + 0.75, 2.0), 120.0)

                        now_log = time.time()
                        last_log = _rate_limit_last_log.get(primary_api, 0)
                        if now_log - last_log >= 20.0:
                            logger.warning(
                                f"API {primary_api} cooling down: {reason} — sleeping {wait_s:.0f}s "
                                f"(holding last cache; not hammering Yahoo)"
                            )
                            _rate_limit_last_log[primary_api] = now_log

                        # Heartbeat cached flow every ~3s while cooling — never freeze UI for full wait_s
                        deadline = time.time() + wait_s
                        while time.time() < deadline:
                            remaining = max(0.0, deadline - time.time())
                            try:
                                cached = _last_successful_flow_data.get(symbol) or {}
                                spot = float(cached.get('stock_price') or 0)
                                if spot <= 0:
                                    spot = float((flow_data or {}).get('stock_price') or 0) if isinstance(flow_data, dict) else 0
                                if spot > 0 and manager.symbol_subscriptions.get(symbol):
                                    # Hold last paint. Do not re-run Boss, do not send
                                    # a ticking "cooling Ns" error — that toast/banner
                                    # is what makes the page jump while Yahoo waits.
                                    last_boss = cached.get('boss_decision') if isinstance(cached.get('boss_decision'), dict) else None
                                    last_signal = cached.get('signal') if isinstance(cached.get('signal'), dict) else None
                                    warm_data = {
                                        'stock_price': spot,
                                        'regular_close': cached.get('regular_close') or spot,
                                        'premarket_price': cached.get('premarket_price') or 0,
                                        'aftermarket_price': cached.get('aftermarket_price') or 0,
                                        'all_calls': cached.get('all_calls') or [],
                                        'all_puts': cached.get('all_puts') or [],
                                        'market_status': market_status,
                                        'data_source': _last_known_data_source.get(symbol, primary_api),
                                        'data_freshness': cached.get('data_freshness') or 'RECENT',
                                        'lite_tick': True,
                                        'yahoo_cooling': True,
                                        'signal': last_signal or {
                                            'action': (last_boss or {}).get('action', 'NO_TRADE'),
                                            'confidence': (last_boss or {}).get('confidence', 0),
                                        },
                                        'shadow_learning': cached.get('shadow_learning') or {},
                                        'dte': 0 if current_session == 'REGULAR' else cached.get('dte', 0),
                                        'expiration_label': cached.get('expiration_label') or '0DTE',
                                    }
                                    if last_boss:
                                        warm_data['boss_decision'] = last_boss
                                    if isinstance(_last_expiry_terms.get(symbol), dict) and _last_expiry_terms[symbol].get('buckets'):
                                        warm_data['expiry_terms'] = _last_expiry_terms[symbol]
                                    warm = {
                                        'type': 'flow_update',
                                        'symbol': symbol,
                                        'timestamp': datetime.now().isoformat(),
                                        'data': warm_data,
                                    }
                                    await manager.broadcast_to_symbol(warm, symbol)
                            except Exception as warm_err:
                                logger.debug(f"Keepalive during cooldown failed: {warm_err}")
                            await asyncio.sleep(min(3.0, max(0.2, remaining)))
                        continue
                    
                    # Respect per-request cooldown WITHOUT blocking the event loop
                    # (api_tracker.wait_if_needed uses time.sleep and freezes all WS clients)
                    wait_time = float(api_tracker.seconds_until_available(primary_api) or 0.0)
                    if wait_time > 0.05:
                        logger.debug(f"Async wait {wait_time:.2f}s for {primary_api} cooldown")
                        await asyncio.sleep(min(wait_time, 8.0))
                    
                    # Get flow data (run in thread pool to avoid blocking)
                    # Only fetch options data during regular market hours
                    loop = asyncio.get_running_loop()
                    flow_data = None
                    
                    if should_update_options:
                        logger.debug(f"Fetching {target_dte}DTE options data for {symbol} (session: {current_session})")
                        try:
                            # Check for preferred source from any connected client for this symbol
                            preferred_source = None
                            if hasattr(manager, 'preferred_sources'):
                                for ws_conn, prefs in manager.preferred_sources.items():
                                    if symbol in prefs:
                                        preferred_source = prefs[symbol]
                                        logger.debug(f"Using preferred source for {symbol}: {preferred_source}")
                                        break
                            
                            # Add timeout to prevent hanging - CRITICAL for continuous updates
                            flow_data = await asyncio.wait_for(
                                loop.run_in_executor(
                                    None, 
                                    multi_source_tracker.get_0dte_options_chain, 
                                    symbol,
                                    preferred_source  # Pass preferred source
                                ),
                                timeout=10.0  # 10 second timeout
                            )
                            if current_session == 'PRE_MARKET':
                                _last_pm_options_fetch[symbol] = time.time()
                            # Record successful API request
                            api_tracker.record_request(primary_api, success=True)
                            if flow_data:
                                # Track successful data source
                                data_source = flow_data.get('data_source', primary_api)
                                if data_source != _last_known_data_source.get(symbol):
                                    logger.info(f"📊 Data source changed for {symbol}: {_last_known_data_source.get(symbol, 'unknown')} -> {data_source}")
                                    _last_known_data_source[symbol] = data_source
                                
                                # Track data delay info (without annoying warnings)
                                if data_source.lower() == 'yfinance':
                                    flow_data['data_delay_warning'] = True
                                    flow_data['data_delay_minutes'] = 15  # Approximate delay
                                else:
                                    flow_data['data_delay_warning'] = False
                                    flow_data['data_delay_minutes'] = 0
                                
                                _data_source_failure_count[symbol] = 0  # Reset failure count
                                
                                # CRITICAL: Extract all_calls and all_puts DIRECTLY into flow_data using helper function
                                calls_data, puts_data = extract_options_data(flow_data, symbol)
                                calls_count = len(calls_data)
                                puts_count = len(puts_data)
                                logger.info(f"✅ Multi-source returned data for {symbol}: {calls_count} calls, {puts_count} puts (extracted to flow_data)")
                                
                                # CRITICAL: Cache successful flow_data for fallback
                                if flow_data and isinstance(flow_data, dict) and flow_data.get('stock_price', 0) > 0:
                                    _last_successful_flow_data[symbol] = flow_data.copy()
                                    _last_successful_data_timestamp[symbol] = time.time()
                                    logger.debug(f"✅ Cached successful flow_data for {symbol} (stock_price: ${flow_data.get('stock_price', 0):.2f}, calls: {calls_count}, puts: {puts_count})")
                        except asyncio.TimeoutError:
                            logger.warning(f"⏱️ Multi-source timeout for {symbol} (10s) - trying single source")
                            api_tracker.record_request(primary_api, success=False, error="Timeout")
                            # Track data source even on timeout (use last known or primary_api)
                            if symbol not in _last_known_data_source:
                                _last_known_data_source[symbol] = primary_api
                            flow_data = None
                        except Exception as e:
                            # Record failed API request
                            api_tracker.record_request(primary_api, success=False, error=str(e))
                            # Track data source even on error (use last known or primary_api)
                            if symbol not in _last_known_data_source:
                                _last_known_data_source[symbol] = primary_api
                            logger.warning(f"Multi-source failed for {symbol}, trying single source: {e}")
                            try:
                                # Try fallback with yfinance
                                fallback_api = 'yfinance'
                                can_request_fb, _ = api_tracker.can_make_request(fallback_api)
                                if can_request_fb:
                                    # Never call wait_if_needed — it blocks the asyncio loop
                                    fb_wait = float(api_tracker.seconds_until_available(fallback_api) or 0.0)
                                    if fb_wait > 0.05:
                                        await asyncio.sleep(min(fb_wait, 5.0))
                                    flow_data = await asyncio.wait_for(
                                        loop.run_in_executor(
                                            None, 
                                            flow_tracker.get_0dte_options_chain, 
                                            symbol
                                        ),
                                        timeout=10.0  # 10 second timeout
                                    )
                                    if flow_data:
                                        api_tracker.record_request(fallback_api, success=True)
                                        # Track successful fallback source
                                        data_source = flow_data.get('data_source', fallback_api)
                                        _last_known_data_source[symbol] = data_source
                                        
                                        # CRITICAL: Cache successful flow_data from fallback
                                        if flow_data and isinstance(flow_data, dict) and flow_data.get('stock_price', 0) > 0:
                                            _last_successful_flow_data[symbol] = flow_data.copy()
                                            _last_successful_data_timestamp[symbol] = time.time()
                                        
                                        calls_count = len(flow_data.get('strikes', {}).get('calls_by_strike', []))
                                        puts_count = len(flow_data.get('strikes', {}).get('puts_by_strike', []))
                                        logger.debug(f"Single source returned data for {symbol}: {calls_count} calls, {puts_count} puts")
                                    else:
                                        api_tracker.record_request(fallback_api, success=False, error="No data returned")
                                        # Track fallback source even if no data
                                        if symbol not in _last_known_data_source:
                                            _last_known_data_source[symbol] = fallback_api
                                else:
                                    logger.warning(f"Fallback API {fallback_api} also rate limited")
                            except asyncio.TimeoutError:
                                logger.warning(f"⏱️ Fallback timeout for {symbol} (10s)")
                                api_tracker.record_request(fallback_api, success=False, error="Timeout")
                                flow_data = None
                            except Exception as e2:
                                api_tracker.record_request(fallback_api, success=False, error=str(e2))
                                logger.warning(f"Single source also failed for {symbol}: {e2}")
                                flow_data = None
                                # Increment failure count for tracking
                                _data_source_failure_count[symbol] = _data_source_failure_count.get(symbol, 0) + 1
                                logger.debug(f"Data source failure count for {symbol}: {_data_source_failure_count[symbol]}")
                    else:
                        # Options not trading during this session - fetch 1DTE for preview
                        logger.debug(f"Extended hours ({current_session}) - fetching 1DTE options for preview for {symbol}")
                        # Try to fetch 1DTE options for next trading day
                        try:
                            flow_data = await asyncio.wait_for(
                                loop.run_in_executor(
                                    None,
                                    multi_source_tracker.get_0dte_options_chain,
                                    symbol
                                ),
                                timeout=10.0
                            )
                            if flow_data and isinstance(flow_data, dict) and flow_data.get('stock_price', 0) > 0:
                                calls_count = len(flow_data.get('strikes', {}).get('calls_by_strike', []))
                                puts_count = len(flow_data.get('strikes', {}).get('puts_by_strike', []))
                                if calls_count > 0 or puts_count > 0:
                                    logger.info(f"✅ Got 1DTE options data for {symbol} - {calls_count} calls, {puts_count} puts")
                                else:
                                    # Stock price available but no options - this is OK for some symbols
                                    logger.info(f"✅ Got stock price for {symbol} (no options data available, showing 1DTE preview)")
                                    # Still valid - has stock price
                            else:
                                logger.warning(f"1DTE options data fetch returned empty/invalid data for {symbol}")
                                flow_data = None
                        except asyncio.TimeoutError:
                            logger.warning(f"⏱️ 1DTE fetch timeout for {symbol}")
                            flow_data = None
                        except Exception as e:
                            logger.warning(f"Could not get 1DTE options data for {symbol}: {e}")
                            flow_data = None
                    
                    # Handle case when flow_data is None or empty (final fallback)
                    # Only show error if we have NO data at all (not even stock price)
                    # If we have stock price (even without options), that's valid data - continue normally
                    if not flow_data or not isinstance(flow_data, dict) or flow_data.get('stock_price', 0) == 0:
                        # No data at all - only show error if we're not in regular hours
                        # (In regular hours, this shouldn't happen, so it's a real error)
                        if current_session != 'REGULAR':
                            # Try one more time to get at least stock price (ASYNC)
                            try:
                                # CRITICAL: Check rate limit before making yfinance call
                                can_request, reason = api_tracker.can_make_request('yfinance')
                                if not can_request:
                                    logger.warning(f"⚠️ yfinance rate limit: {reason} - skipping price fetch")
                                else:
                                    # OPTIMIZED: Make yfinance call async to avoid blocking
                                    loop = asyncio.get_event_loop()
                                    def fetch_price():
                                        if 'yf' not in globals():
                                            import yfinance as yf
                                        ticker = yf.Ticker(symbol)
                                        hist = ticker.history(period="1d")
                                        if not hist.empty:
                                            return float(hist['Close'].iloc[-1])
                                        return 0
                                    
                                    stock_price = await loop.run_in_executor(None, fetch_price)
                                    # CRITICAL: Track yfinance API usage
                                    api_tracker.record_request('yfinance', success=(stock_price > 0))
                                if stock_price > 0:
                                    # Create minimal flow_data with just stock price
                                    flow_data = {
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
                                        'options_available': False
                                    }
                                    logger.info(f"✅ Got stock price for {symbol} (no options, but showing price)")
                            except Exception as e:
                                logger.warning(f"Could not get stock price for {symbol}: {e}")
                        
                        # CRITICAL: Before giving up, try to use cached/last successful data
                        if (not flow_data or not isinstance(flow_data, dict) or flow_data.get('stock_price', 0) == 0) and symbol in _last_successful_flow_data:
                            cached_data = _last_successful_flow_data[symbol]
                            cache_age = time.time() - _last_successful_data_timestamp.get(symbol, 0)
                            cache_age_hours = cache_age / 3600
                            
                            if cached_data and isinstance(cached_data, dict) and cached_data.get('stock_price', 0) > 0:
                                logger.info(f"📦 Using cached flow_data for {symbol} (age: {cache_age_hours:.1f} hours) - markets closed, showing last known data")
                                flow_data = cached_data.copy()
                                # Mark as cached/stale
                                flow_data['_cached'] = True
                                flow_data['_cache_age_seconds'] = int(cache_age)
                                flow_data['data_freshness'] = 'CACHED'
                                flow_data['data_age_seconds'] = int(cache_age)
                                
                                # Update expiration to show 1DTE if it's weekend/premarket
                                if current_session in ['PRE_MARKET', 'AFTER_HOURS', 'OVERNIGHT', 'WEEKEND']:
                                    next_trading_day = datetime.now().date() + timedelta(days=1)
                                    flow_data['expiration'] = next_trading_day.strftime('%Y-%m-%d')
                                    flow_data['expiration_label'] = f"1DTE ({next_trading_day.strftime('%Y-%m-%d')})"
                                    flow_data['dte'] = 1
                        
                        # Only create error message if we STILL have no data (even cached)
                        if not flow_data or not isinstance(flow_data, dict) or flow_data.get('stock_price', 0) == 0:
                            error_message = f"Markets closed - No data available during {current_session}. Options only trade during Regular hours (9:30 AM - 4:00 PM ET)."
                            if market_status.get('session') == 'OVERNIGHT':
                                error_message = "Options trading closed (Overnight hours - options don't trade after-hours)"
                            elif market_status.get('session') == 'WEEKEND':
                                error_message = "Options trading closed (Weekend)"
                            elif market_status.get('session') == 'PRE_MARKET':
                                error_message = "Pre-market connected — spot/PM ok; liquid 0DTE chain unlocks at RTH 9:30 AM ET"
                            elif market_status.get('session') == 'AFTER_HOURS':
                                error_message = "After-hours — options books quiet; Stage A focuses on RTH 9:30 AM - 4:00 PM ET"
                            # Set expiration based on market session
                            # Use top-level timedelta import (no local import needed)
                            today = datetime.now().date()
                            if current_session == 'REGULAR':
                                exp_date = today
                                exp_label = f"0DTE ({today.strftime('%Y-%m-%d')})"
                                dte_value = 0
                            elif current_session in ['PRE_MARKET', 'AFTER_HOURS', 'OVERNIGHT']:
                                exp_date = today + timedelta(days=1)
                                exp_label = f"1DTE ({exp_date.strftime('%Y-%m-%d')})"
                                dte_value = 1
                            else:
                                exp_date = None
                                exp_label = 'N/A'
                                dte_value = 0
                            
                            # Try to get prev_close and extended hours prices even for error messages
                            # CRITICAL: Preserve stock_price from flow_data if available
                            prev_close = 0
                            regular_close = flow_data.get('stock_price', 0) if flow_data else 0  # Preserve flow_data stock_price
                            
                            # FIXED: Ensure stock_price is always set in flow_data if missing (use regular_close as fallback)
                            if flow_data and flow_data.get('stock_price', 0) == 0 and regular_close > 0:
                                flow_data['stock_price'] = regular_close
                                logger.debug(f"✅ Set stock_price from regular_close for {symbol}: ${regular_close:.2f}")
                            
                            # CRITICAL: Initialize all price variables to 0 (never None/undefined)
                            aftermarket_price = 0
                            aftermarket_change_pct = 0
                            premarket_price = 0
                            premarket_change_pct = 0
                            prev_close = 0
                            # Always define info/fast_info before any conditional branches
                            info = None
                            fast_info = None
                            
                            # OPTIMIZED: Make all yfinance calls async to avoid blocking
                            # CRITICAL: Check rate limit before making yfinance calls
                            now_ts = time.time()
                            backoff_until = _yfinance_backoff_until.get(symbol, 0)
                            if now_ts < backoff_until:
                                # Use cached data if available during backoff
                                if symbol in _last_successful_flow_data:
                                    cached = _last_successful_flow_data[symbol]
                                    logger.info(f"⚠️ yfinance backoff active for {symbol}, using cached data (age {int(now_ts - _last_successful_data_timestamp.get(symbol, now_ts))}s)")
                                    flow_data = cached.copy()
                                info = None
                                fast_info = None
                            else:
                                can_request, reason = api_tracker.can_make_request('yfinance')
                                if not can_request:
                                    warn_gap = now_ts - _yfinance_last_warning.get(symbol, 0)
                                    if warn_gap > 5:
                                        logger.warning(f"⚠️ yfinance rate limit: {reason} - backing off")
                                        _yfinance_last_warning[symbol] = now_ts
                                    info = None
                                    fast_info = None
                                    # longer backoff if circuit breaker
                                    backoff_seconds = 120 if 'Circuit breaker' in str(reason) else 60
                                    _yfinance_backoff_until[symbol] = now_ts + backoff_seconds
                                    # Use cached data if available
                                    if symbol in _last_successful_flow_data:
                                        flow_data = _last_successful_flow_data[symbol].copy()
                                else:
                                    loop = asyncio.get_event_loop()
                                    prev_close = 0
                                    
                                    try:
                                        def fetch_all_data():
                                            """Fetch all yfinance data in one function to avoid multiple ticker creations"""
                                            if 'yf' not in globals():
                                                import yfinance as yf
                                            ticker = yf.Ticker(symbol)
                                            hist = ticker.history(period="2d", interval="1d")
                                            info = ticker.info
                                            fast_info = ticker.fast_info
                                            return hist, info, fast_info
                                        
                                        hist, info, fast_info = await loop.run_in_executor(None, fetch_all_data)
                                        # CRITICAL: Track yfinance API usage (counts as 1 request even though we fetch 3 things)
                                        api_tracker.record_request('yfinance', success=True)
                                        _yfinance_backoff_until[symbol] = now_ts  # reset backoff on success
                                        
                                        # Process history
                                        if not hist.empty and len(hist) >= 1:
                                            hist_close = float(hist['Close'].iloc[-1])
                                            if regular_close == 0:
                                                regular_close = hist_close
                                        if not hist.empty and len(hist) >= 2:
                                            prev_close = float(hist['Close'].iloc[-2])
                                    except Exception as e:
                                        logger.debug(f"Error getting extended hours data: {e}")
                                        info = None
                                        fast_info = None
                                        prev_close = 0
                                        _yfinance_backoff_until[symbol] = now_ts + 60  # back off after failure
                        
                        # Method 1: Try fast_info first (more reliable)
                        if fast_info:
                            try:
                                if hasattr(fast_info, 'postMarketPrice') and fast_info.postMarketPrice:
                                    aftermarket_price = float(fast_info.postMarketPrice)
                                    if regular_close > 0:
                                        aftermarket_change_pct = ((aftermarket_price - regular_close) / regular_close) * 100
                                
                                if hasattr(fast_info, 'preMarketPrice') and fast_info.preMarketPrice:
                                    premarket_price = float(fast_info.preMarketPrice)
                                    if regular_close > 0:
                                        premarket_change_pct = ((premarket_price - regular_close) / regular_close) * 100
                            except Exception:
                                pass
                        
                        # Method 2: Try info dict (most reliable method)
                        if info:
                            # Try to get aftermarket price - use postMarketChangePercent if postMarketPrice is missing
                            post_market = info.get('postMarketPrice')
                            post_change_pct = info.get('postMarketChangePercent')
                            
                            # If we have postMarketChangePercent but postMarketPrice is None/0, calculate it
                            if (post_market is None or post_market == 0) and post_change_pct is not None and regular_close > 0:
                                post_market = regular_close * (1 + post_change_pct / 100)
                                aftermarket_price = float(post_market)
                                aftermarket_change_pct = float(post_change_pct)
                            elif post_market is not None and post_market != 0:
                                try:
                                    aftermarket_price = float(post_market)
                                    if regular_close > 0 and aftermarket_price > 0:
                                        aftermarket_change_pct = ((aftermarket_price - regular_close) / regular_close) * 100
                                except (ValueError, TypeError):
                                    pass
                            
                            # Try to get premarket price
                            pre_market = info.get('preMarketPrice')
                            if pre_market is not None and pre_market != 0:
                                try:
                                    premarket_price = float(pre_market)
                                    if regular_close > 0 and premarket_price > 0:
                                        premarket_change_pct = ((premarket_price - regular_close) / regular_close) * 100
                                except (ValueError, TypeError):
                                    pass
                            
                            # FIXED: Prefer PM print in pre-market for context (don't show only yesterday close)
                            if current_session == 'PRE_MARKET' and premarket_price > 0:
                                stock_price_for_message = premarket_price
                            else:
                                stock_price_for_message = regular_close if regular_close > 0 else (aftermarket_price if aftermarket_price > 0 else (premarket_price if premarket_price > 0 else (flow_data.get('stock_price', 0) if flow_data and isinstance(flow_data, dict) else 0)))
                            
                            # FINAL SAFETY CHECK: Ensure stock_price is never 0 if we have valid flow_data
                            if stock_price_for_message == 0 and flow_data and isinstance(flow_data, dict):
                                flow_data_price = flow_data.get('stock_price', 0)
                                if flow_data_price > 0:
                                    stock_price_for_message = flow_data_price
                                    regular_close = flow_data_price  # Also update regular_close for consistency
                                    logger.info(f"✅ Final safety check: stock_price was 0, using flow_data.stock_price: ${stock_price_for_message:.2f} for {symbol}")

                            # Pre-market / off-hours with spot: still run Boss for prep context (no fake liquid chain)
                            prep_boss = {}
                            prep_paper = {}
                            try:
                                if BOSS_ENGINE_AVAILABLE and boss_decision_engine and stock_price_for_message > 0:
                                    armed = bool(paper_arm_state.armed) if paper_arm_state else False
                                    prep_boss = boss_decision_engine.decide(
                                        symbol=symbol,
                                        stock_price=float(stock_price_for_message),
                                        flow_signal={
                                            'action': 'NO_TRADE',
                                            'confidence': 0,
                                            'reasoning': error_message,
                                        },
                                        calls=[],
                                        puts=[],
                                        options_chain={'calls': [], 'puts': []},
                                        paper_armed=armed,
                                    )
                                    if paper_arm_state:
                                        prep_paper = {
                                            'armed': armed,
                                            'arm_status': paper_arm_state.status(),
                                        }
                            except Exception as prep_boss_err:
                                logger.debug(f"Prep Boss error for {symbol}: {prep_boss_err}")
                                prep_boss = {
                                    'action': 'NO_TRADE',
                                    'confidence': 0,
                                    'reason': error_message,
                                    'hard_vetoes': ['OUTSIDE_RTH_OR_NO_OPEN'],
                                }
                            
                            message = {
                                'type': 'flow_update',
                                'symbol': symbol,
                                'timestamp': datetime.now().isoformat(),
                                'data': {
                                    'stock_price': stock_price_for_message,  # Use regular_close instead of 0
                                    'prev_close': prev_close,
                                    'regular_close': regular_close,
                                    'aftermarket_price': aftermarket_price,
                                    'aftermarket_change_pct': aftermarket_change_pct,
                                    'premarket_price': premarket_price,
                                    'premarket_change_pct': premarket_change_pct,
                                    'flow_metrics': {
                                        'total_call_volume': 0,
                                        'total_put_volume': 0,
                                        'call_put_ratio': 1.0,
                                        'net_volume_flow': 0
                                    },
                                    'momentum': {},
                                    'all_calls': [],
                                    'all_puts': [],
                                    'expiration': exp_date.strftime('%Y-%m-%d') if exp_date else 'N/A',
                                    'expiration_label': exp_label,
                                    'dte': dte_value,
                                    'data_source': _last_known_data_source.get(symbol, 'unknown'),  # Use last known instead of 'none'
                                    'rotation_info': _get_comprehensive_rotation_info(_last_known_data_source.get(symbol, 'unknown'), symbol),
                                    'error': error_message,
                                    'market_status': market_status,
                                    'signal': {
                                        'action': (prep_boss.get('action') if prep_boss else 'NO_TRADE'),
                                        'confidence': (prep_boss.get('confidence') if prep_boss else 0),
                                        'reasoning': error_message,
                                        'signal_type': 'WAIT',
                                        'boss_decision': prep_boss,
                                    },
                                    'boss_decision': prep_boss,
                                    'paper_boss': prep_paper,
                                    'data_freshness': 'PREP' if current_session == 'PRE_MARKET' else 'OLD',
                                    'data_age_seconds': 999999,
                                    'order_flow_history': [],
                                    'unusual_activity': None
                                }
                            }
                            # IMPROVED: Always try to broadcast, even if no subscriptions tracked
                            # Sometimes subscriptions exist but aren't tracked correctly
                            try:
                                await manager.broadcast_to_symbol(message, symbol)
                            except Exception as broadcast_error:
                                logger.debug(f"Broadcast failed for {symbol} (may not have active subscriptions): {broadcast_error}")
                            continue  # Skip to next iteration
                    
                    # Get momentum (use multi-source if available, else fallback)
                    try:
                        momentum = await loop.run_in_executor(
                            None,
                            multi_source_tracker.get_flow_momentum,
                            symbol
                        )
                    except Exception as e:
                        # Fallback to flow_tracker if multi_source_tracker fails
                        logger.debug(f"Failed to get momentum from multi_source_tracker for {symbol}: {e}")
                        try:
                            momentum = await loop.run_in_executor(
                                None,
                                flow_tracker.get_flow_momentum,
                                symbol
                            )
                        except Exception as e2:
                            # Final fallback: empty momentum dict
                            logger.debug(f"Failed to get momentum from flow_tracker for {symbol}: {e2}")
                            momentum = {}
                    
                    # Prepare message - send ALL strikes, not just top 10
                    # CRITICAL: Defensive check - flow_data must be a dict
                    if flow_data is None or not isinstance(flow_data, dict):
                        logger.warning(f"⚠️ flow_data is None or not dict for {symbol} - cannot process strikes")
                        calls_by_strike = []
                        puts_by_strike = []
                    else:
                        # CRITICAL: Extract all_calls/all_puts using helper function
                        calls_by_strike, puts_by_strike = extract_options_data(flow_data, symbol)
                        
                        # CRITICAL: Log what we found
                        logger.info(f"[background_updater] Options extraction for {symbol}: {len(calls_by_strike)} calls, {len(puts_by_strike)} puts")
                        
                        # Log for debugging if no options found
                        if not calls_by_strike and not puts_by_strike:
                            logger.warning(f"⚠️ No options data in flow_data for {symbol}")
                            logger.warning(f"   flow_data keys: {list(flow_data.keys())[:15] if isinstance(flow_data, dict) else 'not a dict'}")
                    
                    # OPTIMIZATION: Filter and limit strikes on backend (not frontend)
                    # Only send top 12 ATM strikes with volume to reduce payload size
                    stock_price = flow_data.get('stock_price', 0) if flow_data else 0
                    # Pre-market: prefer live PM print for Boss/context when chain spot is stale
                    if current_session == 'PRE_MARKET' and flow_data:
                        pm = float(flow_data.get('premarket_price') or 0)
                        if pm > 0:
                            stock_price = pm
                            flow_data['stock_price'] = pm
                    
                    # Filter calls: volume > 0, within 5% of ATM (expanded from 2.5% for better coverage)
                    # But show at least top 20 by volume even if not ATM
                    calls_with_volume = [c for c in calls_by_strike if (c.get('volume', 0) > 0)] if calls_by_strike else []
                    if stock_price > 0 and calls_with_volume:
                        # First get ATM options (within 5%)
                        calls_atm = [c for c in calls_with_volume 
                                    if abs(c.get('strike', 0) - stock_price) / stock_price <= 0.05]
                        if calls_atm:
                            calls_sorted = sorted(calls_atm, 
                                                key=lambda x: (abs(x.get('strike', 0) - stock_price), -x.get('volume', 0)))[:20]
                        else:
                            # No ATM options, show top by volume
                            calls_sorted = sorted(calls_with_volume, key=lambda x: x.get('volume', 0), reverse=True)[:20]
                    elif calls_with_volume:
                        calls_sorted = sorted(calls_with_volume, key=lambda x: x.get('volume', 0), reverse=True)[:20]
                    else:
                        # No volume, but include all options for display (show 0 volume)
                        calls_sorted = sorted(calls_by_strike, key=lambda x: abs(x.get('strike', 0) - stock_price) if stock_price > 0 else x.get('strike', 0))[:20] if calls_by_strike else []
                    
                    # Filter puts: volume > 0, within 5% of ATM (expanded from 2.5%)
                    puts_with_volume = [p for p in puts_by_strike if (p.get('volume', 0) > 0)] if puts_by_strike else []
                    if stock_price > 0 and puts_with_volume:
                        # First get ATM options (within 5%)
                        puts_atm = [p for p in puts_with_volume 
                                   if abs(p.get('strike', 0) - stock_price) / stock_price <= 0.05]
                        if puts_atm:
                            puts_sorted = sorted(puts_atm, 
                                                key=lambda x: (abs(x.get('strike', 0) - stock_price), -x.get('volume', 0)))[:20]
                        else:
                            # No ATM options, show top by volume
                            puts_sorted = sorted(puts_with_volume, key=lambda x: x.get('volume', 0), reverse=True)[:20]
                    elif puts_with_volume:
                        puts_sorted = sorted(puts_with_volume, key=lambda x: x.get('volume', 0), reverse=True)[:20]
                    else:
                        # No volume, but include all options for display (show 0 volume)
                        puts_sorted = sorted(puts_by_strike, key=lambda x: abs(x.get('strike', 0) - stock_price) if stock_price > 0 else x.get('strike', 0))[:20] if puts_by_strike else []
                    
                    logger.info(f"📊 Prepared {len(calls_sorted)} calls and {len(puts_sorted)} puts for {symbol} (stock_price: ${stock_price:.2f})")

                    # Early freshness tick — keeps LIVE badge + spot/chain moving while Boss/ML run
                    try:
                        if stock_price > 0 and manager.symbol_subscriptions.get(symbol):
                            prev_cached = _last_successful_flow_data.get(symbol) or {}
                            lite = {
                                'type': 'flow_update',
                                'symbol': symbol,
                                'timestamp': datetime.now().isoformat(),
                                'data': {
                                    'stock_price': stock_price,
                                    'regular_close': stock_price,
                                    'all_calls': calls_sorted[:20],
                                    'all_puts': puts_sorted[:20],
                                    'flow_metrics': (flow_data.get('flow_metrics') if isinstance(flow_data, dict) else {}) or {},
                                    'data_source': (flow_data.get('data_source') if isinstance(flow_data, dict) else None)
                                        or _last_known_data_source.get(symbol, 'yfinance'),
                                    'rotation_info': _get_comprehensive_rotation_info(
                                        (flow_data.get('data_source') if isinstance(flow_data, dict) else None)
                                        or _last_known_data_source.get(symbol, 'yfinance'),
                                        symbol,
                                    ),
                                    'data_freshness': 'NEW',
                                    'data_age_seconds': 0,
                                    'market_status': market_status,
                                    # Only ship Boss if we actually have one. An empty
                                    # dict is truthy on the client and used to blank
                                    # the Boss card between full cycles.
                                    **(
                                        {'boss_decision': prev_cached['boss_decision']}
                                        if isinstance(prev_cached.get('boss_decision'), dict)
                                        and prev_cached['boss_decision']
                                        else {}
                                    ),
                                    # Same for tenor mix: empty {} wipes "Flow by expiration".
                                    **(
                                        {'expiry_terms': _last_expiry_terms[symbol]}
                                        if isinstance(_last_expiry_terms.get(symbol), dict)
                                        and _last_expiry_terms[symbol].get('buckets')
                                        else {}
                                    ),
                                    'signal': prev_cached.get('signal') or {
                                        'action': (prev_cached.get('boss_decision') or {}).get('action', 'NO_TRADE'),
                                        'confidence': (prev_cached.get('boss_decision') or {}).get('confidence', 0),
                                    },
                                    'shadow_learning': prev_cached.get('shadow_learning') or {},
                                    'lite_tick': True,
                                    'dte': 0 if current_session == 'REGULAR' else 1,
                                    'expiration_label': (
                                        f"0DTE ({datetime.now().date().strftime('%Y-%m-%d')})"
                                        if current_session == 'REGULAR'
                                        else f"1DTE ({(datetime.now().date() + timedelta(days=1)).strftime('%Y-%m-%d')})"
                                    ),
                                },
                            }
                            await manager.broadcast_to_symbol(lite, symbol)
                    except Exception as lite_err:
                        logger.debug(f"Lite tick skipped for {symbol}: {lite_err}")
                    
                    # Performance: Track update counter for throttling heavy calculations
                    update_counter = _update_counters.get(symbol, 0)
                    _update_counters[symbol] = update_counter + 1
                    heavy_n = 3 if (
                        current_session == 'PRE_MARKET' or _is_open_protect_window(current_session)
                    ) else _HEAVY_CALC_INTERVAL
                    should_run_heavy_calcs = False  # Stage A: Boss + flow analyzer only (no ML/9-bot theater)
                    
                    # Get historical flow for ML features (lightweight, always run)
                    flow_history_data = order_flow_history.get_recent_flow(symbol, count=20)
                    
                    # Detect market regime (cached 5m — must NOT Yahoo-hit every loop)
                    try:
                        market_regime = market_regime_detector.detect_regime(symbol)
                    except Exception as _mr_e:
                        logger.debug(f"Regime detect skipped: {_mr_e}")
                        market_regime = {'regime': 'NEUTRAL', 'confidence': 0}
                    flow_data['market_regime'] = market_regime

                    # Opening range + real EMAs + IV regime (Direction/Structure workers)
                    session_structure = {}
                    if SESSION_STRUCTURE_AVAILABLE and evaluate_session_structure and stock_price > 0:
                        try:
                            if ingest_price:
                                ingest_price(symbol, stock_price)
                            chain_for_iv = {
                                'calls': flow_data.get('all_calls') or flow_data.get('calls') or [],
                                'puts': flow_data.get('all_puts') or flow_data.get('puts') or [],
                            }
                            vix_lvl = None
                            try:
                                from vix_analyzer import vix_analyzer as _vix_analyzer
                                vix_snap = _vix_analyzer.analyze_vix()
                                vix_lvl = (
                                    vix_snap.get('current_vix')
                                    or vix_snap.get('vix')
                                    or vix_snap.get('level')
                                )
                            except Exception:
                                vix_lvl = None
                            session_structure = evaluate_session_structure(
                                symbol,
                                stock_price,
                                options_chain=chain_for_iv,
                                vix_level=vix_lvl,
                            )
                            flow_data['session_structure'] = session_structure
                        except Exception as e:
                            logger.debug(f"Session structure workers error for {symbol}: {e}")
                            session_structure = {}
                    
                    # Performance: Only run heavy calculations every N updates
                    if should_run_heavy_calcs:
                        # Use ML Ensemble Predictor (combines ML + heuristics) - only if available
                        if ML_ENSEMBLE_AVAILABLE and ml_ensemble_predictor:
                            ensemble_prediction = ml_ensemble_predictor.predict(flow_data, flow_history_data)
                        else:
                            # Fallback: Use basic signal analysis
                            ensemble_prediction = {'action': 'WAIT', 'confidence': 50, 'reasoning': 'ML features not available'}
                        
                        # Apply regime-based adjustments
                        regime_adaptation = market_regime.get('strategy_adaptation', {})
                        if regime_adaptation:
                            confidence_multiplier = regime_adaptation.get('confidence_multiplier', 1.0)
                            adjusted_confidence = int(ensemble_prediction.get('confidence', 50) * confidence_multiplier)
                            ensemble_prediction['confidence'] = min(95, max(30, adjusted_confidence))
                            ensemble_prediction['regime_adjusted'] = True
                            ensemble_prediction['regime'] = market_regime.get('regime', 'NEUTRAL')
                        
                        # INSTITUTIONAL PREDICTION SYSTEM: Get predictions from all specialized bots (9 bots) - only if available
                        if INSTITUTIONAL_PREDICTION_AVAILABLE and institutional_prediction_system:
                            bot_predictions = institutional_prediction_system.predict(flow_data, flow_history_data)
                        else:
                            bot_predictions = {'action': 'WAIT', 'confidence': 50, 'bot_predictions': {}}
                        
                        # ENHANCED BOT CONSENSUS: Use weighted voting based on historical performance (per-symbol)
                        if enhanced_bot_consensus is not None and bot_predictions.get('bot_predictions'):
                            enhanced_consensus = enhanced_bot_consensus.calculate_consensus(
                                bot_predictions.get('bot_predictions', {}),
                                symbol=symbol
                            )
                            # Merge enhanced consensus into bot_predictions
                            bot_predictions['enhanced_consensus'] = enhanced_consensus
                            bot_predictions['action'] = enhanced_consensus.get('action', bot_predictions.get('action'))
                            bot_predictions['confidence'] = enhanced_consensus.get('confidence', bot_predictions.get('confidence'))
                            
                            # Record bot predictions immediately (for performance tracking)
                            # Outcomes will be updated later when trades close
                            try:
                                for bot_name, prediction in bot_predictions.get('bot_predictions', {}).items():
                                    # Use bot_id from prediction dict, fallback to bot_name
                                    bot_id = prediction.get('bot_id', bot_name)
                                    # Record prediction without outcome (will be updated when trade closes)
                                    enhanced_bot_consensus.record_bot_prediction(
                                        bot_id, prediction, actual_outcome=None, symbol=symbol
                                    )
                            except Exception as e:
                                logger.debug(f"Error recording bot predictions: {e}")
                        
                        if pattern_memory_system is not None:
                            pattern_match = pattern_memory_system.match_patterns(flow_data, symbol=symbol)
                            if pattern_match.get('confidence_boost', 0) > 0:
                                current_confidence = bot_predictions.get('confidence', 50)
                                bot_predictions['confidence'] = min(95, current_confidence + pattern_match['confidence_boost'])
                                bot_predictions['pattern_match'] = pattern_match
                        
                        # CRITICAL FIX: Generate basic signal analysis FIRST as fallback
                        # This ensures we always have a signal even if institutional optimizer fails
                        signal_analyzer_instance = ZeroDTESignalAnalyzer()
                        try:
                            # Get basic signal analysis (this is the core signal generator)
                            basic_signal_analysis = signal_analyzer_instance.analyze_flow_signal(flow_data, flow_history_data)
                        except Exception as e:
                            logger.warning(f"Basic signal analysis failed for {symbol}: {e}")
                            basic_signal_analysis = {
                                'action': 'NO_TRADE',
                                'confidence': 0,
                                'reasoning': f'Signal analysis error: {str(e)}',
                                'signal': 'NO_SIGNAL'
                            }
                        
                        # INSTITUTIONAL OPTIMIZER: Use the comprehensive call/put optimizer (combines everything)
                        if INSTITUTIONAL_OPTIMIZER_AVAILABLE and institutional_optimizer is not None:
                            try:
                                optimized_decision = institutional_optimizer.optimize(flow_data, flow_history_data)
                                # CRITICAL FIX: If optimizer returns NO_TRADE with low confidence, fallback to basic signal
                                if optimized_decision.get('action') == 'NO_TRADE' and optimized_decision.get('confidence', 0) < 40:
                                    if basic_signal_analysis.get('action') != 'NO_TRADE':
                                        logger.debug(f"Optimizer returned NO_TRADE (confidence: {optimized_decision.get('confidence', 0)}), using basic signal: {basic_signal_analysis.get('action')}")
                                        optimized_decision = {
                                            'action': basic_signal_analysis.get('action', 'NO_TRADE'),
                                            'confidence': basic_signal_analysis.get('confidence', 50),
                                            'reasoning': f"Basic signal: {basic_signal_analysis.get('reasoning', '')}",
                                            'ensemble_prediction': {},
                                            'enhanced_signal': basic_signal_analysis,
                                            'microstructure': {},
                                            'strike_analysis': basic_signal_analysis.get('strike_analysis', {}),
                                            'market_regime': market_regime,
                                            'risk_analysis': {},
                                            'signal_agreement': {},
                                            'position_sizing': {},
                                            'fallback_to_basic': True
                                        }
                            except Exception as e:
                                logger.warning(f"Institutional optimizer failed for {symbol}: {e}, using basic signal")
                                # Fallback to basic signal analysis
                                optimized_decision = {
                                    'action': basic_signal_analysis.get('action', 'NO_TRADE'),
                                    'confidence': basic_signal_analysis.get('confidence', 50),
                                    'reasoning': f"Optimizer error, using basic signal: {basic_signal_analysis.get('reasoning', '')}",
                                    'ensemble_prediction': {},
                                    'enhanced_signal': basic_signal_analysis,
                                    'microstructure': {},
                                    'strike_analysis': basic_signal_analysis.get('strike_analysis', {}),
                                    'market_regime': market_regime,
                                    'risk_analysis': {},
                                    'signal_agreement': {},
                                    'position_sizing': {},
                                    'fallback_to_basic': True
                                }
                        else:
                            # Fallback if optimizer not available - use basic signal analysis
                            optimized_decision = {
                                'action': basic_signal_analysis.get('action', bot_predictions.get('action', 'NO_TRADE')),
                                'confidence': basic_signal_analysis.get('confidence', bot_predictions.get('confidence', 50)),
                                'reasoning': basic_signal_analysis.get('reasoning', 'Institutional optimizer not available, using basic signal'),
                                'ensemble_prediction': {},
                                'enhanced_signal': basic_signal_analysis,
                                'microstructure': {},
                                'strike_analysis': basic_signal_analysis.get('strike_analysis', {}),
                                'market_regime': market_regime,
                                'risk_analysis': {},
                                'signal_agreement': {},
                                'position_sizing': {},
                                'fallback_to_basic': True
                            }
                    else:
                        # Lightweight fallback: Use basic signal analysis (always available)
                        signal_analyzer_instance = ZeroDTESignalAnalyzer()
                        try:
                            basic_signal_analysis = signal_analyzer_instance.analyze_flow_signal(flow_data, flow_history_data)
                        except Exception as e:
                            logger.warning(f"Basic signal analysis failed in lightweight mode for {symbol}: {e}")
                            basic_signal_analysis = {
                                'action': 'NO_TRADE',
                                'confidence': 0,
                                'reasoning': f'Signal analysis error: {str(e)}',
                                'signal': 'NO_SIGNAL'
                            }
                        
                        ensemble_prediction = {'confidence': 50, 'action': 'NO_TRADE', 'is_ml_prediction': False}
                        bot_predictions = {'action': 'NO_TRADE', 'confidence': 50, 'bot_predictions': {}}
                        optimized_decision = {
                            'action': basic_signal_analysis.get('action', 'NO_TRADE'),
                            'confidence': basic_signal_analysis.get('confidence', 50),
                            'reasoning': basic_signal_analysis.get('reasoning', 'Analyzing market conditions...'),
                            'ensemble_prediction': {},
                            'enhanced_signal': basic_signal_analysis,
                            'microstructure': {},
                            'strike_analysis': basic_signal_analysis.get('strike_analysis', {}),
                            'market_regime': market_regime,
                            'risk_analysis': {},
                            'signal_agreement': {},
                            'position_sizing': {},
                            'fallback_to_basic': True
                        }
                    
                    # Merge bot predictions into optimized decision
                    optimized_decision['bot_predictions'] = bot_predictions.get('bot_predictions', {})
                    optimized_decision['bot_consensus'] = {
                        'action': bot_predictions.get('action', 'NO_TRADE'),
                        'confidence': bot_predictions.get('confidence', 50),
                        'vote_breakdown': bot_predictions.get('vote_breakdown', {}),
                        'agreement': bot_predictions.get('agreement', 'WEAK')
                    }

                    # Attach opening-range / EMA / IV worker bundle for UI + Boss
                    if session_structure:
                        optimized_decision['session_structure'] = session_structure
                        vetoes = set(session_structure.get('veto_flags') or [])
                        if vetoes & {
                            'NO_CLEAR_DATA',
                            'OUTSIDE_RTH_OR_NO_OPEN',
                            'OPENING_BAR_FORMING',
                            'AWAITING_BREAK_HOLD',
                            'AWAITING_FIRST_BREAK',
                        }:
                            optimized_decision['opening_range_block'] = True
                            optimized_decision['session_veto'] = list(vetoes)
                        hint = session_structure.get('direction_hint') or {}
                        optimized_decision['structure_direction_hint'] = hint

                    # Boss: managers fuse workers → one decision → optional local paper
                    boss_decision = {}
                    paper_boss_result = {}
                    if BOSS_ENGINE_AVAILABLE and boss_decision_engine and stock_price > 0:
                        try:
                            # One flow input voice for Stage A: same basic flow vote Boss already weighed
                            flow_for_boss = basic_signal_analysis if 'basic_signal_analysis' in locals() else (
                                optimized_decision.get('enhanced_signal') or {
                                    'action': optimized_decision.get('action', 'NO_TRADE'),
                                    'confidence': optimized_decision.get('confidence', 0),
                                    'reasoning': optimized_decision.get('reasoning', ''),
                                }
                            )
                            vix_for_boss = vix_lvl if 'vix_lvl' in locals() else None
                            stale_cycle = _flow_is_stale(flow_data if isinstance(flow_data, dict) else None)
                            if stale_cycle:
                                last_boss = None
                                if isinstance(flow_data, dict) and isinstance(flow_data.get('boss_decision'), dict):
                                    last_boss = flow_data.get('boss_decision')
                                boss_decision = _sit_out_boss_paint(
                                    flow_data if isinstance(flow_data, dict) else None,
                                    last_boss,
                                )
                                armed = False
                            else:
                                if vix_for_boss is None:
                                    try:
                                        from vix_analyzer import vix_analyzer as _vix_b
                                        vs = _vix_b.analyze_vix()
                                        vix_for_boss = vs.get('current_vix') or vs.get('vix') or vs.get('level')
                                    except Exception:
                                        vix_for_boss = None
                                armed = bool(paper_arm_state.armed) if paper_arm_state else False
                                sess_for_boss = session_structure if 'session_structure' in locals() else flow_data.get('session_structure')
                                calls_for_boss = calls_sorted if 'calls_sorted' in locals() else flow_data.get('all_calls')
                                puts_for_boss = puts_sorted if 'puts_sorted' in locals() else flow_data.get('all_puts')
                                boss_decision = boss_decision_engine.decide(
                                    symbol=symbol,
                                    stock_price=stock_price,
                                    flow_signal=flow_for_boss,
                                    calls=calls_for_boss,
                                    puts=puts_for_boss,
                                    options_chain={
                                        'calls': calls_for_boss or [],
                                        'puts': puts_for_boss or [],
                                    },
                                    vix_level=vix_for_boss,
                                    paper_armed=armed,
                                    session_structure=sess_for_boss,
                                )
                                # Keep session_structure identical to Boss workers (one voice)
                                if boss_decision.get('workers') and sess_for_boss:
                                    flow_data['session_structure'] = sess_for_boss
                                    optimized_decision['session_structure'] = sess_for_boss
                                elif boss_decision.get('workers'):
                                    # Reconstruct minimal session blob from Boss if WS skipped evaluate
                                    synced = {
                                        'workers': boss_decision.get('workers'),
                                        'direction_hint': {
                                            'action': (boss_decision.get('session_context') or {}).get('direction_hint_action'),
                                            'phase': (boss_decision.get('session_context') or {}).get('phase'),
                                            'orb_state': (boss_decision.get('session_context') or {}).get('orb_state'),
                                            'source': (boss_decision.get('session_context') or {}).get('direction_source'),
                                        },
                                        'veto_flags': list(boss_decision.get('hard_vetoes') or []),
                                    }
                                    flow_data['session_structure'] = synced
                                    optimized_decision['session_structure'] = synced

                            optimized_decision['boss_decision'] = boss_decision
                            # Authoritative Stage A verb — hide legacy optimizer action behind legacy_*
                            optimized_decision['legacy_flow_action'] = optimized_decision.get('action')
                            optimized_decision['legacy_flow_confidence'] = optimized_decision.get('confidence')
                            optimized_decision['action'] = boss_decision.get('action', 'NO_TRADE')
                            optimized_decision['confidence'] = boss_decision.get('confidence', 0)
                            optimized_decision['reasoning'] = boss_decision.get('reason') or optimized_decision.get('reasoning', '')

                            # Manage / open local paper from Boss (singleton + kill switch)
                            if paper_trading_engine:
                                c = boss_decision.get('contract') or {}
                                # Honest marks: exit/manage prefer BID; never prefer mid over bid
                                bid = c.get('bid')
                                mark = bid if bid not in (None, 0, 0.0) else (c.get('mid') or c.get('entry_mark'))
                                paper_boss_result['armed'] = bool(armed) and not stale_cycle
                                paper_boss_result['arm_status'] = paper_arm_state.status() if paper_arm_state else {}
                                if stale_cycle:
                                    # Do not flatten opens or open tickets on stale/offline marks
                                    paper_boss_result['offline'] = True
                                    paper_boss_result['can_auto_paper'] = False
                                    paper_boss_result['exits'] = []
                                else:
                                    paper_boss_result['exits'] = paper_trading_engine.manage_boss_positions(
                                        symbol, stock_price, mark, boss_decision, option_bid=bid
                                    )
                                    if boss_decision.get('can_auto_paper'):
                                        paper_boss_result['entry'] = paper_trading_engine.execute_boss_trade(boss_decision)
                                        _persist_live_snapshot(symbol, flow_data if isinstance(flow_data, dict) else {}, boss_decision)
                                paper_boss_result['open_positions'] = paper_trading_engine.get_open_positions()
                                paper_boss_result['performance'] = paper_trading_engine.get_performance()
                                paper_boss_result['risk'] = paper_trading_engine.risk_status()
                            if not stale_cycle and isinstance(flow_data, dict):
                                _persist_live_snapshot(symbol, flow_data, boss_decision)
                            # Shadow LEARN: every Boss BUY_CALLS/BUY_PUTS is graded (paper stays DISARMED)
                            try:
                                from shadow_learning_engine import shadow_learning_engine
                                bots_for_shadow = {}
                                if isinstance(bot_predictions, dict):
                                    bots_for_shadow = bot_predictions.get('bot_predictions') or {}
                                shadow_summary = shadow_learning_engine.process_cycle(
                                    symbol=symbol,
                                    stock_price=float(stock_price or 0),
                                    boss_decision=boss_decision,
                                    flow_data=flow_data if isinstance(flow_data, dict) else {},
                                    bot_predictions=bots_for_shadow,
                                    signal_analysis=optimized_decision if isinstance(optimized_decision, dict) else {},
                                )
                                optimized_decision['shadow_learning'] = shadow_summary
                                if paper_boss_result is not None:
                                    paper_boss_result['shadow_learning'] = shadow_summary
                            except Exception as _sh_e:
                                logger.debug(f"Shadow learning cycle skipped: {_sh_e}")

                            optimized_decision['paper_boss'] = paper_boss_result
                        except Exception as e:
                            logger.debug(f"Boss decision error for {symbol}: {e}")
                            boss_decision = {'action': 'NO_TRADE', 'error': str(e)}
                            optimized_decision['boss_decision'] = boss_decision
                    
                    # Stage A: no cloned prediction bots / ML win-rate theater on the live desk
                    bot_performance = {}
                    optimized_decision['bot_performance'] = bot_performance

                    bot_predictions_dict = (bot_predictions or {}).get('bot_predictions', {}) or optimized_decision.get('bot_predictions', {})
                    
                    signal_analysis = {
                        'action': optimized_decision.get('action', 'NO_TRADE'),
                        'confidence': optimized_decision.get('confidence', 50),
                        'reasoning': optimized_decision.get('reasoning', ''),
                        'ml_prediction': ensemble_prediction,
                        'is_ml_prediction': ensemble_prediction.get('is_ml_prediction', False),
                        'model_type': 'Boss + flow analyzer (Stage A)',
                        'ensemble_prediction': optimized_decision.get('ensemble_prediction', {}),
                        'enhanced_signal': optimized_decision.get('enhanced_signal', {}),
                        'microstructure': optimized_decision.get('microstructure', {}),
                        'strike_analysis': optimized_decision.get('strike_analysis', {}),
                        'market_regime': optimized_decision.get('market_regime', {}),
                        'risk_analysis': optimized_decision.get('risk_analysis', {}),
                        'signal_agreement': optimized_decision.get('signal_agreement', {}),
                        'position_sizing': optimized_decision.get('position_sizing', {}),
                        'optimizer_version': 'stage_a',
                        'bot_predictions': bot_predictions_dict,  # CRITICAL: Store bot predictions for outcome tracking
                        'bot_consensus': optimized_decision.get('bot_consensus', {}),
                        'bot_performance': optimized_decision.get('bot_performance', {}),
                        'boss_decision': optimized_decision.get('boss_decision', {}),
                        'paper_boss': optimized_decision.get('paper_boss', {}),
                        'session_structure': optimized_decision.get('session_structure', {}),
                    }
                    
                    # Calculate advanced confidence and generate HTML (throttled)
                    if should_run_heavy_calcs:
                        try:
                            if ADVANCED_CONFIDENCE_AVAILABLE and advanced_confidence_analyzer:
                                advanced_confidence = advanced_confidence_analyzer.calculate_advanced_confidence(
                                    flow_data, 
                                    signal_analysis
                                )
                                # Generate confidence visualization HTML
                                if confidence_visualizer is not None:
                                    confidence_html = confidence_visualizer.generate_confidence_html(advanced_confidence)
                                    signal_analysis['confidence_html'] = confidence_html
                                else:
                                    signal_analysis['confidence_html'] = ''
                            else:
                                signal_analysis['confidence_html'] = ''
                        except Exception as e:
                            logger.debug(f"Error calculating advanced confidence: {e}")
                            signal_analysis['confidence_html'] = ''
                        
                        # Generate AI rendering visualizations
                        if AI_RENDERING_AVAILABLE and ai_rendering_engine:
                            try:
                                bot_preds = signal_analysis.get('bot_predictions', {})
                                if bot_preds:
                                    signal_analysis['bot_predictions_html'] = ai_rendering_engine.render_bot_predictions_html(bot_preds)
                                
                                bot_consensus = signal_analysis.get('bot_consensus', {})
                                if bot_consensus:
                                    signal_analysis['bot_consensus_html'] = ai_rendering_engine.render_consensus_visualization(bot_consensus)
                                
                                # Add stock price to signal_analysis for price target display in AI summary
                                signal_analysis['stock_price'] = stock_price
                                # CRITICAL: Always generate AI analysis HTML (even if empty) to keep container visible
                                try:
                                    signal_analysis['ai_analysis_html'] = ai_rendering_engine.render_ai_analysis_summary(signal_analysis)
                                except Exception as ai_error:
                                    logger.warning(f"Error generating AI analysis HTML: {ai_error}")
                                    # Generate fallback HTML to keep container visible
                                    signal_analysis['ai_analysis_html'] = '<div style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, rgba(139, 92, 246, 0.15) 100%); border-radius: 8px; padding: 10px; border: 2px solid rgba(59, 130, 246, 0.3);"><div style="display: flex; align-items: center; gap: 6px; margin-bottom: 8px;"><span style="font-size: 1rem;">🤖</span><div style="font-weight: 800; font-size: 0.75rem; color: var(--accent-color); text-transform: uppercase; letter-spacing: 0.5px;">AI Analysis</div></div><div style="padding: 6px; background: rgba(255,255,255,0.05); border-radius: 4px; font-size: 0.7rem; color: var(--text-muted);">Analyzing market conditions...</div></div>'
                            except Exception as e:
                                logger.warning(f"Error generating AI rendering: {e}")
                                # Ensure ai_analysis_html exists even on error
                                if 'ai_analysis_html' not in signal_analysis:
                                    signal_analysis['ai_analysis_html'] = '<div style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, rgba(139, 92, 246, 0.15) 100%); border-radius: 8px; padding: 10px; border: 2px solid rgba(59, 130, 246, 0.3);"><div style="display: flex; align-items: center; gap: 6px; margin-bottom: 8px;"><span style="font-size: 1rem;">🤖</span><div style="font-weight: 800; font-size: 0.75rem; color: var(--accent-color); text-transform: uppercase; letter-spacing: 0.5px;">AI Analysis</div></div><div style="padding: 6px; background: rgba(255,255,255,0.05); border-radius: 4px; font-size: 0.7rem; color: var(--text-muted);">Waiting for analysis...</div></div>'
                        else:
                            # Fallback: Generate simple HTML if AI rendering not available
                            bot_preds = signal_analysis.get('bot_predictions', {})
                            if bot_preds:
                                html_parts = ['<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px;">']
                                for bot_name, pred in bot_preds.items():
                                    action = pred.get('action', 'NO_TRADE')
                                    confidence = pred.get('confidence', 30)
                                    action_color = '#10b981' if action == 'BUY_CALLS' else '#ef4444' if action == 'BUY_PUTS' else '#6b7280'
                                    action_text = 'CALLS' if action == 'BUY_CALLS' else 'PUTS' if action == 'BUY_PUTS' else 'WAIT'
                                    html_parts.append(f'''
                                        <div style="background: rgba(21, 25, 35, 0.8); border-radius: 8px; padding: 12px; border: 1px solid {action_color}40;">
                                            <div style="font-weight: 700; color: {action_color};">{action_text}</div>
                                            <div style="font-size: 0.9rem; color: var(--text-primary); margin-top: 4px;">{confidence}% confidence</div>
                                        </div>
                                    ''')
                                html_parts.append('</div>')
                                signal_analysis['bot_predictions_html'] = ''.join(html_parts)
                        
                        # Merge advanced confidence into signal analysis
                        signal_analysis['advanced_confidence'] = advanced_confidence
                        # Use ensemble confidence if higher, otherwise use advanced confidence
                        final_confidence = max(
                            ensemble_prediction.get('confidence', 50),
                            advanced_confidence.get('confidence', 50)
                        )
                    else:
                        # Lightweight fallback for non-heavy update cycles
                        signal_analysis['advanced_confidence'] = {'confidence': signal_analysis.get('confidence', 50)}
                        final_confidence = signal_analysis.get('confidence', 50)
                        signal_analysis['confidence_html'] = ''
                    
                    signal_analysis['confidence'] = final_confidence
                    
                    # Calculate gamma exposure (always run - lightweight)
                    try:
                        all_calls = flow_data.get('all_calls', [])
                        all_puts = flow_data.get('all_puts', [])
                        stock_price = flow_data.get('stock_price', 0)
                        if gamma_risk_calculator is not None and stock_price > 0:
                            gamma_data = gamma_risk_calculator.calculate_gamma_exposure(
                                all_calls, all_puts, stock_price
                            )
                            signal_analysis['gamma_exposure'] = gamma_data
                            
                            # Add gamma pin level (where price is likely to be pinned)
                            gamma_pin = gamma_risk_calculator.get_gamma_pin_level(
                                all_calls, all_puts, stock_price
                            )
                            if gamma_pin:
                                signal_analysis['gamma_pin_level'] = gamma_pin
                    except Exception as e:
                        logger.debug(f"Error calculating gamma exposure: {e}")
                    
                    # Record features for ML training (if action is not NO_TRADE) - throttled
                    if should_run_heavy_calcs and signal_analysis.get('action') != 'NO_TRADE':
                        try:
                            ml_engine = get_ml_prediction_engine()
                            if ml_engine and ml_feature_engineer is not None:
                                features = ml_feature_engineer.extract_features(flow_data, signal_analysis, flow_history_data, symbol=symbol)
                                ml_engine.record_training_sample(
                                    features,
                                    signal_analysis.get('action', 'NO_TRADE'),
                                    symbol=symbol
                                )
                        except Exception as e:
                            logger.debug(f"Error recording training sample: {e}")
                    
                    # Calculate position size (if action is not NO_TRADE) - throttled
                    if should_run_heavy_calcs and signal_analysis.get('action') != 'NO_TRADE' and signal_analysis.get('confidence', 0) >= 70:
                        try:
                            # Calculate IV percentile for volatility-based position sizing
                            iv_percentile = None
                            try:
                                all_calls = flow_data.get('all_calls', [])
                                all_puts = flow_data.get('all_puts', [])
                                all_options = all_calls + all_puts
                                
                                if all_options:
                                    iv_values = []
                                    for opt in all_options:
                                        iv = opt.get('iv', 0)
                                        # Handle both decimal and percentage formats
                                        if iv > 1 and iv <= 100:
                                            iv = iv / 100
                                        if 0.01 < iv < 2.0:
                                            iv_values.append(iv)
                                    
                                    if iv_values:
                                        avg_iv = sum(iv_values) / len(iv_values)
                                        # For 0DTE, typical range is 5-50%
                                        typical_min = 0.05
                                        typical_max = 0.50
                                        iv_percentile = ((avg_iv - typical_min) / (typical_max - typical_min)) * 100
                                        iv_percentile = max(0, min(100, iv_percentile))
                            except Exception as e:
                                logger.debug(f"Error calculating IV percentile: {e}")
                            
                            position_info = position_sizer.calculate_position_size(
                                confidence=signal_analysis.get('confidence', 50),
                                account_size=10000,  # Default, can be configured
                                iv_percentile=iv_percentile  # Volatility-based sizing
                            )
                            signal_analysis['position_sizing'] = position_info
                            
                            # Calculate stop loss
                            stock_price = flow_data.get('stock_price', 0)
                            if stock_price > 0:
                                stop_loss = position_sizer.calculate_stop_loss(
                                    entry_price=stock_price,
                                    position_type=signal_analysis.get('action', 'BUY_CALLS'),
                                    account_size=10000,
                                    position_size=position_info.get('position_size', 0)
                                )
                                signal_analysis['stop_loss'] = stop_loss
                        except Exception as e:
                            logger.debug(f"Error calculating position size: {e}")
                    
                    # Record prediction for performance monitoring
                    try:
                        prediction_id = signal_analysis.get('signal_id', f"{symbol}_{datetime.now().isoformat()}")
                        model_performance_monitor.record_prediction(
                            prediction_id,
                            ensemble_prediction,
                            flow_data,
                            signal_analysis
                        )
                    except Exception as e:
                        logger.debug(f"Error recording prediction: {e}")
                    
                    # Record signal for ML learning (track wins/losses)
                    if signal_analysis.get('action') and signal_analysis['action'] != 'NO_TRADE':
                        signal_id = signal_analyzer.record_signal(
                            signal_analysis, 
                            symbol, 
                            flow_data.get('expiration', 'N/A')
                        )
                        signal_analysis['signal_id'] = signal_id
                        
                        # Record trade entry for performance tracking
                        # Allow multiple trades per day - check if this is a good entry point
                        action = signal_analysis.get('action', '')
                        stock_price = flow_data.get('stock_price', 0)
                        
                        if action in ['BUY_CALLS', 'BUY_PUTS'] and stock_price > 0:
                            from price_level_learner import price_level_learner
                            
                            # Update price levels and volume profile
                            all_calls = flow_data.get('all_calls', [])
                            all_puts = flow_data.get('all_puts', [])
                            price_level_learner.update_price(symbol, stock_price)
                            price_level_learner.update_volume_profile_from_options(symbol, all_calls, all_puts, stock_price)
                            
                            # Update technical indicators (EMAs) for better entry decisions
                            try:
                                from technical_indicators import technical_indicators
                                technical_indicators.update_price(symbol, stock_price)
                            except Exception as e:
                                logger.debug(f"Error updating technical indicators: {e}")
                            
                            # Check if this is a good entry point (with top/bottom prediction + EMAs)
                            flow_metrics = flow_data.get('flow_metrics', {})
                            volume_change = flow_metrics.get('net_volume_flow', 0)
                            momentum = flow_metrics.get('flow_velocity', 0) / 10000.0 if flow_metrics.get('flow_velocity', 0) else 0
                            
                            # Get EMA signals for entry validation (with signal quality filtering)
                            ema_entry_signal = None
                            try:
                                from technical_indicators import technical_indicators
                                ema_signals = technical_indicators.get_ema_signals(symbol, stock_price)
                                ema_entry_signal = ema_signals.get('ema_trend', 'NEUTRAL')
                                
                                # EMA50 is key - prefer entries when price is on the right side of EMA50
                                if action == 'BUY_CALLS':
                                    # For calls, prefer price above EMA50 (bullish)
                                    if technical_indicators.is_price_above_ema50(symbol, stock_price):
                                        ema_entry_signal = 'BULLISH_ABOVE_EMA50'
                                        # Check if this is a high-value signal
                                        if signal_quality_analyzer.should_use_signal('above_ema50'):
                                            boost = signal_quality_analyzer.get_signal_boost('above_ema50')
                                            if boost > 1.0:
                                                confidence = signal_analysis.get('confidence', 50)
                                                signal_analysis['confidence'] = min(95, int(confidence * boost))
                                elif action == 'BUY_PUTS':
                                    # For puts, prefer price below EMA50 (bearish)
                                    if technical_indicators.is_price_below_ema50(symbol, stock_price):
                                        ema_entry_signal = 'BEARISH_BELOW_EMA50'
                                        # Check if this is a high-value signal
                                        if signal_quality_analyzer.should_use_signal('below_ema50'):
                                            boost = signal_quality_analyzer.get_signal_boost('below_ema50')
                                            if boost > 1.0:
                                                confidence = signal_analysis.get('confidence', 50)
                                                signal_analysis['confidence'] = min(95, int(confidence * boost))
                            except Exception:
                                pass
                            
                            if action == 'BUY_CALLS':
                                is_good_entry, entry_reason = price_level_learner.get_optimal_entry_for_calls(
                                    symbol, stock_price, volume_change, momentum
                                )
                                # Check if approaching top (boiler banger style - sell at top) + EMA signals
                                approaching_top, top_confidence = price_level_learner.predict_approaching_top(
                                    symbol, stock_price, volume_change, momentum
                                )
                                if approaching_top:
                                    entry_reason += f" | Approaching TOP ({top_confidence*100:.0f}% confidence)"
                                    # Calculate price target (top price estimate)
                                    try:
                                        # Get recent price history to estimate top
                                        recent_prices = list(price_level_learner.price_history.get(symbol, []))[-30:]
                                        if len(recent_prices) >= 10:
                                            prices = [p['price'] for p in recent_prices]
                                            recent_high = max(prices)
                                            # Estimate top: current price + (recent high - current price) * confidence
                                            price_target = stock_price + (recent_high - stock_price) * top_confidence
                                            # Cap at reasonable max (e.g., 5% above recent high)
                                            price_target = min(price_target, recent_high * 1.05)
                                            signal_analysis['price_target'] = round(price_target, 2)
                                            signal_analysis['price_target_pct'] = round(((price_target - stock_price) / stock_price) * 100, 2)
                                    except Exception as e:
                                        logger.debug(f"Error calculating price target: {e}")
                                
                                # Add EMA entry signal
                                if ema_entry_signal:
                                    if 'BULLISH' in ema_entry_signal:
                                        entry_reason += f" | {ema_entry_signal}"
                                    elif 'BEARISH' in ema_entry_signal:
                                        # For calls, bearish EMA is a warning
                                        entry_reason += f" | EMA Warning: {ema_entry_signal}"
                            else:  # BUY_PUTS
                                is_good_entry, entry_reason = price_level_learner.get_optimal_entry_for_puts(
                                    symbol, stock_price, volume_change, momentum
                                )
                                # Check if approaching bottom (boiler banger style - sell at bottom) + EMA signals
                                approaching_bottom, bottom_confidence = price_level_learner.predict_approaching_bottom(
                                    symbol, stock_price, volume_change, momentum
                                )
                                if approaching_bottom:
                                    entry_reason += f" | Approaching BOTTOM ({bottom_confidence*100:.0f}% confidence)"
                                    # Calculate price target (bottom price estimate)
                                    try:
                                        # Get recent price history to estimate bottom
                                        recent_prices = list(price_level_learner.price_history.get(symbol, []))[-30:]
                                        if len(recent_prices) >= 10:
                                            prices = [p['price'] for p in recent_prices]
                                            recent_low = min(prices)
                                            # Estimate bottom: current price - (current price - recent low) * confidence
                                            price_target = stock_price - (stock_price - recent_low) * bottom_confidence
                                            # Cap at reasonable min (e.g., 5% below recent low)
                                            price_target = max(price_target, recent_low * 0.95)
                                            signal_analysis['price_target'] = round(price_target, 2)
                                            signal_analysis['price_target_pct'] = round(((price_target - stock_price) / stock_price) * 100, 2)
                                    except Exception as e:
                                        logger.debug(f"Error calculating price target: {e}")
                                
                                # Add EMA entry signal
                                if ema_entry_signal:
                                    if 'BEARISH' in ema_entry_signal:
                                        entry_reason += f" | {ema_entry_signal}"
                                    elif 'BULLISH' in ema_entry_signal:
                                        # For puts, bullish EMA is a warning
                                        entry_reason += f" | EMA Warning: {ema_entry_signal}"
                            
                            # Only record trade if it's a good entry point AND confidence is reasonable
                            confidence = signal_analysis.get('confidence', 0)
                            
                            # Stage A Telegram: Boss BUY only + production bar (not raw legacy conf spam).
                            # Big Run alerts stay on format_big_run_telegram elsewhere.
                            try:
                                boss_tg = signal_analysis.get('boss_decision') or {}
                                boss_action = boss_tg.get('action') or action
                                boss_conf = int(boss_tg.get('confidence') or confidence or 0)
                                bar = {}
                                try:
                                    from production_gates import odte_trade_bar
                                    bar = odte_trade_bar() or {}
                                except Exception:
                                    bar = {'floor': 58, 'block': False}
                                floor = max(85, int(bar.get('floor') or 58))
                                blocked = bool(bar.get('block'))
                                if (
                                    boss_action in ('BUY_CALLS', 'BUY_PUTS')
                                    and not blocked
                                    and boss_conf >= floor
                                ):
                                    telegram_notifier = get_telegram_notifier()
                                    if telegram_notifier and telegram_notifier.enabled:
                                        asyncio.create_task(telegram_notifier.send_signal_alert(
                                            signal_data=signal_analysis,
                                            stock_price=stock_price,
                                            symbol=symbol,
                                            flow_data=flow_data
                                        ))
                            except Exception as e:
                                logger.debug(f"Error sending Telegram alert: {e}")
                            
                            # Stage A: NEVER spam performance_tracker rows from the WS loop.
                            # Boss BUY_CALLS 80%+ was opening+closing a "trade" every cycle (~3s)
                            # with flat entry=exit — looks like terrible PnL history but was not Boss paper.
                            # Executable paper = paper_trading_engine.execute_boss_trade only (requires ARM).
                            should_record = False
                            if confidence >= 80:
                                logger.debug(
                                    f"Stage A: skip legacy trade log for {symbol} {action} "
                                    f"conf={confidence}% (Boss paper only when ARMED)"
                                )
                            
                            # Initialize variables before conditional blocks
                            recent_trades = []
                            open_same_type = []
                            
                            if should_record:
                                # ULTRA-STRICT: Very long cooldown to prevent overtrading
                                # Check if we recently opened a similar trade (within last 30 minutes for same action)
                                # This prevents opening too many trades too quickly
                                # Use top-level timedelta import (no local import needed)
                                from performance_tracker import performance_tracker as pt
                                recent_time = (datetime.now() - timedelta(minutes=30)).isoformat()  # Increased from 15 to 30 minutes
                                recent_trades = [t for t in pt.trades 
                                               if t['symbol'] == symbol 
                                               and t['action'] == action 
                                               and (t.get('status', '').upper() == 'OPEN' or not t.get('status'))
                                               and t.get('entry_time', '') > recent_time]
                                
                                # ULTRA-STRICT: Very strict position limits
                                # Limit to max 1 open trade of same type per expiration (reduced from 2)
                                open_same_type = [t for t in pt.trades 
                                                 if t['symbol'] == symbol 
                                                 and t['action'] == action 
                                                 and (t.get('status', '').upper() == 'OPEN' or not t.get('status'))
                                                 and t.get('expiration') == flow_data.get('expiration', 'N/A')]

                                # GLOBAL RISK GUARDS: Daily trade cap and daily loss limit
                                # These apply across all signals to keep behavior disciplined and product-ready
                                try:
                                    today_str = datetime.now().date().isoformat()
                                    # All trades opened today (any status)
                                    todays_trades = [
                                        t for t in pt.trades
                                        if isinstance(t.get('entry_time'), str) and t.get('entry_time', '').startswith(today_str)
                                    ]
                                    todays_trade_count = len(todays_trades)

                                    # All closed trades today with net P&L
                                    todays_closed_trades = [
                                        t for t in pt.trades
                                        if isinstance(t.get('exit_time'), str) and t.get('exit_time', '').startswith(today_str)
                                    ]
                                    todays_net_pnl = sum(
                                        (t.get('net_profit') or 0.0) for t in todays_closed_trades
                                    )

                                    # Conservative but realistic guardrails based on a $25k account:
                                    # - Max 5 trades per day
                                    # - Max ~3% daily loss (~$750) before stopping new entries
                                    MAX_TRADES_PER_DAY = 5
                                    DAILY_LOSS_LIMIT_DOLLARS = 0.03 * 25000.0  # 3% of $25k

                                    if todays_trade_count >= MAX_TRADES_PER_DAY:
                                        logger.info(
                                            f"🛑 Trade NOT recorded for {symbol} {action} - "
                                            f"daily trade limit reached ({todays_trade_count}/{MAX_TRADES_PER_DAY})"
                                        )
                                        should_record = False

                                    if todays_net_pnl <= -DAILY_LOSS_LIMIT_DOLLARS:
                                        logger.info(
                                            f"🛑 Trade NOT recorded for {symbol} {action} - "
                                            f"daily loss limit reached (P&L={todays_net_pnl:.2f}, "
                                            f"limit=-{DAILY_LOSS_LIMIT_DOLLARS:.2f})"
                                        )
                                        should_record = False
                                except Exception as e:
                                    logger.debug(f"Error applying daily risk guards: {e}")
                                
                            # ULTRA-STRICT: Extremely strict recording criteria
                            # Only record if:
                            # 1. No recent similar trade (30 min cooldown) AND less than 1 open of same type
                            # 2. OR confidence is extremely high (>=95) and less than 1 open
                            # Focus on quality over quantity - prevent overtrading completely
                            # CRITICAL: Stage A kill-switch — never open legacy ledger rows when should_record is False
                            can_record = False
                            if should_record:
                                can_record = (not recent_trades and len(open_same_type) < 1) or (confidence >= 95 and len(open_same_type) < 1)
                            
                            # Log why trade is/isn't being recorded
                            if should_record and not can_record:
                                reason = []
                                if recent_trades:
                                    reason.append(f"Cooldown active ({len(recent_trades)} recent trade(s) in last 30 min)")
                                if len(open_same_type) >= 1:
                                    if confidence < 95:
                                        reason.append(f"Position limit reached ({len(open_same_type)} open, need <1 or confidence>=95)")
                                    else:
                                        reason.append(f"Position limit reached ({len(open_same_type)} open, max 1 allowed)")
                                logger.info(f"⚠️ Trade NOT recorded for {symbol} {action} (confidence={confidence}%): {', '.join(reason)}")
                            
                            if should_record and can_record:
                                # Calculate option price (the actual cost to buy the option, e.g., 1.21, 1.03)
                                option_price = None
                                try:
                                    calls_by_strike, puts_by_strike = extract_options_data(flow_data, symbol)
                                    
                                    if action == 'BUY_CALLS' and calls_by_strike:
                                        # Find ATM or nearest call option
                                        for call in sorted(calls_by_strike, key=lambda x: abs(x.get('strike', 0) - stock_price)):
                                            if call.get('last_price', 0) > 0:
                                                option_price = call.get('last_price', 0)
                                                break
                                    elif action == 'BUY_PUTS' and puts_by_strike:
                                        # Find ATM or nearest put option
                                        for put in sorted(puts_by_strike, key=lambda x: abs(x.get('strike', 0) - stock_price)):
                                            if put.get('last_price', 0) > 0:
                                                option_price = put.get('last_price', 0)
                                                break
                                except Exception as e:
                                    logger.debug(f"Could not calculate option price: {e}")
                                
                                # REALISTIC POSITION SIZING: Calculate contracts based on retail trading patterns
                                num_contracts = 1  # Default fallback
                                position_size_info = None
                                
                                if option_price is not None and option_price > 0:
                                    try:
                                        # Get position sizing recommendation
                                        position_info = signal_analysis.get('position_sizing', {})
                                        
                                        # If position_sizing not in signal_analysis, calculate it now
                                        if not position_info or not position_info.get('position_size'):
                                            # Calculate position size using position_sizer
                                            try:
                                                position_info = position_sizer.calculate_position_size(
                                                    confidence=confidence,
                                                    account_size=25000,  # Realistic $25k account
                                                    risk_tolerance='MODERATE',
                                                    iv_percentile=flow_data.get('iv_percentile'),
                                                    market_regime=signal_analysis.get('market_regime'),
                                                    recent_performance=None  # Could add recent performance tracking
                                                )
                                            except Exception as e:
                                                logger.debug(f"Error calculating position size: {e}")
                                                position_info = {'position_size': 500}  # Fallback: $500 position
                                        
                                        # Calculate number of contracts from position size
                                        position_size = position_info.get('position_size', 500)
                                        contract_info = position_sizer.calculate_contracts(position_size, option_price)
                                        num_contracts = contract_info.get('num_contracts', 1)
                                        position_size_info = contract_info
                                        
                                        logger.debug(f"📊 Position sizing: ${position_size:.2f} → {num_contracts} contracts @ ${option_price:.2f} = ${contract_info.get('actual_cost', 0):.2f}")
                                        
                                    except Exception as e:
                                        logger.debug(f"Error in position sizing: {e}")
                                        num_contracts = 1  # Fallback to 1 contract
                                
                                # COMMISSION CHECK: Verify trade is profitable after commissions
                                should_enter = True
                                commission_reason = ""
                                
                                if option_price is not None and option_price > 0:
                                    try:
                                        from broker_commission_tracker import broker_commission_tracker
                                        should_enter, commission_reason, min_profit_needed = broker_commission_tracker.should_enter_trade(
                                            option_price, num_contracts, min_profit_target_pct=5.0  # Require at least 5% profit target
                                        )
                                        
                                        if not should_enter:
                                            logger.warning(f"⚠️ Trade BLOCKED due to commissions: {commission_reason} (needs {min_profit_needed:.2f}% profit to break even)")
                                            # CRITICAL: Don't record trade if it would be unprofitable after commissions
                                            # This prevents tiny 1-2 penny "wins" that are actually losses
                                            can_record = False
                                    except Exception as e:
                                        logger.debug(f"Error checking commission: {e}")
                                        should_enter = True  # Default to allowing trade if commission check fails
                                
                                # Only record trade if it passes commission check
                                if can_record and should_enter:
                                    from performance_tracker import performance_tracker as pt
                                    # CRITICAL FIX: Store bot_predictions with trade for outcome tracking
                                    bot_predictions_at_entry = signal_analysis.get('bot_predictions', {})
                                    
                                    # VALIDATION: Ensure bot_predictions is a dict (not None or empty)
                                    if not isinstance(bot_predictions_at_entry, dict):
                                        logger.warning(f"⚠️ Trade {signal_id} bot_predictions is not a dict: {type(bot_predictions_at_entry)} - using empty dict")
                                        bot_predictions_at_entry = {}
                                    
                                    # Log realistic trade entry
                                    if position_size_info:
                                        actual_cost = position_size_info.get('actual_cost', num_contracts * option_price * 100)
                                        logger.info(f"💰 Trade Entry: {num_contracts} contracts @ ${option_price:.2f} = ${actual_cost:.2f} ({action})")
                                    else:
                                        logger.info(f"💰 Trade Entry: {num_contracts} contracts @ ${option_price:.2f} ({action})")
                                    
                                    trade_id = pt.record_signal(
                                        signal_id,
                                        symbol,
                                        action,
                                        stock_price,
                                        confidence,
                                        flow_data.get('expiration', 'N/A'),
                                        option_price=option_price,
                                        bot_predictions=bot_predictions_at_entry if bot_predictions_at_entry else {},  # Store bot predictions that led to this trade
                                        num_contracts=num_contracts
                                    )
                                    
                                    # VALIDATION: Verify bot_predictions were stored (check after recording)
                                    if bot_predictions_at_entry:
                                        logger.debug(f"✅ Stored {len(bot_predictions_at_entry)} bot predictions with trade {trade_id}")
                                    else:
                                        logger.warning(f"⚠️ Trade {trade_id} recorded WITHOUT bot_predictions - outcomes cannot be tracked! signal_analysis keys: {list(signal_analysis.keys())}")
                                elif can_record and not should_enter:
                                    # Mark trade as commission-blocked (for learning, but not executed)
                                    try:
                                        trades = pt.trades
                                        for t in trades:
                                            if t.get('trade_id') == trade_id:
                                                t['commission_blocked'] = True
                                                t['commission_reason'] = commission_reason
                                                break
                                        pt._write_file(trades)
                                    except Exception as e:
                                        logger.debug(f"Error marking trade as commission-blocked: {e}")
                                signal_analysis['trade_id'] = trade_id
                                
                                # Initialize max_price for profit learning (track highest price reached)
                                # Store in a way that can be retrieved later
                                try:
                                    # Update the trade record with max_price
                                    trades = pt.trades
                                    for t in trades:
                                        if t.get('trade_id') == trade_id:
                                            t['max_price'] = stock_price  # Initialize with entry price
                                            break
                                except Exception as e:
                                    logger.debug(f"Error initializing max_price: {e}")
                                logger.info(f"✅ Trade RECORDED: {symbol} {action} (confidence={confidence}%, entry={is_good_entry}, trade_id={trade_id})")
                                signal_analysis['entry_reason'] = entry_reason
                                signal_analysis['trade_opened'] = {
                                    'trade_id': trade_id,
                                    'symbol': symbol,  # FIXED: Include symbol in trade notification
                                    'action': action,
                                    'entry_price': stock_price,
                                    'confidence': confidence,
                                    'reason': entry_reason
                                }
                                logger.info(f"NEW TRADE: {action} @ ${stock_price:.2f} (Confidence: {confidence}%) - {entry_reason}")
                            else:
                                signal_analysis['entry_reason'] = f"Skipped - {len(open_same_type)} open {action} trades (cooldown or limit reached)"
                            
                            # REAL-TIME POSITION MONITORING — Stage A: performance_tracker is quarantined (None).
                            # Skip legacy open-trade auto-close; Boss shadow grades ask→bid instead.
                            performance_tracker = get_performance_tracker()
                            open_trades = []
                            if performance_tracker is not None:
                                performance_tracker.auto_close_expired_trades()
                                open_trades = [t for t in performance_tracker.trades
                                             if t['symbol'] == symbol
                                             and (t.get('status', '').upper() == 'OPEN' or not t.get('status'))]
                            
                            # Log monitoring status for visibility
                            if len(open_trades) > 0:
                                logger.debug(f"📊 Monitoring {len(open_trades)} open trade(s) for {symbol}")
                            
                            for trade in open_trades:
                                entry_price = trade.get('entry_price', 0)
                                entry_time = trade.get('entry_time', datetime.now().isoformat())
                                trade_id = trade.get('trade_id', '')
                                action = trade.get('action', '')
                                
                                if entry_price == 0 or not trade_id:
                                    continue
                                
                                # Get market conditions for adaptive profit targets
                                # CRITICAL: Defensive check - flow_data must be a dict
                                if flow_data is None or not isinstance(flow_data, dict):
                                    logger.debug(f"⚠️ flow_data is None or not dict for {symbol} trade {trade_id} - skipping flow_metrics")
                                    flow_metrics = {}
                                else:
                                    flow_metrics = flow_data.get('flow_metrics', {})
                                volume_change = flow_metrics.get('net_volume_flow', 0) if flow_metrics else 0
                                momentum = (flow_metrics.get('flow_velocity', 0) / 10000.0) if (flow_metrics and flow_metrics.get('flow_velocity', 0)) else 0
                                
                                # Get expiration from trade for 0DTE force-close detection
                                expiration = trade.get('expiration', '')
                                
                                conditions = {
                                    'momentum': momentum,
                                    'volume_change': volume_change,
                                    'time_of_day': datetime.now().hour,
                                    'expiration': expiration  # CRITICAL: Pass expiration for 0DTE force-close logic
                                }
                                
                                # CRITICAL: Ensure trade is registered with position monitor
                                # Initialize position tracking if not already done (for trades that were created before monitoring started)
                                if trade_id not in position_monitor.trailing_stops:
                                    # Initialize trailing stop by calling update_position (it will create the stop if not exists)
                                    position_monitor.update_position(trade_id, stock_price, entry_price, action, entry_time, conditions)
                                    logger.debug(f"✅ Initialized position monitoring for trade {trade_id}")
                                
                                # Track max price for learning (store in trade if not exists)
                                if 'max_price' not in trade or stock_price > trade.get('max_price', entry_price):
                                    trade['max_price'] = stock_price
                                
                                # Add recent prices for volatility-based exit logic
                                # Get recent prices from flow history for volatility calculation
                                # CRITICAL: Ensure flow_data is valid before accessing nested data
                                if flow_data and isinstance(flow_data, dict):
                                    conditions['volatility_pct'] = flow_data.get('volatility_pct', 0)
                                    conditions['recent_prices'] = flow_data.get('recent_prices', [])
                                
                                if flow_history_data and len(flow_history_data) >= 5:
                                    recent_prices = [f.get('stock_price', 0) for f in flow_history_data[-10:] 
                                                   if f.get('stock_price', 0) > 0]
                                    conditions['recent_prices'] = recent_prices
                                
                                # Use position monitor for advanced exit logic (trailing stops, time-based exits, adaptive profit targets, volatility exits)
                                exit_suggestion = position_monitor.update_position(
                                    trade_id, stock_price, entry_price, action, entry_time, conditions
                                )
                                
                                # Check gamma risk (critical for 0DTE)
                                all_calls = flow_data.get('all_calls', [])
                                all_puts = flow_data.get('all_puts', [])
                                should_exit_gamma, gamma_reason = False, ''
                                if gamma_risk_calculator is not None:
                                    gamma_data = gamma_risk_calculator.calculate_gamma_exposure(
                                        all_calls, all_puts, stock_price
                                    )
                                    current_hour = datetime.now().hour
                                    should_exit_gamma, gamma_reason = gamma_risk_calculator.should_exit_due_to_gamma(
                                        gamma_data, current_hour
                                    )
                                
                                # Also check price level learner for top/bottom exits
                                if action == 'BUY_CALLS':
                                    should_close_pl, close_reason_pl, size_tier = price_level_learner.should_close_call_trade(
                                        symbol, entry_price, stock_price
                                    )
                                else:  # BUY_PUTS
                                    should_close_pl, close_reason_pl, size_tier = price_level_learner.should_close_put_trade(
                                        symbol, entry_price, stock_price
                                    )
                                
                                # Exit if position monitor suggests OR price level learner suggests OR gamma risk is high
                                should_close = exit_suggestion.get('exit_suggested', False) or should_close_pl or should_exit_gamma
                                
                                # Prioritize exit reasons: gamma risk > position monitor > price level learner
                                if should_exit_gamma:
                                    close_reason = gamma_reason
                                    exit_urgency = 'HIGH'
                                elif exit_suggestion.get('exit_suggested'):
                                    close_reason = exit_suggestion.get('exit_reason', '')
                                    exit_urgency = exit_suggestion.get('exit_urgency', 'MEDIUM')
                                else:
                                    close_reason = close_reason_pl
                                    exit_urgency = 'MEDIUM'
                                
                                # Track max price for learning (update if current price is higher)
                                max_price = trade.get('max_price', entry_price)
                                if action == 'BUY_CALLS':
                                    if stock_price > max_price:
                                        trade['max_price'] = stock_price
                                        max_price = stock_price
                                else:  # BUY_PUTS
                                    if stock_price < max_price:
                                        trade['max_price'] = stock_price
                                        max_price = stock_price
                                
                                # FIXED: Auto-close logic - Only HIGH urgency auto-closes to allow BIG WINNERS
                                # MEDIUM urgency suggests exit but doesn't auto-close (allows manual review)
                                # LOW urgency NEVER auto-closes - trades must run longer for bigger wins
                                # For 0DTE near end of day (after 3 PM), be more aggressive
                                is_0dte = (flow_data.get('dte', 1) == 0) or ('0DTE' in str(flow_data.get('expiration', '')))
                                current_hour = datetime.now().hour
                                is_late_day = current_hour >= 15  # After 3 PM
                                
                                # CRITICAL: Only auto-close on HIGH urgency (30%+ profits, stop losses), or MEDIUM if late in day for 0DTE
                                # LOW urgency is completely ignored - trades must run for bigger wins
                                should_auto_close = should_close and (
                                    exit_urgency == 'HIGH' or 
                                    (exit_urgency == 'MEDIUM' and is_0dte and is_late_day)
                                )
                                # LOW urgency exits are NEVER auto-closed - allows trades to run for 25%+ wins
                                
                                if should_auto_close:
                                    # Auto-close the trade with commission tracking
                                    # Get option price at exit for commission calculation
                                    exit_option_price = None
                                    num_contracts = trade.get('num_contracts', 1)
                                    try:
                                        # Try to get current option price from flow_data
                                        if action == 'BUY_CALLS':
                                            calls_by_strike, _ = extract_options_data(flow_data, symbol)
                                            for call in sorted(calls_by_strike, key=lambda x: abs(x.get('strike', 0) - stock_price)):
                                                if call.get('last_price', 0) > 0:
                                                    exit_option_price = call.get('last_price', 0)
                                                    break
                                        elif action == 'BUY_PUTS':
                                            _, puts_by_strike = extract_options_data(flow_data, symbol)
                                            for put in sorted(puts_by_strike, key=lambda x: abs(x.get('strike', 0) - stock_price)):
                                                if put.get('last_price', 0) > 0:
                                                    exit_option_price = put.get('last_price', 0)
                                                    break
                                    except Exception as e:
                                        logger.debug(f"Could not get exit option price: {e}")
                                    
                                    performance_tracker.close_trade(
                                        trade_id, stock_price,
                                        exit_option_price=exit_option_price,
                                        num_contracts=num_contracts
                                    )
                                    position_monitor.cleanup_position(trade_id)  # Remove from monitoring
                                    
                                    profit_pct = exit_suggestion.get('current_profit_pct', 0)
                                    if profit_pct == 0:
                                        # Calculate manually if not provided
                                        if action == 'BUY_CALLS':
                                            profit_pct = ((stock_price - entry_price) / entry_price * 100)
                                        else:
                                            profit_pct = ((entry_price - stock_price) / entry_price * 100)
                                    
                                    # Record outcome for profit target learning
                                    try:
                                        from profit_target_learner import profit_target_learner
                                        exit_time = datetime.now().isoformat()
                                        profit_target_learner.record_trade_outcome(
                                            trade_id, entry_time, exit_time,
                                            entry_price, stock_price, max_price,
                                            action, conditions
                                        )
                                    except Exception as e:
                                        logger.debug(f"Error recording profit outcome: {e}")
                                    
                                    # VALIDATION: Ensure profit_pct is valid
                                    if not isinstance(profit_pct, (int, float)) or profit_pct != profit_pct:  # Check for NaN
                                        logger.warning(f"Invalid profit_pct {profit_pct} for auto-closed trade {trade_id} - defaulting to 0")
                                        profit_pct = 0.0
                                    
                                    is_win = profit_pct > 0
                                    # Handle breakeven case
                                    if profit_pct == 0:
                                        outcome = 'BREAKEVEN'
                                    else:
                                        outcome = 'WIN' if is_win else 'LOSS'
                                    
                                    # VALIDATION: Ensure outcome is valid
                                    if outcome not in ['WIN', 'LOSS', 'BREAKEVEN']:
                                        logger.error(f"Invalid outcome '{outcome}' for auto-closed trade {trade_id}")
                                        outcome = 'WIN' if is_win else 'LOSS'  # Fallback
                                    
                                    # FIXED Bug 2: Record pattern result for historical pattern matching
                                    # Use global import (already imported at top level - line 82)
                                    try:
                                        if ADVANCED_CONFIDENCE_AVAILABLE and advanced_confidence_analyzer:
                                            # Extract pattern from flow_data at time of trade entry (use current flow_data as proxy)
                                            pattern = {
                                                'cp_ratio': flow_data.get('flow_metrics', {}).get('call_put_ratio', 1.0),
                                                'net_flow': flow_data.get('flow_metrics', {}).get('net_volume_flow', 0),
                                                'premium_flow': flow_data.get('flow_metrics', {}).get('net_premium_flow', 0),
                                                'action': action
                                            }
                                            advanced_confidence_analyzer.record_pattern_result(pattern, outcome)
                                            logger.debug(f"✅ Recorded pattern result for auto-closed trade {trade_id}: {outcome}")
                                    except Exception as e:
                                        logger.debug(f"Error recording pattern result for auto-closed trade: {e}")
                                    
                                    logger.info(f"🔄 TRADE CLOSED: {trade_id} - {close_reason} (P&L: {profit_pct:.2f}%) - {outcome}")
                                    
                                    # CRITICAL: Record bot prediction outcomes for auto-closed trades
                                    # This was missing - bots were getting 0% win rate because outcomes weren't recorded!
                                    try:
                                        # Get bot_predictions from trade entry (stored when trade was opened)
                                        trade_bot_predictions = trade.get('bot_predictions', {})
                                        
                                        if trade_bot_predictions:
                                            # VALIDATION: Ensure bot_predictions is a dict
                                            if not isinstance(trade_bot_predictions, dict):
                                                logger.warning(f"Trade {trade_id} bot_predictions is not a dict: {type(trade_bot_predictions)}")
                                                trade_bot_predictions = {}
                                            
                                            # Update the bot predictions that actually led to this trade
                                            for bot_id, prediction in trade_bot_predictions.items():
                                                try:
                                                    # VALIDATION: Ensure prediction is a dict
                                                    if not isinstance(prediction, dict):
                                                        logger.warning(f"Invalid bot prediction format for {bot_id} in trade {trade_id}: {type(prediction)}")
                                                        continue
                                                    
                                                    # VALIDATION: Ensure prediction has required fields
                                                    if 'action' not in prediction:
                                                        logger.warning(f"Bot prediction for {bot_id} missing 'action' field in trade {trade_id}")
                                                        continue
                                                    
                                                    # Record outcome for this bot's prediction
                                                    if enhanced_bot_consensus is not None:
                                                        enhanced_bot_consensus.record_bot_prediction(
                                                            bot_id, prediction, outcome, symbol=symbol
                                                        )
                                                    logger.debug(f"✅ Recorded outcome '{outcome}' for bot {bot_id} in auto-closed trade {trade_id}")
                                                except Exception as bot_error:
                                                    logger.error(f"Error recording outcome for bot {bot_id} in auto-closed trade {trade_id}: {bot_error}")
                                        else:
                                            logger.warning(f"Trade {trade_id} missing bot_predictions - cannot record bot outcomes for auto-closed trade")
                                    except Exception as e:
                                        logger.error(f"CRITICAL: Failed to record bot prediction outcomes for auto-closed trade {trade_id}: {e}", exc_info=True)
                                    
                                    # Add exit suggestion to signal analysis for frontend display
                                    if 'position_exits' not in signal_analysis:
                                        signal_analysis['position_exits'] = []
                                    signal_analysis['position_exits'].append({
                                        'trade_id': trade_id,
                                        'action': action,
                                        'exit_reason': close_reason,
                                        'profit_pct': profit_pct,
                                        'outcome': outcome
                                    })
                                elif should_close:
                                    # Log suggestion but don't auto-close (user can decide)
                                    # Calculate profit_pct for suggestion (needed for learning)
                                    profit_pct = exit_suggestion.get('current_profit_pct', 0)
                                    if profit_pct == 0:
                                        # Calculate manually if not provided
                                        if action == 'BUY_CALLS':
                                            profit_pct = ((stock_price - entry_price) / entry_price * 100)
                                        else:
                                            profit_pct = ((entry_price - stock_price) / entry_price * 100)
                                    
                                    # VALIDATION: Ensure profit_pct is valid
                                    if not isinstance(profit_pct, (int, float)) or profit_pct != profit_pct:
                                        logger.warning(f"Invalid profit_pct {profit_pct} for trade {trade_id} exit suggestion - defaulting to 0")
                                        profit_pct = 0.0
                                    
                                    is_win = profit_pct > 0
                                    # Handle breakeven case
                                    if profit_pct == 0:
                                        outcome = 'BREAKEVEN'
                                    else:
                                        outcome = 'WIN' if is_win else 'LOSS'
                                    
                                    logger.info(f"💡 EXIT SUGGESTION: {trade_id} - {close_reason} + profit: {profit_pct:.1f}% (Urgency: {exit_urgency})")
                                    
                                    # Add exit suggestion to signal analysis for frontend display
                                    if 'position_exits' not in signal_analysis:
                                        signal_analysis['position_exits'] = []
                                    signal_analysis['position_exits'].append({
                                        'trade_id': trade_id,
                                        'action': action,
                                        'exit_reason': close_reason,
                                        'exit_urgency': exit_urgency,
                                        'profit_pct': profit_pct,
                                        'suggestion_only': True
                                    })
                                    
                                    # AUTONOMOUS LEARNING: Record outcome for all learning systems
                                    # Ensure profit_pct is defined before using it in learning systems
                                    if 'profit_pct' not in locals() or profit_pct is None:
                                        # Calculate profit_pct if not already calculated
                                        if action == 'BUY_CALLS':
                                            profit_pct = ((stock_price - entry_price) / entry_price * 100)
                                        else:
                                            profit_pct = ((entry_price - stock_price) / entry_price * 100)
                                    
                                    # VALIDATION: Ensure profit_pct is valid
                                    if 'profit_pct' not in locals() or not isinstance(profit_pct, (int, float)) or profit_pct != profit_pct:
                                        # Calculate profit_pct if not already calculated
                                        if action == 'BUY_CALLS':
                                            profit_pct = ((stock_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
                                        else:
                                            profit_pct = ((entry_price - stock_price) / entry_price * 100) if entry_price > 0 else 0
                                    
                                    if 'is_win' not in locals() or is_win is None:
                                        is_win = profit_pct > 0
                                    
                                    if 'outcome' not in locals() or outcome is None:
                                        # Handle breakeven case
                                        if profit_pct == 0:
                                            outcome = 'BREAKEVEN'
                                        else:
                                            outcome = 'WIN' if is_win else 'LOSS'
                                    
                                    # VALIDATION: Ensure outcome is valid before recording
                                    if outcome not in ['WIN', 'LOSS', 'BREAKEVEN']:
                                        logger.error(f"Invalid outcome '{outcome}' for trade {trade_id} - skipping bot prediction update")
                                        outcome = 'WIN' if is_win else 'LOSS'  # Fallback to valid outcome
                                    
                                    # TRANSACTION-LIKE ERROR HANDLING: Record all outcomes atomically
                                    outcome_recording_errors = []
                                    try:
                                        # CRITICAL FIX: Use bot_predictions from trade entry, not current flow update
                                        # Retrieve the bot predictions that were made when this trade was ENTERED
                                        trade_bot_predictions = trade.get('bot_predictions', {})
                                        
                                        if trade_bot_predictions:
                                            # VALIDATION: Ensure bot_predictions is a dict
                                            if not isinstance(trade_bot_predictions, dict):
                                                logger.warning(f"Trade {trade_id} bot_predictions is not a dict: {type(trade_bot_predictions)}")
                                                trade_bot_predictions = {}
                                            
                                            # Update the bot predictions that actually led to this trade
                                            for bot_id, prediction in trade_bot_predictions.items():
                                                try:
                                                    # VALIDATION: Ensure prediction is a dict
                                                    if not isinstance(prediction, dict):
                                                        logger.warning(f"Invalid bot prediction format for {bot_id} in trade {trade_id}: {type(prediction)}")
                                                        continue
                                                    
                                                    # VALIDATION: Ensure prediction has required fields
                                                    if 'action' not in prediction:
                                                        logger.warning(f"Bot prediction for {bot_id} missing 'action' field in trade {trade_id}")
                                                        continue
                                                    
                                                    # Record outcome for this bot's prediction
                                                    if enhanced_bot_consensus is not None:
                                                        enhanced_bot_consensus.record_bot_prediction(
                                                            bot_id, prediction, outcome, symbol=symbol
                                                        )
                                                except Exception as bot_error:
                                                    error_msg = f"Error recording outcome for bot {bot_id} in trade {trade_id}: {bot_error}"
                                                    logger.error(error_msg)
                                                    outcome_recording_errors.append(error_msg)
                                        else:
                                            # Fallback: If bot_predictions not stored, try to use current ones
                                            # But log a warning since this is not ideal
                                            logger.warning(f"Trade {trade_id} missing bot_predictions - using current predictions (may be inaccurate)")
                                            if bot_predictions.get('bot_predictions'):
                                                for bot_id, prediction in bot_predictions['bot_predictions'].items():
                                                    try:
                                                        if isinstance(prediction, dict) and 'action' in prediction and enhanced_bot_consensus is not None:
                                                            enhanced_bot_consensus.record_bot_prediction(
                                                                bot_id, prediction, outcome, symbol=symbol
                                                            )
                                                    except Exception as bot_error:
                                                        error_msg = f"Error recording fallback outcome for bot {bot_id}: {bot_error}"
                                                        logger.error(error_msg)
                                                        outcome_recording_errors.append(error_msg)
                                        
                                        # Log summary of outcome recording
                                        if outcome_recording_errors:
                                            logger.warning(f"Trade {trade_id} outcome recording had {len(outcome_recording_errors)} errors: {outcome_recording_errors}")
                                        else:
                                            logger.debug(f"✅ Successfully recorded outcome '{outcome}' for all bot predictions in trade {trade_id}")
                                    except Exception as e:
                                        logger.error(f"CRITICAL: Failed to record bot prediction outcomes for trade {trade_id}: {e}", exc_info=True)
                                        
                                        # Learn from closed trade - record outcome for ML training (ENHANCED)
                                        # Get enhanced features including EMAs for better learning
                                        if should_run_heavy_calcs:
                                            # Update technical indicators with current price
                                            try:
                                                from technical_indicators import technical_indicators
                                                technical_indicators.update_price(symbol, stock_price)
                                            except Exception:
                                                pass
                                            
                                            # Extract comprehensive features (now includes EMAs and symbol)
                                            if ml_feature_engineer is None:
                                                features = {}
                                            else:
                                                features = ml_feature_engineer.extract_features(flow_data, signal_analysis, flow_history_data, symbol=symbol)
                                            
                                            # Add trade-specific features for enhanced learning
                                            features['entry_price'] = float(entry_price)
                                            features['exit_price'] = float(stock_price)
                                            features['profit_pct'] = float(profit_pct)
                                            features['hold_duration'] = 0.0  # Could calculate if we track entry time
                                            
                                            # Get EMA signals at exit
                                            try:
                                                from technical_indicators import technical_indicators
                                                ema_signals = technical_indicators.get_ema_signals(symbol, stock_price)
                                                features['exit_ema_trend'] = features.get('ema_trend', 0.0)
                                                features['exit_price_vs_ema50'] = features.get('price_vs_ema50', 0.0)
                                            except Exception:
                                                pass
                                            
                                            # FIXED Bug 2: Record pattern result for historical pattern matching
                                            # Use global import (already imported at top level - line 82)
                                            try:
                                                if ADVANCED_CONFIDENCE_AVAILABLE and advanced_confidence_analyzer:
                                                    # Extract pattern from flow_data and signal_data
                                                    # Use trade action (what was actually traded), not current prediction
                                                    # CRITICAL: Defensive check - flow_data must be a dict
                                                    flow_metrics = {}
                                                    if flow_data and isinstance(flow_data, dict):
                                                        flow_metrics = flow_data.get('flow_metrics', {})
                                                        if not isinstance(flow_metrics, dict):
                                                            flow_metrics = {}
                                                    
                                                    pattern = {
                                                        'cp_ratio': flow_metrics.get('call_put_ratio', 1.0) if flow_metrics else 1.0,
                                                        'net_flow': flow_metrics.get('net_volume_flow', 0) if flow_metrics else 0,
                                                        'premium_flow': flow_metrics.get('net_premium_flow', 0) if flow_metrics else 0,
                                                        'action': trade['action']  # Use actual trade action
                                                    }
                                                    advanced_confidence_analyzer.record_pattern_result(pattern, outcome)
                                                    logger.debug(f"✅ Recorded pattern result for {trade_id}: {outcome}")
                                            except Exception as e:
                                                logger.debug(f"Error recording pattern result: {e}")
                                            
                                            # Record signal for quality analysis (META-LEARNING)
                                            signal_quality_analyzer.record_signal(
                                                signal_data={
                                                    **features,
                                                    'confidence': signal_analysis.get('confidence', 50),
                                                    'action': trade['action'],
                                                    'approaching_top': signal_analysis.get('approaching_top', False),
                                                    'approaching_bottom': signal_analysis.get('approaching_bottom', False),
                                                    'ema_trend': features.get('ema_trend', 0.0),
                                                    'above_ema50': features.get('above_ema50', 0.0),
                                                    'price_vs_ema50': features.get('price_vs_ema50', 0.0),
                                                    'flow_metrics': flow_data.get('flow_metrics', {})
                                                },
                                                trade_outcome={
                                                    'outcome': outcome,
                                                    'profit_pct': profit_pct,
                                                    'is_win': is_win
                                                }
                                            )
                                            
                                            # Only record winning trades as positive examples
                                            # But still learn from losses (record as negative examples)
                                            ml_engine = get_ml_prediction_engine()
                                            if ml_engine:
                                                if is_win:
                                                    # Record win as positive training example with enhanced features
                                                    ml_engine.record_training_sample(
                                                        features,
                                                        trade['action'],
                                                        actual_outcome='WIN',
                                                        symbol=symbol
                                                    )
                                                    logger.info(f"✅ Recorded WINNING trade for ML learning: {trade['trade_id']} ({profit_pct:.2f}%) - Enhanced with EMAs + Signal Analysis")
                                                else:
                                                    # Record loss as negative example (learn what NOT to do)
                                                    ml_engine.record_training_sample(
                                                        features,
                                                        trade['action'],
                                                        actual_outcome='LOSS',
                                                        symbol=symbol
                                                    )
                                                logger.info(f"📉 Recorded LOSS for ML learning: {trade['trade_id']} ({profit_pct:.2f}%) - Enhanced with EMAs + Signal Analysis")
                                    except Exception as e:
                                        logger.debug(f"Error recording trade outcome for ML: {e}")
                                    
                                    # Ensure profit_pct, outcome, and is_win are defined before using them
                                    # (They should be defined above, but check to prevent UnboundLocalError)
                                    if 'profit_pct' not in locals():
                                        # Calculate profit_pct if not already calculated
                                        if action == 'BUY_CALLS':
                                            profit_pct = ((stock_price - entry_price) / entry_price * 100)
                                        else:
                                            profit_pct = ((entry_price - stock_price) / entry_price * 100)
                                    
                                    if 'is_win' not in locals():
                                        is_win = profit_pct > 0
                                    
                                    if 'outcome' not in locals():
                                        outcome = 'WIN' if is_win else 'LOSS'
                                    
                                    signal_analysis['auto_closed_trade'] = {
                                        'trade_id': trade['trade_id'],
                                        'symbol': symbol,  # FIXED: Include symbol in closed trade notification
                                        'action': trade.get('action', ''),
                                        'reason': close_reason,
                                        'size_tier': size_tier,
                                        'entry_price': entry_price,
                                        'exit_price': stock_price,
                                        'profit_pct': round(profit_pct, 2),
                                        'pnl': round((stock_price - entry_price) * (1 if trade.get('action') == 'BUY_CALLS' else -1), 2),  # FIXED: Add pnl field for frontend
                                        'outcome': outcome,
                                        'is_win': is_win
                                    }
                    
                    # Add performance stats to signal — cache hard (was reloading module every loop)
                    ml_performance = signal_analyzer.get_performance_summary()
                    now_perf = time.time()
                    cached_tp = getattr(background_data_updater, '_trade_perf_cache', None)
                    cached_at = float(getattr(background_data_updater, '_trade_perf_cache_at', 0) or 0)
                    if cached_tp is not None and (now_perf - cached_at) < 15.0:
                        trade_performance = cached_tp
                    else:
                        performance_tracker = get_performance_tracker()
                        if performance_tracker is not None:
                            trade_performance = performance_tracker.get_performance_stats()
                        else:
                            # Stage A: feed WS payload from Boss shadow summary (never call methods on None)
                            try:
                                from shadow_learning_engine import shadow_learning_engine as _sh
                                _s = _sh.summary()
                                trade_performance = {
                                    'win_rate': _s.get('win_rate_today') or 0,
                                    'today_win_rate': _s.get('win_rate_today') or 0,
                                    'total_trades': int(_s.get('closed_today') or 0) + int(_s.get('open_count') or 0),
                                    'today_trades': int(_s.get('closed_today') or 0),
                                    'closed_trades': int(_s.get('closed_today') or 0),
                                    'open_trades': int(_s.get('open_count') or 0),
                                    'wins': int(_s.get('wins_today') or 0),
                                    'losses': int(_s.get('losses_today') or 0),
                                    'source': 'shadow',
                                }
                            except Exception:
                                trade_performance = {'win_rate': 0, 'total_trades': 0, 'source': 'shadow'}
                        background_data_updater._trade_perf_cache = trade_performance
                        background_data_updater._trade_perf_cache_at = now_perf
                    signal_analysis['ml_performance'] = ml_performance
                    signal_analysis['trade_performance'] = trade_performance
                    
                    # Track order flow history
                    order_flow_history.add_flow_snapshot(symbol, flow_data)
                    flow_history_data = order_flow_history.get_recent_flow(symbol, count=50)
                    
                    # Detect unusual activity
                    unusual_activity = unusual_activity_detector.detect_unusual_activity(flow_data)
                    
                    # Initialize extended hours price variables (will be populated later)
                    # CRITICAL: Use stock_price from flow_data as initial value (it's already fetched)
                    # Add validation to prevent AttributeError if flow_data is None
                    # CRITICAL FIX: Always preserve flow_data.stock_price as fallback
                    aftermarket_price = 0
                    premarket_price = 0
                    # Store flow_data stock_price for fallback (before any yfinance calls)
                    flow_data_stock_price = 0
                    if flow_data and isinstance(flow_data, dict):
                        flow_data_stock_price = flow_data.get('stock_price', 0)
                        if flow_data_stock_price > 0:
                            regular_close = flow_data_stock_price  # Use flow_data stock_price as initial value
                        else:
                            regular_close = 0  # Will try to populate from yfinance
                    else:
                        regular_close = 0  # flow_data is None or invalid
                        logger.warning(f"⚠️ flow_data is None or invalid for {symbol} - will try yfinance")
                    
                    # Calculate data freshness - CRITICAL: Check if flow_data exists before accessing
                    data_timestamp = datetime.now()  # Default to current time
                    if flow_data and isinstance(flow_data, dict):
                        data_timestamp = flow_data.get('timestamp', datetime.now())
                    if isinstance(data_timestamp, datetime):
                        data_age_seconds = (datetime.now() - data_timestamp).total_seconds()
                    else:
                        data_age_seconds = 0
                    
                    # Determine if data is "new" or "old" (preserve closed-session snapshot tag)
                    if flow_data and isinstance(flow_data, dict) and (
                        flow_data.get('data_freshness') == 'CLOSED' or flow_data.get('snapshot_mode')
                    ):
                        data_freshness = 'CLOSED'
                        freshness_color = 'var(--text-secondary)'
                    elif data_age_seconds < 60:
                        data_freshness = 'NEW'
                        freshness_color = 'var(--success-color)'
                    elif data_age_seconds < 300:
                        data_freshness = 'RECENT'
                        freshness_color = 'var(--warning-color)'
                    else:
                        data_freshness = 'OLD'
                        freshness_color = 'var(--danger-color)'
                    
                    # Get previous close, aftermarket, and premarket prices
                    # Note: aftermarket_price, premarket_price, regular_close already initialized above
                    prev_close = 0
                    aftermarket_change_pct = 0
                    premarket_change_pct = 0
                    
                    try:
                        # REGULAR hours: already have a live chain spot — never sync-block on ticker.info
                        # Extended hours only need the Yahoo info path for PM/AH prints.
                        if current_session == 'REGULAR' and float(flow_data_stock_price or 0) > 0:
                            regular_close = float(flow_data_stock_price)
                            prev_close = float(flow_data.get('prev_close') or 0) if isinstance(flow_data, dict) else 0
                            aftermarket_price = 0
                            premarket_price = 0
                            aftermarket_change_pct = 0
                            premarket_change_pct = 0
                            hist = None
                            info_temp = None
                        else:
                            # Track yfinance API usage for stock prices (extended hours)
                            # CRITICAL: Ensure yf is available (imported at top level)
                            if 'yf' not in globals():
                                import yfinance as yf
                            
                            can_request_stock, reason_stock = api_tracker.can_make_request('yfinance')
                            if not can_request_stock:
                                logger.warning(f"⚠️ yfinance rate limited for stock prices: {reason_stock} - using flow_data stock_price as fallback")
                                # Use flow_data stock_price if rate limited
                                if regular_close == 0:
                                    regular_close = flow_data.get('stock_price', 0) if isinstance(flow_data, dict) else 0
                                    if regular_close > 0:
                                        logger.info(f"Using flow_data stock_price as regular_close (rate limited): ${regular_close:.2f}")
                                # Record the rate limit hit
                                api_tracker.record_request('yfinance', success=False, error=f"Rate limited: {reason_stock}")
                                hist = None
                                info_temp = None
                            else:
                                # Fetch stock quote off the event loop
                                def _fetch_stock_meta():
                                    import yfinance as _yf
                                    t = _yf.Ticker(symbol)
                                    info = None
                                    try:
                                        info = t.info
                                    except Exception:
                                        info = None
                                    h = t.history(period="2d", interval="1d")
                                    return info, h

                                loop = asyncio.get_running_loop()
                                try:
                                    info_temp, hist = await asyncio.wait_for(
                                        loop.run_in_executor(None, _fetch_stock_meta),
                                        timeout=6.0,
                                    )
                                    api_tracker.record_request('yfinance', success=True)
                                except Exception as e:
                                    logger.warning(f"Extended-hours stock meta failed for {symbol}: {e}")
                                    info_temp, hist = None, None
                                    api_tracker.record_request('yfinance', success=False, error=str(e)[:80])
                                    if regular_close == 0 and isinstance(flow_data, dict):
                                        regular_close = flow_data.get('stock_price', 0)
                        
                        # Get previous day's close from history (always available)
                        if hist is not None and hasattr(hist, 'empty') and (not hist.empty) and len(hist) >= 2:
                            prev_close = float(hist['Close'].iloc[-2])  # Previous day's close
                            logger.debug(f"Previous close from history: ${prev_close:.2f}")
                        elif hist is not None and hasattr(hist, 'empty') and (not hist.empty) and len(hist) >= 1:
                            # If only one day, use it as previous close
                            prev_close = float(hist['Close'].iloc[-1])
                            logger.debug(f"Previous close (single day): ${prev_close:.2f}")
                        
                        # During REGULAR hours: use current price as regular_close
                        # During extended hours: use yesterday's close as regular_close
                        if current_session == 'REGULAR':
                            # Regular hours: prefer chain spot (already set); optional info refresh
                            if regular_close == 0 and info_temp and 'regularMarketPrice' in info_temp:
                                try:
                                    regular_close = float(info_temp['regularMarketPrice'])
                                except (ValueError, TypeError):
                                    pass
                            if regular_close == 0 and info_temp and 'currentPrice' in info_temp:
                                try:
                                    regular_close = float(info_temp['currentPrice'])
                                except (ValueError, TypeError):
                                    pass
                            if regular_close == 0 and isinstance(flow_data, dict):
                                regular_close = float(flow_data.get('stock_price') or 0)
                        else:
                            # Extended hours: use yesterday's close from history
                            if hist is not None and hasattr(hist, 'empty') and (not hist.empty) and len(hist) >= 1:
                                regular_close = float(hist['Close'].iloc[-1])  # Yesterday's close
                                logger.debug(f"Regular close (yesterday) from history: ${regular_close:.2f}")
                        
                            # Fallback chain for regular_close
                            if regular_close == 0:
                                if info_temp and 'regularMarketPrice' in info_temp:
                                    try:
                                        regular_close = float(info_temp['regularMarketPrice'])
                                    except (ValueError, TypeError):
                                        pass
                                
                                if regular_close == 0 and info_temp and 'currentPrice' in info_temp:
                                    try:
                                        regular_close = float(info_temp['currentPrice'])
                                    except (ValueError, TypeError):
                                        pass
                                
                                # Final fallback: use stock_price from flow_data (already fetched)
                                if regular_close == 0 and isinstance(flow_data, dict):
                                    regular_close = flow_data.get('stock_price', 0)
                                    if regular_close > 0:
                                        logger.debug(f"Regular close from flow_data stock_price: ${regular_close:.2f}")
                        
                        # Skip extended-hours Yahoo probes during RTH (was blocking the WS feed every loop)
                        info = info_temp
                        fast_info = None
                        if current_session != 'REGULAR':
                            # Get aftermarket/premarket data - try multiple methods
                            info = None
                            fast_info = None
                            try:
                                import yfinance as yf
                                ticker = yf.Ticker(symbol)
                                info = info_temp if info_temp else ticker.info
                                fast_info = ticker.fast_info
                            except Exception as e:
                                logger.debug(f"Could not fetch fast_info/info: {e}")
                        
                            # Method 1: Try fast_info first (more reliable)
                            try:
                                if hasattr(fast_info, 'postMarketPrice') and fast_info.postMarketPrice:
                                    aftermarket_price = float(fast_info.postMarketPrice)
                                    if regular_close > 0:
                                        aftermarket_change_pct = ((aftermarket_price - regular_close) / regular_close) * 100
                                        logger.debug(f"Got aftermarket price from fast_info: ${aftermarket_price:.2f}")
                                
                                if hasattr(fast_info, 'preMarketPrice') and fast_info.preMarketPrice:
                                    premarket_price = float(fast_info.preMarketPrice)
                                    if regular_close > 0:
                                        premarket_change_pct = ((premarket_price - regular_close) / regular_close) * 100
                                        logger.debug(f"Got premarket price from fast_info: ${premarket_price:.2f}")
                            except Exception as e:
                                logger.debug(f"fast_info method failed: {e}")
                        
                            # Method 2: Try info dict (this is the most reliable)
                            if info:
                                # Try to get aftermarket price - CHECK BOTH postMarketPrice AND postMarketChangePercent
                                post_market = info.get('postMarketPrice')
                                post_change_pct = info.get('postMarketChangePercent')
                                
                                logger.info(f"Extended hours check - postMarketPrice: {post_market}, postMarketChangePercent: {post_change_pct}, regular_close: {regular_close}")
                                
                                # If we have postMarketChangePercent but postMarketPrice is None/0, calculate it
                                if (post_market is None or post_market == 0) and post_change_pct is not None and regular_close > 0:
                                    post_market = regular_close * (1 + post_change_pct / 100)
                                    aftermarket_price = float(post_market)
                                    aftermarket_change_pct = float(post_change_pct)
                                    logger.info(f"CALCULATED aftermarket price from postMarketChangePercent: ${aftermarket_price:.2f} ({aftermarket_change_pct:.2f}%)")
                                elif post_market is not None and post_market != 0:
                                    try:
                                        aftermarket_price = float(post_market)
                                        logger.info(f"FOUND AFTERMARKET PRICE: ${aftermarket_price:.2f}, regular_close: ${regular_close:.2f}")
                                        # Calculate change if we have regular close (always calculate if we have both)
                                        if regular_close > 0:
                                            aftermarket_change_pct = ((aftermarket_price - regular_close) / regular_close) * 100
                                            logger.info(f"Aftermarket change calculated: {aftermarket_change_pct:.2f}%")
                                        elif post_change_pct is not None:
                                            aftermarket_change_pct = float(post_change_pct)
                                            logger.info(f"Using postMarketChangePercent: {aftermarket_change_pct:.2f}%")
                                        else:
                                            logger.warning(f"Aftermarket price found (${aftermarket_price:.2f}) but regular_close is 0, will send price without change %")
                                    except (ValueError, TypeError) as e:
                                        logger.error(f"Error converting postMarketPrice: {e}")
                                else:
                                    logger.debug(f"postMarketPrice is None or 0: {post_market}, postMarketChangePercent: {post_change_pct}")
                                
                                # Try to get premarket price
                                pre_market = info.get('preMarketPrice')
                                if pre_market is not None and pre_market != 0:
                                    try:
                                        premarket_price = float(pre_market)
                                        logger.info(f"Found premarket price: ${premarket_price:.2f}, regular_close: ${regular_close:.2f}")
                                        # Calculate change if we have regular close (always calculate if we have both)
                                        if regular_close > 0:
                                            premarket_change_pct = ((premarket_price - regular_close) / regular_close) * 100
                                            logger.info(f"Premarket change calculated: {premarket_change_pct:.2f}%")
                                        else:
                                            logger.warning(f"Premarket price found (${premarket_price:.2f}) but regular_close is 0, will send price without change %")
                                    except (ValueError, TypeError) as e:
                                        logger.debug(f"Error converting preMarketPrice: {e}")
                                
                                # Also check postMarketChangePercent for additional validation
                                if aftermarket_price == 0 and 'postMarketChangePercent' in info:
                                    post_change_pct = info.get('postMarketChangePercent')
                                    if post_change_pct is not None:
                                        logger.debug(f"Found postMarketChangePercent: {post_change_pct}, but no postMarketPrice")
                                
                                # Method 3: Check currentPrice vs regularMarketPrice (fallback)
                                if aftermarket_price == 0 and premarket_price == 0:
                                    if 'regularMarketPrice' in info and info.get('regularMarketPrice'):
                                        try:
                                            regular_market_price = float(info['regularMarketPrice'])
                                            if 'currentPrice' in info and info.get('currentPrice'):
                                                current_price = float(info['currentPrice'])
                                                # If current price differs from regular market price, it might be aftermarket/premarket
                                                if abs(current_price - regular_market_price) > 0.01:
                                                    # Determine if aftermarket or premarket based on time
                                                    now = datetime.now()
                                                    if now.hour >= 16 or (now.hour == 15 and now.minute >= 30):  # After 4 PM
                                                        aftermarket_price = current_price
                                                        if regular_close > 0:
                                                            aftermarket_change_pct = ((aftermarket_price - regular_close) / regular_close) * 100
                                                            logger.debug(f"Got aftermarket price from currentPrice: ${aftermarket_price:.2f}")
                                                    elif now.hour < 9 or (now.hour == 9 and now.minute < 30):  # Before 9:30 AM
                                                        premarket_price = current_price
                                                        if regular_close > 0:
                                                            premarket_change_pct = ((premarket_price - regular_close) / regular_close) * 100
                                                            logger.debug(f"Got premarket price from currentPrice: ${premarket_price:.2f}")
                                        except (ValueError, TypeError) as e:
                                            logger.debug(f"Error in Method 3 currentPrice comparison: {e}")
                        # end extended-hours-only Yahoo probes
                    except Exception as e:
                        # CRITICAL: Ensure yf is available (it's imported at top level, but catch any scope issues)
                        error_msg = str(e)
                        if "yf" in error_msg or "yfinance" in error_msg:
                            logger.warning(f"Could not get extended hours prices for {symbol}: {e} - yfinance scope issue, using flow_data stock_price")
                        else:
                            logger.warning(f"Could not get extended hours prices for {symbol}: {e}")
                        # Ensure we at least have stock_price from flow_data
                        # CRITICAL FIX: Use stored flow_data_stock_price (preserved before yfinance calls)
                        if regular_close == 0 and flow_data_stock_price > 0:
                            regular_close = flow_data_stock_price
                            logger.info(f"Using flow_data stock_price as regular_close after error: ${regular_close:.2f}")
                        elif regular_close == 0 and flow_data and isinstance(flow_data, dict):
                            regular_close = flow_data.get('stock_price', 0)
                            if regular_close > 0:
                                logger.info(f"Using flow_data stock_price as regular_close after error: ${regular_close:.2f}")
                    
                    # Log extended hours data for debugging (IMPROVED: Better error context)
                    logger.info(f"FINAL Price data for {symbol}:")
                    # Determine price source safely
                    price_source = 'unknown'
                    if flow_data and isinstance(flow_data, dict) and regular_close == flow_data.get('stock_price', 0):
                        price_source = 'flow_data'
                    elif flow_data_stock_price > 0 and regular_close == flow_data_stock_price:
                        price_source = 'flow_data (preserved)'
                    else:
                        price_source = 'yfinance'
                    logger.info(f"   Regular close: ${regular_close:.2f} (from: {price_source}, flow_data_stock_price: ${flow_data_stock_price:.2f})")
                    logger.info(f"   Aftermarket: ${aftermarket_price:.2f} (change: {aftermarket_change_pct:.2f}%)")
                    logger.info(f"   Premarket: ${premarket_price:.2f} (change: {premarket_change_pct:.2f}%)")
                    logger.info(f"   Sending to client - aftermarket_price={aftermarket_price}, premarket_price={premarket_price}, regular_close={regular_close}")
                    
                    # CRITICAL: If regular_close is still 0, use stock_price from flow_data (should never be 0)
                    # FIX: Use stored flow_data_stock_price to ensure we always have a fallback
                    if regular_close == 0:
                        if flow_data_stock_price > 0:
                            regular_close = flow_data_stock_price
                            logger.warning(f"⚠️ regular_close was 0, using flow_data stock_price (preserved): ${regular_close:.2f}")
                        elif flow_data and isinstance(flow_data, dict):
                            regular_close = flow_data.get('stock_price', 0)
                            if regular_close > 0:
                                logger.warning(f"⚠️ regular_close was 0, using flow_data stock_price: ${regular_close:.2f}")
                            else:
                                logger.error(f"❌ CRITICAL: Both regular_close and flow_data.stock_price are 0 for {symbol}!")
                        else:
                            logger.error(f"❌ CRITICAL: regular_close is 0 and flow_data is None or invalid for {symbol}!")
                    
                    # Update price levels for learning (track highs/lows) - NOW that variables are populated
                    # Use aftermarket/premarket price if available, otherwise use regular close or current price
                    stock_price = flow_data.get('stock_price', 0)
                    # Prefer extended hours prices for tracking (they're more current)
                    price_to_track = stock_price
                    if aftermarket_price > 0:
                        price_to_track = aftermarket_price
                    elif premarket_price > 0:
                        price_to_track = premarket_price
                    elif regular_close > 0:
                        price_to_track = regular_close
                    
                    if price_to_track > 0:
                        try:
                            from price_level_learner import price_level_learner
                            price_level_learner.update_price(symbol, price_to_track)
                        except (ImportError, Exception) as e:
                            logger.debug(f"Error updating price levels: {e}")
                    
                    # Helper function to convert datetime objects and other non-JSON types to strings for JSON serialization
                    def convert_datetime_for_json(obj):
                        """Recursively convert datetime objects, numpy types, and other non-JSON types to JSON-compatible types"""
                        import math
                        import numpy as np
                        if isinstance(obj, datetime):
                            return obj.isoformat()
                        elif isinstance(obj, (np.bool_, bool)):
                            # Handle numpy bool and regular bool
                            return bool(obj)
                        elif isinstance(obj, (np.integer, int)):
                            return int(obj)
                        elif isinstance(obj, (np.floating, float)):
                            try:
                                v = float(obj)
                                if not math.isfinite(v):
                                    return None
                                return v
                            except (TypeError, ValueError):
                                return None
                        elif isinstance(obj, dict):
                            return {k: convert_datetime_for_json(v) for k, v in obj.items()}
                        elif isinstance(obj, list):
                            return [convert_datetime_for_json(item) for item in obj]
                        elif hasattr(obj, '__dict__'):
                            # Handle objects with __dict__ (like pandas Timestamp)
                            try:
                                if hasattr(obj, 'isoformat'):
                                    return obj.isoformat()
                                elif hasattr(obj, 'strftime'):
                                    return obj.strftime('%Y-%m-%d %H:%M:%S')
                            except (AttributeError, TypeError, ValueError) as e:
                                # Non-critical: datetime conversion failed, continue to default handling
                                logger.debug(f"Could not convert datetime object to string: {e}")
                                pass
                        return obj
                    
                    # Clean all data for JSON serialization
                    clean_flow_metrics = convert_datetime_for_json(flow_data.get('flow_metrics', {})) if flow_data.get('flow_metrics') else {}
                    
                    # ENHANCED: If flow_metrics are all zero but we have options data, recalculate from options
                    # Also recalculate if flow_metrics is empty or missing
                    should_recalculate = False
                    if not clean_flow_metrics or not isinstance(clean_flow_metrics, dict):
                        should_recalculate = bool(calls_sorted or puts_sorted)
                        logger.debug(f"⚠️ Flow metrics missing/empty for {symbol} - will recalculate from options data")
                    elif isinstance(clean_flow_metrics, dict):
                        total_call_vol = clean_flow_metrics.get('total_call_volume', 0)
                        total_put_vol = clean_flow_metrics.get('total_put_volume', 0)
                        # If metrics are zero but we have options, recalculate
                        if (total_call_vol == 0 and total_put_vol == 0) and (calls_sorted or puts_sorted):
                            should_recalculate = True
                            logger.debug(f"⚠️ Flow metrics are zero but options exist for {symbol} - recalculating...")
                    
                    if should_recalculate and (calls_sorted or puts_sorted):
                        # Recalculate metrics from actual options data
                        total_call_vol = sum(c.get('volume', 0) for c in calls_sorted) if calls_sorted else 0
                        total_put_vol = sum(p.get('volume', 0) for p in puts_sorted) if puts_sorted else 0
                        
                        # Always recalculate even if volumes are 0 (to ensure all fields are present)
                        call_premium = sum(c.get('premium_flow', 0) for c in calls_sorted) if calls_sorted else 0
                        put_premium = sum(p.get('premium_flow', 0) for p in puts_sorted) if puts_sorted else 0
                        net_vol = total_call_vol - total_put_vol
                        net_prem = call_premium - put_premium
                        cp_ratio = round(total_call_vol / total_put_vol, 2) if total_put_vol > 0 else (999.0 if total_call_vol > 0 else 1.0)
                        
                        clean_flow_metrics = {
                            'total_call_volume': total_call_vol,
                            'total_put_volume': total_put_vol,
                            'total_call_oi': sum(c.get('open_interest', 0) for c in calls_sorted) if calls_sorted else 0,
                            'total_put_oi': sum(p.get('open_interest', 0) for p in puts_sorted) if puts_sorted else 0,
                            'call_premium_flow': call_premium,
                            'put_premium_flow': put_premium,
                            'net_volume_flow': net_vol,
                            'net_premium_flow': net_prem,
                            'call_put_ratio': cp_ratio,
                            'put_call_ratio': round(1.0 / cp_ratio, 3) if cp_ratio and cp_ratio < 900 else (0.0 if cp_ratio >= 900 else 1.0),
                            'flow_direction': 'CALL_DOMINANT' if net_vol > 0 else ('PUT_DOMINANT' if net_vol < 0 else 'NEUTRAL')
                        }
                        if total_call_vol > 0 or total_put_vol > 0:
                            logger.info(f"✅ Recalculated flow metrics for {symbol}: Calls={total_call_vol:,}, Puts={total_put_vol:,}, Ratio={cp_ratio:.2f}")
                        else:
                            logger.debug(f"📊 Flow metrics recalculated for {symbol} (all zeros - likely market closed or no options data)")
                    
                    # Ensure flow_metrics always has all required fields (even if zeros)
                    if not clean_flow_metrics:
                        clean_flow_metrics = {
                            'total_call_volume': 0,
                            'total_put_volume': 0,
                            'total_call_oi': 0,
                            'total_put_oi': 0,
                            'call_premium_flow': 0,
                            'put_premium_flow': 0,
                            'net_volume_flow': 0,
                            'net_premium_flow': 0,
                            'call_put_ratio': 1.0,
                            'put_call_ratio': 1.0,
                            'flow_direction': 'NEUTRAL'
                        }
                    elif isinstance(clean_flow_metrics, dict):
                        # Fill premiums/OI when source (e.g. older Polygon path) omitted them
                        if (calls_sorted or puts_sorted) and not (
                            clean_flow_metrics.get('call_premium_flow') or clean_flow_metrics.get('put_premium_flow')
                        ):
                            clean_flow_metrics['call_premium_flow'] = sum(
                                float(c.get('premium_flow') or 0) for c in (calls_sorted or [])
                            )
                            clean_flow_metrics['put_premium_flow'] = sum(
                                float(p.get('premium_flow') or 0) for p in (puts_sorted or [])
                            )
                            clean_flow_metrics['net_premium_flow'] = (
                                clean_flow_metrics['call_premium_flow'] - clean_flow_metrics['put_premium_flow']
                            )
                        if 'total_call_oi' not in clean_flow_metrics and calls_sorted:
                            clean_flow_metrics['total_call_oi'] = sum(int(c.get('open_interest') or 0) for c in calls_sorted)
                        if 'total_put_oi' not in clean_flow_metrics and puts_sorted:
                            clean_flow_metrics['total_put_oi'] = sum(int(p.get('open_interest') or 0) for p in puts_sorted)
                        cp = clean_flow_metrics.get('call_put_ratio')
                        try:
                            cp_f = float(cp) if cp is not None else None
                        except (TypeError, ValueError):
                            cp_f = None
                        if cp_f and cp_f > 0:
                            clean_flow_metrics['put_call_ratio'] = round(1.0 / cp_f, 3)
                        elif clean_flow_metrics.get('total_call_volume') is not None:
                            cv = float(clean_flow_metrics.get('total_call_volume') or 0)
                            pv = float(clean_flow_metrics.get('total_put_volume') or 0)
                            clean_flow_metrics['call_put_ratio'] = round(cv / pv, 3) if pv > 0 else (999.0 if cv > 0 else 1.0)
                            clean_flow_metrics['put_call_ratio'] = round(pv / cv, 3) if cv > 0 else (999.0 if pv > 0 else 1.0)
                    
                    clean_momentum = convert_datetime_for_json(momentum)
                    clean_calls = convert_datetime_for_json(calls_sorted)
                    clean_puts = convert_datetime_for_json(puts_sorted)
                    clean_signal = convert_datetime_for_json(signal_analysis)
                    clean_flow_history = convert_datetime_for_json(flow_history_data)
                    if isinstance(clean_flow_history, list) and len(clean_flow_history) > 12:
                        clean_flow_history = clean_flow_history[-12:]  # trim wire payload
                    clean_unusual = convert_datetime_for_json(unusual_activity)
                    
                    # CRITICAL: Ensure all_calls and all_puts are extracted and logged
                    logger.info(f"[background_updater] Extracted options for {symbol}: {len(clean_calls)} calls, {len(clean_puts)} puts (from calls_sorted: {len(calls_sorted)}, puts_sorted: {len(puts_sorted)})")
                    
                    # timedelta is already imported at top level - use it directly
                    # Prefer official session close outside RTH (not last 1m bar)
                    stock_price_for_message = flow_data.get('stock_price', 0) if flow_data and isinstance(flow_data, dict) else 0
                    if flow_data and isinstance(flow_data, dict):
                        fd_close = float(flow_data.get('regular_close') or 0)
                        if fd_close > 0:
                            regular_close = fd_close
                        fd_ah = float(flow_data.get('aftermarket_price') or 0)
                        if fd_ah > 0 and aftermarket_price <= 0:
                            aftermarket_price = fd_ah
                        fd_pm = float(flow_data.get('premarket_price') or 0)
                        if fd_pm > 0 and premarket_price <= 0:
                            premarket_price = fd_pm
                    closed_sess = current_session in ('WEEKEND', 'OVERNIGHT') or bool(
                        flow_data and flow_data.get('snapshot_mode')
                    )
                    if closed_sess and regular_close > 0:
                        stock_price_for_message = regular_close
                    elif current_session == 'PRE_MARKET' and premarket_price > 0:
                        stock_price_for_message = premarket_price
                    elif stock_price_for_message == 0:
                        stock_price_for_message = regular_close if regular_close > 0 else (aftermarket_price if aftermarket_price > 0 else (premarket_price if premarket_price > 0 else 0))
                        if stock_price_for_message > 0:
                            logger.debug(f"✅ Set stock_price from regular_close for {symbol}: ${stock_price_for_message:.2f}")
                    
                    # CRITICAL FINAL SAFETY CHECK: Ensure stock_price is never 0 if we have valid flow_data
                    if stock_price_for_message == 0 and flow_data and isinstance(flow_data, dict):
                        flow_data_price = flow_data.get('stock_price', 0)
                        if flow_data_price > 0:
                            stock_price_for_message = flow_data_price
                            if regular_close <= 0:
                                regular_close = flow_data_price
                            logger.info(f"✅ Final safety check: stock_price was 0, using flow_data.stock_price: ${stock_price_for_message:.2f} for {symbol}")
                    
                    # CRITICAL: Ensure all price fields are initialized (never None/undefined)
                    # Default to 0 if not set, but ensure they're always included in the message
                    regular_close = regular_close if regular_close is not None else 0
                    aftermarket_price = aftermarket_price if aftermarket_price is not None else 0
                    aftermarket_change_pct = aftermarket_change_pct if aftermarket_change_pct is not None else 0
                    premarket_price = premarket_price if premarket_price is not None else 0
                    premarket_change_pct = premarket_change_pct if premarket_change_pct is not None else 0
                    prev_close = prev_close if prev_close is not None else 0
                    
                    # FINAL SAFETY CHECK: Ensure regular_close is never 0 when we have valid flow_data
                    # This prevents the price reset bug where regular_close gets set to 0 in error paths
                    if regular_close == 0 and flow_data and isinstance(flow_data, dict):
                        flow_data_price = flow_data.get('stock_price', 0)
                        if flow_data_price > 0:
                            regular_close = flow_data_price
                            logger.debug(f"✅ FINAL SAFETY: regular_close was 0, restored from flow_data.stock_price: ${regular_close:.2f} for {symbol}")
                        elif flow_data_stock_price > 0:
                            regular_close = flow_data_stock_price
                            logger.debug(f"✅ FINAL SAFETY: regular_close was 0, restored from flow_data_stock_price: ${regular_close:.2f} for {symbol}")
                    
                    # Get market data for display and context (cached, non-blocking)
                    market_data_for_message = {}
                    try:
                        # Get cached market data (scanned every 5 minutes)
                        if market_data_scanner is None:
                            raise RuntimeError("market_data_scanner unavailable")
                        market_data_for_message = market_data_scanner.scan_market_data(symbol)
                        # Only include key metrics for the message (full data already used in ML features)
                        market_data_for_message = {
                            'vix': market_data_for_message.get('vix_data', {}),
                            'breadth': market_data_for_message.get('breadth_data', {}),
                            'sector_rotation': market_data_for_message.get('sector_data', {}).get('rotation_signal', 'NEUTRAL'),
                            'composite_signals': market_data_for_message.get('composite_signals', {}),
                            'timestamp': market_data_for_message.get('timestamp', datetime.now().isoformat())
                        }
                    except Exception as e:
                        logger.debug(f"Error getting market data for message (non-critical): {e}")
                        market_data_for_message = {}

                    # Multi-tenor expiry mix (0DTE / few days / week / month) — cached ~2 min
                    # Longer tenors: Yahoo sample. 0DTE: overlay live MAIN chain when present.
                    expiry_terms_for_message = {}
                    if EXPIRY_TERM_SCANNER_AVAILABLE and expiry_term_scanner:
                        try:
                            loop = asyncio.get_event_loop()
                            expiry_terms_for_message = await loop.run_in_executor(
                                None, lambda: expiry_term_scanner.scan(symbol)
                            )
                            expiry_terms_for_message = convert_datetime_for_json(expiry_terms_for_message) if expiry_terms_for_message else {}
                            live_src = flow_data.get('data_source') or _last_known_data_source.get(symbol, '')
                            if expiry_terms_for_message and hasattr(expiry_term_scanner, 'overlay_live_0dte'):
                                expiry_terms_for_message = expiry_term_scanner.overlay_live_0dte(
                                    expiry_terms_for_message, flow_data, live_src
                                )
                        except Exception as e:
                            logger.debug(f"Expiry term scan skipped for {symbol}: {e}")
                            expiry_terms_for_message = {}

                    if isinstance(expiry_terms_for_message, dict) and expiry_terms_for_message.get('buckets'):
                        _last_expiry_terms[symbol] = expiry_terms_for_message
                    else:
                        expiry_terms_for_message = _last_expiry_terms.get(symbol) or {}

                    boss_for_msg = (signal_analysis.get('boss_decision') if isinstance(signal_analysis, dict) else {}) or {}
                    strength_payload = _compute_signal_strength(
                        boss_for_msg, clean_signal, clean_flow_metrics, clean_unusual
                    )
                    message = {
                        'type': 'flow_update',
                        'symbol': symbol,
                        'timestamp': datetime.now().isoformat(),
                        'data': {
                            'stock_price': stock_price_for_message,  # Use regular_close fallback if stock_price is 0
                            'prev_close': prev_close,  # Previous day's close
                            'regular_close': regular_close,  # Today's regular market close
                            'aftermarket_price': aftermarket_price,  # Aftermarket price
                            'aftermarket_change_pct': aftermarket_change_pct,  # Aftermarket % change
                            'premarket_price': premarket_price,  # Premarket price
                            'premarket_change_pct': premarket_change_pct,  # Premarket % change
                            'flow_metrics': clean_flow_metrics,
                            'momentum': clean_momentum,
                            'all_calls': clean_calls if isinstance(clean_calls, list) and len(clean_calls) > 0 else (flow_data.get('all_calls', []) if flow_data else []),  # All calls with volume > 0
                            'all_puts': clean_puts if isinstance(clean_puts, list) and len(clean_puts) > 0 else (flow_data.get('all_puts', []) if flow_data else []),     # All puts with volume > 0
                            # ALWAYS set expiration based on current market session (session takes priority over flow_data)
                            'expiration': (datetime.now().date().strftime('%Y-%m-%d') if current_session == 'REGULAR' else (datetime.now().date() + timedelta(days=1)).strftime('%Y-%m-%d')),
                            'expiration_label': (f"0DTE ({datetime.now().date().strftime('%Y-%m-%d')})" if current_session == 'REGULAR' else f"1DTE ({(datetime.now().date() + timedelta(days=1)).strftime('%Y-%m-%d')})"),
                            'dte': (0 if current_session == 'REGULAR' else 1),  # Add DTE number
                            # FIXED: Ensure data_source is never 'unknown' - use last known or flow_data source
                            'data_source': flow_data.get('data_source') or _last_known_data_source.get(symbol, 'yfinance'),
                            'data_delay_warning': flow_data.get('data_delay_warning', False),  # True if using delayed data source
                            'data_delay_minutes': flow_data.get('data_delay_minutes', 0),  # Delay in minutes (15-20 for yfinance)
                            'rotation_info': _get_comprehensive_rotation_info(flow_data.get('data_source') or _last_known_data_source.get(symbol, 'yfinance'), symbol),  # Enhanced rotation info with all APIs
                            'error': flow_data.get('error'),  # Pass error to client
                            'market_status': market_status,  # Add market status
                            'market_regime': flow_data.get('market_regime'),  # Add market regime detection
                            'signal': clean_signal,  # Add signal analysis
                            'data_freshness': data_freshness,  # NEW, RECENT, OLD, or CLOSED
                            'data_age_seconds': round(data_age_seconds, 1),  # Age in seconds
                            'snapshot_mode': bool(flow_data.get('snapshot_mode') or data_freshness == 'CLOSED'),
                            'order_flow_history': clean_flow_history,  # Add order flow history
                            'unusual_activity': clean_unusual,  # Add unusual activity detection
                            'market_data': market_data_for_message,  # Add comprehensive market data for context
                            **(
                                {'expiry_terms': expiry_terms_for_message}
                                if isinstance(expiry_terms_for_message, dict)
                                and expiry_terms_for_message.get('buckets')
                                else {}
                            ),
                            'signal_strength': strength_payload,
                            'session_structure': flow_data.get('session_structure') or {},
                            'boss_decision': boss_for_msg,
                            'paper_boss': (signal_analysis.get('paper_boss') if isinstance(signal_analysis, dict) else {}) or {},
                            'trade_lesson': _trade_lesson_payload(
                                boss_for_msg,
                                (signal_analysis.get('paper_boss') if isinstance(signal_analysis, dict) else {}) or {},
                            ),
                            'shadow_learning': (
                                (signal_analysis.get('shadow_learning') if isinstance(signal_analysis, dict) else None)
                                or ((signal_analysis.get('paper_boss') or {}).get('shadow_learning') if isinstance(signal_analysis, dict) else None)
                                or {}
                            ),
                        }
                    }
                    
                    # CRITICAL: Cache successful flow_data BEFORE broadcasting (for fallback when markets closed)
                    if flow_data and isinstance(flow_data, dict) and stock_price_for_message > 0:
                        _last_successful_flow_data[symbol] = flow_data.copy()
                        _last_successful_data_timestamp[symbol] = time.time()
                        logger.debug(f"💾 Cached flow_data for {symbol} (stock_price: ${stock_price_for_message:.2f})")
                    
                    # Broadcast to all clients subscribed to this symbol
                    client_count = len(manager.symbol_subscriptions.get(symbol, set()))
                    total_connections = len(manager.active_connections)
                    if client_count > 0:
                        logger.debug(f"📡 Broadcasting flow_update for {symbol} to {client_count} client(s) at {datetime.now().strftime('%H:%M:%S')}")
                        await manager.broadcast_to_symbol(message, symbol)
                        logger.debug(f"✅ Successfully broadcasted flow_update for {symbol}")
                    else:
                        # Log detailed info when no subscriptions (helps debug subscription issues)
                        all_subscriptions = {sym: len(conns) for sym, conns in manager.symbol_subscriptions.items()}
                        # IMPROVED: Better subscription tracking - check if symbol is in subscriptions dict
                        # Sometimes subscriptions exist but aren't being tracked correctly
                        has_subscriptions = symbol in manager.symbol_subscriptions and len(manager.symbol_subscriptions[symbol]) > 0
                        if not has_subscriptions:
                            logger.debug(f"⚠️ No clients subscribed to {symbol} - skipping broadcast (Total connections: {total_connections}, All subscriptions: {all_subscriptions})")
                        # Don't skip - still try to broadcast in case subscriptions aren't tracked correctly
                    
                except Exception as e:
                    logger.error(f"❌ Error updating {symbol}: {e}", exc_info=True)
                    # Even on error, try to send a minimal update to keep connection alive
                    try:
                        # Send error message to client so they know what's happening
                        error_message = {
                            'type': 'flow_update',
                            'symbol': symbol,
                            'timestamp': datetime.now().isoformat(),
                            'data': {
                                'error': f'Error fetching data: {str(e)[:100]}',
                                'stock_price': 0,
                                'market_status': market_status,
                                'signal': {
                                    'action': 'NO_TRADE',
                                    'confidence': 0,
                                    'reasoning': f'Data fetch error: {str(e)[:100]}'
                                }
                            }
                        }
                        client_count = len(manager.symbol_subscriptions.get(symbol, set()))
                        if client_count > 0:
                            logger.warning(f"⚠️ Sending error update for {symbol} to {client_count} client(s)")
                            await manager.broadcast_to_symbol(error_message, symbol)
                    except Exception as e2:
                        logger.error(f"❌ Failed to send error update: {e2}")
            except Exception as e:
                logger.error(f"❌ Error in background updater iteration: {e}", exc_info=True)
                await asyncio.sleep(0.5)  # ACCELERATED: Wait 0.5s before retry (reduced from 1.0s)
            
            # Wait before next update — session-aware (open-protect / pre-market save Yahoo)
            loop_end_time = time.time()
            time_spent = loop_end_time - loop_start_time
            sleep_time = _loop_sleep_seconds(current_session, update_interval, time_spent)
            if _is_open_protect_window(current_session):
                logger.debug(f"🛡️ Open-protect: sleep {sleep_time:.1f}s after {time_spent:.1f}s work")
            else:
                logger.debug(f"⏱️ {current_session} — processed in {time_spent:.2f}s, sleeping {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)
            
            # Track loop start time for next iteration
            loop_start_time = time.time()
            
            # Heartbeat log every 10 updates to confirm loop is running
            if hasattr(background_data_updater, '_loop_count'):
                background_data_updater._loop_count += 1
            else:
                background_data_updater._loop_count = 1
            
            if background_data_updater._loop_count % 10 == 0:
                logger.info(f"💓 Background updater heartbeat: Loop #{background_data_updater._loop_count}, {len(current_symbols)} symbol(s) subscribed, {len(manager.active_connections)} connection(s)")
            
            # CRITICAL: Ensure we always continue the loop - never exit!
            if background_data_updater._loop_count % 100 == 0:
                logger.info(f"✅ Background updater still running after {background_data_updater._loop_count} iterations - auto-refresh is ACTIVE")
        
    except asyncio.CancelledError:
        # FIXED: Handle graceful cancellation for shutdown
        logger.info("🛑 Background data updater cancelled - shutting down gracefully")
        raise
    except Exception as e:
        logger.error(f"❌ CRITICAL: Error in background updater loop: {e}", exc_info=True)
        logger.error(f"❌ Background updater failed - this should not happen")
        # This except is for the outer try block, which means the while loop itself failed
        # We can't continue here - the function will exit
        raise

# Telegram initialization moved to lifespan() function - no longer using deprecated @app.on_event

@app.websocket("/ws/{symbol}")
async def websocket_endpoint(websocket: WebSocket, symbol: str = "SPY"):
    """
    WebSocket endpoint with input validation
    """
    # CRITICAL: Initialize all variables at function scope to prevent UnboundLocalError
    # These must be initialized before any conditional logic or exception handling
    # Python treats variables assigned anywhere in function as local, so initialize early
    calls_sorted = []
    puts_sorted = []
    calls_by_strike = []
    puts_by_strike = []
    momentum = {}
    signal = None
    prev_close = 0
    regular_close = 0
    aftermarket_price = 0
    aftermarket_change_pct = 0
    premarket_price = 0
    premarket_change_pct = 0
    
    # Validate symbol input
    is_valid, validated_symbol = validate_symbol(symbol)
    if not is_valid:
        await websocket.close(code=1008, reason=f"Invalid symbol: {validated_symbol}")
        return
    
    # Use validated symbol
    symbol = validated_symbol
    """
    WebSocket endpoint for real-time flow data
    Supports multiple symbols per connection via subscribe_symbols message
    Updates pushed every 3 seconds
    """
    logger.info(f"[WebSocket] New connection attempt for symbol: {symbol}")
    logger.info(f"[WebSocket] Current state BEFORE connect - Active connections: {len(manager.active_connections)}, Subscriptions: {list(manager.symbol_subscriptions.keys())}")
    try:
        await manager.connect(websocket, symbol)
        logger.info(f"[WebSocket] ✅ Connection accepted for {symbol}. State AFTER connect - Active: {len(manager.active_connections)}, Subscriptions: {list(manager.symbol_subscriptions.keys())}")
    except Exception as e:
        logger.error(f"[WebSocket] ❌ Failed to accept connection: {e}", exc_info=True)
        raise
    
    try:
        # Send immediate connection confirmation to client (CRITICAL - must happen first)
        try:
            from market_hours_detector import get_market_status as _get_mkt_status
            _mkt = _get_mkt_status()
            _off = _desk_offline()
            if isinstance(_mkt, dict):
                _mkt = dict(_mkt)
                _mkt['offline'] = _off
            connection_msg = {
                'type': 'connected',
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'message': (
                    'WebSocket connected — OFFLINE (stale snapshot, not live prints)'
                    if _off else
                    'WebSocket connected, fetching data...'
                ),
                'market_status': _mkt,
                'offline': _off,
                'data_freshness': 'OFFLINE' if _off else None,
            }
            await manager.send_personal_message(connection_msg, websocket)
            logger.info(f"[WebSocket] ✅ Sent 'connected' message to client for {symbol}")
            logger.info(f"[WebSocket] Sent 'connected' message to client for {symbol}")
        except Exception as e:
            logger.error(f"[WebSocket] Failed to send 'connected' message: {e}")
            # Continue anyway - connection is established
        
        # CRITICAL: Auto-subscribe client to symbol immediately so it receives broadcasts
        if symbol not in manager.symbol_subscriptions:
            manager.symbol_subscriptions[symbol] = set()
        if websocket not in manager.symbol_subscriptions[symbol]:
            manager.symbol_subscriptions[symbol].add(websocket)
            logger.info(f"✅ AUTO-SUBSCRIBED: Client automatically subscribed to {symbol} on connection")
        
        # CRITICAL: Send minimal data immediately (before fetching full data) so client sees something right away
        logger.info(f"📡 Sending immediate minimal data for {symbol} to client...")
        try:
            # Get cached data if available (fast)
            if symbol in _last_successful_flow_data:
                cached = _last_successful_flow_data[symbol]
                if cached and isinstance(cached, dict) and cached.get('stock_price', 0) > 0:
                    logger.info(f"✅ Sending cached data immediately for {symbol} (stock_price: ${cached.get('stock_price', 0):.2f})")
                    asyncio.create_task(_send_immediate_symbol_data(websocket, symbol))
        except Exception as e:
            logger.debug(f"Could not send immediate cached data: {e}")
        
        # Get market status first (quick, non-blocking)
        market_status = get_market_status()
        
        # Send initial data immediately with timeout to prevent hanging
        loop = asyncio.get_event_loop()
        flow_data = None
        # Note: calls_sorted, puts_sorted, momentum, etc. already initialized at function scope above
        if _desk_offline():
            try:
                from offline_mode import serve_offline_flow

                flow_data = _last_successful_flow_data.get(symbol) or serve_offline_flow(symbol)
                if not flow_data or float((flow_data or {}).get('stock_price') or 0) <= 0:
                    flow_data = serve_offline_flow(symbol)
                logger.info(f"OFFLINE connect payload for {symbol} stock={ (flow_data or {}).get('stock_price') }")
            except Exception as e:
                logger.warning(f"OFFLINE connect payload failed: {e}")
                flow_data = None
        else:
            try:
                # Add timeout to prevent hanging
                flow_data = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        multi_source_tracker.get_0dte_options_chain,
                        symbol
                    ),
                    timeout=10.0  # 10 second timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"Data fetch timeout for {symbol} - using fallback")
                flow_data = None
            except Exception as e:
                logger.warning(f"Multi-source failed, trying single source: {e}")
                try:
                    flow_data = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            flow_tracker.get_0dte_options_chain,
                            symbol
                        ),
                        timeout=10.0  # 10 second timeout
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"Single source also timed out for {symbol}")
                    flow_data = None
                except Exception as e2:
                    logger.warning(f"Single source also failed: {e2}")
                    flow_data = None
        
        # Handle case when flow_data is None or empty
        # When markets are closed, try to get 1DTE options for next trading day
        if not flow_data or not isinstance(flow_data, dict):
            if market_status.get('session') in ['WEEKEND', 'OVERNIGHT', 'AFTER_HOURS', 'PRE_MARKET']:
                logger.info(f"Markets closed ({market_status.get('session')}) - fetching 1DTE options for initial connection for {symbol}")
                try:
                    loop = asyncio.get_event_loop()
                    # get_0dte_options_chain automatically handles 1DTE when markets are closed
                    flow_data = await loop.run_in_executor(
                        None,
                        multi_source_tracker.get_0dte_options_chain,
                        symbol
                    )
                    if flow_data and isinstance(flow_data, dict) and flow_data.get('stock_price', 0) > 0:
                        logger.info(f"✅ Got 1DTE options data for initial connection - {symbol}")
                    else:
                        logger.warning(f"1DTE options data fetch returned empty/invalid data for {symbol}")
                except Exception as e:
                    logger.warning(f"Could not get 1DTE options data for initial connection for {symbol}: {e}")
            
            # Create a message indicating no data available (if still no data)
            if not flow_data or not isinstance(flow_data, dict):
                error_message = "No options data available"
            if market_status.get('session') == 'OVERNIGHT':
                error_message = "Options trading closed (Overnight hours - options don't trade after-hours)"
            elif market_status.get('session') == 'WEEKEND':
                error_message = "Options trading closed (Weekend)"
            elif market_status.get('session') in ['PRE_MARKET', 'AFTER_HOURS']:
                error_message = "Options trading closed (Options only trade during regular market hours 9:30 AM - 4:00 PM ET)"
            
            # Fetch extended hours prices even when flow_data is None (with timeout)
            # CRITICAL: Initialize all price variables to 0 (never None/undefined)
            prev_close = 0
            regular_close = flow_data.get('stock_price', 0) if flow_data and isinstance(flow_data, dict) else 0
            aftermarket_price = 0
            aftermarket_change_pct = 0
            premarket_price = 0
            premarket_change_pct = 0
            try:
                if _desk_offline():
                    raise RuntimeError("offline — skip Yahoo history")
                # Add timeout to prevent hanging - use proper function calls
                ticker = yf.Ticker(symbol)
                
                def fetch_history():
                    return ticker.history(period="2d", interval="1d")
                
                def fetch_info():
                    return ticker.info
                
                hist = await asyncio.wait_for(
                    loop.run_in_executor(None, fetch_history),
                    timeout=5.0
                )
                if not hist.empty and len(hist) >= 1:
                    regular_close = float(hist['Close'].iloc[-1])
                if not hist.empty and len(hist) >= 2:
                    prev_close = float(hist['Close'].iloc[-2])
                
                info = await asyncio.wait_for(
                    loop.run_in_executor(None, fetch_info),
                    timeout=5.0
                )
                if info:
                    # Get aftermarket - use postMarketChangePercent if postMarketPrice is missing
                    post_market = info.get('postMarketPrice')
                    post_change_pct = info.get('postMarketChangePercent')
                    if (post_market is None or post_market == 0) and post_change_pct is not None and regular_close > 0:
                        post_market = regular_close * (1 + post_change_pct / 100)
                        aftermarket_price = float(post_market)
                        aftermarket_change_pct = float(post_change_pct)
                    elif post_market is not None and post_market != 0:
                        aftermarket_price = float(post_market)
                        if regular_close > 0:
                            aftermarket_change_pct = ((aftermarket_price - regular_close) / regular_close) * 100
                        elif post_change_pct is not None:
                            aftermarket_change_pct = float(post_change_pct)
                    
                    # Get premarket
                    pre_market = info.get('preMarketPrice')
                    if pre_market is not None and pre_market != 0:
                        premarket_price = float(pre_market)
                        if regular_close > 0:
                            premarket_change_pct = ((premarket_price - regular_close) / regular_close) * 100
            except asyncio.TimeoutError:
                logger.warning(f"Extended hours fetch timeout for {symbol}")
            except Exception as e:
                logger.debug(f"Could not get extended hours for initial error message: {e}")
            
            initial_message = {
                'type': 'flow_update',
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'data': {
                    'stock_price': regular_close,  # Use regular_close instead of 0
                    'prev_close': prev_close,
                    'regular_close': regular_close,
                    'aftermarket_price': aftermarket_price,
                    'aftermarket_change_pct': aftermarket_change_pct,
                    'premarket_price': premarket_price,
                    'premarket_change_pct': premarket_change_pct,
                    'flow_metrics': {
                        'total_call_volume': 0,
                        'total_put_volume': 0,
                        'call_put_ratio': 1.0,
                        'net_volume_flow': 0
                    },
                    'momentum': {},
                    'all_calls': [],
                    'all_puts': [],
                    'expiration': 'N/A',
                    'expiration_label': 'N/A',
                    'dte': 0,
                    'data_source': _last_known_data_source.get(symbol, 'unknown'),  # Use last known instead of 'none'
                    'rotation_info': _get_comprehensive_rotation_info(_last_known_data_source.get(symbol, 'unknown')),
                    'error': error_message,
                    'market_status': market_status,
                    'signal': {
                        'action': 'NO_TRADE',
                        'confidence': 0,
                        'reasoning': error_message,
                        'signal_type': 'WAIT'
                    },
                    'data_freshness': 'OLD',
                    'data_age_seconds': 999999,
                    'order_flow_history': [],
                    'unusual_activity': None
                }
            }
            logger.info(f"Initial message (no flow_data) - Extended hours: aftermarket={aftermarket_price}, premarket={premarket_price}, regular_close={regular_close}")
            logger.info(f"[WebSocket] ⚠️ NO FLOW_DATA - Sending minimal initial message with stock_price={regular_close} for {symbol}")
            try:
                await manager.send_personal_message(initial_message, websocket)
                logger.info(f"[WebSocket] ✅ SUCCESS: Sent initial message (no flow_data) to client for {symbol}. Message size: {len(str(initial_message))} chars")
            except Exception as e:
                logger.error(f"[WebSocket] ❌ FAILED: Failed to send initial message (no flow_data): {e}", exc_info=True)
                raise  # Re-raise to see the error
        else:
            # Get momentum (with timeout to prevent hanging)
            # Note: momentum already initialized at function scope above
            try:
                momentum = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        multi_source_tracker.get_flow_momentum,
                        symbol
                    ),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"Momentum fetch timeout for {symbol}")
            except Exception as e:
                # Fallback to flow_tracker if multi_source_tracker fails
                logger.debug(f"Failed to get momentum from multi_source_tracker for {symbol}: {e}")
                try:
                    momentum = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            flow_tracker.get_flow_momentum,
                            symbol
                        ),
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"Momentum fallback timeout for {symbol}")
                except Exception as e2:
                    # Final fallback: empty momentum dict
                    logger.debug(f"Failed to get momentum from flow_tracker for {symbol}: {e2}")
                    momentum = {}
            
            # Get all strikes, sorted by volume
            # Try multiple paths to get options data (backward compatibility)
            # CRITICAL: Ensure calls_by_strike and puts_by_strike are always set (they're initialized at top, but reassign here)
            strikes = flow_data.get('strikes', {})
            
            # Try multiple extraction paths in order of preference:
            # 1. strikes['calls_by_strike'] / strikes['puts_by_strike'] (standard format)
            # 2. calls['by_strike'] / puts['by_strike'] (alternative format)
            # 3. all_calls / all_puts (direct format)
            # CRITICAL: Extract options data using helper function
            calls_by_strike, puts_by_strike = extract_options_data(flow_data, symbol)
            
            # CRITICAL: If no options data in current flow_data, try cached data
            if (not calls_by_strike or not puts_by_strike) and symbol in _last_successful_flow_data:
                cached_data = _last_successful_flow_data[symbol]
                if cached_data and isinstance(cached_data, dict):
                    # Try multiple paths to get cached options data
                    cached_calls = None
                    cached_puts = None
                    
                    # Try 1: Direct all_calls/all_puts
                    if cached_data.get('all_calls') or cached_data.get('all_puts'):
                        cached_calls = cached_data.get('all_calls', [])
                        cached_puts = cached_data.get('all_puts', [])
                        logger.info(f"📦 Found cached all_calls/all_puts for {symbol}")
                    
                    # Try 2: strikes dict
                    if (not cached_calls or not cached_puts):
                        cached_strikes = cached_data.get('strikes', {})
                        if isinstance(cached_strikes, dict):
                            if not cached_calls:
                                cached_calls = cached_strikes.get('calls_by_strike', [])
                            if not cached_puts:
                                cached_puts = cached_strikes.get('puts_by_strike', [])
                    
                    # Try 3: calls/puts structure
                    if (not cached_calls or not cached_puts):
                        cached_calls_dict = cached_data.get('calls', {})
                        cached_puts_dict = cached_data.get('puts', {})
                        if isinstance(cached_calls_dict, dict) and not cached_calls:
                            cached_calls = cached_calls_dict.get('by_strike', [])
                        if isinstance(cached_puts_dict, dict) and not cached_puts:
                            cached_puts = cached_puts_dict.get('by_strike', [])
                    
                    # Use cached options if current flow_data has none
                    if not calls_by_strike and cached_calls:
                        logger.info(f"📦 Using cached calls data for {symbol} ({len(cached_calls)} calls)")
                        calls_by_strike = cached_calls
                    if not puts_by_strike and cached_puts:
                        logger.info(f"📦 Using cached puts data for {symbol} ({len(cached_puts)} puts)")
                        puts_by_strike = cached_puts
            
            # CRITICAL: Ensure calls_by_strike and puts_by_strike are lists (defensive check)
            if not isinstance(calls_by_strike, list):
                calls_by_strike = []
            if not isinstance(puts_by_strike, list):
                puts_by_strike = []
            
            # Log for debugging
            if not calls_by_strike and not puts_by_strike:
                logger.warning(f"⚠️ No options data found for {symbol} - flow_data has_strikes: {bool(strikes)}, has_calls: {bool(flow_data.get('calls'))}, has_puts: {bool(flow_data.get('puts'))}, cached_available: {symbol in _last_successful_flow_data}")
            
            # Sort by volume, but include ALL options (not just those with volume)
            # Filter will happen later if needed
            # CRITICAL: Always set calls_sorted and puts_sorted (they're initialized at top, but ensure they're set here)
            try:
                calls_sorted = sorted(calls_by_strike, key=lambda x: x.get('volume', 0), reverse=True)[:50] if calls_by_strike else []
                puts_sorted = sorted(puts_by_strike, key=lambda x: x.get('volume', 0), reverse=True)[:50] if puts_by_strike else []
            except Exception as e:
                logger.warning(f"Error sorting options for {symbol}: {e}")
                calls_sorted = []
                puts_sorted = []
            
            # CRITICAL: Defensive check - ensure calls_sorted and puts_sorted are always lists
            if not isinstance(calls_sorted, list):
                calls_sorted = []
            if not isinstance(puts_sorted, list):
                puts_sorted = []
            
            # Fetch extended hours prices for initial message (with timeout)
            prev_close = 0
            regular_close = flow_data.get('stock_price', 0) if flow_data and isinstance(flow_data, dict) else 0
            aftermarket_price = 0
            aftermarket_change_pct = 0
            premarket_price = 0
            premarket_change_pct = 0
            try:
                if _desk_offline():
                    raise RuntimeError("offline — skip Yahoo history")
                # Add timeout to prevent hanging - use proper function calls
                ticker = yf.Ticker(symbol)
                
                def fetch_history():
                    return ticker.history(period="2d", interval="1d")
                
                def fetch_info():
                    return ticker.info
                
                hist = await asyncio.wait_for(
                    loop.run_in_executor(None, fetch_history),
                    timeout=5.0
                )
                if not hist.empty and len(hist) >= 1:
                    regular_close = float(hist['Close'].iloc[-1])
                if not hist.empty and len(hist) >= 2:
                    prev_close = float(hist['Close'].iloc[-2])
                
                info = await asyncio.wait_for(
                    loop.run_in_executor(None, fetch_info),
                    timeout=5.0
                )
                if info:
                    # Get aftermarket - use postMarketChangePercent if postMarketPrice is missing
                    post_market = info.get('postMarketPrice')
                    post_change_pct = info.get('postMarketChangePercent')
                    if (post_market is None or post_market == 0) and post_change_pct is not None and regular_close > 0:
                        post_market = regular_close * (1 + post_change_pct / 100)
                        aftermarket_price = float(post_market)
                        aftermarket_change_pct = float(post_change_pct)
                    elif post_market is not None and post_market != 0:
                        aftermarket_price = float(post_market)
                        if regular_close > 0:
                            aftermarket_change_pct = ((aftermarket_price - regular_close) / regular_close) * 100
                        elif post_change_pct is not None:
                            aftermarket_change_pct = float(post_change_pct)
                    
                    # Get premarket
                    pre_market = info.get('preMarketPrice')
                    if pre_market is not None and pre_market != 0:
                        premarket_price = float(pre_market)
                        if regular_close > 0:
                            premarket_change_pct = ((premarket_price - regular_close) / regular_close) * 100
            except asyncio.TimeoutError:
                logger.warning(f"Extended hours fetch timeout for {symbol} - continuing without extended hours data")
            except Exception as e:
                logger.debug(f"Could not get extended hours for initial message: {e}")
            
            # CRITICAL SAFETY CHECK: Ensure regular_close is never 0 if we have valid flow_data stock_price
            if regular_close == 0 and flow_data and isinstance(flow_data, dict):
                flow_data_price = flow_data.get('stock_price', 0)
                if flow_data_price > 0:
                    regular_close = flow_data_price
                    logger.info(f"✅ Safety check: regular_close was 0, using flow_data.stock_price: ${regular_close:.2f} for {symbol}")
            
            # Generate signal for the flow data (with timeout to prevent blocking)
            signal = {
                'action': 'NO_TRADE',
                'confidence': 0,
                'reasoning': 'OFFLINE — sitting out on stale snapshot' if _desk_offline() else 'Signal analysis in progress...',
                'signal_type': 'WAIT'
            }
            if not _desk_offline() and not _flow_is_stale(flow_data if isinstance(flow_data, dict) else None):
                try:
                    # Add timeout to prevent signal analysis from blocking
                    flow_history_data = []
                    try:
                        if hasattr(multi_source_tracker, 'flow_history') and symbol in multi_source_tracker.flow_history:
                            flow_history_data = multi_source_tracker.flow_history[symbol][-10:]
                    except (AttributeError, KeyError, TypeError) as e:
                        logger.debug(f"Could not access flow history for {symbol}: {e}")
                    signal = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            signal_analyzer.analyze_flow_signal,
                            flow_data,
                            flow_history_data
                        ),
                        timeout=3.0
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"Signal analysis timeout for {symbol} - using default signal")
                    signal = {
                        'action': 'NO_TRADE',
                        'confidence': 0,
                        'reasoning': 'Signal analysis timeout - data still loading',
                        'signal_type': 'WAIT'
                    }
                except Exception as e:
                    logger.warning(f"Signal analysis failed: {e}")
                    signal = {
                        'action': 'NO_TRADE',
                        'confidence': 0,
                        'reasoning': 'Signal analysis unavailable',
                        'signal_type': 'WAIT'
                    }
            
            # CRITICAL: Ensure all price fields are initialized (never None/undefined)
            regular_close = regular_close if regular_close is not None else 0
            aftermarket_price = aftermarket_price if aftermarket_price is not None else 0
            aftermarket_change_pct = aftermarket_change_pct if aftermarket_change_pct is not None else 0
            premarket_price = premarket_price if premarket_price is not None else 0
            premarket_change_pct = premarket_change_pct if premarket_change_pct is not None else 0
            prev_close = prev_close if prev_close is not None else 0
            
            # CRITICAL FIX: Ensure calls_sorted and puts_sorted are always lists before use
            # Use try-except to handle any UnboundLocalError (Python scoping issue)
            try:
                # Verify variables exist and are lists
                if not isinstance(calls_sorted, list):
                    calls_sorted = []
                if not isinstance(puts_sorted, list):
                    puts_sorted = []
            except (UnboundLocalError, NameError):
                # Variables not set - initialize them
                calls_sorted = []
                puts_sorted = []
            
            # CRITICAL: If calls_sorted/puts_sorted are empty, try to get from flow_data directly
            if (not calls_sorted or not puts_sorted) and flow_data:
                # Try direct access from flow_data
                if not calls_sorted:
                    calls_sorted = flow_data.get('all_calls', []) or flow_data.get('calls', {}).get('by_strike', []) or []
                if not puts_sorted:
                    puts_sorted = flow_data.get('all_puts', []) or flow_data.get('puts', {}).get('by_strike', []) or []
                
                # If still empty, try strikes structure
                if (not calls_sorted or not puts_sorted):
                    strikes = flow_data.get('strikes', {})
                    if isinstance(strikes, dict):
                        if not calls_sorted:
                            calls_sorted = strikes.get('calls_by_strike', []) or []
                        if not puts_sorted:
                            puts_sorted = strikes.get('puts_by_strike', []) or []
                
                if calls_sorted or puts_sorted:
                    logger.info(f"✅ Recovered options data from flow_data: {len(calls_sorted)} calls, {len(puts_sorted)} puts")
            
            # FINAL FALLBACK: If still empty, try cached data one more time
            if (not calls_sorted or not puts_sorted) and symbol in _last_successful_flow_data:
                cached_data = _last_successful_flow_data[symbol]
                if cached_data:
                    # Try all possible paths in cached data
                    if not calls_sorted:
                        calls_sorted = cached_data.get('all_calls', []) or cached_data.get('calls', {}).get('by_strike', []) or cached_data.get('strikes', {}).get('calls_by_strike', []) or []
                    if not puts_sorted:
                        puts_sorted = cached_data.get('all_puts', []) or cached_data.get('puts', {}).get('by_strike', []) or cached_data.get('strikes', {}).get('puts_by_strike', []) or []
                    if calls_sorted or puts_sorted:
                        logger.info(f"✅ FINAL FALLBACK: Using cached options data: {len(calls_sorted)} calls, {len(puts_sorted)} puts")
            
            # Log final state
            logger.info(f"[WebSocket] Final options data for {symbol}: calls={len(calls_sorted)}, puts={len(puts_sorted)}")
            
            initial_message = {
                'type': 'flow_update',
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'data': {
                    'stock_price': flow_data.get('stock_price', 0) if flow_data.get('stock_price', 0) > 0 else (regular_close if regular_close > 0 else 0),
                    'prev_close': prev_close,
                    'regular_close': regular_close,
                    'aftermarket_price': aftermarket_price,
                    'aftermarket_change_pct': aftermarket_change_pct,
                    'premarket_price': premarket_price,
                    'premarket_change_pct': premarket_change_pct,
                    'flow_metrics': flow_data.get('flow_metrics', {}),
                    'momentum': momentum,
                    'all_calls': calls_sorted,
                    'all_puts': puts_sorted,
                    'expiration': flow_data.get('expiration', 'N/A'),
                    'expiration_label': flow_data.get('expiration_label', 'N/A'),
                    'dte': flow_data.get('dte', 0),
                    # FIXED: Ensure data_source is never 'unknown' - use last known or flow_data source
                    'data_source': flow_data.get('data_source') or _last_known_data_source.get(symbol, 'yfinance'),
                    'rotation_info': _get_comprehensive_rotation_info(flow_data.get('data_source') or _last_known_data_source.get(symbol, 'yfinance'), symbol),
                    'error': flow_data.get('error'),  # Pass error to client
                    'market_status': market_status,  # Add market status
                    'signal': signal or {
                        'action': 'NO_TRADE',
                        'confidence': 0,
                        'reasoning': 'Signal analysis unavailable',
                        'signal_type': 'WAIT'
                    }
                }
            }
            if _desk_offline() or _flow_is_stale(flow_data if isinstance(flow_data, dict) else None):
                data = initial_message['data']
                data['offline'] = True
                data['stale'] = True
                data['live'] = False
                data['snapshot_mode'] = True
                data['data_freshness'] = 'OFFLINE'
                data['data_quality'] = 'offline_stale'
                data['data_source'] = 'offline_snapshot'
                last_boss = None
                if isinstance(flow_data, dict) and isinstance(flow_data.get('boss_decision'), dict):
                    last_boss = flow_data.get('boss_decision')
                data['boss_decision'] = _sit_out_boss_paint(flow_data if isinstance(flow_data, dict) else None, last_boss)
                data['paper_boss'] = {'armed': False, 'offline': True, 'can_auto_paper': False}
                initial_message['offline'] = True
                initial_message['data_freshness'] = 'OFFLINE'
            logger.info(f"Initial message (with flow_data) - Extended hours: aftermarket={aftermarket_price}, premarket={premarket_price}, regular_close={regular_close}")
            logger.info(f"[WebSocket] ✅ HAS FLOW_DATA - Sending initial message with stock_price={flow_data.get('stock_price', 0)}, calls={len(calls_sorted)}, puts={len(puts_sorted)} for {symbol}")
            try:
                await manager.send_personal_message(initial_message, websocket)
                logger.info(f"[WebSocket] ✅ SUCCESS: Sent initial message (with flow_data) to client for {symbol}. Message size: {len(str(initial_message))} chars, calls={len(calls_sorted)}, puts={len(puts_sorted)}")
            except Exception as e:
                logger.error(f"[WebSocket] ❌ FAILED: Failed to send initial message (with flow_data): {e}", exc_info=True)
                raise  # Re-raise to see the error
        
        # CRITICAL: Process any pending messages immediately (client might have sent subscribe_symbols already)
        # Use receive with short timeout to check for immediate messages without blocking
        try:
            data = await asyncio.wait_for(websocket.receive_text(), timeout=0.5)
            message = json.loads(data)
            if message.get('type') == 'subscribe_symbols':
                symbols = message.get('symbols', [])
                logger.info(f"📨 Received immediate subscribe_symbols: {symbols}")
                for sym in symbols:
                    if sym not in manager.symbol_subscriptions:
                        manager.symbol_subscriptions[sym] = set()
                        logger.info(f"Created subscription set for {sym}")
                    if websocket not in manager.symbol_subscriptions[sym]:
                        manager.symbol_subscriptions[sym].add(websocket)
                        logger.info(f"Added websocket to {sym} subscription")
                all_subs = {sym: len(conns) for sym, conns in manager.symbol_subscriptions.items()}
                logger.info(f"✅ IMMEDIATE: Client subscribed to {symbols} on connect. All subscriptions: {all_subs}, Active connections: {len(manager.active_connections)}")
                
                # Send immediate data for subscribed symbols
                for sym in symbols:
                    try:
                        asyncio.create_task(_send_immediate_symbol_data(websocket, sym))
                    except Exception as e:
                        logger.warning(f"Could not send immediate data for {sym}: {e}")
        except asyncio.TimeoutError:
            # No immediate message - continue to main loop (this is normal)
            logger.debug(f"No immediate message from client - will wait in main loop")
        except Exception as e:
            logger.debug(f"No immediate message or error: {e}")
        
        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for client message (or timeout)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=20.0)
                
                # Handle client messages (e.g., symbol change)
                try:
                    message = json.loads(data)
                    if message.get('type') in ('pong', 'heartbeat', 'ping'):
                        # Keepalive from client — ack lightly so UI lastPing stays warm
                        if message.get('type') == 'ping':
                            try:
                                await manager.send_personal_message({'type': 'pong'}, websocket)
                            except Exception:
                                pass
                        continue
                    if message.get('type') == 'change_symbol':
                        # Support multiple symbol subscriptions per connection
                        new_symbol = message.get('symbol', 'SPY')
                        if new_symbol not in manager.symbol_subscriptions:
                            manager.symbol_subscriptions[new_symbol] = set()
                        # Add to new symbol (don't remove from old - allow multiple subscriptions)
                        manager.symbol_subscriptions[new_symbol].add(websocket)
                        # Update primary symbol for this connection
                        symbol = new_symbol
                        
                        logger.info(f"Client subscribed to {new_symbol} (can have multiple subscriptions)")
                    
                    elif message.get('type') == 'set_preferred_source':
                        # Handle manual data source selection from client
                        preferred_source = message.get('source', '').strip()
                        symbol = message.get('symbol', symbol)
                        
                        if preferred_source:
                            # Store preferred source per symbol (in memory, per connection)
                            if not hasattr(manager, 'preferred_sources'):
                                manager.preferred_sources = {}  # websocket -> {symbol -> source}
                            
                            if websocket not in manager.preferred_sources:
                                manager.preferred_sources[websocket] = {}
                            
                            manager.preferred_sources[websocket][symbol] = preferred_source
                            logger.info(f"✅ Client set preferred data source for {symbol}: {preferred_source}")
                            
                            # Send confirmation
                            try:
                                await manager.send_personal_message({
                                    'type': 'source_preference_set',
                                    'symbol': symbol,
                                    'source': preferred_source,
                                    'message': f'Data source set to {preferred_source}'
                                }, websocket)
                            except Exception as e:
                                logger.debug(f"Could not send source preference confirmation: {e}")
                    
                    elif message.get('type') == 'subscribe_symbols':
                        # Subscribe to multiple symbols at once (prevent duplicate subscriptions)
                        symbols = message.get('symbols', [])
                        new_symbols = []
                        for sym in symbols:
                            if sym not in manager.symbol_subscriptions:
                                manager.symbol_subscriptions[sym] = set()
                            # Only add if not already subscribed (set prevents duplicates, but log only new ones)
                            if websocket not in manager.symbol_subscriptions[sym]:
                                manager.symbol_subscriptions[sym].add(websocket)
                                new_symbols.append(sym)
                        
                        # Log subscription status
                        total_subscriptions = {sym: len(manager.symbol_subscriptions.get(sym, set())) for sym in symbols}
                        if new_symbols:
                            logger.info(f"✅ Client subscribed to new symbols: {new_symbols} (total subscriptions: {symbols}, counts: {total_subscriptions})")
                        else:
                            logger.info(f"✅ Client already subscribed to all symbols: {symbols} (counts: {total_subscriptions})")
                        
                        # CRITICAL: Log all current subscriptions for debugging
                        all_subscriptions = {sym: len(conns) for sym, conns in manager.symbol_subscriptions.items()}
                        logger.info(f"📊 Total subscriptions across all symbols: {all_subscriptions}")
                        
                        # Send immediate data for all subscribed symbols (only once per subscription)
                        loop = asyncio.get_event_loop()
                        for sym in symbols:
                            try:
                                # Trigger immediate data fetch for this symbol
                                asyncio.create_task(_send_immediate_symbol_data(websocket, sym))
                            except Exception as e:
                                logger.warning(f"Could not send immediate data for {sym}: {e}")
                except json.JSONDecodeError:
                    pass
                    
            except asyncio.TimeoutError:
                # Send ping to keep connection alive and verify it's still connected
                try:
                    await manager.send_personal_message({'type': 'ping'}, websocket)
                    logger.debug(f"Sent ping to keep connection alive for {symbol}")
                except Exception as e:
                    logger.warning(f"Failed to send ping - connection may be dead: {e}")
                    # CRITICAL FIX: Check if websocket is still in active connections before breaking
                    if websocket not in manager.active_connections:
                        logger.info(f"WebSocket removed from active connections - exiting loop")
                        break
                    # Try to continue - connection might recover
                    continue
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"Client disconnected from {symbol}. Remaining connections: {len(manager.active_connections)}")
    except asyncio.CancelledError:
        # Task was cancelled - this is normal during shutdown
        logger.info(f"WebSocket task cancelled for {symbol}")
        manager.disconnect(websocket)
    except RuntimeError as e:
        # Starlette TestClient / client already gone
        if "disconnect" in str(e).lower() or "receive" in str(e).lower():
            manager.disconnect(websocket)
            logger.info(f"Client gone for {symbol}. Remaining connections: {len(manager.active_connections)}")
        else:
            logger.error(f"WebSocket error for {symbol}: {e}", exc_info=True)
            try:
                if websocket in manager.active_connections:
                    manager.disconnect(websocket)
            except Exception:
                pass
    except Exception as e:
        logger.error(f"WebSocket error for {symbol}: {e}", exc_info=True)
        # CRITICAL FIX: Only disconnect if websocket is still in connections
        try:
            if websocket in manager.active_connections:
                manager.disconnect(websocket)
                logger.info(f"Disconnected client after error. Remaining connections: {len(manager.active_connections)}")
        except Exception as disconnect_error:
            logger.warning(f"Error during disconnect cleanup: {disconnect_error}")

@app.get("/")
async def get_index():
    """Serve the HTML client; reload from disk when the file changes."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    content = None
    used_name = None
    for filename in ["zerodte_client_enhanced.html", "zerodte_client.html"]:
        filepath = os.path.join(script_dir, filename)
        if not os.path.isfile(filepath):
            continue
        try:
            mtime = os.path.getmtime(filepath)
            cached = getattr(get_index, '_cached_content', None)
            cached_mtime = getattr(get_index, '_cached_mtime', None)
            cached_name = getattr(get_index, '_cached_name', None)
            if cached is not None and cached_mtime == mtime and cached_name == filename:
                content = cached
                used_name = filename
                break
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            get_index._cached_content = content
            get_index._cached_mtime = mtime
            get_index._cached_name = filename
            used_name = filename
            logger.info(f"✅ Loaded HTML {filename} ({len(content)} bytes, mtime={mtime})")
            break
        except Exception as e:
            logger.warning(f"Failed reading {filename}: {e}")
            continue

    if content is None:
        content = "<h1>Error: Client HTML file not found</h1>"

    return HTMLResponse(
        content=content,
        headers={
            # Avoid stale tour/UI after edits (was caching 1 hour + forever in process memory)
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Content-Type": "text/html; charset=utf-8",
            "X-Content-Type-Options": "nosniff",
            "X-HTML-File": used_name or "missing",
        }
    )

@app.get("/squeeze")
async def get_squeeze_desk():
    """Same live UI, opens the Big Run (squeeze) desk."""
    return RedirectResponse(url="/?desk=squeeze", status_code=302)

@app.get("/calm-preview")
async def get_calm_preview():
    """Static calm Stage A UI mock (Boss + battle + strike charts)."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, "boss_calm_preview.html")
    if not os.path.isfile(filepath):
        return HTMLResponse("<h1>boss_calm_preview.html not found</h1>", status_code=404)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(
        content=content,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Content-Type": "text/html; charset=utf-8",
        },
    )

@app.get("/hybrid-preview")
async def get_hybrid_preview():
    """Static hybrid UI mock — calm chrome + battle/strikes + light lab extras."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, "boss_hybrid_preview.html")
    if not os.path.isfile(filepath):
        return HTMLResponse("<h1>boss_hybrid_preview.html not found</h1>", status_code=404)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(
        content=content,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Content-Type": "text/html; charset=utf-8",
        },
    )

@app.get("/lab-preview")
async def get_lab_upgrade_preview():
    """Static Lab densify mock — ticker + Boss spine + collapsed legacy (live / unchanged)."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, "boss_lab_upgrade_preview.html")
    if not os.path.isfile(filepath):
        return HTMLResponse("<h1>boss_lab_upgrade_preview.html not found</h1>", status_code=404)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(
        content=content,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Content-Type": "text/html; charset=utf-8",
        },
    )

@app.get("/api/yahoo-throttle")
async def get_yahoo_throttle_stats():
    """Stage A Yahoo gate stats (cooldown / backoff / cache hits)."""
    try:
        from yahoo_throttle import yahoo_throttle
        return JSONResponse(yahoo_throttle.stats())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def chrome_devtools_config():
    """Handle Chrome DevTools config request to prevent 404 logs"""
    return JSONResponse(status_code=404, content={})  # Return empty 404 without logging

@app.get("/robots.txt")
async def get_robots():
    """Serve robots.txt to prevent 404 errors"""
    robots_content = """User-agent: *
Disallow: /api/
Disallow: /docs
Disallow: /health
Allow: /
"""
    return Response(
        content=robots_content,
        headers={
            "Cache-Control": "public, max-age=86400",
            "Content-Type": "text/plain"
        }
    )

@app.get("/manifest.json")
async def get_manifest():
    """Serve PWA manifest with proper error handling"""
    try:
        # CRITICAL: Use absolute path to ensure file is found
        script_dir = os.path.dirname(os.path.abspath(__file__))
        manifest_path = os.path.join(script_dir, "manifest.json")
        
        if not os.path.exists(manifest_path):
            logger.warning(f"⚠️ manifest.json not found at {manifest_path}")
            return JSONResponse(
                content={"error": "Manifest not found"},
                status_code=404
            )
        
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
            return JSONResponse(
                content=manifest_data,
                headers={
                    "Cache-Control": "public, max-age=86400",  # 1 day cache
                    "Content-Type": "application/manifest+json"
                }
            )
    except FileNotFoundError:
        logger.error(f"❌ manifest.json file not found")
        return JSONResponse(
            content={"error": "Manifest not found"},
            status_code=404
        )
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error parsing manifest.json: {e}")
        return JSONResponse(
            content={"error": "Invalid manifest format"},
            status_code=500
        )
    except Exception as e:
        logger.error(f"❌ Error serving manifest.json: {e}", exc_info=True)
        return JSONResponse(
            content={"error": f"Server error: {str(e)}"},
            status_code=500
        )

@app.get("/service-worker.js")
async def get_service_worker():
    """Serve service worker"""
    try:
        with open("service-worker.js", "r", encoding="utf-8") as f:
            return Response(
                content=f.read(),
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",  # Always fetch fresh
                    "Content-Type": "application/javascript"
                }
            )
    except FileNotFoundError:
        return Response(
            content="// Service worker not found",
            status_code=404,
            media_type="application/javascript"
        )

@app.get("/offline-data-manager.js")
async def get_offline_manager():
    """Serve offline data manager JavaScript"""
    try:
        with open("offline-data-manager.js", "r", encoding="utf-8") as f:
            return Response(
                content=f.read(),
                headers={
                    "Cache-Control": "public, max-age=86400",  # 1 day cache
                    "Content-Type": "application/javascript"
                }
            )
    except FileNotFoundError:
        return Response(
            content="// Offline data manager not found",
            status_code=404,
            media_type="application/javascript"
        )

@app.get("/favicon.ico")
async def get_favicon():
    """Serve favicon to prevent 404 errors"""
    # Generate a simple SVG favicon
    svg_icon = '''<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">
        <rect width="32" height="32" fill="#3b82f6" rx="6"/>
        <text x="50%" y="50%" font-family="Arial, sans-serif" font-size="20" fill="white" text-anchor="middle" dominant-baseline="middle" font-weight="bold">FS</text>
    </svg>'''
    
    return Response(
        content=svg_icon,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "Content-Type": "image/svg+xml"
        }
    )

@app.get("/icon-{size}.png")
async def get_icon(size: str):
    """Serve PWA icons (placeholder - returns SVG if icons don't exist)"""
    if size not in ["192", "512"]:
        return Response(status_code=404)
    
    # Generate a simple SVG icon as placeholder
    svg_icon = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">
        <rect width="{size}" height="{size}" fill="#3b82f6" rx="20"/>
        <text x="50%" y="50%" font-family="Arial, sans-serif" font-size="{int(int(size)*0.3)}" fill="white" text-anchor="middle" dominant-baseline="middle" font-weight="bold">FS</text>
    </svg>'''
    
    return Response(
        content=svg_icon,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "Content-Type": "image/svg+xml"
        }
    )

@app.get("/health")
async def health_check():
    """Enhanced health check endpoint with comprehensive system status"""
    try:
        # Try to get system metrics
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            system_metrics = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2)
            }
        except ImportError:
            system_metrics = {"note": "psutil not available"}
        
        # Get data source status
        try:
            rotation_info = multi_source_tracker.get_comprehensive_rotation_info()
            api_status = rotation_info.get('api_status', {}) or {}
            available_sources = len([s for s in api_status.values() if s.get('available', False)])
            data_sources = {
                "available": available_sources,
                "total": len(api_status)
            }
        except Exception as e:
            logger.debug(f"Error getting data source status: {e}")
            data_sources = {"status": "unknown"}
        
        # Get detailed connection info
        connection_details = {
            "active_websockets": len(manager.active_connections),
            "subscriptions": {k: len(v) for k, v in manager.symbol_subscriptions.items()},
            "total_subscriptions": sum(len(v) for v in manager.symbol_subscriptions.values()),
            "subscription_breakdown": {sym: {"count": len(conns)} for sym, conns in manager.symbol_subscriptions.items()}
        }
        
        # Add performance metrics
        performance_info = {
            "total_requests": _performance_metrics['request_count'],
            "total_errors": _performance_metrics['error_count'],
            "average_response_time_ms": round(_performance_metrics['average_response_time'] * 1000, 2),
            "error_rate_percent": round(
                (_performance_metrics['error_count'] / max(_performance_metrics['request_count'], 1)) * 100, 
                2
            ),
            "rate_limit_entries": len(_rate_limit_store)
        }
        
        # Get API status with rate limit info
        api_status_detailed = {}
        try:
            from api_tracker import api_tracker
            for api_name in ['yfinance', 'ibkr', 'polygon', 'finnhub', 'alpha_vantage']:
                try:
                    can_request, reason = api_tracker.can_make_request(api_name)
                    usage = api_tracker.get_usage_stats(api_name)
                    api_status_detailed[api_name] = {
                        'available': can_request,
                        'reason': reason if not can_request else 'OK',
                        'requests_today': usage.get('requests_today', 0),
                        'rate_limited': usage.get('rate_limited', False),
                        'success_rate': usage.get('success_rate', 0),
                        'stage_a': api_name in ('yfinance', 'yahoo'),
                        'optional': api_name not in ('yfinance', 'yahoo'),
                    }
                except Exception as e:
                    logger.debug(f"Error getting API status for {api_name}: {e}")
                    api_status_detailed[api_name] = {'available': False, 'reason': 'Not configured'}
        except Exception as e:
            logger.debug(f"Error building API status details: {e}")
            api_status_detailed = {}

        if _desk_offline():
            data_sources = {
                "available": 0,
                "total": len(api_status_detailed) or 1,
                "mode": "offline_snapshot",
                "note": "Live fetches blocked — last-good snapshot only",
            }
            for name, row in list(api_status_detailed.items()):
                row = dict(row)
                row["available"] = False
                row["reason"] = "OFFLINE — not fetching live data"
                api_status_detailed[name] = row
        
        return JSONResponse(
            content={
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "2.0.0",
                "system": system_metrics,
                "connections": connection_details,
                "data_sources": data_sources,
                "performance": performance_info,
                "api_status": api_status_detailed,
                "offline": _offline_status(),
                "background_updater": {
                    "running": hasattr(background_data_updater, '_loop_count'),
                    "iterations": getattr(background_data_updater, '_loop_count', 0)
                }
            },
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse(
            content={
                "status": "degraded",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            },
            status_code=503,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )

@app.get("/api/bot-performance/diagnostic")
async def get_bot_performance_diagnostic():
    return _legacy_ledger_gone()


@app.get("/api/ml-model-status")
async def get_ml_model_status():
    return _legacy_ledger_gone()


@app.post("/api/bot-performance/backfill")
async def backfill_bot_outcomes_endpoint():
    return _legacy_ledger_gone()


@app.get("/api/bot-performance/today")
async def get_today_bot_performance():
    return _legacy_ledger_gone()


@app.get("/api/usage-stats")
async def get_api_usage_stats(request: Request):
    """Get API usage statistics and rate limit status"""
    try:
        stats = api_tracker.get_usage_stats()
        # Format response with better structure
        response_data = {
            'timestamp': datetime.now().isoformat(),
            'stats': stats,
            'yfinance_status': api_tracker.get_usage_stats('yfinance') if 'yfinance' in api_tracker.RATE_LIMITS else None
        }
        
        # Check if client wants HTML (browser) or JSON (API)
        accept_header = request.headers.get('accept', '')
        if 'text/html' in accept_header or request.url.path.endswith('.html'):
            # Return HTML view
            # Get yfinance stats safely
            try:
                yfinance_stats = api_tracker.get_usage_stats('yfinance')
            except Exception as e:
                yfinance_stats = {'error': str(e)}
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>API Usage Stats</title>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: #fff; }}
                    h1 {{ color: #3b82f6; }}
                    .api-card {{ background: #2a2a2a; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #3b82f6; }}
                    .limit {{ color: #f59e0b; }}
                    .blocked {{ color: #ef4444; }}
                    .safe {{ color: #10b981; }}
                    .stat {{ margin: 5px 0; }}
                    pre {{ background: #1a1a1a; padding: 10px; border-radius: 4px; overflow-x: auto; color: #fff; }}
                    .warning {{ background: #f59e0b20; border-left-color: #f59e0b; }}
                    .error {{ background: #ef444420; border-left-color: #ef4444; }}
                </style>
            </head>
            <body>
                <h1>📊 API Usage Statistics</h1>
                <p>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <div class="api-card">
                    <h2>yfinance Status</h2>
                    <pre>{json.dumps(yfinance_stats, indent=2, default=str)}</pre>
                </div>
                <div class="api-card">
                    <h2>All APIs Summary</h2>
                    <pre>{json.dumps(stats, indent=2, default=str)}</pre>
                </div>
                <p><a href="/api/usage-stats?format=json" style="color: #3b82f6;">View as JSON</a></p>
            </body>
            </html>
            """
            return HTMLResponse(content=html_content)
        else:
            # Return JSON
            return JSONResponse(content=response_data, media_type="application/json; charset=utf-8")
    except Exception as e:
        logger.error(f"Error getting API usage stats: {e}", exc_info=True)
        error_response = {'error': str(e), 'timestamp': datetime.now().isoformat()}
        return JSONResponse(content=error_response, status_code=500)

@app.get("/api/broker-config")
async def get_broker_config():
    """Get current broker configuration and commission info"""
    try:
        from broker_commission_tracker import broker_commission_tracker
        broker_info = broker_commission_tracker.get_broker_info()
        return JSONResponse(content=broker_info, media_type="application/json; charset=utf-8")
    except Exception as e:
        logger.error(f"Error getting broker config: {e}", exc_info=True)
        return JSONResponse({'error': str(e)}, status_code=500)

@app.post("/api/broker-config")
async def set_broker_config(request: Request):
    """Set broker configuration"""
    try:
        data = await request.json()
        broker_name = data.get('broker')
        
        if not broker_name:
            return JSONResponse({'error': 'broker name required'}, status_code=400)
        
        from broker_commission_tracker import broker_commission_tracker
        success = broker_commission_tracker.set_broker(broker_name)
        
        if success:
            return JSONResponse({
                'success': True,
                'broker': broker_name,
                'message': f'Broker set to {broker_name}'
            })
        else:
            return JSONResponse({
                'success': False,
                'error': f'Invalid broker: {broker_name}',
                'available_brokers': list(broker_commission_tracker.BROKER_COMMISSIONS.keys())
            }, status_code=400)
    except Exception as e:
        logger.error(f"Error setting broker config: {e}", exc_info=True)
        return JSONResponse({'error': str(e)}, status_code=500)

@app.get("/api/open-trades-status")
async def get_open_trades_status():
    return _legacy_ledger_gone()


@app.get("/api/commission-calculator")
async def calculate_commission(option_price: float, num_contracts: int = 1, broker: str = None):
    """Calculate commission for a trade"""
    try:
        from broker_commission_tracker import broker_commission_tracker
        
        if broker:
            broker_commission_tracker.set_broker(broker)
        
        entry_commission = broker_commission_tracker.calculate_commission(option_price, num_contracts, is_entry=True)
        exit_commission = broker_commission_tracker.calculate_commission(option_price, num_contracts, is_entry=False)
        total_commission = entry_commission + exit_commission
        min_profit_pct = broker_commission_tracker.calculate_min_profit_threshold(option_price, num_contracts)
        
        return JSONResponse({
            'option_price': option_price,
            'num_contracts': num_contracts,
            'broker': broker_commission_tracker.current_broker,
            'entry_commission': entry_commission,
            'exit_commission': exit_commission,
            'total_commission': total_commission,
            'min_profit_needed_pct': min_profit_pct,
            'option_cost': option_price * num_contracts * 100,
            'total_cost_with_commissions': (option_price * num_contracts * 100) + total_commission
        })
    except Exception as e:
        logger.error(f"Error calculating commission: {e}", exc_info=True)
        return JSONResponse({'error': str(e)}, status_code=500)

@app.get("/data-source")
async def get_data_source_info():
    """Get information about data sources"""
    from data_source_info import get_data_source_info
    return get_data_source_info()

@app.get("/rotation-stats")
async def get_rotation_stats():
    """Get API rotation statistics"""
    try:
        from multi_source_flow_tracker import multi_source_tracker
        
        # Get stats from tracker
        stats = {
            'rotation_interval': multi_source_tracker.rotation_interval,
            'total_rotations': len(multi_source_tracker.rotation_history),
            'total_uses': multi_source_tracker.total_source_use_count,
            'available_sources': multi_source_tracker.available_sources,
            'last_rotation': multi_source_tracker.rotation_history[-1] if multi_source_tracker.rotation_history else None,
            'rotation_history': multi_source_tracker.rotation_history[-10:]  # Last 10 rotations
        }
        return json_response(stats)
    except Exception as e:
        logger.error(f"Error getting rotation stats: {e}")
        return json_response({'error': str(e)})

@app.get("/performance-stats")
async def get_performance_stats():
    return _legacy_ledger_gone()


@app.get("/trade-history")
async def get_trade_history():
    return _legacy_ledger_gone()


@app.get("/api/performance-diagnostics")
async def get_performance_diagnostics():
    return _legacy_ledger_gone()


@app.get("/api/analytics/time-of-day")
async def get_time_of_day_analytics():
    return _legacy_ledger_gone()


@app.get("/api/analytics/historical-accuracy")
async def get_historical_accuracy():
    return _legacy_ledger_gone()


@app.get("/api/market-review")
async def get_market_review(days: int = 5):
    """Last N days: SPY context, news, Big Run re-grades, shadow + journal — Stage A learning."""
    try:
        from market_review import build_review

        report = build_review(days=days)
        return JSONResponse(report)
    except Exception as e:
        logger.error(f"market review error: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/shadow-learning/today")
async def get_shadow_learning_today():
    """What Stage A learned today via shadow grading (not paper Trade History)."""
    try:
        from shadow_learning_engine import shadow_learning_engine
        report = shadow_learning_engine.today_report()
        # Optional ML sample count for the day
        ml_today = 0
        ml_total = 0
        try:
            path = "ml_training_data.json"
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    ml = json.load(f)
                samples = ml if isinstance(ml, list) else (ml.get("samples") or ml.get("training_samples") or [])
                ml_total = len(samples)
                today = report.get("date") or datetime.now().date().isoformat()
                ml_today = sum(1 for s in samples if str(s.get("timestamp") or "").startswith(today))
        except Exception:
            pass
        report["ml_samples_today"] = ml_today
        report["ml_samples_total"] = ml_total
        return JSONResponse(report)
    except Exception as e:
        logger.error(f"Error getting shadow learning today: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/squeeze-radar")
async def get_squeeze_radar(request: Request):
    try:
        from squeeze_radar import squeeze_radar
        import hashlib
        snap = squeeze_radar.snapshot()
        # Scans land minutes apart but the desk polls far more often. An ETag
        # turns every in-between poll into an empty 304 instead of ~25KB, so the
        # panel only does work when the book actually changed.
        tag = 'W/"%s"' % hashlib.md5(
            json.dumps(snap, default=str, sort_keys=True).encode()
        ).hexdigest()
        if request.headers.get("if-none-match") == tag:
            return Response(status_code=304, headers={"ETag": tag})
        return JSONResponse(snap, headers={"ETag": tag})
    except Exception as e:
        return JSONResponse({"error": str(e), "alerts": []}, status_code=200)

@app.get("/api/desk-health")
async def get_desk_health():
    try:
        from desk_health import desk_health
        updater = getattr(app.state, "background_updater_task", None)
        sq_task = getattr(app.state, "squeeze_radar_task", None)
        ctx = {
            "ws_clients": len(manager.active_connections),
            "updater_alive": updater is not None and not updater.done(),
            "squeeze_task_alive": sq_task is not None and not sq_task.done(),
            "last_broadcast_ts": getattr(manager, "last_broadcast_ts", None),
        }
        snap = desk_health.last or desk_health.evaluate(ctx)
        return JSONResponse(snap)
    except Exception as e:
        return JSONResponse({"status": "UNHEALTHY", "reports": [str(e)], "error": str(e)}, status_code=200)

@app.post("/api/desk-health/fix")
async def post_desk_health_fix():
    """Client-requested safe autofix pass."""
    try:
        from desk_health import desk_health
        from squeeze_radar import squeeze_radar
        from market_hours_detector import session_clock
        updater = getattr(app.state, "background_updater_task", None)
        if updater is None or updater.done():
            t = asyncio.create_task(background_data_updater(update_interval=3.0))
            app.state.background_updater_task = t
            app.state.background_tasks.append(t)
            desk_health.record_fix("RESTART_UPDATER", "client requested", True)
        # A scan is a few hundred Yahoo requests. On a closed tape it would
        # return the same board it already has, so don't spend the quota.
        clock = session_clock()
        if clock.get("closed"):
            desk_health.record_fix(
                "NUDGE_SQUEEZE", f"skipped — {clock.get('label')}", True
            )
        else:
            await asyncio.to_thread(squeeze_radar.scan_pass)
            desk_health.record_fix("NUDGE_SQUEEZE", "client requested", True)
        ctx = {
            "ws_clients": len(manager.active_connections),
            "updater_alive": True,
            "squeeze_task_alive": True,
            "last_broadcast_ts": getattr(manager, "last_broadcast_ts", None),
        }
        return JSONResponse(desk_health.evaluate(ctx))
    except Exception as e:
        return JSONResponse({"status": "UNHEALTHY", "error": str(e)}, status_code=200)

@app.get("/api/trade-health")
async def get_trade_health():
    try:
        from trade_health import trade_health
        return JSONResponse(trade_health.last or trade_health.evaluate({}))
    except Exception as e:
        return JSONResponse({"status": "UNHEALTHY", "reports": [str(e)]}, status_code=200)

@app.get("/api/desk-org")
async def get_desk_org():
    """Three domain bosses — not cloned prediction bots."""
    try:
        from boss_decision_engine import boss_decision_engine as bde
        last = getattr(bde, "last_decision", None) or {}
    except Exception:
        last = {}
    try:
        from squeeze_radar import squeeze_radar
        sq = squeeze_radar.snapshot()
        prim = sq.get("primary") or {}
        run = {
            "symbol": prim.get("symbol"),
            "level": prim.get("level"),
            "confidence": (prim.get("plan") or {}).get("confidence") or prim.get("confidence"),
            "why": (prim.get("plan") or {}).get("why_plain") or prim.get("why"),
        }
    except Exception as e:
        run = {"error": str(e)}
    try:
        from trade_health import trade_health
        th = trade_health.last or {}
    except Exception:
        th = {}
    return JSONResponse({
        "bosses": {
            "odte": {
                "name": "0DTE Boss",
                "job": "SPY options tickets only",
                "action": last.get("action") or getattr(app.state, "last_boss_action", None),
            },
            "big_run": {
                "name": "Big Run Boss",
                "job": "share runners — never overrides 0DTE",
                **run,
            },
            "risk": {
                "name": "Risk Boss",
                "job": "book / streak / stuck 0DTE — never auto-closes",
                "status": th.get("status"),
                "reports": th.get("reports") or [],
            },
        },
        "note": "One order Boss per desk. Extra prediction bots are not added.",
    })


@app.get("/api/session-recap")
async def get_session_recap():
    """EOD / away-from-desk snapshot."""
    try:
        from shadow_learning_engine import shadow_learning_engine
        from squeeze_radar import squeeze_radar
        from paper_arm_state import paper_arm_state as arm
        rep = shadow_learning_engine.today_report()
        body = {
            "wins": rep.get("wins_today"),
            "losses": rep.get("losses_today"),
            "open": rep.get("open_count"),
            "win_rate": rep.get("win_rate_today"),
            "avg_win_usd": rep.get("avg_win_usd_1ct"),
            "paper_armed": bool(arm.armed) if arm else False,
            "squeeze": (squeeze_radar.snapshot().get("alerts") or [])[:5],
            "takeaways": (rep.get("takeaways") or [])[:4],
        }
        return JSONResponse(body)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/paper-trading/status")
async def get_paper_trading_status():
    """Get paper trading account status (shared singleton with Boss loop)"""
    try:
        from paper_trading_engine import paper_trading_engine as paper_engine
        from paper_arm_state import paper_arm_state as arm
        if paper_engine is None:
            return JSONResponse({'error': 'Paper engine unavailable'}, status_code=503)
        perf = paper_engine.get_performance()
        return JSONResponse({
            'balance': paper_engine.balance,
            'initial_balance': paper_engine.initial_balance,
            'open_positions': len(paper_engine.positions),
            'positions': paper_engine.get_open_positions(),
            'total_trades': len(paper_engine.trade_history),
            'closed_trades': len([t for t in paper_engine.trade_history if t.get('status') == 'CLOSED']),
            'pnl': paper_engine.balance - paper_engine.initial_balance,
            'pnl_pct': ((paper_engine.balance - paper_engine.initial_balance) / paper_engine.initial_balance * 100) if paper_engine.initial_balance > 0 else 0,
            'performance': perf,
            'risk': paper_engine.risk_status(),
            'armed': arm.armed if arm else False,
            'arm_status': arm.status() if arm else {},
        })
    except Exception as e:
        logger.error(f"Error getting paper trading status: {e}", exc_info=True)
        return JSONResponse({'error': str(e)}, status_code=500)

@app.post("/api/paper-trading/execute")
async def execute_paper_trade(request: Request):
    """Execute a paper trade on the shared singleton"""
    try:
        from paper_trading_engine import paper_trading_engine as paper_engine
        data = await request.json()
        if paper_engine is None:
            return JSONResponse({'error': 'Paper engine unavailable'}, status_code=503)
        signal = data.get('signal', {})
        current_price = float(data.get('current_price', 0))
        if current_price <= 0:
            return JSONResponse({'error': 'Invalid current price'}, status_code=400)
        result = await paper_engine.execute_trade(signal, current_price)
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"Error executing paper trade: {e}", exc_info=True)
        return JSONResponse({'error': str(e)}, status_code=500)

@app.get("/api/paper-trading/arm")
async def get_paper_arm_status():
    """Kill-switch status for Boss auto paper"""
    try:
        from paper_arm_state import paper_arm_state as arm
        return JSONResponse(arm.status())
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)

@app.post("/api/paper-trading/arm")
async def set_paper_arm(request: Request):
    """Arm or disarm Boss auto paper (server kill switch)"""
    try:
        from paper_arm_state import paper_arm_state as arm
        data = await request.json()
        armed = bool(data.get('armed', False))
        return JSONResponse(arm.set_armed(armed))
    except Exception as e:
        logger.error(f"Error setting paper arm: {e}", exc_info=True)
        return JSONResponse({'error': str(e)}, status_code=500)

@app.get("/api/risk-calculator")
async def calculate_risk(
    account_size: float = 10000,
    risk_per_trade_pct: float = 1.0,
    stop_loss_pct: float = 2.0,
    option_price: float = None,
    num_contracts: int = 1
):
    """Enhanced risk calculator with max loss limits"""
    try:
        # Calculate position size
        risk_amount = account_size * (risk_per_trade_pct / 100)
        max_loss = account_size * (stop_loss_pct / 100)
        
        # Calculate contracts based on risk
        if option_price and option_price > 0:
            cost_per_contract = option_price * 100
            max_contracts_by_risk = int(risk_amount / cost_per_contract) if cost_per_contract > 0 else 0
            max_contracts_by_loss = int(max_loss / cost_per_contract) if cost_per_contract > 0 else 0
            recommended_contracts = min(max_contracts_by_risk, max_contracts_by_loss, num_contracts)
            
            total_cost = recommended_contracts * cost_per_contract
            max_loss_amount = total_cost * (stop_loss_pct / 100)
        else:
            recommended_contracts = num_contracts
            total_cost = 0
            max_loss_amount = 0
        
        return JSONResponse({
            'account_size': account_size,
            'risk_per_trade_pct': risk_per_trade_pct,
            'risk_amount': round(risk_amount, 2),
            'stop_loss_pct': stop_loss_pct,
            'max_loss_limit': round(max_loss, 2),
            'recommended_contracts': recommended_contracts,
            'total_cost': round(total_cost, 2),
            'max_loss_amount': round(max_loss_amount, 2),
            'risk_reward_ratio': round((risk_amount / max_loss_amount) if max_loss_amount > 0 else 0, 2)
        })
    except Exception as e:
        logger.error(f"Error calculating risk: {e}", exc_info=True)
        return JSONResponse({'error': str(e)}, status_code=500)

@app.get("/api/backtest/run")
async def run_backtest(
    symbol: str = "SPY",
    start_date: str = None,
    end_date: str = None,
    initial_capital: float = 10000,
    position_size_pct: float = 10.0,
    stop_loss_pct: float = 2.0,
    take_profit_pct: float = 5.0
):
    """Run backtest with strategy optimization"""
    try:
        from enhanced_backtesting_engine import EnhancedBacktestingEngine
        engine = EnhancedBacktestingEngine()
        
        results = engine.comprehensive_backtest(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            position_size_pct=position_size_pct / 100,
            stop_loss_pct=stop_loss_pct / 100,
            take_profit_pct=take_profit_pct / 100
        )
        
        return JSONResponse(results)
    except Exception as e:
        logger.error(f"Error running backtest: {e}", exc_info=True)
        return JSONResponse({'error': str(e)}, status_code=500)

@app.get("/api/telegram/test")
async def test_telegram():
    """Test Telegram notification"""
    try:
        telegram_notifier = get_telegram_notifier()
        if not telegram_notifier or not telegram_notifier.enabled:
            return JSONResponse({
                'success': False,
                'message': 'Telegram notifier not enabled',
                'error': 'Missing bot_token or chat_id'
            })
        
        success = await telegram_notifier.send_message(
            "🧪 Test message from ShiftSignals!\n\n"
            "If you received this, your Telegram integration is working correctly. "
            "You will receive alerts for high-confidence trading signals (80%+ confidence)."
        )
        
        return JSONResponse({
            'success': success,
            'message': 'Test message sent' if success else 'Failed to send test message',
            'chat_id': telegram_notifier.chat_id
        })
    except Exception as e:
        logger.error(f"Error testing Telegram: {e}", exc_info=True)
        return JSONResponse({'success': False, 'error': str(e)}, status_code=500)

@app.post("/api/telegram/pause")
async def pause_telegram():
    """Pause Telegram notifications"""
    try:
        telegram_notifier = get_telegram_notifier()
        if not telegram_notifier:
            return JSONResponse({
                'success': False,
                'message': 'Telegram notifier not initialized',
                'error': 'Notifier not available'
            }, status_code=404)
        
        telegram_notifier.pause()
        
        return JSONResponse({
            'success': True,
            'message': 'Telegram notifications paused',
            'paused': True,
            'status': 'Notifications are now PAUSED. No signals will be sent until resumed.'
        })
    except Exception as e:
        logger.error(f"Error pausing Telegram: {e}", exc_info=True)
        return JSONResponse({'success': False, 'error': str(e)}, status_code=500)

@app.post("/api/telegram/resume")
async def resume_telegram():
    """Resume Telegram notifications"""
    try:
        telegram_notifier = get_telegram_notifier()
        if not telegram_notifier:
            return JSONResponse({
                'success': False,
                'message': 'Telegram notifier not initialized',
                'error': 'Notifier not available'
            }, status_code=404)
        
        telegram_notifier.resume()
        
        # Send a resumption message
        await telegram_notifier.send_message(
            "▶️ <b>NOTIFICATIONS RESUMED</b>\n\n"
            "Telegram alerts are now active again.\n"
            "You will receive high-confidence trading signals (85%+ confidence)."
        )
        
        return JSONResponse({
            'success': True,
            'message': 'Telegram notifications resumed',
            'paused': False,
            'status': 'Notifications are now ACTIVE. Signal alerts will be sent.'
        })
    except Exception as e:
        logger.error(f"Error resuming Telegram: {e}", exc_info=True)
        return JSONResponse({'success': False, 'error': str(e)}, status_code=500)

@app.get("/api/telegram/status")
async def telegram_status():
    """Get Telegram notification status"""
    try:
        telegram_notifier = get_telegram_notifier()
        if not telegram_notifier:
            return JSONResponse({
                'enabled': False,
                'paused': False,
                'message': 'Telegram notifier not initialized'
            })
        
        is_paused = telegram_notifier.is_paused()
        is_enabled = telegram_notifier.enabled
        
        return JSONResponse({
            'enabled': is_enabled,
            'paused': is_paused,
            'chat_id': telegram_notifier.chat_id if is_enabled else None,
            'status': 'PAUSED' if is_paused else ('ACTIVE' if is_enabled else 'DISABLED'),
            'message': 'Notifications are paused' if is_paused else ('Notifications are active' if is_enabled else 'Notifications are disabled')
        })
    except Exception as e:
        logger.error(f"Error getting Telegram status: {e}", exc_info=True)
        return JSONResponse({'error': str(e)}, status_code=500)

@app.get("/performance/trades")
async def get_performance_trades():
    return _legacy_ledger_gone()


@app.post("/api/auth/register")
async def register_user(request: Request):
    """Register a new user"""
    try:
        data = await request.json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        email = data.get('email', '').strip()
        
        if not username or not password:
            return JSONResponse(
                content={'success': False, 'message': 'Username and password required'},
                status_code=400
            )
        
        success, message = user_auth.register_user(username, password, email)
        
        if success:
            return JSONResponse(
                content={'success': True, 'message': message},
                status_code=201
            )
        else:
            return JSONResponse(
                content={'success': False, 'message': message},
                status_code=400
            )
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return JSONResponse(
            content={'success': False, 'message': 'Registration failed'},
            status_code=500
        )

@app.post("/api/auth/login")
async def login_user(request: Request):
    """Login user and get session token"""
    try:
        data = await request.json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return JSONResponse(
                content={'success': False, 'message': 'Username and password required'},
                status_code=400
            )
        
        success, token, message = user_auth.login(username, password)
        
        if success:
            preferences = user_auth.get_user_preferences(username)
            watchlist = user_auth.get_user_watchlist(username)
            
            return JSONResponse(
                content={
                    'success': True,
                    'token': token,
                    'username': username,
                    'preferences': preferences,
                    'watchlist': watchlist,
                    'message': message
                }
            )
        else:
            return JSONResponse(
                content={'success': False, 'message': message},
                status_code=401
            )
    except Exception as e:
        logger.error(f"Login error: {e}")
        return JSONResponse(
            content={'success': False, 'message': 'Login failed'},
            status_code=500
        )

@app.post("/api/auth/verify")
async def verify_token(request: Request):
    """Verify session token"""
    try:
        data = await request.json()
        token = data.get('token', '')
        
        if not token:
            return JSONResponse(
                content={'success': False, 'valid': False},
                status_code=400
            )
        
        is_valid, username = user_auth.verify_token(token)
        
        if is_valid:
            preferences = user_auth.get_user_preferences(username)
            watchlist = user_auth.get_user_watchlist(username)
            
            return JSONResponse(
                content={
                    'success': True,
                    'valid': True,
                    'username': username,
                    'preferences': preferences,
                    'watchlist': watchlist
                }
            )
        else:
            return JSONResponse(
                content={'success': True, 'valid': False},
                status_code=401
            )
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return JSONResponse(
            content={'success': False, 'valid': False},
            status_code=500
        )

@app.post("/api/auth/logout")
async def logout_user(request: Request):
    """Logout user (invalidate session)"""
    try:
        data = await request.json()
        token = data.get('token', '')
        
        if token:
            user_auth.logout(token)
        
        return JSONResponse(
            content={'success': True, 'message': 'Logged out'}
        )
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return JSONResponse(
            content={'success': False, 'message': 'Logout failed'},
            status_code=500
        )

# ===== USER PREFERENCES ENDPOINTS =====
@app.post("/api/user/preferences")
async def update_preferences(request: Request):
    """Update user preferences"""
    try:
        data = await request.json()
        token = data.get('token', '')
        preferences = data.get('preferences', {})
        
        is_valid, username = user_auth.verify_token(token)
        if not is_valid:
            return JSONResponse(
                content={'success': False, 'message': 'Invalid token'},
                status_code=401
            )
        
        user_auth.update_user_preferences(username, preferences)
        data_persistence.update_preferences(username, preferences)
        
        return JSONResponse(
            content={'success': True, 'message': 'Preferences updated'}
        )
    except Exception as e:
        logger.error(f"Update preferences error: {e}")
        return JSONResponse(
            content={'success': False, 'message': 'Update failed'},
            status_code=500
        )

@app.post("/api/user/watchlist")
async def update_watchlist(request: Request):
    """Update user watchlist"""
    try:
        data = await request.json()
        token = data.get('token', '')
        watchlist = data.get('watchlist', [])
        
        is_valid, username = user_auth.verify_token(token)
        if not is_valid:
            return JSONResponse(
                content={'success': False, 'message': 'Invalid token'},
                status_code=401
            )
        
        user_auth.update_user_watchlist(username, watchlist)
        data_persistence.update_watchlist(username, watchlist)
        
        return JSONResponse(
            content={'success': True, 'message': 'Watchlist updated'}
        )
    except Exception as e:
        logger.error(f"Update watchlist error: {e}")
        return JSONResponse(
            content={'success': False, 'message': 'Update failed'},
            status_code=500
        )

@app.get("/api/user/data")
async def get_user_data(request: Request):
    """Get all user data (preferences, watchlist, etc.)"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            token = request.query_params.get('token', '')
        
        is_valid, username = user_auth.verify_token(token)
        if not is_valid:
            return JSONResponse(
                content={'success': False, 'message': 'Invalid token'},
                status_code=401
            )
        
        user_data = data_persistence.get_user_data(username)
        preferences = user_auth.get_user_preferences(username)
        watchlist = user_auth.get_user_watchlist(username)
        
        return JSONResponse(
            content={
                'success': True,
                'username': username,
                'preferences': preferences,
                'watchlist': watchlist,
                'data': user_data
            }
        )
    except Exception as e:
        logger.error(f"Get user data error: {e}")
        return JSONResponse(
            content={'success': False, 'message': 'Failed to get user data'},
            status_code=500
        )

# ===== ERROR HANDLING ENDPOINT =====
@app.get("/api/errors/summary")
async def get_error_summary(request: Request):
    """Get error summary (for debugging)"""
    try:
        summary = error_handler.get_error_summary()
        return JSONResponse(content=summary)
    except Exception as e:
        logger.error(f"Error summary error: {e}")
        return JSONResponse(
            content={'error': 'Failed to get error summary'},
            status_code=500
        )

# ===== EXPORT ENDPOINTS =====
@app.get("/api/export/trades/csv")
async def export_trades_csv():
    return _legacy_ledger_gone()


@app.get("/api/export/trades/json")
async def export_trades_json():
    return _legacy_ledger_gone()


@app.get("/api/export/performance")
async def export_performance():
    return _legacy_ledger_gone()


@app.post("/close-trade/{trade_id}")
async def close_trade(trade_id: str):
    return _legacy_ledger_gone()


@app.get("/test-data/{symbol}")
async def test_data(symbol: str):
    """Test data fetching for a symbol - optimized with timeout"""
    try:
        loop = asyncio.get_event_loop()
        # Try multi-source first with timeout (5 seconds max)
        try:
            flow_data = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    multi_source_tracker.get_0dte_options_chain,
                    symbol
                ),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            logger.warning(f"Multi-source timeout for {symbol}, trying single source")
            flow_data = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    flow_tracker.get_0dte_options_chain,
                    symbol
                ),
                timeout=5.0
            )
        except Exception as e:
            logger.warning(f"Multi-source failed, trying single: {e}")
            flow_data = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    flow_tracker.get_0dte_options_chain,
                    symbol
                ),
                timeout=5.0
            )
        
        # Get previous close for price change calculation
        prev_close = 0
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d", interval="1d")
            if not hist.empty and len(hist) >= 2:
                prev_close = float(hist['Close'].iloc[-2])  # Previous day's close
        except Exception as e:
            logger.debug(f"Could not get previous close: {e}")
        
        return JSONResponse(
            content={
                "symbol": symbol,
                "stock_price": flow_data.get('stock_price', 0),
                "prev_close": prev_close,
                "expiration": flow_data.get('expiration'),
                "call_volume": flow_data.get('flow_metrics', {}).get('total_call_volume', 0),
                "put_volume": flow_data.get('flow_metrics', {}).get('total_put_volume', 0),
                "calls_count": len(flow_data.get('strikes', {}).get('calls_by_strike', [])),
                "puts_count": len(flow_data.get('strikes', {}).get('puts_by_strike', [])),
                "error": flow_data.get('error'),
                "data_source": flow_data.get('data_source', 'yfinance'),
                "timestamp": flow_data.get('timestamp', datetime.now()).isoformat() if hasattr(flow_data.get('timestamp', datetime.now()), 'isoformat') else str(flow_data.get('timestamp', datetime.now()))
            },
            media_type="application/json; charset=utf-8"
        )
    except Exception as e:
        return JSONResponse(
            content={
                "symbol": symbol,
                "error": str(e),
                "data_source": "unknown"
            },
            media_type="application/json; charset=utf-8"
        )

@app.post("/clear-cache")
async def clear_cache():
    """Clear yfinance cache"""
    from data_source_info import clear_yfinance_cache
    success, message = clear_yfinance_cache()
    return {"success": success, "message": message}

@app.post("/reload-trades")
async def reload_trades():
    return _legacy_ledger_gone()


@app.get("/market-regime")
async def get_market_regime():
    return _legacy_ledger_gone()


@app.get("/model-performance")
async def get_model_performance():
    return _legacy_ledger_gone()


@app.get("/ml-model-info")
async def get_ml_model_info():
    return _legacy_ledger_gone()


@app.get("/news-impact")
async def get_news_impact(symbol: str = "SPY"):
    """News endpoint disabled by request to avoid extra API usage and UI noise."""
    return JSONResponse(
        content={
            'source': 'disabled',
            'risk_score': 0,
            'articles': [],
            'note': 'News feed disabled'
        },
        media_type="application/json; charset=utf-8"
    )

# REMOVED: Duplicate endpoint - use GET /api/backtest/run instead
# This endpoint was redundant with the GET /api/backtest/run version above

@app.post("/retrain-model")
async def retrain_ml_model():
    return _legacy_ledger_gone()


@app.post("/reset-trades")
async def reset_trades():
    return _legacy_ledger_gone()


@app.post("/api/trade-history/restart")
async def restart_trade_history():
    return _legacy_ledger_gone()


if __name__ == "__main__":
    # Stage A entry — required for START_FLOWSCOUT.bat / Desktop shortcut
    import uvicorn

    host = os.getenv("FLOWSCOUT_HOST", "127.0.0.1")
    port = int(os.getenv("FLOWSCOUT_PORT", "8000"))
    try:
        from offline_mode import live_market_blocked, status_dict

        if live_market_blocked():
            st = status_dict()
            print(
                f"OFFLINE MODE — last-good snapshot, no live Yahoo. "
                f"has_snapshot={st.get('has_snapshot')} paper DISARMED",
                flush=True,
            )
    except Exception:
        pass
    print(f"FlowScout listening on http://{host}:{port}/", flush=True)
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=False,
    )

