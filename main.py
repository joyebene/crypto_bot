import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
import config
from bybit_data import get_bybit_data, get_all_usdt_symbols
from indicators import calculate_ema, calculate_rsi, calculate_macd
from signals import generate_signals
from trade_logger import log_signal
from signal_generator import get_signal_details

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for conversation
CHOOSING_SETTING, TYPING_VALUE = range(2)

# --- Bot State Initialization ---

def initialize_bot_data(bot_data: dict):
    """Initializes the bot_data with default settings and stats."""
    if 'settings' not in bot_data:
        bot_data['settings'] = config.SETTINGS.copy()
    if 'stats' not in bot_data:
        bot_data['stats'] = {}  # Symbol -> {'BUY': 0, 'SELL': 0, 'HOLD': 0}
    if 'last_signal' not in bot_data:
        bot_data['last_signal'] = {}  # Symbol -> "N/A"
    if 'last_signal_time' not in bot_data:
        bot_data['last_signal_time'] = {}  # Symbol -> datetime

# --- Standard Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends explanation and shows the command keyboard."""
    initialize_bot_data(context.bot_data)
    keyboard = [
        [KeyboardButton("/start_bot"), KeyboardButton("/stop_bot")],
        [KeyboardButton("/status"), KeyboardButton("/stats")],
        [KeyboardButton("/price"), KeyboardButton("/settings")],
        [KeyboardButton("/monitor_all_usdt")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Bot V2 Active. Welcome!\n\n"
        "Use the keyboard below to interact with me.",
        reply_markup=reply_markup,
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays a comprehensive status of the bot."""
    initialize_bot_data(context.bot_data)
    settings = context.bot_data['settings']

    # --- Settings ---
    status_message = "--- Current Settings ---\n"
    symbols_list = settings.get('symbols', [])
    for key, value in settings.items():
        if key == 'symbols':
            if len(symbols_list) > 10:
                status_message += f"symbols: (Monitoring {len(symbols_list)} pairs)\n"
            else:
                status_message += f"symbols: {value}\n"
        else:
            status_message += f"{key}: {value}\n"

    # --- Monitoring Status ---
    status_message += "\n--- Monitoring Status ---\n"
    active_symbols = []
    for job in context.job_queue.jobs():
        if job.name and job.name.startswith("signal_check_"):
            symbol = job.name.replace("signal_check_", "")
            active_symbols.append(symbol)

    if active_symbols:
        status_message += f"✅ Bot is RUNNING.\nActively monitoring: {len(active_symbols)} pairs\n"
    else:
        status_message += "❌ Bot is STOPPED.\n"

    # --- Last Signals ---
    status_message += "\n--- Last Recorded Signals ---\n"
    last_signals = context.bot_data.get('last_signal', {})
    
    if not last_signals:
        status_message += "No signals recorded yet.\n"
    else:
        # Show last signals for monitored symbols first
        monitored_last_signals = {s: last_signals[s] for s in active_symbols if s in last_signals}
        
        if not monitored_last_signals:
             status_message += "No signals recorded for currently monitored pairs.\n"
        else:
            # Limit to a reasonable number to avoid a huge message
            signals_to_show = list(monitored_last_signals.items())
            if len(signals_to_show) > 5:
                status_message += f"(Showing first 5 of {len(signals_to_show)} monitored pairs)\n"
                signals_to_show = signals_to_show[:5]
            
            for symbol, signal in signals_to_show:
                status_message += f"{symbol}: {signal}\n"
        
    await update.message.reply_text(status_message)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the signal statistics for all monitored symbols."""
    initialize_bot_data(context.bot_data)
    stats_data = context.bot_data.get('stats', {})
    
    if not stats_data:
        await update.message.reply_text("No statistics available yet.")
        return

    stats_message = "--- Signal Statistics ---\n"
    has_stats = False
    for symbol, symbol_stats in stats_data.items():
        if not any(c > 0 for c in symbol_stats.values()):
            continue
        has_stats = True
        stats_message += f"\nSymbol: {symbol}\n"
        for signal, count in symbol_stats.items():
            stats_message += f"  {signal}: {count}\n"
            
    if not has_stats:
        await update.message.reply_text("No statistics have been recorded yet.")
        return

    await update.message.reply_text(stats_message)


async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetches and displays the current price for monitored symbols."""
    initialize_bot_data(context.bot_data)
    settings = context.bot_data['settings']
    symbols = settings.get('symbols', [])

    if not symbols:
        await update.message.reply_text("No symbols configured. Use /settings to add symbols.")
        return

    message = "--- Current Prices ---\n"
    prices_to_fetch = symbols
    # If monitoring many symbols, only show prices for the first 5
    if len(symbols) > 5:
        prices_to_fetch = symbols[:5]
        message += f"(Showing first 5 of {len(symbols)} monitored pairs)\n"

    for symbol in prices_to_fetch:
        df = get_bybit_data(symbol, settings['timeframe'], limit=1)
        if df is not None and not df.empty:
            price = df.iloc[-1]['close']
            message += f"{symbol}: {price:.4f}\n"
        else:
            message += f"Could not fetch price for {symbol}.\n"
    
    await update.message.reply_text(message)


# --- Settings Conversation Handlers ---

async def settings_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the settings conversation."""
    initialize_bot_data(context.bot_data)
    settings_keys = list(context.bot_data['settings'].keys())
    keyboard = [
        [KeyboardButton(key)] for key in settings_keys
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "Which setting would you like to change? (or /cancel)",
        reply_markup=reply_markup
    )
    return CHOOSING_SETTING

async def received_setting_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks for the new value for the chosen setting."""
    setting_to_change = update.message.text
    context.user_data['setting_to_change'] = setting_to_change

    if setting_to_change == 'strategy':
        keyboard = [[KeyboardButton('breakout'), KeyboardButton('rsi_only')]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            f"Please choose the new value for '{setting_to_change}':",
            reply_markup=reply_markup
        )
    elif setting_to_change == 'symbols':
        await update.message.reply_text(
            f"Please type the new comma-separated list of symbols for '{setting_to_change}':\n(e.g., BTCUSDT,ETHUSDT,SOLUSDT)"
        )
    else:
        await update.message.reply_text(
            f"Please type the new value for '{setting_to_change}':"
        )
    return TYPING_VALUE

async def received_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Updates the setting with the new value."""
    key = context.user_data.get('setting_to_change')
    if not key:
        context.user_data.clear()
        return ConversationHandler.END

    value_str = update.message.text
    settings = context.bot_data['settings']
    is_running = any(job.name and job.name.startswith("signal_check_") for job in context.job_queue.jobs())

    try:
        new_value: object
        if key == 'symbols':
            new_value = [s.strip().upper() for s in value_str.split(',')]
        else:
            original_type = type(settings.get(key))
            if original_type in (int, float):
                if not value_str.replace('.', '', 1).isdigit():
                    raise ValueError("Input is not a valid number.")
                new_value = original_type(value_str)
            else:
                new_value = value_str
        
        settings[key] = new_value
        
        # Re-create the main keyboard for the confirmation message
        main_keyboard = [
            [KeyboardButton("/start_bot"), KeyboardButton("/stop_bot")],
            [KeyboardButton("/status"), KeyboardButton("/stats")],
            [KeyboardButton("/price"), KeyboardButton("/settings")],
            [KeyboardButton("/monitor_all_usdt")],
        ]
        main_reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)

        await update.message.reply_text(
            f"✅ Setting '{key}' updated successfully.",
            reply_markup=main_reply_markup
        )
        
        if is_running:
            await update.message.reply_text("Restarting bot to apply new settings...")
            # Pass the update object to start_bot
            await stop_bot(update, context, silent=True)
            await start_bot(update, context)
        
        context.user_data.clear()
        return ConversationHandler.END
    except (ValueError, KeyError) as e:
        logger.error(f"Error updating setting: {e}")
        await update.message.reply_text("Invalid value or setting. Please try again or /cancel.")
        context.user_data.clear()
        return ConversationHandler.END

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    main_keyboard = [
        [KeyboardButton("/start_bot"), KeyboardButton("/stop_bot")],
        [KeyboardButton("/status"), KeyboardButton("/stats")],
        [KeyboardButton("/price"), KeyboardButton("/settings")],
        [KeyboardButton("/monitor_all_usdt")],
    ]
    main_reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Operation cancelled.",
        reply_markup=main_reply_markup
    )
    context.user_data.clear()
    return ConversationHandler.END

# --- Job Queue Handlers ---

async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Starts signal checking jobs for all configured symbols."""
    initialize_bot_data(context.bot_data)
    chat_id = update.effective_message.chat_id
    settings = context.bot_data['settings']
    symbols = settings.get('symbols', [])
    
    if not symbols:
        await update.message.reply_text("No symbols configured. Use /settings to add symbols.")
        return

    # Stop any existing jobs before starting new ones
    await stop_bot(update, context, silent=True)

    timeframe_minutes = int(settings['timeframe'])
    started_symbols = []
    for symbol in symbols:
        job_name = f"signal_check_{symbol}"
        context.job_queue.run_repeating(
            check_signals,
            interval=timeframe_minutes * 60,
            first=1,
            chat_id=chat_id,
            name=job_name,
            data={'symbol': symbol}
        )
        started_symbols.append(symbol)

    if started_symbols:
        await update.message.reply_text(
            f"Bot started for {len(started_symbols)} pairs.\n"
            f"Strategy: '{settings['strategy']}'. Checking every {timeframe_minutes} mins."
        )
    else:
        await update.message.reply_text("Could not start bot. Check configuration.")

async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE, silent: bool = False) -> None:
    """Stops all signal checking jobs."""
    stopped_count = 0
    for job in context.job_queue.jobs():
        if job.name and job.name.startswith("signal_check_"):
            job.schedule_removal()
            stopped_count += 1

    if not silent:
        if stopped_count > 0:
            await update.message.reply_text(f"Bot stopped. {stopped_count} monitoring job(s) removed.")
        else:
            await update.message.reply_text("Bot is not currently running.")

# --- Core Logic & Error Handling ---

async def check_signals(context: ContextTypes.DEFAULT_TYPE) -> None:
    """The scheduled function to check for and report signals for a specific symbol."""
    job = context.job
    if not job or not job.data:
        logger.error("check_signals called without a job or job data.")
        return
        
    symbol = job.data['symbol']
    
    initialize_bot_data(context.bot_data)
    settings = context.bot_data['settings']
    
    try:
        df = get_bybit_data(symbol, settings['timeframe'])
        if df is not None and not df.empty:
            # --- Indicator Calculations ---
            df['ema'] = calculate_ema(df['close'], settings['ema_period'])
            df['rsi'] = calculate_rsi(df['close'], settings['rsi_period'])
            df['macd'], df['macd_signal'], df['macd_hist'] = calculate_macd(df['close'])

            signal = generate_signals(df, settings)
            price = df.iloc[-1]['close']
            rsi = df.iloc[-1]['rsi']

            # Log every signal generated for backtesting and analysis
            log_signal(symbol, signal, price, rsi)
            
            # Initialize stats for the symbol if not present
            if symbol not in context.bot_data['stats']:
                context.bot_data['stats'][symbol] = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
            context.bot_data['last_signal'][symbol] = signal
            context.bot_data['stats'][symbol][signal] += 1
            
            if signal != "HOLD":
                # --- Signal Throttling Check ---
                now = datetime.now()
                last_time = context.bot_data['last_signal_time'].get(symbol)
                throttle_minutes = settings.get('signal_throttle_minutes', 30)

                if last_time and (now - last_time).total_seconds() / 60 < throttle_minutes:
                    logger.info(f"THROTTLED: Signal for {symbol} was already sent recently.")
                    return
                # --- End Throttling Check ---
                
                context.bot_data['last_signal_time'][symbol] = now # Update the last signal time

                # --- Generate Detailed Signal Message ---
                details = get_signal_details(signal, price, settings)
                if not details:
                    return

                # --- RSI & MACD Context ---
                rsi_context = "(Oversold)" if rsi < 30 else "(Overbought)" if rsi > 70 else ""
                macd_hist = df.iloc[-1]['macd_hist']
                macd_context = "(Bullish Crossover)" if macd_hist > 0 and df.iloc[-2]['macd_hist'] < 0 else "(Bearish Crossover)" if macd_hist < 0 and df.iloc[-2]['macd_hist'] > 0 else ""

                # --- Construct the Message ---
                message = (
                    f"🚨 **STRONG {signal} SIGNAL: {symbol}** 🚨\n\n"
                    f"**Entry Price:** ${price:,.4f}\n\n"
                    f"**Take Profit 1:** ${details['tp1']:,.4f} (+{abs(details['tp1']/price-1):.1%})\n"
                    f"**Take Profit 2:** ${details['tp2']:,.4f} (+{abs(details['tp2']/price-1):.1%})\n"
                    f"**Take Profit 3:** ${details['tp3']:,.4f} (+{abs(details['tp3']/price-1):.1%})\n\n"
                    f"**Stop Loss:** ${details['sl']:,.4f} (-{abs(details['sl']/price-1):.1%})\n\n"
                    f"**Risk/Reward Ratio:** {details['rr_ratio']:.2f}\n"
                    f"**RSI ({settings['rsi_period']}):** {rsi:.2f} {rsi_context}\n"
                    f"**MACD:** {macd_context}\n\n"
                    f"*Validity: 4h | Exchange: Bybit | #{symbol.replace('USDT', '')}*"
                )
                
                await context.bot.send_message(job.chat_id, text=message, parse_mode='Markdown')

            else:
                # Only log HOLD signals, don't send a message
                logger.info(f"Signal is HOLD for {symbol}.")

        else:
            logger.warning(f"Could not fetch data for {symbol} in check_signals.")
    except Exception as e:
        logger.error(f"An error occurred in check_signals for {symbol}: {e}")

async def monitor_all_usdt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetches all USDT symbols and starts monitoring them."""
    await update.message.reply_text("Fetching all available USDT trading pairs from Bybit. This may take a moment...")
    
    all_symbols = get_all_usdt_symbols()
    
    if not all_symbols:
        await update.message.reply_text("Could not retrieve the list of symbols. Please check the logs and try again.")
        return
        
    context.bot_data['settings']['symbols'] = all_symbols
    
    await update.message.reply_text(f"Found {len(all_symbols)} symbols. Restarting bot to monitor all pairs...")
    
    # Restart the bot to apply the new symbol list
    await stop_bot(update, context, silent=True)
    await start_bot(update, context)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

# --- Main Application Setup ---

def main() -> None:
    """Run the bot."""
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    initialize_bot_data(application.bot_data)

    # Setup conversation handler for settings
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("settings", settings_start)],
        states={
            CHOOSING_SETTING: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_setting_choice)],
            TYPING_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_value)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        conversation_timeout=60
    )
    application.add_handler(conv_handler)

    # Add other command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("price", get_price))
    application.add_handler(CommandHandler("start_bot", start_bot))
    application.add_handler(CommandHandler("stop_bot", stop_bot))
    application.add_handler(CommandHandler("monitor_all_usdt", monitor_all_usdt))
    
    application.add_error_handler(error_handler)

    print("--- Bot is running. Press Ctrl-C to stop. ---")
    application.run_polling()

if __name__ == "__main__":
    main()