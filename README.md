## 📖 Overview
This is a Python-based **Binance Futures Trading Bot** designed for the **Binance USDT-M Futures Testnet**.  
It supports **market orders, limit orders, stop-limit orders**, and advanced validation to ensure orders comply with Binance exchange rules.  
The bot comes with:

- **Command-Line Interface (CLI)** for manual trading
- **Validation layer** for price, quantity, symbol, and filters
- **Comprehensive logging** (trade, error, API calls)
- **Extensible architecture** for adding advanced order types and strategies
- **Test suite** (Pytest) for functionality verification


## 🚀 Features
- ✅ Connect to Binance Testnet using API keys
- ✅ Retrieve account balances
- ✅ Place **Market Orders** (Buy/Sell)
- ✅ Place **Limit Orders** with price validation
- ✅ Place **Stop-Limit Orders** with exchange rule enforcement
- ✅ Cancel single or all orders
- ✅ Interactive CLI mode
- ✅ Detailed logging — trades, API calls, errors
- ✅ Supports `.env` secure config for credentials
- ✅ Test suite with unit & integration tests


## 📂 Project Structure

crypto_trading_bot/
│
├── bot/
│   ├── basic_bot.py           # Core bot logic and API interactions
│   ├── cli.py                 # Command-line interface for trading
│   ├── orders.py              # OrderManager (stop-limit, cancel, etc)
│   ├── price_validator.py     # Price validation rules
│   ├── dataclasses.py         # Data models for orders/trades
│   ├── logger.py              # Logging configuration
│   ├── utils.py               # Helper functions
│   └── config.py              # Config constants and classes
│
├── logs/
│   ├── api.log, system.log, trades.log, errors.log, ...
│
├── test/
│   ├── test_trading_bot.py, test_stop_limit_orders.py, ...
│   ├── run_stop_limit_tests.py
│
├── .env                       # API keys and project config (never share publicly)
├── config.json                # Project or task configuration
├── README.md                  # Main documentation
├── requirements.txt           # Python dependencies
└── venv/                      # Python virtual environment


## 🛠 Requirements

- Python **3.8+**
- Binance Testnet account & API keys  
  (Create at: [https://testnet.binancefuture.com/en/futures/USDM](https://testnet.binancefuture.com/en/futures/USDM))
- Installed dependencies (see below)

## 📥 Installation

### 1️⃣ Clone the Repository
git clone https://github.com/your-username/crypto_trading_bot.git
cd crypto_trading_bot


### 2️⃣ Create & Activate Virtual Environment
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

### 3️⃣ Install Dependencies
pip install -r requirements.txt

## 🔑 Environment Configuration

Edit `.env` and add your Binance Testnet API credentials:
BINANCE_API_KEY=your_testnet_api_key
BINANCE_SECRET_KEY=your_testnet_secret
BINANCE_TESTNET=true

# Optional logging config
LOG_LEVEL=INFO
LOG_COLORED_OUTPUT=true

⚠ **Security Note:** Never commit your `.env` file to GitHub or share it publicly.

## 💻 CLI Usage

Run the CLI using:
python -m bot.cli  [options]

### Commands

#### **1. Show Account Balance**
python -m bot.cli account

Example output:
=== Account Balance ===
USDT Available: 14500.50
USDT Total: 15000.00
=======================

#### **2. Place Market Order**
python -m bot.cli market --symbol BTCUSDT --side BUY --quantity 0.001

#### **3. Place Limit Order**
python -m bot.cli limit --symbol BTCUSDT --side SELL --quantity 0.001 --price 122000
✔ Validated to avoid incorrect pricing vs. current market.

#### **4. Place Stop-Limit Order**
python -m bot.cli stop-limit --symbol BTCUSDT --side SELL --quantity 0.001 --price 122000 --stop-price 121800
⚠ Notional must be ≥ 100 USDT unless `reduceOnly` is set.

#### **5. Cancel Order**
python -m bot.cli cancel --symbol BTCUSDT --order-id 12345678

#### **6. Interactive Mode**
python -m bot.cli interactive
Enters a shell-like interface for quicker test trading.

## 🧪 Testing

Run **all tests**:
pytest -v

Run **only stop-limit tests**:
python run_stop_limit_tests.py

## 🗂 Logging

Logs are stored in the `/logs` directory:
- **system.log** — general system messages
- **trades.log** — trade execution records
- **errors.log** — errors & exceptions
- **api.log** — API requests/responses

## ⚠️ Notes & Best Practices

- This bot **only works on Binance Futures Testnet** unless you change `BINANCE_TESTNET=false`.
- Always test strategies with **small quantities** first.
- Use `PriceValidator` to avoid rejected orders.
- Keep your `.env` secure.
- Respect Binance **rate limits** to avoid bans.

## 📌 Future Improvements
- 💡 Add OCO order support via CLI
- 💡 Implement TWAP/Grid trading strategy
- 💡 Web dashboard for monitoring
- 💡 Telegram/Discord notifications

## 📜 License
This project is for **educational and testing purposes only** on Binance Testnet.  
Trading in real markets involves significant risk.

