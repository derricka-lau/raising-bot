# config.py

# Configuration file for the IBKR application
IBKR_ACCOUNT = "YOUR_ACCOUNT_NUMBER"  # <-- Replace with your actual account number
IBKR_PORT = 7496 # 7496 for live trading, 7497 for paper trading

# --- Telegram Credentials (OPTIONAL - Tier 1) ---
TELEGRAM_API_ID = 'YOUR_API_ID'
TELEGRAM_API_HASH = 'YOUR_API_HASH'
TELEGRAM_CHANNEL = 'YOUR_CHANNEL_NAME'  # e.g., '@your_channel_name'

# --- Advanced Multi-Signal Regex ---
MULTI_SIGNAL_REGEX = r"到期日:\s*(\d{4}-\d{2}-\d{2})\s*SC:\s*([\d.]+)\s*LC:\s*([\d.]+)[^未觸發]*未觸發"
IBKR_HOST = '127.0.0.1'
IBKR_CLIENT_ID = 144 # Use a unique ID
UNDERLYING_SYMBOL = "SPX"

# --- Order Configuration ---
DEFAULT_ORDER_TYPE = "SNAP MID"
DEFAULT_LIMIT_PRICE = None
DEFAULT_STOP_PRICE = None
SNAPMID_OFFSET = 0.1