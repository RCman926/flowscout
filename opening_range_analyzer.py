"""
Opening Range / Opening Candle analyzer for 0DTE.

The first 15–30 minutes are the highest-value window:
1) Opening bar (first ~1m) sets initial auction bias
2) First break of OR (5m, then 15m) is the key event
3) Whether that break HOLDS or FAILS (comes back inside) is the real indication
   before a larger continuation move

NO_TRADE when data is unclear — not a blanket sit-out of the whole open.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, date
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo
import logging

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")
RTH_OPEN = time(9, 30)
RTH_CLOSE = time(16, 0)


@dataclass
class OpeningRangeState:
    session_date: Optional[date] = None
    open_price: float = 0.0
    opening_candle_high: float = 0.0
    opening_candle_low: float = 0.0
    opening_candle_close: float = 0.0
    opening_candle_locked: bool = False
    or5_high: float = 0.0
    or5_low: float = 0.0
    or5_locked: bool = False
    or15_high: float = 0.0
    or15_low: float = 0.0
    or15_locked: bool = False
    # First break tracking (the important early signal)
    first_break_side: Optional[str] = None  # 'UP' | 'DOWN'
    first_break_level: float = 0.0
    first_break_time: Optional[datetime] = None
    first_break_held: bool = False
    first_break_failed: bool = False
    max_extension_after_break: float = 0.0  # farthest favorable excursion
    prints: List[Tuple[datetime, float]] = field(default_factory=list)


class OpeningRangeAnalyzer:
    """
    Track opening candle + OR + first-break hold/fail for Direction manager.
    """

    CRITICAL_WINDOW_MINUTES = 30  # first 15–30m is the main focus

    def __init__(self, or_minutes_primary: int = 5):
        self.or_minutes_primary = or_minutes_primary
        self.state: Dict[str, OpeningRangeState] = {}

    def _now_et(self, now: Optional[datetime] = None) -> datetime:
        if now is None:
            return datetime.now(ET)
        if now.tzinfo is None:
            return now.replace(tzinfo=ET)
        return now.astimezone(ET)

    def _minutes_since_open(self, now_et: datetime) -> float:
        open_dt = datetime.combine(now_et.date(), RTH_OPEN, tzinfo=ET)
        return (now_et - open_dt).total_seconds() / 60.0

    def _ensure_session(self, symbol: str, now_et: datetime) -> OpeningRangeState:
        st = self.state.get(symbol)
        if st is None or st.session_date != now_et.date():
            st = OpeningRangeState(session_date=now_et.date())
            self.state[symbol] = st
        return st

    def update(self, symbol: str, price: float, now: Optional[datetime] = None) -> None:
        """Ingest a price print during RTH and maintain OR + first-break state."""
        if price is None or price <= 0:
            return

        now_et = self._now_et(now)
        if now_et.weekday() >= 5:
            return
        if not (RTH_OPEN <= now_et.time() <= RTH_CLOSE):
            return

        st = self._ensure_session(symbol, now_et)
        mins = self._minutes_since_open(now_et)
        if mins < 0:
            return

        st.prints.append((now_et, float(price)))
        if len(st.prints) > 5000:
            st.prints = st.prints[-2500:]

        if st.open_price <= 0:
            st.open_price = float(price)
            st.opening_candle_high = float(price)
            st.opening_candle_low = float(price)
            st.opening_candle_close = float(price)
            st.or5_high = float(price)
            st.or5_low = float(price)
            st.or15_high = float(price)
            st.or15_low = float(price)

        # Opening candle = first 1 minute
        if mins < 1.0 and not st.opening_candle_locked:
            st.opening_candle_high = max(st.opening_candle_high, price)
            st.opening_candle_low = min(st.opening_candle_low, price)
            st.opening_candle_close = float(price)
        elif mins >= 1.0 and not st.opening_candle_locked:
            st.opening_candle_locked = True

        # 5-minute OR
        if mins < 5.0 and not st.or5_locked:
            st.or5_high = max(st.or5_high, price)
            st.or5_low = min(st.or5_low, price)
        elif mins >= 5.0 and not st.or5_locked:
            st.or5_locked = True

        # 15-minute OR
        if mins < 15.0 and not st.or15_locked:
            st.or15_high = max(st.or15_high, price)
            st.or15_low = min(st.or15_low, price)
        elif mins >= 15.0 and not st.or15_locked:
            st.or15_locked = True

        # Track first break hold/fail once OR5 exists (even while still forming after open bar)
        self._update_first_break(st, price, now_et, mins)

    def _active_or_levels(self, st: OpeningRangeState, mins: float) -> Tuple[float, float, str, bool]:
        """Prefer OR15 after lock; else OR5; else opening-candle range as early proxy."""
        if mins >= 15 and st.or15_locked and st.or15_high > st.or15_low:
            return st.or15_high, st.or15_low, 'OR15', True
        if st.or5_locked and st.or5_high > st.or5_low:
            return st.or5_high, st.or5_low, 'OR5', True
        if st.opening_candle_locked and st.opening_candle_high > st.opening_candle_low:
            return st.opening_candle_high, st.opening_candle_low, 'OPEN_BAR', True
        # Still forming — use live expanding OR5 envelope if we have width
        if st.or5_high > st.or5_low:
            return st.or5_high, st.or5_low, 'OR5_LIVE', False
        return st.open_price, st.open_price, 'NONE', False

    def _update_first_break(
        self,
        st: OpeningRangeState,
        price: float,
        now_et: datetime,
        mins: float,
    ) -> None:
        or_high, or_low, label, locked = self._active_or_levels(st, mins)
        if label == 'NONE' or or_high <= or_low:
            return

        buffer = max((or_high - or_low) * 0.05, st.open_price * 0.0002)
        above = price > (or_high + buffer)
        below = price < (or_low - buffer)
        inside = not above and not below

        # Register first break only after opening bar is locked (avoid noise in first 60s)
        if st.first_break_side is None and st.opening_candle_locked and (above or below):
            st.first_break_side = 'UP' if above else 'DOWN'
            st.first_break_level = or_high if above else or_low
            st.first_break_time = now_et
            st.first_break_held = False
            st.first_break_failed = False
            st.max_extension_after_break = 0.0

        if st.first_break_side is None:
            return

        # Classic ORB: stay outside = hold developing; reclaim back inside range = failed break
        if st.first_break_side == 'UP':
            extension = max(0.0, price - st.first_break_level)
            st.max_extension_after_break = max(st.max_extension_after_break, extension)
            if inside or below:
                st.first_break_failed = True
                st.first_break_held = False
            elif above and st.max_extension_after_break >= buffer:
                st.first_break_held = True
                st.first_break_failed = False
        else:  # DOWN
            extension = max(0.0, st.first_break_level - price)
            st.max_extension_after_break = max(st.max_extension_after_break, extension)
            if inside or above:
                st.first_break_failed = True
                st.first_break_held = False
            elif below and st.max_extension_after_break >= buffer:
                st.first_break_held = True
                st.first_break_failed = False

    def analyze(
        self,
        symbol: str,
        current_price: float,
        now: Optional[datetime] = None,
    ) -> Dict:
        """Worker-style output for Boss / Direction manager."""
        now_et = self._now_et(now)
        st = self._ensure_session(symbol, now_et)
        mins = self._minutes_since_open(now_et) if RTH_OPEN <= now_et.time() <= RTH_CLOSE else -1.0
        in_critical = 0 <= mins <= self.CRITICAL_WINDOW_MINUTES

        result = {
            'bot_type': 'OPENING_RANGE_WORKER',
            'action': 'NO_TRADE',
            'confidence': 30,
            'veto_flags': [],
            'reason': 'No opening range yet',
            'session_date': str(st.session_date) if st.session_date else None,
            'minutes_since_open': round(mins, 2) if mins >= 0 else None,
            'in_critical_window': in_critical,
            'open_price': st.open_price,
            'opening_candle': {
                'open': st.open_price,
                'high': st.opening_candle_high,
                'low': st.opening_candle_low,
                'close': st.opening_candle_close,
                'locked': st.opening_candle_locked,
                'direction': 'NEUTRAL',
                'body_pct': 0.0,
                'range_pct': 0.0,
            },
            'or5': {'high': st.or5_high, 'low': st.or5_low, 'locked': st.or5_locked},
            'or15': {'high': st.or15_high, 'low': st.or15_low, 'locked': st.or15_locked},
            'first_break': {
                'side': st.first_break_side,
                'level': st.first_break_level,
                'held': st.first_break_held,
                'failed': st.first_break_failed,
                'time': st.first_break_time.isoformat() if st.first_break_time else None,
                'extension': round(st.max_extension_after_break, 4),
            },
            'orb_state': 'FORMING',
            'phase': 'UNKNOWN',
            'features': {},
        }

        # Unclear / no data → sit out
        if st.open_price <= 0 or current_price <= 0 or mins < 0:
            result['veto_flags'] = ['NO_CLEAR_DATA', 'OUTSIDE_RTH_OR_NO_OPEN']
            result['reason'] = 'No clear opening data (outside RTH or missing open print)'
            result['phase'] = 'NO_DATA'
            return result

        oc_range = max(st.opening_candle_high - st.opening_candle_low, 1e-9)
        oc_body = st.opening_candle_close - st.open_price
        body_pct = (oc_body / st.open_price) * 100.0
        range_pct = (oc_range / st.open_price) * 100.0
        if oc_body > 0:
            oc_dir = 'BULLISH'
        elif oc_body < 0:
            oc_dir = 'BEARISH'
        else:
            oc_dir = 'NEUTRAL'

        result['opening_candle'].update({
            'direction': oc_dir,
            'body_pct': round(body_pct, 4),
            'range_pct': round(range_pct, 4),
        })

        or_high, or_low, or_label, levels_locked = self._active_or_levels(st, mins)
        or_mid = (or_high + or_low) / 2.0 if or_high > or_low else st.open_price
        or_width_pct = ((or_high - or_low) / st.open_price) * 100.0 if st.open_price and or_high > or_low else 0.0
        buffer = max((or_high - or_low) * 0.05, st.open_price * 0.0002) if or_high > or_low else st.open_price * 0.0003

        above = current_price > (or_high + buffer) if or_high > or_low else False
        below = current_price < (or_low - buffer) if or_high > or_low else False
        inside = (or_high > or_low) and (not above and not below)

        drive = abs(body_pct) >= 0.12
        critical_boost = 10 if in_critical else 0

        # ---- Phase 1: opening bar still printing (0–1m) — watch, don't force ----
        if mins < 1.0 or not st.opening_candle_locked:
            result['phase'] = 'OPENING_BAR'
            result['orb_state'] = 'OPENING_BAR_FORMING'
            result['action'] = 'NO_TRADE'
            result['confidence'] = 25
            result['veto_flags'] = ['OPENING_BAR_FORMING']
            result['reason'] = (
                f'Opening bar forming ({mins:.1f}m). Bias watch: {oc_dir} '
                f'body={body_pct:.3f}% — wait for bar close then first break'
            )
            result['features'] = {
                'opening_drive': drive,
                'opening_direction': oc_dir,
                'or_label': or_label,
                'awaiting': 'opening_bar_close_then_first_break',
            }
            result['invalidation_level'] = or_mid
            return result

        # ---- Phase 2: critical 1–30m — opening bar + first break hold/fail ----
        result['phase'] = 'CRITICAL_OPEN' if in_critical else 'POST_OPEN'

        # Failed first break is the big early indication (often fades / waits for reclaim)
        if st.first_break_failed:
            result['orb_state'] = 'FIRST_BREAK_FAILED'
            result['veto_flags'] = ['FIRST_BREAK_FAILED']
            # Soft fade while still early and back on the failed side of the break
            brk = st.first_break_level or or_mid
            if in_critical and st.first_break_side == 'UP' and current_price < brk:
                result['action'] = 'BUY_PUTS'
                result['confidence'] = 55 + critical_boost
                result['reason'] = (
                    f'First break UP failed back inside {or_label}; '
                    f'early fade/put bias until reclaim {or_high:.2f}'
                )
            elif in_critical and st.first_break_side == 'DOWN' and current_price > brk:
                result['action'] = 'BUY_CALLS'
                result['confidence'] = 55 + critical_boost
                result['reason'] = (
                    f'First break DOWN failed back inside {or_label}; '
                    f'early fade/call bias until reclaim {or_low:.2f}'
                )
            else:
                result['action'] = 'NO_TRADE'
                result['confidence'] = 35
                result['reason'] = (
                    f'First break {st.first_break_side} failed - no clear hold. '
                    f'Wait for reclaim or fresh structure'
                )
            result['features'] = self._features(
                or_label, or_high, or_low, or_mid, or_width_pct, drive, oc_dir, current_price, st, in_critical
            )
            result['invalidation_level'] = st.first_break_level or or_mid
            return result

        # Held first break → continuation bias (highest quality early signal)
        if st.first_break_side and st.first_break_held and not st.first_break_failed:
            result['orb_state'] = 'FIRST_BREAK_HOLDING'
            if st.first_break_side == 'UP' and (above or current_price >= st.first_break_level):
                result['action'] = 'BUY_CALLS'
                result['confidence'] = min(88, 62 + critical_boost + (8 if drive and oc_dir == 'BULLISH' else 0))
                result['reason'] = (
                    f'First break UP holding above {st.first_break_level:.2f} ({or_label}) '
                    f'in first {self.CRITICAL_WINDOW_MINUTES}m window'
                )
            elif st.first_break_side == 'DOWN' and (below or current_price <= st.first_break_level):
                result['action'] = 'BUY_PUTS'
                result['confidence'] = min(88, 62 + critical_boost + (8 if drive and oc_dir == 'BEARISH' else 0))
                result['reason'] = (
                    f'First break DOWN holding below {st.first_break_level:.2f} ({or_label}) '
                    f'in first {self.CRITICAL_WINDOW_MINUTES}m window'
                )
            else:
                result['action'] = 'NO_TRADE'
                result['confidence'] = 40
                result['veto_flags'] = ['BREAK_HOLD_UNCLEAR']
                result['reason'] = 'First break was holding but price location is unclear'
            if oc_dir == 'BEARISH' and result['action'] == 'BUY_CALLS':
                result['confidence'] -= 8
                result['veto_flags'] = list(result.get('veto_flags') or []) + ['OPENING_CANDLE_DIVERGENCE']
            if oc_dir == 'BULLISH' and result['action'] == 'BUY_PUTS':
                result['confidence'] -= 8
                result['veto_flags'] = list(result.get('veto_flags') or []) + ['OPENING_CANDLE_DIVERGENCE']
            result['features'] = self._features(
                or_label, or_high, or_low, or_mid, or_width_pct, drive, oc_dir, current_price, st, in_critical
            )
            result['invalidation_level'] = or_mid
            return result

        # Break just happened but not yet confirmed hold
        if st.first_break_side and not st.first_break_held and not st.first_break_failed:
            result['orb_state'] = 'FIRST_BREAK_PENDING_HOLD'
            result['action'] = 'NO_TRADE'
            result['confidence'] = 38
            result['veto_flags'] = ['AWAITING_BREAK_HOLD']
            result['reason'] = (
                f'First break {st.first_break_side} seen @ {st.first_break_level:.2f} — '
                f'waiting to see if it HOLDS or FAILS before big indication'
            )
            result['features'] = self._features(
                or_label, or_high, or_low, or_mid, or_width_pct, drive, oc_dir, current_price, st, in_critical
            )
            result['invalidation_level'] = or_mid
            return result

        # No first break yet — inside range / still building
        if inside or not levels_locked:
            result['orb_state'] = 'INSIDE' if inside else 'FORMING'
            result['action'] = 'NO_TRADE'
            result['confidence'] = 32
            flags = ['INSIDE_OPENING_RANGE'] if inside else ['RANGE_STILL_BUILDING']
            # Opening bar bias is context only until break
            if drive and in_critical:
                result['reason'] = (
                    f'Inside {or_label} ({or_low:.2f}-{or_high:.2f}). '
                    f'Opening bar {oc_dir} drive — wait for first break then hold/fail'
                )
            else:
                result['reason'] = (
                    f'No first break yet inside {or_label} ({or_low:.2f}-{or_high:.2f}). '
                    f'Watching for break in first {self.CRITICAL_WINDOW_MINUTES}m'
                )
            result['veto_flags'] = flags
            result['features'] = self._features(
                or_label, or_high, or_low, or_mid, or_width_pct, drive, oc_dir, current_price, st, in_critical
            )
            result['invalidation_level'] = or_mid
            return result

        # Live break without state machine catch (edge case)
        if above:
            result['orb_state'] = 'BREAK_UP'
            result['action'] = 'NO_TRADE'
            result['veto_flags'] = ['AWAITING_BREAK_HOLD']
            result['confidence'] = 40
            result['reason'] = f'{or_label} break UP — confirming hold before entry'
        elif below:
            result['orb_state'] = 'BREAK_DOWN'
            result['action'] = 'NO_TRADE'
            result['veto_flags'] = ['AWAITING_BREAK_HOLD']
            result['confidence'] = 40
            result['reason'] = f'{or_label} break DOWN — confirming hold before entry'

        if or_width_pct > 0.80:
            result['confidence'] = max(25, result['confidence'] - 12)
            result['veto_flags'] = list(result.get('veto_flags') or []) + ['WIDE_OPENING_RANGE']

        result['features'] = self._features(
            or_label, or_high, or_low, or_mid, or_width_pct, drive, oc_dir, current_price, st, in_critical
        )
        result['invalidation_level'] = or_mid
        return result

    def _features(
        self,
        or_label,
        or_high,
        or_low,
        or_mid,
        or_width_pct,
        drive,
        oc_dir,
        current_price,
        st: OpeningRangeState,
        in_critical: bool,
    ) -> Dict:
        return {
            'or_label': or_label,
            'or_high': or_high,
            'or_low': or_low,
            'or_mid': or_mid,
            'or_width_pct': round(or_width_pct, 4),
            'opening_drive': drive,
            'opening_direction': oc_dir,
            'in_critical_window': in_critical,
            'first_break_side': st.first_break_side,
            'first_break_held': st.first_break_held,
            'first_break_failed': st.first_break_failed,
            'distance_to_or_high_pct': round(((or_high - current_price) / current_price) * 100, 4) if current_price else 0,
            'distance_to_or_low_pct': round(((current_price - or_low) / current_price) * 100, 4) if current_price else 0,
            'invalidation': or_mid,
            'awaiting': None if st.first_break_held or st.first_break_failed else 'hold_or_fail',
        }


# Global instance
opening_range_analyzer = OpeningRangeAnalyzer(or_minutes_primary=5)
