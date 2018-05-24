import dateparser
from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse

from .exceptions import TimestampParseError


earliest_time = isoparse('0001-01-01T00+00:00')


def get_timestamp():
    """returns a timezone aware `datetime` object for `now`.

    :return datetime:

    >>> from snapshotbackup.timestamps import get_timestamp
    >>> get_timestamp()
    datetime.datetime(...)
    """
    return datetime.now(timezone.utc).replace(microsecond=0).astimezone()


def parse_timestamp(string):
    """parse an iso timestamp string, return corresponding `datetime` object.

    :param str string: iso timestamp
    :return datetime datetime:
    :raise TimestampParseError:

    >>> from snapshotbackup.timestamps import parse_timestamp
    >>> parse_timestamp('1989-11-09')
    datetime.datetime(1989, 11, 9, 0, 0)
    >>> parse_timestamp('some random string')
    Traceback (most recent call last):
    ...
    snapshotbackup.exceptions.TimestampParseError: ...
    """
    try:
        return isoparse(string)
    except (ValueError, OverflowError) as e:
        # ValueError: invalid date
        # OverflowError: parsed date exceeds the largest valid C integer
        raise TimestampParseError(str(e), error=e) from e


def parse_human_readable_relative_dates(string: str) -> datetime:
    """parse human readable relative dates.

    :param str string:
    :return datetime datetime:
    :raise TimestampParseError:

    >>> from snapshotbackup.timestamps import parse_human_readable_relative_dates
    >>> parse_human_readable_relative_dates('1 day ago')
    datetime.datetime(...)
    >>> parse_human_readable_relative_dates('anytime')
    Traceback (most recent call last):
    ...
    snapshotbackup.exceptions.TimestampParseError: ...
    """
    date = dateparser.parse(string, settings={'RETURN_AS_TIMEZONE_AWARE': True})
    if date:
        return date
    raise TimestampParseError(f'could not parse `{string}`')


def is_timestamp(string):
    """test if given string is a valid iso timestamp.

    :param str string:
    :return bool: if given string could be parsed as valid timestamp

    >>> from snapshotbackup.timestamps import is_timestamp
    >>> is_timestamp('1989-11-09')
    True
    >>> is_timestamp('some random string')
    False
    """
    try:
        parse_timestamp(string)
        return True
    except TimestampParseError:
        return False


def is_same_hour(date1: datetime, date2: datetime) -> bool:
    """test if given datetime objects are in the same hour.

    :param datetime.datetime date1:
    :param datetime.datetime date2:
    :return bool:

    >>> from snapshotbackup.timestamps import is_same_hour
    >>> from datetime import datetime
    >>> is_same_hour(datetime(1970, 1, 1, 1), datetime(1970, 1, 1, 1, 59, 59))
    True
    >>> is_same_hour(datetime(1970, 1, 1, 1), datetime(1970, 1, 1, 2))
    False
    >>> is_same_hour(datetime(1970, 1, 1, 1), datetime(1970, 1, 2, 1))
    False
    """
    assert(date1 < date2)
    return date1.hour == date2.hour and date2 - date1 < timedelta(hours=1)


def is_same_day(date1: datetime, date2: datetime) -> bool:
    """test if given datetime objects are on the same day.

    :param datetime.datetime date1:
    :param datetime.datetime date2:
    :return bool:

    >>> from snapshotbackup.timestamps import is_same_day
    >>> from datetime import datetime
    >>> is_same_day(datetime(1970, 1, 1), datetime(1970, 1, 1, 23, 59, 59))
    True
    >>> is_same_day(datetime(1970, 1, 1), datetime(1970, 1, 2))
    False
    >>> is_same_day(datetime(1970, 1, 1), datetime(1970, 2, 1))
    False
    """
    assert(date1 < date2)
    return date1.day == date2.day and date2 - date1 < timedelta(days=1)


def is_same_week(date1: datetime, date2: datetime) -> bool:
    """test if given datetime objects are in the same week.

    :param datetime.datetime date1:
    :param datetime.datetime date2:
    :return bool:

    >>> from snapshotbackup.timestamps import is_same_week
    >>> from datetime import datetime
    >>> is_same_week(datetime(1970, 1, 1), datetime(1970, 1, 4))
    True
    >>> is_same_week(datetime(1970, 1, 1), datetime(1970, 1, 5))
    False
    >>> is_same_week(datetime(1970, 1, 1), datetime(1971, 1, 1))
    False
    """
    _, week1, _ = date1.isocalendar()
    _, week2, _ = date2.isocalendar()
    assert(date1 < date2)
    return week1 == week2 and date2 - date1 < timedelta(weeks=1)
