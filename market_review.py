"""
Recent market review — Stage A learning (not ML bot theater).

Pulls last N calendar days of SPY context, headline news, Big Run grade
updates, and Boss journal patterns. Honest delayed Yahoo only.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _day(iso: Optional[str] = None) -> str:
    if iso:
        return str(iso)[:10]
    return datetime.now().strftime("%Y-%m-%d")


def _fetch_spy_days(days: int = 5) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        import yfinance as yf

        end = datetime.now()
        start = end - timedelta(days=max(days + 5, 10))
        hist = yf.Ticker("SPY").history(start=start.strftime("%Y-%m-%d"), interval="1d")
        if hist is None or hist.empty:
            return rows
        tail = hist.tail(days + 2)
        prev_close = None
        for idx, row in tail.iterrows():
            close = float(row.get("Close") or 0)
            open_ = float(row.get("Open") or close)
            high = float(row.get("High") or close)
            low = float(row.get("Low") or close)
            vol = int(row.get("Volume") or 0)
            chg = None
            if prev_close and prev_close > 0:
                chg = round((close - prev_close) / prev_close * 100, 2)
            rows.append(
                {
                    "date": str(idx.date()),
                    "open": round(open_, 2),
                    "high": round(high, 2),
                    "low": round(low, 2),
                    "close": round(close, 2),
                    "volume_m": round(vol / 1_000_000, 1),
                    "change_pct": chg,
                }
            )
            prev_close = close
        return rows[-days:]
    except Exception as e:
        logger.debug(f"SPY history: {e}")
        return rows


def _fetch_vix_snapshot() -> Dict[str, Any]:
    try:
        from vix_analyzer import vix_analyzer

        snap = vix_analyzer.analyze_vix() or {}
        return {
            "level": snap.get("current_vix") or snap.get("vix") or snap.get("level"),
            "regime": snap.get("regime") or snap.get("vix_regime"),
            "note": snap.get("interpretation") or snap.get("message"),
        }
    except Exception as e:
        logger.debug(f"VIX: {e}")
        return {}


def _fetch_spy_news(limit: int = 12) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        import yfinance as yf

        raw = getattr(yf.Ticker("SPY"), "news", None) or []
        for item in raw[: limit * 2]:
            if not isinstance(item, dict):
                continue
            content = item.get("content") if isinstance(item.get("content"), dict) else item
            title = str(content.get("title") or item.get("title") or "").strip()
            if not title:
                continue
            provider = content.get("provider") if isinstance(content.get("provider"), dict) else {}
            canon = content.get("canonicalUrl") if isinstance(content.get("canonicalUrl"), dict) else {}
            when = content.get("pubDate") or content.get("displayTime") or item.get("providerPublishTime")
            if when and isinstance(when, str) and when.endswith("Z"):
                when = when.replace("Z", "+00:00")
            elif when:
                try:
                    when = datetime.fromtimestamp(int(when)).isoformat()
                except Exception:
                    when = str(when)
            out.append(
                {
                    "title": title,
                    "publisher": provider.get("displayName") or item.get("publisher") or "",
                    "time": when,
                    "link": canon.get("url") or content.get("link") or item.get("link"),
                    "type": content.get("contentType") or item.get("type"),
                }
            )
            if len(out) >= limit:
                break
    except Exception as e:
        logger.debug(f"SPY news: {e}")
    return out


def _refresh_big_run_grades() -> Dict[str, Any]:
    try:
        from big_run_grade import refresh_all_grades, _load

        g = refresh_all_grades()
        store = _load()
        return {
            "n": len(store),
            "hits": g.get("hits", 0),
            "misses": g.get("misses", 0),
            "open": g.get("open", 0),
            "items": sorted(store, key=lambda r: str(r.get("day") or ""), reverse=True)[:20],
            "line": g.get("line") or "No Big Run tickets yet",
        }
    except Exception as e:
        logger.debug(f"Big run refresh: {e}")
        return {"error": str(e), "items": []}


def _shadow_recent(days: int) -> Dict[str, Any]:
    try:
        from shadow_learning_engine import shadow_learning_engine as eng

        cutoff = (datetime.now() - timedelta(days=days)).date().isoformat()
        closed = [
            t for t in (eng.closed or [])
            if str(t.get("exit_time") or t.get("entry_time") or "")[:10] >= cutoff
        ]
        opens = list(eng.open or [])
        wins = sum(1 for t in closed if t.get("outcome") == "WIN")
        losses = sum(1 for t in closed if t.get("outcome") == "LOSS")
        graded = wins + losses
        by_day: Dict[str, Dict[str, int]] = {}
        for t in closed:
            d = str(t.get("exit_time") or t.get("entry_time") or "")[:10]
            if not d:
                continue
            by_day.setdefault(d, {"w": 0, "l": 0})
            if t.get("outcome") == "WIN":
                by_day[d]["w"] += 1
            elif t.get("outcome") == "LOSS":
                by_day[d]["l"] += 1
        return {
            "closed": len(closed),
            "open": len(opens),
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / graded * 100, 1) if graded else None,
            "by_day": by_day,
            "rows": [
                {
                    "id": t.get("id"),
                    "day": str(t.get("exit_time") or "")[:10],
                    "action": t.get("action"),
                    "outcome": t.get("outcome"),
                    "pnl_pct": t.get("pnl_pct"),
                    "reason": (t.get("reason") or "")[:100],
                }
                for t in sorted(closed, key=lambda x: str(x.get("exit_time") or ""), reverse=True)[:15]
            ],
        }
    except Exception as e:
        return {"error": str(e)}


def _journal_recent(days: int) -> Dict[str, Any]:
    try:
        from decision_journal import boss_decision_journal as j

        cutoff = (datetime.now() - timedelta(days=days)).date().isoformat()
        recent = [
            e for e in (j.entries or [])
            if str(e.get("time") or "")[:10] >= cutoff
        ]
        counts: Dict[str, int] = {}
        for e in recent:
            b = e.get("bucket") or "NO_TRADE"
            counts[b] = counts.get(b, 0) + 1
        return {
            "count": len(recent),
            "bucket_counts": counts,
            "rows": [j._ui_row(e) for e in reversed(recent[-25:])],
        }
    except Exception as e:
        return {"error": str(e)}


def _takeaways(
    spy_days: List[Dict[str, Any]],
    news: List[Dict[str, Any]],
    shadow: Dict[str, Any],
    big_run: Dict[str, Any],
    journal: Dict[str, Any],
    vix: Dict[str, Any],
) -> List[str]:
    tips: List[str] = []
    if spy_days:
        last = spy_days[-1]
        ch = last.get("change_pct")
        tips.append(
            f"SPY last session {last.get('date')}: close ${last.get('close')} "
            + (f"({ch:+.2f}% vs prior close)" if ch is not None else "")
        )
        if len(spy_days) >= 2:
            first = spy_days[0]
            if first.get("close") and last.get("close"):
                span = round((last["close"] - first["close"]) / first["close"] * 100, 2)
                tips.append(f"Over {len(spy_days)} sessions SPY moved {span:+.2f}% ({first['date']} → {last['date']}).")
    if vix.get("level"):
        regime = vix.get("regime")
        if isinstance(regime, dict):
            regime = regime.get("regime") or regime.get("description") or "NORMAL"
        tips.append(f"VIX now ~{vix.get('level')} ({regime or 'regime n/a'}) — Boss IV/session gates care about this.")
    if news:
        tips.append(f"{len(news)} recent SPY headlines pulled — read for macro catalysts, not as a trade signal.")
        titles = [n.get("title") for n in news[:3] if n.get("title")]
        if titles:
            tips.append("Latest: " + " · ".join(t[:80] for t in titles))
    if shadow.get("closed"):
        wr = shadow.get("win_rate")
        tips.append(
            f"Shadow ledger: {shadow.get('wins')}W / {shadow.get('losses')}L graded in window"
            + (f" ({wr}% WR)" if wr is not None else "")
        )
    elif shadow.get("open") == 0:
        tips.append("Shadow ledger empty in this window — Boss BUY grades start fresh when RTH fires again.")
    if big_run.get("n"):
        tips.append(f"Big Run tickets: {big_run.get('line') or 'see table'} (re-graded vs latest last).")
    jc = journal.get("bucket_counts") or {}
    if journal.get("count"):
        mix = " · ".join(
            f"{k.replace('_', ' ').lower()}×{v}"
            for k, v in sorted(jc.items(), key=lambda kv: -kv[1])
            if v
        )
        tips.append(f"Boss journal: {journal.get('count')} decision changes — {mix or 'no buckets'}.")
        if not jc.get("BUY"):
            tips.append("Zero BUY decisions in the window — every setup was blocked, so nothing reached the shadow ledger.")
    tips.append("Stage A learns from shadow ask→bid + journal + Big Run bands — not cloned prediction bots.")
    return tips


def build_review(days: int = 5) -> Dict[str, Any]:
    days = max(1, min(int(days or 5), 14))
    spy_days = _fetch_spy_days(days)
    news = _fetch_spy_news(12)
    vix = _fetch_vix_snapshot()
    big_run = _refresh_big_run_grades()
    shadow = _shadow_recent(days)
    journal = _journal_recent(days)
    return {
        "mode": "market_review",
        "generated": datetime.now().isoformat(),
        "days": days,
        "spy_days": spy_days,
        "vix": vix,
        "news": news,
        "shadow_recent": shadow,
        "big_run": big_run,
        "journal_recent": journal,
        "takeaways": _takeaways(spy_days, news, shadow, big_run, journal, vix),
        "note": "Delayed Yahoo context for desk learning. News is informational — Boss still decides trades.",
    }
