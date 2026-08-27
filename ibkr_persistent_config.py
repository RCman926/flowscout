"""
Persistent configuration for IBKR connection
Saves working connection parameters to avoid re-detection
"""

import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

CONFIG_FILE = "ibkr_persistent_config.json"

def load_ibkr_config() -> dict:
    """Load IBKR configuration from file"""
    default_config = {
        "host": "127.0.0.1",
        "port": 7497,
        "client_id": 1,
        "connected": False
    }
    
    if not os.path.exists(CONFIG_FILE):
        return default_config
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            # Merge with defaults to ensure all keys exist
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
            return config
    except Exception as e:
        logger.warning(f"Could not load IBKR config: {e}")
        return default_config

def save_ibkr_config(host: str, port: int, client_id: int, connected: bool = False, health_score: int = None):
    """Save IBKR configuration to file with optional health score"""
    try:
        config = {
            "host": host,
            "port": port,
            "client_id": client_id,
            "connected": connected,
            "last_updated": str(datetime.now())
        }
        if health_score is not None:
            config["health_score"] = health_score
            config["last_health_check"] = str(datetime.now())
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        logger.debug(f"Saved IBKR config: port={port}, client_id={client_id}, connected={connected}, health={health_score}")
    except Exception as e:
        logger.warning(f"Could not save IBKR config: {e}")

