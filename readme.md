# Raising Order Management

Raising Order Management is a simple desktop application that helps automate trading strategies on Interactive Brokers (IBKR). It listens for trading signals from a Telegram channel (or manual input) and automatically places orders based on pre-set conditions.

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

## How to Use

1. **Download and Run**
   - Download the zip from the [Releases page](https://github.com/your-username/raising-bot/releases).
   - Open the `.exe` (Windows) or `.app` (macOS) file.
   - The browser should open to `localhost:9527` automatically.

2. **Configure**
   - Fill in your IBKR account details on the **CONFIG** tab.
   - If you don’t set up Telegram, you’ll need to manually paste signals in the **BOT CONSOLE**.

3. **Bot Console**
   - If Telegram has no signal, you can manually enter the signal.
   - The bot will show instructions and examples.

4. **How It Works**
   - The bot waits for market open.
   - If SPX open price > trigger price, it checks Telegram signals again at 9:32.
   - Any conflicting orders will be retried automatically until market close.
   - If you are not using Telegram and find a new signal after 9:31, please stop and rerun the bot, then enter the new signal.

---

## 中文簡介

1. **下載及開啟**
   - 從 [Releases page](https://github.com/your-username/raising-bot/releases) 下載程式。
   - 開啟 `.exe`（Windows）或 `.app`（macOS）。
   - 瀏覽器會自動打開 `localhost:9527`。

2. **設定**
   - 在 **CONFIG** 頁填寫 IBKR 賬戶資料。
   - 沒有 Telegram 訊號時，可在 **BOT CONSOLE** 手動輸入訊號。

3. **操作流程**
   - 市場開市前等待。
   - 若 SPX 開市價高於觸發價，會在 9:32 再檢查 Telegram 訊號。
   - 有衝突的訂單會自動重試直到收市。
   - 若你未使用 Telegram 並在 9:31 後發現新訊號，請停止並重新啟動機械人，然後輸入新訊號。

---

## Developer Guide (Python)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/raising-bot.git
   cd raising-bot/raising-bot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the backend server:**
   ```bash
   python api.py
   ```

4. **Run the frontend (development mode):**
   ```bash
   cd raising-bot-web
   npm install
   npm run dev
   ```

5. **Build the executable (optional):**
   ```bash
   pyinstaller RaisingBot.spec
   ```

6. **Modify code as needed and restart the server to see changes.**
