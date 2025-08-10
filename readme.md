# Raising Bot

Automated SPX Bull Spread Order Management for Interactive Brokers (IBKR)

---

## Features

- Manual entry of SPX bull spread trading signals
- Stages combo orders in IBKR Trader Workstation (TWS)
- Waits for next US market open (skips weekends)
- Checks SPX open price and transmits orders only if conditions are favorable
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
   python3 -m pip install -r requirements.txt --break-system-packages
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
   - 
   - Optionally, set trusted IPs if you want extra security.

2. **Precautionary Settings (Risk Checks):**
    - In TWS, go to `File > Global Configuration > API > Precautions`, Check **"Bypass Precautions for API Orders"**.

---

## Usage

1. **Start IBKR TWS and enable API access.**
2. **Run the bot:**
   ```sh
   python3 main.py
   ```
3. **Manual Signal Entry:**
   - When prompted, paste your multi-signal message in one line and press Enter.
   - The bot will parse your signals and stage orders for review.
   - Orders will be transmitted only if the market open price meets your criteria.

---

## How It Works

- The bot calculates the **next US trading day open** (skipping weekends).
- It fetches the SPX open price at 9:30 AM US/Eastern.
- If the open price is favorable, staged orders are transmitted to IBKR.
- Orders are managed and duplicate signals are ignored.

---

## Troubleshooting

- **Missing dependencies:** Run `python3 -m pip install -r requirements.txt --break-system-packages`
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