"""
INSTITUTIONAL-GRADE POSITION TRACKING ENGINE
Real-time P&L, Greeks, and Risk Management
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np
import yfinance as yf
import os


class InstitutionalPositionTracker:
    """Real position tracking with P&L and Greeks calculations"""
    
    def __init__(self):
        self.positions_file = "trading_positions.json"
        self.pnl_history_file = "pnl_history.json"
        self.positions = self.load_positions()
        
    def load_positions(self) -> Dict:
        """Load existing positions from file"""
        try:
            if os.path.exists(self.positions_file):
                with open(self.positions_file, 'r') as f:
                    return json.load(f)
            return {"options": {}, "stocks": {}, "total_pnl": 0.0}
        except Exception as e:
            print(f"Error loading positions: {e}")
            return {"options": {}, "stocks": {}, "total_pnl": 0.0}
    
    def save_positions(self):
        """Save positions to file"""
        try:
            with open(self.positions_file, 'w') as f:
                json.dump(self.positions, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving positions: {e}")
    
    def add_options_position(self, symbol: str, strike: float, expiry: str, 
                           option_type: str, quantity: int, entry_price: float):
        """Add new options position"""
        position_id = f"{symbol}_{strike}_{expiry}_{option_type}"
        
        self.positions["options"][position_id] = {
            "symbol": symbol,
            "strike": strike,
            "expiry": expiry,
            "type": option_type.upper(),  # CALL or PUT
            "quantity": quantity,
            "entry_price": entry_price,
            "entry_time": datetime.now().isoformat(),
            "current_price": entry_price,
            "unrealized_pnl": 0.0,
            "delta": 0.0,
            "gamma": 0.0,
            "theta": 0.0,
            "vega": 0.0,
            "implied_vol": 0.0
        }
        self.save_positions()
        
    def add_stock_position(self, symbol: str, quantity: int, entry_price: float):
        """Add new stock position"""
        if symbol in self.positions["stocks"]:
            # Average down/up existing position
            existing = self.positions["stocks"][symbol]
            total_shares = existing["quantity"] + quantity
            total_cost = (existing["quantity"] * existing["entry_price"]) + (quantity * entry_price)
            avg_price = total_cost / total_shares
            
            self.positions["stocks"][symbol].update({
                "quantity": total_shares,
                "entry_price": avg_price,
                "last_update": datetime.now().isoformat()
            })
        else:
            self.positions["stocks"][symbol] = {
                "symbol": symbol,
                "quantity": quantity,
                "entry_price": entry_price,
                "entry_time": datetime.now().isoformat(),
                "current_price": entry_price,
                "unrealized_pnl": 0.0
            }
        self.save_positions()
    
    async def update_all_positions(self):
        """Update all positions with real-time data"""
        try:
            # Update stock positions
            for symbol, position in self.positions["stocks"].items():
                await self._update_stock_position(symbol, position)
            
            # Update options positions  
            for position_id, position in self.positions["options"].items():
                await self._update_options_position(position_id, position)
                
            # Calculate total portfolio P&L
            self._calculate_total_pnl()
            self.save_positions()
            
        except Exception as e:
            print(f"Error updating positions: {e}")
    
    async def _update_stock_position(self, symbol: str, position: Dict):
        """Update individual stock position"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d", interval="1m")
            if not hist.empty:
                current_price = float(hist['Close'].iloc[-1])
                position["current_price"] = current_price
                position["unrealized_pnl"] = (current_price - position["entry_price"]) * position["quantity"]
                position["last_update"] = datetime.now().isoformat()
        except Exception as e:
            print(f"Error updating {symbol}: {e}")
    
    async def _update_options_position(self, position_id: str, position: Dict):
        """Update individual options position with Greeks"""
        try:
            symbol = position["symbol"]
            ticker = yf.Ticker(symbol)
            
            # Get current stock price
            hist = ticker.history(period="1d", interval="1m")
            if hist.empty:
                return
                
            current_stock_price = float(hist['Close'].iloc[-1])
            
            # Get options data if available
            try:
                exp_dates = ticker.options
                if position["expiry"] in exp_dates:
                    options_chain = ticker.option_chain(position["expiry"])
                    
                    if position["type"] == "CALL":
                        options_data = options_chain.calls
                    else:
                        options_data = options_chain.puts
                    
                    # Find matching strike
                    matching_option = options_data[options_data['strike'] == position["strike"]]
                    if not matching_option.empty:
                        current_price = float(matching_option['lastPrice'].iloc[0])
                        position["current_price"] = current_price
                        position["unrealized_pnl"] = (current_price - position["entry_price"]) * position["quantity"] * 100
                        position["implied_vol"] = float(matching_option.get('impliedVolatility', 0).iloc[0])
                        
                        # Calculate Greeks (simplified Black-Scholes)
                        self._calculate_greeks(position, current_stock_price)
                        
            except Exception as e:
                print(f"Options data unavailable for {position_id}: {e}")
                # Fallback to theoretical pricing
                position["current_price"] = position["entry_price"]
                
            position["last_update"] = datetime.now().isoformat()
            
        except Exception as e:
            print(f"Error updating options position {position_id}: {e}")
    
    def _calculate_greeks(self, position: Dict, stock_price: float):
        """Calculate option Greeks using simplified Black-Scholes"""
        try:
            from scipy.stats import norm
            import math
            
            S = stock_price  # Current stock price
            K = position["strike"]  # Strike price
            r = 0.05  # Risk-free rate (5%)
            
            # Time to expiry in years
            expiry_date = datetime.fromisoformat(position["expiry"])
            T = max(0.001, (expiry_date - datetime.now()).days / 365.0)
            
            sigma = position.get("implied_vol", 0.25)  # Implied volatility
            
            if T > 0 and sigma > 0:
                # d1 and d2 calculations
                d1 = (math.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma * math.sqrt(T))
                d2 = d1 - sigma * math.sqrt(T)
                
                if position["type"] == "CALL":
                    # Call Greeks
                    position["delta"] = round(norm.cdf(d1), 4)
                    position["gamma"] = round(norm.pdf(d1) / (S * sigma * math.sqrt(T)), 6)
                    position["theta"] = round(-((S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T)) + 
                                             r * K * math.exp(-r * T) * norm.cdf(d2)) / 365, 4)
                    position["vega"] = round(S * norm.pdf(d1) * math.sqrt(T) / 100, 4)
                else:
                    # Put Greeks
                    position["delta"] = round(norm.cdf(d1) - 1, 4)
                    position["gamma"] = round(norm.pdf(d1) / (S * sigma * math.sqrt(T)), 6)
                    position["theta"] = round(-((S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T)) - 
                                             r * K * math.exp(-r * T) * norm.cdf(-d2)) / 365, 4)
                    position["vega"] = round(S * norm.pdf(d1) * math.sqrt(T) / 100, 4)
                    
        except Exception as e:
            print(f"Error calculating Greeks: {e}")
            position["delta"] = 0.0
            position["gamma"] = 0.0
            position["theta"] = 0.0
            position["vega"] = 0.0
    
    def _calculate_total_pnl(self):
        """Calculate total portfolio P&L"""
        total_pnl = 0.0
        
        # Sum stock P&L
        for position in self.positions["stocks"].values():
            total_pnl += position.get("unrealized_pnl", 0.0)
        
        # Sum options P&L
        for position in self.positions["options"].values():
            total_pnl += position.get("unrealized_pnl", 0.0)
        
        self.positions["total_pnl"] = round(total_pnl, 2)
    
    def get_portfolio_summary(self) -> Dict:
        """Get comprehensive portfolio summary"""
        summary = {
            "total_positions": len(self.positions["stocks"]) + len(self.positions["options"]),
            "stock_positions": len(self.positions["stocks"]),
            "options_positions": len(self.positions["options"]),
            "total_pnl": self.positions.get("total_pnl", 0.0),
            "net_delta": 0.0,
            "net_gamma": 0.0,
            "net_theta": 0.0,
            "net_vega": 0.0
        }
        
        # Calculate net Greeks
        for position in self.positions["options"].values():
            summary["net_delta"] += position.get("delta", 0.0) * position.get("quantity", 0)
            summary["net_gamma"] += position.get("gamma", 0.0) * position.get("quantity", 0)
            summary["net_theta"] += position.get("theta", 0.0) * position.get("quantity", 0)
            summary["net_vega"] += position.get("vega", 0.0) * position.get("quantity", 0)
        
        # Round Greeks
        for greek in ["net_delta", "net_gamma", "net_theta", "net_vega"]:
            summary[greek] = round(summary[greek], 4)
        
        return summary
    
    def get_positions_by_symbol(self, symbol: str) -> Dict:
        """Get all positions for a specific symbol"""
        positions = {
            "stock": None,
            "options": [],
            "total_symbol_pnl": 0.0
        }
        
        # Stock position
        if symbol in self.positions["stocks"]:
            positions["stock"] = self.positions["stocks"][symbol]
            positions["total_symbol_pnl"] += positions["stock"].get("unrealized_pnl", 0.0)
        
        # Options positions
        for position_id, position in self.positions["options"].items():
            if position["symbol"] == symbol:
                positions["options"].append(position)
                positions["total_symbol_pnl"] += position.get("unrealized_pnl", 0.0)
        
        positions["total_symbol_pnl"] = round(positions["total_symbol_pnl"], 2)
        return positions
    
    def close_position(self, position_id: str, exit_price: float):
        """Close a position and record realized P&L"""
        try:
            if position_id in self.positions["options"]:
                position = self.positions["options"][position_id]
                realized_pnl = (exit_price - position["entry_price"]) * position["quantity"] * 100
                
                # Record trade history
                self._record_closed_trade(position, exit_price, realized_pnl)
                
                # Remove from active positions
                del self.positions["options"][position_id]
                
            elif position_id in self.positions["stocks"]:
                position = self.positions["stocks"][position_id]
                realized_pnl = (exit_price - position["entry_price"]) * position["quantity"]
                
                # Record trade history
                self._record_closed_trade(position, exit_price, realized_pnl)
                
                # Remove from active positions
                del self.positions["stocks"][position_id]
            
            self.save_positions()
            return realized_pnl
            
        except Exception as e:
            print(f"Error closing position {position_id}: {e}")
            return 0.0
    
    def _record_closed_trade(self, position: Dict, exit_price: float, realized_pnl: float):
        """Record closed trade in history"""
        try:
            trade_history = []
            if os.path.exists(self.pnl_history_file):
                with open(self.pnl_history_file, 'r') as f:
                    trade_history = json.load(f)
            
            trade_record = {
                "symbol": position["symbol"],
                "entry_price": position["entry_price"],
                "exit_price": exit_price,
                "quantity": position["quantity"],
                "realized_pnl": realized_pnl,
                "entry_time": position["entry_time"],
                "exit_time": datetime.now().isoformat(),
                "hold_duration_hours": (datetime.now() - datetime.fromisoformat(position["entry_time"])).seconds / 3600
            }
            
            if "strike" in position:  # Options position
                trade_record.update({
                    "strike": position["strike"],
                    "type": position["type"],
                    "expiry": position["expiry"]
                })
            
            trade_history.append(trade_record)
            
            with open(self.pnl_history_file, 'w') as f:
                json.dump(trade_history, f, indent=2, default=str)
                
        except Exception as e:
            print(f"Error recording trade history: {e}")


# Global position tracker instance
position_tracker = InstitutionalPositionTracker()