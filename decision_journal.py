"""
Boss Decision Journal — learn WHY Boss said CALLS / PUTS / NO_TRADE.

Logs only on meaningful decision changes (not every WS cycle).
Does NOT create shadow P&L, paper trades, or ML WIN/LOSS labels.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from cloud_runtime import state_path
    JOURNAL_FILE = str(state_path("boss_decision_journal.json"))
except Exception:
    JOURNAL_FILE = "boss_decision_journal.json"
MAX_ENTRIES = 400
MIN_SECONDS_BETWEEN_DUPES = 45.0  # even if reason text wobbles


class BossDecisionJournal:
    def __init__(self, path: str = JOURNAL_FILE):
        self.path = path
        self.entries: List[Dict[str, Any]] = []
        self._last_fp: Optional[str] = None
        self._last_ts: float = 0.0
        self._load()

    def _load(self) -> None:
        try:
            if not os.path.exists(self.path):
                return
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.entries = list(data.get("entries") or [])[-MAX_ENTRIES:]
            if self.entries:
                last = self.entries[-1]
                self._last_fp = last.get("fingerprint")
                try:
                    self._last_ts = datetime.fromisoformat(str(last.get("time") or "")).timestamp()
                except Exception:
                    self._last_ts = 0.0
        except Exception as e:
            logger.warning(f"Decision journal load failed: {e}")

    def _save(self) -> None:
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "entries": self.entries[-MAX_ENTRIES:],
                        "updated": datetime.now().isoformat(),
                    },
                    f,
                    indent=2,
                    default=str,
                )
        except Exception as e:
            logger.warning(f"Decision journal save failed: {e}")

    @staticmethod
    def _fingerprint(boss: Dict[str, Any]) -> str:
        action = str(boss.get("action") or "NO_TRADE").upper()
        conf_band = int(float(boss.get("confidence") or 0) // 10) * 10
        vetoes = sorted(str(v) for v in (boss.get("hard_vetoes") or []))
        # Reason stem with every number stripped. Worker confidences like
        # "flow:puts(85)" tick every cycle; leaving them in made the journal
        # log ~6 rows/min instead of only on real decision changes.
        reason = str(boss.get("reason") or "")[:160].strip().lower()
        reason = re.sub(r"\([^)]*\)", "", reason)
        reason = re.sub(r"[-+]?\d[\d.,:%]*", "", reason)
        for ch in (",", "|", ";"):
            reason = reason.replace(ch, " ")
        reason = " ".join(reason.split())[:80]
        return f"{action}|{conf_band}|{'/'.join(vetoes)}|{reason}"

    def _bucket(self, action: str, vetoes: List[str], reason: str) -> str:
        a = (action or "NO_TRADE").upper()
        vset = {str(x).upper() for x in (vetoes or [])}
        r = (reason or "").upper()
        if a in ("BUY_CALLS", "BUY_PUTS"):
            return "BUY"
        if any(x in vset for x in (
            "NO_CLEAR_DATA", "DATA_STALE_OR_RATE_LIMITED", "OUTSIDE_RTH_OR_NO_OPEN",
            "NO_LIQUID_CONTRACT", "WIDE_SPREAD", "NO_DIRECTION",
        )) or "NO DATA" in r or "NOT ENOUGH" in r or "INSUFFICIENT" in r or "STALE" in r:
            return "INSUFFICIENT_DATA"
        if a in ("NO_TRADE", "WAIT", "FLAT", "NEUTRAL") or "NEUTRAL" in r or "FLAT" in r:
            return "NEUTRAL"
        return "NO_TRADE"

    def record(
        self,
        *,
        symbol: str,
        stock_price: float,
        boss_decision: Dict[str, Any],
        flow_data: Optional[Dict[str, Any]] = None,
        now_ts: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Append one journal row if Boss decision changed. Returns entry or None."""
        import time

        boss = boss_decision or {}
        if not boss:
            return None
        fp = self._fingerprint(boss)
        ts = float(now_ts if now_ts is not None else time.time())
        if fp == self._last_fp and (ts - self._last_ts) < 120:
            return None
        if fp == self._last_fp and (ts - self._last_ts) < MIN_SECONDS_BETWEEN_DUPES:
            return None

        action = str(boss.get("action") or "NO_TRADE").upper()
        vetoes = list(boss.get("hard_vetoes") or [])
        reason = str(boss.get("reason") or "")
        workers = boss.get("workers") or {}
        managers = boss.get("managers") or {}
        flow = flow_data or {}

        # Compact worker votes for "why"
        worker_brief = {}
        try:
            for name, vote in (workers.items() if isinstance(workers, dict) else []):
                if not isinstance(vote, dict):
                    continue
                worker_brief[name] = {
                    "action": vote.get("action"),
                    "confidence": vote.get("confidence"),
                    "reason": str(vote.get("reason") or "")[:100],
                }
        except Exception:
            worker_brief = {}

        mgr_brief = {}
        try:
            for name, vote in (managers.items() if isinstance(managers, dict) else []):
                if not isinstance(vote, dict):
                    continue
                mgr_brief[name] = {
                    "thesis": vote.get("thesis") or vote.get("action"),
                    "confidence": vote.get("confidence"),
                    "reason": str(vote.get("reason") or "")[:100],
                }
        except Exception:
            mgr_brief = {}

        entry = {
            "id": f"JRN_{int(ts)}_{action[:4]}",
            "time": datetime.now().isoformat(),
            "symbol": symbol,
            "stock_price": stock_price,
            "action": action,
            "bucket": self._bucket(action, vetoes, reason),
            "confidence": boss.get("confidence"),
            "reason": reason[:280],
            "hard_vetoes": vetoes,
            "can_auto_paper": bool(boss.get("can_auto_paper")),
            "contract": {
                "strike": (boss.get("contract") or {}).get("strike"),
                "right": (boss.get("contract") or {}).get("right"),
                "ask": (boss.get("contract") or {}).get("ask"),
                "bid": (boss.get("contract") or {}).get("bid"),
            } if boss.get("contract") else None,
            "workers": worker_brief,
            "managers": mgr_brief,
            "data_source": flow.get("data_source"),
            "data_freshness": flow.get("data_freshness"),
            "dte": flow.get("dte"),
            "expiration_label": flow.get("expiration_label"),
            "fingerprint": fp,
            "learning": "journal_only",
        }

        self.entries.append(entry)
        self.entries = self.entries[-MAX_ENTRIES:]
        self._last_fp = fp
        self._last_ts = ts
        self._save()
        logger.info(
            f"🗒️ Journal {entry['bucket']} {action} conf={entry.get('confidence')} "
            f"vetoes={vetoes[:3]} · {reason[:80]}"
        )
        return entry

    @staticmethod
    def _ui_row(entry: Dict[str, Any]) -> Dict[str, Any]:
        """Slim row for the Journal card. Heavy keys (workers, managers,
        fingerprint) stay on disk for later analysis, off the wire."""
        keep = (
            "id", "time", "symbol", "action", "bucket", "confidence",
            "reason", "hard_vetoes", "contract", "data_source", "dte",
        )
        return {k: entry.get(k) for k in keep if entry.get(k) is not None}

    def today_report(self) -> Dict[str, Any]:
        today = datetime.now().date().isoformat()
        todays = [e for e in self.entries if str(e.get("time") or "").startswith(today)]
        counts: Dict[str, int] = {}
        for e in todays:
            b = e.get("bucket") or "NO_TRADE"
            counts[b] = counts.get(b, 0) + 1
        # newest first for UI. Only ship the fields the card renders — full
        # worker/manager blobs made this a ~70KB payload on a 5s poll.
        rows = [self._ui_row(e) for e in reversed(todays[-25:])]
        tips = []
        if not todays:
            tips.append("Journal starts when Boss action / veto / reason changes.")
        else:
            tips.append(
                f"Logged {len(todays)} decision change(s) today "
                f"({', '.join(f'{k}×{v}' for k, v in sorted(counts.items()))})."
            )
            insuff = counts.get("INSUFFICIENT_DATA", 0)
            if insuff:
                tips.append(f"{insuff} were insufficiency / data gates — learn these veto reasons.")
            tips.append("Journal does not invent W/L — only the shadow BUY ledger grades P&L.")
        return {
            "mode": "decision_journal",
            "date": today,
            "count_today": len(todays),
            "bucket_counts": counts,
            "rows": rows,
            "takeaways": tips,
        }


boss_decision_journal = BossDecisionJournal()
