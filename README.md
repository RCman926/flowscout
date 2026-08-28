# FlowScout — Stage A

Local Windows desk for **0DTE SPY Boss** decisions + **shadow ask→bid** grading, plus a separate **Big Run** share scanner. Not an ML prediction platform.

## Quick start

1. `pip install -r requirements.txt`
2. Optional: copy `ENV_TEMPLATE.txt` → `.env` (yfinance works without paid keys; `IBKR_ENABLED=0` by default)
3. Double-click **`START_FLOWSCOUT.bat`** and wait for `SERVER STARTED`
4. Browser opens `http://localhost:8000/?fresh=1`

Do **not** open `zerodte_client_enhanced.html` as `file://` — the live WebSocket needs the FastAPI server.

## What Stage A is

| Desk | Job |
|------|-----|
| **0DTE** | Workers → managers → Boss → shadow ledger (`/api/shadow-learning/today`). Paper only when ARMED. |
| **Big Run** | Delayed Yahoo PRE/BUILDING/HOT watch (`squeeze_radar.py`). Does not override SPY Boss. |

Truth ledger = Boss shadow (buy@ask → mark@bid). Legacy `/performance-stats` and Sharpe theater return **410**.

## Core files

- `zerodte_websocket_server.py` — FastAPI + WS loop
- `zerodte_client_enhanced.html` — UI
- `boss_decision_engine.py`, `manager_layer.py`, workers / gates
- `shadow_learning_engine.py`, `decision_journal.py`
- `squeeze_radar.py` — Big Run
- `paper_trading_engine.py`, `paper_arm_state.py`
- `START_FLOWSCOUT.bat` — primary launch

## Always-on cloud (Railway)

The Cloudflare tunnel (`START_SERVER_AND_TUNNEL.bat`) is **PC-on only** — it dies when Ryan's machine sleeps. For a desk that stays up, deploy the Docker web process.

This is **not live IBKR**. IBKR stays off. Paper auto-trading stays **DISARMED**. Quotes are **delayed Yahoo** (yfinance + `yahoo_throttle`). Cloud IPs get throttled, so 0DTE Boss sits out / NO_TRADE more. Cooling holds last-good paint and shows **throttled / stale** — it does not invent prices and does not pretend to be live Polygon.

**Zero paid market-data keys required.** Polygon is an optional later upgrade (`FLOWSCOUT_CLOUD_FEED=polygon` plus a real key). Free Polygon does not even give delayed quotes — do not set it expecting a live chain.

### Deploy on Railway

1. New project from GitHub (`RCman926/flowscout`), Dockerfile builder (see `railway.toml`).
2. Generate a public HTTPS domain on the service (Settings → Networking).
3. **No secrets required to boot.** Optional env vars only:
   - `PAPER_AUTO_ARMED=false` (image already sets this)
   - `IBKR_ENABLED=0` (image already sets this)
   - `UNATTENDED=0` (ignored for auto-arm in cloud anyway)
   - `FLOWSCOUT_DESK_TOKEN` — optional. If unset, ARM is refused so a stranger with the URL cannot auto-enter. Set this only if you later want to ARM from a trusted client (`Authorization: Bearer …` or `X-Desk-Token`).
   - `POLYGON_API_KEY` — optional, unused unless you also set `FLOWSCOUT_CLOUD_FEED=polygon`.
   - `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` — optional alerts.
4. Attach a **volume** mounted at `/data` (Railway injects `RAILWAY_VOLUME_MOUNT_PATH`). Shadow ledger, paper state, and journal survive restarts. Without a volume, those files reset on each deploy.
5. Deploy. Health check is `/healthz` (paper DISARMED, feed `yfinance`, `ibkr_enabled: false`, `polygon_required: false`).
6. Open the public URL. Confirm Source is **yfinance**, freshness may read delayed/throttled, Boss paper button stays **DISARMED**.

Docker locally (same contract):

```bash
docker compose up --build
```

Restart policy is `unless-stopped` (compose) / `ALWAYS` (Railway). Process listens on `0.0.0.0:$PORT` (8000 by default).

### Cloud honesty

| Claim | Truth |
|-------|--------|
| Market data | Delayed Yahoo. Cloud IPs get throttled. |
| Polygon | Optional upgrade. **Not required.** Missing key does **not** fail boot. |
| IBKR | Off. No TWS on the host. Not a live broker. |
| Paper | `PAPER_AUTO_ARMED=false`. Cloud boot force-disarms. Public ARM is 403 without a desk token / login. |
| Yahoo cooling | Last-good paint + **Throttled · last paint**. Boss NO_TRADE. No invented prices. |

`GET /api/runtime` is public and lists feed / paper / IBKR with no secrets.

## Offline / local

Needs network for delayed Yahoo (and optional Polygon/IBKR). Hosting in the cloud does **not** unlock offline trading or live IBKR. Stay local (`START_FLOWSCOUT.bat`) when you want the Windows + yfinance Stage A default on a home IP (less throttle than cloud).

## Config

See `ENV_TEMPLATE.txt`. Keep paper **DISARMED** until shadow W/L looks real.

Smoke:

```bash
python qa/stage_a_smoke.py
python qa/cloud_runtime_smoke.py
```
