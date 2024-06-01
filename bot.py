from asyncio import Queue
import logging
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, CallbackContext, ApplicationBuilder

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Your bot token from BotFather
# FIXME: move to .env
TOKEN = '6976133506:AAGZI8hjMU_4QsLqzxCPhfyIXw8g0gaIYUU'

# Command handlers
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    return update.message.reply_text('Hi! Use /create_group to create a new group or /join_group to join an existing group.')

def create_group(update: Update, context: CallbackContext) -> None:
    """Create a new group."""
    # Implementation for creating a group
    return update.message.reply_text('Group created! Share this token with others to join: XYZ123')

def join_group(update: Update, context: CallbackContext) -> None:
    """Join an existing group."""
    # Implementation for joining a group
    return update.message.reply_text('You have joined the group!')

def log_feeding(update: Update, context: CallbackContext) -> None:
    """Log a feeding."""
    # Implementation for logging a feeding
    return update.message.reply_text('Feeding logged!')

def set_interval(update: Update, context: CallbackContext) -> None:
    """Set the notification interval."""
    # Implementation for setting the notification interval
    return update.message.reply_text('Notification interval set!')

def leave_group(update: Update, context: CallbackContext) -> None:
    """Leave the current group."""
    # Implementation for leaving a group
    return update.message.reply_text('You have left the group.')

def kick_member(update: Update, context: CallbackContext) -> None:
    """Kick a member from the group."""
    # Implementation for kicking a member (only available to the group creator)
    return update.message.reply_text('Member kicked from the group.')

def main() -> None:
    """Start the bot."""

    application = ApplicationBuilder().token(TOKEN).build()
    # handler = CommandHandler('start', start)
    # Create the Bot instance
    # bot = Bot(TOKEN)

    # Create the update queue
    # update_queue = Queue()

    # Create the Updater and pass it your bot's token.
    # updater = Updater(bot, update_queue)

    # Get the dispatcher to register handlers
    # dp = Dispatcher(bot, update_queue, use_context=True)

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("create_group", create_group))
    application.add_handler(CommandHandler("join_group", join_group))
    application.add_handler(CommandHandler("log_feeding", log_feeding))
    application.add_handler(CommandHandler("set_interval", set_interval))
    application.add_handler(CommandHandler("leave_group", leave_group))
    application.add_handler(CommandHandler("kick_member", kick_member))

    # Start the Bot
    application.run_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT, SIGTERM, or SIGABRT
    # updater.idle()

if __name__ == '__main__':
    main()
