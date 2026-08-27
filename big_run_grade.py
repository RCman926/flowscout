"""
Big Run prediction grades — delayed Yahoo after the fact.

Persist tickets, then mark HIT_BASE / HIT_STRETCH / FAIL / OPEN vs later last.
No Sharpe, no fake win-rate theater from three-second prints.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

GRADE_FILE = "big_run_predictions.json"

# Big Run is shares on a swing plan, not 0DTE. Base/stretch targets routinely
# need more than one session, so a ticket stays live across days until it
# resolves or runs out of room.
HORIZON_DAYS = 5

# Terminal once reached. A target that printed is not un-printed by a later
# flush, and a broken ticket does not get to quietly reopen. VOID is for tickets
# written by a target model we no longer trust — discarded, never counted.
_TERMINAL = ("FAIL", "EXPIRED", "HIT_STRETCH", "VOID")
_RANK = {"OPEN": 0, "HIT_BASE": 2, "HIT_STRETCH": 3}

_lock = threading.Lock()


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


def _day(iso: Optional[str] = None) -> str:
    if iso:
        return str(iso)[:10]
    return datetime.now().strftime("%Y-%m-%d")


def r_multiple(entry: float, exit_px: float, fail_px: float) -> Optional[float]:
    """Result in units of the risk taken.

    A raw hit count says nothing about whether the wins pay for the losses.
    Expressing every outcome as a multiple of the distance to invalidation makes
    a 4% gain on a tight stop and a 12% gain on a loose one comparable.
    """
    entry, exit_px, fail_px = _num(entry), _num(exit_px), _num(fail_px)
    if entry <= 0 or fail_px <= 0 or fail_px >= entry:
        return None
    risk = entry - fail_px
    if risk <= 0:
        return None
    return round((exit_px - entry) / risk, 2)


def target_atrs(entry: float, target: float, atr_pct: Optional[float]) -> Optional[float]:
    """How many average daily ranges away the target sits.

    This is the sanity check that was missing: a target 5 ATR away in 5 sessions
    is a lottery ticket, and one 0.3 ATR away gets hit by noise and flatters the
    record. Both look identical as a plain percentage.
    """
    entry, target = _num(entry), _num(target)
    atr = _num(atr_pct)
    if entry <= 0 or target <= 0 or atr <= 0:
        return None
    move_pct = (target - entry) / entry * 100.0
    return round(move_pct / atr, 1)


def _weekdays_since(day: Optional[str], today: Optional[str] = None) -> int:
    """Sessions elapsed since a ticket opened. Weekends are not trading days."""
    try:
        a = datetime.strptime(str(day)[:10], "%Y-%m-%d").date()
        b = datetime.strptime(str(today or _day())[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return 0
    n = 0
    cur = a
    while cur < b:
        cur += timedelta(days=1)
        if cur.weekday() < 5:
            n += 1
    return n


def _age_days(rec: Dict[str, Any], today: Optional[str] = None) -> int:
    return _weekdays_since(rec.get("day"), today)


def _is_live(rec: Dict[str, Any], today: Optional[str] = None) -> bool:
    """Still working: unresolved and inside its horizon."""
    if str(rec.get("status") or "") in _TERMINAL:
        return False
    return _age_days(rec, today) <= HORIZON_DAYS


def _in_book(rec: Dict[str, Any], today: Optional[str] = None) -> bool:
    """Counts toward the rolling scoreboard."""
    return _age_days(rec, today) <= HORIZON_DAYS


def _load() -> List[Dict[str, Any]]:
    if not os.path.exists(GRADE_FILE):
        return []
    try:
        with open(GRADE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        rows = raw if isinstance(raw, list) else (raw.get("predictions") or [])
        return [r for r in rows if isinstance(r, dict)]
    except Exception:
        return []


def _save(rows: List[Dict[str, Any]]) -> None:
    try:
        with open(GRADE_FILE, "w", encoding="utf-8") as f:
            json.dump(rows[-400:], f, indent=2)
    except Exception:
        pass


def grade_vs_last(
    last: float,
    base_px: float,
    stretch_px: float,
    fail_px: float,
    prev_status: Optional[str] = None,
) -> str:
    """Grade a ticket, never downgrading a target that already printed."""
    prev = str(prev_status or "OPEN")
    if prev in _TERMINAL:
        return prev
    last = _num(last)
    if last <= 0:
        return prev
    if stretch_px > 0 and last >= stretch_px:
        return "HIT_STRETCH"
    if base_px > 0 and last >= base_px:
        return "HIT_BASE"
    if fail_px > 0 and last <= fail_px:
        # Base already banked — a later flush is a giveback, not a failed call.
        return prev if prev == "HIT_BASE" else "FAIL"
    return prev if _RANK.get(prev, 0) > 0 else "OPEN"


def upsert_from_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Record / refresh today's tickets. Grade vs current last. Returns grades_today."""
    today = _day()
    with _lock:
        store = _load()
        by_key: Dict[str, Dict[str, Any]] = {}
        for r in store:
            key = f"{str(r.get('symbol') or '').upper()}|{str(r.get('day') or '')}"
            # Discarded tickets are kept for audit but must not occupy the live
            # key, or a fresh ticket inherits VOID as its prior status and is
            # born dead.
            if r.get("status") == "VOID":
                key += "|void"
            by_key[key] = r

        # A name already working inside its horizon keeps its original ticket —
        # re-ticketing it every morning is what buried multi-day runs as
        # perpetual "open" and reset the entry we are grading against.
        live_key: Dict[str, str] = {}
        for key, r in by_key.items():
            if not _is_live(r, today):
                continue
            sym_r = str(r.get("symbol") or "").upper()
            cur = live_key.get(sym_r)
            if cur is None or str(by_key[cur].get("day") or "") < str(r.get("day") or ""):
                live_key[sym_r] = key

        for row in rows or []:
            if not isinstance(row, dict):
                continue
            sym = str(row.get("symbol") or "").upper().strip()
            if not sym:
                continue
            plan = row.get("plan") or {}
            scen = plan.get("scenarios") or {}
            base = scen.get("base") or {}
            stretch = scen.get("stretch") or {}
            fail = scen.get("fail") or {}
            last = _num(row.get("spot") or plan.get("buy_px"))
            base_px = _num(base.get("px") or plan.get("typical_px"))
            stretch_px = _num(stretch.get("px") or plan.get("stretch_px"))
            fail_px = _num(fail.get("px") or plan.get("fail_px") or plan.get("invalidation_px"))
            if last <= 0 or base_px <= 0:
                continue
            t0 = str(row.get("time") or datetime.now().isoformat())
            key = live_key.get(sym) or f"{sym}|{today}"
            prev = by_key.get(key)
            t0_last = _num(prev.get("t0_last")) if prev else last
            if t0_last <= 0:
                t0_last = last
            # A live ticket keeps the targets it was written with; only a brand
            # new ticket takes today's levels.
            if prev:
                base_px = _num(prev.get("base_px")) or base_px
                stretch_px = _num(prev.get("stretch_px")) or stretch_px
                fail_px = _num(prev.get("fail_px")) or fail_px
            status = grade_vs_last(
                last, base_px, stretch_px, fail_px, (prev or {}).get("status")
            )
            day = str((prev or {}).get("day") or today)
            best = max(_num((prev or {}).get("best_last")), last)
            atr = _num(row.get("atr_pct")) or _num((prev or {}).get("atr_pct"))
            rec = {
                "symbol": sym,
                "day": day,
                "t0": (prev or {}).get("t0") or t0,
                "t0_last": round(t0_last, 4 if t0_last < 1 else 2),
                "last": round(last, 4 if last < 1 else 2),
                "best_last": round(best, 4 if best < 1 else 2),
                "base_px": round(base_px, 4 if base_px < 1 else 2),
                "stretch_px": round(stretch_px, 4 if stretch_px < 1 else 2),
                "fail_px": round(fail_px, 4 if fail_px < 1 else 2) if fail_px > 0 else None,
                "level": row.get("level"),
                "status": status,
                "age_days": _weekdays_since(day, today),
                "horizon_days": HORIZON_DAYS,
                "atr_pct": round(atr, 1) if atr > 0 else None,
                "days_to_cover": row.get("days_to_cover") or (prev or {}).get("days_to_cover"),
                "target_atrs": target_atrs(t0_last, base_px, atr),
                "r_target": r_multiple(t0_last, base_px, fail_px),
                "r_now": r_multiple(t0_last, last, fail_px),
                "updated": datetime.now().isoformat(),
            }
            by_key[key] = rec
            live_key[sym] = key

        out = _expire(list(by_key.values()), today)
        _save(out)

    return _summary(out, today)


def _expire(rows: List[Dict[str, Any]], today: str) -> List[Dict[str, Any]]:
    """Close out tickets that ran out of horizon without resolving."""
    for r in rows:
        st = str(r.get("status") or "")
        if st in _TERMINAL:
            continue
        age = _age_days(r, today)
        r["age_days"] = age
        r.setdefault("horizon_days", HORIZON_DAYS)
        if age > HORIZON_DAYS:
            # Never reached base in the time it had. Calling that a miss is
            # honest; leaving it "open" forever is what inflated the open count.
            r["status"] = "HIT_BASE" if st == "HIT_BASE" else "EXPIRED"
    return rows


def _summary(rows: List[Dict[str, Any]], today: str) -> Dict[str, Any]:
    """Rolling multi-day book, not a single session."""
    book = [r for r in rows if _in_book(r, today) and r.get("status") != "VOID"]
    hits = sum(1 for r in book if r.get("status") in ("HIT_BASE", "HIT_STRETCH"))
    stretch_hits = sum(1 for r in book if r.get("status") == "HIT_STRETCH")
    misses = sum(1 for r in book if r.get("status") in ("FAIL", "EXPIRED"))
    open_n = sum(1 for r in book if str(r.get("status") or "") not in _TERMINAL
                 and r.get("status") != "HIT_BASE")
    new_today = sum(1 for r in book if str(r.get("day")) == today)

    # Expectancy in R is the only number that answers "does this make money".
    # Hit count alone is vanity: 90% wins at 0.2R loses to 40% wins at 2R.
    settled = [r for r in book if str(r.get("status") or "") in _TERMINAL
               or r.get("status") == "HIT_BASE"]
    r_vals = [_num(r.get("r_now")) for r in settled if r.get("r_now") is not None]
    wins = [v for v in r_vals if v > 0]
    losses = [v for v in r_vals if v <= 0]
    expectancy = round(sum(r_vals) / len(r_vals), 2) if r_vals else None
    tgt = [_num(r.get("target_atrs")) for r in book if r.get("target_atrs") is not None]
    return {
        "day": today,
        "horizon_days": HORIZON_DAYS,
        "hits": hits,
        "stretch_hits": stretch_hits,
        "misses": misses,
        "open": open_n,
        "n": len(book),
        "new_today": new_today,
        "settled": len(r_vals),
        "expectancy_r": expectancy,
        "avg_win_r": round(sum(wins) / len(wins), 2) if wins else None,
        "avg_loss_r": round(sum(losses) / len(losses), 2) if losses else None,
        "win_rate": round(100.0 * len(wins) / len(r_vals), 0) if r_vals else None,
        "median_target_atrs": round(sorted(tgt)[len(tgt) // 2], 1) if tgt else None,
        "items": sorted(book, key=lambda r: str(r.get("updated") or ""), reverse=True),
        "line": _grades_line(hits, open_n, misses, len(book)),
        "edge_line": _edge_line(expectancy, len(r_vals), tgt),
    }


def _edge_line(expectancy: Optional[float], settled: int, tgt: List[float]) -> str:
    """Say plainly whether the record means anything yet."""
    med = round(sorted(tgt)[len(tgt) // 2], 1) if tgt else None
    shape = f" · targets sit {med} ATR out" if med else ""
    if settled < 20:
        return (
            f"Edge unproven — {settled} settled ticket"
            f"{'' if settled == 1 else 's'}, need ~20+ before the number means "
            f"anything{shape}"
        )
    if expectancy is None:
        return f"No graded outcomes yet{shape}"
    verdict = "profitable" if expectancy > 0.1 else (
        "break-even" if expectancy > -0.1 else "losing"
    )
    return (
        f"Expectancy {expectancy:+.2f}R over {settled} settled — {verdict}{shape}"
    )


def _grades_line(hits: int, open_n: int, misses: int, n: int) -> str:
    if n <= 0:
        return "Predictions: none in the last week — empty is honest"
    return (
        f"Last {HORIZON_DAYS} sessions: {hits} hit base · "
        f"{open_n} still working · {misses} failed"
    )


def refresh_all_grades() -> Dict[str, Any]:
    """Re-grade still-working tickets vs Yahoo last close.

    Resolved tickets are terminal, so only live ones need a quote — that keeps
    this to a handful of requests instead of one per ticket ever recorded.
    """
    today = _day()
    try:
        import yfinance as yf
    except ImportError:
        return grades_today()

    with _lock:
        store = _expire(_load(), today)
        if not store:
            return _summary(store, today)
        syms = sorted({
            str(r.get("symbol") or "").upper()
            for r in store
            if r.get("symbol") and _is_live(r, today)
        })
        last_by: Dict[str, float] = {}
        for sym in syms:
            try:
                hist = yf.Ticker(sym).history(period="5d")
                if hist is not None and len(hist):
                    last_by[sym] = _num(hist["Close"].iloc[-1])
            except Exception:
                continue
        for r in store:
            sym = str(r.get("symbol") or "").upper()
            last = last_by.get(sym)
            if not last or last <= 0:
                continue
            r["last"] = round(last, 4 if last < 1 else 2)
            r["best_last"] = round(max(_num(r.get("best_last")), last), 4 if last < 1 else 2)
            r["status"] = grade_vs_last(
                last,
                _num(r.get("base_px")),
                _num(r.get("stretch_px")),
                _num(r.get("fail_px")),
                r.get("status"),
            )
            r["updated"] = datetime.now().isoformat()
        _save(store)

    return _summary(store, today)


def void_untrusted(min_stop_atr: Optional[float] = None) -> int:
    """Discard tickets the current model would never have written.

    Rescaling them instead would be moving the goalposts after the fact and
    would fabricate a track record. Broken instrument, discarded data. Covers
    tickets with no ATR (flat-percentage targets) and, when `min_stop_atr` is
    given, ones whose stop sits inside the daily noise — their stored
    reward/risk is arithmetic on a stop that would never have survived.
    """
    n = 0
    with _lock:
        store = _load()
        for r in store:
            if r.get("status") in _TERMINAL:
                continue
            reason = None
            atr = _num(r.get("atr_pct"))
            if r.get("atr_pct") is None:
                reason = "flat-percentage target model"
            elif min_stop_atr is not None and atr > 0:
                entry = _num(r.get("t0_last")) or _num(r.get("last"))
                stop = _num(r.get("fail_px"))
                atr_abs = entry * atr / 100.0
                if entry > 0 and stop > 0 and atr_abs > 0:
                    if (entry - stop) / atr_abs < _num(min_stop_atr) * 0.9:
                        reason = "stop inside daily noise — reward/risk was fiction"
            if not reason:
                continue
            r["status"] = "VOID"
            r["void_reason"] = reason
            r["updated"] = datetime.now().isoformat()
            n += 1
        if n:
            _save(store)
    return n


def live_symbols() -> List[str]:
    """Tickets still working — carried across days, not just today's."""
    today = _day()
    with _lock:
        store = _load()
    return sorted({
        str(r.get("symbol") or "").upper()
        for r in store
        if r.get("symbol") and _is_live(r, today)
    })


def grades_today() -> Dict[str, Any]:
    today = _day()
    with _lock:
        store = _load()
    return _summary(_expire(store, today), today)


def symbol_rank_adjust(symbol: str) -> Tuple[int, bool]:
    """Return (boost, drop). Failed names are not re-promoted."""
    sym = str(symbol or "").upper().strip()
    if not sym:
        return 0, False
    today = _day()
    with _lock:
        store = _load()
    rows = [r for r in store if str(r.get("symbol") or "").upper() == sym]
    if not rows:
        return 0, False
    fails = 0
    boost = 0
    for r in rows[-8:]:
        st = str(r.get("status") or "")
        if st == "FAIL":
            fails += 1
            # A break inside the horizon keeps the name off the board — it used
            # to be re-promoted the next morning as if nothing happened.
            if _age_days(r, today) <= HORIZON_DAYS:
                return -20, True
        elif st == "EXPIRED":
            fails += 1
        elif st == "HIT_STRETCH":
            boost += 3
        elif st == "HIT_BASE":
            boost += 1
    if fails >= 2:
        return -10, True
    return boost, False
