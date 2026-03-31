import time
from config import config
from database.db_manager import DatabaseManager
from notifiers.telegram_command_bot import TelegramCommandBot
from utils.logger import get_logger

logger = get_logger(__name__)

def main():
    logger.info("Testing Telegram command bot...")
    
    # Initialize database
    db = DatabaseManager(config.database.path)
    
    # Initialize Telegram command bot
    bot = TelegramCommandBot(config.telegram, db)
    
    # Start the bot
    bot.start()
    
    logger.info("Telegram command bot started. Testing commands...")
    
    # Test sending a message
    test_chat_id = config.telegram.chat_id
    logger.info(f"Testing message to chat_id: {test_chat_id}")
    
    # Test help command
    bot.handle_help(test_chat_id, "/help")
    
    # Try with channel_id if available
    if config.telegram.channel_id:
        logger.info(f"Testing message to channel_id: {config.telegram.channel_id}")
        bot.handle_help(config.telegram.channel_id, "/help")
    
    logger.info("Test completed. Bot is running in background.")
    
    # Keep the script running to test commands
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping bot...")
        bot.stop()

if __name__ == "__main__":
    main()
