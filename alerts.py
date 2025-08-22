import asyncio
import os
import smtplib
from datetime import datetime
import json

try:
    import telegram
except ImportError:
    telegram = None

try:
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
except ImportError:
    MimeText = None
    MimeMultipart = None

class AlertManager:
    def __init__(self):
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "8157079885:AAEgFRkDFwhlO4NQpxZ731iX_jLojGc29KY")
        self.alert_history = []
        self.alert_cooldown = {}  # Prevent spam alerts
        self.cooldown_period = 300  # 5 minutes in seconds
        
    async def send_telegram_alert(self, chat_id, message, parse_mode='HTML'):
        """Send Telegram alert"""
        try:
            if not telegram:
                print("Telegram functionality not available - missing telegram library")
                return False
                
            if not self.telegram_bot_token or not chat_id:
                return False
                
            bot = telegram.Bot(token=self.telegram_bot_token)
            await bot.send_message(
                chat_id=chat_id, 
                text=message, 
                parse_mode=parse_mode
            )
            
            # Log alert
            self._log_alert("telegram", chat_id, message)
            return True
            
        except Exception as e:
            print(f"Telegram alert failed: {e}")
            return False
    
    async def send_email_alert(self, recipient_email, subject, message):
        """Send email alert"""
        try:
            if not MimeText or not MimeMultipart:
                print("Email functionality not available - missing email libraries")
                return False
                
            smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            sender_email = os.getenv("SENDER_EMAIL", "")
            sender_password = os.getenv("SENDER_PASSWORD", "")
            
            if not all([sender_email, sender_password, recipient_email]):
                return False
            
            # Create message
            msg = MimeMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            msg.attach(MimeText(message, 'html'))
            
            # Send email
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            
            # Log alert
            self._log_alert("email", recipient_email, f"{subject}: {message}")
            return True
            
        except Exception as e:
            print(f"Email alert failed: {e}")
            return False
    
    def _log_alert(self, alert_type, recipient, message):
        """Log alert to history"""
        self.alert_history.append({
            'timestamp': datetime.now(),
            'type': alert_type,
            'recipient': recipient,
            'message': message[:100] + "..." if len(message) > 100 else message
        })
        
        # Keep only last 100 alerts
        if len(self.alert_history) > 100:
            self.alert_history = self.alert_history[-100:]
    
    def _should_send_alert(self, alert_key):
        """Check if alert should be sent based on cooldown"""
        now = datetime.now().timestamp()
        
        if alert_key in self.alert_cooldown:
            time_since_last = now - self.alert_cooldown[alert_key]
            if time_since_last < self.cooldown_period:
                return False
        
        self.alert_cooldown[alert_key] = now
        return True
    
    async def send_options_flow_alert(self, chat_id, symbol, flow_data):
        """Send specialized options flow alert"""
        try:
            if not self._should_send_alert(f"flow_{symbol}_{flow_data['strike']}_{flow_data['type']}"):
                return False
            
            # Format options flow message
            message = f"🚨 <b>Unusual Options Activity</b>\n\n"
            message += f"📊 <b>{symbol}</b> - {flow_data['type']}\n"
            message += f"💰 Strike: ${flow_data['strike']}\n"
            message += f"📅 Expiry: {flow_data['expiry']}\n"
            message += f"📈 Volume: {flow_data['volume']:,} ({flow_data.get('unusual_factor', 0):.1f}x avg)\n"
            message += f"💵 Premium: ${flow_data['premium']:,.0f}\n"
            message += f"🎯 Delta: {flow_data.get('delta', 0):.3f}\n"
            message += f"⚡ IV: {flow_data.get('iv', 0)*100:.1f}%\n"
            message += f"⏰ {datetime.now().strftime('%H:%M:%S')}"
            
            return await self.send_telegram_alert(chat_id, message)
            
        except Exception as e:
            print(f"Options flow alert error: {e}")
            return False
    
    async def send_price_alert(self, chat_id, symbol, current_price, trigger_price, alert_type):
        """Send price movement alert"""
        try:
            alert_key = f"price_{symbol}_{alert_type}"
            if not self._should_send_alert(alert_key):
                return False
            
            direction = "🔴" if alert_type == "below" else "🟢"
            message = f"{direction} <b>Price Alert</b>\n\n"
            message += f"📊 <b>{symbol}</b>\n"
            message += f"💰 Current: ${current_price:.2f}\n"
            message += f"🎯 Target: ${trigger_price:.2f}\n"
            message += f"📈 Status: Price is {alert_type} target\n"
            message += f"⏰ {datetime.now().strftime('%H:%M:%S')}"
            
            return await self.send_telegram_alert(chat_id, message)
            
        except Exception as e:
            print(f"Price alert error: {e}")
            return False
    
    async def send_technical_alert(self, chat_id, symbol, indicator, value, condition):
        """Send technical indicator alert"""
        try:
            alert_key = f"technical_{symbol}_{indicator}_{condition}"
            if not self._should_send_alert(alert_key):
                return False
            
            message = f"📊 <b>Technical Alert</b>\n\n"
            message += f"📈 <b>{symbol}</b>\n"
            message += f"🔍 Indicator: {indicator.upper()}\n"
            message += f"📊 Value: {value:.2f}\n"
            message += f"⚠️ Condition: {condition}\n"
            message += f"⏰ {datetime.now().strftime('%H:%M:%S')}"
            
            return await self.send_telegram_alert(chat_id, message)
            
        except Exception as e:
            print(f"Technical alert error: {e}")
            return False
    
    async def send_volatility_alert(self, chat_id, symbol, iv_rank, threshold):
        """Send implied volatility alert"""
        try:
            alert_key = f"volatility_{symbol}"
            if not self._should_send_alert(alert_key):
                return False
            
            status = "HIGH" if iv_rank > threshold else "LOW"
            emoji = "🔥" if status == "HIGH" else "❄️"
            
            message = f"{emoji} <b>Volatility Alert</b>\n\n"
            message += f"📊 <b>{symbol}</b>\n"
            message += f"📈 IV Rank: {iv_rank:.1f}%\n"
            message += f"🎯 Threshold: {threshold:.1f}%\n"
            message += f"⚠️ Status: {status} VOLATILITY\n"
            message += f"⏰ {datetime.now().strftime('%H:%M:%S')}"
            
            return await self.send_telegram_alert(chat_id, message)
            
        except Exception as e:
            print(f"Volatility alert error: {e}")
            return False
    
    async def send_greeks_alert(self, chat_id, symbol, greeks_data, alert_type):
        """Send portfolio Greeks alert"""
        try:
            alert_key = f"greeks_{symbol}_{alert_type}"
            if not self._should_send_alert(alert_key):
                return False
            
            message = f"🔤 <b>Greeks Alert</b>\n\n"
            message += f"📊 <b>{symbol} Portfolio</b>\n"
            message += f"Δ Delta: {greeks_data.get('total_delta', 0):.2f}\n"
            message += f"Γ Gamma: {greeks_data.get('total_gamma', 0):.4f}\n"
            message += f"Θ Theta: {greeks_data.get('total_theta', 0):.2f}\n"
            message += f"ν Vega: {greeks_data.get('total_vega', 0):.2f}\n"
            message += f"⚠️ Alert: {alert_type}\n"
            message += f"⏰ {datetime.now().strftime('%H:%M:%S')}"
            
            return await self.send_telegram_alert(chat_id, message)
            
        except Exception as e:
            print(f"Greeks alert error: {e}")
            return False
    
    def get_alert_history(self, limit=50):
        """Get recent alert history"""
        return self.alert_history[-limit:] if self.alert_history else []
    
    def clear_alert_history(self):
        """Clear alert history"""
        self.alert_history = []
        
    def set_cooldown_period(self, seconds):
        """Set alert cooldown period"""
        self.cooldown_period = seconds
    
    def create_custom_alert_template(self, template_name, template_content):
        """Create custom alert template"""
        try:
            # This would store custom templates for reuse
            templates_file = "alert_templates.json"
            
            try:
                with open(templates_file, 'r') as f:
                    templates = json.load(f)
            except FileNotFoundError:
                templates = {}
            
            templates[template_name] = template_content
            
            with open(templates_file, 'w') as f:
                json.dump(templates, f, indent=2)
                
            return True
            
        except Exception as e:
            print(f"Template creation error: {e}")
            return False
    
    async def send_custom_alert(self, chat_id, template_name, variables):
        """Send alert using custom template"""
        try:
            templates_file = "alert_templates.json"
            
            with open(templates_file, 'r') as f:
                templates = json.load(f)
            
            if template_name not in templates:
                return False
            
            message = templates[template_name]
            
            # Replace variables in template
            for key, value in variables.items():
                message = message.replace(f"{{{key}}}", str(value))
            
            return await self.send_telegram_alert(chat_id, message)
            
        except Exception as e:
            print(f"Custom alert error: {e}")
            return False
