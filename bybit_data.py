import pandas as pd
from pybit.unified_trading import HTTP
import config
import time
import os
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import ConnectionError, Timeout, RequestException

# Use environment variables on Railway (recommended)
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY") or config.BYBIT_API_KEY
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET") or config.BYBIT_API_SECRET


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ConnectionError, Timeout, RequestException, Exception)),
    reraise=True
)
def get_bybit_data(symbol: str, timeframe: str, limit: int = 200):
    """Fetch kline with retries - optimized for Railway"""
    try:
        session = HTTP(
            api_key=BYBIT_API_KEY,
            api_secret=BYBIT_API_SECRET,
            testnet=False,
            base_url="https://api.bytick.com"   # More stable alternative
        )

        response = session.get_kline(
            category="linear",
            symbol=symbol,
            interval=timeframe,
            limit=limit
        )

        if response.get('retCode') != 0:
            print(f"Bybit API Error: {response.get('retMsg')}")
            return None

        data_list = response['result'].get('list', [])
        if not data_list:
            print(f"No candle data returned for {symbol}")
            return None

        df = pd.DataFrame(data_list, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])

        df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp']), unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume', 'turnover']:
            df[col] = pd.to_numeric(df[col])

        df = df.iloc[::-1].reset_index(drop=True)

        print(f"✅ Railway Success: {len(df)} candles for {symbol} | Latest Close: {df['close'].iloc[-1]}")
        return df

    except Exception as e:
        print(f"❌ Attempt failed for {symbol}: {type(e).__name__} - {e}")
        raise  # Let tenacity retry


@retry(stop=stop_after_attempt(4), wait=wait_exponential(min=3, max=15))
def get_all_usdt_symbols():
    """Fetch symbols with retries"""
    symbols = []
    cursor = None
    try:
        session = HTTP(
            api_key=BYBIT_API_KEY,
            api_secret=BYBIT_API_SECRET,
            testnet=False,
            base_url="https://api.bytick.com"
        )

        while True:
            response = session.get_instruments_info(
                category="linear",
                limit=1000,
                cursor=cursor
            )

            if response.get('retCode') != 0:
                print(f"Instruments Error: {response.get('retMsg')}")
                return []

            for item in response['result'].get('list', []):
                if item.get('status') == 'Trading' and item.get('symbol', '').endswith('USDT'):
                    symbols.append(item['symbol'])

            cursor = response['result'].get('nextPageCursor')
            if not cursor:
                break
            time.sleep(0.3)

        print(f"✅ Fetched {len(symbols)} USDT symbols on Railway")
        return sorted(symbols)

    except Exception as e:
        print(f"❌ Symbols fetch failed: {e}")
        raise