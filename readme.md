# Raising Bot

Raising Bot is a simple desktop application that helps automate trading strategies on Interactive Brokers (IBKR). It listens for trading signals from a Telegram channel (or manual input) and automatically places orders based on pre-set conditions.

## Features

-   **Simple Web Interface**: Configure and monitor the bot from your web browser.
-   **Automated order management**: Fetches signals and places orders automatically.
-   **Go/No-Go Logic**: Checks market conditions at open before transmitting orders.
-   **Prioritization**: Orders are automatically sorted to place the one with the lowest trigger price first.
-   **Automated Conflict Resolution**: If an order fails due to a conflict between strike prices in the provided signals, the bot actively monitors the market. It will automatically retry the failed order as soon as the live SPX price reaches the order's long call (LC) strike.
-   **Live Console**: See what the bot is doing in real-time.
-   **Cross-Platform**: Works on both macOS and Windows.


---

## Installation and Usage

Follow these simple steps to get the bot running.

### Step 1: Download the Application

1.  Go to the **[Releases Page](https://github.com/your-username/raising-bot/releases)** of this project.
2.  Download the correct file for your operating system:
    -   For **macOS**: `RaisingBot-macOS.zip`
    -   For **Windows**: `RaisingBot-Windows.zip`

### Step 2: Run the Application

**On macOS:**
1.  Unzip the downloaded file.
2.  Drag `RaisingBot.app` to your `Applications` folder.
3.  The first time you run it, you may need to **right-click** the app and select **Open**.
4.  A new tab will open in your web browser.

**On Windows:**
1.  Unzip the downloaded file.
2.  Open the new folder and double-click `RaisingBot.exe`.
3.  A new tab will open in your web browser.

### Step 3: Configure the Bot

1.  Before starting the bot, make sure **IBKR Trader Workstation (TWS) or Gateway** is running and you are logged in.
2.  In the browser window that opened, click on the **CONFIG** tab.
3.  Fill in the required fields:
    -   **IBKR Account Number**: Your account ID (e.g., `U1234567`).
    -   **IBKR Port**: The port TWS/Gateway is using. (Default is `7496` for live accounts, `7497` for paper accounts).
    -   **IBKR Client ID**: A random number (e.g., `144`) that is not being used by another API program.
4.  (Optional) If you want to get signals from Telegram, fill in the `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, and `TELEGRAM_CHANNEL`.
5.  Click **Save Config**.

### Step 4: Start the Bot

1.  Click on the **BOT CONSOLE** tab.
2.  Click the **START BOT** button.
3.  The console will show the bot's status. If Telegram is not configured, it will ask you to paste the signal text directly into the input box.
4.  To stop the bot at any time, click the **STOP BOT** button.

---

## For Developers

If you want to run the project from the source code:

**Prerequisites:**
-   Python 3.9+
-   Node.js 16+

**Setup:**
```bash
# 1. Clone the repository
git clone https://github.com/your-username/raising-bot.git
cd raising-bot

# 2. Set up the Python backend
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Set up the React frontend
cd raising-bot-web
npm install
npm run build
cd ..

# 4. Run the application
python api.py
```

**To build the executable:**
```bash
# Make sure you are in the activated virtual environment
pip install pyinstaller

# Build the app
pyinstaller RaisingBot.spec
```
The final application will be
