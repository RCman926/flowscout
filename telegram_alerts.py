"""
Smart Telegram Alerts System for Options Trading Platform
Sends real-time notifications for unusual activity, price targets, and custom signals
"""

import requests
import os
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class TelegramAlertsEngine:
    def __init__(self):
        self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = "6314164168"  # User's chat ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        # Alert cooldown tracking (prevent spam)
        self.last_alerts = {}
        self.cooldown_minutes = 5
        
        # Alert history for analytics
        self.alert_history = []
        
    def send_alert(self, message: str, alert_type: str = "general", disable_notification: bool = False) -> bool:
        """Send a Telegram alert with spam protection"""
        try:
            if not self.bot_token:
                return False
                
            # Check cooldown for this alert type
            now = datetime.now()
            cooldown_key = f"{alert_type}_{hash(message[:50])}"  # Use first 50 chars as key
            
            if cooldown_key in self.last_alerts:
                time_since_last = (now - self.last_alerts[cooldown_key]).total_seconds() / 60
                if time_since_last < self.cooldown_minutes:
                    return False  # Still in cooldown
            
            # Send the alert
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_notification': disable_notification
            }
            
            response = requests.post(f"{self.base_url}/sendMessage", json=payload, timeout=10)
            
            if response.status_code == 200:
                # Update cooldown tracking
                self.last_alerts[cooldown_key] = now
                
                # Log alert
                self.alert_history.append({
                    'timestamp': now.isoformat(),
                    'type': alert_type,
                    'message': message[:100],  # Truncated for storage
                    'success': True
                })
                
                return True
            else:
                return False
                
        except Exception as e:
            return False
    
    def check_unusual_options_activity(self, symbol: str, call_data: List[Dict], put_data: List[Dict], 
                                     call_volume: int, put_volume: int, alert_settings: Dict) -> None:
        """Check for unusual options activity and send alerts"""
        
        if not alert_settings.get('unusual_activity', False):
            return
            
        # Volume thresholds
        high_volume_threshold = alert_settings.get('volume_threshold', 1000)
        unusual_ratio_threshold = alert_settings.get('ratio_threshold', 3.0)
        
        alerts_sent = []
        
        # Check total volume
        total_volume = call_volume + put_volume
        if total_volume > high_volume_threshold * 2:
            message = f"""
🚨 *UNUSUAL VOLUME ALERT*
Symbol: *{symbol}*
Total Volume: *{total_volume:,}*
Calls: {call_volume:,} | Puts: {put_volume:,}

📊 This is {total_volume/high_volume_threshold:.1f}x normal volume!
🕐 {datetime.now().strftime('%H:%M:%S')}
            """
            if self.send_alert(message, "unusual_volume"):
                alerts_sent.append("High Volume")
        
        # Check call/put ratio extremes
        if put_volume > 0:
            cp_ratio = call_volume / put_volume
            
            if cp_ratio > unusual_ratio_threshold:
                message = f"""
🟢 *STRONG CALL FLOW ALERT*
Symbol: *{symbol}*
C/P Ratio: *{cp_ratio:.2f}*
Call Volume: {call_volume:,}
Put Volume: {put_volume:,}

📈 Extremely bullish flow detected!
🕐 {datetime.now().strftime('%H:%M:%S')}
                """
                if self.send_alert(message, "call_flow"):
                    alerts_sent.append("Call Flow")
                    
            elif cp_ratio < (1 / unusual_ratio_threshold):
                message = f"""
🔴 *STRONG PUT FLOW ALERT*
Symbol: *{symbol}*
C/P Ratio: *{cp_ratio:.2f}*
Call Volume: {call_volume:,}
Put Volume: {put_volume:,}

📉 Extremely bearish flow detected!
🕐 {datetime.now().strftime('%H:%M:%S')}
                """
                if self.send_alert(message, "put_flow"):
                    alerts_sent.append("Put Flow")
        
        # Check individual strike unusual activity
        for call in call_data:
            vol = int(call.get('Vol', '0').replace(',', ''))
            if vol > high_volume_threshold:
                strike = call.get('Strike', 'Unknown')
                message = f"""
⚡ *SINGLE STRIKE ALERT*
Symbol: *{symbol}*
Strike: *{strike}* CALL
Volume: *{vol:,}*
Price: {call.get('Last', 'N/A')}

🎯 Massive activity on single strike!
🕐 {datetime.now().strftime('%H:%M:%S')}
                """
                if self.send_alert(message, "single_strike"):
                    alerts_sent.append(f"Call {strike}")
                    break  # Only alert once per scan
        
        for put in put_data:
            vol = int(put.get('Vol', '0').replace(',', ''))
            if vol > high_volume_threshold:
                strike = put.get('Strike', 'Unknown')
                message = f"""
⚡ *SINGLE STRIKE ALERT*
Symbol: *{symbol}*
Strike: *{strike}* PUT
Volume: *{vol:,}*
Price: {put.get('Last', 'N/A')}

🎯 Massive activity on single strike!
🕐 {datetime.now().strftime('%H:%M:%S')}
                """
                if self.send_alert(message, "single_strike"):
                    alerts_sent.append(f"Put {strike}")
                    break  # Only alert once per scan
    
    def check_price_targets(self, symbol: str, current_price: float, support: float, 
                          resistance: float, alert_settings: Dict) -> None:
        """Check for support/resistance breaks and send alerts"""
        
        if not alert_settings.get('price_targets', False):
            return
            
        # Calculate distances
        resistance_distance = abs(current_price - resistance) / current_price
        support_distance = abs(current_price - support) / current_price
        
        # Alert if within threshold of key levels
        proximity_threshold = alert_settings.get('proximity_threshold', 0.01)  # 1%
        
        if resistance_distance < proximity_threshold and current_price < resistance:
            message = f"""
🎯 *RESISTANCE APPROACH ALERT*
Symbol: *{symbol}*
Current: *${current_price:.2f}*
Resistance: *${resistance:.2f}*
Distance: {resistance_distance*100:.1f}%

📈 Approaching key resistance level!
🕐 {datetime.now().strftime('%H:%M:%S')}
            """
            self.send_alert(message, "resistance_approach")
            
        elif support_distance < proximity_threshold and current_price > support:
            message = f"""
🎯 *SUPPORT APPROACH ALERT*
Symbol: *{symbol}*
Current: *${current_price:.2f}*
Support: *${support:.2f}*
Distance: {support_distance*100:.1f}%

📉 Approaching key support level!
🕐 {datetime.now().strftime('%H:%M:%S')}
            """
            self.send_alert(message, "support_approach")
        
        # Break alerts
        if current_price > resistance:
            message = f"""
🚀 *RESISTANCE BREAK ALERT*
Symbol: *{symbol}*
Current: *${current_price:.2f}*
Resistance: *${resistance:.2f}*

📈 BULLISH BREAKOUT!
🕐 {datetime.now().strftime('%H:%M:%S')}
            """
            self.send_alert(message, "resistance_break")
            
        elif current_price < support:
            message = f"""
💥 *SUPPORT BREAK ALERT*
Symbol: *{symbol}*
Current: *${current_price:.2f}*
Support: *${support:.2f}*

📉 BEARISH BREAKDOWN!
🕐 {datetime.now().strftime('%H:%M:%S')}
            """
            self.send_alert(message, "support_break")
    
    def check_volatility_spikes(self, symbol: str, current_iv: float, historical_iv: float, 
                              alert_settings: Dict) -> None:
        """Check for implied volatility spikes"""
        
        if not alert_settings.get('volatility_spikes', False):
            return
            
        spike_threshold = alert_settings.get('iv_spike_threshold', 1.5)  # 50% increase
        
        if current_iv > historical_iv * spike_threshold:
            increase_pct = ((current_iv / historical_iv) - 1) * 100
            message = f"""
📊 *VOLATILITY SPIKE ALERT*
Symbol: *{symbol}*
Current IV: *{current_iv:.1f}%*
Historical: {historical_iv:.1f}%
Increase: *+{increase_pct:.0f}%*

⚡ Significant volatility expansion!
🕐 {datetime.now().strftime('%H:%M:%S')}
            """
            self.send_alert(message, "volatility_spike")
    
    def check_trading_signals(self, symbol: str, signal: str, confidence: float, 
                            signal_details: Dict, alert_settings: Dict) -> None:
        """Check trading signals and send alerts"""
        
        if not alert_settings.get('trading_signals', False):
            return
            
        min_confidence = alert_settings.get('min_signal_confidence', 60)
        
        if confidence >= min_confidence and signal in ['CALL', 'PUT']:
            emoji = "🟢" if signal == "CALL" else "🔴"
            direction = "BULLISH" if signal == "CALL" else "BEARISH"
            
            message = f"""
{emoji} *{direction} SIGNAL ALERT*
Symbol: *{symbol}*
Signal: *{signal}*
Confidence: *{confidence:.0f}%*

📊 High-confidence trading signal detected!
🎯 Consider {signal.lower()} options
🕐 {datetime.now().strftime('%H:%M:%S')}
            """
            self.send_alert(message, "trading_signal")
    
    def check_0dte_alerts(self, symbol: str, dte: int, flow_direction: str, momentum: float,
                         time_to_close: float, alert_settings: Dict) -> None:
        """Special alerts for 0DTE options"""
        
        if not alert_settings.get('dte_alerts', False) or dte > 0:
            return
        
        # High momentum 0DTE alert
        if momentum > 75:
            message = f"""
🔥 *0DTE HIGH MOMENTUM ALERT*
Symbol: *{symbol}*
Flow: *{flow_direction}*
Momentum: *{momentum:.0f}%*
Time Left: {time_to_close:.1f}h

⚡ Extreme 0DTE activity!
🕐 {datetime.now().strftime('%H:%M:%S')}
            """
            self.send_alert(message, "0dte_momentum")
        
        # Time decay warning
        if time_to_close < 1 and momentum > 50:  # Less than 1 hour left
            message = f"""
⏰ *0DTE TIME DECAY WARNING*
Symbol: *{symbol}*
Time Left: *{time_to_close:.1f}h*
Flow: {flow_direction}

⚠️ Time decay accelerating!
🕐 {datetime.now().strftime('%H:%M:%S')}
            """
            self.send_alert(message, "time_decay", disable_notification=True)
    
    def send_test_alert(self) -> bool:
        """Send a test alert to verify connection"""
        message = f"""
✅ *TEST ALERT*
Your Telegram alerts are working!

🚀 Platform: Options Trading
🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

You'll now receive real-time alerts for:
• Unusual options activity
• Price target breaks  
• Volatility spikes
• Trading signals
• 0DTE alerts
        """
        return self.send_alert(message, "test")
    
    def get_alert_stats(self) -> Dict:
        """Get alert statistics"""
        if not self.alert_history:
            return {"total": 0, "today": 0, "types": {}}
        
        today = datetime.now().date()
        today_alerts = [a for a in self.alert_history 
                       if datetime.fromisoformat(a['timestamp']).date() == today]
        
        types_count = {}
        for alert in self.alert_history:
            alert_type = alert['type']
            types_count[alert_type] = types_count.get(alert_type, 0) + 1
        
        return {
            "total": len(self.alert_history),
            "today": len(today_alerts),
            "types": types_count,
            "success_rate": sum(1 for a in self.alert_history if a['success']) / len(self.alert_history) * 100
        }

# Global instance
telegram_alerts = TelegramAlertsEngine()