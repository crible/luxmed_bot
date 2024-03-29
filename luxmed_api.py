import random
import uuid
import os
from dotenv import load_dotenv
from datetime import datetime
from enum import Enum
import utils
import json
import requests


load_dotenv()


PROXY = { 
    'https' : "http://" + os.getenv('PROXY_USER') + ":" + os.getenv("PROXY_PASS") + "@pl.smartproxy.com:20000",
    'http' : "http://" + os.getenv('PROXY_USER') + ":" + os.getenv("PROXY_PASS") + "@pl.smartproxy.com:20000",
} 


class Language(Enum):
    POLISH = 10
    ENGLISH = 11


class LuxmedApiException(Exception):
    pass

__APP_VERSION = "4.19.0"
__CUSTOM_USER_AGENT = f"Patient Portal; {__APP_VERSION}; {str(uuid.uuid4())}; Android; {str(random.randint(23, 29))};" \
                      f" {str(uuid.uuid4())}"
__BASE_DOMAIN = "https://portalpacjenta.luxmed.pl"
__API_BASE_URL = f"{__BASE_DOMAIN}/PatientPortal/NewPortal"


def get_cities() -> []:
    print("Retrieving cities from the Luxmed API...")
    return __send_request_for_filters("/Dictionary/cities")


def get_services() -> []:
    print("Retrieving services from the Luxmed API...")
    return __send_request_for_filters("/Dictionary/serviceVariantsGroups")


def get_clinics_and_doctors(city_id: int, service_id: int) -> []:
    print("Retrieving clinics and doctors from the Luxmed API...")
    return __send_request_for_filters(
        f"/Dictionary/facilitiesAndDoctors?cityId={city_id}&serviceVariantId={service_id}")


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


def book_term(user, term) -> []:
    print("Temporary locking term... %s", term["visits"][0])

    session = __log_in(user)

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
        "date": utils.convert_date_to_string(term["date"]),
        "timeFrom": utils.convert_time_to_string(term["visits"][0]["timeFrom"]),
        "timeTo": utils.convert_time_to_string(term["visits"][0]["timeTo"]),
        "roomId": term["visits"][0]["roomId"],
        "serviceVariantId": term["visits"][0]["serviceId"],
        "facilityId": term["visits"][0]["facilityId"],
        "facilityName": term["visits"][0]["facilityName"],
        "scheduleId": term["visits"][0]["scheduleId"],
        "doctorId": term["visits"][0]["doctorId"],
        "doctor": term["visits"][0]["doctor"]
    }

    response_lock = session.post(f"{__API_BASE_URL}/reservation/lockterm", headers=headers, json=params_lock)

    __validate_response(response_lock)

    temp_reservation_id = response_lock.json()["value"]["temporaryReservationId"]

    ## REFACTOR ME
    params_confirm = {
        "date": utils.convert_date_to_string(term["date"]),
        "serviceVariantId": term["visits"][0]["serviceId"],
        "doctorId": term["visits"][0]["doctorId"],
        "facilityId": term["visits"][0]["facilityId"],
        "roomId": term["visits"][0]["roomId"],
        "temporaryReservationId": temp_reservation_id,
        "timeFrom": utils.convert_time_to_string(term["visits"][0]["timeFrom"]),
        "scheduleId": term["visits"][0]["scheduleId"],
        "valuation": response_lock.json()["value"]["valuations"][0]
    }

    response_confirm = confirm_term(session, token, params_confirm)

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


def get_terms(user, city_id: int, service_id: int, from_date: datetime, to_date: datetime, language: Language,
              clinic_id: int = None, doctor_id: int = None) -> []:
    print("Getting terms for given search parameters...")

    session = __log_in(user)

    headers = {
        "Accept": "application/json",
        "accept-language": "pl",
        "host": "portalpacjenta.luxmed.pl",
        "Content-Type": "application/json",
        "x-requested-with": "XMLHttpRequest",
    }
    params = {
        "cityId": city_id,
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

    return response.json()["termsForService"]["termsForDays"]


def __send_request_for_filters(uri: str):
    session = __log_in()
    headers = {
        "Accept": "application/json",
        "accept-language": "pl",
        "host": "portalpacjenta.luxmed.pl",
        "Content-Type": "application/json",
    }
    response = session.get(f"{__API_BASE_URL}{uri}", headers=headers, proxies=PROXY)
    __validate_response(response)
    return response.json()


def __log_in(user) -> requests.Session:
    access_token = __get_access_token(user)

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


def __get_access_token(user) -> str:
    headers = {"Api-Version": "2.0",
               "accept-language": "pl",
               "Content-Type": "application/x-www-form-urlencoded",
               "accept-encoding": "gzip",
               "x-api-client-identifier": "Android",
               "User-Agent": "okhttp/3.11.0",
               "Custom-User-Agent": __CUSTOM_USER_AGENT}

    # __CONFIG = config_loader.read_configuration(user, ["username", "password", "language"])

    # FIXME: need proper user/pass selector here
    authentication_body = {"username": os.getenv("KIRYL_USER"),
                           "password": os.getenv("KIRYL_PASS"),
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