import telegram
import asyncio
import config

async def send_telegram_message(message):
    """
    Sends a message to a Telegram user or channel.

    Args:
        message (str): The message to send.
    """
    try:
        bot = telegram.Bot(token=config.TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=config.TELEGRAM_CHAT_ID, text=message)
        print("Telegram message sent successfully!")
    except Exception as e:
        print(f"An error occurred while sending Telegram message: {e}")

if __name__ == '__main__':
    # This is for testing the function directly
    # We create a sample message and send it.
    test_message = "Hello from your trading bot! This is a test message."
    
    # The python-telegram-bot library is asynchronous, so we need to run the function
    # within an asyncio event loop.
    print("Sending a test message to Telegram...")
    asyncio.run(send_telegram_message(test_message))