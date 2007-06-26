# Copyright (c) 2007 Thomas Lotze
# See also LICENSE.txt

import locale
import time
import datetime


class Namespace(dict):
    """Collection of named variables, accessible both as attributes and
       mapping items.
    """

    def __init__(self, *args, **kwargs):
        self.__dict__ = self
        super(Namespace, self).__init__(*args, **kwargs)


def strftime(format, t=None):
    """Similar to time.strftime, but returns unicode.

    Decodes the time representation returned by time.strftime according to the
    character encoding as determined by the current locale.

    format: str or unicode, a time format string
    t: optional, if given: tuple, datetime.datetime, or datetime.time
       If t is omitted, the current time is used. If t is a tuple, it must be
       a valid time tuple as accepted by time.strftime().

    returns unicode
    """
    encoding = locale.nl_langinfo(locale.CODESET)
    format = format.encode(encoding)

    if t is None:
        time_str = time.strftime(format)
    else:
        if isinstance(t, (datetime.datetime, datetime.date)):
            t = t.timetuple()
        time_str = time.strftime(format, t)

    return time_str.decode(encoding)
