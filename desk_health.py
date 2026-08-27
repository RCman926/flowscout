"""
Desk Health — workers / managers / boss for the live dashboard.

Checks that the server, numbers, and loops are actually working.
Safe AUTOFIX only (restart a dead updater, nudge a stale Big Run scan).
Everything else is REPORT so a human (or the UI) can see it.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

STATE_FILE = "desk_health_state.json"
TELEGRAM_COOLDOWN = 15 * 60
SQUEEZE_STALE_SEC = 12 * 60
BROADCAST_STALE_SEC = 90
SHADOW_STALE_SEC = 180


def _age_iso(iso: Optional[str]) -> Optional[float]:
    if not iso:
        return None
    try:
        s = str(iso).replace("Z", "")
        dt = datetime.fromisoformat(s)
        return max(0.0, time.time() - dt.timestamp())
    except Exception:
        return None


def worker_http() -> Dict[str, Any]:
    return {
        "ok": True,
        "source": "http",
        "note": "process is serving (this worker ran)",
    }


def _clock() -> Dict[str, Any]:
    try:
        from market_hours_detector import session_clock

        return session_clock()
    except Exception:
        return {"session": "UNKNOWN", "closed": False, "rth": True, "label": "—"}


def worker_spy_loop(ctx: Dict[str, Any], clock: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    clock = clock or _clock()
    alive = bool(ctx.get("updater_alive"))
    last = ctx.get("last_broadcast_ts")
    age = (time.time() - float(last)) if last else None
    ws_n = int(ctx.get("ws_clients") or 0)
    stale_lim = 8 * 60 if clock.get("closed") else (180 if clock.get("extended") else BROADCAST_STALE_SEC)
    issues = []
    notes = []
    if not alive:
        issues.append("SPY background updater task is dead")
    if ws_n > 0 and age is not None and age > stale_lim:
        issues.append(f"last WS broadcast {int(age)}s ago with clients connected")
    elif clock.get("closed") and age is not None:
        notes.append(f"{clock.get('label')} — slower Yahoo cadence is expected, not a crash")
    return {
        "ok": alive and not (ws_n > 0 and age is not None and age > stale_lim),
        "updater_alive": alive,
        "ws_clients": ws_n,
        "broadcast_age_sec": round(age, 1) if age is not None else None,
        "issues": issues,
        "notes": notes,
    }


def worker_squeeze(ctx: Dict[str, Any], clock: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    clock = clock or _clock()
    issues = []
    notes = []
    last_scan = None
    uni = 0
    try:
        from squeeze_radar import squeeze_radar

        snap = squeeze_radar.snapshot()
        last_scan = snap.get("last_scan")
        uni = int(snap.get("universe_size") or snap.get("sweep_size") or 0)
    except Exception as e:
        issues.append(f"squeeze snapshot failed: {e}")
    age = _age_iso(last_scan)
    task_alive = bool(ctx.get("squeeze_task_alive", True))
    stale_lim = 45 * 60 if clock.get("closed") else SQUEEZE_STALE_SEC
    if not task_alive:
        issues.append("Big Run scan task is dead")
    if age is not None and age > stale_lim and not clock.get("closed"):
        issues.append(f"Big Run last scan {int(age)}s ago (stale)")
    elif clock.get("closed") and age is not None and age > stale_lim:
        notes.append(f"Big Run last scan {int(age // 60)}m ago — weekend/overnight pause is expected")
    if last_scan is None:
        if clock.get("closed"):
            notes.append("Big Run has not scanned yet this closed session")
        else:
            issues.append("Big Run has not completed a scan yet")
    return {
        "ok": not issues,
        "last_scan": last_scan,
        "scan_age_sec": round(age, 1) if age is not None else None,
        "universe_size": uni,
        "task_alive": task_alive,
        "issues": issues,
        "notes": notes,
    }


def worker_shadow() -> Dict[str, Any]:
    issues = []
    nums: Dict[str, Any] = {}
    try:
        from shadow_learning_engine import shadow_learning_engine

        rep = shadow_learning_engine.today_report() or {}
        for k in ("wins_today", "losses_today", "open_count", "win_rate_today", "pnl_today_usd"):
            v = rep.get(k)
            nums[k] = v
            if isinstance(v, float) and v != v:
                issues.append(f"shadow {k} is NaN")
        if rep.get("error"):
            issues.append(str(rep.get("error")))
    except Exception as e:
        issues.append(f"shadow today_report failed: {e}")
    return {"ok": not issues, "numbers": nums, "issues": issues}


def worker_sources() -> Dict[str, Any]:
    issues = []
    notes = []
    names = []
    try:
        from multi_source_flow_tracker import multi_source_tracker

        names = list(getattr(multi_source_tracker, "available_sources", None) or [])
        if not names:
            issues.append("no data sources listed")
        elif "yfinance" not in [str(n).lower() for n in names] and "yahoo" not in str(names).lower():
            if not any("yfin" in str(n).lower() for n in names):
                issues.append("yfinance not in available_sources")
        try:
            from yahoo_throttle import yahoo_throttle

            st = yahoo_throttle.stats()
            cool = float(st.get("backoff_remaining_seconds") or 0)
            if cool > 0:
                notes.append(f"Yahoo cooling {int(cool)}s — holding last quote (Stage A, not a dead site)")
        except Exception:
            pass
    except Exception as e:
        issues.append(f"source check: {e}")
    return {"ok": not issues, "available": names, "issues": issues, "notes": notes}


def worker_files() -> Dict[str, Any]:
    issues = []
    root = os.path.dirname(os.path.abspath(__file__))
    html = os.path.join(root, "zerodte_client_enhanced.html")
    if not os.path.isfile(html):
        issues.append("zerodte_client_enhanced.html missing")
    return {"ok": not issues, "issues": issues}


def structure_manager(workers: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Can the desk serve at all?"""
    fatal = []
    if not workers.get("http", {}).get("ok", True):
        fatal.append("http worker down")
    if not workers.get("files", {}).get("ok", True):
        fatal.extend(workers["files"].get("issues") or [])
    if not workers.get("spy_loop", {}).get("updater_alive", True):
        fatal.append("SPY updater dead")
    ok = not fatal
    return {"ok": ok, "fatal": fatal, "manager": "STRUCTURE"}


def integrity_manager(workers: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Are numbers / scans honest?"""
    warns = []
    for name in ("spy_loop", "squeeze", "shadow", "sources"):
        w = workers.get(name) or {}
        warns.extend(w.get("issues") or [])
    return {"ok": not warns, "warnings": warns, "manager": "INTEGRITY"}


class DeskHealthBoss:
    def __init__(self) -> None:
        self.last: Dict[str, Any] = {}
        self.fixes: List[Dict[str, Any]] = []
        self.reports: List[Dict[str, Any]] = []
        self._last_telegram = 0.0
        self._last_nudge_squeeze = 0.0

    def evaluate(self, ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ctx = ctx or {}
        clock = _clock()
        workers = {
            "http": worker_http(),
            "files": worker_files(),
            "spy_loop": worker_spy_loop(ctx, clock),
            "squeeze": worker_squeeze(ctx, clock),
            "shadow": worker_shadow(),
            "sources": worker_sources(),
        }
        structure = structure_manager(workers)
        integrity = integrity_manager(workers)

        actions: List[str] = []
        reports: List[str] = []
        notes: List[str] = []

        if not workers["spy_loop"].get("updater_alive"):
            actions.append("RESTART_UPDATER")
            reports.append("SPY updater task died — restarting")

        sq = workers["squeeze"]
        stale_lim = 45 * 60 if clock.get("closed") else SQUEEZE_STALE_SEC
        age = sq.get("scan_age_sec")
        stale = bool(not sq.get("task_alive")) or (
            age is not None and age > stale_lim and not clock.get("closed")
        )
        if stale and (time.time() - self._last_nudge_squeeze) > 8 * 60:
            actions.append("NUDGE_SQUEEZE")
            reports.append("Big Run scan stale — nudging a scan pass")

        for w in workers.values():
            for issue in w.get("issues") or []:
                if issue not in reports:
                    reports.append(issue)
            for note in w.get("notes") or []:
                if note not in notes:
                    notes.append(note)

        if clock.get("closed"):
            notes.append(
                f"{clock.get('label')} — slower Yahoo / cooling APIs are the clock, not a dead site."
            )

        if not structure["ok"]:
            status = "UNHEALTHY"
        elif reports:
            status = "DEGRADED"
        elif clock.get("closed"):
            status = "CLOSED"
        else:
            status = "HEALTHY"

        snap = {
            "mode": "desk_health",
            "status": status,
            "clock": clock,
            "time": datetime.now().isoformat(),
            "workers": {
                k: {kk: vv for kk, vv in v.items() if kk != "numbers" or True}
                for k, v in workers.items()
            },
            "managers": {"structure": structure, "integrity": integrity},
            "actions": actions,
            "reports": reports[:12],
            "notes": notes[:8],
            "fixes": list(self.fixes[-8:]),
            "note": "Safe autofix only. CLOSED/overnight is the market clock, not a crash. Does not override SPY Boss.",
        }
        self.last = snap
        if reports:
            self.reports.append({"time": snap["time"], "status": status, "reports": reports[:8]})
            self.reports = self.reports[-40:]
        return snap

    def record_fix(self, action: str, detail: str, ok: bool) -> None:
        self.fixes.append(
            {
                "time": datetime.now().isoformat(),
                "action": action,
                "detail": detail,
                "ok": ok,
            }
        )
        self.fixes = self.fixes[-40:]
        if action == "NUDGE_SQUEEZE":
            self._last_nudge_squeeze = time.time()

    def should_telegram(self) -> bool:
        if (self.last or {}).get("status") in ("HEALTHY", "CLOSED"):
            return False
        if time.time() - self._last_telegram < TELEGRAM_COOLDOWN:
            return False
        self._last_telegram = time.time()
        return True


desk_health = DeskHealthBoss()
