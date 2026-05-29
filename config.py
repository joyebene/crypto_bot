# Bybit API Credentials
BYBIT_API_KEY = "uhTpTxjRaxQ6lTnvHO"
BYBIT_API_SECRET = "pKJlmqdWDFUNcU6klQpKnC5ILnr8o8kHeau7"

# Telegram Bot Credentials
TELEGRAM_BOT_TOKEN = "8793872824:AAGUp4CdxbsZUaVWlyPKn8SUyPrMlfzIKfI"
TELEGRAM_CHAT_ID = "6885264991" # Optional: for sending to a specific chat/channel

# Trading settings
SETTINGS = {
    "symbols": [
        # Large Caps
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "SOLUSDT", "DOGEUSDT", "DOTUSDT", "MATICUSDT", "LTCUSDT",
        # Mid-Cap & Popular Altcoins
        "AVAXUSDT", "SHIBUSDT", "LINKUSDT", "UNIUSDT", "FTMUSDT", "AAVEUSDT", "XLMUSDT", "ALGOUSDT", "VETUSDT", "TRXUSDT",
        "EOSUSDT", "SANDUSDT", "MANAUSDT", "NEARUSDT", "ATOMUSDT", "ICPUSDT", "THETAUSDT", "FLOWUSDT", "KSMUSDT", "QNTUSDT",
        # Promising / High Potential
        "CROUSDT", "ZILUSDT", "HBARUSDT", "CELOUSDT", "ENJUSDT", "CHZUSDT", "RUNEUSDT", "LRCUSDT", "STXUSDT", "GRTUSDT",
        "SNXUSDT", "EGLDUSDT", "KAVAUSDT", "CFXUSDT", "1INCHUSDT", "FTTUSDT", "SXPUSDT", "ANKRUSDT", "ICONUSDT", "ARUSDT"
    ], # List of symbols to monitor
    "timeframe": "60",  # Timeframe in minutes (e.g., 60 for 1-hour)
    "rsi_period": 14,
    "ema_period": 200,
    "volume_threshold": 1000000,  # Example volume threshold
    "strategy": "breakout", # Default strategy
    "signal_throttle_minutes": 30 # Don't send a signal for the same coin if the last one was within X minutes
}