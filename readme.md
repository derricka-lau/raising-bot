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
   - The bot stages all orders before market open, checking for duplicates against existing TWS orders and current session orders.
   - At market open, it fetches the official SPX open price.
   - If the SPX open price is **less than or equal to the trigger price**, staged orders are transmitted; otherwise, they are cancelled.
   - At 9:32 AM, the bot checks for new signals (from Telegram or manual entry) and stages any additional valid orders.
   - After open, the bot continuously monitors for errors and failed signals:
     - **Error orders** (e.g., conflicting strikes or rejected orders) are automatically retried when market conditions are met.
     - **Failed signals** (e.g., missing contract IDs or strikes too far OTM) are retried, including logic to adjust strikes (+5/-5) if needed.
     - All retries include duplicate checks to prevent submitting the same order twice.
   - The bot loops every second, ensuring orders are submitted as soon as conditions are met, until market close.
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
   - 機械人會在市場開市前預先準備所有訂單，並檢查是否有重複（包括 TWS 已存在訂單和本次會話訂單）。
   - 開市時，機械人會獲取 SPX 官方開市價。
   - 如果 SPX 開市價 **小於或等於觸發價**，預設訂單會自動傳送；否則會取消。
   - 9:32 AM 時，機械人會再次檢查 Telegram 或手動輸入的新訊號，並補充任何有效新訂單。
   - 開市後，機械人會持續監控錯誤訂單和失敗訊號：
     - **錯誤訂單**（如撞腳、被拒絕等）會在市場條件符合時自動重試。
     - **失敗訊號**（如找不到合約 ID 或沒有行使價）會自動重試，並包含行使價調整邏輯（LC -5、SC +5）。
     - 所有重試都會再次檢查是否有重複訂單，避免重複下單。
   - 機械人每秒循環一次，確保只要條件達成就會即時下單，直到收市為止。
   - 如果你未使用 Telegram 並在 9:31 後發現新訊號，請停止並重新啟動機械人，然後輸入新訊號。

## macOS Security Warning

If you see a warning that "Apple could not verify 'xxx' is free of malware":

1. Go to **System Settings > Privacy & Security**.
2. Scroll down to **Security**.
3. You should see a message about "xxx" being blocked. Click **Open Anyway**.
4. You should expect this multiple times on the first run.
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