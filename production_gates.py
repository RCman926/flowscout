"""
Production gates for 0DTE Boss — sit out when the book is sick.

Not a second order Boss. Raises the bar or blocks new tickets.
Does not flatten opens. Does not invent P&L.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


def odte_trade_bar() -> Dict[str, Any]:
    """floor = min Boss confidence to fire; block=True means no new ticket."""
    floor = 58
    block = False
    flags: List[str] = []
    notes: List[str] = []

    try:
        from trade_health import trade_health

        st = (trade_health.last or {}).get("status") or "HEALTHY"
        if st == "UNHEALTHY":
            block = True
            flags.append("TRADE_HEALTH_UNHEALTHY")
            notes.append("Trade Health UNHEALTHY — no new 0DTE")
        elif st == "DEGRADED":
            floor = max(floor, 66)
            notes.append("Trade Health DEGRADED — higher bar")
    except Exception:
        pass

    try:
        from cloud_runtime import is_cloud_mode, yahoo_is_throttled

        if is_cloud_mode():
            floor = max(floor, 70)
            flags.append("CLOUD_DELAYED_YAHOO")
            notes.append("Cloud delayed Yahoo — sit out more; quotes are not live")
            if yahoo_is_throttled():
                block = True
                flags.append("CLOUD_YAHOO_THROTTLED")
                notes.append("Yahoo cooling/throttled — NO_TRADE until a fresh chain")
    except Exception:
        pass

    try:
        from shadow_learning_engine import shadow_learning_engine as eng

        s = eng.summary()
        wins = int(s.get("wins_today") or 0)
        losses = int(s.get("losses_today") or 0)
        open_n = int(s.get("open_count") or 0)
        if open_n >= 4:
            block = True
            flags.append("TOO_MANY_OPEN_SHADOWS")
            notes.append(f"{open_n} shadows already open")
        if losses >= 3 and losses > wins:
            floor = max(floor, 72)
            notes.append(f"shadow {wins}W/{losses}L — raise floor to {floor}")
        if losses >= 5 and wins == 0:
            block = True
            flags.append("SHADOW_BLOOD_DAY")
            notes.append("five losses no wins — sit out new 0DTE")
    except Exception:
        pass

    return {
        "floor": floor,
        "block": block,
        "flags": flags,
        "notes": notes,
    }
