import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re

def format_currency(amount, symbol="$", precision=2):
    """Format number as currency"""
    try:
        if abs(amount) >= 1e9:
            return f"{symbol}{amount/1e9:.1f}B"
        elif abs(amount) >= 1e6:
            return f"{symbol}{amount/1e6:.1f}M"
        elif abs(amount) >= 1e3:
            return f"{symbol}{amount/1e3:.1f}K"
        else:
            return f"{symbol}{amount:.{precision}f}"
    except:
        return f"{symbol}0.00"

def format_percentage(value, precision=2):
    """Format number as percentage"""
    try:
        return f"{value:.{precision}f}%"
    except:
        return "0.00%"

def format_large_number(number):
    """Format large numbers with K, M, B suffixes"""
    try:
        if abs(number) >= 1e9:
            return f"{number/1e9:.2f}B"
        elif abs(number) >= 1e6:
            return f"{number/1e6:.2f}M"
        elif abs(number) >= 1e3:
            return f"{number/1e3:.2f}K"
        else:
            return f"{number:,.0f}"
    except:
        return "0"

def calculate_time_to_expiry(expiry_date):
    """Calculate time to expiry in days and years"""
    try:
        if isinstance(expiry_date, str):
            expiry = datetime.strptime(expiry_date, '%Y-%m-%d')
        else:
            expiry = expiry_date
            
        now = datetime.now()
        time_diff = expiry - now
        
        days = time_diff.days
        years = days / 365.25
        
        return {
            'days': days,
            'years': years,
            'business_days': calculate_business_days(now, expiry)
        }
    except:
        return {'days': 0, 'years': 0, 'business_days': 0}

def calculate_business_days(start_date, end_date):
    """Calculate number of business days between two dates"""
    try:
        return pd.bdate_range(start_date, end_date).shape[0] - 1
    except:
        return 0

def validate_symbol(symbol):
    """Validate stock symbol format"""
    try:
        # Basic validation - letters only, 1-5 characters
        pattern = r'^[A-Z]{1,5}$'
        return bool(re.match(pattern, symbol.upper()))
    except:
        return False

def calculate_portfolio_metrics(positions):
    """Calculate portfolio-level metrics"""
    try:
        if not positions:
            return {}
            
        total_value = sum(pos.get('market_value', 0) for pos in positions)
        total_pnl = sum(pos.get('unrealized_pnl', 0) for pos in positions)
        
        # Calculate beta-weighted portfolio metrics
        weighted_delta = sum(pos.get('delta', 0) * pos.get('market_value', 0) for pos in positions) / total_value if total_value > 0 else 0
        
        return {
            'total_value': total_value,
            'total_pnl': total_pnl,
            'pnl_percentage': (total_pnl / total_value) * 100 if total_value > 0 else 0,
            'weighted_delta': weighted_delta,
            'position_count': len(positions)
        }
    except:
        return {}

def calculate_option_moneyness(spot_price, strike_price):
    """Calculate option moneyness"""
    try:
        moneyness = spot_price / strike_price
        
        if moneyness > 1.05:
            return "Deep ITM" if moneyness > 1.2 else "ITM"
        elif moneyness < 0.95:
            return "Deep OTM" if moneyness < 0.8 else "OTM"
        else:
            return "ATM"
    except:
        return "Unknown"

def get_next_expiry_friday():
    """Get next options expiry Friday"""
    try:
        today = datetime.now().date()
        days_until_friday = (4 - today.weekday()) % 7
        if days_until_friday == 0:  # Today is Friday
            days_until_friday = 7
        
        next_friday = today + timedelta(days=days_until_friday)
        
        # Check if it's the third Friday of the month
        third_friday = get_third_friday_of_month(next_friday.year, next_friday.month)
        
        if next_friday == third_friday:
            return next_friday.strftime('%Y-%m-%d')
        else:
            # Find next third Friday
            if next_friday < third_friday:
                return third_friday.strftime('%Y-%m-%d')
            else:
                # Next month
                next_month = next_friday.month + 1 if next_friday.month < 12 else 1
                next_year = next_friday.year if next_friday.month < 12 else next_friday.year + 1
                return get_third_friday_of_month(next_year, next_month).strftime('%Y-%m-%d')
    except:
        return (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')

def get_third_friday_of_month(year, month):
    """Get third Friday of given month"""
    try:
        # Find first day of month
        first_day = datetime(year, month, 1)
        
        # Find first Friday
        days_to_friday = (4 - first_day.weekday()) % 7
        first_friday = first_day + timedelta(days=days_to_friday)
        
        # Third Friday is 14 days after first Friday
        third_friday = first_friday + timedelta(days=14)
        
        return third_friday.date()
    except:
        return datetime.now().date()

def calculate_implied_move(price, iv, days_to_expiry):
    """Calculate expected price move based on implied volatility"""
    try:
        time_sqrt = np.sqrt(days_to_expiry / 365)
        implied_move = price * iv * time_sqrt
        
        return {
            'dollar_move': implied_move,
            'percentage_move': (implied_move / price) * 100,
            'upper_bound': price + implied_move,
            'lower_bound': price - implied_move
        }
    except:
        return {'dollar_move': 0, 'percentage_move': 0, 'upper_bound': price, 'lower_bound': price}

def get_market_hours_info():
    """Get market hours information"""
    try:
        now = datetime.now()
        
        # Regular market hours: 9:30 AM - 4:00 PM EST
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        # Pre-market: 4:00 AM - 9:30 AM EST
        premarket_open = now.replace(hour=4, minute=0, second=0, microsecond=0)
        
        # After-hours: 4:00 PM - 8:00 PM EST
        afterhours_close = now.replace(hour=20, minute=0, second=0, microsecond=0)
        
        is_weekend = now.weekday() >= 5
        is_market_hours = market_open <= now <= market_close and not is_weekend
        is_premarket = premarket_open <= now < market_open and not is_weekend
        is_afterhours = market_close < now <= afterhours_close and not is_weekend
        
        return {
            'is_market_hours': is_market_hours,
            'is_premarket': is_premarket,
            'is_afterhours': is_afterhours,
            'is_weekend': is_weekend,
            'market_open': market_open,
            'market_close': market_close,
            'time_to_open': (market_open - now).total_seconds() if now < market_open else 0,
            'time_to_close': (market_close - now).total_seconds() if now < market_close else 0
        }
    except:
        return {}

def sanitize_input(input_string):
    """Sanitize user input to prevent injection attacks"""
    try:
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\';\\]', '', str(input_string))
        # Limit length
        return sanitized[:100]
    except:
        return ""

def validate_chat_id(chat_id):
    """Validate Telegram chat ID format"""
    try:
        # Chat IDs are typically integers or strings starting with @
        if isinstance(chat_id, int):
            return abs(chat_id) > 0
        elif isinstance(chat_id, str):
            return chat_id.startswith('@') or chat_id.lstrip('-').isdigit()
        return False
    except:
        return False

def calculate_risk_metrics(positions):
    """Calculate portfolio risk metrics"""
    try:
        if not positions:
            return {}
        
        # Portfolio delta
        total_delta = sum(pos.get('delta', 0) * pos.get('quantity', 0) for pos in positions)
        
        # Portfolio gamma
        total_gamma = sum(pos.get('gamma', 0) * pos.get('quantity', 0) for pos in positions)
        
        # Portfolio theta
        total_theta = sum(pos.get('theta', 0) * pos.get('quantity', 0) for pos in positions)
        
        # Portfolio vega
        total_vega = sum(pos.get('vega', 0) * pos.get('quantity', 0) for pos in positions)
        
        # Maximum loss calculation (simplified)
        max_loss = sum(pos.get('premium_paid', 0) for pos in positions if pos.get('quantity', 0) > 0)
        
        return {
            'portfolio_delta': total_delta,
            'portfolio_gamma': total_gamma,
            'portfolio_theta': total_theta,
            'portfolio_vega': total_vega,
            'max_potential_loss': max_loss,
            'delta_neutral': abs(total_delta) < 0.1,
            'gamma_exposure': 'high' if abs(total_gamma) > 0.1 else 'moderate' if abs(total_gamma) > 0.05 else 'low'
        }
    except Exception as e:
        print(f"Risk metrics calculation error: {e}")
        return {}

def format_option_symbol(symbol, expiry, strike, option_type):
    """Format option symbol for display"""
    try:
        exp_date = datetime.strptime(expiry, '%Y-%m-%d')
        exp_str = exp_date.strftime('%m%d%y')
        strike_str = f"{int(strike*1000):08d}"
        type_char = 'C' if option_type.upper() == 'CALL' else 'P'
        
        return f"{symbol}{exp_str}{type_char}{strike_str}"
    except:
        return f"{symbol}_{expiry}_{strike}_{option_type}"
