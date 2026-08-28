"""
Boss decision engine — sole order authority.

Workers -> Managers -> Boss -> paper/live intent
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from datetime import datetime
from zoneinfo import ZoneInfo
import logging

from session_structure_workers import evaluate_session_structure
from contract_quality_gates import contract_quality_gates
from manager_layer import run_direction_manager, run_structure_manager, run_timing_manager, run_risk_manager
from session_hard_flags import HARD_SESSION

logger = logging.getLogger(__name__)



class BossDecisionEngine:
    """Produce one decision per cycle with full audit trail."""

    MIN_CONFIDENCE = 58

    def __init__(self) -> None:
        self.last_decision: Dict[str, Any] = {}

    def decide(
        self,
        symbol: str,
        stock_price: float,
        flow_signal: Optional[Dict] = None,
        calls: Optional[List[Dict]] = None,
        puts: Optional[List[Dict]] = None,
        options_chain: Optional[Dict] = None,
        vix_level: Optional[float] = None,
        now: Optional[datetime] = None,
        paper_armed: bool = False,
        session_structure: Optional[Dict] = None,
        data_stale: bool = False,
        offline: bool = False,
    ) -> Dict[str, Any]:
        flow_signal = flow_signal or {}
        flow_action = flow_signal.get("action", "NO_TRADE")
        flow_confidence = float(flow_signal.get("confidence") or 0)
        flow_reason = flow_signal.get("reasoning") or flow_signal.get("reason") or ""

        # Prefer single session blob from the WS cycle — avoid re-evaluate / desync
        if session_structure and isinstance(session_structure, dict) and session_structure.get("workers"):
            session = session_structure
        else:
            session = evaluate_session_structure(
                symbol,
                stock_price,
                options_chain=options_chain or {"calls": calls or [], "puts": puts or []},
                vix_level=vix_level,
                now=now,
            )
        opening = session.get("workers", {}).get("opening_range", {})
        ema_vote = session.get("workers", {}).get("ema_regime", {})
        iv_vote = session.get("workers", {}).get("iv_regime", {})
        clock = session.get("workers", {}).get("clock") or {}
        tape = session.get("workers", {}).get("tape") or {}
        value = session.get("workers", {}).get("value") or {}

        direction = run_direction_manager(
            opening, ema_vote, flow_action, flow_confidence, flow_reason,
            tape_vote=tape, value_vote=value,
        )

        timing = run_timing_manager(clock, opening)

        tentative = direction.get("thesis", "NO_TRADE")
        quality = {
            "ok": False,
            "veto_flags": ["NO_DIRECTION"],
            "contract": None,
            "reason": "No direction",
            "scenarios": [],
            "primary_scenario": None,
        }
        if tentative in ("BUY_CALLS", "BUY_PUTS") and stock_price > 0:
            quality = contract_quality_gates.select_contract(
                tentative, stock_price, calls=calls, puts=puts
            )

        structure = run_structure_manager(
            iv_vote,
            quality,
            session.get("veto_flags") or [],
        )
        risk = run_risk_manager(tentative)

        action = "NO_TRADE"
        confidence = 30
        reasons = []
        vetoes: List[str] = []

        for v in structure.get("hard_vetoes") or []:
            if v not in vetoes:
                vetoes.append(v)
        for v in session.get("veto_flags") or []:
            if v in HARD_SESSION and v not in vetoes:
                vetoes.append(v)
        for v in (timing.get("veto_flags") or []):
            if v not in vetoes:
                vetoes.append(v)
        for v in (risk.get("veto_flags") or []):
            if v not in vetoes:
                vetoes.append(v)

        timing_ok = timing.get("thesis") == "ALLOW"
        late_only = (
            timing.get("thesis") == "BLOCK"
            and "TOO_LATE_0DTE" in (timing.get("veto_flags") or [])
        )
        managers_agree = (
            direction.get("thesis") in ("BUY_CALLS", "BUY_PUTS")
            and structure.get("thesis") == "ALLOW"
            and risk.get("thesis") == "ALLOW"
            and direction.get("agreement") in ("STRONG", "MODERATE")
            and (timing_ok or late_only)
        )

        if managers_agree and not (set(vetoes) & HARD_SESSION - {"TOO_LATE_0DTE"}) and not structure.get("hard_vetoes"):
            action = direction["thesis"]
            confidence = int(
                0.5 * direction.get("confidence", 50)
                + 0.3 * structure.get("confidence", 50)
                + 0.2 * timing.get("confidence", 50)
            )
            if structure.get("posture") == "CAUTION":
                confidence = max(40, confidence - 10)
                reasons.append("IV/structure caution")
            reasons.append(direction.get("summary", ""))
            reasons.append(structure.get("summary", ""))
            reasons.append(timing.get("summary", ""))
            reasons.append(risk.get("summary", ""))
            try:
                from production_gates import odte_trade_bar

                bar = odte_trade_bar()
            except Exception:
                bar = {"floor": self.MIN_CONFIDENCE, "block": False, "flags": [], "notes": []}
            if bar.get("block"):
                action = "NO_TRADE"
                for f in bar.get("flags") or []:
                    if f not in vetoes:
                        vetoes.append(f)
                reasons.extend(bar.get("notes") or [])
            else:
                floor = int(bar.get("floor") or self.MIN_CONFIDENCE)
                if confidence < floor:
                    action = "NO_TRADE"
                    vetoes.append("BOSS_CONFIDENCE_FLOOR")
                    reasons.append(f"Confidence {confidence} < {floor} (production bar)")
                    reasons.extend(bar.get("notes") or [])
        else:
            if direction.get("agreement") == "SPLIT":
                vetoes.append("MANAGERS_SPLIT")
            if structure.get("thesis") == "BLOCK":
                vetoes.append("STRUCTURE_BLOCK")
            if timing.get("thesis") == "WAIT":
                vetoes.append("TIMING_WAIT")
            if risk.get("thesis") == "BLOCK":
                vetoes.append("RISK_BLOCK")
            reasons.append(direction.get("summary", "No direction"))
            reasons.append(structure.get("summary", "Structure blocked"))
            reasons.append(timing.get("summary", ""))
            reasons.append(risk.get("summary", ""))

        contract = quality.get("contract") if action != "NO_TRADE" else None
        scenarios = list(quality.get("scenarios") or [])
        if action != "NO_TRADE" and not quality.get("ok"):
            action = "NO_TRADE"
            confidence = 25
            vetoes.append("CONTRACT_GATE")
            contract = None

        # Quotes may still show for context when NO_TRADE, but never look executable
        if not scenarios and tentative in ("BUY_CALLS", "BUY_PUTS") and stock_price > 0:
            probe = contract_quality_gates.select_scenarios(
                tentative, stock_price, calls=calls, puts=puts
            )
            scenarios = list(probe.get("scenarios") or [])

        tradeable = action in ("BUY_CALLS", "BUY_PUTS") and contract is not None
        primary_scenario = quality.get("primary_scenario") if tradeable else None

        # Late-day 0DTE + same-side streak brakes (shadow ledger)
        try:
            et = datetime.now(ZoneInfo("America/New_York"))
            minutes_to_close = (16 * 60) - (et.hour * 60 + et.minute)
        except Exception:
            minutes_to_close = 999
        streak_side = None
        streak_n = 0
        try:
            from shadow_learning_engine import shadow_learning_engine
            streak_side, streak_n = shadow_learning_engine.consecutive_losses()
        except Exception:
            pass
        if action in ("BUY_CALLS", "BUY_PUTS"):
            if streak_n >= 2 and streak_side == action:
                action = "NO_TRADE"
                tradeable = False
                contract = None
                flag = "STREAK_BLOCK_CALLS" if streak_side == "BUY_CALLS" else "STREAK_BLOCK_PUTS"
                if flag not in vetoes:
                    vetoes.append(flag)
                reasons.append(f"{flag}: {streak_n} consecutive losses — sit out this side")
            elif minutes_to_close <= 45:
                allow_puts = (
                    action == "BUY_PUTS"
                    and streak_side == "BUY_CALLS"
                    and streak_n >= 2
                    and direction.get("agreement") == "STRONG"
                )
                if not allow_puts:
                    action = "NO_TRADE"
                    tradeable = False
                    contract = None
                    if "TOO_LATE_0DTE" not in vetoes:
                        vetoes.append("TOO_LATE_0DTE")
                    reasons.append(f"Too late for new 0DTE ({minutes_to_close}m to close)")

        # ~$500 premium ticket
        contracts = 1
        if tradeable and contract:
            try:
                from shadow_learning_engine import contracts_for_premium
                contracts = contracts_for_premium(contract.get("ask") or contract.get("mid") or 0)
            except Exception:
                contracts = 10
            contract = dict(contract)
            contract["contracts"] = contracts

        if not tradeable:
            primary_scenario = None
        if scenarios:
            tagged = []
            for s in scenarios:
                row = dict(s)
                if not tradeable:
                    row["executable"] = False
                    row["advisory_only"] = True
                    row["primary"] = False
                    if row.get("blurb") and "not executable" not in str(row["blurb"]).lower():
                        row["blurb"] = f"{row['blurb']} · NOT EXECUTABLE (Boss NO_TRADE)"
                    else:
                        row["blurb"] = "Quote only · Boss NO_TRADE · not paper-executable"
                else:
                    row["executable"] = bool(row.get("primary"))
                    # Aggressive stays advisory even when side is tradeable
                    if row.get("advisory_only"):
                        row["executable"] = False
                tagged.append(row)
            scenarios = tagged

        soft = list(structure.get("soft_vetoes") or [])
        hard = list(structure.get("hard_vetoes") or [])
        # Mirror session hard flags onto hard_vetoes for UI strip consistency
        for v in vetoes:
            if v in HARD_SESSION and v not in hard:
                hard.append(v)
        market = contract_quality_gates.market_magnet_context(
            stock_price, calls=calls, puts=puts
        )
        iv_w = iv_vote or {}
        or_w = opening or {}
        decision = {
            "boss": True,
            "action": action,
            "confidence": int(confidence),
            "symbol": symbol,
            "stock_price": stock_price,
            "contract": contract,
            "scenarios": scenarios,
            "primary_scenario": primary_scenario,
            "invalidation_level": direction.get("invalidation") or session.get("invalidation_level"),
            "reason": " | ".join([r for r in reasons if r])[:500],
            "veto_flags": vetoes,
            "hard_vetoes": hard,
            "soft_vetoes": soft,
            "managers": {
                "direction": direction,
                "structure": structure,
                "timing": timing,
                "risk": risk,
            },
            "workers": session.get("workers", {}),
            "vote_trail": self._vote_trail(direction, structure, timing, risk, flow_action, flow_confidence),
            "session_context": {
                "phase": or_w.get("phase") or session.get("direction_hint", {}).get("phase"),
                "orb_state": or_w.get("orb_state") or session.get("direction_hint", {}).get("orb_state"),
                "first_break": or_w.get("first_break"),
                "direction_source": session.get("direction_hint", {}).get("source"),
                "direction_hint_action": (session.get("direction_hint") or {}).get("action"),
            },
            "iv_context": {
                "richness": iv_w.get("richness"),
                "atm_iv": iv_w.get("atm_iv"),
                "realized_vol": iv_w.get("realized_vol"),
                "iv_minus_rv": iv_w.get("iv_minus_rv"),
                "vix_level": iv_w.get("vix_level"),
                "prefer_long_premium": (iv_w.get("features") or {}).get("prefer_long_premium"),
            },
            "market_context": market,
            "fill_model": "buy_ask_sell_bid",
            "data_quality": "delayed",
            "venue": "local_sim",
            "timestamp": datetime.now().isoformat(),
            "paper_armed": bool(paper_armed),
            "can_auto_paper": bool(tradeable and paper_armed),
            "executable": bool(tradeable),
            "contracts": contracts if tradeable else 0,
            "manager_thesis": direction.get("thesis"),
        }
        stale = bool(data_stale or offline)
        if not stale:
            try:
                from offline_mode import live_market_blocked, payload_is_stale

                stale = bool(live_market_blocked() or payload_is_stale(options_chain))
            except Exception:
                stale = False
        if stale:
            try:
                from offline_mode import sit_out_boss

                prior = dict(self.last_decision) if self.last_decision else decision
                decision = sit_out_boss(prior)
            except Exception:
                decision["action"] = "NO_TRADE"
                decision["can_auto_paper"] = False
                decision["executable"] = False
                decision["paper_armed"] = False
                decision["offline"] = True
                decision["stale_paint"] = True
                decision["data_quality"] = "offline_stale"
                vetoes = list(decision.get("veto_flags") or [])
                if "OFFLINE_STALE" not in vetoes:
                    vetoes.append("OFFLINE_STALE")
                decision["veto_flags"] = vetoes
        self.last_decision = decision
        return decision

    def _vote_trail(self, direction: Dict, structure: Dict, timing: Dict, risk: Dict, flow_action: str, flow_conf: float) -> List[Dict]:
        trail = []
        for v in direction.get("votes") or []:
            trail.append({
                "layer": "worker",
                "name": v.get("source"),
                "action": v.get("action"),
                "confidence": v.get("confidence"),
            })
        trail.append({
            "layer": "manager",
            "name": "direction",
            "action": direction.get("thesis"),
            "confidence": direction.get("confidence"),
            "agreement": direction.get("agreement"),
        })
        trail.append({
            "layer": "manager",
            "name": "structure",
            "action": structure.get("thesis"),
            "confidence": structure.get("confidence"),
            "posture": structure.get("posture"),
        })
        trail.append({
            "layer": "manager",
            "name": "timing",
            "action": timing.get("thesis"),
            "confidence": timing.get("confidence"),
        })
        trail.append({
            "layer": "manager",
            "name": "risk",
            "action": risk.get("thesis"),
            "confidence": risk.get("confidence"),
        })
        trail.append({
            "layer": "worker",
            "name": "flow_input",
            "action": flow_action,
            "confidence": int(flow_conf),
        })
        return trail


boss_decision_engine = BossDecisionEngine()
