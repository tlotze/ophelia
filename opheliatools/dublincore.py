import datetime

from ophelia import oapi


def bumpDate(*args):
    date = datetime.datetime(*args)
    context = oapi.getContext()
    if hasattr(context, "dc_date"):
        max_date = max(context.dc_date, date)
    else:
        max_date = date
    context.dc_date = max_date
    context.dc_date_rfc2822 = max_date.strftime(
        "%a, %d %b %Y %H:%M:%S GMT")
    return max_date
