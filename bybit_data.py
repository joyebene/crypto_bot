import pandas as pd
from pybit.unified_trading import HTTP
import config
import time


def get_all_usdt_symbols():
    """Fetches all active USDT perpetual (linear) symbols from Bybit."""
    symbols = []
    cursor = None
    try:
        session = HTTP(
            api_key=config.BYBIT_API_KEY,
            api_secret=config.BYBIT_API_SECRET,
            testnet=True
        )

        while True:
            response = session.get_instruments_info(
                category="linear",
                limit=1000,
                cursor=cursor
            )

            if response.get('retCode') != 0:
                print(f"Error fetching instruments: {response.get('retMsg')}")
                return []

            result = response['result']
            for item in result.get('list', []):
                if item.get('status') == 'Trading' and item.get('symbol', '').endswith('USDT'):
                    symbols.append(item['symbol'])

            cursor = result.get('nextPageCursor')
            if not cursor:
                break

            time.sleep(0.2)  # Be gentle with rate limits

        return sorted(symbols)

    except Exception as e:
        print(f"Exception in get_all_usdt_symbols: {e}")
        return []


def get_bybit_data(symbol: str, timeframe: str, limit: int = 200):
    """
    Fetches candlestick (kline) data from Bybit.
    Returns pandas DataFrame with columns: timestamp, open, high, low, close, volume, turnover
    """
    try:
        session = HTTP(
            api_key=config.BYBIT_API_KEY,
            api_secret=config.BYBIT_API_SECRET,
            testnet=True
        )

        response = session.get_kline(
            category="linear",
            symbol=symbol,
            interval=timeframe,
            limit=limit
        )

        if response.get('retCode') != 0:
            print(f"Bybit API Error for {symbol}: {response.get('retMsg')}")
            return None

        data_list = response['result'].get('list', [])

        if not data_list:
            print(f"No kline data returned for {symbol} (testnet may have limited data)")
            return None

        # Correct column mapping for Bybit V5 kline
        df = pd.DataFrame(data_list, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
        ])

        # Convert types safely
        df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', errors='coerce')

        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'turnover']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df.dropna(inplace=True)

        # Bybit returns newest candle first → reverse to oldest first
        df = df.iloc[::-1].reset_index(drop=True)

        print(f"✅ Successfully fetched {len(df)} candles for {symbol}")
        return df

    except Exception as e:
        print(f"Exception in get_bybit_data for {symbol}: {e}")
        return None


if __name__ == '__main__':
    settings = config.SETTINGS
    test_symbol = settings.get('symbols', ['BTCUSDT'])[0]

    print("=== Testing get_bybit_data ===")
    df = get_bybit_data(test_symbol, settings['timeframe'], limit=200)

    if df is not None and not df.empty:
        print(df.head())
        print(f"\nLatest Close Price: {df['close'].iloc[-1]}")
    else:
        print("Failed to fetch price data. Try increasing limit or switching to mainnet (testnet=False).")

    print("\n=== Testing get_all_usdt_symbols ===")
    all_symbols = get_all_usdt_symbols()
    if all_symbols:
        print(f"Total USDT Perpetual symbols: {len(all_symbols)}")
        print(f"First 10: {all_symbols[:10]}")
    else:
        print("Failed to fetch symbols list.")