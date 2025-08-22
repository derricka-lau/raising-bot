# Raising Order Management

## How to Use

1. **TWS (Trader Workstation)**
   - Download IBKR Trader Workstation (TWS) from [Interactive Brokers official site](https://www.interactivebrokers.com/en/index.php?f=16040).
   - Install and open TWS.
   - In TWS, go to **Edit > Global Configuration > API > Settings**.
   - Enable **"Enable ActiveX and Socket Clients"** and set the port (default is 7496 for live, 7497 for paper).
   - **Make sure "Read-Only API" is unchecked** so the bot can place orders.
   - Log in to your IBKR account and keep TWS running while using the bot.

2. **Download and Run**
   - Download the app zip from the [Releases page](https://github.com/derricka-lau/raising-bot/releases) Assets.
   - Open the `.exe` (Windows) or `.app` (macOS) file.
   - The browser should open to `localhost:9527` automatically.

3. **Configure**
   - Fill in your IBKR account details on the **CONFIG** tab.
   - If you don’t set up Telegram, you’ll need to manually paste signals in the **BOT CONSOLE**.

4. **BOT CONSOLE**
   - If Telegram has no signal, you can manually enter the untriggered signals.
   - The bot will show instructions and examples.

5. **How It Works**
   - The bot waits for market open with staged orders.
   - If SPX open price <= trigger price, it transmits staged orders. It then checks Telegram signals again at 9:32.
   - Any conflicting orders will be retried automatically until market close.
   - If you are not using Telegram and find a new signal after 9:31, please stop and rerun the bot, then enter the new signal.

---

## 中文簡介

1. **TWS（IBKR 交易工作站）**
   - 請先到 [IBKR 官方網站](https://www.interactivebrokers.com/en/index.php?f=16040) 下載並安裝 Trader Workstation (TWS)。
   - 開啟 TWS，並登入您的 IBKR 帳戶。
   - 在 TWS 中，前往 **Edit > Global Configuration > API > Settings**。
   - 勾選 **"Enable ActiveX and Socket Clients"**，並設定端口（預設 7496 為真實帳戶，7497 為模擬帳戶）。
   - **請確保「Read-Only API」沒有被勾選**，這樣機械人才能下單。
   - 請保持 TWS 開啟並登入狀態。
2. **下載及開啟**
   - 從 [Releases page](https://github.com/derricka-lau/raising-bot/releases) Assets 下載程式。
   - 開啟 `.exe`（Windows）或 `.app`（macOS）。
   - 瀏覽器會自動打開 `localhost:9527`。

2. **設定**
   - 在 **CONFIG** 頁填寫 IBKR 賬戶資料。
   - 如果你沒有設定 Telegram，則需要在 **BOT CONSOLE** 手動貼上訊號。

3. **BOT CONSOLE**
   - 當 Telegram 沒有訊號時，你可以手動輸入未觸發的訊號。
   - 機械人會顯示指示和範例。

4. **運作流程**
   - 機械人會在市場開市前等待並準備預設訂單。
   - 若 SPX 開市價<=觸發價，會傳送預設訂單，然後在 9:32 再檢查 Telegram 訊號。
   - 有撞腳的訂單會自動重試直到收市。
   - 如果你未使用 Telegram 並在 9:31 後發現新訊號，請停止並重新啟動機械人，然後輸入新訊號。

## macOS Security Warning

If you see a warning that "Apple could not verify 'RaisingBot' is free of malware":

1. Go to **System Settings > Privacy & Security**.
2. Scroll down to **Security**.
3. You should see a message about "RaisingBot" being blocked. Click **Open Anyway**.
4. Try opening the app again.

This will allow you to run the app even if it is not from the App Store.


## Developer Guide (Python)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/derricka-lau/raising-bot.git
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