"""
Thin Polygon / Massive API client for Stage A options + quotes.
Uses official polygon-api-client when available; falls back to REST.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class MassiveAPIClient:
    """Minimal Polygon/Massive wrapper expected by multi_source_flow_tracker."""

    # Massive rebrand (2025): prefer api.massive.com; polygon.io still works for transition
    BASES = (
        "https://api.massive.com",
        "https://api.polygon.io",
    )

    def __init__(self, api_key: str):
        self.api_key = (api_key or "").strip().strip('"').strip("'")
        self.client = None
        self.base = self.BASES[0]
        if not self.api_key:
            return
        try:
            from polygon import RESTClient

            self.client = RESTClient(self.api_key)
        except Exception as e:
            logger.warning(f"polygon SDK unavailable ({e}); using REST fallback")
            self.client = "rest"  # truthy so callers proceed

    def _get(self, path: str, params: Optional[dict] = None) -> Optional[dict]:
        params = dict(params or {})
        headers = {"Authorization": f"Bearer {self.api_key}"}
        last_err = None
        for base in self.BASES:
            try:
                r = requests.get(f"{base}{path}", params=params, headers=headers, timeout=12)
                if r.status_code == 401:
                    logger.warning(f"Massive/Polygon 401 at {base} — unknown/invalid API key")
                    last_err = 401
                    continue
                if r.status_code == 403:
                    logger.warning(f"Massive/Polygon 403 at {base} — plan may lack this endpoint")
                    return None
                if r.status_code == 429:
                    logger.warning("Massive/Polygon HTTP 429 — rate limited")
                    return None
                if r.status_code >= 400:
                    logger.warning(f"Massive/Polygon HTTP {r.status_code} at {base}: {r.text[:160]}")
                    last_err = r.status_code
                    continue
                self.base = base
                return r.json()
            except Exception as e:
                last_err = e
                logger.warning(f"Massive/Polygon request failed ({base}): {e}")
        if last_err:
            return None
        return None

    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Last trade / prev close style spot for underlying."""
        symbol = (symbol or "SPY").upper()
        # Prefer previous close + minute agg as resilient path on free/delayed tiers
        prev = self._get(f"/v2/aggs/ticker/{symbol}/prev")
        price = 0.0
        if prev and prev.get("results"):
            try:
                price = float(prev["results"][0].get("c") or 0)
            except Exception:
                price = 0.0
        # Newer snapshot if entitled
        snap = self._get(f"/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}")
        if snap:
            try:
                day = (snap.get("ticker") or {}).get("day") or {}
                last = (snap.get("ticker") or {}).get("lastTrade") or {}
                price = float(last.get("p") or day.get("c") or price or 0)
            except Exception:
                pass
        if price <= 0:
            return None
        return {"price": price, "symbol": symbol}

    def get_options_chain(self, symbol: str, expiration: Optional[str] = None) -> Optional[Dict[str, List[dict]]]:
        """
        Fetch option contracts for an expiration and enrich with day snapshot when possible.
        Free Options Basic is limited; Starter+ works better.
        """
        symbol = (symbol or "SPY").upper()
        expiration = expiration or datetime.now().strftime("%Y-%m-%d")

        contracts = self._get(
            "/v3/reference/options/contracts",
            {
                "underlying_ticker": symbol,
                "expiration_date": expiration,
                "limit": 250,
                "expired": "false",
            },
        )
        results = (contracts or {}).get("results") or []
        if not results:
            # Try snapshot options chain if entitled
            snap = self._get(f"/v3/snapshot/options/{symbol}", {"expiration_date": expiration, "limit": 250})
            results = (snap or {}).get("results") or []
            return self._normalize_snapshot_results(results)

        calls: List[dict] = []
        puts: List[dict] = []
        for c in results:
            row = {
                "strike": float(c.get("strike_price") or 0),
                "volume": int(c.get("volume") or 0),
                "open_interest": int(c.get("open_interest") or 0),
                "last_price": float(c.get("last_quote", {}).get("midpoint") or c.get("day", {}).get("close") or 0)
                if isinstance(c.get("last_quote"), dict)
                else float(c.get("day", {}).get("close") or 0) if isinstance(c.get("day"), dict) else 0.0,
                "bid": 0.0,
                "ask": 0.0,
                "iv": 0.0,
                "ticker": c.get("ticker"),
            }
            ctype = (c.get("contract_type") or "").lower()
            if ctype == "call":
                calls.append(row)
            elif ctype == "put":
                puts.append(row)

        # If reference contracts have no volume/quotes, try options snapshot for the underlying
        if calls or puts:
            has_marks = any(
                (r.get("bid") or 0) > 0 or (r.get("ask") or 0) > 0 or (r.get("last_price") or 0) > 0 or (r.get("volume") or 0) > 0
                for r in (calls + puts)
            )
            snap = self._get(f"/v3/snapshot/options/{symbol}", {"expiration_date": expiration, "limit": 250})
            if snap and snap.get("results"):
                return self._normalize_snapshot_results(snap.get("results") or [])
            if not has_marks:
                # Options Basic ($0) returns contract list only — Snapshot needs Starter+
                logger.warning(
                    "Massive/Polygon: contract list has no bid/ask/volume (likely Options Basic). "
                    "Upgrade to Options Starter for snapshot quotes — failing over."
                )
                return None
            return {"calls": calls, "puts": puts}

        return None

    def _normalize_snapshot_results(self, results: List[dict]) -> Optional[Dict[str, List[dict]]]:
        if not results:
            return None
        calls: List[dict] = []
        puts: List[dict] = []
        for item in results:
            details = item.get("details") or {}
            day = item.get("day") or {}
            quote = item.get("last_quote") or {}
            greeks = item.get("greeks") or {}
            row = {
                "strike": float(details.get("strike_price") or 0),
                "volume": int(day.get("volume") or 0),
                "open_interest": int(item.get("open_interest") or 0),
                "last_price": float(day.get("close") or quote.get("midpoint") or 0),
                "bid": float(quote.get("bid") or 0),
                "ask": float(quote.get("ask") or 0),
                "iv": float(item.get("implied_volatility") or greeks.get("iv") or 0),
                "ticker": details.get("ticker"),
            }
            ctype = (details.get("contract_type") or "").lower()
            if ctype == "call":
                calls.append(row)
            elif ctype == "put":
                puts.append(row)
        if not calls and not puts:
            return None
        has_marks = any(
            (r.get("bid") or 0) > 0 or (r.get("ask") or 0) > 0 or (r.get("last_price") or 0) > 0 or (r.get("volume") or 0) > 0
            for r in (calls + puts)
        )
        if not has_marks:
            logger.warning("Massive/Polygon snapshot returned rows without quotes — treating as empty")
            return None
        return {"calls": calls, "puts": puts}
