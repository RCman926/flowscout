"""
Shadow learning — every Boss BUY_CALLS / BUY_PUTS is logged and graded.

Does NOT paper-execute and does NOT write fake zerodte_trades spam.
Grades against live option marks (buy@ask → track@bid).
Stage A does not feed ML bots or signal_performance.json.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from cloud_runtime import state_path
    SHADOW_FILE = str(state_path("shadow_learning_trades.json"))
except Exception:
    SHADOW_FILE = "shadow_learning_trades.json"
# Asymmetric Stage A grading: tight losses, let winners breathe / trail
STOP_PCT = 15.0           # hard loss — tight risk
HARD_WIN_PCT = 100.0      # bank monsters at +100% (can be higher peak before trail)
TRAIL_ARM_PCT = 25.0      # after +25%, protect with a trail
TRAIL_GIVEBACK_PCT = 12.0  # exit if give back 12pts from peak (peak 50 → exit ~38)
MAX_HOLD_SECONDS = 900    # 15 minutes then force grade
SAME_STRIKE_REOPEN_SECONDS = 45
LOSS_REOPEN_SECONDS = 480  # 8 min after a LOSS on same side
TARGET_PREMIUM_USD = 500.0
MIN_CONTRACTS = 5
MAX_CONTRACTS = 50


def contracts_for_premium(entry_ask: float, target: float = TARGET_PREMIUM_USD) -> int:
    ask = float(entry_ask or 0)
    if ask <= 0:
        return MIN_CONTRACTS
    n = int(round(target / (ask * 100.0)))
    return max(MIN_CONTRACTS, min(MAX_CONTRACTS, n))

# Back-compat aliases (older code / API cards)
WIN_PCT = HARD_WIN_PCT
LOSS_PCT = STOP_PCT


class ShadowLearningEngine:
    def __init__(self, path: str = SHADOW_FILE):
        self.path = path
        self.open: List[Dict[str, Any]] = []
        self.closed: List[Dict[str, Any]] = []
        self.last_boss: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        try:
            if not os.path.exists(self.path):
                return
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.open = list(data.get("open") or [])
            self.closed = list(data.get("closed") or [])[-500:]
        except Exception as e:
            logger.warning(f"Shadow learning load failed: {e}")

    def _save(self) -> None:
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "open": self.open,
                        "closed": self.closed[-500:],
                        "updated": datetime.now().isoformat(),
                    },
                    f,
                    indent=2,
                    default=str,
                )
        except Exception as e:
            logger.warning(f"Shadow learning save failed: {e}")

    def summary(self) -> Dict[str, Any]:
        today = datetime.now().date().isoformat()
        closed_today = [
            t for t in self.closed
            if str(t.get("exit_time") or "").startswith(today)
        ]
        wins = sum(1 for t in closed_today if t.get("outcome") == "WIN")
        losses = sum(1 for t in closed_today if t.get("outcome") == "LOSS")
        be = sum(1 for t in closed_today if t.get("outcome") == "BREAKEVEN")
        graded = wins + losses + be
        return {
            "mode": "shadow",
            "date": today,
            "open_count": len(self.open),
            "closed_today": len(closed_today),
            "wins_today": wins,
            "losses_today": losses,
            "breakeven_today": be,
            "win_rate_today": round((wins / graded) * 100, 1) if graded else None,
            "learning": True,
            "note": "Every Boss BUY is graded vs bid; paper stays DISARMED",
        }

    def _takeaways(self, closed_today: List[Dict[str, Any]], opens: List[Dict[str, Any]]) -> List[str]:
        tips: List[str] = []
        if not closed_today and not opens:
            tips.append("No Boss BUY shadows yet today — learning starts when Boss says BUY_CALLS/BUY_PUTS.")
            return tips
        wins = [t for t in closed_today if t.get("outcome") == "WIN"]
        losses = [t for t in closed_today if t.get("outcome") == "LOSS"]
        if closed_today:
            tips.append(f"Graded {len(closed_today)} shadow trades today ({len(wins)}W / {len(losses)}L).")
            if losses and len(losses) >= len(wins):
                tips.append("More losses than wins so far — model is learning what NOT to chase on delayed Yahoo marks.")
            elif wins:
                tips.append("Wins and losses are the Boss shadow ledger — not ML training theater.")
            win_usds = [float(t.get("pnl_usd") or 0) for t in wins if t.get("pnl_usd") is not None]
            if win_usds:
                tips.append(
                    f"Avg winner: ${sum(win_usds)/len(win_usds):.2f}/contract "
                    f"({sum(float(t.get('pnl_pct') or 0) for t in wins)/len(wins):+.1f}%)."
                )
            tenors = {}
            for t in closed_today:
                k = t.get("tenor") or "0DTE?"
                tenors[k] = tenors.get(k, 0) + 1
            if tenors:
                tips.append("Tenors graded: " + ", ".join(f"{k}×{v}" for k, v in sorted(tenors.items())))
        if opens:
            tips.append(f"{len(opens)} shadow trade(s) still open and being marked to bid.")
        tips.append("Trade History stays empty until you ARM paper — this panel is the learning ledger.")
        return tips

    def process_cycle(
        self,
        *,
        symbol: str,
        stock_price: float,
        boss_decision: Dict[str, Any],
        flow_data: Optional[Dict[str, Any]] = None,
        bot_predictions: Optional[Dict[str, Any]] = None,
        signal_analysis: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Open shadows for BUY actions + grade open ones. Always runs."""
        self.last_boss = boss_decision or {}
        opened = None
        try:
            opened = self._maybe_open(
                symbol=symbol,
                stock_price=stock_price,
                boss_decision=boss_decision or {},
                flow_data=flow_data or {},
                bot_predictions=bot_predictions or {},
                signal_analysis=signal_analysis or {},
            )
        except Exception as e:
            logger.debug(f"Shadow open error: {e}")

        closed_now: List[Dict[str, Any]] = []
        try:
            closed_now = self._grade_open(
                symbol=symbol,
                stock_price=stock_price,
                flow_data=flow_data or {},
                boss_decision=boss_decision or {},
            )
        except Exception as e:
            logger.debug(f"Shadow grade error: {e}")

        # Decision journal — CALLS/PUTS/NO_TRADE/insufficient (change-only, no P&L)
        journal_entry = None
        try:
            from decision_journal import boss_decision_journal
            journal_entry = boss_decision_journal.record(
                symbol=symbol,
                stock_price=float(stock_price or 0),
                boss_decision=boss_decision or {},
                flow_data=flow_data or {},
            )
        except Exception as e:
            logger.debug(f"Decision journal skip: {e}")

        for trade in closed_now:
            try:
                self._feed_learners(trade)
            except Exception as e:
                logger.debug(f"Shadow feed learners error: {e}")

        if opened or closed_now or self.open:
            self._save()

        out = self.summary()
        out['learning_proper'] = True
        out['paper_armed_required'] = False
        out['grade_rules'] = {
            'stop_pct': STOP_PCT,
            'hard_win_pct': HARD_WIN_PCT,
            'trail_arm_pct': TRAIL_ARM_PCT,
            'trail_giveback_pct': TRAIL_GIVEBACK_PCT,
            'max_hold_seconds': MAX_HOLD_SECONDS,
            'entry': 'ask',
            'mark': 'bid',
            'note': 'Tight stop; winners trail / can run to +100%+',
        }
        try:
            from decision_journal import boss_decision_journal
            out['decision_journal'] = boss_decision_journal.today_report()
        except Exception:
            out['decision_journal'] = None
        if journal_entry:
            out['last_journal'] = {
                'bucket': journal_entry.get('bucket'),
                'action': journal_entry.get('action'),
                'reason': (journal_entry.get('reason') or '')[:120],
            }
        if opened:
            out["last_opened"] = {
                "id": opened.get("id"),
                "action": opened.get("action"),
                "strike": opened.get("strike"),
                "entry": opened.get("entry_ask"),
            }
        if closed_now:
            out["last_closed"] = [
                {
                    "id": t.get("id"),
                    "outcome": t.get("outcome"),
                    "pnl_pct": t.get("pnl_pct"),
                    "action": t.get("action"),
                }
                for t in closed_now
            ]
        return out

    def _extract_entry_mark(self, boss: Dict[str, Any], action: str, flow: Dict[str, Any]) -> Dict[str, Any]:
        contract = boss.get("contract") or {}
        scenarios = boss.get("scenarios") or boss.get("price_scenarios") or []
        primary = None
        if isinstance(scenarios, list):
            primary = next((s for s in scenarios if s.get("primary")), None) or (scenarios[0] if scenarios else None)
        elif isinstance(scenarios, dict):
            primary = scenarios.get("Balanced") or scenarios.get("primary")

        ask = float(contract.get("ask") or contract.get("entry_mark") or contract.get("buy") or 0)
        bid = float(contract.get("bid") or contract.get("exit_mark") or contract.get("sell") or 0)
        mid = float(contract.get("mid") or 0)
        strike = contract.get("strike")
        right = contract.get("right") or ("CALL" if action == "BUY_CALLS" else "PUT")

        if primary:
            ask = ask or float(primary.get("buy") or primary.get("ask") or 0)
            bid = bid or float(primary.get("sell") or primary.get("bid") or 0)
            mid = mid or float(primary.get("mid") or 0)
            strike = strike if strike is not None else primary.get("strike")
            right = primary.get("right") or right

        # Fallback: ATM-ish from chain rows
        if ask <= 0:
            side = "all_calls" if action == "BUY_CALLS" else "all_puts"
            rows = flow.get(side) or []
            if not rows:
                chain = flow.get("options_chain") or {}
                rows = chain.get("calls" if action == "BUY_CALLS" else "puts") or []
            spot = float(flow.get("stock_price") or 0)
            if rows and spot > 0:
                best = min(rows, key=lambda r: abs(float(r.get("strike") or 0) - spot))
                ask = float(best.get("ask") or best.get("last_price") or best.get("entry_mark") or 0)
                bid = float(best.get("bid") or best.get("last_price") or 0)
                mid = float(best.get("mid") or ((ask + bid) / 2 if ask and bid else 0))
                strike = best.get("strike", strike)

        entry = ask if ask > 0 else (mid if mid > 0 else bid)
        return {
            "entry_ask": entry,
            "bid": bid,
            "ask": ask if ask > 0 else entry,
            "mid": mid,
            "strike": strike,
            "right": right,
            "tp1": float(contract.get("tp1") or (primary or {}).get("tp1") or 0) or None,
            "stop": float(contract.get("stop") or (primary or {}).get("stop") or 0) or None,
            "expiry": (
                contract.get("expiry")
                or contract.get("expiration")
                or (primary or {}).get("expiry")
            ),
            "dte": contract.get("dte") if contract.get("dte") is not None else (primary or {}).get("dte"),
        }

    @staticmethod
    def _tenor_label(dte: Optional[int], expiry: Any, flow_label: Any = None) -> str:
        """Human tenor for Stage A learning charts."""
        label = str(flow_label or "")
        if "0DTE" in label.upper() or (dte is not None and int(dte) == 0):
            return "0DTE"
        if "1DTE" in label.upper() or (dte is not None and int(dte) == 1):
            return "1DTE"
        if dte is None:
            # Stage A Boss chain is almost always today's 0DTE during RTH
            return "0DTE?"
        d = int(dte)
        if d <= 0:
            return "0DTE"
        if d == 1:
            return "1DTE"
        if d <= 7:
            return f"{d}D · ~1W"
        if d <= 14:
            return f"{d}D · ~2W"
        if d <= 45:
            return f"{d}D · ~1M"
        return f"{d}D"

    @staticmethod
    def _pnl_dollars_1ct(entry_ask: float, exit_bid: Optional[float], contracts: int = 1) -> Optional[float]:
        if not entry_ask or entry_ask <= 0 or exit_bid is None or exit_bid <= 0:
            return None
        n = max(1, int(contracts or 1))
        return round((float(exit_bid) - float(entry_ask)) * 100.0 * n, 2)

    def consecutive_losses(self):
        """Trailing same-side LOSS streak today -> (action, count) or (None, 0)."""
        today = datetime.now().date().isoformat()
        closed_today = [
            t for t in self.closed
            if str(t.get("exit_time") or "").startswith(today)
        ]
        if not closed_today:
            return None, 0
        last = closed_today[-1]
        if last.get("outcome") != "LOSS":
            return None, 0
        side = last.get("action")
        n = 0
        for t in reversed(closed_today):
            if t.get("outcome") != "LOSS" or t.get("action") != side:
                break
            n += 1
        return side, n

    def _row_view(self, t: Dict[str, Any], status: str) -> Dict[str, Any]:
        entry_ask = t.get("entry_ask")
        entry_bid = t.get("entry_bid")
        mark = t.get("last_mark") if status == "OPEN" else t.get("exit_mark")
        pnl_pct = t.get("last_pnl_pct") if status == "OPEN" else t.get("pnl_pct")
        pnl_usd = t.get("last_pnl_usd") if status == "OPEN" else t.get("pnl_usd")
        if pnl_usd is None and entry_ask and mark:
            pnl_usd = self._pnl_dollars_1ct(float(entry_ask), float(mark), int(t.get("contracts") or 1))
        return {
            "id": t.get("id"),
            "status": status,
            "action": t.get("action"),
            "right": t.get("right"),
            "strike": t.get("strike"),
            "contracts": t.get("contracts") or 1,
            "entry": entry_ask,
            "entry_ask": entry_ask,
            "entry_bid": entry_bid,
            "mark": mark,
            "exit_bid": t.get("exit_mark") if status == "CLOSED" else None,
            "ask": t.get("last_ask") or entry_ask,
            "bid": mark if status == "OPEN" else t.get("exit_mark"),
            "pnl_pct": pnl_pct,
            "pnl_usd": pnl_usd,
            "confidence": t.get("confidence"),
            "outcome": t.get("outcome") if status == "CLOSED" else None,
            "reason": t.get("reason"),
            "exit_reason": t.get("exit_reason") if status == "CLOSED" else None,
            "time": (t.get("exit_time") if status == "CLOSED" else None) or t.get("entry_time"),
            "entry_time": t.get("entry_time"),
            "expiry": t.get("expiry"),
            "dte": t.get("dte"),
            "tenor": t.get("tenor") or self._tenor_label(
                t.get("dte"),
                t.get("expiry"),
                t.get("expiration_label") or ("0DTE" if t.get("dte") in (0, "0", None) else None),
            ),
            "hold_seconds": t.get("hold_seconds"),
            "lesson": t.get("lesson"),
        }

    def today_report(self) -> Dict[str, Any]:
        """UI/API friendly report of what was learned today."""
        today = datetime.now().date().isoformat()
        closed_today = [
            t for t in self.closed
            if str(t.get("exit_time") or "").startswith(today)
        ]
        opens = list(self.open)
        recent_closed = list(reversed(closed_today[-12:]))
        rows = [self._row_view(t, "OPEN") for t in opens] + [
            self._row_view(t, "CLOSED") for t in recent_closed
        ]
        base = self.summary()
        base["rows"] = rows
        base["takeaways"] = self._takeaways(closed_today, opens)
        # Helpful aggregate for charts
        wins = [t for t in closed_today if t.get("outcome") == "WIN"]
        if wins:
            avg_win = sum(float(t.get("pnl_pct") or 0) for t in wins) / len(wins)
            avg_win_usd = sum(float(t.get("pnl_usd") or 0) for t in wins) / len(wins)
            base["avg_win_pct"] = round(avg_win, 1)
            base["avg_win_usd_1ct"] = round(avg_win_usd, 2)
        losses = [t for t in closed_today if t.get("outcome") == "LOSS"]
        if losses:
            avg_loss = sum(float(t.get("pnl_pct") or 0) for t in losses) / len(losses)
            avg_loss_usd = sum(float(t.get("pnl_usd") or 0) for t in losses) / len(losses)
            base["avg_loss_pct"] = round(avg_loss, 1)
            base["avg_loss_usd_1ct"] = round(avg_loss_usd, 2)
        try:
            from decision_journal import boss_decision_journal
            base["decision_journal"] = boss_decision_journal.today_report()
        except Exception:
            base["decision_journal"] = None
        try:
            from trade_lesson import pack
            from squeeze_radar import squeeze_radar

            snap = squeeze_radar.snapshot()
            open_rows = [r for r in rows if r.get("status") == "OPEN"]
            base["lessons"] = pack(
                self.last_boss or {},
                shadow_opens=open_rows,
                big_run=snap.get("primary"),
            )
        except Exception:
            base["lessons"] = {
                "odte": None,
                "big_run": None,
                "open_shadows": [r for r in rows if r.get("status") == "OPEN"],
            }
        return base

    def _maybe_open(
        self,
        symbol: str,
        stock_price: float,
        boss_decision: Dict[str, Any],
        flow_data: Dict[str, Any],
        bot_predictions: Dict[str, Any],
        signal_analysis: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        action = str(boss_decision.get("action") or "").upper()
        if action not in ("BUY_CALLS", "BUY_PUTS"):
            return None

        marks = self._extract_entry_mark(boss_decision, action, flow_data)
        entry = float(marks.get("entry_ask") or 0)
        if entry <= 0:
            # Still learn the decision — grade vs underlying move as fallback
            entry = 0.0

        strike = marks.get("strike")
        now = time.time()
        # Block clone spam: same symbol/action/strike still open, or reopened <45s ago
        for t in self.open:
            if (
                t.get("symbol") == symbol
                and t.get("action") == action
                and str(t.get("strike")) == str(strike)
            ):
                return None
        for t in reversed(self.closed[-20:]):
            if t.get("symbol") != symbol or t.get("action") != action:
                continue
            wait = LOSS_REOPEN_SECONDS if t.get("outcome") == "LOSS" else SAME_STRIKE_REOPEN_SECONDS
            same_strike = str(t.get("strike")) == str(strike)
            if same_strike and (now - float(t.get("exit_ts") or 0)) < wait:
                return None
            if t.get("outcome") == "LOSS" and (now - float(t.get("exit_ts") or 0)) < wait:
                return None

        # Tenor from live chain (Stage A is usually 0DTE during RTH)
        raw_dte = marks.get("dte")
        if raw_dte is None:
            raw_dte = flow_data.get("dte")
        try:
            dte_i = int(raw_dte) if raw_dte is not None else None
        except (TypeError, ValueError):
            dte_i = None
        expiry = (
            marks.get("expiry")
            or flow_data.get("expiration")
            or flow_data.get("expiry")
        )
        exp_label = flow_data.get("expiration_label")
        tenor = self._tenor_label(dte_i, expiry, exp_label)

        entry_bid = float(marks.get("bid") or 0) or None
        entry_ask = entry if entry > 0 else None

        trade = {
            "id": f"SHAD_{uuid.uuid4().hex[:10]}",
            "symbol": symbol,
            "action": action,
            "right": marks.get("right"),
            "strike": strike,
            "entry_ask": entry_ask,
            "entry_bid": entry_bid,
            "last_ask": entry_ask,
            "entry_stock": stock_price,
            "tp1": marks.get("tp1"),
            "stop": marks.get("stop"),
            "expiry": expiry,
            "expiration_label": exp_label,
            "dte": dte_i,
            "tenor": tenor,
            "entry_time": datetime.now().isoformat(),
            "entry_ts": now,
            "confidence": boss_decision.get("confidence"),
            "reason": boss_decision.get("reason"),
            "hard_vetoes": list(boss_decision.get("hard_vetoes") or []),
            "lesson": None,
            "flow_metrics": {
                "call_put_ratio": ((flow_data.get("flow_metrics") or {}).get("call_put_ratio")),
                "net_volume_flow": ((flow_data.get("flow_metrics") or {}).get("net_volume_flow")),
                "total_call_volume": ((flow_data.get("flow_metrics") or {}).get("total_call_volume")),
                "total_put_volume": ((flow_data.get("flow_metrics") or {}).get("total_put_volume")),
            },
            "status": "OPEN",
            "learning": True,
            "contracts": contracts_for_premium(entry_ask or 0)
                if entry_ask
                else int(boss_decision.get("contracts") or MIN_CONTRACTS),
        }
        try:
            from trade_lesson import from_boss

            trade["lesson"] = from_boss(boss_decision, shadow_open=trade)
        except Exception:
            trade["lesson"] = None
        self.open.append(trade)
        logger.info(
            f"📘 Shadow LEARN open {trade['id']} {symbol} {action} "
            f"strike={strike} ask={entry_ask} bid={entry_bid} tenor={tenor} conf={trade.get('confidence')}"
        )
        return trade

    def _current_option_bid(
        self,
        trade: Dict[str, Any],
        flow_data: Dict[str, Any],
        boss_decision: Dict[str, Any],
    ) -> Optional[float]:
        # Prefer live Boss contract if same strike
        c = boss_decision.get("contract") or {}
        try:
            if c and str(c.get("strike")) == str(trade.get("strike")):
                bid = float(c.get("bid") or 0)
                # Stage A honesty: mark open P&L at bid only — never mid/ask fallback
                if bid > 0:
                    return bid
                return None
        except Exception:
            pass

        side = "all_calls" if trade.get("action") == "BUY_CALLS" else "all_puts"
        rows = flow_data.get(side) or []
        strike = trade.get("strike")
        if strike is None:
            return None
        for row in rows:
            try:
                if abs(float(row.get("strike") or 0) - float(strike)) < 0.01:
                    bid = float(row.get("bid") or 0)
                    if bid > 0:
                        return bid
                    return None
            except Exception:
                continue
        return None

    def _grade_open(
        self,
        symbol: str,
        stock_price: float,
        flow_data: Dict[str, Any],
        boss_decision: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        now = time.time()
        still_open: List[Dict[str, Any]] = []
        closed: List[Dict[str, Any]] = []

        for trade in self.open:
            if trade.get("symbol") != symbol:
                still_open.append(trade)
                continue

            entry = float(trade.get("entry_ask") or 0)
            mark = self._current_option_bid(trade, flow_data, boss_decision)
            age = now - float(trade.get("entry_ts") or now)
            outcome = None
            pnl_pct = None
            exit_reason = None

            if entry > 0 and mark is not None and mark > 0:
                pnl_pct = ((mark - entry) / entry) * 100.0
                peak = float(trade.get("peak_pnl_pct") or pnl_pct)
                if pnl_pct > peak:
                    peak = pnl_pct
                trade["peak_pnl_pct"] = round(peak, 2)

                tp1 = float(trade.get("tp1") or 0)  # reserved / logged; winners are not clipped at TP1
                stop_px = float(trade.get("stop") or 0)

                # 1) Tight hard stop (price or %)
                if stop_px > 0 and mark <= stop_px:
                    outcome, exit_reason = "LOSS", f"STOP_PX · actual {pnl_pct:+.1f}%"
                elif pnl_pct <= -STOP_PCT:
                    outcome, exit_reason = "LOSS", f"STOP -{STOP_PCT:.0f}% · actual {pnl_pct:+.1f}%"
                # 2) Monster take — allow full runners up to +100%+
                elif pnl_pct >= HARD_WIN_PCT:
                    outcome, exit_reason = "WIN", f"BANK +{HARD_WIN_PCT:.0f}% · actual {pnl_pct:+.1f}%"
                # 3) Trail winners: after +25%, exit on giveback (small/mid wins) — runners keep going
                elif peak >= TRAIL_ARM_PCT and pnl_pct <= (peak - TRAIL_GIVEBACK_PCT):
                    outcome, exit_reason = (
                        "WIN",
                        f"TRAIL peak {peak:+.1f}% → {pnl_pct:+.1f}%",
                    )
                # 4) Time grade — small wins / small losses / flat (variation)
                elif age >= MAX_HOLD_SECONDS:
                    if pnl_pct >= 8:
                        outcome, exit_reason = "WIN", f"TIME · actual {pnl_pct:+.1f}%"
                    elif pnl_pct <= -STOP_PCT / 2:
                        outcome, exit_reason = "LOSS", f"TIME · actual {pnl_pct:+.1f}%"
                    else:
                        outcome, exit_reason = "BREAKEVEN", f"TIME_FLAT · actual {pnl_pct:+.1f}%"
            elif age >= MAX_HOLD_SECONDS:
                # No option marks — grade underlying direction as crude fallback
                entry_px = float(trade.get("entry_stock") or 0)
                if entry_px > 0 and stock_price > 0:
                    move = ((stock_price - entry_px) / entry_px) * 100.0
                    if trade.get("action") == "BUY_PUTS":
                        move = -move
                    pnl_pct = move * 5.0  # rough premium beta proxy for logging only
                    if move >= 0.15:
                        outcome, exit_reason = "WIN", "STOCK_PROXY"
                    elif move <= -0.15:
                        outcome, exit_reason = "LOSS", "STOCK_PROXY"
                    else:
                        outcome, exit_reason = "BREAKEVEN", "STOCK_PROXY_FLAT"
                else:
                    outcome, exit_reason = "BREAKEVEN", "NO_MARK_TIMEOUT"

            if outcome:
                pnl_usd = self._pnl_dollars_1ct(entry, mark, int(trade.get("contracts") or 1)) if entry > 0 else None
                if not trade.get("tenor"):
                    trade["tenor"] = self._tenor_label(
                        trade.get("dte"),
                        trade.get("expiry"),
                        trade.get("expiration_label") or flow_data.get("expiration_label"),
                    )
                    if trade.get("dte") is None and flow_data.get("dte") is not None:
                        try:
                            trade["dte"] = int(flow_data.get("dte"))
                        except (TypeError, ValueError):
                            pass
                trade.update({
                    "status": "CLOSED",
                    "outcome": outcome,
                    "pnl_pct": round(pnl_pct, 2) if pnl_pct is not None else None,
                    "pnl_usd": pnl_usd,
                    "exit_mark": mark,
                    "exit_bid": mark,
                    "exit_stock": stock_price,
                    "exit_time": datetime.now().isoformat(),
                    "exit_ts": now,
                    "exit_reason": exit_reason,
                    "hold_seconds": int(age),
                })
                closed.append(trade)
                self.closed.append(trade)
                logger.info(
                    f"📗 Shadow LEARN close {trade['id']} {outcome} "
                    f"pnl={trade.get('pnl_pct')}% ${trade.get('pnl_usd')}/ct "
                    f"ask→bid {entry}->{mark} tenor={trade.get('tenor')} via {exit_reason}"
                )
            else:
                pnl_usd = self._pnl_dollars_1ct(entry, mark, int(trade.get("contracts") or 1)) if entry > 0 and mark else None
                trade["last_mark"] = mark
                trade["last_mark_ts"] = time.time()
                trade["last_pnl_pct"] = round(pnl_pct, 2) if pnl_pct is not None else None
                trade["last_pnl_usd"] = pnl_usd
                # refresh live ask when Boss still quotes same strike
                try:
                    c = boss_decision.get("contract") or {}
                    if c and str(c.get("strike")) == str(trade.get("strike")):
                        la = float(c.get("ask") or 0)
                        if la > 0:
                            trade["last_ask"] = la
                        if trade.get("entry_bid") in (None, 0) and float(c.get("bid") or 0) > 0:
                            trade["entry_bid"] = float(c.get("bid"))
                except Exception:
                    pass
                if not trade.get("tenor"):
                    trade["tenor"] = self._tenor_label(
                        trade.get("dte") if trade.get("dte") is not None else flow_data.get("dte"),
                        trade.get("expiry") or flow_data.get("expiration"),
                        trade.get("expiration_label") or flow_data.get("expiration_label"),
                    )
                still_open.append(trade)

        self.open = still_open
        return closed

    def _feed_learners(self, trade: Dict[str, Any]) -> None:
        """Stage A: Boss shadow ledger only — do not write ML/bot theater files."""
        return


shadow_learning_engine = ShadowLearningEngine()
