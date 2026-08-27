"""
Manager layer between workers and Boss.

Direction manager: OR / flow / EMA
Structure manager: IV / liquidity / session vetoes
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional

from session_hard_flags import STRUCTURE_HARD


def _vote(action: str, confidence: float, source: str, reason: str = '', veto_flags: List[str] = None) -> Dict:
    return {
        'action': action or 'NO_TRADE',
        'confidence': int(confidence or 0),
        'source': source,
        'reason': reason or '',
        'veto_flags': list(veto_flags or []),
    }


def run_direction_manager(
    opening: Dict,
    ema_vote: Dict,
    flow_action: str,
    flow_confidence: float,
    flow_reason: str = '',
    tape_vote: Optional[Dict] = None,
    value_vote: Optional[Dict] = None,
) -> Dict:
    """Merge opening-range, EMA, flow, tape, and value into one direction thesis."""
    votes = []
    opening_action = opening.get('action', 'NO_TRADE')
    orb_state = opening.get('orb_state', '')
    votes.append(_vote(
        opening_action,
        opening.get('confidence', 0),
        'opening_range',
        opening.get('reason', ''),
        opening.get('veto_flags'),
    ))
    votes.append(_vote(
        ema_vote.get('action', 'NO_TRADE'),
        ema_vote.get('confidence', 0),
        'ema',
        ema_vote.get('reason', ''),
        ema_vote.get('veto_flags'),
    ))
    votes.append(_vote(flow_action, flow_confidence, 'flow', flow_reason))
    tape_vote = tape_vote or {}
    if tape_vote:
        votes.append(_vote(
            tape_vote.get('action', 'NO_TRADE'),
            tape_vote.get('confidence', 0),
            'tape',
            tape_vote.get('reason', ''),
            tape_vote.get('veto_flags'),
        ))
    value_vote = value_vote or {}
    if value_vote:
        votes.append(_vote(
            value_vote.get('action', 'NO_TRADE'),
            value_vote.get('confidence', 0),
            'value',
            value_vote.get('reason', ''),
            value_vote.get('veto_flags'),
        ))

    call_w = 0.0
    put_w = 0.0
    details = []
    for v in votes:
        w = max(0, v['confidence']) / 100.0
        # Opening first-break states get extra weight in the open
        if v['source'] == 'opening_range' and orb_state in ('FIRST_BREAK_HOLDING', 'FIRST_BREAK_FAILED'):
            w *= 1.35
        if v['action'] == 'BUY_CALLS':
            call_w += w
            details.append(f"{v['source']}:CALLS({v['confidence']})")
        elif v['action'] == 'BUY_PUTS':
            put_w += w
            details.append(f"{v['source']}:PUTS({v['confidence']})")
        else:
            details.append(f"{v['source']}:FLAT")

    agree = abs(call_w - put_w)
    total = call_w + put_w
    if total <= 0.15:
        thesis = 'NO_TRADE'
        conf = 25
        agreement = 'NONE'
    elif call_w > put_w and call_w >= 0.55:
        thesis = 'BUY_CALLS'
        conf = min(90, int(50 + call_w * 35))
        agreement = 'STRONG' if put_w < 0.25 and call_w >= 0.9 else 'MODERATE'
    elif put_w > call_w and put_w >= 0.55:
        thesis = 'BUY_PUTS'
        conf = min(90, int(50 + put_w * 35))
        agreement = 'STRONG' if call_w < 0.25 and put_w >= 0.9 else 'MODERATE'
    else:
        thesis = 'NO_TRADE'
        conf = 35
        agreement = 'SPLIT'

    dissent = []
    if thesis == 'BUY_CALLS' and put_w > 0.2:
        dissent.append('PUT_DISSENT')
    if thesis == 'BUY_PUTS' and call_w > 0.2:
        dissent.append('CALL_DISSENT')

    return {
        'manager': 'DIRECTION',
        'thesis': thesis,
        'confidence': conf,
        'agreement': agreement,
        'call_weight': round(call_w, 3),
        'put_weight': round(put_w, 3),
        'dissent': dissent,
        'votes': votes,
        'summary': f"Direction {thesis} ({agreement}) " + ', '.join(details),
        'invalidation': opening.get('invalidation_level'),
        'orb_state': orb_state,
        'phase': opening.get('phase'),
    }


def run_structure_manager(
    iv_vote: Dict,
    quality: Dict,
    session_vetoes: List[str],
) -> Dict:
    """Structure/risk: IV + liquidity + session hard flags."""
    vetoes = []
    for v in session_vetoes or []:
        if v not in vetoes:
            vetoes.append(v)
    for v in (iv_vote.get('veto_flags') or []):
        if v not in vetoes:
            vetoes.append(v)
    for v in (quality.get('veto_flags') or []):
        if v not in vetoes:
            vetoes.append(v)

    hard_hit = [v for v in vetoes if v in STRUCTURE_HARD]
    soft = [v for v in vetoes if v not in STRUCTURE_HARD]

    safe = len(hard_hit) == 0 and quality.get('ok', False)
    # IV rich is soft: structure can still be "caution" not hard fail
    if 'IV_RICH_VS_REALIZED' in vetoes or 'IV_RICH_SOFT_BLOCK' in vetoes:
        posture = 'CAUTION'
    elif safe:
        posture = 'GREEN'
    else:
        posture = 'RED'

    conf = 70 if posture == 'GREEN' else 45 if posture == 'CAUTION' else 20
    return {
        'manager': 'STRUCTURE_RISK',
        'thesis': 'ALLOW' if posture in ('GREEN', 'CAUTION') and quality.get('ok') else 'BLOCK',
        'posture': posture,
        'confidence': conf,
        'hard_vetoes': hard_hit,
        'soft_vetoes': soft,
        'veto_flags': vetoes,
        'quality_ok': bool(quality.get('ok')),
        'contract': quality.get('contract'),
        'summary': (
            f"Structure {posture}: hard={hard_hit or 'none'} "
            f"quality={'OK' if quality.get('ok') else 'FAIL'}"
        ),
        'iv_richness': iv_vote.get('richness'),
    }


def run_timing_manager(clock: Dict, opening: Dict) -> Dict:
    """When to take a new 0DTE — clock + open-range phase. Not a second order Boss."""
    vetoes = list(clock.get('veto_flags') or [])
    orb = opening.get('orb_state') or ''
    phase = clock.get('phase') or opening.get('phase') or ''
    if orb in ('FORMING', 'RANGE_STILL_BUILDING') or clock.get('phase') == 'OPEN_PRINT':
        thesis = 'WAIT'
        if 'OPENING_BAR_FORMING' not in vetoes and orb in ('FORMING', 'RANGE_STILL_BUILDING'):
            vetoes.append('AWAITING_FIRST_BREAK')
    elif any(v in ('TOO_LATE_0DTE', 'OUTSIDE_RTH_OR_NO_OPEN') for v in vetoes):
        thesis = 'BLOCK'
    else:
        thesis = 'ALLOW'
    return {
        'manager': 'TIMING',
        'thesis': thesis,
        'phase': phase,
        'minutes_to_close': clock.get('minutes_to_close'),
        'orb_state': orb,
        'confidence': 75 if thesis == 'ALLOW' else 35,
        'veto_flags': vetoes,
        'summary': f"Timing {thesis} · {phase} · OR {orb or '—'}",
    }


def run_risk_manager(direction_thesis: str) -> Dict:
    """Streak + open book — can sit out a side. Does not flatten live tickets."""
    vetoes: List[str] = []
    streak_side = None
    streak_n = 0
    open_n = 0
    try:
        from shadow_learning_engine import shadow_learning_engine as eng

        streak_side, streak_n = eng.consecutive_losses()
        open_n = len(eng.open or [])
    except Exception:
        pass
    if streak_n >= 2 and streak_side and streak_side == direction_thesis:
        flag = 'STREAK_BLOCK_CALLS' if streak_side == 'BUY_CALLS' else 'STREAK_BLOCK_PUTS'
        vetoes.append(flag)
    if open_n >= 5:
        vetoes.append('TOO_MANY_OPEN')
    thesis = 'BLOCK' if vetoes else 'ALLOW'
    return {
        'manager': 'RISK',
        'thesis': thesis,
        'streak_side': streak_side,
        'streak_n': streak_n,
        'open_shadows': open_n,
        'confidence': 70 if thesis == 'ALLOW' else 25,
        'veto_flags': vetoes,
        'summary': (
            f"Risk {thesis} · open {open_n} · streak {streak_n} {streak_side or ''}"
        ).strip(),
    }
