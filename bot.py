from asyncio import Queue
import logging
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, CallbackContext, ApplicationBuilder, ContextTypes, ConversationHandler, MessageHandler, filters
from models import User, Group, UserGroup, FeedingLog
from db import SessionLocal
from sqlalchemy.orm import Session
import os

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

CHOOSING_ACTION, ENTER_GROUP_NAME = range(2)

TEST_ACTION, JOIN_GROUP, CREATE_GROUP = range(3)

# Your bot token from BotFather
# FIXME: move to .env
TOKEN = os.environ['TELEGRAM_TOKEN']

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
async def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user_id = init_user_if_not_exist(SessionLocal(), update.message.from_user.username)
    logger.info("User %s started the conversation.", user_id)

    # reply_keyboard = [
    #     ["Create Group", "Join Group"],
    #     ["Done"],
    # ]
    # reply_markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    # await update.callback_query.answer()
    keyboard = [
        [
            InlineKeyboardButton("Some action", callback_data=str(TEST_ACTION)),
            # InlineKeyboardButton("Log new feeding", callback_data=str(JOIN_GROUP)),
            # InlineKeyboardButton("Create new group", callback_data=str(CREATE_GROUP)),
        ]
        # ,
        # [InlineKeyboardButton("Option 3", callback_data="3")],
    ]
    # reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    reply_markup = InlineKeyboardMarkup(keyboard)



    # Define the conversation handler with states
    # conv_handler = ConversationHandler(
    #     entry_points=[CommandHandler('start', start)],
    #     states={
    #         ENTER_TEXT: [MessageHandler(Filters.text & ~Filters.command, enter_text)],
    #     },
    #     fallbacks=[CommandHandler('cancel', cancel)],
    # )





    await update.message.reply_text("Please choose:", reply_markup=reply_markup)
    return CHOOSING_ACTION

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
    # TODO?: https://docs.python-telegram-bot.org/en/stable/telegram.ext.conversationhandler.html#:~:text=heavily%20relies%20on%20incoming%20updates%20being
    # application.concurrent_updates = False
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
    # application.add_handler(CommandHandler("start", start))
    # application.add_handler(CommandHandler("create_group", create_group))
    # application.add_handler(CommandHandler("join_group", join_group))
    # application.add_handler(CommandHandler("log_feeding", log_feeding))
    # application.add_handler(CommandHandler("set_interval", set_interval))
    # application.add_handler(CommandHandler("leave_group", leave_group))
    # application.add_handler(CommandHandler("kick_member", kick_member))
    # application.add_handler(CallbackQueryHandler(button))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_ACTION: [
                CallbackQueryHandler(test_action, pattern=f"^{str(TEST_ACTION)}$"),
                CallbackQueryHandler(set_user_is_joining_group, pattern=f"^{str(JOIN_GROUP)}$"),
                CallbackQueryHandler(set_user_is_creating_group, pattern=f"^{str(CREATE_GROUP)}$"),
            ],
            ENTER_GROUP_NAME: [
                MessageHandler(
                    filters.TEXT & ~(filters.COMMAND | filters.Regex("^Done$")), enter_group_name
                )
            ],
        },
        fallbacks=[MessageHandler(filters.Regex("^Done$"), done)],
    )

    application.add_handler(conv_handler)

    # Start the Bot
    application.run_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT, SIGTERM, or SIGABRT
    # updater.idle()

async def test_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    return

async def set_user_is_joining_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["action"] = JOIN_GROUP

    return 

async def set_user_is_creating_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["action"] = CREATE_GROUP


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer('testing')

    await query.edit_message_text(text=f"Selected option: {query.data}")

async def choose_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's choice of action."""
    text = update.message.text.lower()
    context.user_data["action"] = text
    
    if text == "create group":
        await update.message.reply_text("Please enter the name of the group to create:")
    elif text == "join group":
        await update.message.reply_text("Please enter the name of the group to join:")
    else:
        await update.message.reply_text("Invalid choice. Please choose 'Create Group' or 'Join Group'.")

    return ENTER_GROUP_NAME

async def enter_group_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's input of the group name."""
    group_name = update.message.text
    action = context.user_data["action"]

    if action == "create group":
        await create_group(update, context, group_name)
    elif action == "join group":
        await join_group(update, context, group_name)

    await update.message.reply_text(
        "Done"
        # reply_markup=markup,
    )
    return CHOOSING_ACTION

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """End the conversation."""
    await update.message.reply_text(
        "Goodbye! Have a nice day!",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END

if __name__ == '__main__':
    main()
