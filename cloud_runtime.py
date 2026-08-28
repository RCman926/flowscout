"""
Always-on cloud runtime (Railway / Docker) for Stage A.

Zero paid market-data keys required. Cloud feed = delayed Yahoo (yfinance)
plus the existing yahoo_throttle / source-rotation path. Polygon is an
optional later upgrade — never required, never pretended to be live.

Paper stays DISARMED. IBKR stays off (no TWS on the host). UNATTENDED
does not auto-arm. A stranger with the public URL cannot ARM or trade.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

PLACEHOLDER_MARKERS = (
    "your_",
    "changeme",
    "example",
    "placeholder",
    "replace_me",
)

CLOUD_FEED_NOTE = (
    "Cloud Yahoo is delayed and cloud IPs get throttled. "
    "0DTE Boss sits out more. Cooling holds last-good paint — not live Polygon."
)
LOCAL_FEED_NOTE = "Delayed Yahoo (Stage A). Not a live broker."


def _truthy(name: str, default: str = "") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


def _configured_secret(raw: Optional[str]) -> bool:
    value = (raw or "").strip().strip('"').strip("'")
    if not value:
        return False
    low = value.lower()
    return not any(marker in low for marker in PLACEHOLDER_MARKERS)


def is_cloud_mode() -> bool:
    """True on Railway/Render/Fly or when FLOWSCOUT_CLOUD=1 (Docker image)."""
    if _truthy("FLOWSCOUT_CLOUD"):
        return True
    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_ENVIRONMENT_ID"):
        return True
    if os.getenv("RAILWAY_PROJECT_ID") or os.getenv("RAILWAY_SERVICE_ID"):
        return True
    if os.getenv("RENDER") or os.getenv("FLY_APP_NAME"):
        return True
    return False


def ibkr_enabled() -> bool:
    return _truthy("IBKR_ENABLED")


def paper_auto_armed_env() -> bool:
    """Env default for the kill switch. Cloud always reads as false."""
    if is_cloud_mode():
        return False
    return _truthy("PAPER_AUTO_ARMED")


def unattended_may_auto_arm() -> bool:
    """UNATTENDED may arm paper on a local PC overnight. Never on cloud."""
    if is_cloud_mode():
        return False
    return _truthy("UNATTENDED")


def polygon_key_configured() -> bool:
    return _configured_secret(os.getenv("POLYGON_API_KEY")) or _configured_secret(
        os.getenv("MASSIVE_API_KEY")
    )


def cloud_feed_prefers_polygon() -> bool:
    """Opt-in only. Default cloud feed is yfinance even if a Polygon key exists."""
    return os.getenv("FLOWSCOUT_CLOUD_FEED", "yfinance").strip().lower() in (
        "polygon",
        "massive",
    )


def cloud_feed_name() -> str:
    if (
        is_cloud_mode()
        and cloud_feed_prefers_polygon()
        and polygon_key_configured()
    ):
        return "Polygon"
    return "yfinance"


def allow_source_for_0dte(name: str) -> bool:
    """
    Local: existing rotation (IBKR if enabled, then paid APIs, Yahoo last).
    Cloud: yfinance is the always-on path. Polygon only if explicitly opted in.
    Finnhub / Alpha Vantage are not required and are skipped in cloud (weak options).
    """
    canon = (name or "").strip()
    if not is_cloud_mode():
        return True
    if canon == "yfinance":
        return True
    if canon == "Polygon":
        return cloud_feed_prefers_polygon() and polygon_key_configured()
    return False


def quotes_are_live() -> bool:
    """Stage A Yahoo is delayed. IBKR real-time is local-only and off in cloud."""
    return (not is_cloud_mode()) and ibkr_enabled()


def yahoo_min_interval_seconds() -> float:
    """Cloud IPs trip Yahoo faster — space requests out."""
    return 8.0 if is_cloud_mode() else 2.5


def yahoo_is_throttled() -> bool:
    try:
        from yahoo_throttle import yahoo_throttle

        stats = yahoo_throttle.stats() or {}
        return float(stats.get("backoff_remaining_seconds") or 0) > 0.5
    except Exception:
        return False


def data_dir() -> Path:
    """Persistent desk files. Railway injects RAILWAY_VOLUME_MOUNT_PATH."""
    for key in ("FLOWSCOUT_DATA_DIR", "RAILWAY_VOLUME_MOUNT_PATH"):
        raw = (os.getenv(key) or "").strip()
        if raw:
            path = Path(raw)
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            return path
    if is_cloud_mode():
        for candidate in (Path("/data"), Path("/app/data")):
            if candidate.is_dir():
                return candidate
    return Path(".")


def state_path(filename: str) -> Path:
    return data_dir() / filename


def listen_host_port() -> Tuple[str, int]:
    port = int(os.getenv("PORT") or os.getenv("FLOWSCOUT_PORT") or "8000")
    if is_cloud_mode() or os.getenv("PORT"):
        host = os.getenv("FLOWSCOUT_HOST") or "0.0.0.0"
    else:
        host = os.getenv("FLOWSCOUT_HOST") or "127.0.0.1"
    return host, port


def desk_token_configured() -> bool:
    return _configured_secret(os.getenv("FLOWSCOUT_DESK_TOKEN"))


def extract_request_token(request: Any) -> str:
    headers = getattr(request, "headers", None) or {}
    auth = headers.get("authorization") or headers.get("Authorization") or ""
    if isinstance(auth, str) and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    for key in ("x-desk-token", "X-Desk-Token", "x-auth-token", "X-Auth-Token"):
        value = headers.get(key)
        if value:
            return str(value).strip()
    try:
        query = request.query_params
        for key in ("token", "desk_token"):
            value = query.get(key)
            if value:
                return str(value).strip()
    except Exception:
        pass
    return ""


def public_register_allowed() -> bool:
    if not is_cloud_mode():
        return True
    return _truthy("FLOWSCOUT_ALLOW_REGISTER")


def desk_write_permitted(request: Any) -> bool:
    """
    Local Stage A: ARM stays open (localhost).
    Cloud: require FLOWSCOUT_DESK_TOKEN or a valid user_auth session.
    If neither is set up, ARM is refused — stranger with the URL cannot trade.
    """
    if not is_cloud_mode():
        return True
    token = extract_request_token(request)
    expected = (os.getenv("FLOWSCOUT_DESK_TOKEN") or "").strip()
    if expected and token and token == expected:
        return True
    if token:
        try:
            from user_auth import user_auth

            ok, _username = user_auth.verify_token(token)
            if ok:
                return True
        except Exception:
            pass
    return False


def feed_honesty_fields() -> Dict[str, Any]:
    cloud = is_cloud_mode()
    throttled = yahoo_is_throttled() if cloud else False
    return {
        "cloud": cloud,
        "quotes_live": quotes_are_live(),
        "data_source_hint": cloud_feed_name(),
        "feed_note": CLOUD_FEED_NOTE if cloud else LOCAL_FEED_NOTE,
        "yahoo_cooling": throttled,
        "data_delay_minutes": 0 if quotes_are_live() else 15,
        "data_delay_warning": not quotes_are_live(),
    }


def runtime_snapshot() -> Dict[str, Any]:
    feed = cloud_feed_name()
    try:
        from paper_arm_state import paper_arm_state

        armed = bool(paper_arm_state.armed) if paper_arm_state else False
    except Exception:
        armed = False
    return {
        "ok": True,
        "cloud": is_cloud_mode(),
        "feed": feed,
        "quotes_live": quotes_are_live(),
        "paper_armed": armed,
        "paper_auto_armed_env": paper_auto_armed_env(),
        "ibkr_enabled": ibkr_enabled(),
        "polygon_configured": polygon_key_configured(),
        "polygon_required": False,
        "unattended_auto_arm": unattended_may_auto_arm(),
        "desk_token_configured": desk_token_configured(),
        "data_dir": str(data_dir().resolve()),
        "feed_note": CLOUD_FEED_NOTE if is_cloud_mode() else LOCAL_FEED_NOTE,
    }


def assert_cloud_boot() -> None:
    """
    Cloud starts on yfinance with zero paid keys.
    Does not fail if POLYGON_API_KEY is missing.
    Forces IBKR off and ignores PAPER_AUTO_ARMED / UNATTENDED arming.
    """
    if not is_cloud_mode():
        return
    if ibkr_enabled():
        logger.warning(
            "Cloud boot: IBKR_ENABLED is on — forcing off (no TWS on always-on host)."
        )
        os.environ["IBKR_ENABLED"] = "0"
    if _truthy("PAPER_AUTO_ARMED"):
        logger.warning("Cloud boot: PAPER_AUTO_ARMED ignored — paper stays DISARMED.")
        os.environ["PAPER_AUTO_ARMED"] = "false"
    if _truthy("UNATTENDED"):
        logger.warning("Cloud boot: UNATTENDED does not auto-arm paper.")
    if cloud_feed_prefers_polygon() and not polygon_key_configured():
        logger.warning(
            "FLOWSCOUT_CLOUD_FEED=polygon but no key — using delayed yfinance."
        )
    logger.info(
        "Cloud boot: feed=%s (delayed Yahoo, quotes_live=false). "
        "Polygon optional=%s required=false. Paper DISARMED. IBKR off.",
        cloud_feed_name(),
        polygon_key_configured(),
    )


def apply_cloud_boot_policy() -> Dict[str, Any]:
    assert_cloud_boot()
    if is_cloud_mode():
        try:
            from paper_arm_state import paper_arm_state

            if paper_arm_state is not None:
                paper_arm_state.set_armed(False)
                logger.info("Cloud boot: paper DISARMED (stranger cannot auto-enter).")
        except Exception as exc:
            logger.warning("Cloud boot disarm skipped: %s", exc)
    return runtime_snapshot()
