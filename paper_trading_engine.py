"""
Paper Trading Engine
Simulates trade execution for strategy testing without real money
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone
import json
import os

try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except Exception:  # pragma: no cover
    ET = timezone(timedelta(hours=-4))

logger = logging.getLogger(__name__)


def _now_et() -> datetime:
    return datetime.now(ET)


class PaperTradingEngine:
    """
    Paper trading simulation engine
    Tracks virtual positions and performance
    """

    def __init__(self, initial_balance: float = 100000, trades_file: str = None):
        if not trades_file:
            try:
                from cloud_runtime import state_path
                trades_file = str(state_path("paper_trades.json"))
            except Exception:
                trades_file = "paper_trades.json"
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions = {}  # position_id -> position dict
        self.trade_history = []
        self.trades_file = trades_file
        self.commission_per_trade = 1.0
        self.slippage_pct = 0.001

        self.max_contracts = int(os.getenv("PAPER_MAX_CONTRACTS", "50"))
        self.max_open = int(os.getenv("PAPER_MAX_OPEN", "1"))
        self.daily_loss_halt = float(os.getenv("PAPER_DAILY_LOSS_HALT", "500"))
        self.cooldown_seconds = int(os.getenv("PAPER_COOLDOWN_SECONDS", "120"))
        self._last_boss_entry_at: Optional[datetime] = None

        self._load_trades()

    def _load_trades(self):
        if os.path.exists(self.trades_file):
            try:
                with open(self.trades_file, "r") as f:
                    data = json.load(f)
                    self.trade_history = data.get("trades", [])
                    self.balance = data.get("balance", self.initial_balance)
                    for trade in self.trade_history:
                        if trade.get("status") == "OPEN":
                            self.positions[trade["trade_id"]] = trade
            except Exception as e:
                logger.error(f"Error loading paper trades: {e}")

    def _save_trades(self):
        try:
            data = {
                "balance": self.balance,
                "initial_balance": self.initial_balance,
                "trades": self.trade_history,
                "last_updated": datetime.now().isoformat(),
            }
            with open(self.trades_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving paper trades: {e}")

    def _today_realized_pnl(self) -> float:
        today = _now_et().date()
        total = 0.0
        for t in self.trade_history:
            if t.get("status") != "CLOSED":
                continue
            try:
                exit_t = datetime.fromisoformat(t["exit_time"])
                if exit_t.tzinfo is None:
                    exit_t = exit_t.replace(tzinfo=ET)
                else:
                    exit_t = exit_t.astimezone(ET)
                if exit_t.date() == today:
                    total += float(t.get("profit_loss") or 0)
            except Exception:
                continue
        return total

    def risk_status(self) -> Dict:
        daily_pnl = self._today_realized_pnl()
        halted = daily_pnl <= -abs(self.daily_loss_halt)
        cooldown_left = 0
        if self._last_boss_entry_at:
            elapsed = (_now_et() - self._last_boss_entry_at).total_seconds()
            cooldown_left = max(0, int(self.cooldown_seconds - elapsed))
        return {
            "max_contracts": self.max_contracts,
            "max_open": self.max_open,
            "open_count": len(self.positions),
            "daily_realized_pnl": round(daily_pnl, 2),
            "daily_loss_halt": self.daily_loss_halt,
            "daily_halted": halted,
            "cooldown_seconds_left": cooldown_left,
        }

    def _risk_blocks_entry(self) -> Optional[str]:
        status = self.risk_status()
        if status["daily_halted"]:
            return f"Daily loss halt (${status['daily_realized_pnl']:.2f})"
        if status["open_count"] >= self.max_open:
            return f"Max open positions ({self.max_open})"
        if status["cooldown_seconds_left"] > 0:
            return f"Cooldown {status['cooldown_seconds_left']}s"
        return None

    async def execute_trade(self, signal: Dict, current_price: float) -> Dict:
        action = signal.get("action", "NO_TRADE")
        if action == "NO_TRADE":
            return {"success": False, "reason": "No trade signal"}

        symbol = signal.get("symbol", "SPY")
        confidence = signal.get("confidence", 50)
        position_size = self._calculate_position_size(signal, current_price)

        if action == "BUY_CALLS":
            fill_price = current_price * (1 + self.slippage_pct)
        else:
            fill_price = current_price * (1 - self.slippage_pct)

        cost = position_size * fill_price
        total_cost = cost + self.commission_per_trade

        if total_cost > self.balance:
            return {
                "success": False,
                "reason": f"Insufficient balance: need ${total_cost:.2f}, have ${self.balance:.2f}",
            }

        trade_id = f"PAPER_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        trade = {
            "trade_id": trade_id,
            "symbol": symbol,
            "action": action,
            "entry_price": fill_price,
            "position_size": position_size,
            "entry_time": datetime.now().isoformat(),
            "status": "OPEN",
            "confidence": confidence,
            "cost": total_cost,
            "commission": self.commission_per_trade,
            "data_quality": "delayed",
            "venue": "local_sim",
        }

        self.balance -= total_cost
        self.positions[trade_id] = trade
        self.trade_history.append(trade)
        self._save_trades()

        logger.info(f"📝 Paper trade executed: {action} {symbol} @ ${fill_price:.2f} (size: {position_size})")

        return {
            "success": True,
            "trade_id": trade_id,
            "fill_price": fill_price,
            "position_size": position_size,
            "cost": total_cost,
            "remaining_balance": self.balance,
        }

    def _calculate_position_size(self, signal: Dict, current_price: float) -> float:
        confidence = signal.get("confidence", 50)
        base_size = 10
        if confidence >= 90:
            size_multiplier = 2.0
        elif confidence >= 80:
            size_multiplier = 1.5
        elif confidence >= 70:
            size_multiplier = 1.0
        else:
            size_multiplier = 0.5

        position_size = base_size * size_multiplier
        max_affordable = (self.balance * 0.1) / max(current_price, 1e-9)
        position_size = min(position_size, max_affordable)
        return max(1, int(position_size))

    async def close_trade(self, trade_id: str, exit_price: float, reason: str = "Manual") -> Dict:
        if trade_id not in self.positions:
            return {"success": False, "reason": "Trade not found"}

        trade = self.positions[trade_id]
        if trade["status"] != "OPEN":
            return {"success": False, "reason": "Trade already closed"}

        entry_price = trade["entry_price"]
        position_size = trade["position_size"]

        if trade["action"] == "BUY_CALLS":
            pnl = (exit_price - entry_price) * position_size
        else:
            pnl = (entry_price - exit_price) * position_size

        pnl -= self.commission_per_trade
        proceeds = exit_price * position_size
        self.balance += proceeds - self.commission_per_trade

        trade["exit_price"] = exit_price
        trade["exit_time"] = datetime.now().isoformat()
        trade["status"] = "CLOSED"
        trade["profit_loss"] = pnl
        trade["profit_loss_pct"] = (pnl / (entry_price * position_size)) * 100
        trade["exit_reason"] = reason

        del self.positions[trade_id]
        self._save_trades()

        logger.info(f"📝 Paper trade closed: {trade_id} | P&L: ${pnl:.2f} ({trade['profit_loss_pct']:.2f}%)")

        return {
            "success": True,
            "trade_id": trade_id,
            "profit_loss": pnl,
            "profit_loss_pct": trade["profit_loss_pct"],
            "new_balance": self.balance,
        }

    def get_performance(self) -> Dict:
        closed_trades = [t for t in self.trade_history if t.get("status") == "CLOSED"]
        open_trades = [t for t in self.trade_history if t.get("status") == "OPEN"]

        total_pnl = sum(t.get("profit_loss", 0) for t in closed_trades)
        winning_trades = [t for t in closed_trades if t.get("profit_loss", 0) > 0]
        losing_trades = [t for t in closed_trades if t.get("profit_loss", 0) <= 0]

        win_rate = (len(winning_trades) / len(closed_trades) * 100) if closed_trades else 0.0
        avg_win = sum(t.get("profit_loss", 0) for t in winning_trades) / len(winning_trades) if winning_trades else 0.0
        avg_loss = sum(t.get("profit_loss", 0) for t in losing_trades) / len(losing_trades) if losing_trades else 0.0

        return {
            "initial_balance": self.initial_balance,
            "current_balance": self.balance,
            "total_pnl": total_pnl,
            "total_pnl_pct": ((self.balance - self.initial_balance) / self.initial_balance) * 100,
            "total_trades": len(self.trade_history),
            "open_trades": len(open_trades),
            "closed_trades": len(closed_trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": abs(avg_win / avg_loss) if avg_loss != 0 else 0.0,
            "risk": self.risk_status(),
        }

    def get_open_positions(self) -> List[Dict]:
        return list(self.positions.values())

    def execute_boss_trade(self, boss: Dict) -> Dict:
        """
        Stage-A paper entry from Boss (options premium: buy near ask).
        """
        if not boss or not boss.get("can_auto_paper"):
            return {"success": False, "reason": "Boss not cleared for paper (disarmed or no trade)"}

        block = self._risk_blocks_entry()
        if block:
            return {"success": False, "reason": block}

        action = boss.get("action", "NO_TRADE")
        # Prefer primary non-aggressive scenario contract
        contract = boss.get("contract") or {}
        for sc in boss.get("scenarios") or []:
            if sc.get("primary") and not sc.get("advisory_only") and sc.get("contract"):
                contract = sc["contract"]
                break

        symbol = boss.get("symbol", "SPY")
        ask = float(contract.get("ask") or 0)
        mid = float(contract.get("mid") or 0)
        entry = float(contract.get("entry_mark") or ask or mid or 0)

        if action not in ("BUY_CALLS", "BUY_PUTS") or entry <= 0:
            return {"success": False, "reason": "Missing action or entry mark"}

        if ask <= 0 and mid <= 0:
            return {"success": False, "reason": "NO_BID_ASK — refuse paper fill without quote"}

        for t in self.positions.values():
            if t.get("symbol") == symbol and t.get("status") == "OPEN":
                return {"success": False, "reason": "Already have open paper position", "trade_id": t.get("trade_id")}

        from shadow_learning_engine import contracts_for_premium
        sized = contracts_for_premium(entry)
        contracts = max(1, min(self.max_contracts, int(boss.get("contracts") or sized)))
        multiplier = 100
        cost = entry * contracts * multiplier + self.commission_per_trade
        if cost > self.balance:
            return {"success": False, "reason": f"Insufficient balance for paper entry (${cost:.2f})"}

        trade_id = f"BOSS_{symbol}_{_now_et().strftime('%Y%m%d_%H%M%S')}"
        primary_sc = next((s for s in (boss.get("scenarios") or []) if s.get("primary")), None)
        trade = {
            "trade_id": trade_id,
            "symbol": symbol,
            "action": action,
            "entry_price": entry,
            "position_size": contracts,
            "multiplier": multiplier,
            "strike": contract.get("strike"),
            "right": contract.get("right"),
            "bid_at_entry": contract.get("bid"),
            "ask_at_entry": contract.get("ask"),
            "mid_at_entry": contract.get("mid"),
            "entry_time": _now_et().isoformat(),
            "status": "OPEN",
            "confidence": boss.get("confidence"),
            "cost": cost,
            "commission": self.commission_per_trade,
            "data_quality": boss.get("data_quality", "delayed"),
            "venue": boss.get("venue", "local_sim"),
            "invalidation_level": boss.get("invalidation_level"),
            "boss_reason": boss.get("reason"),
            "vote_trail": boss.get("vote_trail"),
            "stock_price_at_entry": boss.get("stock_price"),
            "scenario": (primary_sc or {}).get("scenario") or boss.get("primary_scenario") or "Conservative",
            "tp1": (primary_sc or {}).get("tp1"),
            "tp2": (primary_sc or {}).get("tp2"),
            "stop": (primary_sc or {}).get("stop"),
        }
        self.balance -= cost
        self.positions[trade_id] = trade
        self.trade_history.append(trade)
        self._last_boss_entry_at = _now_et()
        self._save_trades()
        logger.info(
            f"Boss paper OPEN {action} {symbol} {contract.get('right')} {contract.get('strike')} "
            f"@ ask/mark {entry} ({trade['scenario']}) dq={trade['data_quality']}"
        )
        return {"success": True, "trade_id": trade_id, "trade": trade, "remaining_balance": self.balance}

    def manage_boss_positions(
        self,
        symbol: str,
        stock_price: float,
        option_mark: Optional[float],
        boss: Dict,
        option_bid: Optional[float] = None,
    ) -> List[Dict]:
        """
        Exit open Boss paper trades — sell near bid when available.
        Flatten uses America/New_York clock.
        """
        results = []
        now = _now_et()
        for trade_id, trade in list(self.positions.items()):
            if trade.get("symbol") != symbol or trade.get("status") != "OPEN":
                continue
            entry = float(trade.get("entry_price") or 0)
            # Prefer bid for exit (honest sell), else mid/mark
            mark = float(option_bid or 0) or float(option_mark or 0)
            if mark <= 0:
                continue

            reason = None
            inv = trade.get("invalidation_level")
            action = trade.get("action")
            pnl_pct = ((mark - entry) / entry) * 100.0 if entry > 0 else 0.0

            tp1 = trade.get("tp1")
            tp2 = trade.get("tp2")
            stop = trade.get("stop")
            if tp2 and mark >= float(tp2):
                reason = "TP2"
            elif tp1 and mark >= float(tp1):
                reason = "TP1"
            elif stop and mark <= float(stop):
                reason = "STOP"
            elif pnl_pct >= 35:
                reason = "PROFIT_TARGET"
            elif pnl_pct <= -45:
                reason = "STOP_LOSS"

            if reason is None and inv and stock_price > 0:
                if action == "BUY_CALLS" and stock_price < float(inv):
                    reason = "INVALIDATION"
                elif action == "BUY_PUTS" and stock_price > float(inv):
                    reason = "INVALIDATION"

            if reason is None and boss.get("action") in ("BUY_CALLS", "BUY_PUTS"):
                if boss.get("action") != action and boss.get("confidence", 0) >= 70:
                    reason = "BOSS_FLIP"

            try:
                entry_t = datetime.fromisoformat(trade["entry_time"])
                if entry_t.tzinfo is None:
                    entry_t = entry_t.replace(tzinfo=ET)
                if (now - entry_t.astimezone(ET)) >= timedelta(minutes=45):
                    reason = "TIME_STOP"
            except Exception:
                pass

            # Flatten near cash close (ET)
            if reason is None and now.hour == 15 and now.minute >= 55:
                reason = "FLATTEN_BEFORE_CLOSE"

            if not reason:
                continue

            phantom = abs(mark - entry) < 1e-6
            close_res = self._close_trade_sync(trade_id, mark, reason, phantom=phantom)
            results.append(close_res)
        return results

    def _close_trade_sync(self, trade_id: str, exit_price: float, reason: str, phantom: bool = False) -> Dict:
        if trade_id not in self.positions:
            return {"success": False, "reason": "Trade not found"}
        trade = self.positions[trade_id]
        if trade["status"] != "OPEN":
            return {"success": False, "reason": "Trade already closed"}

        entry_price = float(trade["entry_price"])
        position_size = float(trade.get("position_size") or 1)
        multiplier = float(trade.get("multiplier") or 100)
        pnl = (exit_price - entry_price) * position_size * multiplier - self.commission_per_trade
        proceeds = exit_price * position_size * multiplier
        self.balance += proceeds - self.commission_per_trade

        trade["exit_price"] = exit_price
        trade["exit_time"] = _now_et().isoformat()
        trade["status"] = "CLOSED"
        trade["profit_loss"] = 0.0 if phantom else pnl
        trade["profit_loss_pct"] = (
            0.0 if phantom else ((pnl / max(entry_price * position_size * multiplier, 1e-9)) * 100)
        )
        trade["exit_reason"] = reason
        trade["phantom_flat"] = phantom
        trade["count_for_learning"] = (not phantom) and trade.get("data_quality") in (
            "delayed",
            "opra",
            "ibkr_paper",
        )

        del self.positions[trade_id]
        self._save_trades()
        return {
            "success": True,
            "trade_id": trade_id,
            "profit_loss": trade["profit_loss"],
            "profit_loss_pct": trade["profit_loss_pct"],
            "exit_reason": reason,
            "phantom_flat": phantom,
            "count_for_learning": trade["count_for_learning"],
            "vote_trail": trade.get("vote_trail"),
            "action": trade.get("action"),
        }

    def reset(self):
        self.balance = self.initial_balance
        self.positions = {}
        self.trade_history = []
        self._last_boss_entry_at = None
        self._save_trades()
        logger.info("Paper trading account reset")


# Global singleton — REST + WS Boss loop must share this instance
paper_trading_engine = PaperTradingEngine()
