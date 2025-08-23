import asyncio
import json
import os
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from typing import List, Dict, Any

class AlertSystem:
    def __init__(self):
        self.alerts_file = "active_alerts.json"
        self.alert_history_file = "alert_history.json"
        self.alert_cooldown = 300  # 5 minutes cooldown between similar alerts
        self.ensure_files_exist()
    
    def ensure_files_exist(self):
        """Ensure alert files exist"""
        if not os.path.exists(self.alerts_file):
            with open(self.alerts_file, 'w') as f:
                json.dump([], f)
        
        if not os.path.exists(self.alert_history_file):
            with open(self.alert_history_file, 'w') as f:
                json.dump([], f)
    
    async def check_price_alerts(self, symbol, current_price, price_change_pct):
        """Check for price-based alerts"""
        alerts = []
        
        # Large price movements (>3%)
        if abs(price_change_pct) >= 3.0:
            alert_type = "price_spike" if price_change_pct > 0 else "price_drop"
            alerts.append({
                'symbol': symbol,
                'type': alert_type,
                'severity': 'high' if abs(price_change_pct) >= 5 else 'medium',
                'message': f'{symbol} moved {price_change_pct:+.1f}% to ${current_price:.2f}',
                'value': price_change_pct,
                'timestamp': datetime.now().isoformat(),
                'triggered_price': current_price
            })
        
        # Breakout detection (simplified)
        if abs(price_change_pct) >= 2.0:
            direction = "upward" if price_change_pct > 0 else "downward"
            alerts.append({
                'symbol': symbol,
                'type': 'breakout',
                'severity': 'medium',
                'message': f'{symbol} potential {direction} breakout: {price_change_pct:+.1f}%',
                'value': price_change_pct,
                'timestamp': datetime.now().isoformat(),
                'triggered_price': current_price
            })
        
        return alerts
    
    async def check_volume_alerts(self, symbol, volume_data):
        """Check for volume-based alerts"""
        alerts = []
        
        # Unusual volume (3x+ average)
        if volume_data.get('volume_ratio', 1) >= 3.0:
            alerts.append({
                'symbol': symbol,
                'type': 'unusual_volume',
                'severity': 'high' if volume_data['volume_ratio'] >= 5 else 'medium',
                'message': f'{symbol} volume {volume_data["volume_ratio"]:.1f}x above average',
                'value': volume_data['volume_ratio'],
                'timestamp': datetime.now().isoformat()
            })
        
        # Volume spikes
        volume_spikes = volume_data.get('volume_spikes', {})
        if volume_spikes.get('recent_spikes', 0) >= 2:
            alerts.append({
                'symbol': symbol,
                'type': 'volume_spikes',
                'severity': 'medium',
                'message': f'{symbol} multiple volume spikes detected',
                'value': volume_spikes['recent_spikes'],
                'timestamp': datetime.now().isoformat()
            })
        
        # Institutional activity
        institutional = volume_data.get('institutional_activity', {})
        if institutional.get('probability', 0) >= 75:
            alerts.append({
                'symbol': symbol,
                'type': 'institutional_activity',
                'severity': 'high',
                'message': f'{symbol} high institutional activity detected ({institutional["probability"]}%)',
                'value': institutional['probability'],
                'timestamp': datetime.now().isoformat()
            })
        
        return alerts
    
    async def check_options_flow_alerts(self, symbol, flow_data):
        """Check for options flow alerts"""
        alerts = []
        
        if flow_data.empty:
            return alerts
        
        # Calculate unusual factor for each flow
        avg_premium = flow_data['premium'].mean()
        avg_volume = flow_data['volume'].mean()
        
        unusual_flows = flow_data[
            (flow_data['premium'] > avg_premium * 3) | 
            (flow_data['volume'] > avg_volume * 5)
        ]
        
        if len(unusual_flows) > 0:
            total_unusual_premium = unusual_flows['premium'].sum()
            max_flow = unusual_flows.loc[unusual_flows['premium'].idxmax()]
            
            alerts.append({
                'symbol': symbol,
                'type': 'unusual_options_flow',
                'severity': 'high' if total_unusual_premium > 10000000 else 'medium',  # >$10M
                'message': f'{symbol} unusual options flow: ${total_unusual_premium/1000000:.1f}M premium',
                'value': total_unusual_premium,
                'timestamp': datetime.now().isoformat(),
                'details': {
                    'flow_count': len(unusual_flows),
                    'largest_flow': {
                        'type': max_flow['type'],
                        'strike': max_flow['strike'],
                        'premium': max_flow['premium'],
                        'volume': max_flow['volume']
                    }
                }
            })
        
        return alerts
    
    async def check_technical_alerts(self, symbol, indicators):
        """Check for technical indicator alerts"""
        alerts = []
        
        # RSI extreme levels
        rsi = indicators.get('rsi', 50)
        if rsi <= 20:
            alerts.append({
                'symbol': symbol,
                'type': 'rsi_oversold',
                'severity': 'medium',
                'message': f'{symbol} RSI oversold at {rsi:.1f}',
                'value': rsi,
                'timestamp': datetime.now().isoformat()
            })
        elif rsi >= 80:
            alerts.append({
                'symbol': symbol,
                'type': 'rsi_overbought',
                'severity': 'medium',
                'message': f'{symbol} RSI overbought at {rsi:.1f}',
                'value': rsi,
                'timestamp': datetime.now().isoformat()
            })
        
        # MACD crossover (simplified detection)
        macd = indicators.get('macd', 0)
        macd_signal = indicators.get('macd_signal', 0)
        if abs(macd - macd_signal) < 0.1 and macd != 0:  # Near crossover
            direction = "bullish" if macd > macd_signal else "bearish"
            alerts.append({
                'symbol': symbol,
                'type': 'macd_crossover',
                'severity': 'low',
                'message': f'{symbol} potential {direction} MACD crossover',
                'value': macd - macd_signal,
                'timestamp': datetime.now().isoformat()
            })
        
        # Bollinger Band breakouts
        bb_upper = indicators.get('bb_upper', 0)
        bb_lower = indicators.get('bb_lower', 0)
        current_price = indicators.get('current_price', 0)
        
        if current_price > bb_upper and bb_upper > 0:
            alerts.append({
                'symbol': symbol,
                'type': 'bb_breakout_upper',
                'severity': 'medium',
                'message': f'{symbol} broke above upper Bollinger Band',
                'value': (current_price - bb_upper) / bb_upper * 100,
                'timestamp': datetime.now().isoformat()
            })
        elif current_price < bb_lower and bb_lower > 0:
            alerts.append({
                'symbol': symbol,
                'type': 'bb_breakout_lower',
                'severity': 'medium',
                'message': f'{symbol} broke below lower Bollinger Band',
                'value': (bb_lower - current_price) / bb_lower * 100,
                'timestamp': datetime.now().isoformat()
            })
        
        return alerts
    
    def is_alert_on_cooldown(self, alert):
        """Check if similar alert is on cooldown"""
        try:
            with open(self.alert_history_file, 'r') as f:
                history = json.load(f)
            
            current_time = datetime.now()
            cooldown_time = current_time - timedelta(seconds=self.alert_cooldown)
            
            for past_alert in history:
                past_time = datetime.fromisoformat(past_alert['timestamp'])
                if (past_time > cooldown_time and 
                    past_alert['symbol'] == alert['symbol'] and 
                    past_alert['type'] == alert['type']):
                    return True
            
            return False
            
        except:
            return False
    
    def save_alert(self, alert):
        """Save alert to history and active alerts"""
        if self.is_alert_on_cooldown(alert):
            return False
        
        try:
            # Add to active alerts
            with open(self.alerts_file, 'r') as f:
                active_alerts = json.load(f)
            
            active_alerts.append(alert)
            
            # Keep only last 50 active alerts
            if len(active_alerts) > 50:
                active_alerts = active_alerts[-50:]
            
            with open(self.alerts_file, 'w') as f:
                json.dump(active_alerts, f, indent=2)
            
            # Add to history
            with open(self.alert_history_file, 'r') as f:
                history = json.load(f)
            
            history.append(alert)
            
            # Keep only last 1000 historical alerts
            if len(history) > 1000:
                history = history[-1000:]
            
            with open(self.alert_history_file, 'w') as f:
                json.dump(history, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Error saving alert: {e}")
            return False
    
    def get_active_alerts(self, max_alerts=10):
        """Get current active alerts"""
        try:
            with open(self.alerts_file, 'r') as f:
                alerts = json.load(f)
            
            # Sort by timestamp (most recent first) and limit
            alerts.sort(key=lambda x: x['timestamp'], reverse=True)
            return alerts[:max_alerts]
            
        except:
            return []
    
    def clear_old_alerts(self, hours=24):
        """Clear alerts older than specified hours"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            with open(self.alerts_file, 'r') as f:
                alerts = json.load(f)
            
            # Keep only recent alerts
            recent_alerts = []
            for alert in alerts:
                alert_time = datetime.fromisoformat(alert['timestamp'])
                if alert_time > cutoff_time:
                    recent_alerts.append(alert)
            
            with open(self.alerts_file, 'w') as f:
                json.dump(recent_alerts, f, indent=2)
            
            return len(alerts) - len(recent_alerts)  # Number of alerts cleared
            
        except Exception as e:
            print(f"Error clearing old alerts: {e}")
            return 0
    
    def get_alert_summary(self):
        """Get summary of alert activity"""
        try:
            with open(self.alert_history_file, 'r') as f:
                history = json.load(f)
            
            if not history:
                return {'total_alerts': 0, 'by_type': {}, 'by_severity': {}, 'by_symbol': {}}
            
            # Count by type
            by_type = {}
            by_severity = {}
            by_symbol = {}
            
            for alert in history:
                alert_type = alert.get('type', 'unknown')
                severity = alert.get('severity', 'unknown')
                symbol = alert.get('symbol', 'unknown')
                
                by_type[alert_type] = by_type.get(alert_type, 0) + 1
                by_severity[severity] = by_severity.get(severity, 0) + 1
                by_symbol[symbol] = by_symbol.get(symbol, 0) + 1
            
            return {
                'total_alerts': len(history),
                'by_type': by_type,
                'by_severity': by_severity,
                'by_symbol': by_symbol
            }
            
        except:
            return {'total_alerts': 0, 'by_type': {}, 'by_severity': {}, 'by_symbol': {}}
    
    async def process_all_alerts(self, symbol, current_price, price_change_pct, volume_data, flow_data, indicators):
        """Process all types of alerts for a symbol"""
        all_alerts = []
        
        # Check all alert types
        price_alerts = await self.check_price_alerts(symbol, current_price, price_change_pct)
        volume_alerts = await self.check_volume_alerts(symbol, volume_data)
        flow_alerts = await self.check_options_flow_alerts(symbol, flow_data)
        technical_alerts = await self.check_technical_alerts(symbol, indicators)
        
        all_alerts.extend(price_alerts)
        all_alerts.extend(volume_alerts)
        all_alerts.extend(flow_alerts)
        all_alerts.extend(technical_alerts)
        
        # Save new alerts
        saved_alerts = []
        for alert in all_alerts:
            if self.save_alert(alert):
                saved_alerts.append(alert)
        
        return saved_alerts