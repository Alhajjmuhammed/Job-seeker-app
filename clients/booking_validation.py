"""
Shared validation for creating a service request.

The web form and the mobile API are two independent implementations of the
same booking. Keeping the rules here stops them drifting apart - they had
already drifted far enough that the web form accepted a booking for -5 workers
and a start date a month in the past, while the API had begun refusing both.
"""
from datetime import date, datetime

from django.utils import timezone

# A booking is for a crew, not a workforce. Anything above this is a mistake or
# abuse, and the client is charged per worker.
MAX_WORKERS_PER_REQUEST = 20

# SQLite silently ignores max_length; PostgreSQL raises. Without these checks an
# over-long title is a 500 in production and a stored monstrosity in dev.
TEXT_LIMITS = (
    ('title', 200),
    ('location', 255),
    ('city', 100),
    ('description', 5000),
    ('client_notes', 2000),
)


def as_date(value):
    """Coerce a request value to a date, or None if it is not one."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value)[:10], '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None


def clean_workers_needed(raw):
    """Return (workers_needed, error). Never silently coerces nonsense."""
    if raw in (None, ''):
        return 1, None
    try:
        workers_needed = int(raw)
    except (TypeError, ValueError):
        return None, 'Number of workers must be a whole number.'
    if workers_needed < 1 or workers_needed > MAX_WORKERS_PER_REQUEST:
        return None, (f'Number of workers must be between 1 and '
                      f'{MAX_WORKERS_PER_REQUEST}.')
    return workers_needed, None


def check_text_lengths(data):
    """Return an error message for the first over-long field, else None."""
    for field, limit in TEXT_LIMITS:
        value = data.get(field)
        if value is not None and len(str(value)) > limit:
            return (f'{field.replace("_", " ").capitalize()} must be at most '
                    f'{limit} characters.')
    return None


def check_dates(start, end, preferred=None):
    """Validate a booking's date range. Returns an error message or None."""
    start, end, preferred = as_date(start), as_date(end), as_date(preferred)
    if start and end and end < start:
        return 'The end date must not be before the start date.'
    today = timezone.localdate()
    if start and start < today:
        return 'The start date cannot be in the past.'
    if preferred and preferred < today:
        return 'The preferred date cannot be in the past.'
    return None
