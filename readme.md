# Raising Bot

Automated SPX Bull Spread Order Management for Interactive Brokers (IBKR)

---

## Features

- Manual entry of SPX bull spread trading signals
- Stages combo orders in IBKR Trader Workstation (TWS)
- Waits for US market open (skips weekends)
- **Lets you choose to check at today's or next trading day's open**
- Fetches SPX open price and transmits orders only if conditions are favorable
- Prevents duplicate signals and manages orders automatically

---

## Requirements

- **Python 3.8+** (recommended: Python 3.10 or newer)
- **IBKR Trader Workstation (TWS)** running and API enabled
- All Python dependencies listed in `requirements.txt`

---

## Installation

1. **Clone the repository:**
   ```sh
   git clone https://github.com/derricka-lau/raising-bot.git
   cd raising-bot
   ```

2. **(Optional) Create and activate a virtual environment:**
   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```sh
   python3 -m pip install -r requirements.txt
   ```

4. **Configure your settings:**
   - Copy `config_example.py` to `config.py`
   - Fill in your IBKR account and other settings in `config.py`
   - **Never share your `config.py`!** (It is ignored by git for your safety.)

---

## Configuration (`config.py`)

Your `config.py` file contains all the sensitive and user-specific settings for the bot.  
**This file is ignored by git for your safety.**

**Typical fields in `config.py`:**
```python
IBKR_HOST = '127.0.0.1'          # TWS API host (usually localhost)
IBKR_PORT = 7496                 # TWS API port (default: 7496 for live, 7497 for paper)
IBKR_CLIENT_ID = 144             # Unique integer for your API session (any number, must be unique per script)
UNDERLYING_SYMBOL = "SPX"        # The underlying index symbol
IBKR_ACCOUNT = "U5345336"        # Your IBKR account number (find in TWS)
```
- **IBKR_HOST/PORT:** Where your TWS API is running.
- **IBKR_CLIENT_ID:** Any integer; must be unique if running multiple bots.
- **UNDERLYING_SYMBOL:** Usually "SPX" for S&P 500 index options.
- **IBKR_ACCOUNT:** Your actual IBKR account number.

---

## IBKR TWS Setup

To allow your bot to place orders, you must configure TWS:

1. **Enable API Access:**
   - In TWS, go to `File > Global Configuration > API > Settings`.
   - Check **"Enable ActiveX and Socket Clients"**.
   - Uncheck **"Read-Only API"** (so your bot can place orders).
   - Optionally, set trusted IPs if you want extra security.

2. **Precautionary Settings (Risk Checks):**
    - In TWS, go to `File > Global Configuration > API > Precautions`, Check **"Bypass Precautions for API Orders"**.

---

## Usage

1.  **Start IBKR TWS and enable API access.** (Ensure settings are correct as per the "IBKR TWS Setup" section).

2.  **Run the bot from your terminal.** You can specify whether to check at today's open or the next trading day's open using a command-line argument.

    *   **To schedule for the *today* trading day's open (default behavior):**
        ```sh
        python3 main.py
        ```

    *   **To schedule for *next's* open:**
        ```sh
        python3 main.py --check-day next
        ```

3.  **Enter Signals:**
    When prompted, paste your trading signals into the terminal. The bot will parse them, check for duplicates against existing orders in TWS, and stage new orders for review.

4.  **Wait for Market Open:**
    The bot will wait until 9:30 AM US/Eastern on the selected day, then perform the GO/NO-GO check and either transmit or cancel the staged orders automatically.

---

## How It Works

- The bot lets you choose to check at **today's** or the **next trading day's** US market open (skipping weekends).
- It fetches the SPX open price at 9:30 AM US/Eastern on the selected day.
- If the open price is favorable, staged orders are transmitted to IBKR.

---

## Troubleshooting

- **Missing dependencies:** Run `python3 -m pip install -r requirements.txt`
- **IBKR API errors:** Ensure TWS is running and API is enabled.
- **Order not transmitted:** Check TWS risk settings and ensure your account is specified in `config.py`.

---

## Security

- Your sensitive settings (account numbers, API keys) are stored in `config.py`, which is **ignored by git**.
- Always keep your credentials private.

---

## Contributing

Pull requests and suggestions are welcome!  
Please fork the repo and submit your changes.

---

## License

MIT License

---

## Optional: Telegram Signal Integration

You can configure the bot to automatically fetch trading signals from a Telegram channel.

### Setup Steps

1. **Create a Telegram API Application:**
   - Go to [my.telegram.org](https://my.telegram.org).
   - Log in and click **API Development Tools**.
   - Create a new application and note your `api_id` and `api_hash`.

2. **Install Telethon:**
   ```sh
   python3 -m pip install telethon
   ```

3. **Configure Telegram in `config.py`:**
   Add these fields to your `config.py`:
   ```python
   TELEGRAM_API_ID = 1234567           # Your Telegram API ID (integer)
   TELEGRAM_API_HASH = "your_api_hash" # Your Telegram API hash (string)
   TELEGRAM_CHANNEL = "your_channel"   # Channel username or ID (e.g. "@mychannel")
   ```
   - If you do not wish to use Telegram, leave these fields blank or set `TELEGRAM_API_ID = "YOUR_API_ID"`.

4. **How It Works:**
   - If Telegram is configured, the bot will attempt to fetch the latest signal from your channel.
   - If Telegram is not configured or times out, you can enter signals manually.

---

> **Tip:** Telegram integration is not required. If you skip this setup, the bot will prompt you for signals manually.
