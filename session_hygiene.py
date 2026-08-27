"""
Day-bound session hygiene.

Paper arm does not survive midnight unless UNATTENDED is set this process.
Big Run board from a prior day is cleared. Shadow ledger is kept (that's learning).
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _iso_day(iso: Any) -> str:
    return str(iso or "")[:10]


def apply_session_hygiene() -> Dict[str, Any]:
    unattended = os.getenv("UNATTENDED", "").lower() in ("1", "true", "yes")
    paper_env = os.getenv("PAPER_AUTO_ARMED", "false").lower() in ("1", "true", "yes")
    auto_arm = unattended or paper_env
    notes = []

    try:
        from paper_arm_state import paper_arm_state as arm

        day = _iso_day(arm.status().get("updated_at"))
        if arm.armed and not auto_arm and day != _today():
            arm.set_armed(False)
            notes.append(f"disarmed paper (file day {day or 'n/a'} != {_today()})")
        elif auto_arm:
            notes.append("UNATTENDED/PAPER_AUTO_ARMED — arm left to lifespan")
        elif arm.armed:
            notes.append("paper armed today (explicit)")
    except Exception as e:
        notes.append(f"arm: {e}")

    try:
        path = "squeeze_radar_state.json"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                st = json.load(f)
            scan_day = _iso_day(st.get("last_scan"))
            if scan_day and scan_day != _today():
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "alerts": [],
                            "spikes": [],
                            "squeezes": [],
                            "pres": [],
                            "last_scan": None,
                            "mode": "big_run",
                        },
                        f,
                        indent=2,
                    )
                notes.append(f"cleared Big Run board from {scan_day}")
    except Exception as e:
        notes.append(f"squeeze state: {e}")

    logger.info("session hygiene: " + "; ".join(notes) if notes else "session hygiene: ok")
    return {"unattended": unattended, "notes": notes}
