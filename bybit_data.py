import pandas as pd
from pybit.unified_trading import HTTP
import config
import time

def get_all_usdt_symbols():
    """
    Fetches all trading USDT linear perpetual symbols from Bybit.

    Returns:
        list: A list of USDT symbols (e.g., ['BTCUSDT', 'ETHUSDT']), or an empty list if an error occurs.
    """
    symbols = []
    cursor = None
    try:
        session = HTTP(api_key=config.BYBIT_API_KEY, api_secret=config.BYBIT_API_SECRET, testnet=True)
        while True:
            response = session.get_instruments_info(
                category="linear",
                limit=1000,  # Max limit is 1000
                cursor=cursor
            )

            if response.get('retCode') == 0 and 'result' in response:
                result_list = response['result'].get('list', [])
                for item in result_list:
                    if item.get('status') == 'Trading' and item.get('symbol', '').endswith('USDT'):
                        symbols.append(item['symbol'])
                
                cursor = response['result'].get('nextPageCursor')
                if not cursor:
                    break  # Exit loop if no more pages
            else:
                print(f"Error fetching instruments: {response.get('retMsg', 'Unknown Error')}")
                return [] # Return empty list on error
            
            time.sleep(0.1) # Respect rate limits

        return sorted(symbols)

    except Exception as e:
        print(f"An error occurred in get_all_usdt_symbols: {e}")
        return []

def get_bybit_data(symbol, timeframe, limit=200):
    """
    Fetches candlestick data from Bybit.

    Args:
        symbol (str): The trading symbol (e.g., 'BTCUSDT').
        timeframe (str): The timeframe for the candles (e.g., '60' for 1-hour).
        limit (int): The number of candles to fetch.

    Returns:
        pandas.DataFrame: A DataFrame with the candlestick data, or None if an error occurs.
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

        if response['retCode'] == 0 and 'list' in response['result']:
            data = response['result']['list']
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])

            # Convert timestamp to a numeric type first, then to datetime
            df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', errors='coerce')

            # Convert all other columns to numeric
            for col in ['open', 'high', 'low', 'close', 'volume', 'turnover']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Drop any rows that failed any conversion step (have NaN or NaT)
            df.dropna(inplace=True)

            # Bybit returns data in reverse chronological order, so we reverse it
            df = df.iloc[::-1].reset_index(drop=True)
            return df
        else:
            print(f"Error fetching data from Bybit: {response['retMsg']}")
            return None

    except Exception as e:
        print(f"An error occurred in get_bybit_data: {e}")
        return None

if __name__ == '__main__':
    # --- Test get_bybit_data ---
    print("--- Testing get_bybit_data ---")
    settings = config.SETTINGS
    # Use the first symbol from the list for testing
    test_symbol = settings['symbols'][0] if settings.get('symbols') else 'BTCUSDT'
    df = get_bybit_data(test_symbol, settings['timeframe'])

    if df is not None:
        print(f"Successfully fetched {len(df)} candles for {test_symbol}")
        print(df.head())
    else:
        print(f"Failed to fetch data for {test_symbol}")

    # --- Test get_all_usdt_symbols ---
    print("\n--- Testing get_all_usdt_symbols ---")
    all_symbols = get_all_usdt_symbols()
    if all_symbols:
        print(f"Successfully fetched {len(all_symbols)} USDT symbols.")
        print(f"First 5 symbols: {all_symbols[:5]}")
    else:
        print("Failed to fetch the list of USDT symbols.")