import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import requests
import warnings
warnings.filterwarnings('ignore')

class FinancialCalendar:
    def __init__(self):
        self.cache = {}
        self.cache_duration = 3600  # 1 hour cache
        
    def _is_cache_valid(self, key):
        if key not in self.cache:
            return False
        return (datetime.now() - self.cache[key]['timestamp']).seconds < self.cache_duration
    
    def get_earnings_calendar(self, symbol):
        """Get earnings dates for a symbol"""
        cache_key = f"earnings_{symbol}"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
            
        try:
            ticker = yf.Ticker(symbol)
            earnings_data = {}
            
            # Try to get earnings calendar
            try:
                calendar = ticker.calendar
                if calendar is not None and hasattr(calendar, 'index') and len(calendar.index) > 0:
                    next_date = calendar.index[0]
                    earnings_data = {
                        'next_earnings': next_date.strftime('%Y-%m-%d'),
                        'days_until': (next_date.date() - datetime.now().date()).days,
                        'eps_estimate': calendar.iloc[0].get('EPS Estimate', 0) if len(calendar) > 0 else 0
                    }
                elif calendar is not None and hasattr(calendar, 'empty') and not calendar.empty:
                    # Handle DataFrame format
                    next_date = calendar.index[0]
                    earnings_data = {
                        'next_earnings': next_date.strftime('%Y-%m-%d'),
                        'days_until': (next_date.date() - datetime.now().date()).days,
                        'eps_estimate': float(calendar.iloc[0].get('EPS Estimate', 0)) if 'EPS Estimate' in calendar.columns else 0
                    }
            except:
                # Fallback to ticker info
                try:
                    info = ticker.info
                    if 'earningsDate' in info and info['earningsDate']:
                        earnings_date = info['earningsDate']
                        if isinstance(earnings_date, list) and len(earnings_date) > 0:
                            next_date = datetime.fromtimestamp(earnings_date[0])
                            earnings_data = {
                                'next_earnings': next_date.strftime('%Y-%m-%d'),
                                'days_until': (next_date.date() - datetime.now().date()).days,
                                'eps_estimate': info.get('forwardEps', 0)
                            }
                except:
                    pass
            
            self.cache[cache_key] = {
                'data': earnings_data,
                'timestamp': datetime.now()
            }
            return earnings_data
            
        except Exception as e:
            print(f"Earnings calendar error for {symbol}: {e}")
            return {}
    
    def get_fomc_dates(self):
        """Get upcoming FOMC meeting dates"""
        cache_key = "fomc_dates"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
            
        try:
            # FOMC meeting dates for 2024-2025 (manually maintained as they're scheduled)
            fomc_dates = [
                '2024-09-17/18',
                '2024-10-30/31', 
                '2024-12-17/18',
                '2025-01-28/29',
                '2025-03-18/19',
                '2025-04-29/30',
                '2025-06-10/11',
                '2025-07-29/30',
                '2025-09-16/17',
                '2025-10-28/29',
                '2025-12-16/17'
            ]
            
            upcoming_dates = []
            today = datetime.now().date()
            
            for date_range in fomc_dates:
                # Parse the end date of the meeting
                end_date_str = date_range.split('/')[1]
                try:
                    # Add year if not present
                    if len(end_date_str.split('-')) == 2:
                        year = date_range.split('-')[0]
                        end_date_str = f"{year}-{end_date_str}"
                    
                    meeting_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                    days_until = (meeting_date - today).days
                    
                    if days_until >= 0:  # Future or today
                        upcoming_dates.append({
                            'date': date_range,
                            'days_until': days_until,
                            'meeting_date': meeting_date
                        })
                except ValueError:
                    continue
            
            # Sort by date and take next 3
            upcoming_dates.sort(key=lambda x: x['days_until'])
            result = upcoming_dates[:3]
            
            self.cache[cache_key] = {
                'data': result,
                'timestamp': datetime.now()
            }
            return result
            
        except Exception as e:
            print(f"FOMC dates error: {e}")
            return []
    
    def get_economic_events(self):
        """Get major economic events this week"""
        cache_key = "econ_events"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
            
        try:
            # Key economic indicators and typical release schedules
            today = datetime.now()
            events = []
            
            # CPI (usually around 13th of month)
            for month_offset in range(3):
                target_month = today + timedelta(days=30*month_offset)
                cpi_date = target_month.replace(day=13)
                if cpi_date > today:
                    days_until = (cpi_date.date() - today.date()).days
                    if days_until <= 30:
                        events.append({
                            'event': 'CPI Release',
                            'date': cpi_date.strftime('%Y-%m-%d'),
                            'days_until': days_until,
                            'impact': 'HIGH'
                        })
                        break
            
            # NFP (first Friday of month)
            for month_offset in range(3):
                target_month = today + timedelta(days=30*month_offset)
                first_day = target_month.replace(day=1)
                # Find first Friday
                days_ahead = 4 - first_day.weekday()  # Friday is 4
                if days_ahead < 0:
                    days_ahead += 7
                nfp_date = first_day + timedelta(days=days_ahead)
                
                if nfp_date > today:
                    days_until = (nfp_date.date() - today.date()).days
                    if days_until <= 30:
                        events.append({
                            'event': 'Jobs Report (NFP)',
                            'date': nfp_date.strftime('%Y-%m-%d'),
                            'days_until': days_until,
                            'impact': 'HIGH'
                        })
                        break
            
            # Sort by days until
            events.sort(key=lambda x: x['days_until'])
            
            self.cache[cache_key] = {
                'data': events[:5],  # Top 5 upcoming events
                'timestamp': datetime.now()
            }
            return events[:5]
            
        except Exception as e:
            print(f"Economic events error: {e}")
            return []
    
    def get_options_expiration_dates(self):
        """Get upcoming options expiration dates"""
        try:
            today = datetime.now()
            expirations = []
            
            # Weekly expirations (every Friday)
            current_date = today
            for i in range(8):  # Next 8 weeks
                days_ahead = 4 - current_date.weekday()  # Friday is 4
                if days_ahead <= 0:
                    days_ahead += 7
                friday = current_date + timedelta(days=days_ahead)
                
                days_until = (friday.date() - today.date()).days
                exp_type = "Weekly"
                
                # Check if it's monthly (3rd Friday)
                if 15 <= friday.day <= 21:
                    exp_type = "Monthly"
                
                # Check if it's quarterly (March, June, September, December)
                if friday.month in [3, 6, 9, 12] and 15 <= friday.day <= 21:
                    exp_type = "Quarterly"
                
                expirations.append({
                    'date': friday.strftime('%Y-%m-%d'),
                    'days_until': days_until,
                    'type': exp_type,
                    'day_name': friday.strftime('%A')
                })
                
                current_date = friday + timedelta(days=1)
            
            return expirations[:6]  # Next 6 expiration dates
            
        except Exception as e:
            print(f"Options expiration error: {e}")
            return []