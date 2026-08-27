"""
Bundle Opening Range + EMA regime + IV regime workers for Boss / managers.
"""

from __future__ import annotations

from typing import Dict, Optional
from datetime import datetime
import logging

from technical_indicators import technical_indicators
from opening_range_analyzer import opening_range_analyzer
from iv_regime_analyzer import iv_regime_analyzer

logger = logging.getLogger(__name__)

# Hard blocks for auto direction (sit out — unclear / still printing open bar)
HARD_NO_TRADE = {
    'NO_CLEAR_DATA',
    'OUTSIDE_RTH_OR_NO_OPEN',
    'OPENING_BAR_FORMING',
    'AWAITING_BREAK_HOLD',
    'BREAK_HOLD_UNCLEAR',
}


def ingest_price(symbol: str, price: float, now: Optional[datetime] = None) -> None:
    """Update all session/structure price-based workers."""
    if not price or price <= 0:
        return
    technical_indicators.update_price(symbol, price)
    opening_range_analyzer.update(symbol, price, now=now)
    iv_regime_analyzer.update_price(symbol, price)


def evaluate_session_structure(
    symbol: str,
    stock_price: float,
    options_chain: Optional[Dict] = None,
    vix_level: Optional[float] = None,
    iv_skew: Optional[float] = None,
    now: Optional[datetime] = None,
) -> Dict:
    """
    Run Opening Range, EMA, and IV workers.
    Priority in the open: opening bar → first break → hold/fail, then EMA agreement.
    """
    try:
        ingest_price(symbol, stock_price, now=now)
    except Exception as e:
        logger.debug(f"ingest_price error: {e}")

    opening = opening_range_analyzer.analyze(symbol, stock_price, now=now)
    ema = technical_indicators.get_ema_signals(symbol, stock_price)
    from extra_session_workers import clock_worker, tape_worker, vwap_proxy_worker

    chain = options_chain or {}
    clock = clock_worker(now=now)
    tape = tape_worker(chain.get("calls") or [], chain.get("puts") or [])
    value = vwap_proxy_worker(symbol, stock_price)
    ema_vote = {
        'bot_type': 'EMA_REGIME_WORKER',
        'action': ema.get('action', 'NO_TRADE'),
        'confidence': ema.get('confidence', 30),
        'veto_flags': ema.get('veto_flags', []),
        'reason': ema.get('reason', ''),
        'features': ema,
    }
    iv = iv_regime_analyzer.analyze(
        symbol,
        stock_price,
        options_chain=options_chain,
        vix_level=vix_level,
        iv_skew=iv_skew,
    )

    vetoes = []
    for vote in (opening, ema_vote, iv, clock):
        for flag in vote.get('veto_flags') or []:
            if flag not in vetoes:
                vetoes.append(flag)

    direction_action = 'NO_TRADE'
    direction_confidence = 30
    direction_source = 'none'

    orb_state = opening.get('orb_state')
    opening_action = opening.get('action', 'NO_TRADE')

    # Prefer opening-range first-break hold / failed-break fade when it has a real action
    if opening_action in ('BUY_CALLS', 'BUY_PUTS') and orb_state in (
        'FIRST_BREAK_HOLDING',
        'FIRST_BREAK_FAILED',
    ):
        direction_action = opening_action
        direction_confidence = int(opening.get('confidence', 50))
        direction_source = 'opening_first_break'
        if ema_vote.get('action') == direction_action:
            direction_confidence = min(92, direction_confidence + 10)
        elif ema_vote.get('action') in ('BUY_CALLS', 'BUY_PUTS') and ema_vote.get('action') != direction_action:
            direction_confidence = max(30, direction_confidence - 12)
            if 'EMA_OR_DISAGREE' not in vetoes:
                vetoes.append('EMA_OR_DISAGREE')
    elif opening_action in ('BUY_CALLS', 'BUY_PUTS'):
        direction_action = opening_action
        direction_confidence = int(opening.get('confidence', 50))
        direction_source = 'opening_range'
    elif ema_vote.get('action') in ('BUY_CALLS', 'BUY_PUTS') and not opening.get('in_critical_window'):
        # Outside critical open window, EMA can lead if OR is quiet
        direction_action = ema_vote['action']
        direction_confidence = int(ema_vote.get('confidence', 50))
        direction_source = 'ema'
    elif ema_vote.get('action') in ('BUY_CALLS', 'BUY_PUTS') and orb_state in ('INSIDE', 'FORMING', 'RANGE_STILL_BUILDING'):
        # In open but no break yet — EMA is context only, keep NO_TRADE for autos
        direction_action = 'NO_TRADE'
        direction_confidence = 28
        direction_source = 'awaiting_first_break'
        if 'AWAITING_FIRST_BREAK' not in vetoes:
            vetoes.append('AWAITING_FIRST_BREAK')

    if iv.get('richness') == 'RICH' and direction_action in ('BUY_CALLS', 'BUY_PUTS'):
        direction_confidence = max(25, direction_confidence - 12)
        if 'IV_RICH_SOFT_BLOCK' not in vetoes:
            vetoes.append('IV_RICH_SOFT_BLOCK')

    # Sit out when data unclear, open bar printing, or break not confirmed yet
    if any(v in vetoes for v in HARD_NO_TRADE):
        direction_action = 'NO_TRADE'
        direction_confidence = min(direction_confidence, 25)
        if direction_source == 'none':
            direction_source = 'blocked'

    return {
        'workers': {
            'opening_range': opening,
            'ema_regime': ema_vote,
            'iv_regime': iv,
            'clock': clock,
            'tape': tape,
            'value': value,
        },
        'direction_hint': {
            'action': direction_action,
            'confidence': direction_confidence,
            'source': direction_source,
            'phase': opening.get('phase'),
            'orb_state': orb_state,
            'first_break': opening.get('first_break'),
        },
        'veto_flags': vetoes,
        'invalidation_level': opening.get('invalidation_level') or opening.get('features', {}).get('invalidation'),
        'summary': (
            f"phase={opening.get('phase')} OR={orb_state} "
            f"FB={opening.get('first_break', {}).get('side')}/"
            f"hold={opening.get('first_break', {}).get('held')}/"
            f"fail={opening.get('first_break', {}).get('failed')} "
            f"EMA={ema.get('ema_trend')} IV={iv.get('richness')} "
            f"-> {direction_action} ({direction_confidence})"
        ),
    }
