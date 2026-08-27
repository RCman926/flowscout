"""
Trade Health — workers / managers / boss for MONEY, not the webpage.

Separate from Desk Health. This stack watches shadow/paper trades:
stuck 0DTE, stale marks, one-sided streak, NaN P&L, arm mismatch.

Safe AUTOFIX only (never flatten a live ticket from here).
Most issues are REPORT so you can act.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

TELEGRAM_COOLDOWN = 10 * 60
STALE_MARK_SEC = 180
STUCK_0DTE_SEC = 45 * 60
OPEN_LOSS_WARN_PCT = -35.0
MAX_OPEN = 5


def _num(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        x = float(v)
        if x != x:
            return default
        return x
    except (TypeError, ValueError):
        return default


def worker_shadow_book() -> Dict[str, Any]:
    issues: List[str] = []
    opens: List[Dict[str, Any]] = []
    try:
        from shadow_learning_engine import shadow_learning_engine as eng

        opens = list(eng.open or [])
        now = time.time()
        calls = puts = 0
        stale = 0
        stuck = 0
        nan_pnl = 0
        deep = 0
        for t in opens:
            act = str(t.get("action") or "")
            if "PUT" in act:
                puts += 1
            else:
                calls += 1
            mark_ts = float(t.get("last_mark_ts") or t.get("entry_ts") or 0)
            age = now - mark_ts if mark_ts else None
            if age is not None and age > STALE_MARK_SEC:
                stale += 1
            hold = now - float(t.get("entry_ts") or 0)
            tenor = str(t.get("tenor") or "0DTE")
            if hold > STUCK_0DTE_SEC and "0DTE" in tenor.upper():
                stuck += 1
            pnl = t.get("last_pnl_pct")
            if pnl is None and t.get("last_mark") is not None:
                nan_pnl += 0
            try:
                if pnl is not None and float(pnl) != float(pnl):
                    nan_pnl += 1
                if pnl is not None and float(pnl) <= OPEN_LOSS_WARN_PCT:
                    deep += 1
            except (TypeError, ValueError):
                nan_pnl += 1
        closed = False
        try:
            from market_hours_detector import session_clock

            closed = bool(session_clock().get("closed"))
        except Exception:
            closed = False
        notes: List[str] = []
        if stale and not closed:
            issues.append(f"{stale} open shadow(s) not marked to bid in {STALE_MARK_SEC}s")
        elif stale and closed:
            notes.append(f"{stale} bid mark(s) paused overnight — not a dead book")
        if stuck:
            issues.append(f"{stuck} 0DTE shadow(s) open > {STUCK_0DTE_SEC // 60} min — expiry risk")
        if nan_pnl:
            issues.append(f"{nan_pnl} open P&L is NaN")
        if deep:
            issues.append(f"{deep} open past {OPEN_LOSS_WARN_PCT:.0f}% vs bid (stop should have fired)")
        if len(opens) > MAX_OPEN:
            issues.append(f"{len(opens)} shadows open (cap {MAX_OPEN})")
        return {
            "ok": not issues,
            "open": len(opens),
            "calls": calls,
            "puts": puts,
            "stale_marks": stale,
            "stuck_0dte": stuck,
            "issues": issues,
            "notes": notes,
        }
    except Exception as e:
        return {"ok": False, "open": 0, "issues": [f"shadow book: {e}"]}


def worker_graded_today() -> Dict[str, Any]:
    issues: List[str] = []
    try:
        from shadow_learning_engine import shadow_learning_engine as eng

        s = eng.summary()
        w = int(s.get("wins_today") or 0)
        l = int(s.get("losses_today") or 0)
        closed = int(s.get("closed_today") or 0)
        streak_side, streak_n = eng.consecutive_losses()
        if streak_n >= 2:
            issues.append(f"{streak_n} consecutive {streak_side or ''} losses — Boss should block that side")
        today = datetime.now().date().isoformat()
        closed_today = [t for t in (eng.closed or []) if str(t.get("exit_time") or "").startswith(today)]
        c_calls = sum(1 for t in closed_today if "CALL" in str(t.get("action") or ""))
        c_puts = sum(1 for t in closed_today if "PUT" in str(t.get("action") or ""))
        if closed >= 4 and c_puts == 0 and c_calls >= 4:
            issues.append("only CALLS graded today — two-sided Boss may be stuck")
        return {
            "ok": not issues,
            "wins": w,
            "losses": l,
            "closed": closed,
            "streak_side": streak_side,
            "streak_n": streak_n,
            "issues": issues,
        }
    except Exception as e:
        return {"ok": False, "issues": [f"graded today: {e}"]}


def worker_paper_arm() -> Dict[str, Any]:
    issues: List[str] = []
    armed = False
    paper_open = 0
    try:
        from paper_arm_state import paper_arm_state as arm

        armed = bool(arm and arm.armed)
    except Exception as e:
        issues.append(f"arm state: {e}")
    try:
        from paper_trading_engine import paper_trading_engine as pe

        if pe:
            paper_open = len(getattr(pe, "positions", None) or [])
    except Exception:
        pass
    if armed and paper_open > MAX_OPEN:
        issues.append(f"paper armed with {paper_open} positions")
    return {"ok": not issues, "armed": armed, "paper_open": paper_open, "issues": issues}


def worker_boss_side(ctx: Dict[str, Any]) -> Dict[str, Any]:
    issues: List[str] = []
    action = str(ctx.get("last_boss_action") or "")
    if action.startswith("BUY") and not (ctx.get("updater_alive", True)):
        issues.append("Boss last said BUY but SPY updater is dead — tickets may be stale")
    return {"ok": not issues, "last_action": action or None, "issues": issues}


def risk_manager(workers: Dict[str, Any]) -> Dict[str, Any]:
    fatal = []
    book = workers.get("book") or {}
    if book.get("stuck_0dte"):
        fatal.append("0DTE still open too long")
    if (book.get("open") or 0) > MAX_OPEN:
        fatal.append("too many open shadows")
    return {"ok": not fatal, "fatal": fatal, "manager": "TRADE_RISK"}


def integrity_manager(workers: Dict[str, Any]) -> Dict[str, Any]:
    warns = []
    for name in ("book", "graded", "paper"):
        warns.extend((workers.get(name) or {}).get("issues") or [])
    return {"ok": not warns, "warnings": warns, "manager": "TRADE_INTEGRITY"}


class TradeHealthBoss:
    def __init__(self) -> None:
        self.last: Dict[str, Any] = {}
        self.fixes: List[Dict[str, Any]] = []
        self._last_telegram = 0.0

    def evaluate(self, ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ctx = ctx or {}
        workers = {
            "book": worker_shadow_book(),
            "graded": worker_graded_today(),
            "paper": worker_paper_arm(),
            "boss": worker_boss_side(ctx),
        }
        risk = risk_manager(workers)
        integrity = integrity_manager(workers)
        reports: List[str] = []
        notes: List[str] = []
        for w in workers.values():
            for i in w.get("issues") or []:
                if i not in reports:
                    reports.append(i)
            for n in w.get("notes") or []:
                if n not in notes:
                    notes.append(n)
        actions: List[str] = []
        # Never auto-flatten. Safe actions only.
        if workers["book"].get("stale_marks"):
            actions.append("REPORT_STALE_MARKS")
        if workers["book"].get("stuck_0dte"):
            actions.append("REPORT_STUCK_0DTE")

        clock = {}
        try:
            from market_hours_detector import session_clock

            clock = session_clock()
        except Exception:
            clock = {}

        if not risk["ok"]:
            status = "UNHEALTHY"
        elif reports:
            status = "DEGRADED"
        elif clock.get("closed"):
            status = "CLOSED"
        else:
            status = "HEALTHY"

        book = workers["book"]
        snap = {
            "mode": "trade_health",
            "status": status,
            "clock": clock,
            "priority": "MONEY — more important than desk/UI health",
            "time": datetime.now().isoformat(),
            "open": book.get("open"),
            "calls": book.get("calls"),
            "puts": book.get("puts"),
            "armed": workers["paper"].get("armed"),
            "wins": workers["graded"].get("wins"),
            "losses": workers["graded"].get("losses"),
            "workers": workers,
            "managers": {"risk": risk, "integrity": integrity},
            "actions": actions,
            "reports": reports[:12],
            "notes": notes[:8],
            "fixes": list(self.fixes[-8:]),
            "note": "Does not close trades automatically. Overnight CLOSED is the clock, not a crash. Stuck 0DTE still UNHEALTHY.",
        }
        self.last = snap
        return snap

    def record_fix(self, action: str, detail: str, ok: bool) -> None:
        self.fixes.append(
            {"time": datetime.now().isoformat(), "action": action, "detail": detail, "ok": ok}
        )
        self.fixes = self.fixes[-40:]

    def should_telegram(self) -> bool:
        if (self.last or {}).get("status") in ("HEALTHY", "CLOSED"):
            return False
        if time.time() - self._last_telegram < TELEGRAM_COOLDOWN:
            return False
        self._last_telegram = time.time()
        return True


trade_health = TradeHealthBoss()
