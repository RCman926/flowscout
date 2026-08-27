"""
Catalyst headlines for Big Run — public RSS + Yahoo news, cached.

Tape says *that* it is moving. Headlines say *why*. Yahoo's Ticker.news
lags (RZLV's 25 Aug GlobeNewswire PR was missing there). So we union:

  - Google News RSS (wires + blogs, not a Google Search scrape)
  - Yahoo Finance headline RSS
  - yfinance Ticker.news (when it has caught up)
  - GlobeNewswire org RSS filtered to the ticker/name

Cached per symbol so a scan pass does not spend extra Yahoo quote quota.
Never invent a catalyst — empty is honest.
"""
from __future__ import annotations

import logging
import re
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

CACHE_SEC = 25 * 60
MAX_HEADLINES = 5
UA = "FlowScout/1.0 (desk catalyst; +local)"

# Words that mean a real event vs a roundup / "why it soared" recap.
_CATALYST = (
    "select", "selected", "selects", "partnership", "partner", "contract",
    "awarded", "wins", "won", "google cloud", "microsoft", "fda", "approval",
    "earnings", "guidance", "revenue", "acquire", "acquisition", "deal",
    "launch", "launches", "deploy", "deployment", "customer", "order",
    "offering", "buyback", "upgrade", "downgrade", "short squeeze",
)
_NOISE = (
    "why it soared", "why shares", "better buy", "undervalued", "top stock",
    "stocks to watch", "best stock", "which stock", "cheap after",
)

_lock = threading.Lock()
_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_when(raw: Any) -> Optional[datetime]:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        try:
            return datetime.fromtimestamp(float(raw), tz=timezone.utc)
        except Exception:
            return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return parsedate_to_datetime(s).astimezone(timezone.utc)
    except Exception:
        pass
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except Exception:
        return None


def _age_hours(when: Optional[datetime]) -> Optional[float]:
    if not when:
        return None
    return max(0.0, (_now() - when).total_seconds() / 3600.0)


def _http_get(url: str, timeout: float = 8.0) -> Optional[bytes]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml, */*"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception as e:
        logger.debug(f"catalyst get {url[:80]}: {e}")
        return None


def _rss_items(xml_bytes: Optional[bytes], source: str) -> List[Dict[str, Any]]:
    if not xml_bytes:
        return []
    out: List[Dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_bytes)
    except Exception:
        return []
    # RSS 2.0 or Atom
    items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    for el in items[:20]:
        title = ""
        link = ""
        when_raw = None
        pub = source
        if el.tag.endswith("entry"):
            ns = "{http://www.w3.org/2005/Atom}"
            title = (el.findtext(f"{ns}title") or "").strip()
            link_el = el.find(f"{ns}link")
            if link_el is not None:
                link = (link_el.get("href") or link_el.text or "").strip()
            when_raw = el.findtext(f"{ns}updated") or el.findtext(f"{ns}published")
        else:
            title = (el.findtext("title") or "").strip()
            link = (el.findtext("link") or "").strip()
            when_raw = el.findtext("pubDate") or el.findtext("published")
            pub = (el.findtext("source") or el.findtext("{http://purl.org/dc/elements/1.1/}creator") or source)
        title = re.sub(r"<[^>]+>", "", title).strip()
        if not title:
            continue
        when = _parse_when(when_raw)
        out.append({
            "title": title,
            "publisher": str(pub or source)[:80],
            "source": source,
            "link": link,
            "time": when.isoformat() if when else None,
            "age_hours": round(_age_hours(when), 1) if when else None,
        })
    return out


def _yf_items(symbol: str) -> List[Dict[str, Any]]:
    try:
        import yfinance as yf

        raw = getattr(yf.Ticker(symbol), "news", None) or []
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    for item in raw[:16]:
        if not isinstance(item, dict):
            continue
        content = item.get("content") if isinstance(item.get("content"), dict) else item
        title = str(content.get("title") or item.get("title") or "").strip()
        if not title:
            continue
        provider = content.get("provider") if isinstance(content.get("provider"), dict) else {}
        canon = content.get("canonicalUrl") if isinstance(content.get("canonicalUrl"), dict) else {}
        when = _parse_when(
            content.get("pubDate") or content.get("displayTime") or item.get("providerPublishTime")
        )
        out.append({
            "title": title,
            "publisher": provider.get("displayName") or item.get("publisher") or "Yahoo",
            "source": "yahoo",
            "link": canon.get("url") or content.get("link") or item.get("link") or "",
            "time": when.isoformat() if when else None,
            "age_hours": round(_age_hours(when), 1) if when else None,
        })
    return out


def _score(title: str) -> int:
    t = title.lower()
    if any(n in t for n in _NOISE):
        return 0
    n = sum(1 for w in _CATALYST if w in t)
    if n >= 2:
        return 3
    if n == 1:
        return 2
    return 1


def _dedupe(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for it in items:
        key = re.sub(r"[^a-z0-9]+", " ", str(it.get("title") or "").lower())[:90]
        if not key or key in seen:
            continue
        seen.add(key)
        it = dict(it)
        it["score"] = _score(str(it.get("title") or ""))
        out.append(it)
    out.sort(key=lambda x: (
        -int(x.get("score") or 0),
        x.get("age_hours") if x.get("age_hours") is not None else 999,
    ))
    return out[:MAX_HEADLINES]


def _query(symbol: str, name: Optional[str] = None) -> str:
    parts = [symbol]
    if name:
        # Strip Inc/Ltd noise so Google News matches the company, not ticker-only.
        clean = re.sub(r"\b(inc|ltd|plc|corp|corporation|ai)\b\.?", "", name, flags=re.I)
        clean = re.sub(r"\s+", " ", clean).strip()
        if clean and clean.upper() != symbol.upper():
            parts.append(f'"{clean}"')
    return " OR ".join(parts)


def fetch(symbol: str, name: Optional[str] = None) -> Dict[str, Any]:
    """Union of public feeds. Cached. Empty pack if nothing usable."""
    sym = str(symbol or "").upper().strip()
    empty = {
        "symbol": sym,
        "headlines": [],
        "catalyst": False,
        "fresh": False,
        "line": "",
        "sources": [],
    }
    if not re.fullmatch(r"[A-Z.]{1,8}", sym):
        return empty
    now = time.time()
    with _lock:
        hit = _cache.get(sym)
        if hit and now - hit[0] < CACHE_SEC:
            return hit[1]

    q = urllib.parse.quote(_query(sym, name))
    urls = [
        ("google_news", f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"),
        ("yahoo_rss", f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={sym}&region=US&lang=en-US"),
        ("globenewswire", f"https://www.globenewswire.com/RssFeed/stock/{sym}"),
    ]
    bag: List[Dict[str, Any]] = []
    used: List[str] = []
    for src, url in urls:
        items = _rss_items(_http_get(url), src)
        if items:
            used.append(src)
            bag.extend(items)
    yf_items = _yf_items(sym)
    if yf_items:
        used.append("yahoo")
        bag.extend(yf_items)

    headlines = _dedupe(bag)
    fresh = any(
        (h.get("age_hours") is not None and h["age_hours"] <= 18 and (h.get("score") or 0) >= 2)
        for h in headlines
    )
    catalyst = any((h.get("score") or 0) >= 2 and (h.get("age_hours") is None or h["age_hours"] <= 72)
                   for h in headlines)
    top = next((h for h in headlines if (h.get("score") or 0) >= 2), headlines[0] if headlines else None)
    line = ""
    if top:
        age = top.get("age_hours")
        when = "today" if age is not None and age <= 18 else (
            f"{int(age)}h ago" if age is not None else "undated"
        )
        line = f"{when} · {top.get('publisher') or top.get('source')}: {top.get('title')}"

    pack = {
        "symbol": sym,
        "headlines": headlines,
        "catalyst": catalyst,
        "fresh": fresh,
        "line": line[:280],
        "sources": used,
    }
    with _lock:
        _cache[sym] = (now, pack)
        if len(_cache) > 400:
            for k in list(_cache)[:200]:
                _cache.pop(k, None)
    return pack


def attach(row: Dict[str, Any], name: Optional[str] = None) -> Dict[str, Any]:
    """Stamp a ticket with catalyst copy. Does not invent a setup."""
    sym = str((row or {}).get("symbol") or "")
    pack = fetch(sym, name)
    row = dict(row or {})
    row["catalyst"] = pack
    if pack.get("line"):
        plan = dict(row.get("plan") or {})
        why = str(plan.get("why_plain") or row.get("why") or "")
        extra = " Catalyst: " + pack["line"]
        if extra.strip() not in why:
            plan["why_plain"] = (why + extra).strip()
            plan["tells"] = plan.get("tells") or plan["why_plain"]
            row["plan"] = plan
            row["why"] = plan["why_plain"]
        tells = list(plan.get("tell_list") or [])
        if pack.get("fresh") and "fresh catalyst" not in tells:
            tells.append("fresh catalyst")
            plan["tell_list"] = tells[:5]
            plan["tell_n"] = len(plan["tell_list"])
            row["plan"] = plan
    return row
