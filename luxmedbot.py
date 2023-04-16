#!/usr/bin/env python
# pylint: disable=C0116,W0613

import logging
from datetime import timedelta, date
from dotenv import load_dotenv
from luxmed_api import Language
from utils import resolve_visit
import booking_service
import os
from uuid import uuid4

# === BACKLOG ===
# Add all Clinics or Klimczaka only
# Add finding closest clinic by GPS
# Add confirmation for reservation start
# Add stomatolog service
# Doctors blacklist/whitelist
# Make buttons inline with emojis
# Add exception handling for Luxmed API and HTTP proxy

# Add support for websockets

# Choose sleep time for kids to ignore
# Add release temp reservation in case of error (transaction like)
# Add random timeouts in given range
# Add one session support
# Add proper Request/Response objects mapping

# If first book in available terms failed - book next one
# Add time range selector for booking


from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackQueryHandler,
    CallbackContext,
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


# Define emoji codes
CHECK_MARK = u"\U00002705"  # Green check mark emoji
CROSS_MARK = u"\U0000274C"  # Red cross mark emoji

# Define doctor whitelist that we trust
DOCTOR_WHITELIST = {41195:'Olga Marczuk'}

CLINICS = {2259: 'Klimczaka', 0: 'Closest available', 1:'All in Warsaw'}

SERVICES = {8914: 'Stomatolog dzieci', 7408: 'Pediatr healthy', 7409: 'Pediatr sick'}

PORT = int(os.environ.get('PORT', 8443))

KID, CLINIC, SICK_OR_HEALTHY, CONFIRMATION = range(4)

def monitor(context: CallbackContext) -> None:
    """Send the alarm message."""

    job = context.job

    chat_id = context.job.context.user_data['chat_id']
    user = context.job.context.user_data['user'].lower()

    available_terms = []

    parsed_from_date = date.today()
    parsed_to_date = date.today() + timedelta(days=1)
    parsed_language = Language.POLISH

    parsed_visit = resolve_visit(context.job.context.user_data['visit'])

    
    logger.info("Checking available terms for luxmed user %s, visit type: %s", user, parsed_visit)
    available_terms = booking_service.get_available_terms(user, 1, parsed_visit, parsed_from_date,
        parsed_to_date, 0,
        parsed_language, 2259, None)
    
    if available_terms:
            logger.info("Found a termin, locking...")
            res_lock = booking_service.book_term(user, available_terms[0])
            if res_lock:     
                msg = "Beep! You have booked an appointment! Check email for details."
                context.bot.send_message(chat_id, text=msg)
            remove_job_if_exists(job.name, context)
    else:
            logger.info("No available terms, continuing search...")


def remove_job_if_exists(name: str, context: CallbackContext) -> bool:
    logger.info("Stopping job...")
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True

def set_timer(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id

    context.user_data['chat_id'] = chat_id

    try:
        due = int(100)
        if due < 0:
            update.message.reply_text('Sorry we can not go back to future!')
            return

        job_removed = remove_job_if_exists(str(chat_id), context)
        context.job_queue.run_repeating(monitor, due, 1, context=context, name=str(chat_id))

        text = 'Timer successfully set!'
        if job_removed:
            text += ' Old one was removed.'
        update.message.reply_text(text)

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /set <seconds>')

def unset(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = 'Monitoring successfully cancelled!' if job_removed else 'You have no active monitoring enabled.'
    update.message.reply_text(text)


def start(update: Update, context: CallbackContext) -> int:
    """Starts the conversation and asks the user."""
    keyboard = [[InlineKeyboardButton("Dzianis", callback_data='kid_Dzianis'),
                 InlineKeyboardButton("Kiryl", callback_data='kid_Kiryl')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Hi! Who is your kid?', reply_markup=reply_markup)
    return KID


def kid(update: Update, context: CallbackContext) -> int:
    reply_keyboard = [['Klimczaka']]
    logger.info("Kid: %s", update.message.text)

    user = update.message.text
    context.user_data["user"] = user

    update.message.reply_text(
        'OK! Please choose the clinic to book an appointment.',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Klimczaka?'
        ),
    )

    return CLINIC

def clinic(update: Update, context: CallbackContext) -> int:
    reply_keyboard = [['SICK', 'HEALTHY']]

    logger.info("Clinic: %s",update.message.text)

    update.message.reply_text(
        'Finally, choose type of service: SICK kids or HEALHTY kids.',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Sick or healthy?'
        ),
    )

    return SICK_OR_HEALTHY

def sick_or_healthy(update: Update, context: CallbackContext) -> int:

    logger.info("Visit type: %s",update.message.text)
    context.user_data["visit"] = update.message.text

    set_timer(update, context)

    update.message.reply_text(
        'Done! You will receive notification when I can book an appointment. Send /cancel if you would like to stop monitoring.',
    )

    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    
    unset(update, context)

    logger.info("User %s canceled the booking.", user.first_name)
    update.message.reply_text(
        'Bye! Please run /start again if you need to find free slot.', reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END

def confirmation():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{CHECK_MARK} Yes", callback_data='confirm'),
         InlineKeyboardButton(f"{CROSS_MARK} No", callback_data='cancel')]
    ])

def confirm(update, context):
    query = update.callback_query
    if query.data == 'confirm':
        query.answer()
        query.edit_message_text(f"{CHECK_MARK} Great! Your kid {context.user_data['kid']} will have an appointment soon.")
        return ConversationHandler.END
    elif query.data == 'cancel':
        query.answer()
        query.edit_message_text("Oops, let's start again. What is your kid's name?")
        return KID


def main() -> None:
    # Create the Updater and pass it your bot's token.
    load_dotenv()

    updater = Updater(os.getenv("TG_TOKEN"))
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            KID: [MessageHandler(Filters.regex('^(kid_Dzianis|kid_Kiryl)$'), kid)],
            CLINIC: [
                MessageHandler(Filters.regex('^(Klimczaka)$'), clinic)
                ],
            SICK_OR_HEALTHY: [MessageHandler(Filters.regex('^(SICK|HEALTHY)$'), sick_or_healthy)],
            CONFIRMATION: [CallbackQueryHandler(confirm)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(CommandHandler('cancel', cancel))

    updater.start_polling()

    logger.info("Luxmed Bot has just started.")

    updater.idle()


if __name__ == '__main__':
    main()
