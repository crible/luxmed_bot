#!/usr/bin/env python
# pylint: disable=C0116,W0613

import logging
from datetime import timedelta, date
from dotenv import load_dotenv
from luxmed_api import Language
from utils import resolve_visit
import booking_service
import os

# === BACKLOG ===
# Add all Clinics or Klimczaka only
# Add stomatolog
# Add noip.net or ddns support
# Add code for Gajmed
# Remove config file code
# Choose sleep time for kids to ignore
# Add confirmation for reservation start
# Integrate with arduino
# Package for Debian and autostart
# Add buttons for how much days to look for ahead
# Make buttons inline with emojis
# Add exception handling for Luxmed API and HTTP proxy
# Add release temp reservation in case of error (transaction like)
# Add random timeouts in given range
# Add one session support
# Add proper Request/Response objects mapping
# Get rid of config loader module
# Doctos blacklist
# If first book in available terms failed - book next one
# Add time range selector for booking


from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

load_dotenv()

PORT = int(os.environ.get('PORT', 8443))

KID, CLINIC, SICK_OR_HEALTHY = range(3)

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
    
    ## 2259 - Klimczaka
    ## 44 - KEN93
    # serviceVariant 8914 -Stomatolog Dzieci
    # dooctorsIds = 41195 Olga Marczuk
    # city id - 1 - warszawa
    # id":7408 Paediatrician consultation - for healthy children
    # id":7409 Paediatrician consultation - for sick children"
    
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
    reply_keyboard = [['Kiryl', 'Dzianis']]

    user = update.message.from_user
    logger.info("User %s started the booking process.", user.first_name)

    update.message.reply_text(
        'Hi! Please choose a kid to search free visits.'
        'Send /cancel to stop talking to me.\n\n',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Kiryl or Dzianis?'
        ),
    )
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


def main() -> None:
    # Create the Updater and pass it your bot's token.
    updater = Updater(os.getenv("TG_TOKEN"))
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            KID: [MessageHandler(Filters.regex('^(Kiryl|Dzianis)$'), kid)],
            CLINIC: [
                MessageHandler(Filters.regex('^(Klimczaka)$'), clinic)
                ],
            SICK_OR_HEALTHY: [MessageHandler(Filters.regex('^(SICK|HEALTHY)$'), sick_or_healthy)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(CommandHandler('cancel', cancel))

    updater.start_polling()
    # Start the Bot
    # updater.start_webhook(listen="0.0.0.0",
                        #    port=int(PORT),
                        #    url_path=os.getenv("TG_TOKEN"),
                        #    webhook_url="https://rpitulia.ddns.net:8443/" + os.getenv("TG_TOKEN"))

    # updater.bot.setWebhook()
    ### 
    updater.idle()


if __name__ == '__main__':
    main()
