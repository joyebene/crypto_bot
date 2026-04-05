import pandas as pd
import config
from bybit_data import get_bybit_data

def calculate_ema(data, period):
    """
    Calculates the Exponential Moving Average (EMA).

    Args:
        data (pd.Series): A pandas Series of price data (e.g., close prices).
        period (int): The period for the EMA.

    Returns:
        pd.Series: A pandas Series with the EMA values.
    """
    return data.ewm(span=period, adjust=False).mean()

def calculate_rsi(data, period):
    """
    Calculates the Relative Strength Index (RSI).

    Args:
        data (pd.Series): A pandas Series of price data (e.g., close prices).
        period (int): The period for the RSI.

    Returns:
        pd.Series: A pandas Series with the RSI values.
    """
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

if __name__ == '__main__':
    # This is for testing the functions directly
    settings = config.SETTINGS
    
    # Fetch data to test with
    df = get_bybit_data(settings['symbol'], settings['timeframe'])

    if df is not None:
        # Calculate indicators and add them as new columns to the DataFrame
        df['ema'] = calculate_ema(df['close'], settings['ema_period'])
        df['rsi'] = calculate_rsi(df['close'], settings['rsi_period'])

        print(f"Successfully calculated indicators for {settings['symbol']}")
        # Print the last 15 rows to see the new 'ema' and 'rsi' columns
        print(df.tail(15))