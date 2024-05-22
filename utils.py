from enum import Enum
from datetime import datetime

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
