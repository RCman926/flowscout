"""
Liquidity / strike quality gates for Boss contract selection.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Scenario distance bands as % OTM from spot (calls above, puts below)
SCENARIO_BANDS = {
    "Conservative": (0.0, 0.35),   # ATM / tiny OTM
    "Balanced": (0.35, 0.85),      # near-ATM OTM
    "Aggressive": (0.85, 1.6),     # further OTM (still gated)
}

TP1_PCT = 40.0
TP2_PCT = 100.0
STOP_PCT = 40.0


class ContractQualityGates:
    """Pick a tradeable contract or veto with reasons."""

    def __init__(
        self,
        max_spread_pct: float = 12.0,
        min_volume: int = 50,
        min_oi: int = 10,
        max_otm_pct: float = 1.6,
    ):
        self.max_spread_pct = max_spread_pct
        self.min_volume = min_volume
        self.min_oi = min_oi
        self.max_otm_pct = max_otm_pct

    def _score_row(self, row: Dict, stock_price: float, side: str) -> Tuple[float, List[str], Dict]:
        vetoes = []
        strike = float(row.get("strike") or 0)
        bid = float(row.get("bid") or 0)
        ask = float(row.get("ask") or 0)
        last = float(row.get("last_price") or row.get("lastPrice") or 0)
        volume = int(row.get("volume") or 0)
        oi = int(row.get("open_interest") or row.get("openInterest") or 0)
        mid = (bid + ask) / 2.0 if bid > 0 and ask > 0 else last

        if strike <= 0 or stock_price <= 0:
            return -1e9, ["BAD_STRIKE"], {}

        if mid <= 0:
            vetoes.append("NO_MARK")
        if bid > 0 and ask > 0:
            spread_pct = ((ask - bid) / mid) * 100.0 if mid > 0 else 999.0
            if spread_pct > self.max_spread_pct:
                vetoes.append("SPREAD_TOO_WIDE")
        else:
            spread_pct = 999.0
            vetoes.append("NO_BID_ASK")

        if volume < self.min_volume and oi < self.min_oi:
            vetoes.append("THIN_LIQUIDITY")

        # Signed OTM %: calls want strike >= spot, puts strike <= spot
        if side == "CALL":
            otm_pct = (strike - stock_price) / stock_price * 100.0
        else:
            otm_pct = (stock_price - strike) / stock_price * 100.0

        dist_pct = abs(strike - stock_price) / stock_price * 100.0
        if otm_pct < -0.15:  # deep ITM — skip for long premium Stage A
            vetoes.append("TOO_ITM")
        if otm_pct > self.max_otm_pct:
            vetoes.append("TOO_FAR_OTM")

        atm_score = max(0.0, 40.0 - dist_pct * 20.0)
        liq_score = min(30.0, volume / 50.0) + min(15.0, oi / 100.0)
        spread_score = max(0.0, 25.0 - min(spread_pct, 25.0))
        score = atm_score + liq_score + spread_score
        if vetoes:
            score -= 100.0

        iv_raw = row.get("implied_volatility") or row.get("impliedVolatility") or row.get("iv")
        try:
            iv = float(iv_raw) if iv_raw is not None else None
            if iv is not None and iv > 2.0:  # already percent
                iv = iv / 100.0
        except (TypeError, ValueError):
            iv = None

        meta = {
            "strike": strike,
            "side": side,
            "bid": bid,
            "ask": ask,
            "mid": mid,
            "last": last,
            "volume": volume,
            "open_interest": oi,
            "spread_pct": round(spread_pct, 2) if spread_pct < 900 else None,
            "distance_pct": round(dist_pct, 3),
            "otm_pct": round(otm_pct, 3),
            "veto_flags": vetoes,
            "score": round(score, 2),
            "iv": round(iv, 4) if iv is not None else None,
        }
        return score, vetoes, meta

    def _contract_from_meta(self, meta: Dict, side: str) -> Dict:
        ask = float(meta.get("ask") or 0)
        bid = float(meta.get("bid") or 0)
        mid = float(meta.get("mid") or 0)
        last = float(meta.get("last") or 0)
        buy = ask if ask > 0 else (mid or last)
        sell = bid if bid > 0 else (mid or last)
        return {
            "symbol_root": None,
            "right": side,
            "strike": meta["strike"],
            "bid": bid,
            "ask": ask,
            "mid": mid,
            "last": last,
            "entry_mark": buy,
            "exit_mark": sell,
            "volume": meta["volume"],
            "open_interest": meta["open_interest"],
            "spread_pct": meta["spread_pct"],
            "otm_pct": meta.get("otm_pct"),
            "distance_pct": meta.get("distance_pct"),
            "score": meta.get("score"),
            "iv": meta.get("iv"),
            "fill_model": "buy_ask_sell_bid",
        }

    def _scenario_style(self, otm_pct: Optional[float]) -> str:
        if otm_pct is None:
            return "unknown"
        if otm_pct < 0.15:
            return "ATM"
        if otm_pct < 0.55:
            return "near-OTM"
        return "farther-OTM"

    def _scenario_blurb(self, scenario: str, style: str, is_primary: bool) -> str:
        if scenario == "Conservative":
            return "Safer ATM / denser book · tighter spreads preferred"
        if scenario == "Balanced":
            return "Primary paper strike · near-ATM OTM balance" if is_primary else "Near-ATM OTM balance"
        if scenario == "Aggressive":
            return "Further OTM · advisory only · not auto-paper"
        return style

    def _price_plan(self, contract: Dict, scenario: str, is_primary: bool) -> Dict:
        buy = float(contract.get("entry_mark") or contract.get("ask") or contract.get("mid") or 0)
        sell = float(contract.get("exit_mark") or contract.get("bid") or contract.get("mid") or 0)
        mid = float(contract.get("mid") or 0) or ((buy + sell) / 2.0 if buy and sell else buy)
        tp1 = round(buy * (1 + TP1_PCT / 100.0), 4) if buy > 0 else None
        tp2 = round(buy * (1 + TP2_PCT / 100.0), 4) if buy > 0 else None
        stop = round(buy * (1 - STOP_PCT / 100.0), 4) if buy > 0 else None
        mult = 100

        def pnl(target: Optional[float]) -> Optional[float]:
            if buy <= 0 or target is None:
                return None
            return round((target - buy) * mult, 2)

        pnl_tp1 = pnl(tp1)
        pnl_tp2 = pnl(tp2)
        pnl_stop = pnl(stop)
        risk = abs(pnl_stop) if pnl_stop is not None else None

        def rr(reward: Optional[float]) -> Optional[float]:
            if risk is None or risk <= 0 or reward is None:
                return None
            return round(reward / risk, 2)

        spread_warn = bool(contract.get("spread_pct") and contract["spread_pct"] > 8)
        otm = contract.get("otm_pct")
        try:
            otm_f = float(otm) if otm is not None else None
        except (TypeError, ValueError):
            otm_f = None
        style = self._scenario_style(otm_f)

        bid = float(contract.get("bid") or 0)
        ask = float(contract.get("ask") or 0)
        iv = contract.get("iv")
        try:
            iv_f = float(iv) if iv is not None else None
        except (TypeError, ValueError):
            iv_f = None

        return {
            "scenario": scenario,
            "primary": is_primary,
            "advisory_only": scenario == "Aggressive",
            "strike": contract.get("strike"),
            "right": contract.get("right"),
            "style": style,
            "blurb": self._scenario_blurb(scenario, style, is_primary),
            "buy": round(buy, 4) if buy else None,
            "mid": round(mid, 4) if mid else None,
            "sell": round(sell, 4) if sell else None,
            "bid": round(bid, 4) if bid else None,
            "ask": round(ask, 4) if ask else None,
            "tp1": tp1,
            "tp2": tp2,
            "stop": stop,
            "tp1_pct": TP1_PCT,
            "tp2_pct": TP2_PCT,
            "stop_pct": STOP_PCT,
            "cost_1ct": round(buy * mult, 2) if buy > 0 else None,
            "pnl_tp1_1ct": pnl_tp1,
            "pnl_tp2_1ct": pnl_tp2,
            "pnl_stop_1ct": pnl_stop,
            "rr_tp1": rr(pnl_tp1),
            "rr_tp2": rr(pnl_tp2),
            "spread_pct": contract.get("spread_pct"),
            "spread_warn": spread_warn,
            "otm_pct": otm_f,
            "distance_pct": contract.get("distance_pct"),
            "volume": contract.get("volume"),
            "open_interest": contract.get("open_interest"),
            "iv": round(iv_f, 4) if iv_f is not None else None,
            "iv_pct": round(iv_f * 100.0, 1) if iv_f is not None else None,
            "score": contract.get("score"),
            "fill_model": contract.get("fill_model") or "buy_ask_sell_bid",
            "entry_fill": "ASK" if ask > 0 else "MID/LAST",
            "exit_fill": "BID" if bid > 0 else "MID/LAST",
            "contract": contract,
        }

    def market_magnet_context(
        self,
        stock_price: float,
        calls: Optional[List[Dict]] = None,
        puts: Optional[List[Dict]] = None,
    ) -> Dict:
        """Cheap OI walls + approximate max-pain from chain (Stage A decision context)."""
        calls = calls or []
        puts = puts or []

        def _oi(row: Dict) -> int:
            try:
                return int(row.get("open_interest") or row.get("openInterest") or 0)
            except (TypeError, ValueError):
                return 0

        def _vol(row: Dict) -> int:
            try:
                return int(row.get("volume") or 0)
            except (TypeError, ValueError):
                return 0

        def _strike(row: Dict) -> float:
            try:
                return float(row.get("strike") or 0)
            except (TypeError, ValueError):
                return 0.0

        call_wall = max(calls, key=_oi) if calls else None
        put_wall = max(puts, key=_oi) if puts else None
        hot_call = max(calls, key=_vol) if calls else None
        hot_put = max(puts, key=_vol) if puts else None

        # Approximate max pain: strike minimizing total OI*intrinsic at expiry
        strikes = sorted({_strike(r) for r in (calls + puts) if _strike(r) > 0})
        max_pain = None
        if strikes and stock_price > 0:
            call_oi = {_strike(r): _oi(r) for r in calls}
            put_oi = {_strike(r): _oi(r) for r in puts}
            best_cost = None
            for s in strikes:
                cost = 0.0
                for k, oi in call_oi.items():
                    cost += oi * max(0.0, s - k) * 100.0
                for k, oi in put_oi.items():
                    cost += oi * max(0.0, k - s) * 100.0
                if best_cost is None or cost < best_cost:
                    best_cost = cost
                    max_pain = s

        return {
            "call_wall": _strike(call_wall) if call_wall else None,
            "call_wall_oi": _oi(call_wall) if call_wall else None,
            "put_wall": _strike(put_wall) if put_wall else None,
            "put_wall_oi": _oi(put_wall) if put_wall else None,
            "hot_call": _strike(hot_call) if hot_call else None,
            "hot_put": _strike(hot_put) if hot_put else None,
            "hot_call_vol": _vol(hot_call) if hot_call else None,
            "hot_put_vol": _vol(hot_put) if hot_put else None,
            "max_pain": max_pain,
            "spot_vs_max_pain": round(stock_price - max_pain, 2) if max_pain else None,
        }

    def _accept_meta(self, vetoes: List[str], score: float) -> bool:
        hard = set(vetoes) & {"SPREAD_TOO_WIDE", "NO_MARK", "TOO_FAR_OTM", "BAD_STRIKE", "TOO_ITM"}
        return (not vetoes) or (not hard and score > 0)

    def select_contract(
        self,
        action: str,
        stock_price: float,
        calls: Optional[List[Dict]] = None,
        puts: Optional[List[Dict]] = None,
    ) -> Dict:
        scenarios = self.select_scenarios(action, stock_price, calls=calls, puts=puts)
        primary = next((s for s in scenarios.get("scenarios", []) if s.get("primary")), None)
        if primary and primary.get("contract"):
            return {
                "ok": True,
                "veto_flags": primary.get("contract", {}).get("veto_flags") or [],
                "contract": primary["contract"],
                "reason": f"Primary {primary['scenario']} {primary['right']} {primary['strike']}",
                "scenarios": scenarios.get("scenarios", []),
                "primary_scenario": primary["scenario"],
            }
        return {
            "ok": False,
            "veto_flags": scenarios.get("veto_flags") or ["NO_QUALITY_CONTRACT"],
            "contract": None,
            "reason": scenarios.get("reason") or "No quality contract",
            "scenarios": scenarios.get("scenarios", []),
            "primary_scenario": None,
        }

    def select_scenarios(
        self,
        action: str,
        stock_price: float,
        calls: Optional[List[Dict]] = None,
        puts: Optional[List[Dict]] = None,
    ) -> Dict:
        if action not in ("BUY_CALLS", "BUY_PUTS") or stock_price <= 0:
            return {
                "ok": False,
                "veto_flags": ["NO_ACTION_OR_PRICE"],
                "scenarios": [],
                "reason": "No actionable side or spot price",
            }

        side = "CALL" if action == "BUY_CALLS" else "PUT"
        rows = calls if side == "CALL" else puts
        rows = rows or []
        if not rows:
            return {
                "ok": False,
                "veto_flags": ["NO_CHAIN"],
                "scenarios": [],
                "reason": f"No {side} chain rows",
            }

        ranked: List[Tuple[float, List[str], Dict]] = []
        for row in rows:
            score, vetoes, meta = self._score_row(row, stock_price, side)
            if meta:
                ranked.append((score, vetoes, meta))
        ranked.sort(key=lambda x: x[0], reverse=True)

        picked: Dict[str, Dict] = {}
        used_strikes = set()
        for name, (lo, hi) in SCENARIO_BANDS.items():
            target = (lo + hi) / 2.0
            # Prefer in-band; else nearest acceptable strike to band center
            candidates = []
            for score, vetoes, meta in ranked:
                if not self._accept_meta(vetoes, score):
                    continue
                strike = meta["strike"]
                if strike in used_strikes:
                    continue
                otm = float(meta.get("otm_pct") or 0)
                in_band = lo <= otm < hi
                dist = abs(otm - target)
                # Soft-allow slightly outside band for coarse strike grids
                if in_band or abs(otm - target) <= max(0.55, (hi - lo)):
                    candidates.append((0 if in_band else 1, dist, -score, score, vetoes, meta))
            candidates.sort()
            if candidates:
                _, _, _, score, vetoes, meta = candidates[0]
                contract = self._contract_from_meta(meta, side)
                contract["veto_flags"] = vetoes
                picked[name] = contract
                used_strikes.add(meta["strike"])

        # Fallback: closest ATM for Conservative if still empty
        if "Conservative" not in picked:
            for score, vetoes, meta in ranked[:20]:
                if self._accept_meta(vetoes, score):
                    contract = self._contract_from_meta(meta, side)
                    contract["veto_flags"] = vetoes
                    picked["Conservative"] = contract
                    break

        if not picked:
            best_vetoes = ranked[0][1] if ranked else ["NO_QUALITY_CONTRACT"]
            return {
                "ok": False,
                "veto_flags": best_vetoes,
                "scenarios": [],
                "reason": f"No quality {side} scenarios near ATM",
            }

        # Primary: Balanced if liquid, else Conservative
        primary_name = "Balanced" if "Balanced" in picked else "Conservative"
        if primary_name not in picked:
            primary_name = next(iter(picked))

        scenarios = []
        for name in ("Conservative", "Balanced", "Aggressive"):
            if name not in picked:
                continue
            scenarios.append(
                self._price_plan(picked[name], name, is_primary=(name == primary_name))
            )

        return {
            "ok": True,
            "veto_flags": [],
            "scenarios": scenarios,
            "primary_scenario": primary_name,
            "reason": f"{len(scenarios)} scenarios; primary={primary_name}",
        }


contract_quality_gates = ContractQualityGates()
