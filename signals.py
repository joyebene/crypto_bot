import pandas as pd
from bybit_data import get_bybit_data
from indicators import calculate_ema, calculate_rsi
import config

# --- Strategy 1: Breakout Confirmation ---

def _detect_breakout(data, lookback_period=20):
    """
    Helper function to detect a simple price breakout.
    (Underscore indicates it's intended for internal use within this module)
    """
    if len(data) < lookback_period:
        return False
    
    recent_data = data.tail(lookback_period)
    latest_high = recent_data['high'].iloc[-1]
    highest_in_lookback = recent_data['high'].iloc[:-1].max()

    return latest_high > highest_in_lookback

def strategy_breakout(df, settings):
    """
    Generates trading signals based on the breakout strategy.
    """
    latest_candle = df.iloc[-1]

    # --- Buy Signal Conditions ---
    price_above_ema = latest_candle['close'] > latest_candle['ema']
    rsi_ok = latest_candle['rsi'] < 70
    breakout_detected = _detect_breakout(df)
    volume_ok = latest_candle['volume'] > settings['volume_threshold']

    if price_above_ema and rsi_ok and breakout_detected and volume_ok:
        return "BUY"

    # --- Sell Signal Conditions ---
    if latest_candle['rsi'] > 75:
        return "SELL"

    return "HOLD"

# --- Strategy 2: Simple RSI ---

def strategy_rsi_only(df, settings):
    """
    Generates signals based only on RSI (oversold/overbought).
    """
    latest_candle = df.iloc[-1]

    # --- Buy Signal ---
    if latest_candle['rsi'] < 30:
        return "BUY"

    # --- Sell Signal ---
    if latest_candle['rsi'] > 70:
        return "SELL"
        
    return "HOLD"

# --- Main Signal Generation Router ---

def generate_signals(df, settings):
    """
    Calls the appropriate strategy function based on the settings.
    """
    strategy = settings.get("strategy", "breakout") # Default to breakout if not set

    if strategy == "breakout":
        return strategy_breakout(df, settings)
    elif strategy == "rsi_only":
        return strategy_rsi_only(df, settings)
    else:
        # If the strategy is unknown, default to HOLD and log a warning
        print(f"Warning: Unknown strategy '{strategy}'. Defaulting to HOLD.")
        return "HOLD"

# --- Testing Block ---

if __name__ == '__main__':
    # This block is for testing the new structure
    settings = config.SETTINGS
    
    df = get_bybit_data(settings['symbol'], settings['timeframe'])

    if df is not None:
        df['ema'] = calculate_ema(df['close'], settings['ema_period'])
        df['rsi'] = calculate_rsi(df['close'], settings['rsi_period'])

        # --- Test the breakout strategy ---
        settings['strategy'] = 'breakout'
        signal_breakout = generate_signals(df, settings)
        print(f"--- Signal for Breakout Strategy ---")
        print(f"Generated Signal: {signal_breakout}")

        # --- Test the RSI-only strategy ---
        settings['strategy'] = 'rsi_only'
        signal_rsi = generate_signals(df, settings)
        print(f"\n--- Signal for RSI-Only Strategy ---")
        print(f"Generated Signal: {signal_rsi}")