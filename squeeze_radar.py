"""
Big Run · Predict — share-runner desk (not SPY 0DTE).

Workers → managers → Boss. Honest delayed Yahoo. Empty board beats a bank.
Tickets: will it pop (PRE/BUILDING/HOT), why, bands, buy/when/sell, confidence.
This desk does not call SPY 0DTE Boss and does not override it.
Keep module name + squeeze_radar singleton for the existing WS loop / API.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from cloud_runtime import state_path
    WATCH_FILE = str(state_path("squeeze_watchlist.json"))
    STATE_FILE = str(state_path("squeeze_radar_state.json"))
except Exception:
    WATCH_FILE = "squeeze_watchlist.json"
    STATE_FILE = "squeeze_radar_state.json"
COOLDOWN_SEC = 11 * 60
SCAN_PAUSE_SEC = 1.35  # deep-scan pacing; sweep itself is cheap screener HTTP
# Sweep = whole Yahoo mover market (cheap). Deep = full workers on a rotating slice.
SWEEP_MAX = 280
DEEP_PER_PASS = 72
SCREENER_COUNT = 100
PRICE_MIN = 0.50
PRICE_MAX = 25.0
NOTIONAL_TARGET = 500.0  # internal liquidity band only; never shown on tickets
MIN_VOLUME = 25_000
INSANE_SPREAD = 0.08  # 8%
TOO_LATE_PCT = 80.0
PRE_MAX_PCT = 5.5  # still "before the pop" if under this
PRE_MIN_SCORE = 6  # was 3 — RVOL 1.5 + coil was enough to list Ford
PRE_FLOAT_MAX_M = 80.0  # PRE veto above this unless real SI on still-small float
PRE_FLOAT_SHORT_MAX_M = 120.0
PRE_UNKNOWN_FLOAT_RVOL = 2.5
MEGA_FLOAT_M = 1000.0  # ABEV-style: never PRE, never SQUEEZE
MKTCAP_BLOCK = 10e9  # $10B+ is not a small/mid squeeze name
SQUEEZE_FLOAT_MAX_M = 20.0
# A name that structurally cannot move is not a setup, whatever its market cap.
# Measured on daily bars, so it holds in premarket and at 9:31 when the session
# range is still meaningless. ~2.5% ATR names (DOLE, BDN) never deliver a pop;
# real movers sit 5-10%+.
MIN_ATR_PCT = 3.0
ATR_BASELINE_PCT = 7.0  # archetypal mover the level targets were written for
# A stop inside the name's own daily noise is not a stop, it is a coin flip, and
# it makes every reward/risk number fiction.
MIN_STOP_ATR = 1.0
# Risking a dollar to make less than a dollar is not a setup. With a realistic
# stop this filters the lottery tickets that used to advertise huge reward/risk
# purely because their stop was inside the noise.
MIN_R_TARGET = 1.0

_atr_cache: Dict[str, Tuple[str, Optional[float]]] = {}
_atr_lock = threading.Lock()

# Yahoo predefined movers — union ≈ "whole market" of names that can actually run
SCREENER_IDS = (
    "day_gainers",
    "day_losers",
    "most_actives",
    "small_cap_gainers",
    "most_shorted_stocks",
    "aggressive_small_caps",
    "growth_technology_stocks",
    "undervalued_growth_stocks",
)

MEGA_BLOCK = {
    "SPY", "QQQ", "IWM", "DIA", "VOO", "VTI", "TQQQ", "SQQQ", "SPXL", "SPXS",
    "QLD", "QID", "UVXY", "VXX", "SVXY", "SOXL", "SOXS", "TNA", "TZA",
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "GOOG", "META", "TSLA", "NFLX",
    "AMD", "AVGO", "BRK.B", "BRK-B", "BRKB", "COST", "JPM", "LLY", "UNH",
    "JNJ", "V", "MA", "XOM", "WMT", "PG", "HD", "ORCL", "BAC", "KO", "PEP",
    "DIS", "INTU", "NOW", "IBM", "CAT", "GE", "CRM", "ADBE", "CSCO", "INTC",
    "MU", "TXN", "QCOM", "AMAT", "LIN", "ABBV", "MRK", "PFE", "TMO", "ABT",
    "WFC", "GS", "MS", "BLK", "BA", "NKE", "MCD", "SBUX", "LOW", "CVX",
    "COP", "PM", "T", "VZ", "CMCSA", "NFLX", "ISRG", "AMGN", "GILD",
    "SPX", "ES", "NQ", "RUT",
    # Cheap mega/liquid names that sneak in via the $0.50–$25 band. They do not squeeze.
    "F", "GM", "SAN", "NU", "ABEV", "VALE", "PBR", "PBR.A", "PBRA",
    "ITUB", "BBD", "C", "USB", "KEY", "RF", "HBAN", "BCS", "DB", "ING",
    "HSBC", "NOK", "ERIC", "SNAP", "NIO", "AAL", "DAL", "UAL", "GOLD",
    "NEM", "SOFI",
}

NOTE = (
    "Delayed Yahoo (not live tape). Shares, not 0DTE. Scans RTH + premarket + after-hours. "
    "Sweeps Yahoo mover screens market-wide, then deep-grades a rotating slice "
    "(full NYSE/NASDAQ deep-fetch every tick is not honest on free delayed Yahoo). "
    "Bands are scenarios, not a promise. This desk does not override SPY 0DTE Boss. "
    "Mega names are blocked — they do not squeeze."
)


def _num(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        x = float(v)
        if x != x:  # NaN
            return default
        return x
    except (TypeError, ValueError):
        return default


def _opt_num(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        x = float(v)
        if x != x:
            return None
        return x
    except (TypeError, ValueError):
        return None


def _norm_sym(s: Any) -> str:
    return str(s or "").upper().strip().replace("/", "")


def _is_otc_junk(sym: str) -> bool:
    if not sym or len(sym) > 5:
        return True
    if any(ch in sym for ch in (".", " ", "^")):
        # Keep listed class shares like BRK.B (already mega-blocked).
        if sym.count(".") == 1 and not sym.endswith((".WS", ".W", ".U", ".RT")):
            return False
        return True
    if len(sym) == 5 and sym[-1] in "FYGQZ":
        return True
    return False


def _blocked(sym: str) -> bool:
    if not sym:
        return True
    if sym in MEGA_BLOCK:
        return True
    if _is_otc_junk(sym):
        return True
    return False


def _quotes_from_payload(raw: Any) -> List[Dict[str, Any]]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [q for q in raw if isinstance(q, dict)]
    if isinstance(raw, dict):
        if isinstance(raw.get("quotes"), list):
            return [q for q in raw["quotes"] if isinstance(q, dict)]
        fin = raw.get("finance")
        if isinstance(fin, dict):
            results = fin.get("result") or []
            if results and isinstance(results, list) and isinstance(results[0], dict):
                qs = results[0].get("quotes") or []
                return [q for q in qs if isinstance(q, dict)]
        # DataFrame-like
        if hasattr(raw, "to_dict"):
            try:
                rec = raw.to_dict("records")
                return [q for q in rec if isinstance(q, dict)]
            except Exception:
                pass
    return []


def _http_screen(scr_id: str, count: int = 40) -> List[Dict[str, Any]]:
    url = (
        "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved"
        f"?formatted=false&lang=en-US&region=US&scrIds={scr_id}&count={count}"
        "&corsDomain=finance.yahoo.com"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 FlowScout/1.0"})
    with urllib.request.urlopen(req, timeout=12) as resp:
        payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    return _quotes_from_payload(payload)


def _yf_screen(scr_id: str, count: int = 40) -> List[Dict[str, Any]]:
    try:
        import yfinance as yf

        if hasattr(yf, "screen"):
            raw = yf.screen(scr_id, count=count)
            qs = _quotes_from_payload(raw)
            if qs:
                return qs
    except Exception as e:
        logger.debug(f"yf.screen {scr_id}: {e}")
    try:
        return _http_screen(scr_id, count)
    except Exception as e:
        logger.debug(f"http screen {scr_id}: {e}")
        return []


def _quote_price(q: Dict[str, Any]) -> float:
    return _num(
        q.get("regularMarketPrice")
        or q.get("intradayprice")
        or q.get("lastPrice")
        or q.get("price")
    )


def _quote_volume(q: Dict[str, Any]) -> float:
    return _num(q.get("regularMarketVolume") or q.get("volume") or q.get("dayvolume"))


def _load_watchlist_symbols() -> List[str]:
    out: List[str] = []
    try:
        if not os.path.exists(WATCH_FILE):
            return out
        with open(WATCH_FILE, "r", encoding="utf-8") as f:
            extra = json.load(f)
        names = extra if isinstance(extra, list) else (extra.get("symbols") or [])
        for s in names:
            u = _norm_sym(s)
            if u and not _blocked(u) and u not in out:
                out.append(u)
    except Exception as e:
        logger.debug(f"squeeze watchlist: {e}")
    return out


def _build_universe() -> List[str]:
    """Backward-compatible: deep-scan list for this pass (rotating slice of the sweep). """
    sweep = _sweep_market()
    return [s for _, s in sweep[:DEEP_PER_PASS]]


def _sweep_market() -> List[Tuple[float, str]]:
    """
    Cheap whole-market mover sweep via Yahoo predefined screeners.
    Returns (score, symbol) sorted hottest-first. No per-name history fetch.
    """
    seen = set()
    ranked: List[Tuple[float, str]] = []
    for sid in SCREENER_IDS:
        for q in _yf_screen(sid, count=SCREENER_COUNT):
            sym = _norm_sym(q.get("symbol"))
            if not sym or _blocked(sym) or sym in seen:
                continue
            px = _quote_price(q)
            if px and (px < PRICE_MIN or px > PRICE_MAX):
                continue
            vol = _quote_volume(q)
            # Prefer extended-hours change when Yahoo sends it
            pct = abs(
                _num(
                    q.get("preMarketChangePercent")
                    or q.get("postMarketChangePercent")
                    or q.get("regularMarketChangePercent")
                    or q.get("percentchange")
                )
            )
            # Hot tape first: % move weighted, then volume
            score = pct * 1e6 + vol
            seen.add(sym)
            ranked.append((score, sym))
    for u in _load_watchlist_symbols():
        if u not in seen:
            seen.add(u)
            ranked.append((0.0, u))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked[:SWEEP_MAX]


def _deep_slice(sweep: List[Tuple[float, str]], cursor: int, n: int) -> Tuple[List[str], int]:
    """Rotate through the full sweep so every mover gets a deep pass over time."""
    if not sweep:
        return [], 0
    syms = [s for _, s in sweep]
    n = max(1, min(n, len(syms)))
    start = int(cursor) % len(syms)
    out: List[str] = []
    for i in range(n):
        out.append(syms[(start + i) % len(syms)])
    next_cursor = (start + n) % len(syms)
    return out, next_cursor


def _fast_map(fi: Any) -> Dict[str, Any]:
    if fi is None:
        return {}
    try:
        if isinstance(fi, dict):
            return dict(fi)
        out = {}
        for k in (
            "lastPrice", "last_price", "previousClose", "previous_close",
            "regularMarketPreviousClose", "open", "dayHigh", "dayLow",
            "lastVolume", "last_volume", "tenDayAverageVolume",
            "threeMonthAverageVolume", "shares", "sharesOutstanding",
            "marketCap", "bid", "ask", "yearHigh", "yearLow",
        ):
            try:
                if hasattr(fi, k):
                    out[k] = getattr(fi, k)
            except Exception:
                pass
        try:
            out.update(dict(fi))
        except Exception:
            pass
        return out
    except Exception:
        return {}


def _fetch_ctx(symbol: str, session: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Cheap per-name snapshot. Includes Yahoo premarket / after-hours when available."""
    try:
        import yfinance as yf
    except Exception:
        return None
    try:
        t = yf.Ticker(symbol)
    except Exception:
        return None

    sess = str(session or "").upper()
    ctx: Dict[str, Any] = {
        "symbol": symbol,
        "spot": 0.0,
        "prev_close": 0.0,
        "open": 0.0,
        "volume": 0.0,
        "avg_volume": 0.0,
        "bid": 0.0,
        "ask": 0.0,
        "float_shares": None,
        "shares_out": None,
        "short_pct": None,
        "bars_5m": None,
        "high": 0.0,
        "low": 0.0,
        "mktcap": None,
        "atr_pct": None,
        "days_to_cover": None,
        "si_change_pct": None,
        "session": sess or None,
        "quote_source": "regular",
        "pre_price": 0.0,
        "post_price": 0.0,
        "regular_price": 0.0,
    }

    fi = {}
    try:
        fi = _fast_map(getattr(t, "fast_info", None))
    except Exception:
        fi = {}

    ctx["spot"] = _num(fi.get("lastPrice") or fi.get("last_price"))
    ctx["prev_close"] = _num(
        fi.get("previousClose") or fi.get("previous_close") or fi.get("regularMarketPreviousClose")
    )
    ctx["open"] = _num(fi.get("open"))
    ctx["volume"] = _num(fi.get("lastVolume") or fi.get("last_volume"))
    ctx["avg_volume"] = _num(
        fi.get("threeMonthAverageVolume") or fi.get("tenDayAverageVolume") or fi.get("three_month_average_volume")
    )
    ctx["bid"] = _num(fi.get("bid"))
    ctx["ask"] = _num(fi.get("ask"))
    ctx["shares_out"] = _opt_num(fi.get("shares") or fi.get("sharesOutstanding"))
    ctx["high"] = _num(fi.get("dayHigh") or fi.get("day_high"))
    ctx["low"] = _num(fi.get("dayLow") or fi.get("day_low"))
    ctx["mktcap"] = _opt_num(fi.get("marketCap") or fi.get("market_cap"))

    # Extended-hours 5m tape (premarket 4:00 + after-hours to ~20:00 ET)
    try:
        h = t.history(period="1d", interval="5m", prepost=True)
        if h is not None and not getattr(h, "empty", True):
            ctx["bars_5m"] = h
            if ctx["spot"] <= 0:
                ctx["spot"] = _num(h["Close"].iloc[-1])
            if ctx["open"] <= 0:
                ctx["open"] = _num(h["Open"].iloc[0])
            if "Volume" in h.columns:
                sess_vol = _session_bar_volume(h, sess)
                if sess_vol > 0:
                    ctx["volume"] = sess_vol
                elif ctx["volume"] <= 0:
                    ctx["volume"] = _num(h["Volume"].sum())
            if "High" in h.columns:
                ctx["high"] = max(ctx["high"], _num(h["High"].max()))
            if "Low" in h.columns:
                lo = _num(h["Low"].min())
                if lo > 0:
                    ctx["low"] = lo if ctx["low"] <= 0 else min(ctx["low"], lo)
            # Premarket / AH open = first print of that session window
            so = _session_open_from_bars(h, sess)
            if so > 0 and sess in ("PREMARKET", "AFTER_HOURS", "OVERNIGHT"):
                ctx["open"] = so
    except Exception:
        pass

    if ctx["prev_close"] <= 0:
        try:
            d = t.history(period="5d", interval="1d")
            if d is not None and not getattr(d, "empty", True) and len(d) >= 2:
                ctx["prev_close"] = _num(d["Close"].iloc[-2])
                if ctx["open"] <= 0:
                    ctx["open"] = _num(d["Open"].iloc[-1])
                if ctx["spot"] <= 0:
                    ctx["spot"] = _num(d["Close"].iloc[-1])
                if ctx["volume"] <= 0 and "Volume" in d.columns:
                    ctx["volume"] = _num(d["Volume"].iloc[-1])
        except Exception:
            pass

    need_info = (
        ctx["float_shares"] is None
        or ctx["short_pct"] is None
        or ctx["avg_volume"] <= 0
        or ctx["spot"] <= 0
        or sess in ("PREMARKET", "AFTER_HOURS", "OVERNIGHT")
    )
    if need_info:
        try:
            info = t.info or {}
            if not isinstance(info, dict):
                info = {}
            pre_px = _num(info.get("preMarketPrice") or info.get("premarketPrice"))
            post_px = _num(info.get("postMarketPrice") or info.get("postmarketPrice"))
            reg_px = _num(info.get("regularMarketPrice") or info.get("currentPrice"))
            ctx["pre_price"] = pre_px
            ctx["post_price"] = post_px
            ctx["regular_price"] = reg_px
            # Prefer the print that matches the session clock
            if sess == "PREMARKET" and pre_px > 0:
                ctx["spot"] = pre_px
                ctx["quote_source"] = "premarket"
            elif sess in ("AFTER_HOURS", "OVERNIGHT") and post_px > 0:
                ctx["spot"] = post_px
                ctx["quote_source"] = "after_hours"
            elif ctx["spot"] <= 0 and reg_px > 0:
                ctx["spot"] = reg_px
                ctx["quote_source"] = "regular"
            elif ctx["spot"] <= 0:
                ctx["spot"] = _num(info.get("regularMarketPrice") or info.get("currentPrice"))
            if ctx["prev_close"] <= 0:
                ctx["prev_close"] = _num(info.get("previousClose") or info.get("regularMarketPreviousClose"))
            if ctx["open"] <= 0:
                ctx["open"] = _num(info.get("open") or info.get("regularMarketOpen"))
            pre_vol = _num(info.get("preMarketVolume") or info.get("premarketVolume"))
            if sess == "PREMARKET" and pre_vol > 0:
                ctx["volume"] = pre_vol
            elif ctx["volume"] <= 0:
                ctx["volume"] = _num(info.get("volume") or info.get("regularMarketVolume"))
            if ctx["avg_volume"] <= 0:
                ctx["avg_volume"] = _num(info.get("averageVolume") or info.get("averageVolume10days"))
            if ctx["bid"] <= 0:
                ctx["bid"] = _num(info.get("bid"))
            if ctx["ask"] <= 0:
                ctx["ask"] = _num(info.get("ask"))
            ctx["float_shares"] = _opt_num(info.get("floatShares"))
            ctx["shares_out"] = ctx["shares_out"] or _opt_num(info.get("sharesOutstanding"))
            ctx["name"] = str(info.get("shortName") or info.get("longName") or "").strip() or None
            if ctx.get("mktcap") is None:
                ctx["mktcap"] = _opt_num(info.get("marketCap"))
            sp = _opt_num(info.get("shortPercentOfFloat"))
            if sp is not None:
                # Yahoo sometimes 0.15, sometimes 15.0
                ctx["short_pct"] = round(sp * 100.0, 2) if sp <= 1.5 else round(sp, 2)
            # Days to cover = shares short / avg daily volume. Short % of float
            # says the trade is crowded; days to cover says the exit is narrow,
            # which is the part that actually forces a squeeze.
            dtc = _opt_num(info.get("shortRatio"))
            shares_short = _opt_num(info.get("sharesShort"))
            if dtc is None and shares_short and ctx["avg_volume"] > 0:
                dtc = shares_short / ctx["avg_volume"]
            if dtc is not None and dtc > 0:
                ctx["days_to_cover"] = round(dtc, 1)
            prior = _opt_num(info.get("sharesShortPriorMonth"))
            if shares_short and prior and prior > 0:
                chg = (shares_short / prior - 1.0) * 100.0
                # Reverse splits and share-count restatements produce nonsense
                # like +7000%; that is a corporate action, not the crowd piling in.
                if -95.0 <= chg <= 300.0:
                    ctx["si_change_pct"] = round(chg, 1)
        except Exception:
            pass

    if ctx.get("mktcap") is None:
        so = ctx.get("shares_out") or ctx.get("float_shares")
        if so and ctx["spot"] > 0:
            ctx["mktcap"] = float(so) * ctx["spot"]

    if ctx["spot"] <= 0:
        return None
    # Only spend a request on names that clear the price band, and the result is
    # cached per day — so this is about one call per name per session.
    if PRICE_MIN <= ctx["spot"] <= PRICE_MAX:
        ctx["atr_pct"] = _atr_pct(symbol, t)
    return ctx


def _bar_minutes_et(idx) -> Optional[int]:
    """Return HH*60+MM in America/New_York for a bar index label."""
    try:
        from zoneinfo import ZoneInfo
        import pandas as pd

        ts = pd.Timestamp(idx)
        if ts.tzinfo is None:
            ts = ts.tz_localize("America/New_York")
        else:
            ts = ts.tz_convert("America/New_York")
        return int(ts.hour * 60 + ts.minute)
    except Exception:
        return None


def _session_open_from_bars(h: Any, session: str) -> float:
    """First open print inside the active extended window."""
    try:
        if h is None or getattr(h, "empty", True):
            return 0.0
        sess = str(session or "").upper()
        for idx, row in h.iterrows():
            mins = _bar_minutes_et(idx)
            if mins is None:
                continue
            if sess == "PREMARKET" and mins < (9 * 60 + 30):
                return _num(row.get("Open"))
            if sess in ("AFTER_HOURS", "OVERNIGHT") and mins >= (16 * 60):
                return _num(row.get("Open"))
        return _num(h["Open"].iloc[0])
    except Exception:
        return 0.0


def _session_bar_volume(h: Any, session: str) -> float:
    """Sum 5m volume for the session window (pre / AH), else full prepost day."""
    try:
        if h is None or getattr(h, "empty", True) or "Volume" not in h.columns:
            return 0.0
        sess = str(session or "").upper()
        total = 0.0
        matched = False
        for idx, row in h.iterrows():
            mins = _bar_minutes_et(idx)
            vol = _num(row.get("Volume"))
            if mins is None:
                total += vol
                continue
            if sess == "PREMARKET":
                if mins < (9 * 60 + 30):
                    total += vol
                    matched = True
            elif sess in ("AFTER_HOURS", "OVERNIGHT"):
                if mins >= (16 * 60):
                    total += vol
                    matched = True
            else:
                total += vol
                matched = True
        if matched and total > 0:
            return total
        return _num(h["Volume"].sum())
    except Exception:
        return 0.0


def spike_worker(ctx: Dict[str, Any]) -> Dict[str, Any]:
    spot = _num(ctx.get("spot"))
    prev = _num(ctx.get("prev_close"))
    opn = _num(ctx.get("open"))
    vol = _num(ctx.get("volume"))
    avg = _num(ctx.get("avg_volume"))
    sess = str(ctx.get("session") or "").upper()
    pct = ((spot - prev) / prev * 100.0) if prev > 0 else 0.0
    gap = ((opn - prev) / prev * 100.0) if prev > 0 and opn > 0 else 0.0
    # Extended hours: session volume is a slice of the day — scale the baseline
    if sess == "PREMARKET" and avg > 0:
        baseline = avg * 0.12
    elif sess in ("AFTER_HOURS", "OVERNIGHT") and avg > 0:
        baseline = avg * 0.08
    else:
        baseline = avg
    rvol = (vol / baseline) if baseline > 0 else 0.0
    accel = 0.0
    h = ctx.get("bars_5m")
    try:
        if h is not None and not getattr(h, "empty", True) and len(h) >= 4:
            last = _num(h["Close"].iloc[-1])
            prior = _num(h["Close"].iloc[-4])
            if prior > 0:
                accel = (last - prior) / prior * 100.0
    except Exception:
        accel = 0.0
    notes = []
    score = 0
    if abs(pct) >= 0.4:
        notes.append(f"{pct:+.1f}% vs prev close")
        score += 1
    if rvol >= 1.4:
        tag = "ext RVOL" if sess in ("PREMARKET", "AFTER_HOURS", "OVERNIGHT") else "RVOL"
        notes.append(f"{tag} {rvol:.1f}x")
        score += 2
    if abs(gap) >= 3:
        notes.append(f"gap {gap:+.1f}%")
        score += 1
    if accel >= 2:
        notes.append(f"5m accel {accel:+.1f}%")
        score += 1
    qs = ctx.get("quote_source")
    if qs and qs != "regular":
        notes.append(f"quote={qs}")
    return {
        "pct": round(pct, 2),
        "rvol": round(rvol, 2),
        "gap_pct": round(gap, 2),
        "accel_5m": round(accel, 2),
        "notes": notes,
        "score": score,
        "veto": [],
    }


def squeeze_worker(ctx: Dict[str, Any]) -> Dict[str, Any]:
    fs = ctx.get("float_shares")
    so = ctx.get("shares_out")
    float_shares = _opt_num(fs) or _opt_num(so)
    float_m = round(float_shares / 1e6, 2) if float_shares and float_shares > 0 else None
    short_pct = _opt_num(ctx.get("short_pct"))  # None = unknown, never fake
    spot = _num(ctx.get("spot"))
    in_band = PRICE_MIN <= spot <= PRICE_MAX
    mktcap = _opt_num(ctx.get("mktcap"))
    notes = []
    score = 0
    veto: List[str] = []
    if float_m is not None and float_m >= MEGA_FLOAT_M:
        veto.append("mega float — cannot squeeze")
    if mktcap is not None and mktcap >= MKTCAP_BLOCK:
        veto.append("mega cap — cannot squeeze")
    if float_m is not None and float_m < SQUEEZE_FLOAT_MAX_M:
        notes.append(f"float {float_m:.1f}M")
        score += 3
    if short_pct is not None and short_pct >= 15.0 and (float_m is None or float_m < PRE_FLOAT_SHORT_MAX_M):
        notes.append(f"short {short_pct:.1f}% of float")
        score += 2
    # Days to cover is the exit-width measure: crowding alone does not squeeze
    # anyone, being unable to get out does. Thresholds follow the published
    # work — 5+ days is where forced covering starts showing up, 10+ is extreme.
    dtc = _opt_num(ctx.get("days_to_cover"))
    if dtc is not None and dtc > 0:
        if dtc >= 10.0:
            notes.append(f"{dtc:.1f} days to cover — shorts are trapped")
            score += 4
        elif dtc >= 5.0:
            notes.append(f"{dtc:.1f} days to cover")
            score += 2
        elif dtc >= 3.0:
            notes.append(f"{dtc:.1f} days to cover — shorts still nimble")
    # Rising short interest into strength is the crowd adding to a losing bet.
    si_chg = _opt_num(ctx.get("si_change_pct"))
    if si_chg is not None and si_chg >= 15.0:
        notes.append(f"short interest +{si_chg:.0f}% vs prior month")
        score += 2
    elif si_chg is not None and si_chg <= -20.0:
        notes.append(f"shorts already covering ({si_chg:.0f}%)")
    return {
        "float_m": float_m,
        "short_pct": round(short_pct, 2) if short_pct is not None else None,
        "days_to_cover": dtc,
        "si_change_pct": si_chg,
        "mktcap": mktcap,
        "in_band": in_band,
        "notes": notes,
        "score": score,
        "veto": veto,
    }


def liquidity_worker(ctx: Dict[str, Any]) -> Dict[str, Any]:
    vol = _num(ctx.get("volume"))
    bid = _num(ctx.get("bid"))
    ask = _num(ctx.get("ask"))
    spread_pct = None
    if bid > 0 and ask > bid:
        spread_pct = (ask - bid) / ask
    halt_risk = False
    h = ctx.get("bars_5m")
    try:
        if h is not None and not getattr(h, "empty", True) and len(h) >= 2:
            last_hi = _num(h["High"].iloc[-1])
            last_lo = _num(h["Low"].iloc[-1])
            last_c = _num(h["Close"].iloc[-1])
            if last_c > 0 and (last_hi - last_lo) / last_c >= 0.08:
                halt_risk = True
    except Exception:
        pass
    notes = []
    score = 1 if vol >= MIN_VOLUME else 0
    veto: List[str] = []
    if vol > 0:
        notes.append(f"vol {vol:,.0f}")
    if spread_pct is not None:
        notes.append(f"spread {spread_pct:.1%}")
        if spread_pct >= INSANE_SPREAD:
            veto.append("insane spread")
    if halt_risk:
        notes.append("halt-risk (wide 5m range)")
        veto.append("halt risk — drop")
    return {
        "volume": vol,
        "spread_pct": spread_pct,
        "halt_risk": halt_risk,
        "notes": notes,
        "score": score,
        "veto": veto,
    }


def pre_worker(ctx: Dict[str, Any], spike: Dict[str, Any], squeeze: Dict[str, Any]) -> Dict[str, Any]:
    """Leading tells *before* the +5–12% spike. Volume/structure first, price last."""
    notes: List[str] = []
    score = 0
    pct = _num(spike.get("pct"))
    rvol = _num(spike.get("rvol"))
    gap = _num(spike.get("gap_pct"))
    accel = _num(spike.get("accel_5m"))
    float_m = squeeze.get("float_m")
    short_pct = squeeze.get("short_pct")
    spot = _num(ctx.get("spot"))
    high = _num(ctx.get("high"))
    low = _num(ctx.get("low"))
    h = ctx.get("bars_5m")
    primary = False
    secondary: List[str] = []

    still_quiet = pct < PRE_MAX_PCT and pct > -8.0
    if not still_quiet:
        return {
            "score": 0, "notes": [], "still_quiet": False, "coiled": False,
            "volume_before_price": False, "secondary_tells": [], "veto": [],
        }

    # 1) Volume arriving before price — required PRE tell
    if rvol >= 1.5:
        score += 4
        primary = True
        notes.append("volume ahead of price")
    elif rvol >= 1.2:
        score += 1
        notes.append("RVOL starting")

    # 2) Last 5m bars expanding vs the open (tape waking up)
    try:
        if h is not None and not getattr(h, "empty", True) and "Volume" in h.columns and len(h) >= 6:
            vols = [float(x) for x in h["Volume"].tolist() if float(x) == float(x)]
            if len(vols) >= 6:
                early = sum(vols[:-3]) / max(1, len(vols) - 3)
                late = sum(vols[-3:]) / 3.0
                if early > 0 and late >= 2.0 * early:
                    score += 3
                    secondary.append("vol_expand")
                    notes.append("5m volume expanding")
                if len(h) >= 4:
                    lows = [float(x) for x in h["Low"].tolist()]
                    if lows[-1] > lows[-2] > lows[-3]:
                        score += 2
                        secondary.append("higher_lows")
                        notes.append("5m higher lows")
    except Exception:
        pass

    # 3) Tight day range then first break of the high (coiled)
    try:
        if spot > 0 and high > 0 and low > 0:
            rng = (high - low) / spot
            if rng <= 0.035 and high > 0 and (high - spot) / high <= 0.004:
                score += 3
                secondary.append("coil")
                notes.append("first break of tight range")
            elif rng <= 0.025:
                score += 2
                secondary.append("coil")
                notes.append("range coiled")
    except Exception:
        pass

    # 4) Gap held, not yet extended — leftover premarket interest
    if 2.0 <= gap <= 12.0 and pct < PRE_MAX_PCT and pct >= 0:
        score += 3
        secondary.append("gap_hold")
        notes.append(f"gap {gap:+.1f}% still holding")

    if accel >= 1.2 and pct < PRE_MAX_PCT:
        score += 1
        notes.append("early 5m lift")

    # 5) Squeeze coiled: only when float is actually small
    coiled = False
    if float_m is not None and float_m < SQUEEZE_FLOAT_MAX_M and rvol >= 1.15:
        coiled = True
        score += 2
        notes.append("low float + volume tick")
    if (
        short_pct is not None
        and short_pct >= 15.0
        and rvol >= 1.1
        and float_m is not None
        and float_m < PRE_FLOAT_MAX_M
    ):
        coiled = True
        score += 2
        notes.append("short% loaded, tape not extended")

    return {
        "score": score,
        "notes": notes,
        "still_quiet": True,
        "coiled": coiled,
        "volume_before_price": primary,
        "secondary_tells": list(dict.fromkeys(secondary)),
        "veto": [],
    }


def _pre_float_ok(float_m: Optional[float], short_pct: Optional[float], rvol: float) -> bool:
    """Huge float cannot be PRE. Unknown float needs stronger volume."""
    if float_m is not None:
        if float_m >= MEGA_FLOAT_M:
            return False
        if float_m > PRE_FLOAT_MAX_M:
            si = short_pct is not None and short_pct >= 15.0
            return bool(si and float_m < PRE_FLOAT_SHORT_MAX_M)
        return True
    return rvol >= PRE_UNKNOWN_FLOAT_RVOL


def _too_big_to_squeeze(float_m: Optional[float], mktcap: Optional[float]) -> bool:
    if float_m is not None and float_m >= MEGA_FLOAT_M:
        return True
    if mktcap is not None and mktcap >= MKTCAP_BLOCK:
        return True
    return False


def veto_worker(
    ctx: Dict[str, Any],
    spike: Dict[str, Any],
    squeeze: Dict[str, Any],
    liq: Dict[str, Any],
) -> Dict[str, Any]:
    fatal: List[str] = []
    watch_only = False
    spot = _num(ctx.get("spot"))
    if spot <= 0:
        fatal.append("missing price")
    if not (PRICE_MIN <= spot <= PRICE_MAX):
        fatal.append("price outside $0.50–$25 band")
    vol = _num(liq.get("volume"))
    rvol = _num(spike.get("rvol"))
    float_m = squeeze.get("float_m")
    short_pct = squeeze.get("short_pct")
    mktcap = squeeze.get("mktcap") if squeeze.get("mktcap") is not None else ctx.get("mktcap")
    if _too_big_to_squeeze(float_m, mktcap):
        fatal.append("mega float / mega cap — cannot squeeze")
    setup_ok = rvol >= 1.4 or (
        float_m is not None and float_m < SQUEEZE_FLOAT_MAX_M and short_pct is not None and short_pct >= 15.0
    )
    if vol < MIN_VOLUME and not setup_ok:
        fatal.append("no volume")
    atr = ctx.get("atr_pct")
    if atr is not None and _num(atr) < MIN_ATR_PCT:
        # Not a cap question — this name simply does not travel far enough to
        # pay for the risk, so it never belonged on a spike/squeeze board.
        fatal.append(f"does not move — {_num(atr):.1f}% ATR")
    sp = liq.get("spread_pct")
    if sp is not None and sp >= INSANE_SPREAD:
        fatal.append("insane spread")
    pct = _num(spike.get("pct"))
    if pct >= TOO_LATE_PCT:
        watch_only = True
        fatal.append("already +80% — too late to chase HOT")
    return {"fatal": fatal, "watch_only": watch_only, "score": 0 if fatal else 1, "notes": fatal, "veto": fatal}


def extension_worker(spike: Dict[str, Any]) -> Dict[str, Any]:
    """Already too late / leftover only — never invent a first-print if it's gone."""
    pct = _num(spike.get("pct"))
    notes: List[str] = []
    veto: List[str] = []
    too_late = pct >= TOO_LATE_PCT
    leftover = pct >= PRE_MAX_PCT
    score = 0
    if too_late:
        veto.append("already +80% — leftover only, skip chase")
        notes.append("too late / leftover only")
    elif pct >= 12.0:
        leftover = True
        notes.append(f"already {pct:+.1f}% — leftover, not the first print")
        score = 1
    elif leftover:
        notes.append(f"already {pct:+.1f}% — leftover")
        score = 1
    else:
        notes.append("not extended yet")
        score = 2
    return {
        "score": score,
        "notes": notes,
        "veto": veto,
        "too_late": too_late,
        "leftover": leftover,
    }


def regime_worker(bench: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Is the tape paying for long risk today?

    Small-cap spikes and squeezes are long, high-beta bets. They work far less
    often when the index is bleeding, so instead of silencing the desk on red
    days we demand a better payoff to take the same risk.
    """
    bench = bench or {}
    spy = _opt_num(bench.get("SPY"))
    qqq = _opt_num(bench.get("QQQ"))
    ref = spy if spy is not None else qqq
    if ref is None:
        return {"label": "UNKNOWN", "risk_off": False, "spy_pct": None,
                "note": "no index read this pass", "r_multiplier": 1.0}
    ref = float(ref)
    if ref <= -1.0:
        return {"label": "RISK_OFF", "risk_off": True, "spy_pct": round(ref, 2),
                "note": f"index {ref:+.1f}% — long small-cap risk is uphill",
                "r_multiplier": 1.5}
    if ref >= 0.5:
        return {"label": "RISK_ON", "risk_off": False, "spy_pct": round(ref, 2),
                "note": f"index {ref:+.1f}% — tape supports long risk",
                "r_multiplier": 1.0}
    return {"label": "NEUTRAL", "risk_off": False, "spy_pct": round(ref, 2),
            "note": f"index {ref:+.1f}% — mixed tape", "r_multiplier": 1.15}


def relative_worker(spike: Dict[str, Any], bench: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Name % vs SPY/QQQ day % — skip if bench wasn't fetched this scan."""
    bench = bench or {}
    pct = _num(spike.get("pct"))
    spy = _opt_num(bench.get("SPY"))
    qqq = _opt_num(bench.get("QQQ"))
    if spy is None and qqq is None:
        return {"score": 0, "notes": [], "veto": [], "skipped": True, "vs_spy": None}
    ref = spy if spy is not None else qqq
    rel = pct - float(ref)
    notes: List[str] = []
    score = 0
    label = "SPY" if spy is not None else "QQQ"
    if rel >= 2.0:
        score = 2
        notes.append(f"{rel:+.1f}pp vs {label} today")
    elif rel <= -2.0:
        notes.append(f"lagging {label} ({rel:+.1f}pp) — may be beta, not a runner")
    else:
        notes.append(f"in line with {label} ({rel:+.1f}pp)")
    return {
        "score": score,
        "notes": notes,
        "veto": [],
        "skipped": False,
        "vs_spy": round(rel, 2) if spy is not None else None,
        "spy_pct": spy,
        "qqq_pct": qqq,
    }


def clock_worker() -> Dict[str, Any]:
    """RTH + premarket + after-hours are first-class. Overnight still labels last print."""
    session = "UNKNOWN"
    rth = False
    extended = False
    try:
        from zoneinfo import ZoneInfo

        now = datetime.now(ZoneInfo("America/New_York"))
        mins = now.hour * 60 + now.minute
        weekday = now.weekday() < 5
        rth = weekday and (9 * 60 + 30) <= mins < (16 * 60)
        pre = weekday and (4 * 60) <= mins < (9 * 60 + 30)
        ah = weekday and (16 * 60) <= mins < (20 * 60)
        overnight = weekday and (mins >= 20 * 60 or mins < 4 * 60)
        if rth:
            session = "RTH"
        elif pre:
            session = "PREMARKET"
            extended = True
        elif ah:
            session = "AFTER_HOURS"
            extended = True
        elif overnight:
            session = "OVERNIGHT"
            extended = True  # still read last AH print / Yahoo delayed
        elif weekday:
            session = "CLOSED"
        else:
            session = "WEEKEND"
    except Exception:
        session = "UNKNOWN"
    active = rth or extended
    notes = [f"session {session}"]
    if session == "PREMARKET":
        notes.append("premarket tape live — volume-before-price matters most")
    elif session == "AFTER_HOURS":
        notes.append("after-hours tape live — delayed Yahoo, thinner book")
    elif session == "OVERNIGHT":
        notes.append("overnight — grading last AH print until premarket 4:00 ET")
    return {
        "score": 1 if active else 0,
        "notes": notes,
        "veto": [],
        "session": session,
        "rth": rth,
        "extended": extended,
    }


def _fetch_bench_day_pct() -> Dict[str, float]:
    """One SPY + QQQ % this scan (prefers pre/AH print when outside RTH)."""
    out: Dict[str, float] = {}
    t0 = time.time()
    try:
        import yfinance as yf
    except Exception:
        return out
    clock = clock_worker()
    sess = str(clock.get("session") or "").upper()
    for sym in ("SPY", "QQQ"):
        if time.time() - t0 > 3.5:
            break
        try:
            t = yf.Ticker(sym)
            fi = _fast_map(getattr(t, "fast_info", None))
            last = _num(fi.get("lastPrice") or fi.get("last_price"))
            prev = _num(
                fi.get("previousClose") or fi.get("previous_close") or fi.get("regularMarketPreviousClose")
            )
            try:
                info = t.info or {}
                if isinstance(info, dict):
                    pre_px = _num(info.get("preMarketPrice"))
                    post_px = _num(info.get("postMarketPrice"))
                    if sess == "PREMARKET" and pre_px > 0:
                        last = pre_px
                    elif sess in ("AFTER_HOURS", "OVERNIGHT") and post_px > 0:
                        last = post_px
                    if prev <= 0:
                        prev = _num(info.get("previousClose") or info.get("regularMarketPreviousClose"))
            except Exception:
                pass
            if last > 0 and prev > 0:
                out[sym] = round((last - prev) / prev * 100.0, 2)
        except Exception:
            continue
    return out


def setup_manager(
    klass: Optional[Dict[str, Any]],
    pre: Dict[str, Any],
    extension: Dict[str, Any],
) -> Dict[str, Any]:
    """Is this a runner structure (PRE coil vs already extended spike)."""
    if not klass:
        return {"ok": False, "structure": "NONE", "notes": ["no runner structure"], "score": 0, "veto": ["skip"]}
    if extension.get("too_late"):
        return {
            "ok": False,
            "structure": "TOO_LATE",
            "notes": ["already extended — skip chase"],
            "score": 0,
            "veto": list(extension.get("veto") or []),
        }
    level = str(klass.get("level") or "")
    if level == "PRE":
        return {
            "ok": True,
            "structure": "PRE_COIL",
            "notes": ["volume-before-price coil — still before the pop"],
            "score": 3,
            "veto": [],
        }
    if level == "BUILDING":
        leftover = bool(extension.get("leftover"))
        return {
            "ok": True,
            "structure": "EXTENDED_SPIKE" if leftover else "BUILDING_RUN",
            "notes": ["already moving — leftover, not the first print"] if leftover else ["building run"],
            "score": 2,
            "veto": [],
        }
    return {
        "ok": True,
        "structure": "HOT_LEFTOVER",
        "notes": ["HOT leftover — typical leftover is small"],
        "score": 1,
        "veto": [],
    }


def timing_manager(level: str) -> Dict[str, Any]:
    """Buy now / buy dip / skip chase."""
    lvl = str(level or "")
    if lvl == "PRE":
        return {"action": "BUY_NOW", "notes": ["buy on the quiet tape, not after it rips"], "score": 2, "veto": []}
    if lvl == "BUILDING":
        return {"action": "BUY_DIP", "notes": ["buy a pullback, not the high"], "score": 1, "veto": []}
    return {"action": "SKIP_CHASE", "notes": ["HOT is late — wait a dip or pass"], "score": 0, "veto": []}


def risk_manager(
    veto: Dict[str, Any],
    liq: Dict[str, Any],
    squeeze: Dict[str, Any],
    extension: Dict[str, Any],
) -> Dict[str, Any]:
    """Float too big, spread, halt, mega — DROP the name."""
    fatal: List[str] = list(veto.get("fatal") or [])
    for src in (liq, squeeze, extension):
        for v in src.get("veto") or []:
            if v not in fatal:
                fatal.append(v)
    drop = bool(fatal)
    return {"drop": drop, "fatal": fatal, "ok": not drop, "notes": fatal, "score": 0 if drop else 1, "veto": fatal}


def _fmt_px(px: float) -> str:
    x = _num(px)
    if x <= 0:
        return "—"
    if x < 1:
        return f"{x:.4f}"
    return f"{x:.2f}"


def direction_manager() -> str:
    """Long-only hunt. Never BUY_PUTS on this desk."""
    return "BUY"


def structure_manager(veto: Dict[str, Any]) -> bool:
    """False = drop name."""
    return not bool(veto.get("fatal"))


def _atr_pct(symbol: str, ticker: Any = None) -> Optional[float]:
    """Average true range as % of price, cached per symbol per day.

    ATR barely moves day to day, so one fetch per name per session is plenty —
    the cache keeps this off the per-pass request budget.
    """
    sym = str(symbol or "").upper().strip()
    if not sym:
        return None
    today = datetime.now().strftime("%Y-%m-%d")
    with _atr_lock:
        hit = _atr_cache.get(sym)
        if hit and hit[0] == today:
            return hit[1]

    val: Optional[float] = None
    try:
        import yfinance as yf

        t = ticker if ticker is not None else yf.Ticker(sym)
        h = t.history(period="1mo", interval="1d")
        if h is not None and len(h) >= 6:
            h = h.tail(14)
            px = _num(h["Close"].iloc[-1])
            prev = h["Close"].shift(1)
            tr = (h["High"] - h["Low"]).combine((h["High"] - prev).abs(), max).combine(
                (h["Low"] - prev).abs(), max
            )
            atr = _num(tr.tail(10).mean())
            if px > 0 and atr > 0:
                val = atr / px * 100.0
    except Exception:
        val = None

    with _atr_lock:
        _atr_cache[sym] = (today, val)
        if len(_atr_cache) > 800:
            for k in [k for k, v in _atr_cache.items() if v[0] != today][:400]:
                _atr_cache.pop(k, None)
    return val


def _dip_and_chase(spot: float, high: float, low: float) -> Tuple[float, float]:
    """Pullback zone + a 'don't chase through here' print from the day's range."""
    px = max(spot, 0.01)
    hi = high if high > 0 else 0.0
    lo = low if low > 0 else 0.0
    chase = hi if hi > px else px * 1.03
    if lo > 0 and lo < px:
        dip = max(lo, px * 0.97)
        if hi > lo:
            # BUILDING/HOT: prefer a dip inside today's range, not the low of a dump.
            mid = lo + 0.55 * (px - lo)
            dip = max(lo, min(px * 0.99, mid))
    else:
        dip = px * 0.97
    return round(dip, 4 if px < 1 else 2), round(chase, 4 if px < 1 else 2)


def _vol_scale(atr_pct: Optional[float]) -> float:
    """Fit the target to how far the name actually travels.

    The level percentages below were written for an archetypal mover with a ~7%
    ATR. Applied flat, the same +12% base is trivial for a 25% ATR microcap and
    near-unreachable for a 2.5% ATR name — which is why low-vol tickets sat open
    forever and never graded either way.

    Deliberately ATR and not today's high-low: session range is meaningless in
    premarket and at 9:31, and a merely quiet day would shrink a real mover's
    target for no reason.
    """
    atr = _num(atr_pct)
    if atr <= 0:
        return 1.0
    return max(0.45, min(1.80, atr / ATR_BASELINE_PCT))


def _classify(
    spike: Dict[str, Any],
    squeeze: Dict[str, Any],
    ctx: Dict[str, Any],
    pre: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    pct = _num(spike.get("pct"))
    rvol = _num(spike.get("rvol"))
    float_m = squeeze.get("float_m")
    short_pct = squeeze.get("short_pct")
    mktcap = squeeze.get("mktcap") if squeeze.get("mktcap") is not None else ctx.get("mktcap")
    spot = _num(ctx.get("spot"))
    pre = pre or {}

    if _too_big_to_squeeze(float_m, mktcap):
        return None

    spike_level = None
    if pct >= 12.0 and rvol >= 5.0 and pct < TOO_LATE_PCT:
        spike_level = "HOT"
    elif pct >= 5.0 and rvol >= 2.0 and pct < TOO_LATE_PCT:
        spike_level = "BUILDING"

    squeeze_level = None
    squeezeable = float_m is not None and float_m < SQUEEZE_FLOAT_MAX_M
    strong_rvol_cheap = rvol >= 3.0 and spot < 10.0
    if squeezeable:
        if (short_pct is not None and short_pct >= 15.0) or strong_rvol_cheap:
            squeeze_level = "BUILDING"
        if float_m < 10.0 and pct < TOO_LATE_PCT:
            if (short_pct is not None and short_pct >= 20.0) or rvol >= 5.0:
                squeeze_level = "HOT"
    elif float_m is None and strong_rvol_cheap and rvol >= PRE_UNKNOWN_FLOAT_RVOL:
        if short_pct is None or short_pct >= 10.0:
            squeeze_level = "BUILDING"

    # PRE: not extended yet, AND volume-before-price plus a second independent tell
    pre_level = None
    secondary = list(pre.get("secondary_tells") or [])
    pre_ok = (
        bool(pre.get("still_quiet"))
        and _num(pre.get("score")) >= PRE_MIN_SCORE
        and bool(pre.get("volume_before_price"))
        and len(secondary) >= 1
        and _pre_float_ok(float_m, short_pct, rvol)
    )
    if not spike_level and not (squeeze_level == "HOT") and pre_ok:
        pre_level = "PRE"
        if squeeze_level == "BUILDING" and pct < PRE_MAX_PCT:
            squeeze_level = None  # keep it on the PRE board, not "already squeezing"

    if not spike_level and not squeeze_level and not pre_level:
        return None

    if pre_level and not spike_level:
        play_type = "SQUEEZE" if pre.get("coiled") and squeezeable else "SPIKE"
        if squeezeable and (short_pct or 0) >= 15:
            play_type = "SQUEEZE"
        return {
            "play_type": play_type,
            "level": "PRE",
            "spike_level": None,
            "squeeze_level": None,
            "pre_score": int(pre.get("score") or 0),
        }

    if spike_level and squeeze_level:
        play_type = "BOTH"
        level = "HOT" if "HOT" in (spike_level, squeeze_level) else "BUILDING"
    elif spike_level:
        play_type = "SPIKE"
        level = spike_level
    else:
        play_type = "SQUEEZE"
        level = squeeze_level
    return {
        "play_type": play_type,
        "level": level,
        "spike_level": spike_level,
        "squeeze_level": squeeze_level,
        "pre_score": int(pre.get("score") or 0),
    }


def _independent_tells(
    klass: Dict[str, Any],
    pre: Dict[str, Any],
    spike: Dict[str, Any],
    squeeze: Dict[str, Any],
    relative: Dict[str, Any],
) -> List[str]:
    """Real independent tells only — max 5. Never pad with slogans."""
    tells: List[str] = []
    level = str(klass.get("level") or "")
    rvol = _num(spike.get("rvol"))
    if pre.get("volume_before_price") or (level == "PRE" and rvol >= 1.5):
        tells.append("volume leading price")
    elif rvol >= 2.0:
        tells.append("elevated RVOL")
    for key, label in (
        ("vol_expand", "5m volume expanding"),
        ("higher_lows", "higher lows"),
        ("coil", "coil / tight range"),
        ("gap_hold", "gap holding"),
    ):
        if key in (pre.get("secondary_tells") or []):
            tells.append(label)
    if level != "PRE":
        if _num(spike.get("gap_pct")) >= 3.0 and "gap holding" not in tells:
            tells.append("gap")
        if _num(spike.get("accel_5m")) >= 2.0:
            tells.append("5m acceleration")
    float_m = squeeze.get("float_m")
    short_pct = squeeze.get("short_pct")
    if float_m is not None and float_m < SQUEEZE_FLOAT_MAX_M:
        tells.append("small float")
    elif short_pct is not None and short_pct >= 15.0 and float_m is not None and float_m < PRE_FLOAT_SHORT_MAX_M:
        tells.append("short interest loaded")
    # The trapped-shorts tell. Crowding without a narrow exit is just crowding.
    dtc = _opt_num(squeeze.get("days_to_cover"))
    if dtc is not None and dtc >= 5.0:
        tells.append(f"{dtc:.1f} days for shorts to cover")
    if (relative or {}).get("score", 0) >= 2 and relative.get("notes"):
        tells.append(str(relative["notes"][0]))
    out: List[str] = []
    for t in tells:
        if t not in out:
            out.append(t)
        if len(out) >= 5:
            break
    return out


def _confidence(level: str, n_tells: int, halt_risk: bool = False) -> int:
    """0–100 from tell agreement. Capped — never 95% theater.
    PRE 2 tells ~45–60; 4+ tells ~65–75.
    """
    n = max(0, int(n_tells))
    lvl = str(level or "")
    if lvl == "PRE":
        table = {0: 28, 1: 38, 2: 52, 3: 60, 4: 70, 5: 74}
        conf = table.get(n, 74)
    elif lvl == "BUILDING":
        table = {0: 30, 1: 38, 2: 48, 3: 56, 4: 62, 5: 66}
        conf = table.get(n, 66)
    else:
        conf = 32 + min(n, 4) * 4  # HOT is late
    if halt_risk:
        conf -= 8
    if n <= 1:
        conf = min(conf, 42)
    return max(18, min(int(conf), 78))


def _evidence_copy(
    klass: Dict[str, Any],
    spike: Dict[str, Any],
    squeeze: Dict[str, Any],
    pre: Optional[Dict[str, Any]],
    liq: Dict[str, Any],
    ctx: Dict[str, Any],
    relative: Optional[Dict[str, Any]] = None,
    clock: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:
    """Plain-English evidence paragraph + one-line tell. Never 'BEFORE THE POP'."""
    pre = pre or {}
    notes = set(pre.get("notes") or [])
    rvol = _num(spike.get("rvol"))
    pct = _num(spike.get("pct"))
    gap = _num(spike.get("gap_pct"))
    float_m = squeeze.get("float_m")
    short_pct = squeeze.get("short_pct")
    level = str(klass.get("level") or "")
    parts: List[str] = []

    if rvol >= 1.5 and abs(pct) < PRE_MAX_PCT:
        parts.append(
            f"Volume is {rvol:.1f}x normal while price is only {pct:+.1f}% "
            "(tape waking up before the move)."
        )
    elif rvol >= 1.4:
        parts.append(f"Volume is {rvol:.1f}x normal with price {pct:+.1f}% today.")
    elif abs(pct) >= 0.4:
        parts.append(f"Price is {pct:+.1f}% vs yesterday.")

    if "5m volume expanding" in notes:
        parts.append("5-minute volume is expanding vs the open.")
    if "5m higher lows" in notes:
        parts.append("Last three 5-minute bars are making higher lows.")
    if "first break of tight range" in notes:
        parts.append("Tight range just broke the high.")
    elif "range coiled" in notes:
        parts.append("Range is still tight (coiled).")
    if "gap" in " ".join(notes) or (2.0 <= gap <= 12.0 and pct < PRE_MAX_PCT and pct >= 0):
        if gap >= 2:
            parts.append(f"Gap {gap:+.1f}% is still holding.")

    if float_m is not None and float_m < SQUEEZE_FLOAT_MAX_M:
        bit = f"Float is {float_m:.1f}M"
        if short_pct is not None and short_pct >= 10:
            bit += f" with {short_pct:.0f}% short"
        parts.append(bit + ".")
    elif short_pct is not None and short_pct >= 15 and float_m is not None and float_m < PRE_FLOAT_SHORT_MAX_M:
        parts.append(f"Short interest is {short_pct:.0f}% of a {float_m:.0f}M float.")

    if liq.get("halt_risk"):
        parts.append("Wide 5-minute range — halt risk.")

    if relative and not relative.get("skipped") and relative.get("notes"):
        parts.append(str(relative["notes"][0]) + ".")
    if clock and clock.get("session") and clock.get("session") not in ("RTH", "UNKNOWN"):
        parts.append(f"Session is {clock.get('session')} — still scanning, delayed Yahoo.")

    if level == "BUILDING" and pct >= 5:
        parts.append("Already moving — leftover only, not the first print.")
    elif level == "HOT":
        parts.append("Extended: typical leftover is small.")

    paragraph = " ".join(parts).strip() or "Tape tell is weak — skip."
    tell_line = parts[0] if parts else paragraph
    return paragraph, tell_line


def _run_plan(
    klass: Dict[str, Any],
    spike: Dict[str, Any],
    squeeze: Dict[str, Any],
    spot: float,
    why: str,
    high: float = 0.0,
    low: float = 0.0,
    tell_list: Optional[List[str]] = None,
    halt_risk: bool = False,
    clock: Optional[Dict[str, Any]] = None,
    timing: Optional[Dict[str, Any]] = None,
    atr_pct: Optional[float] = None,
) -> Dict[str, Any]:
    """Boss ticket: tells, bands, buy/when/sell, confidence. Not a share-count card."""
    level = str(klass.get("level") or "")
    play = str(klass.get("play_type") or "SPIKE")
    pct_now = _num(spike.get("pct"))
    rvol = _num(spike.get("rvol"))
    last = max(_num(spot), 0.01)
    dip, chase = _dip_and_chase(last, _num(high), _num(low))
    fail_px = dip
    lo = _num(low)
    if lo > 0:
        fail_px = min(dip, lo) if dip > 0 else lo
    # Widen a structural stop that sits inside one average daily range. On a 35%
    # ATR name a 1% stop gets taken out by noise before the thesis is tested,
    # which is how a hopeless ticket ends up advertising 10:1 reward/risk.
    atr_abs = last * _num(atr_pct) / 100.0
    if atr_abs > 0:
        floor_px = last - MIN_STOP_ATR * atr_abs
        if fail_px > floor_px:
            fail_px = max(floor_px, last * 0.05)
    last_s, dip_s, chase_s = _fmt_px(last), _fmt_px(dip), _fmt_px(chase)
    fail_s = _fmt_px(fail_px)
    timing = timing or timing_manager(level)
    action = str(timing.get("action") or "")
    if level == "PRE":
        typ_pct, stretch_pct = 12.0, 35.0
        window = "before the pop"
        leftover_note = "if volume keeps leading price"
        buy = f"Buy near {last_s}, not chase if it rips through {chase_s}"
        when = "Before the pop — while the coil holds. Get filled on the quiet tape, not after it already runs."
    elif level == "BUILDING":
        typ_pct, stretch_pct = 10.0, 25.0
        window = "already moving"
        leftover_note = "leftover in the move — not the first print"
        buy = f"Buy a dip near {dip_s} (last {last_s}). Do not buy the high / chase through {chase_s}"
        when = f"Already moving. Buy only a pullback to {dip_s} — skip if you would be paying the high."
    else:
        typ_pct, stretch_pct = 5.0, 15.0
        window = "extended"
        leftover_note = "HOT is late; typical leftover is small"
        buy = f"Do not buy the high ({last_s}). Wait for a pullback toward {dip_s}, or skip"
        when = "HOT is late. Wait for a pullback, or pass — this is not a chase."
    if play in ("SQUEEZE", "BOTH"):
        typ_pct *= 1.35
        stretch_pct *= 1.5
    vscale = _vol_scale(atr_pct)
    typ_pct *= vscale
    stretch_pct *= vscale
    typ_px = round(last * (1.0 + typ_pct / 100.0), 4 if last < 1 else 2)
    stretch_px = round(last * (1.0 + stretch_pct / 100.0), 4 if last < 1 else 2)
    fail_px = round(fail_px, 4 if last < 1 else 2)
    if play == "SQUEEZE":
        thesis = "Squeeze / cover-driven pop"
    elif play == "BOTH":
        thesis = "Spike + squeeze structure"
    else:
        thesis = "Volume spike / gap-and-go"
    why_plain = (why or leftover_note).strip()
    tell_line = why_plain.split(".")[0].strip()
    if tell_line and not tell_line.endswith("."):
        tell_line += "."
    typ_pct_r = round(typ_pct, 0)
    stretch_pct_r = round(stretch_pct, 0)
    tells_n = len(tell_list or [])
    conf = _confidence(level, tells_n, halt_risk=halt_risk)
    agree = f"{tells_n}/5 tells"
    band = (
        f"base +{typ_pct_r:.0f}% to {_fmt_px(typ_px)} · "
        f"stretch +{stretch_pct_r:.0f}% to {_fmt_px(stretch_px)} · "
        f"invalidation {fail_s}"
    )
    invalidation = f"Thesis dead below {fail_s} (dip / day's low)"
    sell = (
        f"Potential sell: base {_fmt_px(typ_px)} (+{typ_pct_r:.0f}%) · "
        f"stretch {_fmt_px(stretch_px)} (+{stretch_pct_r:.0f}%)"
    )
    sess = (clock or {}).get("session")
    sess_bit = f" Session {sess}." if sess and sess not in ("UNKNOWN",) else ""
    honesty = (
        "Delayed Yahoo — not a live fill, not a guarantee the name pops. "
        f"{agree} agree ({conf}). Shares, not 0DTE. Does not override SPY Boss.{sess_bit}"
    )
    telegram = (
        f"{level} {{sym}} · {conf}\n"
        f"The tell: {why_plain}\n"
        f"Band: {band}\n"
        f"Buy: {buy}\n"
        f"When: {when}\n"
        f"Sell: {sell}\n"
        f"{invalidation}\n"
        f"{honesty}"
    )
    scenarios = {
        "base": {"px": typ_px, "pct": typ_pct_r, "label": f"typical {_fmt_px(typ_px)} (+{typ_pct_r:.0f}%)"},
        "stretch": {"px": stretch_px, "pct": stretch_pct_r, "label": f"stretch {_fmt_px(stretch_px)} (+{stretch_pct_r:.0f}%)"},
        "fail": {"px": fail_px, "label": invalidation},
    }
    prediction_line = f"buy {last_s} → base {_fmt_px(typ_px)} · {conf}"
    return {
        "thesis": thesis,
        "window": window,
        "why_plain": why_plain,
        "tells": why_plain,
        "tell_list": list(tell_list or []),
        "tell_n": tells_n,
        "tell_line": tell_line or why_plain,
        "already_pct": round(pct_now, 1),
        "typical_pct": typ_pct_r,
        "stretch_pct": stretch_pct_r,
        "typical_px": typ_px,
        "stretch_px": stretch_px,
        "fail_px": fail_px,
        "invalidation": invalidation,
        "invalidation_px": fail_px,
        "r_target": (
            round((typ_px - last) / (last - fail_px), 2)
            if last > fail_px > 0 else None
        ),
        "target_atrs": (
            round((typ_px - last) / last * 100.0 / _num(atr_pct), 1)
            if _num(atr_pct) > 0 and last > 0 else None
        ),
        "atr_pct": round(_num(atr_pct), 1) if _num(atr_pct) > 0 else None,
        "scenarios": scenarios,
        "band": band,
        "confidence": conf,
        "timing_action": action,
        "buy": buy,
        "when": when,
        "sell": sell,
        "buy_px": round(last, 4 if last < 1 else 2),
        "dip_px": dip,
        "chase_px": chase,
        "rvol": round(rvol, 1),
        "honesty": honesty,
        "prediction_line": prediction_line,
        "telegram": telegram,
    }


def format_big_run_telegram(row: Dict[str, Any]) -> str:
    """Tells + band + buy/when/sell + honesty. No size."""
    plan = row.get("plan") or {}
    tmpl = str(plan.get("telegram") or "")
    sym = str(row.get("symbol") or "")
    if tmpl:
        return tmpl.replace("{sym}", sym)
    lvl = str(row.get("level") or "")
    conf = plan.get("confidence")
    conf_s = f" · {conf}" if conf is not None else ""
    return (
        f"{lvl} {sym}{conf_s}\n"
        f"The tell: {plan.get('tells') or plan.get('why_plain') or row.get('why') or ''}\n"
        f"Band: {plan.get('band') or ''}\n"
        f"Buy: {plan.get('buy') or row.get('buy') or ''}\n"
        f"When: {plan.get('when') or ''}\n"
        f"Sell: {plan.get('sell') or ''}\n"
        f"{plan.get('invalidation') or ''}\n"
        f"{plan.get('honesty') or NOTE}"
    )


def boss_rank(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def key(r: Dict[str, Any]) -> Tuple:
        lvl_map = {"PRE": 3, "BUILDING": 2, "HOT": 1}
        lvl = lvl_map.get(str(r.get("level") or ""), 0)
        both = 1 if r.get("play_type") == "BOTH" else 0
        pre_s = _num(r.get("pre_score"))
        conf = _num((r.get("plan") or {}).get("confidence") or r.get("confidence"))
        grade_boost = _num(r.get("_grade_boost"))
        cat = r.get("catalyst") or {}
        cat_boost = 2 if cat.get("fresh") else (1 if cat.get("catalyst") else 0)
        return (lvl, pre_s, conf + grade_boost + cat_boost, both, _num(r.get("rvol")), -abs(_num(r.get("pct"))))

    kept: List[Dict[str, Any]] = []
    try:
        from big_run_grade import symbol_rank_adjust
    except Exception:
        symbol_rank_adjust = None  # type: ignore
    for r in rows:
        drop = False
        boost = 0
        if symbol_rank_adjust:
            try:
                boost, drop = symbol_rank_adjust(str(r.get("symbol") or ""))
            except Exception:
                boost, drop = 0, False
        if drop:
            continue
        r = dict(r)
        r["_grade_boost"] = boost
        kept.append(r)
    ranked = sorted(kept, key=key, reverse=True)
    for r in ranked:
        r.pop("_grade_boost", None)
    return ranked


def _stale_ticket(row: Any) -> bool:
    """Drop persisted tickets from the old share-count / BEFORE THE POP era."""
    if not isinstance(row, dict):
        return True
    sym = _norm_sym(row.get("symbol"))
    if _blocked(sym):
        return True
    if row.get("shares") is not None or row.get("notional") is not None:
        return True
    buy = str(row.get("buy") or "")
    buy_l = buy.lower()
    toks = buy.replace(",", " ").split()
    old_buy = len(toks) >= 2 and toks[0].upper() == "BUY" and toks[1].isdigit()
    if old_buy or "~$" in buy or "shares)" in buy_l or "~$500" in buy_l:
        return True
    plan = row.get("plan") or {}
    if not isinstance(plan, dict):
        return True
    if plan.get("typical_usd") is not None or plan.get("stretch_usd") is not None:
        return True
    why = str(plan.get("why_plain") or row.get("why") or "")
    if why.strip().upper().startswith("BEFORE THE POP"):
        return True
    if not plan.get("when") or not plan.get("sell"):
        return True
    if plan.get("confidence") is None or not plan.get("scenarios"):
        return True
    if _too_big_to_squeeze(row.get("float_m"), row.get("mktcap")):
        return True
    return False


def _clean_rows(rows: Any, limit: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in list(rows or []):
        if _stale_ticket(r):
            continue
        out.append(r)
        if len(out) >= limit:
            break
    return out


class SqueezeRadar:
    def __init__(self) -> None:
        self.universe: List[str] = []
        self.sweep: List[str] = []
        self.deep_batch: List[str] = []
        self._deep_cursor: int = 0
        self.last_alert: Dict[str, float] = {}
        self.alerts: List[Dict[str, Any]] = []
        self.spikes: List[Dict[str, Any]] = []
        self.squeezes: List[Dict[str, Any]] = []
        self.pres: List[Dict[str, Any]] = []
        self.last_scan: Optional[str] = None
        # Why a pass produced nothing. "No setup" on its own tells you nothing;
        # "22 of 45 blocked on after-hours spreads" tells you to go to bed.
        self.blocked: Dict[str, int] = {}
        self._block_tally: Dict[str, int] = {}
        self._lock = threading.Lock()
        self._bench: Dict[str, float] = {}
        self._bench_ts: float = 0.0
        self._load_state()

    def _blocked(self, reason: str) -> None:
        r = str(reason or "").strip() or "vetoed"
        with self._lock:
            self._block_tally[r] = self._block_tally.get(r, 0) + 1

    def _load_state(self) -> None:
        try:
            if not os.path.exists(STATE_FILE):
                return
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                st = json.load(f)
            self.alerts = _clean_rows(st.get("alerts"), 16)
            self.spikes = _clean_rows(st.get("spikes"), 12)
            self.squeezes = _clean_rows(st.get("squeezes"), 12)
            self.pres = _clean_rows(st.get("pres"), 12)
            kept = bool(self.alerts or self.pres or self.spikes or self.squeezes)
            self.last_scan = st.get("last_scan") if kept else None
            if not kept:
                self._persist()
        except Exception as e:
            logger.debug(f"squeeze state load: {e}")

    def _persist(self) -> None:
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "alerts": self.alerts[:20],
                        "spikes": self.spikes[:12],
                        "squeezes": self.squeezes[:12],
                        "pres": self.pres[:12],
                        "last_scan": self.last_scan,
                        "mode": "big_run",
                    },
                    f,
                    indent=2,
                )
        except Exception:
            pass

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            alerts = _clean_rows(self.alerts, 16)
            spikes = _clean_rows(self.spikes, 12)
            squeezes = _clean_rows(self.squeezes, 12)
            pres = _clean_rows(self.pres, 12)
            last_scan = self.last_scan
            uni = list(self.universe)
            sweep = list(self.sweep)
            deep = list(self.deep_batch)
            blocked = dict(self.blocked)
        if len(alerts) != len(self.alerts) or len(pres) != len(self.pres):
            with self._lock:
                self.alerts = alerts
                self.spikes = spikes
                self.squeezes = squeezes
                self.pres = pres
                self._persist()
        primary_pre = next((a for a in alerts if a.get("level") == "PRE"), None)
        primary_move = next((a for a in alerts if a.get("level") == "BUILDING"), None) or next(
            (a for a in alerts if a.get("level") == "HOT"), None
        )
        primary = primary_pre or primary_move
        also = [a for a in alerts if not primary or a.get("symbol") != primary.get("symbol")][:5]
        try:
            from big_run_grade import grades_today

            grades = grades_today()
        except Exception:
            grades = {"hits": 0, "misses": 0, "open": 0, "n": 0, "line": "Predictions today: none yet — empty is honest", "items": []}
        # The denominator: what a random comparable name does over the same
        # horizon. Without it a hit rate is a number with nothing to beat.
        base = {}
        try:
            import base_rate as _br

            data = _br.get()
            k = grades.get("median_target_atrs")
            base = {
                "curve": (data or {}).get("curve") or {},
                "windows": (data or {}).get("windows"),
                "symbols": (data or {}).get("symbols"),
                "target_atrs": k,
                "probability": _br.probability(k, data),
                "verdict": _br.verdict(
                    grades.get("win_rate"), k, int(grades.get("settled") or 0), data
                ),
            }
        except Exception as e:
            logger.debug(f"base rate: {e}")
        sweep_n = len(sweep) if sweep else len(uni)
        deep_n = len(deep) if deep else len(uni)
        return {
            "mode": "big_run",
            "note": NOTE,
            "last_scan": last_scan,
            "universe_size": sweep_n,
            "sweep_size": sweep_n,
            "deep_size": deep_n,
            "universe": sweep[:80] if sweep else uni,
            "deep_batch": deep,
            "blocked": blocked,
            "base_rate": base,
            "regime": regime_worker(self._bench),
            "primary": primary,
            "primary_pre": primary_pre,
            "primary_move": primary_move,
            "also": also,
            "pres": pres,
            "spikes": spikes,
            "squeezes": squeezes,
            "alerts": alerts,
            "grades_today": grades,
        }

    def _bench_cached(self) -> Dict[str, float]:
        now = time.time()
        with self._lock:
            if self._bench and now - self._bench_ts < 600:
                return dict(self._bench)
        bench = _fetch_bench_day_pct()
        with self._lock:
            if bench:
                self._bench = dict(bench)
                self._bench_ts = now
                return dict(self._bench)
            return dict(self._bench)

    def _row(
        self,
        symbol: str,
        ctx: Dict[str, Any],
        spike: Dict[str, Any],
        squeeze: Dict[str, Any],
        liq: Dict[str, Any],
        klass: Dict[str, Any],
        pre: Optional[Dict[str, Any]] = None,
        relative: Optional[Dict[str, Any]] = None,
        clock: Optional[Dict[str, Any]] = None,
        setup: Optional[Dict[str, Any]] = None,
        timing: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        pre = pre or {}
        relative = relative or {}
        clock = clock or clock_worker()
        timing = timing or timing_manager(str(klass.get("level") or ""))
        spot = round(_num(ctx.get("spot")), 4 if _num(ctx.get("spot")) < 1 else 2)
        why, tell_line = _evidence_copy(klass, spike, squeeze, pre, liq, ctx, relative, clock)
        tell_list = _independent_tells(klass, pre, spike, squeeze, relative)
        plan = _run_plan(
            klass,
            spike,
            squeeze,
            _num(ctx.get("spot")),
            why,
            high=_num(ctx.get("high")),
            low=_num(ctx.get("low")),
            tell_list=tell_list,
            halt_risk=bool(liq.get("halt_risk")),
            clock=clock,
            timing=timing,
            atr_pct=ctx.get("atr_pct"),
        )
        plan["tell_line"] = tell_line
        plan["tells"] = why
        plan["telegram"] = str(plan.get("telegram") or "").replace("{sym}", symbol)
        buy = plan.get("buy") or f"Buy near {_fmt_px(spot)}"
        return {
            "symbol": symbol,
            "play_type": klass["play_type"],
            "level": klass["level"],
            "spot": spot,
            "pct": spike.get("pct"),
            "rvol": spike.get("rvol"),
            "float_m": squeeze.get("float_m"),
            "short_pct": squeeze.get("short_pct"),
            "days_to_cover": squeeze.get("days_to_cover"),
            "si_change_pct": squeeze.get("si_change_pct"),
            "atr_pct": ctx.get("atr_pct"),
            "mktcap": squeeze.get("mktcap"),
            "buy": buy,
            "when": plan.get("when"),
            "sell": plan.get("sell"),
            "buy_at": plan.get("buy_px") or spot,
            "why": why,
            "time": datetime.now().isoformat(),
            "gap_pct": spike.get("gap_pct"),
            "accel_5m": spike.get("accel_5m"),
            "volume": liq.get("volume"),
            "halt_risk": bool(liq.get("halt_risk")),
            "side": "SHARES",
            "pre_score": int(klass.get("pre_score") or 0),
            "confidence": plan.get("confidence"),
            "prediction_line": plan.get("prediction_line"),
            "session": clock.get("session"),
            "setup": (setup or {}).get("structure"),
            "plan": plan,
        }

    def _scan_one(
        self,
        symbol: str,
        bench: Optional[Dict[str, Any]] = None,
        clock: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        clock = clock or clock_worker()
        ctx = _fetch_ctx(symbol, session=clock.get("session"))
        if not ctx:
            self._blocked("no quote")
            return None
        ctx["session"] = ctx.get("session") or clock.get("session")
        spike = spike_worker(ctx)
        squeeze = squeeze_worker(ctx)
        liq = liquidity_worker(ctx)
        pre = pre_worker(ctx, spike, squeeze)
        extension = extension_worker(spike)
        relative = relative_worker(spike, bench or {})
        veto = veto_worker(ctx, spike, squeeze, liq)
        risk = risk_manager(veto, liq, squeeze, extension)
        if risk.get("drop") or not structure_manager(veto):
            for f in veto.get("fatal") or ["vetoed"]:
                self._blocked(str(f).split("—")[0].strip())
            return None
        klass = _classify(spike, squeeze, ctx, pre)
        setup = setup_manager(klass, pre, extension)
        if not setup.get("ok") or not klass:
            self._blocked("not a spike" if not klass else "setup not clean")
            return None
        timing = timing_manager(str(klass.get("level") or ""))
        if klass.get("level") == "PRE":
            extra = pre.get("notes") or []
            spike = dict(spike)
            spike["notes"] = list(extra) + list(spike.get("notes") or [])
        now = time.time()
        with self._lock:
            last = float(self.last_alert.get(symbol) or 0)
        row = self._row(symbol, ctx, spike, squeeze, liq, klass, pre, relative, clock, setup, timing)
        try:
            from catalyst_news import attach as _cat_attach

            row = _cat_attach(row, ctx.get("name"))
        except Exception:
            pass
        regime = regime_worker(bench)
        row["regime"] = regime.get("label")
        min_r = MIN_R_TARGET * _num(regime.get("r_multiplier"), 1.0)
        r_t = _opt_num((row.get("plan") or {}).get("r_target"))
        if r_t is not None and r_t < min_r:
            self._blocked(f"pays under {min_r:.2g}R ({r_t:.2f}R)")
            return None
        if now - last < COOLDOWN_SEC:
            row["_fresh"] = False
            return row
        row["_fresh"] = True
        with self._lock:
            self.last_alert[symbol] = now
        return row

    def ticket_from_ctx(
        self,
        symbol: str,
        ctx: Dict[str, Any],
        bench: Optional[Dict[str, Any]] = None,
        clock: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Build a ticket from an already-fetched ctx (tests). No cooldown."""
        clock = clock or clock_worker()
        spike = spike_worker(ctx)
        squeeze = squeeze_worker(ctx)
        liq = liquidity_worker(ctx)
        pre = pre_worker(ctx, spike, squeeze)
        extension = extension_worker(spike)
        relative = relative_worker(spike, bench or {})
        veto = veto_worker(ctx, spike, squeeze, liq)
        risk = risk_manager(veto, liq, squeeze, extension)
        if risk.get("drop") or not structure_manager(veto):
            return None
        klass = _classify(spike, squeeze, ctx, pre)
        setup = setup_manager(klass, pre, extension)
        if not setup.get("ok") or not klass:
            return None
        timing = timing_manager(str(klass.get("level") or ""))
        row = self._row(symbol, ctx, spike, squeeze, liq, klass, pre, relative, clock, setup, timing)
        try:
            from catalyst_news import attach as _cat_attach

            row = _cat_attach(row, ctx.get("name"))
        except Exception:
            pass
        return row

    def scan_pass(self) -> List[Dict[str, Any]]:
        """Sweep Yahoo movers market-wide, then deep-grade a rotating slice."""
        hits: List[Dict[str, Any]] = []
        try:
            sweep = _sweep_market()
            with self._lock:
                cursor = int(self._deep_cursor or 0)
            deep, next_cursor = _deep_slice(sweep, cursor, DEEP_PER_PASS)
            # Always deep-scan the hottest names this pass + rotate through the rest
            hottest = [s for _, s in sweep[: max(24, DEEP_PER_PASS // 3)]]
            universe: List[str] = []
            for s in hottest + deep:
                if s not in universe:
                    universe.append(s)
            universe = universe[:DEEP_PER_PASS]

            clock = clock_worker()
            bench = self._bench_cached()
            with self._lock:
                self._block_tally = {}
                self.sweep = [s for _, s in sweep]
                self.deep_batch = list(universe)
                self.universe = list(self.sweep)  # UI "names" = full sweep
                self._deep_cursor = next_cursor

            rows: List[Dict[str, Any]] = []
            for i, sym in enumerate(universe):
                try:
                    hit = self._scan_one(sym, bench=bench, clock=clock)
                    if hit:
                        rows.append(hit)
                except Exception as e:
                    logger.debug(f"big run {sym}: {e}")
                if i < len(universe) - 1:
                    time.sleep(SCAN_PAUSE_SEC)
            hits = [r for r in rows if r.get("_fresh")]
            fresh_syms = {r.get("symbol") for r in hits}
            ranked = boss_rank(rows)
            for r in ranked:
                r.pop("_fresh", None)
            board = ranked[:6]
            try:
                from big_run_grade import upsert_from_rows

                upsert_from_rows(board)
            except Exception as e:
                logger.debug(f"big run grade: {e}")
            try:
                import base_rate as _br

                # Sample the population the desk actually fishes in. Cached per
                # day, so the requests are spent once, not every pass.
                _br.get([s for _, s in sweep][: _br.MAX_SYMBOLS])
            except Exception as e:
                logger.debug(f"base rate refresh: {e}")
            spikes = [r for r in ranked if r.get("level") != "PRE" and r.get("play_type") in ("SPIKE", "BOTH")]
            squeezes = [r for r in ranked if r.get("level") != "PRE" and r.get("play_type") in ("SQUEEZE", "BOTH")]
            pres = [r for r in ranked if r.get("level") == "PRE"]
            with self._lock:
                self.alerts = ranked[:16]
                self.spikes = spikes[:12]
                self.squeezes = squeezes[:12]
                self.pres = pres[:12]
                self.last_scan = datetime.now().isoformat()
                self.blocked = dict(
                    sorted(self._block_tally.items(), key=lambda kv: -kv[1])[:6]
                )
                self._persist()
            out = [r for r in board if r.get("symbol") in fresh_syms]
            for r in out:
                logger.info(
                    f"Big Run {r.get('level')} {r.get('play_type')} {r.get('symbol')} {r.get('buy')} {r.get('why')}"
                )
            logger.info(
                f"Big Run sweep={len(sweep)} deep={len(universe)} cursor={next_cursor} "
                f"session={clock.get('session')}"
            )
            return out
        except Exception as e:
            logger.debug(f"big run scan_pass: {e}")
            try:
                with self._lock:
                    self.last_scan = datetime.now().isoformat()
            except Exception:
                pass
            return []


squeeze_radar = SqueezeRadar()
