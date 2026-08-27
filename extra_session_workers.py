"""Extra 0DTE workers: clock (when) and tape (call vs put volume).

Not prediction bots. They feed Timing + Direction managers.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo


def clock_worker(now: Optional[datetime] = None) -> Dict[str, Any]:
    """RTH clock — when a new 0DTE ticket is even allowed."""
    try:
        et = now.astimezone(ZoneInfo("America/New_York")) if now else datetime.now(
            ZoneInfo("America/New_York")
        )
    except Exception:
        et = datetime.now()
    minutes = et.hour * 60 + et.minute
    open_m, close_m = 9 * 60 + 30, 16 * 60
    to_close = close_m - minutes
    veto: List[str] = []
    if minutes < open_m or minutes >= close_m:
        phase = "OUTSIDE_RTH"
        action = "NO_TRADE"
        veto.append("OUTSIDE_RTH_OR_NO_OPEN")
    elif minutes < open_m + 5:
        phase = "OPEN_PRINT"
        action = "NO_TRADE"
        veto.append("OPENING_BAR_FORMING")
    elif to_close <= 45:
        phase = "LATE"
        action = "NO_TRADE"
        veto.append("TOO_LATE_0DTE")
    elif to_close <= 90:
        phase = "AFTERNOON"
        action = "CAUTION"
    else:
        phase = "RTH"
        action = "ALLOW"
    return {
        "bot_type": "CLOCK_WORKER",
        "action": action,
        "phase": phase,
        "minutes_to_close": to_close,
        "veto_flags": veto,
        "confidence": 80 if action == "ALLOW" else 40,
        "reason": f"{phase} · {to_close}m to close",
    }


def tape_worker(calls: Optional[List[Dict]] = None, puts: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """Call vs put volume on the chain — a Direction vote, not a standalone bot."""
    calls = calls or []
    puts = puts or []

    def _vol(rows: List[Dict]) -> float:
        s = 0.0
        for r in rows:
            try:
                s += float(r.get("volume") or r.get("Volume") or 0)
            except (TypeError, ValueError):
                pass
        return s

    cv, pv = _vol(calls), _vol(puts)
    tot = cv + pv
    ratio = (cv / pv) if pv > 0 else (99.0 if cv > 0 else 1.0)
    action = "NO_TRADE"
    conf = 30
    if tot < 500:
        reason = "thin tape"
    elif ratio >= 1.45:
        action = "BUY_CALLS"
        conf = min(78, int(50 + (ratio - 1) * 20))
        reason = f"call volume {ratio:.2f}x puts"
    elif ratio <= 1 / 1.45:
        action = "BUY_PUTS"
        conf = min(78, int(50 + (1 / max(ratio, 0.01) - 1) * 20))
        reason = f"put volume {1 / max(ratio, 0.01):.2f}x calls"
    else:
        reason = f"balanced tape C/P {ratio:.2f}"
    return {
        "bot_type": "TAPE_WORKER",
        "action": action,
        "confidence": conf,
        "call_vol": round(cv),
        "put_vol": round(pv),
        "cp_ratio": round(ratio, 2) if ratio < 50 else None,
        "veto_flags": [],
        "reason": reason,
    }


def vwap_proxy_worker(symbol: str, spot: float) -> Dict[str, Any]:
    """Price vs EMA21 as a value line (true VWAP needs tape; we don't fake it)."""
    action = "NO_TRADE"
    conf = 30
    vs = None
    reason = "no EMA21 yet"
    try:
        from technical_indicators import technical_indicators as ti

        ema21 = float(ti.get_ema(symbol, 21) or 0)
        if ema21 > 0 and spot > 0:
            vs = (spot - ema21) / ema21 * 100.0
            if vs >= 0.15:
                action = "BUY_CALLS"
                conf = 58
                reason = f"price {vs:+.2f}% vs EMA21"
            elif vs <= -0.15:
                action = "BUY_PUTS"
                conf = 58
                reason = f"price {vs:+.2f}% vs EMA21"
            else:
                reason = "hugging EMA21"
    except Exception as e:
        reason = str(e)
    return {
        "bot_type": "VALUE_WORKER",
        "action": action,
        "confidence": conf,
        "vs_ema21_pct": round(vs, 2) if vs is not None else None,
        "veto_flags": [],
        "reason": reason,
        "note": "EMA21 stand-in for VWAP — not a volume-weighted print",
    }
