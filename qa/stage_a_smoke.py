"""
Stage A smoke checks — run: python qa/stage_a_smoke.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Ensure kill switch default for tests
os.environ.setdefault("PAPER_AUTO_ARMED", "false")
os.environ.setdefault("PAPER_MAX_CONTRACTS", "1")
os.environ.setdefault("PAPER_DAILY_LOSS_HALT", "500")


def _chain(spot: float = 100.0):
    calls = []
    puts = []
    for k in range(98, 103):
        mid = max(0.15, 2.0 - abs(k - spot) * 0.4)
        spread = 0.04
        row = {
            "strike": float(k),
            "bid": round(mid - spread / 2, 2),
            "ask": round(mid + spread / 2, 2),
            "last_price": mid,
            "volume": 200,
            "open_interest": 500,
        }
        calls.append(dict(row))
        puts.append(dict(row))
    return calls, puts


def test_scenarios():
    from contract_quality_gates import contract_quality_gates

    calls, puts = _chain(100)
    out = contract_quality_gates.select_scenarios("BUY_CALLS", 100.0, calls=calls, puts=puts)
    assert out["ok"], out
    names = {s["scenario"] for s in out["scenarios"]}
    assert "Conservative" in names
    assert any(s.get("primary") for s in out["scenarios"])
    primary = next(s for s in out["scenarios"] if s["primary"])
    assert primary["buy"] and primary["tp1"] and primary["stop"]
    assert primary["scenario"] != "Aggressive" or len(out["scenarios"]) == 1
    assert primary.get("style") in ("ATM", "near-OTM", "farther-OTM", "unknown")
    assert primary.get("cost_1ct") is not None
    assert primary.get("rr_tp1") is not None
    assert primary.get("blurb")
    assert primary.get("pnl_tp1_1ct") is not None
    assert primary.get("fill_model") == "buy_ask_sell_bid"
    assert primary.get("entry_fill") in ("ASK", "MID/LAST")
    assert primary.get("exit_fill") in ("BID", "MID/LAST")
    assert primary.get("mid") is not None
    assert "otm_pct" in primary
    assert primary.get("tp1_pct") == 40.0
    print("OK scenarios", names, "primary=", primary["scenario"], "elite=", primary["style"], primary["rr_tp1"], primary["fill_model"])


def test_boss_disarmed():
    from boss_decision_engine import BossDecisionEngine

    eng = BossDecisionEngine()
    calls, puts = _chain(100)
    # Force a path that may or may not trade — arm gate must hold
    d = eng.decide(
        "SPY",
        100.0,
        flow_signal={"action": "BUY_CALLS", "confidence": 80, "reason": "test"},
        calls=calls,
        puts=puts,
        paper_armed=False,
    )
    assert d["paper_armed"] is False
    assert d["can_auto_paper"] is False
    assert "market_context" in d
    assert "iv_context" in d
    assert "session_context" in d
    assert d.get("fill_model") == "buy_ask_sell_bid"
    assert d.get("executable") is False
    # Quotes may exist but must be marked non-executable when Boss sits out
    for s in d.get("scenarios") or []:
        assert s.get("executable") is False
        assert s.get("advisory_only") is True
        assert s.get("primary") is False
    assert d.get("primary_scenario") is None
    print("OK boss disarmed can_auto_paper=False action=", d["action"], "mp=", d["market_context"].get("max_pain"))


def test_paper_arm_and_fills():
    from paper_arm_state import PaperArmState
    from paper_trading_engine import PaperTradingEngine

    with tempfile.TemporaryDirectory() as td:
        arm = PaperArmState(state_file=Path(td) / "arm.json")
        assert arm.armed is False or True  # may inherit env
        arm.set_armed(False)
        assert arm.armed is False
        arm.set_armed(True)
        assert arm.armed is True

        engine = PaperTradingEngine(trades_file=str(Path(td) / "trades.json"))
        boss = {
            "can_auto_paper": True,
            "action": "BUY_CALLS",
            "symbol": "SPY",
            "confidence": 70,
            "data_quality": "delayed",
            "venue": "local_sim",
            "stock_price": 100,
            "contract": {
                "right": "CALL",
                "strike": 100,
                "bid": 0.90,
                "ask": 1.00,
                "mid": 0.95,
                "entry_mark": 1.00,
            },
            "scenarios": [
                {
                    "scenario": "Balanced",
                    "primary": True,
                    "advisory_only": False,
                    "tp1": 1.4,
                    "tp2": 2.0,
                    "stop": 0.6,
                    "contract": {
                        "right": "CALL",
                        "strike": 100,
                        "bid": 0.90,
                        "ask": 1.00,
                        "mid": 0.95,
                        "entry_mark": 1.00,
                    },
                }
            ],
        }
        res = engine.execute_boss_trade(boss)
        assert res["success"], res
        assert res["trade"]["entry_price"] == 1.00
        assert res["trade"]["data_quality"] == "delayed"

        # Second entry blocked by max open / same symbol
        res2 = engine.execute_boss_trade(boss)
        assert not res2["success"]

        exits = engine.manage_boss_positions("SPY", 100.0, 0.95, boss, option_bid=0.55)
        assert exits and exits[0]["success"]
        print("OK paper fill + exit", exits[0].get("exit_reason"))


def test_kill_switch_blocks_execute():
    from paper_trading_engine import PaperTradingEngine
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as td:
        engine = PaperTradingEngine(trades_file=str(Path(td) / "t.json"))
        res = engine.execute_boss_trade(
            {
                "can_auto_paper": False,
                "action": "BUY_CALLS",
                "contract": {"ask": 1.0, "entry_mark": 1.0, "mid": 1.0, "strike": 100, "right": "CALL"},
                "symbol": "SPY",
            }
        )
        assert not res["success"]
        print("OK kill switch blocks entry")


def test_veto_sets_aligned():
    from session_hard_flags import HARD_SESSION, STRUCTURE_HARD
    from manager_layer import run_structure_manager

    assert "AWAITING_FIRST_BREAK" in HARD_SESSION
    assert "AWAITING_FIRST_BREAK" in STRUCTURE_HARD
    st = run_structure_manager(
        {"richness": "FAIR", "veto_flags": []},
        {"ok": True, "veto_flags": [], "contract": {"strike": 100}},
        ["AWAITING_FIRST_BREAK"],
    )
    assert "AWAITING_FIRST_BREAK" in st["hard_vetoes"]
    assert st["posture"] == "RED"
    assert st["thesis"] == "BLOCK"
    print("OK veto alignment AWAITING_FIRST_BREAK -> STRUCT BLOCK/RED")


def test_session_pass_through_no_desync():
    from boss_decision_engine import BossDecisionEngine

    eng = BossDecisionEngine()
    calls, puts = _chain(100)
    session = {
        "workers": {
            "opening_range": {
                "phase": "OPEN",
                "orb_state": "FIRST_BREAK_HOLDING",
                "action": "BUY_CALLS",
                "confidence": 70,
                "veto_flags": [],
                "first_break": {"side": "UP", "held": True, "failed": False},
                "or5": {"high": 100.5, "low": 99.5},
            },
            "ema_regime": {
                "action": "BUY_CALLS",
                "confidence": 65,
                "veto_flags": [],
                "features": {"ema9": 100.1, "ema21": 99.9, "ema50": 99.5, "ema_trend": "BULL"},
            },
            "iv_regime": {
                "richness": "FAIR",
                "atm_iv": 18.0,
                "realized_vol": 16.0,
                "iv_minus_rv": 2.0,
                "veto_flags": [],
                "features": {"prefer_long_premium": True},
            },
        },
        "direction_hint": {
            "action": "BUY_CALLS",
            "phase": "OPEN",
            "orb_state": "FIRST_BREAK_HOLDING",
            "source": "opening_first_break",
        },
        "veto_flags": [],
    }
    d = eng.decide(
        "SPY",
        100.0,
        flow_signal={"action": "BUY_CALLS", "confidence": 75, "reason": "coherence"},
        calls=calls,
        puts=puts,
        paper_armed=False,
        session_structure=session,
    )
    # Boss must reuse the passed workers blob (no silent re-generate of different OR state)
    assert d["workers"]["opening_range"]["orb_state"] == "FIRST_BREAK_HOLDING"
    assert d["session_context"]["orb_state"] == "FIRST_BREAK_HOLDING"
    assert d["workers"] is session["workers"]
    print("OK session pass-through workers identity preserved")


def test_quote_only_when_hard_session():
    from boss_decision_engine import BossDecisionEngine

    eng = BossDecisionEngine()
    calls, puts = _chain(100)
    session = {
        "workers": {
            "opening_range": {
                "phase": "OPEN",
                "orb_state": "FORMING",
                "action": "NO_TRADE",
                "confidence": 30,
                "veto_flags": ["AWAITING_FIRST_BREAK"],
            },
            "ema_regime": {"action": "BUY_CALLS", "confidence": 70, "veto_flags": [], "features": {}},
            "iv_regime": {"richness": "FAIR", "veto_flags": [], "features": {}},
        },
        "direction_hint": {"action": "NO_TRADE", "orb_state": "FORMING", "source": "awaiting_first_break"},
        "veto_flags": ["AWAITING_FIRST_BREAK"],
    }
    d = eng.decide(
        "SPY",
        100.0,
        flow_signal={"action": "BUY_CALLS", "confidence": 80, "reason": "flow loud"},
        calls=calls,
        puts=puts,
        paper_armed=True,
        session_structure=session,
    )
    assert d["action"] == "NO_TRADE"
    assert d["can_auto_paper"] is False
    assert "AWAITING_FIRST_BREAK" in (d.get("hard_vetoes") or [])
    for s in d.get("scenarios") or []:
        assert s.get("executable") is False
    print("OK hard session blocks auto paper; quotes not executable")


if __name__ == "__main__":
    test_scenarios()
    test_boss_disarmed()
    test_paper_arm_and_fills()
    test_kill_switch_blocks_execute()
    test_veto_sets_aligned()
    test_session_pass_through_no_desync()
    test_quote_only_when_hard_session()
    print("\nAll Stage A smoke checks passed.")
