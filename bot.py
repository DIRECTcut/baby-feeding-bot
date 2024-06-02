from asyncio import Queue
import logging
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, CallbackContext, ApplicationBuilder, ContextTypes
from models import User, Group, UserGroup, FeedingLog
from db import SessionLocal
from sqlalchemy.orm import Session

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Your bot token from BotFather
# FIXME: move to .env
TOKEN = '6976133506:AAGZI8hjMU_4QsLqzxCPhfyIXw8g0gaIYUU'

def init_user_if_not_exist(db: Session, username: str) -> int:
    user = db.query(User).filter_by(username=username).first()
    if user:
        return user.id
    if not user:
        user = User(username=username)
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Created user {username}")
        return user.id

# Command handlers
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    init_user_if_not_exist(SessionLocal(), update.message.from_user.username)

    keyboard = [
        [
            InlineKeyboardButton("Option 1", callback_data="1"),
            InlineKeyboardButton("Option 2", callback_data="2"),
        ],
        [InlineKeyboardButton("Option 3", callback_data="3")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    return update.message.reply_text("Please choose:", reply_markup=reply_markup)

    # return update.message.reply_text('Hi! Use /create_group to create a new group or /join_group to join an existing group.')

def create_group(update: Update, context: CallbackContext) -> None:
    """Create a new group."""
    logger.info("create_group handler invoked")
    username = update.message.from_user.username
    group_name = ' '.join(context.args)
    
    if not group_name:
        logger.info("No group name provided")
        return update.message.reply_text('Please provide a group name.')
        
    logger.info(f"Creating group with name: {group_name}")
    
    db: Session = SessionLocal()

    user_id = init_user_if_not_exist(db, username)
    
    if db.query(Group).filter_by(name=group_name).first():
        return update.message.reply_text(f'Group "{group_name}" already exists!')

    group = Group(name=group_name, creator_id=user_id)
    db.add(group)
    db.commit()
    
    return update.message.reply_text(f'Group "{group_name}" created!')

def join_group(update: Update, context: CallbackContext) -> None:
    """Join an existing group."""
    logger.info("join_group handler invoked")

    username = update.message.from_user.username
    group_name = ' '.join(context.args)
    
    if not group_name:
        logger.info("No group name provided")
        return update.message.reply_text('Please provide a group name.')

            
    db: Session = SessionLocal()
    user_id = init_user_if_not_exist(db, username)

    group = db.query(Group).filter_by(name=group_name).first()
    if not group:
        logger.info(f"Group does not exist: {group_name}")

        return update.message.reply_text(f'Group "{group_name}" does not exist.')

    if db.query(UserGroup).filter_by(user_id=user_id, group_id=group.id).first():
        logger.info(f"User trying join group they are already part of: {group_name}")

        return update.message.reply_text(f'You are already part of group {group_name}')

    user_group = UserGroup(user_id=user_id, group_id=group.id)
    db.add(user_group)
    db.commit()

    logger.info(f"User {user_id} joined group {group_name}")
    return update.message.reply_text(f'You have joined the group "{group_name}".')

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
    application.add_handler(CallbackQueryHandler(button))

    # Start the Bot
    application.run_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT, SIGTERM, or SIGABRT
    # updater.idle()

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()

    await query.edit_message_text(text=f"Selected option: {query.data}")
if __name__ == '__main__':
    main()
