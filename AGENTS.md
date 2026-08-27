# FlowScout — agent notes

Stage A truth: **Boss + shadow ask→bid + Big Run**. Not an ML / performance_tracker platform.

Live surface only:

- `zerodte_websocket_server.py` — FastAPI + WS loop (`START_FLOWSCOUT.bat` primary)
- `zerodte_client_enhanced.html` — UI (huge; grep, do not read end-to-end)
- `boss_decision_engine.py`, `manager_layer.py`, `session_structure_workers.py`, `session_hard_flags.py`, `contract_quality_gates.py`, `production_gates.py`
- `trade_lesson.py` — plain-English “why you’re in this trade” card
- `shadow_learning_engine.py`, `decision_journal.py`
- `multi_source_flow_tracker.py`, `zerodte_signal_analyzer.py`
- `paper_trading_engine.py`, `paper_arm_state.py`
- `squeeze_radar.py` — multi-name BUILDING/HOT watch (not Boss)
- `desk_health.py`, `trade_health.py`

Ledger: `/api/shadow-learning/today`. Legacy performance routes are 410 stubs. `get_performance_tracker()` returns `None` — never call methods on it without a null guard.

Do not read `_archive_unused/`, JSON dumps, or trade archives. Prefer Grep over opening the full HTML.
