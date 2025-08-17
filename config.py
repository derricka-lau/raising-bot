# config.py

import json
import os

CONFIG_FILE = 'config.json'
CONFIG_DEFAULTS = {
    "IBKR_ACCOUNT": "YOUR_ACCOUNT_NUMBER",
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
TELEGRAM_API_ID = int(config_data.get("TELEGRAM_API_ID"))
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
