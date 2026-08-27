"""Base rates for Big Run targets — the denominator the scoreboard was missing.

A hit rate on its own is decoration. If a target 1.5 ATR away gets reached by
45% of random comparable names inside the horizon anyway, then a 45% desk hit
rate is exactly zero skill. This module measures that denominator from history
so the desk's record can be compared against doing nothing clever at all.

Deliberately graded on forward *closes*, not intraday highs, because that is how
big_run_grade marks a ticket. A control group that measures something different
from the thing it controls for is worse than no control group.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

BASE_RATE_FILE = "big_run_base_rates.json"

HORIZON_DAYS = 5
ATR_WINDOW = 10
LOOKBACK = "8mo"
# Target distances we care about, in ATR units.
BUCKETS = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0)
MAX_SYMBOLS = 40

_lock = threading.Lock()


def _num(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        x = float(v)
        return default if x != x else x
    except (TypeError, ValueError):
        return default


def _day() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _load() -> Dict[str, Any]:
    if not os.path.exists(BASE_RATE_FILE):
        return {}
    try:
        with open(BASE_RATE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _save(payload: Dict[str, Any]) -> None:
    try:
        with open(BASE_RATE_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass


def _forward_atr_gains(hist: Any, horizon: int = HORIZON_DAYS) -> List[float]:
    """Best forward close over `horizon` sessions, in ATR units, per start day."""
    try:
        import pandas as pd  # noqa: F401
    except ImportError:
        return []
    try:
        if hist is None or len(hist) < ATR_WINDOW + horizon + 2:
            return []
        close = hist["Close"]
        prev = close.shift(1)
        tr = (hist["High"] - hist["Low"]).combine(
            (hist["High"] - prev).abs(), max
        ).combine((hist["Low"] - prev).abs(), max)
        atr = tr.rolling(ATR_WINDOW).mean()

        out: List[float] = []
        vals = close.values
        atr_vals = atr.values
        n = len(vals)
        for i in range(ATR_WINDOW, n - horizon):
            entry = _num(vals[i])
            a = _num(atr_vals[i])
            if entry <= 0 or a <= 0:
                continue
            atr_pct = a / entry * 100.0
            if atr_pct <= 0:
                continue
            fwd = vals[i + 1: i + 1 + horizon]
            if len(fwd) == 0:
                continue
            best = max(_num(x) for x in fwd)
            gain_pct = (best - entry) / entry * 100.0
            out.append(gain_pct / atr_pct)
        return out
    except Exception:
        return []


def measure(symbols: List[str], horizon: int = HORIZON_DAYS) -> Dict[str, Any]:
    """P(a target k ATR away is reached within the horizon) across a sample."""
    try:
        import yfinance as yf
    except ImportError:
        return {}

    syms = [str(s).upper().strip() for s in (symbols or []) if s][:MAX_SYMBOLS]
    gains: List[float] = []
    used = 0
    for sym in syms:
        try:
            h = yf.Ticker(sym).history(period=LOOKBACK, interval="1d")
            g = _forward_atr_gains(h, horizon)
            if g:
                gains.extend(g)
                used += 1
        except Exception:
            continue

    if not gains:
        return {}
    curve = {
        f"{k:.1f}": round(100.0 * sum(1 for g in gains if g >= k) / len(gains), 1)
        for k in BUCKETS
    }
    return {
        "day": _day(),
        "horizon": horizon,
        "symbols": used,
        "windows": len(gains),
        "curve": curve,
    }


def get(symbols: Optional[List[str]] = None, horizon: int = HORIZON_DAYS) -> Dict[str, Any]:
    """Cached per day. Recomputing hourly would spend requests for no new signal."""
    with _lock:
        cached = _load()
        if cached.get("day") == _day() and cached.get("curve"):
            return cached
    if not symbols:
        return _load()
    fresh = measure(symbols, horizon)
    if fresh:
        with _lock:
            _save(fresh)
        return fresh
    return _load()


def probability(k: Optional[float], data: Optional[Dict[str, Any]] = None) -> Optional[float]:
    """Base-rate probability for a target k ATR away, interpolated between buckets."""
    if k is None:
        return None
    data = data if data is not None else _load()
    curve = (data or {}).get("curve") or {}
    if not curve:
        return None
    pts = sorted((float(x), _num(v)) for x, v in curve.items())
    kk = _num(k)
    if kk <= pts[0][0]:
        return pts[0][1]
    if kk >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= kk <= x1 and x1 > x0:
            return round(y0 + (y1 - y0) * (kk - x0) / (x1 - x0), 1)
    return None


def verdict(desk_hit_pct: Optional[float], k: Optional[float], settled: int,
            data: Optional[Dict[str, Any]] = None) -> str:
    """Plain English on whether the desk beat doing nothing clever."""
    data = data if data is not None else _load()
    curve = (data or {}).get("curve") or {}
    if not curve:
        return "Base rate not measured yet — hit rate has no denominator"
    base = probability(k, data)
    if base is None:
        # Curve is built, there is just no live target to price against it.
        ref = probability(1.5, data)
        n = data.get("windows")
        return (
            f"Base rate ready on {n} historical windows — a 1.5 ATR target lands "
            f"{ref:.0f}% of the time. No open tickets to score yet"
        )
    ask = f"a {k:.1f} ATR target" if k is not None else "this target"
    if settled < 30 or desk_hit_pct is None:
        return (
            f"Random comparable names reach {ask} {base:.0f}% of the time. "
            f"Beat that and the desk has edge; {settled} settled so far"
        )
    # Two standard errors on a coin weighted at the base rate. Anything inside
    # that band is a sample too small to distinguish from luck, however good the
    # raw difference looks.
    p = base / 100.0
    se = 100.0 * (p * (1.0 - p) / settled) ** 0.5
    diff = desk_hit_pct - base
    head = f"Desk {desk_hit_pct:.0f}% vs base rate {base:.0f}% on {settled}"
    if abs(diff) < 2.0 * se:
        return f"{head} — inside noise (±{2.0 * se:.0f}pp), not distinguishable yet"
    if diff > 0:
        return f"{head} — beating random by {diff:.0f}pp"
    return f"{head} — worse than random by {abs(diff):.0f}pp"
