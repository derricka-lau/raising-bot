# config.py

# --- User Configuration ---
IBKR_HOST = '127.0.0.1'
IBKR_PORT = 7496
IBKR_CLIENT_ID = 144 # Use a unique ID
IBKR_ACCOUNT = "YOUR_ACCOUNT_NUMBER"  # <-- Replace with your actual account number

# --- Trade Defaults ---
UNDERLYING_SYMBOL = "SPX"

# --- Order Configuration ---
DEFAULT_ORDER_TYPE = "SNAP MID"
DEFAULT_LIMIT_PRICE = None
DEFAULT_STOP_PRICE = None
SNAPMID_OFFSET = 0.5  # Default offset for SNAP MID orders

# # --- Telegram Credentials (OPTIONAL - Tier 1) ---
# TELEGRAM_API_ID = 'YOUR_API_ID'
# TELEGRAM_API_HASH = 'YOUR_API_HASH'
# TELEGRAM_CHANNEL = '@RaisingCycle_Notification_bot'

# # --- CSV Configuration (OPTIONAL - Tier 2) ---
# CSV_FILE_PATH = 'QuantRaiser Raising Cycle.csv'
# CSV_COLUMN_MAPPING = {
#     "expiry": "完結日期", "lc_strike": "開始價格", "sc_strike": "觸發點", "trigger_price": "觸發點"
# }
# CSV_STATUS_COLUMN = "狀態"
# CSV_PENDING_VALUE = "PENDING"

# --- Advanced Multi-Signal Regex ---
MULTI_SIGNAL_REGEX = r"到期日:\s*(\d{4}-\d{2}-\d{2})\s*SC:\s*([\d.]+)\s*LC:\s*([\d.]+)[^未觸發]*未觸發"
