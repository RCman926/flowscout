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

## Offline / cloud

Needs network for delayed Yahoo (and optional Polygon/IBKR). Hosting in the cloud does **not** unlock offline trading. Stay local for Stage A.

## Config

See `ENV_TEMPLATE.txt`. Keep paper **DISARMED** until shadow W/L looks real.
