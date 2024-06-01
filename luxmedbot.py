#!/usr/bin/env python
# pylint: disable=C0116,W0613

import logging
from datetime import timedelta, date
from luxmed_api import Language
import booking_service
import os
from subprocess import call

from uuid import uuid4
import coloredlogs
import schedule
import time
from telegram_send import send as t_send

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

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

coloredlogs.install(level="INFO")
logger = logging.getLogger(__name__)


parsed_from_date = date(2024, 6, 3)
parsed_to_date = date(2024, 6, 7)

parsed_language = Language.POLISH

def check():
    try:
        user = os.getenv("LUXMED_USERNAME")
        password = os.getenv("LUXMED_PASS")
        doctorId = os.getenv("LUXMED_DOCTOR_ID")
        locationId = os.getenv("LUXMED_LOCATION_ID")
        serviceId = os.getenv("LUXMED_SERVICE_ID")

        appointments = booking_service.get_available_terms(user, password, 1, serviceId, parsed_from_date,
            parsed_to_date, 0,
            parsed_language, locationId, doctorId)
        
        if not appointments:
            logger.info("No appointments found. Trying again...")
            return
        else:
            for appointment in appointments:
                logger.info(
                    "Appointment found! {AppointmentDate} at {ClinicPublicName} - {DoctorName}".format(
                        **appointment))
                call(["telegram-send", "New visit! {AppointmentDate} at {ClinicPublicName} - {DoctorName}".format(**appointment)])
            schedule.clear()            
    except Exception as e:
        logger.error(e)


if __name__ == '__main__':
    logger.info("Luxmed Bot has just started")
    check()
    schedule.every(60).seconds.do(check)

    while True:
        schedule.run_pending()
        time.sleep(1)