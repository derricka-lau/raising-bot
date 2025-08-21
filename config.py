# config.py

import json
import os
from pathlib import Path
import sys

# --- START: New code to find the correct config path ---
def get_user_data_dir():
    """Get a writable directory for user data (config, logs, session)."""
    if sys.platform == "win32":
        path = Path(os.getenv("APPDATA")) / "RaisingBot"
    else: # macOS and other Unix-like
        path = Path.home() / "Library" / "Application Support" / "RaisingBot"
    # The subprocess doesn't create the dir, it assumes the API server did.
    return str(path)

# Use the same logic as api.py to locate the config file
USER_DATA_DIR = get_user_data_dir()
CONFIG_FILE = os.path.join(USER_DATA_DIR, 'config.json')
# --- END: New code ---

CONFIG_DEFAULTS = {
    "IBKR_ACCOUNT": "",
    "IBKR_PORT": 7496,
    "TELEGRAM_API_ID": "",
    "TELEGRAM_API_HASH": "",
    "TELEGRAM_CHANNEL": "",
    "MULTI_SIGNAL_REGEX": r"到期日:\s*(\d{4}-\d{2}-\d{2})\s*SC:\s*([\d.]+)\s*LC:\s*([\d.]+)[^未觸發]*未觸發",
    "IBKR_HOST": '127.0.0.1',
    "IBKR_CLIENT_ID": 144,
    "UNDERLYING_SYMBOL": "SPX",
    "DEFAULT_ORDER_TYPE": "SNAP MID",
    "DEFAULT_LIMIT_PRICE": None,
    "DEFAULT_STOP_PRICE": None,
    "SNAPMID_OFFSET": 0.1
}

config_data = CONFIG_DEFAULTS.copy()
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'r') as f:
        try:
            config_data.update(json.load(f))
        except Exception:
            pass

IBKR_ACCOUNT = config_data.get("IBKR_ACCOUNT")
IBKR_PORT = int(config_data.get("IBKR_PORT"))
TELEGRAM_API_ID = config_data.get("TELEGRAM_API_ID")
TELEGRAM_API_HASH = config_data.get("TELEGRAM_API_HASH")
TELEGRAM_CHANNEL = config_data.get("TELEGRAM_CHANNEL")
MULTI_SIGNAL_REGEX = config_data.get("MULTI_SIGNAL_REGEX")
IBKR_HOST = config_data.get("IBKR_HOST")
IBKR_CLIENT_ID = int(config_data.get("IBKR_CLIENT_ID"))
UNDERLYING_SYMBOL = config_data.get("UNDERLYING_SYMBOL")
DEFAULT_ORDER_TYPE = config_data.get("DEFAULT_ORDER_TYPE")
SNAPMID_OFFSET = float(config_data.get("SNAPMID_OFFSET"))
DEFAULT_LIMIT_PRICE = float(config_data.get("DEFAULT_LIMIT_PRICE")) if config_data.get("DEFAULT_LIMIT_PRICE") not in (None, "", "None") else None
DEFAULT_STOP_PRICE = float(config_data.get("DEFAULT_STOP_PRICE")) if config_data.get("DEFAULT_STOP_PRICE") not in (None, "", "None") else None
