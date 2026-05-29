import pandas as pd

def get_signal_details(signal: str, price: float, settings: dict):
    """
    Generates detailed signal information including TP, SL, and R/R ratio.

    Args:
        signal (str): The trading signal ('BUY' or 'SELL').
        price (float): The current price.
        settings (dict): The bot's settings dictionary.

    Returns:
        dict: A dictionary with detailed signal info, or None if signal is 'HOLD'.
    """
    if signal == "HOLD":
        return None

    # --- Default Percentages ---
    # These can be moved to config.py later if you want to make them easily adjustable
    tp_percs = [0.02, 0.04, 0.06]  # Take Profit percentages
    sl_perc = 0.03                 # Stop Loss percentage

    details = {
        "entry_price": price,
        "tp1": 0.0,
        "tp2": 0.0,
        "tp3": 0.0,
        "sl": 0.0,
        "rr_ratio": 0.0
    }

    if signal == "BUY":
        details["tp1"] = price * (1 + tp_percs[0])
        details["tp2"] = price * (1 + tp_percs[1])
        details["tp3"] = price * (1 + tp_percs[2])
        details["sl"] = price * (1 - sl_perc)
    elif signal == "SELL": # For SHORT signals
        details["tp1"] = price * (1 - tp_percs[0])
        details["tp2"] = price * (1 - tp_percs[1])
        details["tp3"] = price * (1 - tp_percs[2])
        details["sl"] = price * (1 + sl_perc)

    # --- Calculate Risk/Reward Ratio ---
    # Based on the first take profit target
    potential_profit = abs(details["tp1"] - price)
    potential_loss = abs(details["sl"] - price)

    if potential_loss > 0:
        details["rr_ratio"] = potential_profit / potential_loss
    else:
        details["rr_ratio"] = float('inf') # Avoid division by zero

    return details