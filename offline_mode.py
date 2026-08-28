"""
Stage A offline desk.

Last-good snapshot on disk. Never invent live prices. Boss sits out on stale
quotes. Paper stays DISARMED.

Flags (read live from the environment — not cached at import):

  FLOWSCOUT_OFFLINE=1   explicit offline: no Yahoo / Polygon / IBKR fetches
  YAHOO_DISABLED=1      test hook: treat Yahoo as unreachable (same sit-out)
  FLOWSCOUT_OFFLINE_SNAPSHOT  optional path for the JSON snapshot file

A runtime latch also trips after live Yahoo failures so a no-network boot
without the flag still stays up instead of hanging the WS loop.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_SNAPSHOT = Path("offline_snapshot.json")
_FAILURES_TO_LATCH = 2
_RETRY_SECONDS = 300.0

_lock = threading.Lock()
_yahoo_unreachable = False
_fail_count = 0
_latched_at = 0.0
_last_retry_at = 0.0


def _truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def snapshot_path() -> Path:
    raw = (os.getenv("FLOWSCOUT_OFFLINE_SNAPSHOT") or "").strip()
    return Path(raw) if raw else DEFAULT_SNAPSHOT


def forced_offline() -> bool:
    """Explicit operator / test flag — never retry live fetches."""
    return _truthy("FLOWSCOUT_OFFLINE") or _truthy("YAHOO_DISABLED")


def live_market_blocked() -> bool:
    """True when the desk must not hit Yahoo/Polygon/IBKR."""
    if forced_offline():
        return True
    with _lock:
        if not _yahoo_unreachable:
            return False
        # Occasional retry only when the operator did not force offline
        now = time.time()
        if _last_retry_at and (now - _last_retry_at) >= _RETRY_SECONDS:
            return False
        return True


def mark_live_success() -> None:
    global _yahoo_unreachable, _fail_count, _latched_at
    with _lock:
        _yahoo_unreachable = False
        _fail_count = 0
        _latched_at = 0.0


def mark_live_failure(reason: str = "") -> None:
    """Count a Yahoo/network miss. Latch after a couple of hits so we stop hanging."""
    global _yahoo_unreachable, _fail_count, _latched_at, _last_retry_at
    with _lock:
        _fail_count += 1
        _last_retry_at = time.time()
        if _fail_count >= _FAILURES_TO_LATCH and not _yahoo_unreachable:
            _yahoo_unreachable = True
            _latched_at = time.time()
            logger.warning(
                "OFFLINE latch — live Yahoo unreachable (%s). "
                "Serving last-good snapshot as STALE; Boss will sit out.",
                (reason or "no network")[:160],
            )


def begin_live_retry() -> None:
    """Called just before an allowed retry so the next miss can re-latch."""
    global _last_retry_at
    with _lock:
        _last_retry_at = time.time()


def payload_is_stale(data: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(data, dict):
        return bool(live_market_blocked())
    if data.get("offline") or data.get("stale") or data.get("stale_paint"):
        return True
    freshness = str(data.get("data_freshness") or "").upper()
    if freshness in ("OFFLINE", "STALE", "CACHED"):
        return True
    if live_market_blocked():
        return True
    return False


def _jsonable(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            key = str(k)
            # Drop theater / huge blobs — keep Stage A desk paint
            if key.startswith("_") and key not in ("_cached", "_cache_age_seconds"):
                continue
            if key in (
                "bot_predictions",
                "ml_prediction",
                "ensemble_prediction",
                "confidence_html",
                "advanced_analysis",
            ):
                continue
            try:
                out[key] = _jsonable(v)
            except Exception:
                out[key] = str(v)
        return out
    if isinstance(obj, (list, tuple)):
        return [_jsonable(x) for x in list(obj)[:400]]
    try:
        json.dumps(obj)
        return obj
    except Exception:
        return str(obj)


def empty_offline_flow(symbol: str = "SPY") -> Dict[str, Any]:
    return {
        "symbol": symbol,
        "stock_price": 0,
        "regular_close": 0,
        "all_calls": [],
        "all_puts": [],
        "calls": {"total_volume": 0, "total_open_interest": 0, "by_strike": []},
        "puts": {"total_volume": 0, "total_open_interest": 0, "by_strike": []},
        "flow_metrics": {
            "total_call_volume": 0,
            "total_put_volume": 0,
            "call_put_ratio": 1.0,
            "flow_direction": "NEUTRAL",
        },
        "strikes": {"calls_by_strike": [], "puts_by_strike": []},
        "data_source": "offline_snapshot",
        "data_freshness": "OFFLINE",
        "data_quality": "offline_stale",
        "offline": True,
        "stale": True,
        "live": False,
        "snapshot_mode": True,
        "options_available": False,
        "yahoo_cooling": False,
        "lite_tick": False,
    }


def sit_out_boss(last: Optional[Dict[str, Any]] = None, *, reason: Optional[str] = None) -> Dict[str, Any]:
    """
    Reuse last-good Boss paint so the card is not blank, but never allow a new
    ticket. Action is NO_TRADE. last_live_action keeps the previous verb visible.
    """
    base = dict(last) if isinstance(last, dict) else {}
    last_action = base.get("last_live_action") or base.get("action") or "NO_TRADE"
    vetoes = [v for v in (base.get("veto_flags") or []) if v]
    if "OFFLINE_STALE" not in vetoes:
        vetoes.append("OFFLINE_STALE")
    hard = [v for v in (base.get("hard_vetoes") or []) if v]
    if "OFFLINE_STALE" not in hard:
        hard.append("OFFLINE_STALE")
    scenarios = []
    for s in base.get("scenarios") or []:
        if not isinstance(s, dict):
            continue
        row = dict(s)
        row["executable"] = False
        row["advisory_only"] = True
        row["primary"] = False
        scenarios.append(row)
    sit_reason = reason or (
        "OFFLINE — sitting out. Quotes are last-good / stale, not live. "
        "Boss will not open paper from this tape."
    )
    prior = (base.get("reason") or "").strip()
    if prior and "OFFLINE" not in prior and sit_reason not in prior:
        sit_reason = f"{sit_reason} Last live: {last_action}. {prior}"[:500]
    painted = {
        **base,
        "boss": True,
        "action": "NO_TRADE",
        "last_live_action": last_action,
        "stale_paint": True,
        "offline": True,
        "stale": True,
        "can_auto_paper": False,
        "executable": False,
        "paper_armed": False,
        "primary_scenario": None,
        "data_quality": "offline_stale",
        "venue": base.get("venue") or "local_sim",
        "fill_model": base.get("fill_model") or "buy_ask_sell_bid",
        "veto_flags": vetoes,
        "hard_vetoes": hard,
        "scenarios": scenarios,
        "reason": sit_reason[:500],
        "timestamp": datetime.now().isoformat(),
    }
    # Keep last contract on the card as advisory (do not blank the strike line)
    if painted.get("contract") and isinstance(painted["contract"], dict):
        c = dict(painted["contract"])
        painted["contract"] = c
    return painted


def annotate_stale(
    flow: Optional[Dict[str, Any]],
    *,
    symbol: str = "SPY",
    captured_at: Optional[str] = None,
    snapshot_age_sec: Optional[float] = None,
) -> Dict[str, Any]:
    """Mark a payload so the UI cannot mistake it for a fresh live print."""
    out = dict(flow) if isinstance(flow, dict) else empty_offline_flow(symbol)
    out["symbol"] = out.get("symbol") or symbol
    out["offline"] = True
    out["stale"] = True
    out["live"] = False
    out["snapshot_mode"] = True
    out["data_freshness"] = "OFFLINE"
    out["data_quality"] = "offline_stale"
    src = str(out.get("data_source") or "")
    if src.lower() not in ("offline_snapshot", "offline"):
        out["data_source"] = "offline_snapshot"
        if src:
            out["last_live_source"] = src
    out["yahoo_cooling"] = False
    if captured_at:
        out["snapshot_captured_at"] = captured_at
    if snapshot_age_sec is not None:
        out["data_age_seconds"] = int(max(0, snapshot_age_sec))
        out["_cache_age_seconds"] = int(max(0, snapshot_age_sec))
        out["_cached"] = True
    last_boss = out.get("boss_decision") if isinstance(out.get("boss_decision"), dict) else None
    out["boss_decision"] = sit_out_boss(last_boss)
    paper = out.get("paper_boss") if isinstance(out.get("paper_boss"), dict) else {}
    paper = dict(paper)
    paper["armed"] = False
    paper["offline"] = True
    paper["can_auto_paper"] = False
    out["paper_boss"] = paper
    return out


class OfflineDesk:
    """Persist / load last-good SPY flow + Boss paint."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self._path_override = path

    @property
    def path(self) -> Path:
        return self._path_override or snapshot_path()

    def load(self) -> Optional[Dict[str, Any]]:
        path = self.path
        try:
            if not path.exists():
                return None
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return None
            return raw
        except Exception as e:
            logger.warning("offline snapshot load failed: %s", e)
            return None

    def save(self, payload: Dict[str, Any]) -> None:
        path = self.path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
            tmp.replace(path)
        except Exception as e:
            logger.warning("offline snapshot save failed: %s", e)

    def capture(
        self,
        symbol: str,
        flow: Dict[str, Any],
        boss: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        if payload_is_stale(flow):
            return
        if not isinstance(flow, dict) or float(flow.get("stock_price") or 0) <= 0:
            return
        now = datetime.now().isoformat()
        blob = {
            "saved_at": now,
            "captured_at": now,
            "captured_ts": time.time(),
            "symbol": symbol or "SPY",
            "stock_price": flow.get("stock_price"),
            "flow": _jsonable(flow),
            "boss_decision": _jsonable(boss or flow.get("boss_decision") or {}),
        }
        if extra:
            blob.update(_jsonable(extra))
        self.save(blob)
        mark_live_success()
        logger.info(
            "Saved offline snapshot for %s @ %s",
            symbol,
            blob.get("stock_price"),
        )

    def serve_flow(self, symbol: str = "SPY") -> Dict[str, Any]:
        snap = self.load()
        age = None
        captured_at = None
        flow = None
        if snap:
            captured_at = snap.get("captured_at") or snap.get("saved_at")
            ts = snap.get("captured_ts")
            if ts:
                try:
                    age = max(0.0, time.time() - float(ts))
                except (TypeError, ValueError):
                    age = None
            flow = snap.get("flow") if isinstance(snap.get("flow"), dict) else None
            if flow is None and float(snap.get("stock_price") or 0) > 0:
                flow = {k: v for k, v in snap.items() if k not in ("saved_at", "captured_at", "captured_ts")}
            if isinstance(snap.get("boss_decision"), dict) and flow is not None:
                flow = dict(flow)
                flow["boss_decision"] = snap["boss_decision"]
        if not flow:
            out = empty_offline_flow(symbol)
            out["boss_decision"] = sit_out_boss(
                None,
                reason="OFFLINE — no live quotes and no last-good snapshot yet. Desk is up; Boss sits out.",
            )
            return out
        return annotate_stale(flow, symbol=symbol, captured_at=captured_at, snapshot_age_sec=age)


offline_desk = OfflineDesk()


def capture_live_snapshot(
    symbol: str,
    flow: Dict[str, Any],
    boss: Optional[Dict[str, Any]] = None,
) -> None:
    try:
        offline_desk.capture(symbol, flow, boss=boss)
    except Exception as e:
        logger.debug("capture_live_snapshot: %s", e)


def serve_offline_flow(symbol: str = "SPY") -> Dict[str, Any]:
    return offline_desk.serve_flow(symbol)


def hydrate_last_good() -> Optional[Dict[str, Any]]:
    """Load disk snapshot for in-memory last-good on boot."""
    return offline_desk.load()


def status_dict() -> Dict[str, Any]:
    snap = offline_desk.load()
    age = None
    if snap and snap.get("captured_ts"):
        try:
            age = round(max(0.0, time.time() - float(snap["captured_ts"])), 1)
        except (TypeError, ValueError):
            age = None
    blocked = live_market_blocked()
    return {
        "offline": blocked,
        "forced": forced_offline(),
        "yahoo_disabled": _truthy("YAHOO_DISABLED"),
        "flag": _truthy("FLOWSCOUT_OFFLINE"),
        "live_fetches": not blocked,
        "data_freshness": "OFFLINE" if blocked else "LIVE",
        "has_snapshot": bool(snap and (snap.get("flow") or snap.get("stock_price"))),
        "snapshot_age_sec": age,
        "snapshot_captured_at": (snap or {}).get("captured_at") or (snap or {}).get("saved_at"),
        "snapshot_path": str(offline_desk.path),
        "latched": _yahoo_unreachable,
        "note": (
            "Last-good snapshot only — not live prints. Boss NO_TRADE. Paper DISARMED."
            if blocked
            else "Live delayed Yahoo path."
        ),
    }
