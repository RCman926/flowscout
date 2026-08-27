"""
Technical Indicators - real recursive EMAs, SMAs, and regime signals.
"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """Calculate technical indicators for trading signals with proper EMAs."""

    DEFAULT_PERIODS = (9, 21, 50, 100, 200)

    def __init__(self):
        self.price_history: Dict[str, List[float]] = {}
        # Running EMA state: symbol -> {period: ema_value}
        self.ema_state: Dict[str, Dict[int, float]] = {}
        # Samples seen per symbol (for SMA seed)
        self.sample_count: Dict[str, int] = {}
        self.max_history = 500

    def update_price(self, symbol: str, price: float):
        """Update price history and maintain recursive EMAs in O(1) per period."""
        if price is None or price <= 0:
            return

        if symbol not in self.price_history:
            self.price_history[symbol] = []
            self.ema_state[symbol] = {}
            self.sample_count[symbol] = 0

        self.price_history[symbol].append(float(price))
        self.sample_count[symbol] += 1

        if len(self.price_history[symbol]) > self.max_history:
            self.price_history[symbol] = self.price_history[symbol][-self.max_history:]

        prices = self.price_history[symbol]
        n = self.sample_count[symbol]

        for period in self.DEFAULT_PERIODS:
            multiplier = 2.0 / (period + 1)
            if period not in self.ema_state[symbol]:
                # Seed with SMA once we have `period` samples
                if len(prices) >= period:
                    seed = sum(prices[-period:]) / period
                    self.ema_state[symbol][period] = seed
                continue

            # Recursive EMA update on every new print after seed
            prev = self.ema_state[symbol][period]
            self.ema_state[symbol][period] = (price * multiplier) + (prev * (1.0 - multiplier))

        # n tracked for debugging / readiness
        _ = n

    def seed_from_prices(self, symbol: str, prices: List[float]):
        """Rebuild history and EMA state from an ordered price series (oldest -> newest)."""
        self.price_history[symbol] = []
        self.ema_state[symbol] = {}
        self.sample_count[symbol] = 0
        for p in prices:
            if p and p > 0:
                self.update_price(symbol, float(p))

    def calculate_ema(self, prices: List[float], period: int) -> float:
        """
        True EMA over a full series:
        - Seed = SMA of first `period` prices
        - Then recursive update through the rest of the series
        """
        if not prices or len(prices) < period or period <= 0:
            return 0.0

        multiplier = 2.0 / (period + 1)
        ema = sum(prices[:period]) / period
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1.0 - multiplier))
        return float(ema)

    def get_ema(self, symbol: str, period: int) -> float:
        """Get current EMA for a symbol/period from running state (fallback to full calc)."""
        if symbol in self.ema_state and period in self.ema_state[symbol]:
            return float(self.ema_state[symbol][period])

        prices = self.price_history.get(symbol, [])
        if len(prices) < period:
            return 0.0

        value = self.calculate_ema(prices, period)
        if symbol not in self.ema_state:
            self.ema_state[symbol] = {}
        self.ema_state[symbol][period] = value
        return value

    def get_all_emas(self, symbol: str) -> Dict[int, float]:
        """Get multiple EMAs at once."""
        emas = {}
        for period in self.DEFAULT_PERIODS:
            ema = self.get_ema(symbol, period)
            if ema > 0:
                emas[period] = ema
        return emas

    def get_ema_signals(self, symbol: str, current_price: float) -> Dict:
        """EMA regime / cross / distance signals for Direction manager."""
        signals = {
            'price_vs_ema50': 0.0,
            'price_vs_ema21': 0.0,
            'price_vs_ema9': 0.0,
            'ema_trend': 'NEUTRAL',
            'ema_cross': 'NONE',
            'ema_support_resistance': 'NONE',
            'ema9': 0.0,
            'ema21': 0.0,
            'ema50': 0.0,
            'ema200': 0.0,
            'ready': False,
            'action': 'NO_TRADE',
            'confidence': 30,
            'veto_flags': [],
            'reason': 'EMA not ready',
        }

        ema9 = self.get_ema(symbol, 9)
        ema21 = self.get_ema(symbol, 21)
        ema50 = self.get_ema(symbol, 50)
        ema200 = self.get_ema(symbol, 200)

        signals['ema9'] = ema9
        signals['ema21'] = ema21
        signals['ema50'] = ema50
        signals['ema200'] = ema200

        if current_price == 0 or ema50 == 0:
            signals['veto_flags'] = ['EMA_NOT_READY']
            return signals

        signals['ready'] = True
        signals['price_vs_ema50'] = ((current_price - ema50) / ema50) * 100
        signals['price_vs_ema21'] = ((current_price - ema21) / ema21) * 100 if ema21 > 0 else 0.0
        signals['price_vs_ema9'] = ((current_price - ema9) / ema9) * 100 if ema9 > 0 else 0.0

        if ema9 > 0 and ema21 > 0 and ema50 > 0:
            if current_price > ema9 > ema21 > ema50:
                signals['ema_trend'] = 'STRONG_BULLISH'
                signals['action'] = 'BUY_CALLS'
                signals['confidence'] = 72
            elif current_price > ema21 > ema50:
                signals['ema_trend'] = 'BULLISH'
                signals['action'] = 'BUY_CALLS'
                signals['confidence'] = 62
            elif current_price < ema9 < ema21 < ema50:
                signals['ema_trend'] = 'STRONG_BEARISH'
                signals['action'] = 'BUY_PUTS'
                signals['confidence'] = 72
            elif current_price < ema21 < ema50:
                signals['ema_trend'] = 'BEARISH'
                signals['action'] = 'BUY_PUTS'
                signals['confidence'] = 62
            else:
                signals['ema_trend'] = 'NEUTRAL'
                signals['action'] = 'NO_TRADE'
                signals['confidence'] = 35
                signals['veto_flags'] = ['EMA_CHOP']

        if ema9 > 0 and ema21 > 0:
            if ema9 > ema21:
                signals['ema_cross'] = 'BULLISH_CROSS'
            elif ema9 < ema21:
                signals['ema_cross'] = 'BEARISH_CROSS'

        if ema50 > 0:
            distance_from_ema50 = abs(signals['price_vs_ema50'])
            if distance_from_ema50 < 0.5:
                if current_price > ema50:
                    signals['ema_support_resistance'] = 'AT_EMA50'
                else:
                    signals['ema_support_resistance'] = 'AT_EMA50'

        # Optional higher-TF filter
        if ema200 > 0:
            if signals['action'] == 'BUY_CALLS' and current_price < ema200:
                signals['confidence'] = max(40, signals['confidence'] - 15)
                signals['veto_flags'] = signals.get('veto_flags', []) + ['AGAINST_EMA200']
            elif signals['action'] == 'BUY_PUTS' and current_price > ema200:
                signals['confidence'] = max(40, signals['confidence'] - 15)
                signals['veto_flags'] = signals.get('veto_flags', []) + ['AGAINST_EMA200']

        signals['reason'] = (
            f"EMA trend={signals['ema_trend']} cross={signals['ema_cross']} "
            f"vs50={signals['price_vs_ema50']:.2f}%"
        )
        return signals

    def is_price_above_ema50(self, symbol: str, current_price: float) -> bool:
        ema50 = self.get_ema(symbol, 50)
        if ema50 == 0:
            return False
        return current_price > ema50

    def is_price_below_ema50(self, symbol: str, current_price: float) -> bool:
        ema50 = self.get_ema(symbol, 50)
        if ema50 == 0:
            return False
        return current_price < ema50

    def get_ema_distance(self, symbol: str, current_price: float, period: int = 50) -> float:
        ema = self.get_ema(symbol, period)
        if ema == 0:
            return 0.0
        return ((current_price - ema) / ema) * 100


# Global instance
technical_indicators = TechnicalIndicators()
