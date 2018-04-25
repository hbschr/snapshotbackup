from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse


class TimestampParseError(Exception):
    def __init__(self, message, error):
        super().__init__(message)
        self.error = error

    def __str__(self):
        return f'TimestampParseError: {self.error}'


def get_timestamp():
    """returns a timezone aware datetime object for `now`

    >>> from btrfsbackup.timestamps import get_timestamp
    >>> get_timestamp()
    datetime.datetime(...)
    """
    return datetime.now(timezone.utc).replace(microsecond=0).astimezone()


def parse_timestamp(string):
    """

    :param string:
    :return datetime:

    >>> from btrfsbackup.timestamps import parse_timestamp
    >>> parse_timestamp('1989-11-09')
    datetime.datetime(1989, 11, 9, 0, 0)
    >>> parse_timestamp('some random string')
    Traceback (most recent call last):
    ...
    btrfsbackup.timestamps.TimestampParseError: ...
    """
    try:
        return isoparse(string)
    except ValueError as e:
        # invalid date
        raise TimestampParseError(str(e), e) from e
    except OverflowError as e:                          # pragma: no cover
        # parsed date exceeds the largest valid C integer
        raise TimestampParseError(str(e), e) from e     # pragma: no cover


def is_timestamp(string):
    """

    :param string:
    :return bool: if given string could be parsed as valid timestamp

    >>> from btrfsbackup.timestamps import is_timestamp
    >>> is_timestamp('1989-11-09')
    True
    >>> is_timestamp('some random string')
    False
    """
    try:
        parse_timestamp(string)
        return True
    except TimestampParseError as e:
        return False


def is_same_hour(date1: datetime, date2: datetime) -> bool:
    """
    >>> from btrfsbackup.timestamps import is_same_hour
    >>> from datetime import datetime
    >>> is_same_hour(datetime(1970, 1, 1, 1), datetime(1970, 1, 1, 1, 59, 59))
    True
    >>> is_same_hour(datetime(1970, 1, 1, 1), datetime(1970, 1, 2))
    False
    >>> is_same_hour(datetime(1970, 1, 1, 1), datetime(1970, 1, 2, 1))
    False
    """
    assert(date1 < date2)
    return date1.hour == date2.hour and date2 - date1 < timedelta(hours=1)


def is_same_day(date1: datetime, date2: datetime) -> bool:
    """
    >>> from btrfsbackup.timestamps import is_same_day
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
    """
    >>> from btrfsbackup.timestamps import is_same_week
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
