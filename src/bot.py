import logging
import os
from datetime import datetime, timedelta
import pytz
from tzlocal import get_localzone
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, KeyboardButton
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

# Define states and callbacks
(
    CHOOSING_ACTION,
    CHOOSE_TIME_OPTION,
    CHOOSE_FEEDING_TYPE,

    NOW_CALLBACK,
    FIVE_MINUTES_AGO_CALLBACK,
    FIFTEEN_MINUTES_AGO_CALLBACK,
    THIRTY_MINUTES_AGO_CALLBACK,
    FORTY_FIVE_MINUTES_AGO_CALLBACK,
    ONE_HOUR_AGO_CALLBACK,

    BOTTLE_CALLBACK,
    LEFT_BREAST_CALLBACK,
    RIGHT_BREAST_CALLBACK,

    CANCEL_CALLBACK,
    BACK_CALLBACK
) = range(14)

# Define common dictionaries
FEEDING_TYPE_TEXT = {
    str(BOTTLE_CALLBACK): "Бутылочка",
    str(LEFT_BREAST_CALLBACK): "Левая грудь",
    str(RIGHT_BREAST_CALLBACK): "Правая грудь"
}

TIME_DELTAS = {
    str(NOW_CALLBACK): timedelta(),
    str(FIVE_MINUTES_AGO_CALLBACK): timedelta(minutes=5),
    str(FIFTEEN_MINUTES_AGO_CALLBACK): timedelta(minutes=15),
    str(THIRTY_MINUTES_AGO_CALLBACK): timedelta(minutes=30),
    str(FORTY_FIVE_MINUTES_AGO_CALLBACK): timedelta(minutes=45),
    str(ONE_HOUR_AGO_CALLBACK): timedelta(hours=1),
}

# Define inline keyboards
time_option_keyboard = [
    [InlineKeyboardButton("Сейчас", callback_data=str(NOW_CALLBACK))],
    [InlineKeyboardButton("5 минут назад", callback_data=str(FIVE_MINUTES_AGO_CALLBACK))],
    [InlineKeyboardButton("15 минут назад", callback_data=str(FIFTEEN_MINUTES_AGO_CALLBACK))],
    [InlineKeyboardButton("30 минут назад", callback_data=str(THIRTY_MINUTES_AGO_CALLBACK))],
    [InlineKeyboardButton("45 минут назад", callback_data=str(FORTY_FIVE_MINUTES_AGO_CALLBACK))],
    [InlineKeyboardButton("1 час назад", callback_data=str(ONE_HOUR_AGO_CALLBACK))],
    [InlineKeyboardButton("Oтмена", callback_data=str(CANCEL_CALLBACK))],
]
time_option_markup = InlineKeyboardMarkup(time_option_keyboard)

feeding_type_keyboard = [
    [InlineKeyboardButton("Бутылочка", callback_data=str(BOTTLE_CALLBACK))],
    [InlineKeyboardButton("Левая грудь", callback_data=str(LEFT_BREAST_CALLBACK))],
    [InlineKeyboardButton("Правая грудь", callback_data=str(RIGHT_BREAST_CALLBACK))],
    [InlineKeyboardButton("Назад", callback_data=str(BACK_CALLBACK))],
]
feeding_type_markup = InlineKeyboardMarkup(feeding_type_keyboard)

# Define reply keyboard
reply_keyboard = [
    [KeyboardButton("Записать кормление")],
    [KeyboardButton("Проверить последнее кормление")],
    [KeyboardButton("Статистика за последние 24 часа")],  # New button for 24-hour stats
]
reply_markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False, resize_keyboard=True)

USER_TZ = pytz.timezone('America/Argentina/Buenos_Aires')
SERVER_TZ = get_localzone()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask user for an action."""
    if update.effective_user.username not in TELEGRAM_USERNAME_WHITELIST:
        return update.message.reply_text("Nothing of interest here")

    message = await update.message.reply_text(
        "Привет! Давайте запишем новое кормление или проверим последнее кормление. Выберите опцию ниже:",
        reply_markup=reply_markup
    )
    context.user_data['start_message_id'] = message.message_id
    return CHOOSING_ACTION

async def choose_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's choice of action."""
    text = update.message.text
    
    if text == 'Записать кормление':
        # Reset context data related to time option and feeding type
        context.user_data.pop('time_option_message_id', None)
        context.user_data.pop('feeding_type_message_id', None)

        message = await update.message.reply_text("Когда произошло кормление?", reply_markup=time_option_markup)
        context.user_data['time_option_message_id'] = message.message_id
        return CHOOSE_TIME_OPTION
    elif text == 'Проверить последнее кормление':
        await check_last_feeding(update, context)
        return CHOOSING_ACTION
    elif text == 'Статистика за последние 24 часа':
        await display_24h_stats(update, context)
        return CHOOSING_ACTION

    await update.message.reply_text("Неверный выбор. Пожалуйста, выберите 'Записать кормление', 'Проверить последнее кормление' или 'Статистика за последние 24 часа'.")
    return CHOOSING_ACTION

async def choose_time_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's choice of time option."""
    query = update.callback_query
    await query.answer()
    context.user_data["time_option"] = query.data
    
    if query.data == str(CANCEL_CALLBACK):
        if 'time_option_message_id' in context.user_data:
            try:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=context.user_data['time_option_message_id'])
            except Exception as e:
                logger.error(f"Failed to remove message: {e}")

        return CHOOSING_ACTION

    if query.data in TIME_DELTAS:
        feeding_datetime_argentina = datetime.now(USER_TZ) - TIME_DELTAS[query.data]
        feeding_datetime_server = feeding_datetime_argentina.astimezone(SERVER_TZ)
        context.user_data["feeding_datetime"] = feeding_datetime_server
        message = await query.edit_message_text("Выберите тип кормления:", reply_markup=feeding_type_markup)
        context.user_data['feeding_type_message_id'] = message.message_id
        return CHOOSE_FEEDING_TYPE

async def choose_feeding_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's choice of feeding type."""
    query = update.callback_query
    await query.answer()
    
    if query.data == str(BACK_CALLBACK):
        message = await query.edit_message_text("Когда произошло кормление?", reply_markup=time_option_markup)
        context.user_data['time_option_message_id'] = message.message_id
        return CHOOSE_TIME_OPTION
    
    context.user_data["feeding_type"] = query.data
    
    feeding_datetime = context.user_data["feeding_datetime"]
    feeding_type = query.data

    await log_feeding(update, context, feeding_datetime, feeding_type)
    await delete_log_message(update, context)
    await delete_feeding_type_message(update, context)

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
    feeding_type_text = FEEDING_TYPE_TEXT.get(feeding_type, "Неизвестный тип")
    await send_message(update, f'Кормление записано на {formatted_time} ({feeding_type_text})!')

async def check_last_feeding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Function to check and display the last feeding log."""
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
        feeding_type_text = FEEDING_TYPE_TEXT.get(last_feeding_log.feeding_type, "Неизвестный тип")
        text = f'Последнее кормление было в {formatted_time} ({feeding_type_text}). Прошло времени: {hours} часов {minutes} минут.'
    else:
        text = "Нет записей о кормлении."

    await send_message(update, text)

async def display_24h_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Function to display feeding stats for the last 24 hours."""
    username = update.effective_user.username

    session = SessionLocal()
    now = datetime.now(SERVER_TZ)
    twenty_four_hours_ago = now - timedelta(hours=24)

    # Fetch the feeding logs for the last 24 hours
    feeding_logs = session.query(FeedingLog).join(User).filter(User.username == username, FeedingLog.timestamp >= twenty_four_hours_ago).order_by(FeedingLog.timestamp).all()

    if feeding_logs:
        stats_text = "Статистика кормлений за последние 24 часа:\n\n"
        feeding_counts = {str(BOTTLE_CALLBACK): 0, str(LEFT_BREAST_CALLBACK): 0, str(RIGHT_BREAST_CALLBACK): 0}
        previous_feeding_time = None

        for log in feeding_logs:
            feeding_datetime_argentina = log.timestamp.astimezone(USER_TZ)
            formatted_time = feeding_datetime_argentina.strftime("%H:%M")
            feeding_type_text = FEEDING_TYPE_TEXT.get(log.feeding_type, "Неизвестный тип")
            stats_text += f'{formatted_time} - {feeding_type_text}\n'
            feeding_counts[log.feeding_type] += 1

            if previous_feeding_time:
                time_between_feedings = feeding_datetime_argentina - previous_feeding_time
                stats_text += f'Время между кормлениями: {time_between_feedings}\n'
            previous_feeding_time = feeding_datetime_argentina

        stats_text += "\nКоличество кормлений по типам:\n"
        stats_text += f'Бутылочка: {feeding_counts[str(BOTTLE_CALLBACK)]}\n'
        stats_text += f'Левая грудь: {feeding_counts[str(LEFT_BREAST_CALLBACK)]}\n'
        stats_text += f'Правая грудь: {feeding_counts[str(RIGHT_BREAST_CALLBACK)]}\n'
    else:
        stats_text = "Нет записей о кормлении за последние 24 часа."

    await send_message(update, stats_text)

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
            logger.error(f"Failed to remove message: {e}")

async def delete_feeding_type_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete the feeding type message after the user selects a feeding type."""
    if 'feeding_type_message_id' in context.user_data:
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=context.user_data['feeding_type_message_id'])
        except Exception as e:
            logger.error(f"Failed to remove message: {e}")

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
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_action),
            ],
            CHOOSE_TIME_OPTION: [
                CallbackQueryHandler(choose_time_option, pattern=f'^{str(NOW_CALLBACK)}$|^{str(FIVE_MINUTES_AGO_CALLBACK)}$|^{str(FIFTEEN_MINUTES_AGO_CALLBACK)}$|^{str(THIRTY_MINUTES_AGO_CALLBACK)}$|^{str(FORTY_FIVE_MINUTES_AGO_CALLBACK)}$|^{str(ONE_HOUR_AGO_CALLBACK)}$|^{str(CANCEL_CALLBACK)}'),
            ],
            CHOOSE_FEEDING_TYPE: [
                CallbackQueryHandler(choose_feeding_type, pattern=f'^{str(BOTTLE_CALLBACK)}$|^{str(LEFT_BREAST_CALLBACK)}$|^{str(RIGHT_BREAST_CALLBACK)}$|^{str(BACK_CALLBACK)}'),
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
