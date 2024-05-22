import random
import uuid
import os
from datetime import datetime
from enum import Enum
from utils import convert_date_to_string, convert_string_to_date, convert_string_to_time, convert_time_to_string
import json
import requests
import logging


PROXY = { 
    'https' : "http://" + os.getenv('PROXY_USER') + ":" + os.getenv("PROXY_PASS") + "@pl.smartproxy.com:20000",
    'http' : "http://" + os.getenv('PROXY_USER') + ":" + os.getenv("PROXY_PASS") + "@pl.smartproxy.com:20000",
} 

class Language(Enum):
    POLISH = 10
    ENGLISH = 11

class LuxmedApiException(Exception):
    pass

__APP_VERSION = "4.29.0"
__CUSTOM_USER_AGENT = f"Patient Portal; {__APP_VERSION}; {str(uuid.uuid4())}; Android; {str(random.randint(23, 29))};" \
                      f" {str(uuid.uuid4())}"
__BASE_DOMAIN = "https://portalpacjenta.luxmed.pl"
__API_BASE_URL = f"{__BASE_DOMAIN}/PatientPortal/NewPortal"

logger = logging.getLogger(__name__)


def get_forgery_token(session):
    print("Getting forgery token...")

    headers = {
        "Accept": "application/json",
        "accept-language": "pl",
        "host": "portalpacjenta.luxmed.pl",
        "Content-Type": "application/json",
        "x-requested-with": "XMLHttpRequest",
    }

    response = session.get(f"{__API_BASE_URL}/security/getforgerytoken", headers=headers)

    __validate_response(response)

    return response.json()["token"]


def book_appointment(user, password, appointment):
    print("Temporary locking term... %s", appointment)

    session = __log_in(user, password)

    token = get_forgery_token(session)

    headers = {
        "Accept": "application/json",
        "accept-language": "pl",
        "host": "portalpacjenta.luxmed.pl",
        "Content-Type": "application/json",
        "x-requested-with": "XMLHttpRequest",
        "xsrf-token": token,
    }

    params_lock = {
        "date": convert_date_to_string(appointment["Date"]),
        "timeFrom": convert_time_to_string(convert_string_to_time(appointment["AppointmentDate"])),
        "timeTo": convert_time_to_string(appointment["dateTimeTo"]),
        "roomId": appointment["roomId"],
        "serviceVariantId": appointment["ServiceId"],
        "facilityId": appointment["facilityId"],
        "facilityName": appointment["ClinicPublicName"],
        "scheduleId": appointment["scheduleId"],
        "doctorId": appointment["doctorId"],
        "doctor": appointment["doctor"]
    }

    response_lock = session.post(f"{__API_BASE_URL}/reservation/lockterm", headers=headers, json=params_lock)

    __validate_response(response_lock)

    temp_reservation_id = response_lock.json()["value"]["temporaryReservationId"]

    if not temp_reservation_id:
        return None

    ## REFACTOR ME
    params_confirm = {
        "date": convert_date_to_string(appointment["Date"]),
        "serviceVariantId": appointment["ServiceId"],
        "doctorId": appointment["doctorId"],
        "facilityId": appointment["facilityId"],
        "temporaryReservationId": temp_reservation_id,
        "timeFrom": convert_time_to_string(convert_string_to_time(appointment["AppointmentDate"])),
        "scheduleId": appointment["scheduleId"],
        "valuation": response_lock.json()["value"]["valuations"][0]
    }

    response_confirm = confirm_term(session, token, params_confirm)

    if response_confirm["errors"]:
        logger.error(response_confirm["errors"][0])
        response_lock = session.post(f"{__API_BASE_URL}/reservation/releaseterm?reservationId={temp_reservation_id}", headers=headers, json={})
        __validate_response(response_lock)
        return None

    return response_confirm


def confirm_term(session, token, reservation_term) -> []:
    print("Confirming reservation...")

    headers = {
        "Accept": "application/json",
        "accept-language": "pl",
        "host": "portalpacjenta.luxmed.pl",
        "Content-Type": "application/json",
        "x-requested-with": "XMLHttpRequest",
        "xsrf-token": token,
    }

    response = session.post(f"{__API_BASE_URL}/reservation/confirm", headers=headers, json=reservation_term)
    __validate_response(response)

    return response.json() ### change it


def get_terms(user, password,  city_id: int, service_id: int, from_date: datetime, to_date: datetime, language: Language,
              clinic_id: int = None, doctor_id: int = None) -> []:
    print("Getting terms for given search parameters...")

    session = __log_in(user, password)

    headers = {
        "Accept": "application/json",
        "accept-language": "pl",
        "host": "portalpacjenta.luxmed.pl",
        "Content-Type": "application/json",
        "x-requested-with": "XMLHttpRequest",
    }
    params = {
        "searchPlace.id": city_id,
        "searchPlace.name": "Warszawa",
        "serviceVariantId": service_id,
        "languageId": language.value,
        "searchDateFrom": from_date.strftime("%Y-%m-%d"),
        "searchDateTo": to_date.strftime("%Y-%m-%d"),
        "facilitiesIds": clinic_id,
        "doctorsIds": doctor_id,
        "delocalized": False
    }

    response = session.get(f"{__API_BASE_URL}/terms/index", headers=headers, params=params)

    __validate_response(response)

    return response #.json()["termsForService"]["termsForDays"]



def __log_in(user, password) -> requests.Session:
    access_token = __get_access_token(user, password)

    session = requests.Session()
    session.proxies = PROXY


    headers = {
        "authorization": access_token,
        "accept-language": "pl",
        "upgrade-insecure-requests": "1",
        "host": "portalpacjenta.luxmed.pl",
        "Content-Type": "application/json",
        "x-requested-with": "pl.luxmed.pp",
        "Origin": __BASE_DOMAIN
    }
    params = {
        "app": "search",
        "client": 3,
        "paymentSupported": "true",
        "lang": "pl"
    }
    response = session.get(f"{__BASE_DOMAIN}/PatientPortal/Account/LogInToApp", headers=headers, params=params)

    if response.status_code != 200:
        raise LuxmedApiException("Unexpected response code, cannot log in")

    return session


def __get_access_token(user, password) -> str:
    headers = {"Api-Version": "2.0",
               "accept-language": "pl",
               "Content-Type": "application/x-www-form-urlencoded",
               "accept-encoding": "gzip",
               "x-api-client-identifier": "Android",
               "User-Agent": "okhttp/3.11.0",
               "Custom-User-Agent": __CUSTOM_USER_AGENT}

    # FIXME: need proper user/pass selector here
    authentication_body = {"username": user,
                           "password": password,
                           "grant_type": "password",
                           "account_id": str(uuid.uuid4())[:35],
                           "client_id": str(uuid.uuid4())
                           }

    response = requests.post(f"{__BASE_DOMAIN}/PatientPortalMobileAPI/api/token", headers=headers,
                             data=authentication_body, proxies=PROXY)

    __validate_response(response)

    return response.json()["access_token"]


def __validate_response(response: requests.Response):
    if response.status_code == 503:
        raise LuxmedApiException("Service unavailable, probably Luxmed server is down for maintenance")
    if "application/json" not in response.headers["Content-Type"]:
        raise LuxmedApiException("Something went wrong")
    if response.status_code != 200:
        raise LuxmedApiException(response.json())