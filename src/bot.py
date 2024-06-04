import logging
import os
from datetime import datetime, timedelta
import pytz
from tzlocal import get_localzone
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    CallbackContext,
    JobQueue
)

from env import (
    TELEGRAM_USERNAME_WHITELIST,
    TELEGRAM_TOKEN,
    NOTIFICATION_JOB_QUEUE_INTERVAL_SECONDS,
    NOTIFICATION_JOB_QUEUE_FIRST_SECONDS,
    NOTIFY_IF_UNFED_FOR_SECONDS
)

from log import logger

from db import SessionLocal
from models import FeedingLog, User

# Define states
CHOOSING_ACTION, CHOOSE_TIME_OPTION, CHOOSE_FEEDING_TYPE = range(3)
NOW_CALLBACK, FIVE_MINUTES_AGO_CALLBACK, TEN_MINUTES_AGO_CALLBACK, FIFTEEN_MINUTES_AGO_CALLBACK, THIRTY_MINUTES_AGO_CALLBACK, FORTY_FIVE_MINUTES_AGO_CALLBACK, ONE_HOUR_AGO_CALLBACK = range(7)
BOTTLE_CALLBACK, LEFT_BREAST_CALLBACK, RIGHT_BREAST_CALLBACK = range(7, 10)

# Define inline keyboards
inline_keyboard = [
    [InlineKeyboardButton("Записать кормление", callback_data='log_feeding')],
    [InlineKeyboardButton("Проверить последнее кормление", callback_data='check_last_feeding')],
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

feeding_type_keyboard = [
    [InlineKeyboardButton("Бутылочка", callback_data=str(BOTTLE_CALLBACK))],
    [InlineKeyboardButton("Левая грудь", callback_data=str(LEFT_BREAST_CALLBACK))],
    [InlineKeyboardButton("Правая грудь", callback_data=str(RIGHT_BREAST_CALLBACK))],
]
feeding_type_markup = InlineKeyboardMarkup(feeding_type_keyboard)

USER_TZ = pytz.timezone('America/Argentina/Buenos_Aires')
SERVER_TZ = get_localzone()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask user for an action."""
    if update.effective_user.username not in TELEGRAM_USERNAME_WHITELIST:
        return update.message.reply_text("Nothing of interest here")

    message = await update.message.reply_text(
        "Привет! Давайте запишем новое кормление или проверим последнее кормление. Выберите опцию ниже:",
        reply_markup=inline_markup
    )
    context.user_data['start_message_id'] = message.message_id
    return CHOOSING_ACTION

async def choose_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's choice of action."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'log_feeding':
        await query.edit_message_text("Когда произошло кормление?", reply_markup=time_option_markup)
        return CHOOSE_TIME_OPTION
    elif query.data == 'check_last_feeding':
        await check_last_feeding(update, context)
        await query.edit_message_text(
            "Привет! Давайте запишем новое кормление или проверим последнее кормление. Выберите опцию ниже:",
            reply_markup=inline_markup
        )
        return CHOOSING_ACTION

    await query.edit_message_text("Неверный выбор. Пожалуйста, выберите 'Записать кормление' или 'Проверить последнее кормление'.")
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
        feeding_datetime_argentina = datetime.now(USER_TZ) - time_deltas[query.data]
        feeding_datetime_server = feeding_datetime_argentina.astimezone(SERVER_TZ)
        context.user_data["feeding_datetime"] = feeding_datetime_server
        await query.edit_message_text("Выберите тип кормления:", reply_markup=feeding_type_markup)
        return CHOOSE_FEEDING_TYPE

async def choose_feeding_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's choice of feeding type."""
    query = update.callback_query
    await query.answer()
    context.user_data["feeding_type"] = query.data
    
    feeding_datetime = context.user_data["feeding_datetime"]
    feeding_type = query.data

    await log_feeding(update, context, feeding_datetime, feeding_type)
    await delete_log_message(update, context)
    await send_message(update, 
        "Добавить еще?",
        reply_markup=inline_markup,
    )
    return CHOOSING_ACTION

async def log_feeding(update: Update, context: ContextTypes.DEFAULT_TYPE, feeding_datetime: datetime, feeding_type: str) -> None:
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
    feeding_log = FeedingLog(user_id=user.id, timestamp=feeding_datetime, feeding_type=feeding_type)
    session.add(feeding_log)
    session.commit()

    # Convert the feeding time back to Argentina timezone for display
    feeding_datetime_argentina = feeding_datetime.astimezone(USER_TZ)
    formatted_time = feeding_datetime_argentina.strftime("%H:%M")
    feeding_type_text = {
        str(BOTTLE_CALLBACK): "Бутылочка",
        str(LEFT_BREAST_CALLBACK): "Левая грудь",
        str(RIGHT_BREAST_CALLBACK): "Правая грудь"
    }[feeding_type]
    await send_message(update, f'Кормление записано на {formatted_time} ({feeding_type_text})!')

async def check_last_feeding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Function to check and display the last feeding log."""
    user_id = update.effective_user.id
    username = update.effective_user.username

    session = SessionLocal()

    # Fetch the last feeding log for the user
    last_feeding_log = session.query(FeedingLog).join(User).filter(User.username == username).order_by(FeedingLog.timestamp.desc()).first()
    
    if last_feeding_log:
        # Convert the feeding time back to Argentina timezone for display
        feeding_datetime_argentina = last_feeding_log.timestamp.astimezone(USER_TZ)
        formatted_time = feeding_datetime_argentina.strftime("%H:%M")
        time_elapsed = datetime.now(USER_TZ) - feeding_datetime_argentina
        hours, remainder = divmod(time_elapsed.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        feeding_type_text = {
            "7": "Бутылочка",
            "8": "Левая грудь",
            "9": "Правая грудь"
        }[last_feeding_log.feeding_type]
        text = f'Последнее кормление было в {formatted_time} ({feeding_type_text}). Прошло времени: {hours} часов {minutes} минут.'
    else:
        text = "Нет записей о кормлении."

    await send_message(update, text)
    await send_message(update,
        "Привет! Давайте запишем новое кормление или проверим последнее кормление. Выберите опцию ниже:",
        reply_markup=inline_markup
    )

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

async def notify_users(context: CallbackContext) -> None:
    """Notify users if the feeding interval has passed."""
    session = SessionLocal()
    now = datetime.now(SERVER_TZ)  # Ensure `now` is timezone-aware
    notification_interval = timedelta(seconds=NOTIFY_IF_UNFED_FOR_SECONDS)

    for username in TELEGRAM_USERNAME_WHITELIST:
        user = session.query(User).filter_by(username=username).first()
        # FIXME: early return
        if user:
            last_feeding_log = session.query(FeedingLog).filter_by(user_id=user.id).order_by(FeedingLog.timestamp.desc()).first()
            if last_feeding_log:
                last_feeding_time = last_feeding_log.timestamp

                # Ensure `last_feeding_time` is timezone-aware
                if last_feeding_time.tzinfo is None:
                    last_feeding_time = last_feeding_time.replace(tzinfo=ZoneInfo(str(SERVER_TZ)))

                time_passed = now - last_feeding_time
                time_passed_minutes = divmod(time_passed.total_seconds(), 60)[0]  # Convert to minutes

                if time_passed > notification_interval:
                    # Convert the time to Argentina timezone for display
                    last_feeding_time_argentina = last_feeding_time.astimezone(USER_TZ)
                    formatted_time = last_feeding_time_argentina.strftime("%H:%M")
                    await context.bot.send_message(
                        chat_id=user.id,
                        text=f'Прошло {int(time_passed_minutes)} минут с последнего кормления в {formatted_time}. Пожалуйста, проверьте.'
                    )

def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add conversation handler with the states CHOOSING_ACTION, CHOOSE_TIME_OPTION, and CHOOSE_FEEDING_TYPE
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_ACTION: [
                CallbackQueryHandler(choose_action, pattern='^log_feeding$|^check_last_feeding$'),
            ],
            CHOOSE_TIME_OPTION: [
                CallbackQueryHandler(choose_time_option, pattern=f'^{str(NOW_CALLBACK)}|{str(FIVE_MINUTES_AGO_CALLBACK)}|{str(TEN_MINUTES_AGO_CALLBACK)}|{str(FIFTEEN_MINUTES_AGO_CALLBACK)}|{str(THIRTY_MINUTES_AGO_CALLBACK)}|{str(FORTY_FIVE_MINUTES_AGO_CALLBACK)}|{str(ONE_HOUR_AGO_CALLBACK)}$'),
            ],
            CHOOSE_FEEDING_TYPE: [
                CallbackQueryHandler(choose_feeding_type, pattern=f'^{str(BOTTLE_CALLBACK)}|{str(LEFT_BREAST_CALLBACK)}|{str(RIGHT_BREAST_CALLBACK)}$'),
            ],
        },
        fallbacks=[MessageHandler(filters.Regex("^Done$"), done)],
    )

    application.add_handler(conv_handler)

    # Initialize job queue
    job_queue = application.job_queue
    if job_queue is not None:
        job_queue.run_repeating(notify_users, interval=timedelta(seconds=NOTIFICATION_JOB_QUEUE_INTERVAL_SECONDS), first=timedelta(seconds=NOTIFICATION_JOB_QUEUE_FIRST_SECONDS))
    else:
        logger.error("Job queue is not initialized properly.")

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()
