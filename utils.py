from enum import Enum
from datetime import datetime

#FIXME - use structure as in get_clinic
class SickOrHealthy(Enum):
    SICK = 7409
    HEALTHY = 7408

    def __str__(self):
        return '%s' % self.value

def get_clinic_id(clinic_name):
    """
    Maps a clinic name to a clinic ID.

    Args:
    clinic_name (str): The name of the clinic.

    Returns:
    int: The clinic ID corresponding to the clinic name.
    """
    # Map for clinic names to their IDs
    clinic_ids = {
        "Klimczaka_1": 288,
        "Rzecypospolitej_1": 13
    }

    # Return the clinic ID if it exists in the dictionary, otherwise return 0
    return clinic_ids.get(clinic_name, 0)


def convert_string_to_time(date: str) -> datetime.time:
    return datetime.strptime(date, "%Y-%m-%dT%H:%M:%S").time()

def convert_time_to_string(date: datetime.time) -> str:
    return date.strftime("%H:%M")

def convert_date_to_string(date: datetime.date) -> str:
    return date.strftime("%Y-%m-%dT%H:%M:%S")

def convert_string_to_date(date: str) -> datetime.date:
    return datetime.strptime(date, "%Y-%m-%dT%H:%M:%S").date()

def make_date_human_ready(date: datetime.date) -> str:
    return date.strftime("%d.%m.%Y")

def make_time_human_ready(date: datetime.date) -> str:
    return date.strftime("%H:%M")

def get_visit_type(doctor_type):
    service_ids = {
        'Stomatolog': 8914,
        'Pediatr_healthy': 7408,
        'Pediatr_healthy': 7409
    }

    # Get proper service id from the data
    return service_ids.get(doctor_type, 0)