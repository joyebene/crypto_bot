import logging
import os
from datetime import datetime

LOG_DIR = 'logs'
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Create a custom logger for signals
signal_logger = logging.getLogger('signal_logger')
signal_logger.setLevel(logging.INFO)
signal_logger.propagate = False # Prevent signals from appearing in the main console log

# Create a file handler for the signal logger
# We will use a CSV format for easy analysis.
log_file = os.path.join(LOG_DIR, 'signals.csv')

# Check if the file exists to write the header only once
write_header = not os.path.exists(log_file)

file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.INFO)

# Set a simple formatter, as we will format the message ourselves
formatter = logging.Formatter('%(message)s')
file_handler.setFormatter(formatter)

# Add the handler to the logger
if not signal_logger.handlers:
    signal_logger.addHandler(file_handler)
    if write_header:
        # The header for our CSV file
        signal_logger.info('timestamp,symbol,signal,price,rsi')

def log_signal(symbol: str, signal: str, price: float, rsi: float):
    """Logs a trading signal to the signals.csv file."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"{timestamp},{symbol},{signal},{price:.4f},{rsi:.2f}"
    signal_logger.info(log_message)