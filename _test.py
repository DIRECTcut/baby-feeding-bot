import logging
import os
from datetime import datetime, timedelta
import pytz

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from db import SessionLocal
from models import FeedingLog, User

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_USERNAME_WHITELIST = os.environ['TELEGRAM_USERNAME_WHITELIST'].split(',')
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']

# Define states
CHOOSING_ACTION, CHOOSE_TIME_OPTION, CHOOSE_DAY, ENTER_TIME = range(4)
NOW_CALLBACK, FIVE_MINUTES_AGO_CALLBACK, TEN_MINUTES_AGO_CALLBACK, FIFTEEN_MINUTES_AGO_CALLBACK, THIRTY_MINUTES_AGO_CALLBACK, FORTY_FIVE_MINUTES_AGO_CALLBACK, ONE_HOUR_AGO_CALLBACK = range(7)

# Define inline keyboards
inline_keyboard = [
    [InlineKeyboardButton("Записать кормление", callback_data='log_feeding')],
]
inline_markup = InlineKeyboardMarkup(inline_keyboard)

time_option_keyboard = [
    [InlineKeyboardButton("Сейчас", callback_data=str(NOW_CALLBACK))],
    [InlineKeyboardButton("5 минут назад", callback_data=str(FIVE_MINUTES_AGO_CALLBACK))],
    [InlineKeyboardButton("10 минут назад", callback_data=str(TEN_MINUTES_AGO_CALLBACK))],
    [InlineKeyboardButton("15 минут назад", callback_data=str(FIFTEEN_MINUTES_AGO_CALLBACK))],
    [InlineKeyboardButton("30 минут назад", callback_data=str(THIRTY_MINUTES_AGO_CALLBACK))],
    [InlineKeyboardButton("45 минут назад", callback_data=str(FORTY_FIVE_MINUTES_AGO_CALLBACK))],
    [InlineKeyboardButton("1 час назад", callback_data=str(ONE_HOUR_AGO_CALLBACK))],
]
time_option_markup = InlineKeyboardMarkup(time_option_keyboard)

# Define the Argentina timezone
ARGENTINA_TZ = pytz.timezone('America/Argentina/Buenos_Aires')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask user for an action."""
    if update.effective_user.username not in TELEGRAM_USERNAME_WHITELIST:
        return update.message.reply_text("Nothing of interest here")

    await update.message.reply_text(
        "Привет! Давайте запишем новое кормление. Выберите опцию ниже:",
        reply_markup=inline_markup
    )
    return CHOOSING_ACTION

async def choose_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's choice of action."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'log_feeding':
        message = await query.edit_message_text("Когда произошло кормление?", reply_markup=time_option_markup)
        context.user_data['log_message_id'] = message.message_id
        return CHOOSE_TIME_OPTION

    await query.edit_message_text("Неверный выбор. Пожалуйста, выберите 'Записать кормление'.")
    return CHOOSING_ACTION

async def choose_time_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's choice of time option."""
    query = update.callback_query
    await query.answer()
    context.user_data["time_option"] = query.data
    
    time_deltas = {
        str(NOW_CALLBACK): timedelta(),
        str(FIVE_MINUTES_AGO_CALLBACK): timedelta(minutes=5),
        str(TEN_MINUTES_AGO_CALLBACK): timedelta(minutes=10),
        str(FIFTEEN_MINUTES_AGO_CALLBACK): timedelta(minutes=15),
        str(THIRTY_MINUTES_AGO_CALLBACK): timedelta(minutes=30),
        str(FORTY_FIVE_MINUTES_AGO_CALLBACK): timedelta(minutes=45),
        str(ONE_HOUR_AGO_CALLBACK): timedelta(hours=1),
    }

    if query.data in time_deltas:
        feeding_datetime_argentina = datetime.now(ARGENTINA_TZ) - time_deltas[query.data]
        feeding_datetime_utc = feeding_datetime_argentina.astimezone(pytz.utc)
        await log_feeding(update, context, feeding_datetime_utc)
        await delete_log_message(update, context)
        await send_message(update, 
            "Добавить еще?",
            reply_markup=inline_markup,
        )
        return CHOOSING_ACTION

async def log_feeding(update: Update, context: ContextTypes.DEFAULT_TYPE, feeding_datetime: datetime) -> None:
    """Function to log feeding into the database."""
    user_id = update.effective_user.id
    username = update.effective_user.username

    session = SessionLocal()

    # Fetch or create the user
    user = session.query(User).filter_by(username=username).first()
    if not user:
        user = User(id=user_id, username=username)
        session.add(user)
        session.commit()

    # Create a new feeding log
    feeding_log = FeedingLog(user_id=user.id, timestamp=feeding_datetime)
    session.add(feeding_log)
    session.commit()

    # Convert the feeding time back to Argentina timezone for display
    feeding_datetime_argentina = feeding_datetime.astimezone(ARGENTINA_TZ)
    formatted_time = feeding_datetime_argentina.strftime("%H:%M")
    await send_message(update, f'Кормление записано на {formatted_time}!')

async def send_message(update: Update, text: str, reply_markup=None) -> None:
    """Send a message to the user, handling both message and callback_query contexts."""
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup)

async def delete_log_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete the log message after logging the feeding."""
    if 'log_message_id' in context.user_data:
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=context.user_data['log_message_id'])
        except Exception as e:
            logger.error(f"Не удалось удалить сообщение: {e}")

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """End the conversation."""
    await update.message.reply_text(
        "До свидания! Хорошего дня!",
    )
    return ConversationHandler.END

def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add conversation handler with the states CHOOSING_ACTION, CHOOSE_TIME_OPTION, CHOOSE_DAY, and ENTER_TIME
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_ACTION: [
                CallbackQueryHandler(choose_action, pattern='^log_feeding$'),
            ],
            CHOOSE_TIME_OPTION: [
                CallbackQueryHandler(choose_time_option, pattern=f'^{str(NOW_CALLBACK)}|{str(FIVE_MINUTES_AGO_CALLBACK)}|{str(TEN_MINUTES_AGO_CALLBACK)}|{str(FIFTEEN_MINUTES_AGO_CALLBACK)}|{str(THIRTY_MINUTES_AGO_CALLBACK)}|{str(FORTY_FIVE_MINUTES_AGO_CALLBACK)}|{str(ONE_HOUR_AGO_CALLBACK)}$'),
            ],
        },
        fallbacks=[MessageHandler(filters.Regex("^Done$"), done)],
    )

    application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()
