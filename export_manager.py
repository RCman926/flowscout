"""
Export Manager
Handles exporting trades, performance reports, and data
"""

import json
import csv
import os
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ExportManager:
    """
    Manages exporting of:
    - Trade history (CSV, JSON)
    - Performance reports (PDF-like text, JSON)
    - Options flow data (CSV)
    """
    
    def __init__(self):
        self.exports_dir = "exports"
        if not os.path.exists(self.exports_dir):
            os.makedirs(self.exports_dir)
    
    def export_trades_csv(self, trades: List[Dict], filename: Optional[str] = None) -> str:
        """Export trades to CSV"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trades_export_{timestamp}.csv"
        
        filepath = os.path.join(self.exports_dir, filename)
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                if not trades:
                    writer = csv.writer(f)
                    writer.writerow(['No trades to export'])
                    return filepath
                
                # Get all unique keys from trades
                fieldnames = set()
                for trade in trades:
                    fieldnames.update(trade.keys())
                fieldnames = sorted(list(fieldnames))
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for trade in trades:
                    # Convert dict values to strings for CSV
                    row = {}
                    for key, value in trade.items():
                        if isinstance(value, (dict, list)):
                            row[key] = json.dumps(value)
                        else:
                            row[key] = str(value) if value is not None else ''
                    writer.writerow(row)
            
            logger.info(f"Exported {len(trades)} trades to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error exporting trades to CSV: {e}")
            raise
    
    def export_trades_json(self, trades: List[Dict], filename: Optional[str] = None) -> str:
        """Export trades to JSON"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trades_export_{timestamp}.json"
        
        filepath = os.path.join(self.exports_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'export_date': datetime.now().isoformat(),
                    'total_trades': len(trades),
                    'trades': trades
                }, f, indent=2, default=str)
            
            logger.info(f"Exported {len(trades)} trades to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error exporting trades to JSON: {e}")
            raise
    
    def export_performance_report(self, performance_data: Dict, filename: Optional[str] = None) -> str:
        """Export performance report as text file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_report_{timestamp}.txt"
        
        filepath = os.path.join(self.exports_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("FLOWSCOUT PRO - PERFORMANCE REPORT\n")
                f.write("=" * 60 + "\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Overall stats
                f.write("OVERALL PERFORMANCE\n")
                f.write("-" * 60 + "\n")
                f.write(f"Total Trades: {performance_data.get('total_trades', 0)}\n")
                f.write(f"Wins: {performance_data.get('wins', 0)}\n")
                f.write(f"Losses: {performance_data.get('losses', 0)}\n")
                f.write(f"Win Rate: {performance_data.get('win_rate', 0):.2f}%\n")
                f.write(f"Total P&L: ${performance_data.get('total_pnl', 0):,.2f}\n")
                f.write(f"Average Profit: ${performance_data.get('avg_profit', 0):,.2f}\n")
                f.write(f"Average Loss: ${performance_data.get('avg_loss', 0):,.2f}\n")
                f.write(f"Profit Factor: {performance_data.get('profit_factor', 0):.2f}\n\n")
                
                # Best/Worst trades
                if performance_data.get('best_trade'):
                    f.write("BEST TRADE\n")
                    f.write("-" * 60 + "\n")
                    best = performance_data['best_trade']
                    f.write(f"Trade ID: {best.get('trade_id', 'N/A')}\n")
                    f.write(f"Action: {best.get('action', 'N/A')}\n")
                    f.write(f"P&L: ${best.get('profit_loss', 0):,.2f} ({best.get('profit_loss_pct', 0):.2f}%)\n\n")
                
                if performance_data.get('worst_trade'):
                    f.write("WORST TRADE\n")
                    f.write("-" * 60 + "\n")
                    worst = performance_data['worst_trade']
                    f.write(f"Trade ID: {worst.get('trade_id', 'N/A')}\n")
                    f.write(f"Action: {worst.get('action', 'N/A')}\n")
                    f.write(f"P&L: ${worst.get('profit_loss', 0):,.2f} ({worst.get('profit_loss_pct', 0):.2f}%)\n\n")
                
                # Recent trades
                if performance_data.get('recent_trades'):
                    f.write("RECENT TRADES\n")
                    f.write("-" * 60 + "\n")
                    for trade in performance_data['recent_trades'][:10]:
                        f.write(f"{trade.get('entry_time', 'N/A')} | {trade.get('action', 'N/A')} | "
                               f"${trade.get('profit_loss', 0):,.2f} | {trade.get('result', 'N/A')}\n")
            
            logger.info(f"Exported performance report to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error exporting performance report: {e}")
            raise
    
    def export_performance_json(self, performance_data: Dict, filename: Optional[str] = None) -> str:
        """Export performance data to JSON"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_data_{timestamp}.json"
        
        filepath = os.path.join(self.exports_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'export_date': datetime.now().isoformat(),
                    'performance': performance_data
                }, f, indent=2, default=str)
            
            logger.info(f"Exported performance data to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error exporting performance data: {e}")
            raise


# Global instance
export_manager = ExportManager()

