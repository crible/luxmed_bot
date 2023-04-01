from enum import Enum
from datetime import datetime

class SickOrHealthy(Enum):
    SICK = 7409
    HEALTHY = 7408

    def __str__(self):
        return '%s' % self.value

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

def resolve_visit(visit: str) -> SickOrHealthy:
    return SickOrHealthy.SICK if visit == "SICK" else SickOrHealthy.HEALTHY