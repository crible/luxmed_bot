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
# BUG: Facilities ID and doctor ID doesn't work well togtheer. No terms returned.
# Add TWILLIO support
# Add status command
# Rewrite to normal scheduling, not telegram one.
# Add all Clinics or Klimczaka only
# Add stomatolog service
# Add user/pass taking from YAML.
# Add finding closest clinic by GPS
# Add confirmation for reservation start
# Doctors blacklist/whitelist to yaml.
# Move all configuration state to yaml file.
# Make buttons inline with emojis
# Add exception handling for Luxmed API and HTTP proxy
# Add how many days to look ahead
# Add possibility to book ONLY term not earlier than 1 hour from now?
# Add support for websockets
# Migrate to new SDK version?
# Run as docker on RPi

# Choose sleep time for kids to ignore
# Add release temp reservation in case of error (transaction like)
# Add random timeouts in given range
# Add one session support
# Add proper Request/Response objects mapping

# If first book in available terms failed - book next one
# Add time range selector for booking
# Add pobranie krwi


from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
    CallbackQueryHandler
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)

# Define emoji codes
CHECK_MARK = u"\U00002705"  # Green check mark emoji
CROSS_MARK = u"\U0000274C"  # Red cross mark emoji
SMALL_KID =  u"\U0001F476"   # Small kid
BIG_KID =    u"\U0001F466"   # Big kid
HOSPITAL =   u"\U0001F3E5"   # Hospital

# Define doctor whitelist that we trust
DOCTOR_WHITELIST = {41195:'Olga Marczuk', 40404: 'MAŁGORZATA BIAŁA-GÓRNIAK'}

CLINICS = {2259: 'Klimczaka', 0: 'Closest available', 1: 'All in Warsaw'}

SERVICES = {8914: 'Stomatolog dzieci', 7408: 'Pediatr healthy', 7409: 'Pediatr sick'}

PORT = int(os.environ.get('PORT', 8443))

# States of conversation
KID, CLINIC, SICK_OR_HEALTHY, CONFIRMATION = range(4)

def monitor(context: CallbackContext) -> None:
    """Send the alarm message."""

    job = context.job

    chat_id = context.job.context.user_data['chat_id']
    user = context.job.context.user_data['user'].lower()

    available_terms = []

    parsed_from_date = date.today()
    parsed_to_date = date.today() + timedelta(days=3)
    parsed_language = Language.POLISH

    parsed_visit = resolve_visit(context.job.context.user_data['visit'])
    
    logger.info("Checking available terms for luxmed user %s, visit type: %s", user, parsed_visit)
    available_terms = booking_service.get_available_terms(user, 1, parsed_visit, parsed_from_date,
        parsed_to_date, 0,
        parsed_language, 288, 40404)
    
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
    keyboard = [[
        InlineKeyboardButton("Kiryl 👦", callback_data='Kiryl'),
        InlineKeyboardButton("Dzianis 👦", callback_data='Dzianis')
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    user = update.message.from_user
    logger.info("User %s started the booking process.", user.first_name)

    update.message.reply_text(
        'Hi! Please choose a kid to search free visits.'
        'Send /cancel to stop talking to me.\n\n',
        reply_markup=reply_markup,
    )

    return KID


def kid(update: Update, context: CallbackContext) -> int:
    keyboard = [[
        InlineKeyboardButton("Klimczaka 🏥", callback_data='Klimczaka')
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    logger.info("Kid: %s", update.message.text)

    user = update.message.text
    context.user_data["user"] = user

    update.message.reply_text(
        'OK! Please choose the clinic to book an appointment.',
        reply_markup=reply_markup,
    )

    return CLINIC

def clinic(update: Update, context: CallbackContext) -> int:
    keyboard = [[
        InlineKeyboardButton("SICK 😷", callback_data='SICK'),
        InlineKeyboardButton("HEALTHY 💪", callback_data='HEALTHY')
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    logger.info("Clinic: %s", update.message.text)

    update.message.reply_text(
        'Finally, choose type of service: SICK kids or HEALTHY kids.',
        reply_markup=reply_markup,
    )

    return SICK_OR_HEALTHY


def sick_or_healthy(update: Update, context: CallbackContext) -> int:
    logger.info("Visit type: %s", context.user_data["visit"])

    set_timer(update, context)

    update.message.reply_text(
        'Done! You will receive notification when I can book an appointment. Send /cancel if you would like to stop monitoring.',
    )

    return ConversationHandler.END

def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_data = context.user_data
    user_data["user"] = query.data

    if user_data.get("clinic"):
        user_data["visit"] = query.data

        set_timer(update, context)

        query.edit_message_text(
            text="Done! You will receive notification when I can book an appointment. Send /cancel if you would like to stop monitoring.",
        )
    else:
        user_data["clinic"] = query.data

        keyboard = [[
            InlineKeyboardButton("SICK 😷", callback_data='SICK'),
            InlineKeyboardButton("HEALTHY 💪", callback_data='HEALTHY')
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            text='Finally, choose type of service: SICK kids or HEALTHY kids.',
            reply_markup=reply_markup,
        )


def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user

    unset(update, context)

    logger.info("User %s canceled the booking.", user.first_name)
    update.message.reply_text(
        'Bye! Please run /start again if you need to find free slot.', reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END

# Add a new function to ask confirmation
def confirmation_question(update: Update, context: CallbackContext) -> int:
    keyboard = [[
        InlineKeyboardButton("Yes ✅", callback_data='yes'),
        InlineKeyboardButton("No ❌", callback_data='no')
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        'Are you sure you want to proceed?',
        reply_markup=reply_markup,
    )

    return CONFIRMATION

def main() -> None:
    # Create the Updater and pass it your bot's token.
    load_dotenv()

    updater = Updater(os.getenv("TG_TOKEN"))
    dispatcher = updater.dispatcher
    
    # Create conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            KID: [CallbackQueryHandler(kid)],
            CLINIC: [CallbackQueryHandler(clinic)],
            SICK_OR_HEALTHY: [CallbackQueryHandler(sick_or_healthy)],
            CONFIRMATION: [CallbackQueryHandler(confirmation_question)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Add conversation handler to the dispatcher
    dispatcher.add_handler(CallbackQueryHandler(confirmation_question))

    dispatcher.add_handler(CallbackQueryHandler(button))
    # Add error handling to the dispatcher

    # General flow:
    # ask for kid
    # ask for service type
    # if service = stomatolog, ask for location and doctors
    # else ask for location,  ask for doctor whitelist or all.
    # show review screen and ask for confirmation
    #dispatcher.add_handler(CommandHandler('cancel', cancel))

    updater.start_polling()

    logger.info("Luxmed Bot has just started.")

    updater.idle()


if __name__ == '__main__':
    main()
