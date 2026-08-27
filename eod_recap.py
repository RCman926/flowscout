"""End-of-day recap for unattended sessions. Run at ~16:20 ET."""
from __future__ import annotations

import json
import os
from datetime import datetime

os.chdir(os.path.dirname(os.path.abspath(__file__)))


def main():
    recap = {"time": datetime.now().isoformat()}
    try:
        from shadow_learning_engine import shadow_learning_engine
        r = shadow_learning_engine.today_report()
        recap["shadow"] = {
            "wins": r.get("wins_today"),
            "losses": r.get("losses_today"),
            "open": r.get("open_count"),
            "win_rate": r.get("win_rate_today"),
            "takeaways": (r.get("takeaways") or [])[:5],
        }
    except Exception as e:
        recap["shadow_error"] = str(e)
    try:
        from big_run_grade import grades_today

        recap["big_run_grades"] = grades_today()
    except Exception as e:
        recap["grades_error"] = str(e)
    try:
        from squeeze_radar import squeeze_radar
        recap["squeeze"] = (squeeze_radar.snapshot().get("alerts") or [])[:8]
    except Exception as e:
        recap["squeeze_error"] = str(e)
    try:
        from paper_arm_state import paper_arm_state
        paper_arm_state.set_armed(False)
        recap["paper_armed"] = False
    except Exception as e:
        recap["paper_error"] = str(e)

    path = f"session_recap_{datetime.now().strftime('%Y%m%d')}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(recap, f, indent=2, default=str)
    print(f"Wrote {path}")

    try:
        import asyncio
        from telegram_notifier import get_telegram_notifier, init_telegram_notifier
        from config_loader import get_config
        cfg = get_config()
        if cfg.get("telegram_bot_token") and cfg.get("telegram_chat_id"):
            init_telegram_notifier(cfg.get("telegram_bot_token"), cfg.get("telegram_chat_id"))
        tn = get_telegram_notifier()
        sh = recap.get("shadow") or {}
        g = recap.get("big_run_grades") or {}
        msg = (
            f"FlowScout EOD\n"
            f"Shadow {sh.get('wins')}W / {sh.get('losses')}L  wr={sh.get('win_rate')}\n"
            f"{g.get('line') or 'Big Run grades: n/a'}\n"
            f"Paper disarmed."
        )
        if tn and tn.enabled:
            asyncio.run(tn.send_message(msg))
            print("Telegram sent")
    except Exception as e:
        print(f"Telegram skip: {e}")


if __name__ == "__main__":
    main()
