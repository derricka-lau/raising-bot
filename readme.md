# Raising Order Management

## How to Use

**EN:**

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
   - **Note:** When you enter a signal, the bot will automatically adjust the expiry date to the most recent valid US trading day if the expiry date you provide is a holiday or non-trading day.

5. **How It Works**
   - The bot stages all orders before market open, checking for duplicates against existing TWS orders and current session orders.
   - At market open, it fetches the official SPX open price.
   - If the SPX open price is **less than or equal to the trigger price**, staged orders are transmitted; otherwise, they are cancelled.
   - At 9:32 AM, the bot checks for new signals from Telegram and stages any additional valid orders.
   - **If you are not using Telegram and receive a new signal after 9:31, please stop and restart the bot, then enter the new signal manually.**
   - After open, the bot continuously monitors for errors and failed signals:
     - **Error orders** (e.g., conflicting strikes or rejected orders) are automatically retried when market conditions are met.
     - **Failed signals** (e.g., missing contract IDs, no strike price, or other issues) are retried, including logic to adjust strikes (+5/-5) if needed.
       **Note:** Adjusting strikes (+5/-5) will not affect the trigger price; the trigger price always uses the original LC/SC strikes from the signal.
     - Retries for both error orders and failed signals are triggered when the SPX price reaches or exceeds the LC strike.
     - All retries include duplicate checks to prevent submitting the same order twice.
     - The bot loops every second, ensuring orders are submitted as soon as conditions are met, until market close.

**中文:**  

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

3. **設定**
   - 在 **CONFIG** 頁填寫 IBKR 賬戶資料。
   - 如果你沒有設定 Telegram，則需要在 **BOT CONSOLE** 手動貼上訊號。

4. **BOT CONSOLE**
   - 當 Telegram 沒有訊號時，你可以手動輸入未觸發的訊號。
   - 機械人會顯示指示和範例。
   - **注意：** 當你輸入訊號後，如果你提供的到期日是假期或非交易日，機械人會自動將到期日調整為最近的有效美國交易日。

5. **運作流程**
   - 機械人會在市場開市前預先準備所有訂單，並檢查是否有重複（包括 TWS 已存在訂單和本次會話訂單）。
   - 開市時，機械人會獲取 SPX 官方開市價。
   - 如果 SPX 開市價 **小於或等於觸發價**，預設訂單會自動傳送；否則會取消。
   - 9:32 AM 時，機械人會檢查 Telegram 新訊號並補充任何有效新訂單。
   - **如果你沒有使用 Telegram，並在 9:31 之後收到新訊號，請停止並重新啟動機械人，然後手動輸入新訊號。**
   - 開市後，機械人會持續監控錯誤訂單和失敗訊號：
     - **錯誤訂單**（如撞腳、被拒絕等）會在市場條件符合時自動重試。
     - **失敗訊號**（如找不到合約 ID 或沒有行使價）會自動重試，並包含行使價調整邏輯（LC -5、SC +5）。
       **注意：** 行使價調整（LC -5、SC +5）不會影響觸發價，觸發價始終以原始訊號的 LC/SC 行使價計算。
     - 錯誤訂單和失敗訊號的重試，都是在 SPX 價格達到或超過 LC 行使價時觸發。
     - 所有重試都會再次檢查是否有重複訂單，避免重複下單。
     - 機械人每秒循環一次，確保只要條件達成就會即時下單，直到收市為止。
---

## Signal Deduplication & Retry Logic / 訊號去重及重試邏輯

**EN:**  
- The bot automatically counts how many times each unique signal (same expiry, LC strike, SC strike, trigger price) appears in the input (API, Telegram, manual).
- Each signal is assigned an `allowed_duplicates` value based on this count.
- Before placing any order (including retries), the bot checks all existing and managed orders for duplicates and only allows up to the permitted number for each signal.
- All error and failed signal retries also use this duplicate check, ensuring no order is ever placed more than the allowed limit.
- This logic applies to initial staging, 9:32 signal checks, error order retries, and failed conid retries.

**中文:**  
- 機械人會自動統計每個唯一訊號（到期日、LC行使價、SC行使價、觸發價相同）在輸入（API、Telegram、手動）中出現的次數。
- 每個訊號都會根據出現次數自動設定 `allowed_duplicates`（允許重複下單數）。
- 每次下單（包括重試）前，機械人都會檢查所有已存在和已管理的訂單，確保每個訊號的下單次數不超過允許的數量。
- 所有錯誤訂單和失敗訊號的重試也會用這個去重邏輯，確保不會超過允許的下單次數。
- 此邏輯適用於初始下單、9:32訊號檢查、錯誤訂單重試和合約ID失敗重試。

---

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