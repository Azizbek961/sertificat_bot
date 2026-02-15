import random
from datetime import datetime

def make_test_public_id() -> str:
    return f"T{random.randint(10000, 99999)}"

def now_utc() -> datetime:
    return datetime.utcnow()

def seconds_between(a: datetime, b: datetime) -> int:
    return int((b - a).total_seconds())