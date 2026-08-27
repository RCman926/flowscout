"""
Secure Configuration Loader
Loads API keys from environment variables (secure) or .env file
NEVER hardcode API keys in code or commit them to git
"""

import os
from typing import Optional, Dict
from pathlib import Path

# Try to load python-dotenv if available
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


def load_env_file():
    """Load .env files if they exist (project root + .streamlit for legacy keys)."""
    if not DOTENV_AVAILABLE:
        return False
    loaded = False
    # Prefer project root; then merge Streamlit-era keys without wiping root
    candidates = [
        Path('.env'),
        Path(__file__).resolve().parent / '.env',
        Path('.streamlit') / '.env',
        Path(__file__).resolve().parent / '.streamlit' / '.env',
    ]
    seen = set()
    for env_path in candidates:
        try:
            resolved = env_path.resolve()
        except Exception:
            resolved = env_path
        if resolved in seen:
            continue
        seen.add(resolved)
        if env_path.exists():
            # Root first with override; later files fill gaps only
            load_dotenv(env_path, override=(env_path.name == '.env' and '.streamlit' not in env_path.parts))
            loaded = True
    return loaded


def get_api_key(key_name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get API key from environment variable (secure method)
    
    Priority:
    1. Environment variable (set in system or .env file)
    2. Default value (if provided)
    3. None (fail gracefully)
    
    NEVER reads from api_config.json (security risk)
    """
    # Load .env file if available
    load_env_file()
    
    # Get from environment variable
    value = os.getenv(key_name, default)
    
    if not value:
        return None
    
    return value


def get_config() -> Dict[str, Optional[str]]:
    """
    Get all configuration values from environment variables
    Returns dict with all API keys and settings
    """
    load_env_file()
    
    return {
        # API Keys
        'finnhub_api_key': get_api_key('FINNHUB_API_KEY'),
        'iex_cloud_api_key': get_api_key('IEX_CLOUD_API_KEY'),
        'twelve_data_api_key': get_api_key('TWELVE_DATA_API_KEY'),
        'alpha_vantage_api_key': get_api_key('ALPHA_VANTAGE_API_KEY'),
        # Polygon.io API key (supports both POLYGON_API_KEY and MASSIVE_API_KEY)
        'polygon_api_key': get_api_key('POLYGON_API_KEY') or get_api_key('MASSIVE_API_KEY'),
        'massive_api_key': get_api_key('POLYGON_API_KEY') or get_api_key('MASSIVE_API_KEY'),  # Alias for backward compatibility
        'marketaux_api_key': get_api_key('MARKETAUX_API_KEY'),
        # StockData API (news + sentiment + real-time data)
        'stockdata_api_key': get_api_key('STOCKDATA_API_KEY'),
        
        # Reddit API (optional)
        'reddit_client_id': get_api_key('REDDIT_CLIENT_ID'),
        'reddit_secret': get_api_key('REDDIT_SECRET'),
        'reddit_user_agent': get_api_key('REDDIT_USER_AGENT', 'ShortSqueezeScanner/1.0'),
        
        # IBKR Settings
        'ibkr_host': get_api_key('IBKR_HOST', '127.0.0.1'),
        'ibkr_port': get_api_key('IBKR_PORT', '4001'),
        
        # App Settings
        'app_mode': get_api_key('APP_MODE', 'production'),
        'debug': get_api_key('DEBUG', 'False').lower() == 'true',
        
        # Telegram Notifications
        'telegram_bot_token': get_api_key('TELEGRAM_BOT_TOKEN'),
        'telegram_chat_id': get_api_key('TELEGRAM_CHAT_ID'),
    }


def check_required_keys() -> Dict[str, bool]:
    """
    Check which required API keys are configured
    Returns dict showing which keys are missing
    """
    config = get_config()
    
    return {
        'finnhub_configured': config['finnhub_api_key'] is not None,
        'polygon_configured': config['polygon_api_key'] is not None,
        'massive_configured': config['massive_api_key'] is not None,  # Alias for backward compatibility
        'reddit_configured': config['reddit_client_id'] is not None and config['reddit_secret'] is not None,
    }

