from datetime import datetime
from typing import Callable, Any, Union
import logging
import luxmed_api
import utils
from luxmed_api import Language

from typing import List


logger = logging.getLogger(__name__)

def _parseVisitsNewPortal(data) -> List[dict]:
        appointments = []
        (clinicIds, doctorIds) = (2086, 41195) #
        content = data.json()
        for termForDay in content["termsForService"]["termsForDays"]:
            for term in termForDay["terms"]:
                doctor = term['doctor']

                if doctorIds != '-1' and str(doctor['id']) != str(doctorIds):
                    continue
                if clinicIds != '-1' and str(term['clinicId']) != str(clinicIds):
                    continue

                appointments.append(
                    {
                        'Date': utils.convert_string_to_date(termForDay['day']),
                        'AppointmentDate': term['dateTimeFrom'],
                        'dateTimeTo': utils.convert_string_to_time(term['dateTimeTo']),
                        'facilityId': term['clinicId'],
                        'ClinicPublicName': term['clinic'],
                        'DoctorName': f'{doctor["academicTitle"]} {doctor["firstName"]} {doctor["lastName"]}',
                        'doctorId': doctor['id'],
                        'doctor': term['doctor'],
                        'ServiceId': term['serviceId'],
                        "scheduleId": term["scheduleId"],
                        "partOfDay": term["partOfDay"],
                        "roomId": term["roomId"],

                    }
                )
        return appointments


def get_available_terms(user, password, city_id: int, service_id: int, from_date: datetime, to_date: datetime, part_of_day: int,
                        language: Language, clinic_id: int = None, doctor_id: int = None):

    result = luxmed_api.get_terms(user, password, city_id, service_id, from_date, to_date, language, clinic_id, doctor_id)

    return [*filter(
            lambda a: datetime.fromisoformat(a['AppointmentDate']).date() <= to_date,
            _parseVisitsNewPortal(result))]


def book_appointment(user, password, appointment) -> {}:
    result = luxmed_api.book_appointment(user, password, appointment)
    return result

