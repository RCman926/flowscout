"""
IV regime worker: ATM IV vs realized vol, skew context, premium richness.
"""

from __future__ import annotations

from typing import Dict, List, Optional
import math
import logging
import numpy as np

logger = logging.getLogger(__name__)


class IVRegimeAnalyzer:
    """
    Structure/Risk worker for options premium regime.
    - Compare ATM IV to recent realized vol
    - Use VIX level when chain IV missing
    - Soft veto when buying premium into rich/crush regimes
    """

    def __init__(self, realized_lookback: int = 20):
        self.realized_lookback = realized_lookback
        self.price_history: Dict[str, List[float]] = {}

    def update_price(self, symbol: str, price: float) -> None:
        if price is None or price <= 0:
            return
        hist = self.price_history.setdefault(symbol, [])
        hist.append(float(price))
        if len(hist) > 500:
            self.price_history[symbol] = hist[-500:]

    def realized_vol_annualized(self, symbol: str) -> float:
        prices = self.price_history.get(symbol, [])
        if len(prices) < max(5, self.realized_lookback // 2):
            return 0.0
        window = prices[-self.realized_lookback:]
        rets = np.diff(np.log(np.array(window, dtype=float)))
        if len(rets) < 2:
            return 0.0
        # Assume ~1-minute-ish prints during RTH: scale roughly to daily then annualize.
        # For Stage A this is a relative regime score, not a perfect RV estimator.
        sigma = float(np.std(rets, ddof=1))
        # ~390 one-minute bars/session; use sqrt(252 * 390) if dense, else sqrt(252)
        bars_per_day = 78 if len(window) > 60 else 1  # 5m-ish vs daily fallback
        return sigma * math.sqrt(252 * bars_per_day) * 100.0  # percent

    def _atm_iv_from_chain(self, options_chain: Optional[Dict], stock_price: float) -> Optional[float]:
        if not options_chain or stock_price <= 0:
            return None
        best_iv = None
        best_dist = 1e18
        for side in ('calls', 'puts'):
            for row in options_chain.get(side, []) or []:
                try:
                    strike = float(row.get('strike') or row.get('Strike') or 0)
                    iv = row.get('impliedVolatility', row.get('iv', row.get('implied_volatility')))
                    if iv is None:
                        continue
                    iv = float(iv)
                    # yfinance often returns decimal (0.20) or percent (20)
                    if iv > 3:  # clearly percent
                        iv_pct = iv
                    else:
                        iv_pct = iv * 100.0
                    dist = abs(strike - stock_price)
                    if dist < best_dist and iv_pct > 0:
                        best_dist = dist
                        best_iv = iv_pct
                except Exception:
                    continue
        return best_iv

    def analyze(
        self,
        symbol: str,
        stock_price: float,
        options_chain: Optional[Dict] = None,
        vix_level: Optional[float] = None,
        iv_skew: Optional[float] = None,
    ) -> Dict:
        rv = self.realized_vol_annualized(symbol)
        atm_iv = self._atm_iv_from_chain(options_chain, stock_price)

        # Fallback: use VIX as SPY IV proxy when chain IV missing
        iv_source = 'chain_atm'
        if atm_iv is None or atm_iv <= 0:
            if vix_level and vix_level > 0:
                atm_iv = float(vix_level)
                iv_source = 'vix_proxy'
            else:
                atm_iv = 0.0
                iv_source = 'none'

        iv_minus_rv = (atm_iv - rv) if atm_iv > 0 and rv > 0 else 0.0
        richness = 'UNKNOWN'
        if atm_iv > 0 and rv > 0:
            if iv_minus_rv >= 8:
                richness = 'RICH'
            elif iv_minus_rv <= -3:
                richness = 'CHEAP'
            else:
                richness = 'FAIR'

        action = 'NO_TRADE'
        confidence = 35
        veto_flags = []
        reason = f'IV regime source={iv_source}'

        # Structure guidance: rich IV -> avoid naked long premium; cheap -> long premium OK with direction
        if richness == 'RICH':
            veto_flags.append('IV_RICH_VS_REALIZED')
            confidence = 40
            reason = f'IV rich vs realized ({atm_iv:.1f} vs {rv:.1f}); long premium disadvantaged'
        elif richness == 'CHEAP':
            confidence = 55
            reason = f'IV cheap vs realized ({atm_iv:.1f} vs {rv:.1f}); premium buy freer'
            # Direction still required from other workers
            action = 'NO_TRADE'
        elif richness == 'FAIR':
            confidence = 45
            reason = f'IV fair vs realized ({atm_iv:.1f} vs {rv:.1f})'

        if vix_level and vix_level >= 30:
            veto_flags.append('VIX_ELEVATED')
            confidence = max(25, confidence - 10)
            reason += ' | VIX elevated'
        elif vix_level and vix_level <= 14:
            reason += ' | VIX low (crush risk into calm)'

        if iv_skew is not None:
            # Positive skew often = put IV > call IV
            if iv_skew > 0.05:
                reason += ' | put skew bid'
            elif iv_skew < -0.05:
                reason += ' | call skew bid'

        if atm_iv <= 0:
            veto_flags.append('IV_UNAVAILABLE')
            confidence = 25
            reason = 'No ATM IV / VIX available'

        return {
            'bot_type': 'IV_REGIME_WORKER',
            'action': action,
            'confidence': int(confidence),
            'veto_flags': veto_flags,
            'reason': reason,
            'atm_iv': round(atm_iv, 3) if atm_iv else 0.0,
            'realized_vol': round(rv, 3) if rv else 0.0,
            'iv_minus_rv': round(iv_minus_rv, 3),
            'richness': richness,
            'iv_source': iv_source,
            'vix_level': vix_level,
            'features': {
                'iv_rich': richness == 'RICH',
                'iv_cheap': richness == 'CHEAP',
                'prefer_long_premium': richness in ('CHEAP', 'FAIR') and 'VIX_ELEVATED' not in veto_flags,
            },
        }


iv_regime_analyzer = IVRegimeAnalyzer()
