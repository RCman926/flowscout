"""
Plain-English lesson for the trade you are in (or sitting out).

No paid APIs. Builds a checklist from Boss workers / shadow / Big Run
so a human can later match the same story on a chart.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _s(v: Any, n: int = 220) -> str:
    t = " ".join(str(v or "").split())
    return t[:n] if t else ""


def _or_state(boss: Dict[str, Any]) -> str:
    sc = boss.get("session_context") or {}
    w = (boss.get("workers") or {}).get("opening_range") or {}
    return str(sc.get("orb_state") or w.get("orb_state") or w.get("phase") or "—")


def _setup_name(boss: Dict[str, Any]) -> str:
    action = str(boss.get("action") or "NO_TRADE").upper()
    orb = _or_state(boss).upper()
    hard = [str(x) for x in (boss.get("hard_vetoes") or [])]
    if action == "NO_TRADE":
        if hard:
            return "SIT_OUT · " + hard[0]
        if "FORMING" in orb or "AWAITING" in orb:
            return "WAIT · opening range still forming"
        return "NO_TRADE · no executable thesis"
    side = "CALLS" if "CALL" in action else "PUTS"
    if "FIRST_BREAK" in orb or "HOLD" in orb:
        return f"{side} · opening-range first break"
    ema = ((boss.get("workers") or {}).get("ema_regime") or {}).get("action") or ""
    if ema:
        return f"{side} · structure + EMA ({ema})"
    return f"{side} · Boss BUY"


def from_boss(
    boss: Optional[Dict[str, Any]],
    *,
    shadow_open: Optional[Dict[str, Any]] = None,
    paper: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    boss = boss if isinstance(boss, dict) else {}
    action = str(boss.get("action") or "NO_TRADE").upper()
    in_trade = action in ("BUY_CALLS", "BUY_PUTS")
    c = boss.get("contract") or {}
    sc = boss.get("session_context") or {}
    iv = boss.get("iv_context") or {}
    mdir = (boss.get("managers") or {}).get("direction") or {}
    mst = (boss.get("managers") or {}).get("structure") or {}
    hard = [str(x) for x in (boss.get("hard_vetoes") or []) if x]
    soft = [str(x) for x in (boss.get("soft_vetoes") or []) if x]
    inv = boss.get("invalidation_level")
    strike = c.get("strike")
    right = c.get("right") or ("CALL" if "CALL" in action else "PUT" if "PUT" in action else "—")

    evidence: List[str] = []
    if sc.get("orb_state") or sc.get("phase"):
        evidence.append(f"Opening range: {sc.get('orb_state') or sc.get('phase')}")
    if mdir.get("agreement"):
        evidence.append(f"Direction {mdir.get('agreement')} · thesis {mdir.get('thesis') or '—'}")
    if mst.get("posture") or mst.get("thesis"):
        evidence.append(f"Structure {mst.get('posture') or mst.get('thesis')}")
    if iv.get("richness"):
        evidence.append(f"IV {iv.get('richness')}" + (f" (ATM {iv.get('atm_iv')})" if iv.get("atm_iv") is not None else ""))
    src = sc.get("direction_source")
    if src:
        evidence.append(f"Hint source: {src}")
    if not evidence:
        r = _s(boss.get("reason"), 160)
        if r:
            evidence.append(r)

    must: List[str] = []
    if in_trade:
        must.append("Hold the thesis — first-break / EMA side does not reverse")
        if inv is not None:
            try:
                must.append(f"Spot stays on the right side of invalidation {float(inv):.2f}")
            except (TypeError, ValueError):
                must.append(f"Invalidation {inv}")
        must.append("Grade at bid (never mark mid/ask as a win)")
        if not boss.get("paper_armed"):
            must.append("Paper is DISARMED — this is a shadow lesson, not a live fill")
    else:
        must.append("Do not invent a trade — empty / sit-out is the call")
        if hard:
            must.append("Hard veto still on: " + ", ".join(hard[:3]))

    dead: List[str] = []
    if hard:
        dead.extend(hard[:4])
    if inv is not None and in_trade:
        dead.append(f"Lose invalidation {inv}")
    if "CALL" in action:
        dead.append("OR fail back / EMA flip bearish")
    elif "PUT" in action:
        dead.append("OR fail back / EMA flip bullish")
    else:
        dead.append("No ticket until vetoes clear and OR has a held first break")

    clock = "0DTE clock · delayed Yahoo (not live tape)"
    if sc.get("phase"):
        clock = f"Session phase {sc.get('phase')} · delayed Yahoo"

    headline = "SITTING OUT" if not in_trade else (
        "IN A SHADOW TRADE" if shadow_open else "BOSS SAYS BUY (shadow grades it)"
    )
    if paper and (paper.get("open") or paper.get("trade")):
        headline = "PAPER POSITION OPEN"

    contract_line = "—"
    if strike:
        ask = c.get("ask") or c.get("entry_mark")
        bid = c.get("bid")
        contract_line = f"{right} {strike}"
        if ask:
            contract_line += f" · buy@ask {ask}"
        if bid:
            contract_line += f" · mark@bid {bid}"
    elif shadow_open:
        contract_line = (
            f"{shadow_open.get('right') or right} {shadow_open.get('strike')} "
            f"· ask {shadow_open.get('entry_ask')} · live bid {shadow_open.get('mark') or shadow_open.get('bid')}"
        )

    sh_note = None
    if shadow_open:
        pnl = shadow_open.get("pnl_pct")
        sh_note = (
            f"Shadow {shadow_open.get('id')} {shadow_open.get('tenor') or '0DTE'} "
            f"{('P&L ' + str(pnl) + '% vs bid') if pnl is not None else 'marking bid'}"
        )

    return {
        "desk": "0dte",
        "in_trade": bool(in_trade or shadow_open),
        "headline": headline,
        "setup": _setup_name(boss),
        "action": action,
        "confidence": boss.get("confidence"),
        "contract": contract_line,
        "evidence": evidence[:6],
        "must_stay_true": must[:5],
        "invalidation": dead[:5],
        "clock": clock,
        "do_nothing_if": hard[:3] or (["No first break / no liquid chain"] if not in_trade else []),
        "fill_model": "Buy ask → grade/exit bid · delayed Yahoo",
        "reason": _s(boss.get("reason"), 280),
        "shadow": sh_note,
        "armed": bool(boss.get("paper_armed")),
        "chart_later": [
            "Box the opening range (first 5–15m high/low)",
            "Mark first break + whether it held",
            "Draw EMA 9/21/50 vs spot",
            "Invalidation = level in this card",
        ],
    }


def from_big_run(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(row, dict) or not row.get("symbol"):
        return None
    plan = row.get("plan") or {}
    scen = plan.get("scenarios") or {}
    fail = (scen.get("fail") or {}) if isinstance(scen, dict) else {}
    lvl = str(row.get("level") or "")
    leftover = lvl in ("BUILDING", "HOT")
    return {
        "desk": "big_run",
        "in_trade": True,
        "headline": f"BIG RUN · {row.get('symbol')} {lvl}",
        "setup": plan.get("thesis") or row.get("setup") or lvl,
        "action": "SHARES",
        "confidence": plan.get("confidence") or row.get("confidence"),
        "contract": f"Shares {row.get('symbol')} last {row.get('spot')}",
        "evidence": [plan.get("tells") or row.get("why") or ""][:1],
        "must_stay_true": [
            plan.get("when") or row.get("when") or "Buy only on the stated trigger",
            "Does not override SPY Boss",
        ],
        "invalidation": [
            plan.get("invalidation") or fail.get("label") or "Thesis fails if leftover chase / fail band hits",
        ],
        "clock": f"Session {row.get('session') or '—'} · delayed Yahoo shares",
        "do_nothing_if": ["HOT leftover / paying the high"] if leftover else ["No volume-before-price coil"],
        "fill_model": "Shares · delayed Yahoo (not 0DTE)",
        "reason": _s(plan.get("tells") or row.get("why"), 280),
        "shadow": None,
        "armed": False,
        "chart_later": [
            "Mark yesterday close vs today's gap",
            "Volume expanding before price (PRE coil)",
            "Do not chase through the stated high",
        ],
    }


def pack(
    boss: Optional[Dict[str, Any]] = None,
    *,
    shadow_opens: Optional[List[Dict[str, Any]]] = None,
    paper: Optional[Dict[str, Any]] = None,
    big_run: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    opens = [o for o in (shadow_opens or []) if isinstance(o, dict)]
    primary_shadow = opens[0] if opens else None
    odte = from_boss(boss, shadow_open=primary_shadow, paper=paper)
    br = from_big_run(big_run)
    return {
        "odte": odte,
        "big_run": br,
        "open_shadows": [
            {
                "id": o.get("id"),
                "action": o.get("action"),
                "strike": o.get("strike"),
                "tenor": o.get("tenor"),
                "pnl_pct": o.get("pnl_pct"),
                "lesson": o.get("lesson") or from_boss(boss, shadow_open=o),
            }
            for o in opens[:4]
        ],
    }
