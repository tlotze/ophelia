# Copyright (c) 2006-2012 Thomas Lotze
# See also LICENSE.txt

import codecs
import datetime
import locale
import md5
import ophelia.request
import ophelia.util
import os


RFC2822_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"

HEX_ENCODER = codecs.getencoder("hex_codec")


def c_locale(function):
    # XXX implement as context manager when 2.4 support has been dropped
    def wrapper(*args, **kw):
        current_locale = locale.getlocale()
        locale.setlocale(locale.LC_ALL, 'C')
        try:
            return function(*args, **kw)
        finally:
            locale.setlocale(locale.LC_ALL, current_locale)
    return wrapper


class MetaData(object):
    """Stores, calculates and formats metadata such as dates or digests.
    """

    def __init__(self):
        self.request = ophelia.request.get_request()
        self._date = datetime.datetime.min

    def bump_date(self, *args):
        """Store the maximum of the given date and that stored before.

        *args: datetime.datetime arguments

        returns nothing
        """
        if len(args) == 1 and isinstance(args[0], datetime.datetime):
            date = args[0]
        else:
            date = datetime.datetime(*args)
        self._date = max(self._date, date)

    def mtime(self):
        """Return the mtime of the current input file as a datetime object.
        """
        try:
            file_path = ophelia.request.get_file_context().__file__
        except AttributeError:
            raise LookupError("Could not find current input file.")

        mtime = os.stat(file_path).st_mtime
        return datetime.datetime.fromtimestamp(mtime)

    def date(self, format=RFC2822_FORMAT):
        """Format the stored date, defaults to RFC 2822 compliant format.

        format: str, format str

        returns str
        """
        return ophelia.util.strftime(format, self._date)

    @c_locale
    def header_date(self):
        """Format the stored date in RFC 2822 compliant format and C locale.

        returns str
        """
        return ophelia.util.strftime(RFC2822_FORMAT, self._date)

    @c_locale
    def expires(self, *args):
        """Calulate a date relative to now, format by RFC 2822 in C locale.

        *args: datetime.timedelta arguments

        returns str
        """
        exp_date = datetime.datetime.now() + datetime.timedelta(*args)
        return exp_date.strftime(RFC2822_FORMAT)

    def etag(self):
        """Calculate an ETag for the page.

        returns str
        """
        if self.request.content is None:
            raise RuntimeError(
                "Can't compute an Etag before content has been built.")

        obj = md5.new()
        obj.update(self.request.content)
        return HEX_ENCODER(obj.digest())[0]
