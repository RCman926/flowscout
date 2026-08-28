"""
Server-side kill switch for Boss auto paper trading.

Default: DISARMED. UI / API must arm before can_auto_paper executes.
Persists to paper_arm_state.json so restarts keep the last choice.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from cloud_runtime import (
    is_cloud_mode,
    paper_auto_armed_env,
    state_path,
    unattended_may_auto_arm,
)

logger = logging.getLogger(__name__)

STATE_FILE = state_path("paper_arm_state.json")


class PaperArmState:
    def __init__(self, state_file: Path = STATE_FILE):
        self.state_file = Path(state_file)
        env_default = paper_auto_armed_env()
        self._armed = env_default
        self._updated_at: str | None = None
        self._load()
        if is_cloud_mode() and self._armed:
            self._armed = False
            logger.info("Cloud host: paper DISARMED (PAPER_AUTO_ARMED ignored)")

    def _load(self) -> None:
        if not self.state_file.exists():
            return
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            if "armed" in data:
                self._armed = bool(data["armed"])
            self._updated_at = data.get("updated_at")
            unattended = unattended_may_auto_arm()
            paper_env = paper_auto_armed_env()
            day = str(self._updated_at or "")[:10]
            today = datetime.now().strftime("%Y-%m-%d")
            if is_cloud_mode():
                if self._armed:
                    self._armed = False
                    logger.info("Cloud host: persisted paper arm cleared — DISARMED")
                return
            if self._armed and not (unattended or paper_env) and day != today:
                self._armed = False
                logger.info("Paper arm expired (prior day) — DISARMED")
        except Exception as e:
            logger.warning(f"Could not load paper arm state: {e}")

    def _save(self) -> None:
        try:
            payload = {
                "armed": self._armed,
                "updated_at": self._updated_at or datetime.now().isoformat(),
            }
            self.state_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Could not save paper arm state: {e}")

    @property
    def armed(self) -> bool:
        return bool(self._armed)

    def set_armed(self, armed: bool) -> Dict[str, Any]:
        self._armed = bool(armed)
        self._updated_at = datetime.now().isoformat()
        self._save()
        logger.info(f"Paper auto {'ARMED' if self._armed else 'DISARMED'}")
        return self.status()

    def status(self) -> Dict[str, Any]:
        return {
            "armed": self.armed,
            "updated_at": self._updated_at,
            "message": "Paper auto armed — Boss may open local_sim trades"
            if self.armed
            else "Paper auto disarmed — Boss decisions only (no entries)",
        }


paper_arm_state = PaperArmState()
