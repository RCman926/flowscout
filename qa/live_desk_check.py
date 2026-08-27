"""
Live desk checks against a running FlowScout server.

    python zerodte_websocket_server.py        # in another shell
    python qa/live_desk_check.py

Stage A surface only: Boss card, trade lesson, shadow ask->bid ledger,
Big Run. Closed/overnight sessions and Yahoo cooldown are NOT failures --
that is the market clock and the throttle doing their job. What IS a
failure is the desk lying about arm state, a legacy ledger route coming
back to life, or a flow_update that blanks a panel the desk already
painted.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_BASE = "http://127.0.0.1:8000"

# Every legacy ledger prefix the server quarantines. If any of these answers
# with anything but 410 the ML/performance_tracker platform is creeping back.
LEGACY_ROUTES = [
    "/performance-stats",
    "/performance/trades",
    "/trade-history",
    "/api/trade-history",
    "/api/bot-performance/today",
    "/api/bot-performance/diagnostic",
    "/api/performance-diagnostics",
    "/api/analytics/time-of-day",
    "/api/analytics/historical-accuracy",
    "/api/export/performance",
    "/api/ml-model-status",
    "/model-performance",
    "/ml-model-info",
    "/market-regime",
]

CLOSED_SESSIONS = {"WEEKEND", "OVERNIGHT", "AFTER_HOURS", "PRE_MARKET", "CLOSED"}

_results: list[tuple[str, str, str]] = []  # (state, name, detail)


def record(state: str, name: str, detail: str = "") -> None:
    _results.append((state, name, detail))
    tag = {"PASS": "PASS", "FAIL": "FAIL", "INFO": "info", "SKIP": "skip"}[state]
    print(f"[{tag:4}] {name}" + (f" -- {detail}" if detail else ""), flush=True)


def check(name: str, ok: bool, detail: str = "") -> bool:
    record("PASS" if ok else "FAIL", name, detail)
    return ok


def get(base: str, path: str, headers: dict | None = None, timeout: float = 30.0):
    """Return (status, body_text, response_headers). Never raises on HTTP status.

    Header keys are lowercased: uvicorn sends them lowercase over HTTP/1.1, so a
    case-sensitive lookup silently misses ETag.
    """
    req = urllib.request.Request(base + path, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace"), _lower(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), _lower(e.headers)


def _lower(headers) -> dict:
    return {str(k).lower(): v for k, v in dict(headers).items()}


def get_json(base: str, path: str, timeout: float = 30.0):
    status, body, hdrs = get(base, path, timeout=timeout)
    try:
        return status, json.loads(body), hdrs
    except Exception:
        return status, None, hdrs


def real_boss(b) -> bool:
    """A Boss payload the desk can actually paint (not None, not {})."""
    return isinstance(b, dict) and bool(b) and b.get("action") is not None


# ---------------------------------------------------------------- HTTP checks


def check_server_up(base: str) -> bool:
    status, doc, _ = get_json(base, "/health")
    if not check("server /health reachable", status == 200, f"status={status}"):
        return False
    if isinstance(doc, dict):
        record("INFO", "health status", str(doc.get("status")))
    return True


def check_legacy_quarantine(base: str) -> None:
    bad = []
    for path in LEGACY_ROUTES:
        status, _, _ = get(base, path, timeout=15.0)
        if status != 410:
            bad.append(f"{path}={status}")
    check(
        "legacy ledger routes all 410",
        not bad,
        "; ".join(bad) if bad else f"{len(LEGACY_ROUTES)} routes quarantined",
    )


def check_desk_health(base: str) -> None:
    status, doc, _ = get_json(base, "/api/desk-health")
    if not check("/api/desk-health 200", status == 200, f"status={status}"):
        return
    if not isinstance(doc, dict):
        check("/api/desk-health json object", False)
        return
    clock = doc.get("clock") or {}
    session = str(clock.get("session") or "")
    check("desk-health has clock.session", bool(session), session)
    check("desk-health has workers", isinstance(doc.get("workers"), dict))
    check("desk-health has managers", isinstance(doc.get("managers"), dict))

    # CLOSED overnight/weekend is the market clock, not a crash. Only an
    # unexpected status on a session we believe is open deserves a FAIL.
    if session in CLOSED_SESSIONS or doc.get("status") == "CLOSED":
        record("INFO", "desk-health session closed (expected off-hours)",
               f"status={doc.get('status')} session={session}")
    else:
        check("desk-health status OK while open", doc.get("status") in ("OK", "WARN"),
              f"status={doc.get('status')}")

    for wname, w in (doc.get("workers") or {}).items():
        if isinstance(w, dict) and w.get("ok") is False:
            record("INFO", f"desk-health worker {wname} not ok", json.dumps(w.get("issues"))[:160])


def check_trade_health(base: str) -> None:
    status, doc, _ = get_json(base, "/api/trade-health")
    if not check("/api/trade-health 200", status == 200, f"status={status}"):
        return
    if isinstance(doc, dict):
        check("trade-health reports armed flag", "armed" in doc, f"armed={doc.get('armed')}")


def check_disarmed(base: str) -> None:
    status, doc, _ = get_json(base, "/api/paper-trading/arm")
    if not check("/api/paper-trading/arm 200", status == 200, f"status={status}"):
        return
    armed = (doc or {}).get("armed")
    check("paper desk is DISARMED", armed is False, f"armed={armed!r}")

    status, doc, _ = get_json(base, "/api/paper-trading/status")
    if status == 200 and isinstance(doc, dict):
        check("paper status agrees on arm state", doc.get("armed") is False,
              f"armed={doc.get('armed')!r}")


def check_shadow_ledger(base: str) -> None:
    status, doc, _ = get_json(base, "/api/shadow-learning/today")
    if not check("/api/shadow-learning/today 200", status == 200, f"status={status}"):
        return
    if not isinstance(doc, dict):
        check("shadow ledger json object", False)
        return
    check("shadow ledger has no error", not doc.get("error"), str(doc.get("error"))[:160])
    for key in ("date", "open_count", "closed_today", "wins_today", "losses_today", "rows"):
        check(f"shadow ledger has {key}", key in doc)
    check("shadow rows is a list", isinstance(doc.get("rows"), list))
    record("INFO", "shadow ledger today",
           f"open={doc.get('open_count')} closed={doc.get('closed_today')} "
           f"W/L={doc.get('wins_today')}/{doc.get('losses_today')}")


def check_big_run(base: str) -> None:
    status, doc, hdrs = get_json(base, "/api/squeeze-radar", timeout=45.0)
    if not check("/api/squeeze-radar 200", status == 200, f"status={status}"):
        return
    if not isinstance(doc, dict):
        check("squeeze-radar json object", False)
        return
    check("squeeze-radar has no error", not doc.get("error"), str(doc.get("error"))[:160])
    for key in ("alerts", "spikes", "squeezes"):
        check(f"squeeze-radar {key} is a list", isinstance(doc.get(key), list))
    record("INFO", "Big Run",
           f"last_scan={doc.get('last_scan')} universe={doc.get('universe_size')} "
           f"alerts={len(doc.get('alerts') or [])}")
    if not doc.get("last_scan"):
        record("INFO", "Big Run has not scanned yet",
               "expected while closed / Yahoo cooling -- not a failure")

    etag = hdrs.get("etag")
    if not etag:
        record("INFO", "squeeze-radar sent no ETag", "revalidation check skipped")
        return
    status2, _, _ = get(base, "/api/squeeze-radar", headers={"If-None-Match": etag}, timeout=45.0)
    check("squeeze-radar revalidates to 304", status2 == 304, f"status={status2}")


def check_yahoo_throttle(base: str) -> None:
    status, doc, _ = get_json(base, "/api/yahoo-throttle")
    if not check("/api/yahoo-throttle 200", status == 200, f"status={status}"):
        return
    if isinstance(doc, dict):
        record("INFO", "yahoo throttle",
               f"allowed={doc.get('allowed')} cache_hits={doc.get('cache_hits')} "
               f"rate_limit_hits={doc.get('rate_limit_hits')} "
               f"backoff_s={doc.get('backoff_remaining_seconds')}")
        if doc.get("rate_limit_hits") or doc.get("backoff_remaining_seconds"):
            record("INFO", "Yahoo is cooling", "expected from a cloud IP -- throttle is working")


def check_html_shell(base: str) -> None:
    status, body, _ = get(base, "/", timeout=60.0)
    if not check("/ serves the desk HTML", status == 200, f"status={status}"):
        return
    for needle in ('id="boss-card"', 'id="boss-action"', 'id="squeeze-radar"'):
        check(f"HTML contains {needle}", needle in body)


# ------------------------------------------------------------------ WS checks


async def _collect_flow_updates(base: str, symbol: str, seconds: float) -> list[dict]:
    try:
        import websockets
    except ImportError:
        record("SKIP", "websocket checks", "pip install websockets")
        return []

    uri = base.replace("http://", "ws://").replace("https://", "wss://") + f"/ws/{symbol}"
    msgs: list[dict] = []
    loop = asyncio.get_event_loop()
    deadline = loop.time() + seconds
    try:
        async with websockets.connect(uri, max_size=None, open_timeout=30) as ws:
            while loop.time() < deadline:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=max(1.0, deadline - loop.time()))
                except asyncio.TimeoutError:
                    break
                try:
                    m = json.loads(raw)
                except Exception:
                    continue
                if m.get("type") == "flow_update":
                    msgs.append(m)
    except Exception as e:
        record("FAIL", "websocket connect", f"{type(e).__name__}: {e}")
    return msgs


def check_ws(base: str, symbol: str, seconds: float) -> None:
    msgs = asyncio.run(_collect_flow_updates(base, symbol, seconds))
    if not msgs:
        record("FAIL", "websocket delivered flow_update", f"none in {seconds:.0f}s")
        return
    record("INFO", "flow_update messages received", str(len(msgs)))

    bosses = [(i, (m.get("data") or {}).get("boss_decision")) for i, m in enumerate(msgs)]
    with_boss = [i for i, b in bosses if real_boss(b)]
    check("at least one flow_update carries a Boss decision", bool(with_boss),
          f"indexes={with_boss}")

    # An empty dict is truthy in JS. Shipping boss_decision:{} is how the
    # Boss card and Lab chrome got blanked between cycles, so the server
    # must either send a real decision or omit the key entirely.
    empties = [i for i, b in bosses if isinstance(b, dict) and not b]
    check("no flow_update ships boss_decision as {}", not empties, f"indexes={empties}")

    # Once the desk has painted a Boss, no later message on the same
    # connection may arrive Boss-less -- that is the refresh blank/jump.
    if with_boss:
        first = with_boss[0]
        regressed = [i for i, b in bosses if i > first and not real_boss(b)]
        check("Boss is carried forward on every later flow_update", not regressed,
              f"boss-less after first paint: indexes={regressed}")

    lessons = [i for i, m in enumerate(msgs) if isinstance((m.get("data") or {}).get("trade_lesson"), dict)]
    check("at least one flow_update carries a trade lesson", bool(lessons), f"indexes={lessons}")
    for i in lessons[:1]:
        lesson = msgs[i]["data"]["trade_lesson"]
        check("trade lesson has an 0dte card", isinstance(lesson.get("odte"), dict),
              f"keys={sorted(lesson)}")
        odte = lesson.get("odte") or {}
        for key in ("headline", "evidence", "invalidation"):
            check(f"trade lesson 0dte has {key}", key in odte)

    if with_boss:
        boss = msgs[with_boss[0]]["data"]["boss_decision"]
        record("INFO", "Boss says",
               f"action={boss.get('action')} conf={boss.get('confidence')} "
               f"executable={boss.get('executable')}")
        check("Boss reports paper_armed False", boss.get("paper_armed") is False,
              f"paper_armed={boss.get('paper_armed')!r}")
        check("Boss reports can_auto_paper False", boss.get("can_auto_paper") is False,
              f"can_auto_paper={boss.get('can_auto_paper')!r}")
        check("Boss states a fill model", boss.get("fill_model") == "buy_ask_sell_bid",
              f"fill_model={boss.get('fill_model')!r}")
        for s in boss.get("scenarios") or []:
            if s.get("executable") is not False and boss.get("can_auto_paper") is False:
                check("disarmed Boss scenarios are advisory only", False,
                      f"{s.get('scenario')} executable={s.get('executable')!r}")
                break
        else:
            check("disarmed Boss scenarios are advisory only", True,
                  f"{len(boss.get('scenarios') or [])} scenario(s)")


# ----------------------------------------------------------------------- main


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default=DEFAULT_BASE, help="server base URL")
    ap.add_argument("--symbol", default="SPY")
    ap.add_argument("--ws-seconds", type=float, default=90.0,
                    help="how long to listen for flow_update broadcasts")
    ap.add_argument("--no-ws", action="store_true", help="skip websocket checks")
    args = ap.parse_args()

    base = args.base.rstrip("/")
    print(f"FlowScout live desk check -> {base}\n")

    if not check_server_up(base):
        print("\nServer is not answering. Start it with: python zerodte_websocket_server.py")
        return 2

    check_legacy_quarantine(base)
    check_desk_health(base)
    check_trade_health(base)
    check_disarmed(base)
    check_shadow_ledger(base)
    check_big_run(base)
    check_yahoo_throttle(base)
    check_html_shell(base)
    if not args.no_ws:
        check_ws(base, args.symbol, args.ws_seconds)

    failed = [r for r in _results if r[0] == "FAIL"]
    passed = [r for r in _results if r[0] == "PASS"]
    print(f"\n{len(passed)} passed, {len(failed)} failed.")
    if failed:
        print("\nFailures:")
        for _, name, detail in failed:
            print(f"  - {name}" + (f" -- {detail}" if detail else ""))
        return 1
    print("\nLive desk check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
