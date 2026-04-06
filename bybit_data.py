import pandas as pd
from pybit.unified_trading import HTTP
import config
import time


def get_all_usdt_symbols():
    """Fetches all active USDT perpetual symbols from Bybit (Mainnet)."""
    symbols = []
    cursor = None
    try:
        session = HTTP(
            api_key=config.BYBIT_API_KEY,
            api_secret=config.BYBIT_API_SECRET,
            testnet=False          # ← Changed to False
        )

        while True:
            response = session.get_instruments_info(
                category="linear",
                limit=1000,
                cursor=cursor
            )

            if response.get('retCode') != 0:
                print(f"Error: {response.get('retMsg')}")
                return []

            for item in response['result'].get('list', []):
                if item.get('status') == 'Trading' and item.get('symbol', '').endswith('USDT'):
                    symbols.append(item['symbol'])

            cursor = response['result'].get('nextPageCursor')
            if not cursor:
                break

            time.sleep(0.2)

        return sorted(symbols)

    except Exception as e:
        print(f"Exception in get_all_usdt_symbols: {e}")
        return []


def get_bybit_data(symbol: str, timeframe: str, limit: int = 200):
    """Fetches kline data from Bybit (Mainnet)."""
    try:
        session = HTTP(
            api_key=config.BYBIT_API_KEY,
            api_secret=config.BYBIT_API_SECRET,
            testnet=False          # ← Changed to False
        )

        response = session.get_kline(
            category="linear",
            symbol=symbol,
            interval=timeframe,
            limit=limit
        )

        if response.get('retCode') != 0:
            print(f"Bybit Error for {symbol}: {response.get('retMsg')}")
            return None

        data_list = response['result'].get('list', [])
        if not data_list:
            print(f"No data returned for {symbol}")
            return None

        df = pd.DataFrame(data_list, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])

        df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp'], errors='coerce'), unit='ms', errors='coerce')
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'turnover']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df.dropna(inplace=True)
        df = df.iloc[::-1].reset_index(drop=True)   # oldest first

        print(f"✅ Fetched {len(df)} candles for {symbol} | Latest Close: {df['close'].iloc[-1]}")
        return df

    except Exception as e:
        print(f"Exception fetching {symbol}: {e}")
        return None


if __name__ == '__main__':
    settings = config.SETTINGS
    test_symbol = settings.get('symbols', ['BTCUSDT'])[0]

    print("=== Testing get_bybit_data (Mainnet) ===")
    df = get_bybit_data(test_symbol, settings['timeframe'], limit=200)

    print("\n=== Testing get_all_usdt_symbols (Mainnet) ===")
    all_symbols = get_all_usdt_symbols()
    if all_symbols:
        print(f"Total USDT symbols: {len(all_symbols)}")
        print(f"First 10: {all_symbols[:10]}")
    else:
        print("Failed to fetch symbols.")