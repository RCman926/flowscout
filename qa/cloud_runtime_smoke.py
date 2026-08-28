"""
Cloud / always-on smoke — run: python qa/cloud_runtime_smoke.py

Proves: paper DISARMED, IBKR off, yfinance is the cloud feed,
missing Polygon key does not fail boot, UNATTENDED does not arm,
a stranger cannot ARM without a desk token.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _clear_paid_keys(env: dict) -> dict:
    env = dict(env)
    for key in (
        "POLYGON_API_KEY",
        "MASSIVE_API_KEY",
        "FINNHUB_API_KEY",
        "ALPHA_VANTAGE_API_KEY",
        "FLOWSCOUT_DESK_TOKEN",
        "UNATTENDED",
        "PAPER_AUTO_ARMED",
        "IBKR_ENABLED",
        "FLOWSCOUT_CLOUD_FEED",
        "RAILWAY_ENVIRONMENT",
        "RAILWAY_PROJECT_ID",
    ):
        env.pop(key, None)
    return env


def test_cloud_config_files_disarmed():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    railway = (ROOT / "railway.toml").read_text(encoding="utf-8")
    nixpacks = (ROOT / "nixpacks.toml").read_text(encoding="utf-8")
    for text, name in (
        (dockerfile, "Dockerfile"),
        (compose, "docker-compose.yml"),
        (nixpacks, "nixpacks.toml"),
    ):
        assert "PAPER_AUTO_ARMED" in text and "false" in text.lower(), name
        assert "IBKR_ENABLED" in text and "0" in text, name
        assert "FLOWSCOUT_CLOUD" in text, name
    assert "healthcheckPath" in railway
    assert "/healthz" in railway
    assert "ALWAYS" in railway or "ON_FAILURE" in railway
    assert "restart: unless-stopped" in compose
    print("OK cloud config files: paper false, IBKR 0, healthz, restart")


def test_missing_polygon_does_not_fail_boot():
    env = _clear_paid_keys(os.environ)
    env["FLOWSCOUT_CLOUD"] = "1"
    env["PAPER_AUTO_ARMED"] = "false"
    env["IBKR_ENABLED"] = "0"
    with patch.dict(os.environ, env, clear=True):
        import importlib
        import cloud_runtime

        importlib.reload(cloud_runtime)
        cloud_runtime.assert_cloud_boot()  # must not raise
        snap = cloud_runtime.runtime_snapshot()
        assert snap["polygon_required"] is False
        assert snap["feed"] == "yfinance"
        assert snap["quotes_live"] is False
        assert snap["ibkr_enabled"] is False
        assert snap["paper_auto_armed_env"] is False
        assert cloud_runtime.polygon_key_configured() is False
        print("OK cloud boot without Polygon key → yfinance delayed")


def test_cloud_selects_yfinance_not_polygon():
    env = _clear_paid_keys(os.environ)
    env["FLOWSCOUT_CLOUD"] = "1"
    env["IBKR_ENABLED"] = "0"
    with patch.dict(os.environ, env, clear=True):
        import importlib
        import cloud_runtime

        importlib.reload(cloud_runtime)
        assert cloud_runtime.cloud_feed_name() == "yfinance"
        assert cloud_runtime.allow_source_for_0dte("yfinance") is True
        assert cloud_runtime.allow_source_for_0dte("Polygon") is False
        assert cloud_runtime.allow_source_for_0dte("Finnhub") is False
        assert cloud_runtime.allow_source_for_0dte("IBKR") is False

        from multi_source_flow_tracker import MultiSourceFlowTracker

        tracker = MultiSourceFlowTracker()
        assert tracker.available_sources[0] == "yfinance"
        assert tracker.primary_source() == "yfinance"
        assert "IBKR" not in tracker.available_sources
        print("OK cloud 0DTE source is yfinance (Polygon not required)")


def test_paper_stays_disarmed_even_if_env_true():
    env = _clear_paid_keys(os.environ)
    env["FLOWSCOUT_CLOUD"] = "1"
    env["PAPER_AUTO_ARMED"] = "true"
    env["UNATTENDED"] = "1"
    with patch.dict(os.environ, env, clear=True):
        import importlib
        import cloud_runtime

        importlib.reload(cloud_runtime)
        cloud_runtime.assert_cloud_boot()
        assert cloud_runtime.paper_auto_armed_env() is False
        assert cloud_runtime.unattended_may_auto_arm() is False
        from paper_arm_state import PaperArmState

        with tempfile.TemporaryDirectory() as td:
            arm = PaperArmState(state_file=Path(td) / "arm.json")
            assert arm.armed is False
            # Persisted ARMED file must not come back live on a cloud boot.
            arm.set_armed(True)
            arm2 = PaperArmState(state_file=Path(td) / "arm.json")
            assert arm2.armed is False
        print("OK cloud ignores PAPER_AUTO_ARMED/UNATTENDED — stays DISARMED")


def test_ibkr_forced_off_in_cloud():
    env = _clear_paid_keys(os.environ)
    env["FLOWSCOUT_CLOUD"] = "1"
    env["IBKR_ENABLED"] = "1"
    with patch.dict(os.environ, env, clear=True):
        import importlib
        import cloud_runtime

        importlib.reload(cloud_runtime)
        cloud_runtime.assert_cloud_boot()
        assert cloud_runtime.ibkr_enabled() is False
        print("OK cloud forces IBKR off")


def test_stranger_cannot_arm():
    env = _clear_paid_keys(os.environ)
    env["FLOWSCOUT_CLOUD"] = "1"
    with patch.dict(os.environ, env, clear=True):
        import importlib
        import cloud_runtime

        importlib.reload(cloud_runtime)

        class _Req:
            headers = {}
            query_params = {}

        assert cloud_runtime.desk_write_permitted(_Req()) is False
        assert cloud_runtime.public_register_allowed() is False

        env["FLOWSCOUT_DESK_TOKEN"] = "desk-secret-token"
        with patch.dict(os.environ, env, clear=True):
            importlib.reload(cloud_runtime)

            class _Authed:
                headers = {"Authorization": "Bearer desk-secret-token"}
                query_params = {}

            class _Stranger:
                headers = {}
                query_params = {}

            assert cloud_runtime.desk_write_permitted(_Authed()) is True
            assert cloud_runtime.desk_write_permitted(_Stranger()) is False
        print("OK cloud ARM gate: stranger denied, desk token allowed")


def test_production_bar_sits_out_when_throttled():
    env = _clear_paid_keys(os.environ)
    env["FLOWSCOUT_CLOUD"] = "1"
    with patch.dict(os.environ, env, clear=True):
        import importlib
        import cloud_runtime

        importlib.reload(cloud_runtime)
        with patch.object(cloud_runtime, "yahoo_is_throttled", return_value=True):
            import production_gates

            importlib.reload(production_gates)
            bar = production_gates.odte_trade_bar()
            assert bar["block"] is True
            assert "CLOUD_YAHOO_THROTTLED" in bar["flags"]
            assert bar["floor"] >= 70
        print("OK cloud throttled Yahoo → Boss NO_TRADE bar")


def test_local_still_allows_yfinance_without_cloud():
    env = _clear_paid_keys(os.environ)
    env.pop("FLOWSCOUT_CLOUD", None)
    with patch.dict(os.environ, env, clear=True):
        import importlib
        import cloud_runtime

        importlib.reload(cloud_runtime)
        assert cloud_runtime.is_cloud_mode() is False
        assert cloud_runtime.allow_source_for_0dte("yfinance") is True
        cloud_runtime.assert_cloud_boot()  # no-op locally
        print("OK local Stage A still uses yfinance without cloud flags")


if __name__ == "__main__":
    test_cloud_config_files_disarmed()
    test_missing_polygon_does_not_fail_boot()
    test_cloud_selects_yfinance_not_polygon()
    test_paper_stays_disarmed_even_if_env_true()
    test_ibkr_forced_off_in_cloud()
    test_stranger_cannot_arm()
    test_production_bar_sits_out_when_throttled()
    test_local_still_allows_yfinance_without_cloud()
    print("\nAll cloud runtime smoke checks passed.")
