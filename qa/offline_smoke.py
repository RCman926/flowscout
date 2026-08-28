"""
Offline desk smoke — run: python qa/offline_smoke.py

Proves the FastAPI desk boots with Yahoo/network disabled:
health OK, dashboard served, WebSocket connects, Boss does not auto-paper,
offline/stale is visible, snapshot survives a second load. No live fetches.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# MUST be set before importing the server / tracker
os.environ["FLOWSCOUT_OFFLINE"] = "1"
os.environ["YAHOO_DISABLED"] = "1"
os.environ["IBKR_ENABLED"] = "0"
os.environ["PAPER_AUTO_ARMED"] = "false"
os.environ["UNATTENDED"] = "0"
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["TELEGRAM_CHAT_ID"] = ""

_TD = tempfile.TemporaryDirectory()
_SNAP = Path(_TD.name) / "offline_snapshot.json"
os.environ["FLOWSCOUT_OFFLINE_SNAPSHOT"] = str(_SNAP)

# Seed a last-good snapshot so the second-boot path has paint
_SNAP.write_text(
    json.dumps(
        {
            "saved_at": "2026-08-27T20:00:00",
            "captured_at": "2026-08-27T20:00:00",
            "captured_ts": 1756324800.0,
            "symbol": "SPY",
            "stock_price": 512.34,
            "flow": {
                "symbol": "SPY",
                "stock_price": 512.34,
                "regular_close": 512.34,
                "all_calls": [{"strike": 512, "bid": 0.90, "ask": 1.10, "last_price": 1.00}],
                "all_puts": [{"strike": 512, "bid": 0.80, "ask": 1.00, "last_price": 0.90}],
                "data_source": "yfinance",
                "data_freshness": "NEW",
                "boss_decision": {
                    "action": "BUY_CALLS",
                    "confidence": 62,
                    "can_auto_paper": True,
                    "reason": "last live paint",
                    "contract": {"strike": 512, "right": "CALL", "ask": 1.1, "bid": 0.9},
                },
            },
            "boss_decision": {
                "action": "BUY_CALLS",
                "confidence": 62,
                "can_auto_paper": True,
                "reason": "last live paint",
                "contract": {"strike": 512, "right": "CALL", "ask": 1.1, "bid": 0.9},
            },
        }
    ),
    encoding="utf-8",
)


class _BoomTicker:
    def __init__(self, *a, **k):
        raise RuntimeError("Yahoo disabled — offline smoke must not fetch live data")

    def history(self, *a, **k):
        raise RuntimeError("Yahoo disabled")

    @property
    def options(self):
        raise RuntimeError("Yahoo disabled")

    @property
    def info(self):
        raise RuntimeError("Yahoo disabled")


def _ban_yahoo():
    import yfinance as yf

    yf.Ticker = _BoomTicker  # type: ignore[misc]


def test_offline_server():
    from fastapi.testclient import TestClient

    import zerodte_websocket_server as srv

    _ban_yahoo()

    from offline_mode import live_market_blocked, status_dict, forced_offline

    assert forced_offline() is True
    assert live_market_blocked() is True
    st = status_dict()
    assert st["live_fetches"] is False
    assert st["has_snapshot"] is True

    from paper_arm_state import paper_arm_state

    paper_arm_state.set_armed(False)
    assert paper_arm_state.armed is False

    errors = []

    def _trap(loop, context):
        err = context.get("exception") or context.get("message")
        errors.append(str(err))

    with TestClient(srv.app) as client:
        # Health
        h = client.get("/health")
        assert h.status_code == 200, h.text
        body = h.json()
        assert body.get("status") in ("healthy", "degraded")
        off = body.get("offline") or {}
        assert off.get("offline") is True or off.get("forced") is True
        assert off.get("live_fetches") is False
        assert off.get("data_freshness") == "OFFLINE"
        assert off.get("has_snapshot") is True

        # Dashboard HTML
        page = client.get("/")
        assert page.status_code == 200, page.text
        html = page.text
        assert "zerodte" in html.lower() or "boss" in html.lower() or "FlowScout" in html or "0DTE" in html
        assert "OFFLINE" in html or "offline" in html  # badge / status copy in client

        # Paper stays DISARMED
        arm = client.get("/api/paper-trading/arm")
        assert arm.status_code == 200, arm.text
        arm_j = arm.json()
        armed = arm_j.get("armed")
        if armed is None and isinstance(arm_j.get("status"), dict):
            armed = arm_j["status"].get("armed")
        assert armed is False, arm_j

        # Desk health names OFFLINE / stale, not a crash
        dh = client.get("/api/desk-health")
        assert dh.status_code == 200, dh.text
        desk = dh.json()
        assert desk.get("status") in ("OFFLINE", "CLOSED", "HEALTHY", "DEGRADED")
        blob = json.dumps(desk).lower()
        assert "offline" in blob or "stale" in blob or desk.get("status") == "OFFLINE"

        # WebSocket connects and paints stale/offline — no live Yahoo
        with client.websocket_connect("/ws/SPY") as ws:
            first = ws.receive_json()
            kinds = [first.get("type")]
            payloads = [first]
            for _ in range(5):
                try:
                    nxt = ws.receive_json()
                    payloads.append(nxt)
                    kinds.append(nxt.get("type"))
                except Exception:
                    break
            connected_offline = any(
                p.get("type") == "connected"
                and (p.get("offline") or p.get("data_freshness") == "OFFLINE")
                for p in payloads
            )
            assert connected_offline or "connected" in kinds, (kinds, first)
            flow_msgs = [p for p in payloads if p.get("type") == "flow_update"]
            assert flow_msgs, kinds
            for payload in flow_msgs:
                data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
                assert data.get("offline") or str(data.get("data_freshness") or "").upper() == "OFFLINE", payload
                boss = data.get("boss_decision") or {}
                if boss:
                    assert boss.get("can_auto_paper") is not True
                    if boss.get("action") in ("BUY_CALLS", "BUY_PUTS"):
                        raise AssertionError("Boss must sit out on stale/offline data, not emit a live ticket")
                if data.get("stock_price"):
                    assert data.get("live") is not True

    assert not errors, f"background traceback: {errors[:3]}"

    # Second load of the same snapshot file (process-restart stand-in)
    from offline_mode import OfflineDesk

    again = OfflineDesk(Path(os.environ["FLOWSCOUT_OFFLINE_SNAPSHOT"])).serve_flow("SPY")
    assert again["stock_price"] == 512.34
    assert again["data_freshness"] == "OFFLINE"
    assert again["boss_decision"]["can_auto_paper"] is False
    print("OK offline server health/dashboard/ws sit-out + snapshot reload")


def test_tracker_does_not_hit_yahoo():
    _ban_yahoo()
    from multi_source_flow_tracker import multi_source_tracker

    data = multi_source_tracker.get_0dte_options_chain("SPY")
    assert isinstance(data, dict)
    assert data.get("offline") is True or data.get("data_freshness") == "OFFLINE"
    assert data.get("live") is not True
    print("OK tracker serves snapshot without Yahoo")


if __name__ == "__main__":
    try:
        test_tracker_does_not_hit_yahoo()
        test_offline_server()
        print("\nAll offline smoke checks passed.")
    finally:
        _TD.cleanup()
