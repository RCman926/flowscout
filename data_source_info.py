"""
Data Source Information and Diagnostics
Shows what data sources are available and being used
"""

from datetime import datetime
import yfinance as yf
import os

def get_data_source_info():
    """Get information about available data sources"""
    
    # Force reload .env file
    from config_loader import load_env_file
    load_env_file()
    
    info = {
        'timestamp': datetime.now().isoformat(),
        'sources': {},
        'priority_order': ['IBKR', 'Polygon', 'Finnhub', 'AlphaVantage', 'yfinance']
    }
    
    # Check yfinance
    try:
        from offline_mode import live_market_blocked

        yahoo_off = live_market_blocked()
    except Exception:
        yahoo_off = False
    if yahoo_off:
        info['sources']['yfinance'] = {
            'available': False,
            'status': 'OFFLINE',
            'note': 'Live Yahoo disabled — serving last-good snapshot as STALE (not live prints)'
        }
    else:
        try:
            ticker = yf.Ticker("SPY")
            exp_dates = ticker.options
            info['sources']['yfinance'] = {
                'available': True,
                'status': 'OK' if exp_dates else 'No data',
                'expirations_available': len(exp_dates) if exp_dates else 0,
                'note': 'Free but may have delays and rate limits'
            }
        except Exception as e:
            info['sources']['yfinance'] = {
                'available': False,
                'status': 'Error',
                'error': str(e),
                'note': 'May need cache cleared'
            }
    
    # Check IBKR
    try:
        from ibkr_client import get_ibkr_client
        ibkr = get_ibkr_client()
        if ibkr and ibkr.is_connected():
            # Check for delayed data warning (no subscription)
            has_delayed_only = False
            if hasattr(ibkr.wrapper, 'error_messages'):
                recent_errors = [e for e in ibkr.wrapper.error_messages[-5:] if e.get('code') == 10089]
                has_delayed_only = len(recent_errors) > 0
            
            if has_delayed_only:
                info['sources']['ibkr'] = {
                    'available': False,
                    'status': 'Connected but delayed data only',
                    'note': 'Market data subscription required ($1.50-$4.50/month). See IBKR_MARKET_DATA_SUBSCRIPTIONS.md'
                }
            else:
                info['sources']['ibkr'] = {
                    'available': True,
                    'status': 'Connected',
                    'note': 'Best quality - real-time data (requires market data subscriptions)'
                }
        else:
            info['sources']['ibkr'] = {
                'available': False,
                'status': 'Not connected',
                'note': 'Connect IBKR TWS/Gateway to use. See IB_GATEWAY_SETUP.md'
            }
    except Exception as e:
        info['sources']['ibkr'] = {
            'available': False,
            'status': 'Not available',
            'error': str(e),
            'note': 'IBKR client not configured'
        }
    
    # Check Polygon/Massive
    try:
        from config_loader import get_api_key
        polygon_key = get_api_key('POLYGON_API_KEY') or get_api_key('MASSIVE_API_KEY')
        
        # Also check api_config.json for backward compatibility
        api_key = polygon_key
        if not api_key:
            import json
            if os.path.exists('api_config.json'):
                with open('api_config.json', 'r') as f:
                    config = json.load(f)
                    api_key = config.get('massive_api_key') or config.get('polygon_api_key')
        
        if api_key and api_key not in ['your_key_here', 'your_polygon_key_here', '']:
            # Test if SDK is available
            try:
                from polygon import RESTClient
                info['sources']['polygon'] = {
                    'available': True,
                    'status': 'Ready (API key + SDK)',
                    'note': 'Professional data source - will be used if IBKR unavailable'
                }
            except ImportError:
                info['sources']['polygon'] = {
                    'available': False,
                    'status': 'API key found but SDK missing',
                    'note': 'Install: pip install polygon-api-client'
                }
        else:
            info['sources']['polygon'] = {
                'available': False,
                'status': 'No API key',
                'note': 'Add POLYGON_API_KEY or MASSIVE_API_KEY to .env file'
            }
    except Exception as e:
        info['sources']['polygon'] = {
            'available': False,
            'status': 'Error',
            'error': str(e)
        }
    
    # Check Finnhub
    try:
        from config_loader import get_api_key
        finnhub_key = get_api_key('FINNHUB_API_KEY')
        if finnhub_key and finnhub_key not in ['your_finnhub_key_here', 'your_key_here', '']:
            info['sources']['finnhub'] = {
                'available': True,
                'status': 'API key configured',
                'note': 'Note: Free tier has limited options data'
            }
        else:
            info['sources']['finnhub'] = {
                'available': False,
                'status': 'No API key',
                'note': 'Add FINNHUB_API_KEY to .env file'
            }
    except Exception as e:
        info['sources']['finnhub'] = {
            'available': False,
            'status': 'Not configured',
            'error': str(e)
        }
    
    # Check Alpha Vantage
    try:
        from config_loader import get_api_key
        av_key = get_api_key('ALPHA_VANTAGE_API_KEY')
        if av_key and av_key not in ['your_key_here', 'your_alpha_vantage_key_here', '']:
            info['sources']['alphavantage'] = {
                'available': True,
                'status': 'API key configured',
                'note': 'Note: Free tier has limited options data'
            }
        else:
            info['sources']['alphavantage'] = {
                'available': False,
                'status': 'No API key',
                'note': 'Add ALPHA_VANTAGE_API_KEY to .env file'
            }
    except Exception as e:
        info['sources']['alphavantage'] = {
            'available': False,
            'status': 'Not configured',
            'error': str(e)
        }
    
    return info

def clear_yfinance_cache():
    """Clear yfinance cache to fix corruption issues"""
    try:
        import shutil
        cache_dir = os.path.join(os.path.expanduser('~'), '.cache', 'yfinance')
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir, ignore_errors=True)
            return True, "Cache cleared successfully"
        else:
            return True, "No cache directory found (already clean)"
    except Exception as e:
        return False, f"Error clearing cache: {str(e)}"

