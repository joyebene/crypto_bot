import pandas as pd
from pybit.unified_trading import HTTP
import config
import time
import os

# Use environment variables on Railway (fallback to config for local)
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY") or getattr(config, "BYBIT_API_KEY", None)
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET") or getattr(config, "BYBIT_API_SECRET", None)


def get_bybit_data(symbol: str, timeframe: str, limit: int = 200):
    """Fetches candlestick data - Optimized for Railway"""
    try:
        # Use 'recv_window' and keep testnet=False for mainnet
        session = HTTP(
            api_key=BYBIT_API_KEY,
            api_secret=BYBIT_API_SECRET,
            testnet=False,           # Mainnet
            # No base_url here - pybit doesn't support it in your version
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

        df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp'], errors='coerce'), unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume', 'turnover']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df.dropna(inplace=True)
        df = df.iloc[::-1].reset_index(drop=True)   # oldest first

        print(f"✅ SUCCESS on Railway: {len(df)} candles for {symbol} | Latest Close: {df['close'].iloc[-1]}")
        return df

    except Exception as e:
        print(f"❌ Error fetching {symbol}: {type(e).__name__} - {e}")
        return None


def get_all_usdt_symbols():
    """Fetches all active USDT perpetual symbols"""
    symbols = []
    cursor = None
    try:
        session = HTTP(
            api_key=BYBIT_API_KEY,
            api_secret=BYBIT_API_SECRET,
            testnet=False
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
            time.sleep(0.25)

        print(f"✅ Fetched {len(symbols)} USDT symbols successfully")
        return sorted(symbols)

    except Exception as e:
        print(f"Exception in get_all_usdt_symbols: {e}")
        return []


if __name__ == '__main__':
    settings = config.SETTINGS
    test_symbol = settings.get('symbols', ['BTCUSDT'])[0]

    print("=== Testing get_bybit_data ===")
    df = get_bybit_data(test_symbol, settings['timeframe'], limit=200)

    if df is not None and not df.empty:
        print(df.tail(3))

    print("\n=== Testing get_all_usdt_symbols ===")
    all_symbols = get_all_usdt_symbols()
    if all_symbols:
        print(f"Total symbols: {len(all_symbols)}")
        print(f"First 10: {all_symbols[:10]}")