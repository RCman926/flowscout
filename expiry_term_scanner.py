"""
Scan option volume across expirations to show where flow sits:
0DTE, few days, ~1 week, ~1 month.
Heavily cached to respect Yahoo/IBKR rate limits.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import time

try:
    from zoneinfo import ZoneInfo
    _ET = ZoneInfo("America/New_York")
except Exception:
    _ET = None

logger = logging.getLogger(__name__)


class ExpiryTermScanner:
    """Aggregate call/put volume by tenor buckets."""

    CACHE_SECONDS = 120  # slow scan — UI can still refresh strike chart from 0DTE chain

    def __init__(self):
        self._cache: Dict[str, Tuple[float, Dict]] = {}

    def _today_et(self):
        if _ET is not None:
            return datetime.now(_ET).date()
        return datetime.now().date()

    def _dte_from_exp(self, exp: Optional[str]) -> Optional[int]:
        if not exp:
            return None
        try:
            d = datetime.strptime(str(exp)[:10], '%Y-%m-%d').date()
            return (d - self._today_et()).days
        except Exception:
            return None

    def _bucket_for_dte(self, dte: int) -> str:
        if dte <= 0:
            return '0dte'
        if dte <= 3:
            return 'few_days'
        if dte <= 10:
            return '1_week'
        if dte <= 45:
            return '1_month'
        return 'longer'

    def _zero_counts(self, bucket: Dict) -> Dict:
        """Keep the slot, drop numbers so the same expiry is not counted twice."""
        out = dict(bucket)
        out.update({
            'expiration': None,
            'dte': None,
            'call_volume': 0,
            'put_volume': 0,
            'call_premium': 0.0,
            'put_premium': 0.0,
            'total_volume': 0,
            'total_premium': 0.0,
            'volume_share_pct': 0.0,
            'premium_share_pct': 0.0,
            'top_call_strikes': [],
            'top_put_strikes': [],
            'scanned': False,
            'live_overlay': False,
            'error': None,
        })
        return out

    def _recompute_shares(self, buckets: Dict) -> Tuple[int, float, Optional[str]]:
        total_vol = sum(int(b.get('total_volume') or 0) for b in buckets.values())
        total_prem = sum(float(b.get('total_premium') or 0) for b in buckets.values())
        for b in buckets.values():
            b['volume_share_pct'] = round((int(b.get('total_volume') or 0) / total_vol) * 100, 1) if total_vol else 0.0
            b['premium_share_pct'] = round((float(b.get('total_premium') or 0) / total_prem) * 100, 1) if total_prem else 0.0
        # Heaviest = most contracts, matching the vol numbers on the bars.
        ranked = sorted(
            buckets.values(),
            key=lambda x: int(x.get('total_volume') or 0),
            reverse=True,
        )
        dominant = ranked[0]['key'] if ranked and int(ranked[0].get('total_volume') or 0) > 0 else None
        return int(total_vol), float(total_prem), dominant

    def _pick_exps(self, exp_dates: List[str], today) -> List[Tuple[str, str, int]]:
        """
        Pick up to one expiration per bucket to limit API calls.
        Returns list of (exp_str, bucket, dte).
        """
        parsed = []
        for exp in exp_dates:
            try:
                d = datetime.strptime(exp, '%Y-%m-%d').date()
                dte = (d - today).days
                if dte < 0:
                    continue
                parsed.append((exp, dte, self._bucket_for_dte(dte)))
            except Exception:
                continue

        chosen = []
        seen = set()
        # Prefer exact / nearest in each bucket order
        for bucket in ('0dte', 'few_days', '1_week', '1_month', 'longer'):
            candidates = [p for p in parsed if p[2] == bucket]
            if not candidates:
                continue
            # nearest in bucket
            candidates.sort(key=lambda x: x[1])
            exp, dte, b = candidates[0]
            if b not in seen:
                chosen.append((exp, b, dte))
                seen.add(b)
        return chosen

    def scan(self, symbol: str = 'SPY') -> Dict:
        now = time.time()
        cached = self._cache.get(symbol)
        if cached and (now - cached[0]) < self.CACHE_SECONDS:
            return cached[1]

        empty = self._empty(symbol, reason='No data')
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            exp_dates = list(ticker.options or [])
            if not exp_dates:
                self._cache[symbol] = (now, empty)
                return empty

            today = self._today_et()
            picks = self._pick_exps(exp_dates, today)
            if not picks:
                self._cache[symbol] = (now, empty)
                return empty

            buckets = {
                '0dte': self._zero_bucket('0DTE', 'Today / same day'),
                'few_days': self._zero_bucket('Few days', '1–3 DTE'),
                '1_week': self._zero_bucket('~1 Week', '4–10 DTE'),
                '1_month': self._zero_bucket('~1 Month', '11–45 DTE'),
                'longer': self._zero_bucket('Longer', '45+ DTE'),
            }

            stock_price = 0.0
            try:
                fi = getattr(ticker, 'fast_info', None)
                if fi is not None:
                    stock_price = float(getattr(fi, 'last_price', 0) or getattr(fi, 'lastPrice', 0) or 0)
            except Exception:
                stock_price = 0.0

            for exp, bucket, dte in picks:
                try:
                    time.sleep(0.35)  # be gentle with Yahoo
                    chain = ticker.option_chain(exp)
                    c_vol, c_prem, c_top = self._side_stats(chain.calls, 'CALL', stock_price)
                    p_vol, p_prem, p_top = self._side_stats(chain.puts, 'PUT', stock_price)
                    buckets[bucket].update({
                        'expiration': exp,
                        'dte': dte,
                        'call_volume': c_vol,
                        'put_volume': p_vol,
                        'call_premium': c_prem,
                        'put_premium': p_prem,
                        'total_volume': c_vol + p_vol,
                        'total_premium': c_prem + p_prem,
                        'top_call_strikes': c_top[:5],
                        'top_put_strikes': p_top[:5],
                        'scanned': True,
                    })
                except Exception as e:
                    logger.debug(f"Expiry scan failed {symbol} {exp}: {e}")
                    buckets[bucket]['error'] = str(e)

            total_vol, total_prem, dominant = self._recompute_shares(buckets)

            result = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'stock_price': stock_price,
                'buckets': buckets,
                'dominant_tenor': dominant,
                'total_volume': int(total_vol),
                'total_premium': float(total_prem),
                'cache_seconds': self.CACHE_SECONDS,
                'data_source': 'yfinance',
                'source_note': 'Multi-tenor sample via Yahoo. 0DTE can be overlaid from live MAIN chain.',
                'note': 'Sampled one expiry per tenor bucket (cached). 0DTE may use live primary source.',
            }
            self._cache[symbol] = (now, result)
            return result
        except Exception as e:
            logger.warning(f"Expiry term scan error for {symbol}: {e}")
            empty['reason'] = str(e)
            self._cache[symbol] = (now, empty)
            return empty

    def overlay_live_0dte(self, result: Dict, flow_data: Optional[Dict], live_source: str = '') -> Dict:
        """
        Replace the nearest live chain bucket with metrics from the live
        multi_source chain so Boss / battle / expiry map agree.

        Premarket/AH often *is* tomorrow (1DTE). Do not stamp that as 0DTE,
        and do not leave the same expiry sitting in Few days as well —
        that double-counted volume and made 0DTE and Few days identical.
        """
        if not result or not isinstance(result, dict):
            return result or {}
        out = dict(result)
        buckets = dict(out.get('buckets') or {})

        fm = (flow_data or {}).get('flow_metrics') or {}
        calls = (flow_data or {}).get('calls') or {}
        puts = (flow_data or {}).get('puts') or {}
        c_vol = int(fm.get('total_call_volume') or calls.get('total_volume') or 0)
        p_vol = int(fm.get('total_put_volume') or puts.get('total_volume') or 0)
        c_prem = float(fm.get('call_premium_flow') or 0)
        p_prem = float(fm.get('put_premium_flow') or 0)

        if c_vol <= 0 and p_vol <= 0 and c_prem <= 0 and p_prem <= 0:
            out['buckets'] = buckets
            out['data_source'] = out.get('data_source') or 'yfinance'
            out['live_0dte_overlaid'] = False
            return out

        src = live_source or (flow_data or {}).get('data_source') or 'live'
        exp = (flow_data or {}).get('expiration')
        dte = self._dte_from_exp(exp)
        if dte is None:
            dte = 0
        target = self._bucket_for_dte(dte)
        if target not in buckets:
            target = '0dte'

        live = dict(buckets.get(target) or self._zero_bucket(
            '0DTE' if target == '0dte' else 'Few days',
            'Today / same day' if target == '0dte' else '1–3 DTE',
        ))
        live.update({
            'call_volume': c_vol,
            'put_volume': p_vol,
            'call_premium': c_prem,
            'put_premium': p_prem,
            'total_volume': c_vol + p_vol,
            'total_premium': c_prem + p_prem,
            'dte': dte,
            'expiration': exp,
            'scanned': True,
            'live_overlay': True,
            'live_source': src,
            'description': (
                f'Today · live {src}' if dte <= 0 else f'{dte}DTE · live {src}'
            ),
        })
        buckets[target] = live

        # Same calendar expiry must not live in two buckets.
        exp_key = str(exp)[:10] if exp else ''
        for key, b in list(buckets.items()):
            if key == target:
                continue
            other = str(b.get('expiration') or '')[:10]
            if exp_key and other == exp_key:
                buckets[key] = self._zero_counts(b)

        total_vol, total_prem, dominant = self._recompute_shares(buckets)

        out['buckets'] = buckets
        out['dominant_tenor'] = dominant or target
        out['total_volume'] = int(total_vol)
        out['total_premium'] = float(total_prem)
        out['live_0dte_overlaid'] = True
        out['live_0dte_source'] = src
        out['live_bucket'] = target
        out['data_source'] = f'{src}+yfinance_tenors'
        out['source_note'] = (
            f'Live {src} chain is {dte}DTE ({exp}); other tenors sampled via Yahoo. '
            'Shares are by volume, not premium.'
        )
        return out

    def _zero_bucket(self, label: str, desc: str) -> Dict:
        key = {
            '0DTE': '0dte',
            'Few days': 'few_days',
            '~1 Week': '1_week',
            '~1 Month': '1_month',
            'Longer': 'longer',
        }.get(label, label.lower().replace(' ', '_'))
        return {
            'key': key,
            'label': label,
            'description': desc,
            'expiration': None,
            'dte': None,
            'call_volume': 0,
            'put_volume': 0,
            'call_premium': 0.0,
            'put_premium': 0.0,
            'total_volume': 0,
            'total_premium': 0.0,
            'volume_share_pct': 0.0,
            'premium_share_pct': 0.0,
            'top_call_strikes': [],
            'top_put_strikes': [],
            'scanned': False,
        }

    def _side_stats(self, df, side: str, stock_price: float):
        if df is None or getattr(df, 'empty', True):
            return 0, 0.0, []
        total_vol = 0
        total_prem = 0.0
        rows = []
        for _, row in df.iterrows():
            try:
                import pandas as pd
                strike = float(row.get('strike', 0) or 0)
                vol = float(row.get('volume', 0)) if pd.notna(row.get('volume')) else 0.0
                last = float(row.get('lastPrice', 0)) if pd.notna(row.get('lastPrice')) else 0.0
                prem = vol * last * 100 if last > 0 else 0.0
                total_vol += vol
                total_prem += prem
                rows.append({
                    'strike': strike,
                    'volume': int(vol),
                    'premium_flow': prem,
                    'side': side,
                })
            except Exception:
                continue
        rows.sort(key=lambda x: x['volume'], reverse=True)
        return int(total_vol), float(total_prem), rows

    def _empty(self, symbol: str, reason: str = '') -> Dict:
        buckets = {
            '0dte': self._zero_bucket('0DTE', 'Today / same day'),
            'few_days': self._zero_bucket('Few days', '1–3 DTE'),
            '1_week': self._zero_bucket('~1 Week', '4–10 DTE'),
            '1_month': self._zero_bucket('~1 Month', '11–45 DTE'),
            'longer': self._zero_bucket('Longer', '45+ DTE'),
        }
        return {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'buckets': buckets,
            'dominant_tenor': None,
            'total_volume': 0,
            'total_premium': 0.0,
            'reason': reason,
            'data_source': 'yfinance',
            'source_note': 'Multi-tenor sample via Yahoo when available.',
        }


expiry_term_scanner = ExpiryTermScanner()
