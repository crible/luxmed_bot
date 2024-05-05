#!/usr/bin/env python
# pylint: disable=C0116,W0613

import logging
from datetime import timedelta, date
from luxmed_api import Language
from utils import get_visit_type, get_clinic_id
import booking_service
import os
from uuid import uuid4

# === BACKLOG ===
# BUG: Facilities ID and doctor ID doesn't work well togtheer. No terms returned.
# Add TWILLIO support
# Add status command
# Rewrite to normal scheduling, not telegram one.
# Add exception handling for Luxmed API and HTTP proxy
# Add how many days to look ahead
# Add release temp reservation in case of error (transaction like)
# Add one session support
# If first book in available terms failed - book next one
# Add time range selector for booking
# Add pobranie krwi
# Add emergency mode for 1 Sierpnia 8 


# FOR ANY CLINIC IN WARSAW DON't SHOW FAV DOCTOR
# MAKE AT FIRST ASKING FOR DOCTOR TYPE, THAN FAVOURITE OR NOT, than only show places.

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CallbackContext, CommandHandler, ConversationHandler, ContextTypes


# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)


doctors = {
    'Pediatr_sick': {
        'fav': {'id': 40404, 'name': 'MAŁGORZATA BIAŁA-GÓRNIAK'},
        'any': {'id': 0, 'name': 'Any available pediatr'}
    },
    'Pediatr_healthy': {
        'any': {'id': 0, 'name': 'Any available pediatr'},
        'fav': {'id': 40404, 'name': 'MAŁGORZATA BIAŁA-GÓRNIAK'}
    },
    'Stomatolog': {
        'fav': {'id': 41195, 'name': 'Olga Marczuk'},
        'any': {'id': 0, 'name': 'Any available stomatolog'}
    }
}

# User favorites (this could be dynamic based on user preferences stored elsewhere)
user_favorites = {
    'user_chat_id': {  # Replace 'user_chat_id' with the actual Telegram chat ID
        'Pediatr_healthy': 'any',  # User prefers the favorite pediatr
        'Pediatr_sick': 'fav',  # User prefers the favorite pediatr
        'Stomatolog': 'fav'  # User prefers any stomatolog
    }
}

PORT = int(os.environ.get('PORT', 8443))

# Define stages of conversation
CHILD, CLINIC, DOCTOR_TYPE, DOCTOR_NAME, CONFIRMATION = range(5)


async def monitor(context: CallbackContext) -> None:
    """Send the alarm message."""

    data = context.job.data

    user = data.user_data['username']
    password = data.user_data['password']
    clinic = data.user_data['clinic']
    doctor_type = data.user_data['doctor_type']
    chat_id = data.user_data['chat_id']

    available_terms = []

    parsed_from_date = date(2024, 6, 1)
    parsed_to_date = date(2024, 6, 6)
    parsed_language = Language.POLISH

    parsed_visit = get_visit_type(doctor_type)

    print("!!!!!!!! Parsed visit: %s", parsed_visit)

    logger.info(">>>>>> Checking available terms for luxmed user %s", user)
    
    available_terms = booking_service.get_available_terms(user, password, 1, 8914, parsed_from_date,
        parsed_to_date, 0,
        parsed_language, 13, 17175)

    if available_terms:
            logger.info("!!!!!!!!!! Found a termin, locking...")
            # res_lock = booking_service.book_term(user, password, available_terms[0])
            # if res_lock:
            #     msg = "Beep! You have booked an appointment! Check email for details."
            #     await context.bot.send_message(chat_id, text=msg)
            #     remove_job_if_exists(str(chat_id), context)
    else:
             logger.info(">>>>>>>> No available terms, continuing search...")


def remove_job_if_exists(name: str, context: CallbackContext) -> bool:
    logger.info("Stopping job...")
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def set_timer(update: Update, context: CallbackContext) -> None:
    chatid = update.callback_query.message.chat_id
    context.user_data['chat_id'] = chatid

    try:
        remove_job_if_exists(str(chatid), context)
        context.job_queue.run_repeating(monitor, interval=60, first=3, data = context, chat_id = chatid,  name=str(chatid))

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /set <seconds>')


def unset(update: Update, context: CallbackContext) -> None:
    chat_id = update.callback_query.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = 'Monitoring successfully cancelled!' if job_removed else 'You have no active monitoring enabled.'
    update.message.reply_text(text)


# Error handling function
def error(update, context):
    """Log Errors caused by Updates."""
    logging.error('Update "%s" caused error "%s"', update, context.error)


# Entry point for the conversation
async def start(update: Update, context: ContextTypes) -> int:
    keyboard = [
        [InlineKeyboardButton("Kiryl", callback_data='Kiryl')],
        [InlineKeyboardButton("Dzianis", callback_data='Dzianis')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Check if the function is called from a callback query
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text('For which child would you like to book an appointment?', reply_markup=reply_markup)
    else:
        await update.message.reply_text('For which child would you like to book an appointment?', reply_markup=reply_markup)
    return CHILD

# Choose clinic

async def clinic(update: Update, context: ContextTypes) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['child'] = query.data
    keyboard = [
        [InlineKeyboardButton("Klimczaka 1", callback_data='Klimczaka_1')],
        [InlineKeyboardButton("Any clinic in Warsaw",
                              callback_data='Anyw')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('Which clinic would you like to book?', reply_markup=reply_markup)
    return CLINIC

# Choose doctor type

async def doctor_type(update: Update, context: ContextTypes) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['clinic'] = query.data
    keyboard = [
        [InlineKeyboardButton("Pediatr healthy", callback_data='Pediatr_healthy')],
        [InlineKeyboardButton("Pediatr sick", callback_data='Pediatr_sick')],
        [InlineKeyboardButton("Stomatolog", callback_data='Stomatolog')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('Which type of doctor do you need?', reply_markup=reply_markup)
    return DOCTOR_TYPE


async def doctor_name(update, context):
    query = update.callback_query
    await query.answer()

    # Assume user_data already has 'child' and 'clinic' stored
    doctor_type = query.data
    context.user_data['doctor_type'] = doctor_type


    print(">>>>>>> DOCTOR TYPE: %s", doctor_type)
    # Check if there's a favorite set for this user
    chat_id = query.message.chat_id
    favorite_preference = user_favorites.get(str(chat_id), {}).get(doctor_type, 'any')

    # Prepare buttons for favorite or any doctor
    fav_doctor = doctors[doctor_type]['fav']
    any_doctor = doctors[doctor_type]['any']

    keyboard = [
        [InlineKeyboardButton(f"Favorite: {fav_doctor['name']}", callback_data=fav_doctor['id'])],
        [InlineKeyboardButton("Any Available", callback_data=any_doctor['id'])]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"Choose your doctor for {doctor_type}:", reply_markup=reply_markup)
    return DOCTOR_NAME

# Confirmation
async def confirmation(update: Update, context: ContextTypes) -> int:
    query = update.callback_query
    await query.answer()

    context.user_data['doctor_name'] = query.data
    context.user_data['doctor_type'] = doctor_type

    # BUG here: wrong doctor name during confirmation
    text = f"Confirm looking for {context.user_data['child']} at {
        context.user_data['clinic']} to see a {context.user_data['doctor_type']} - {query.data}?"

    keyboard = [
        [InlineKeyboardButton("Confirm", callback_data='Confirm')],
        [InlineKeyboardButton("Cancel", callback_data='Cancel')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return CONFIRMATION

# End conversation


async def end(update: Update, context: ContextTypes) -> int:
    query = update.callback_query

    await query.answer()
    if query.data == 'Confirm':
        text = 'Thank you! Your booking has been confirmed.'
        # Determine which credentials to use
        child_name = context.user_data['child'] 
        if child_name == "Kiryl":
            context.user_data['username']  = os.getenv("KIRYL_USERNAME")
            context.user_data['password']  = os.getenv("KIRYL_PASS")
        elif child_name == "Dzianis":
            context.user_data['username']  = os.getenv("DZIANIS_USERNAME")
            context.user_data['password']  = os.getenv("DZIANIS_PASS")
        else:
            # Handle error or unexpected child name
            await update.message.reply_text("Error: Unknown child name.")
            return
        
        set_timer(update, context)
    else:
        text = 'Booking has been cancelled.'
        logger.info("User %s canceled the booking.") 
        unset(update, context)

    await query.edit_message_text(text)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes):
    # Check if there is a job in the context
    chat_id = update.message.chat_id
    job = context.job_queue.get_jobs_by_name(str(chat_id))
    if job:
        job[0].schedule_removal()  # Stop the job if it exists
        await update.message.reply_text('Your scheduled job has been cancelled.')
    else:
        await update.message.reply_text('No active job to cancel.')

    return ConversationHandler.END  # Ends the conversation


def main() -> None:
    # Create the Updater and pass it your bot's token.
    load_dotenv()

    application = Application.builder().token(os.getenv('TG_TOKEN')).build()   
    
    # Create conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHILD: [CallbackQueryHandler(clinic)],
            CLINIC: [CallbackQueryHandler(doctor_type)],
            DOCTOR_TYPE: [CallbackQueryHandler(doctor_name)],
            DOCTOR_NAME: [CallbackQueryHandler(confirmation)],
            CONFIRMATION: [CallbackQueryHandler(end, pattern='^Confirm$'), CallbackQueryHandler(start, pattern='^Cancel$')]
        },
        fallbacks=[CommandHandler('cancel', end)]
    )

    application.add_handler(CommandHandler("cancel", cancel))


    # Add conversation handler to the dispatcher
    application.add_handler(conv_handler)
    application.add_error_handler(error)


    # General flow:
    # ask for kid
    # ask for service type
    # if service = stomatolog, ask for location and doctors
    # else ask for location,  ask for doctor whitelist or all.
    # show review screen and ask for confirmation
    #dispatcher.add_handler(CommandHandler('cancel', cancel))

    application.run_polling()

    logger.info("Luxmed Bot has just started.")

if __name__ == '__main__':
    main()
