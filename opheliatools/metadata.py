import datetime
import md5
import codecs

import ophelia.publisher


RFC2822_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"

HEX_ENCODER = codecs.getencoder("hex_codec")


class MetaData(object):
    """Stores, calculates and formats metadata such as dates or digests.

    Registers with the TALES names.
    """

    def __init__(self, tales_name="meta"):
        self.publisher = ophelia.publisher.get_publisher()
        self._date = datetime.datetime.min

    def bumpDate(self, *args):
        """Store the maximum of the given date and that stored before.

        *args: datetime.datetime arguments

        returns nothing
        """
        date = datetime.datetime(*args)
        self._date = max(self._date, date)

    def date(self, format=RFC2822_FORMAT):
        """Format the stored date, defaults to RFC 2822 compliant format.

        format: str, format str

        returns str
        """
        return self._date.strftime(format)

    def expires(self, *args):
        """Calulate a date relative to now, format by RFC 2822.

        *args: datetime.timedelta arguments

        returns str
        """
        exp_date = datetime.datetime.now() + datetime.timedelta(*args)
        return exp_date.strftime(RFC2822_FORMAT)

    def etag(self):
        """Calculate an ETag for the page.

        returns str
        """
        if self.publisher.content is None:
            raise RuntimeError(
                "Can't compute an Etag before content has been built.")
        
        obj = md5.new()
        obj.update(self.publisher.content)
        return HEX_ENCODER(obj.digest())[0]
